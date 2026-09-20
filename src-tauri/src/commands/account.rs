//! The in-app AI account: device registration, QRIS top-ups, and the LiteLLM
//! key the sidecar actually infers with.
//!
//! Everything here runs in Rust rather than the renderer on purpose. The device
//! token *is* the balance — there is no password behind it and no recovery path
//! on the server — so it lives in the OS credential store and never crosses the
//! IPC boundary. The one deliberate exception is [`account_export_token`],
//! which exists because a design with no server-side recovery has to give the
//! user *some* way to carry their balance to a new machine.
//!
//! The LiteLLM secret is treated as derived state: it can always be re-minted
//! from the device token, so losing it is a rotation, not a disaster.

use serde::{Deserialize, Serialize};
use serde_json::json;
use std::time::Duration;

/// Account, billing and catalogue. Not the inference endpoint.
const API_BASE: &str = "https://api-v2.ytclip.org/api/public/v1";

/// Where the LiteLLM key from `POST /keys` is actually used.
pub const INFERENCE_BASE: &str = "https://ai-api.ytclip.org/v1";

const KEYRING_SERVICE: &str = "com.jipraks.ytshortclipper-v2";
const ENTRY_DEVICE_TOKEN: &str = "device-token";
const ENTRY_INFERENCE_KEY: &str = "litellm-key";

/// The name every key this app mints is created under.
const KEY_NAME: &str = "YT Short Clipper";

const TIMEOUT: Duration = Duration::from_secs(30);

// ---------------------------------------------------------------------------
// Credential store
// ---------------------------------------------------------------------------

fn entry(name: &str) -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, name)
        .map_err(|e| format!("KEYSTORE: cannot open the OS credential store: {e}"))
}

fn secret_read(name: &str) -> Result<Option<String>, String> {
    match entry(name)?.get_password() {
        Ok(value) if value.trim().is_empty() => Ok(None),
        Ok(value) => Ok(Some(value)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(format!("KEYSTORE: cannot read from the credential store: {e}")),
    }
}

fn secret_write(name: &str, value: &str) -> Result<(), String> {
    entry(name)?
        .set_password(value)
        .map_err(|e| format!("KEYSTORE: cannot write to the credential store: {e}"))
}

fn secret_delete(name: &str) -> Result<(), String> {
    match entry(name)?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(format!("KEYSTORE: cannot clear the credential store: {e}")),
    }
}

fn device_token() -> Result<String, String> {
    secret_read(ENTRY_DEVICE_TOKEN)?
        .ok_or_else(|| "NO_ACCOUNT: In-app AI is not activated on this device yet.".to_string())
}

/// The displayable half of the token. Everything before the dot, minus the
/// prefix — safe to show and to quote to support.
fn account_id_from_token(token: &str) -> String {
    token
        .split('.')
        .next()
        .unwrap_or(token)
        .trim_start_matches("ytclip_dev_")
        .to_string()
}

/// Cheap shape check so an obviously wrong paste fails before a round trip.
fn looks_like_token(token: &str) -> bool {
    token.starts_with("ytclip_dev_") && token.split('.').count() == 2
        && token.split('.').all(|part| !part.is_empty())
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------

fn client() -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .timeout(TIMEOUT)
        .build()
        .map_err(|e| format!("NETWORK: cannot create the HTTP client: {e}"))
}

#[derive(Deserialize)]
struct ApiErrorEnvelope {
    error: ApiErrorBody,
}

#[derive(Deserialize)]
struct ApiErrorBody {
    code: String,
    message: String,
    #[serde(default)]
    details: Option<serde_json::Value>,
}

/// How much of a `details` payload or an unexpected body is worth carrying.
const MAX_DETAIL_CHARS: usize = 400;

/// Appends technical context inside a trailing `[...]`.
///
/// Errors here are a single string, because that is all a Tauri command can
/// return, and the string has to serve two readers at once: a person, who wants
/// the sentence, and whoever is debugging, who wants the endpoint and the
/// status code. The bracket keeps them apart — `errorMessage()` on the frontend
/// strips it for toasts, and the run log prints the whole thing.
fn with_context(error: String, context: &str) -> String {
    match error.strip_suffix(']') {
        Some(head) => format!("{head}; {context}]"),
        None => format!("{error} [{context}]"),
    }
}

fn truncate(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.chars().count() <= MAX_DETAIL_CHARS {
        return trimmed.to_string();
    }
    let cut: String = trimmed.chars().take(MAX_DETAIL_CHARS).collect();
    format!("{cut}…")
}

/// Turns a response into either its JSON body or a `CODE: message [context]`
/// error.
///
/// The prefix is the contract with the frontend: it branches on the code, never
/// on the prose, exactly as the API documents for its own envelope. The
/// bracketed tail names the request that failed, which is the difference
/// between "the AI service rejected the request" and something anybody can act
/// on.
fn read_response(
    method: &str,
    path: &str,
    response: reqwest::blocking::Response,
) -> Result<serde_json::Value, String> {
    let status = response.status();
    let route = format!("{method} {path} → {}", status.as_u16());

    let body = response.text().map_err(|e| {
        with_context(
            format!("NETWORK: cannot read the response body: {e}"),
            &route,
        )
    })?;

    if status.is_success() {
        if body.trim().is_empty() {
            return Ok(serde_json::Value::Null);
        }
        return serde_json::from_str(&body).map_err(|e| {
            with_context(
                format!("UPSTREAM_FAILED: unreadable response: {e}"),
                &format!("{route}; body: {}", truncate(&body)),
            )
        });
    }

    match serde_json::from_str::<ApiErrorEnvelope>(&body) {
        Ok(envelope) => {
            let mut context = route;
            if let Some(details) = envelope.error.details {
                context.push_str(&format!("; details: {}", truncate(&details.to_string())));
            }
            Err(with_context(
                format!("{}: {}", envelope.error.code, envelope.error.message),
                &context,
            ))
        }
        Err(_) => Err(with_context(
            "UPSTREAM_FAILED: the server answered with an unexpected body".to_string(),
            &format!("{route}; body: {}", truncate(&body)),
        )),
    }
}

fn get(path: &str, token: &str) -> Result<serde_json::Value, String> {
    let response = client()?
        .get(format!("{API_BASE}{path}"))
        .bearer_auth(token)
        .send()
        .map_err(|e| network_error(e, "GET", path))?;
    read_response("GET", path, response)
}

fn post(path: &str, token: &str, body: serde_json::Value) -> Result<serde_json::Value, String> {
    let response = client()?
        .post(format!("{API_BASE}{path}"))
        .bearer_auth(token)
        .json(&body)
        .send()
        .map_err(|e| network_error(e, "POST", path))?;
    read_response("POST", path, response)
}

fn delete(path: &str, token: &str) -> Result<serde_json::Value, String> {
    let response = client()?
        .delete(format!("{API_BASE}{path}"))
        .bearer_auth(token)
        .send()
        .map_err(|e| network_error(e, "DELETE", path))?;
    read_response("DELETE", path, response)
}

fn network_error(e: reqwest::Error, method: &str, path: &str) -> String {
    let message = if e.is_timeout() {
        "NETWORK: the server did not answer in time. Check your connection and try again."
            .to_string()
    } else {
        format!("NETWORK: cannot reach the YTClip AI server: {e}")
    };
    with_context(message, &format!("{method} {path}"))
}

// ---------------------------------------------------------------------------
// The LiteLLM key
// ---------------------------------------------------------------------------

/// Returns the key the sidecar should infer with, minting one if this device
/// does not have it.
///
/// A device can hold a valid token and no key at all — after a restore on a new
/// machine, for instance, where the account has keys but their secrets stayed
/// behind. Minting a fresh one is always correct; the old ones are cleaned up
/// by [`rotate_inference_key`] on the restore path.
fn ensure_inference_key() -> Result<String, String> {
    if let Some(secret) = secret_read(ENTRY_INFERENCE_KEY)? {
        return Ok(secret);
    }
    let token = device_token()?;
    mint_inference_key(&token)
}

fn mint_inference_key(token: &str) -> Result<String, String> {
    let created = post(
        "/keys",
        token,
        json!({ "name": KEY_NAME, "maxBudgetUsd": null }),
    )?;

    let secret = created
        .get("secret")
        .and_then(|v| v.as_str())
        .ok_or("UPSTREAM_FAILED: the server issued a key without a secret")?;

    secret_write(ENTRY_INFERENCE_KEY, secret)?;
    Ok(secret.to_string())
}

/// Mint first, store, then revoke the old ones.
///
/// That order matters: a failure anywhere leaves the device with a key that
/// works. The reverse order can strand an account with no usable key and no way
/// to recover the secrets of the ones it just deleted.
fn rotate_inference_key(token: &str) -> Result<String, String> {
    let existing: Vec<String> = get("/keys", token)
        .ok()
        .and_then(|v| v.get("data").cloned())
        .and_then(|v| v.as_array().cloned())
        .unwrap_or_default()
        .iter()
        .filter_map(|key| key.get("token").and_then(|t| t.as_str()).map(String::from))
        .collect();

    let secret = mint_inference_key(token)?;

    for old in existing {
        // Best effort. A key that outlives its rotation costs nothing as long
        // as nobody holds its secret, and failing here would strand a device
        // that already has a working key.
        let _ = delete(&format!("/keys/{old}"), token);
    }

    Ok(secret)
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AccountState {
    /// Whether this device holds a token at all. False means in-app AI has
    /// never been activated here.
    activated: bool,
    /// Displayable half of the token, or null when there is none.
    account_id: Option<String>,
    /// Whether a LiteLLM secret is already stored locally.
    has_inference_key: bool,
}

/// Local state only — no network, safe to call on every launch.
#[tauri::command]
pub async fn account_state() -> Result<AccountState, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = secret_read(ENTRY_DEVICE_TOKEN)?;
        Ok(AccountState {
            account_id: token.as_deref().map(account_id_from_token),
            activated: token.is_some(),
            has_inference_key: secret_read(ENTRY_INFERENCE_KEY)?.is_some(),
        })
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Creates the account for this installation and mints its first LiteLLM key.
///
/// Deliberately not called on first launch: an account here can never be
/// deleted by the user and can never be recovered without its token, so one is
/// created only when somebody actually asks for in-app AI.
///
/// `idempotency_key` is the installation UUID the app already keeps, so a
/// timeout that really succeeded server-side returns the same token instead of
/// silently orphaning an account nobody can reach.
#[tauri::command]
pub async fn account_register(
    app_version: String,
    idempotency_key: String,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        if secret_read(ENTRY_DEVICE_TOKEN)?.is_some() {
            return Err(
                "ALREADY_ACTIVATED: this device already has an in-app AI account.".to_string(),
            );
        }

        let platform = if cfg!(windows) {
            "win32"
        } else if cfg!(target_os = "macos") {
            "darwin"
        } else {
            "linux"
        };

        let response = client()?
            .post(format!("{API_BASE}/devices"))
            .header("Idempotency-Key", idempotency_key)
            .json(&json!({ "platform": platform, "appVersion": app_version }))
            .send()
            .map_err(|e| network_error(e, "POST", "/devices"))?;

        let created = read_response("POST", "/devices", response)?;
        let token = created
            .get("token")
            .and_then(|v| v.as_str())
            .ok_or("UPSTREAM_FAILED: registration returned no token")?;

        // Persist before anything else can fail. The token is returned exactly
        // once; losing it here loses the account permanently.
        secret_write(ENTRY_DEVICE_TOKEN, token)?;

        // A key failure is not fatal — the account exists and `ensure` will try
        // again on first use — so the activation still counts as done. It is
        // still worth a line on stderr: without one, a server that cannot mint
        // keys looks like a successful activation here and only surfaces as a
        // rejected run much later.
        if let Err(e) = mint_inference_key(token) {
            eprintln!("[account] registered, but minting the first key failed: {e}");
        }

        get("/me", token)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Balance, membership and block state.
#[tauri::command]
pub async fn account_me() -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        get("/me", &token)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// The device token in plaintext, for the Export Account Key screen.
///
/// This is the only place the secret is ever handed out, and it exists because
/// the server keeps no way to restore a lost balance. Callers must show it
/// behind an explicit reveal, never render it unprompted, and never log it.
#[tauri::command]
pub async fn account_export_token() -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(device_token)
        .await
        .map_err(|e| format!("Task failed: {e}"))?
}

/// Adopts an exported token on this device and gives it a fresh LiteLLM key.
///
/// The paste is validated against `/me` before anything is written, so a typo
/// cannot evict a working account.
/// Writes the account key to a file the user picked.
///
/// The renderer chooses the path and never has to hold the secret to do it —
/// saving a backup should not require revealing the key on screen first.
#[tauri::command]
pub async fn account_export_to_file(path: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        let contents = format!(
            "YT Short Clipper — in-app AI account key\n\
             \n\
             Account: {}\n\
             \n\
             Anyone holding the line below can spend this account's balance.\n\
             It is also the only way to get the balance back after a reinstall,\n\
             a new machine, or a disk failure. Nobody can restore it for you,\n\
             support included. Keep this file somewhere private and backed up.\n\
             \n\
             {}\n",
            account_id_from_token(&token),
            token
        );
        std::fs::write(&path, contents).map_err(|e| format!("IO: cannot write {path}: {e}"))
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[tauri::command]
pub async fn account_restore(token: String) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = token.trim().to_string();
        if !looks_like_token(&token) {
            return Err(
                "VALIDATION_FAILED: that does not look like an account key. It starts with \
                 ytclip_dev_ and contains a single dot."
                    .to_string(),
            );
        }

        let account = get("/me", &token)?;

        secret_write(ENTRY_DEVICE_TOKEN, &token)?;
        secret_delete(ENTRY_INFERENCE_KEY)?;

        // The secrets of this account's existing keys stayed on the old
        // machine, so they are dead weight here — mint ours and retire them.
        let _ = rotate_inference_key(&token);

        Ok(account)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Detaches the account from this device without touching the server.
///
/// The balance stays with the token, so a caller must make sure the user has
/// exported it first — there is no way back otherwise.
#[tauri::command]
pub async fn account_forget() -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        secret_delete(ENTRY_DEVICE_TOKEN)?;
        secret_delete(ENTRY_INFERENCE_KEY)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Exchange rate, platform fee and top-up limits for the top-up screen.
#[tauri::command]
pub async fn account_fee_rate() -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        get("/fee-rate", &token)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// The model catalogue, with prices and capabilities.
#[tauri::command]
pub async fn account_models() -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        get("/models", &token)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Creates a QRIS invoice. The caller renders `qrString` as a QR code.
#[tauri::command]
pub async fn account_topup_create(usd_amount: u32) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        post("/topups", &token, json!({ "usdAmount": usd_amount }))
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Polls one invoice. `force` skips the server's own 4-second throttle and is
/// only for an explicit "I have paid" press.
#[tauri::command]
pub async fn account_topup_get(
    topup_id: String,
    force: Option<bool>,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        let path = if force.unwrap_or(false) {
            format!("/topups/{topup_id}?force=true")
        } else {
            format!("/topups/{topup_id}")
        };
        get(&path, &token)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Top-up history, newest first.
#[tauri::command]
pub async fn account_topups(page: Option<u32>, page_size: Option<u32>) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        get(
            &format!(
                "/topups?page={}&pageSize={}",
                page.unwrap_or(1),
                page_size.unwrap_or(10)
            ),
            &token,
        )
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Per-request spend log. Dates are Jakarta calendar dates, not instants.
#[tauri::command]
pub async fn account_usage(
    start_date: String,
    end_date: String,
    page: Option<u32>,
    page_size: Option<u32>,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let token = device_token()?;
        get(
            &format!(
                "/usage?startDate={start_date}&endDate={end_date}&page={}&pageSize={}",
                page.unwrap_or(1),
                page_size.unwrap_or(20)
            ),
            &token,
        )
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

/// Version floor and notices. Unauthenticated: an app too old to authenticate
/// still has to be able to learn that it is too old.
#[tauri::command]
pub async fn account_app_info() -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let response = client()?
            .get(format!("{API_BASE}/app"))
            .send()
            .map_err(|e| network_error(e, "GET", "/app"))?;
        read_response("GET", "/app", response)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

// ---------------------------------------------------------------------------
// Resolver
// ---------------------------------------------------------------------------

/// Fills in the credentials a sidecar call needs, then drops the `source` marker.
///
/// The renderer sends `{ source: "inapp", model }` and never sees a key; this is
/// where the LiteLLM secret joins the payload, one layer below the webview.
/// Custom providers pass through untouched — their key was typed by the user
/// and already sits in the payload.
pub fn resolve_ai(ai: &mut serde_json::Value) -> Result<(), String> {
    resolve_ai_with(ai, |_| {})
}

/// As [`resolve_ai`], but reports what it is doing.
///
/// This step runs before the sidecar is even spawned, so without a log line of
/// its own a failure here lands between "Starting..." and an error with no
/// indication that the app never got as far as the transcript.
pub fn resolve_ai_with<F: Fn(String)>(
    ai: &mut serde_json::Value,
    log: F,
) -> Result<(), String> {
    let object = ai
        .as_object_mut()
        .ok_or("VALIDATION_FAILED: malformed AI settings")?;

    let source = object
        .get("source")
        .and_then(|v| v.as_str())
        .unwrap_or("custom")
        .to_string();
    object.remove("source");

    if source == "inapp" {
        let had_key = secret_read(ENTRY_INFERENCE_KEY)?.is_some();
        log(if had_key {
            "Using the in-app AI key from the credential store".to_string()
        } else {
            "No in-app AI key stored yet — asking the server for one".to_string()
        });

        let secret = ensure_inference_key().map_err(|e| {
            with_context(
                e,
                if had_key {
                    "while reading the in-app AI key"
                } else {
                    "while issuing an in-app AI key"
                },
            )
        })?;
        object.insert("api_key".into(), json!(secret));
        object.insert("base_url".into(), json!(INFERENCE_BASE));
    } else {
        log(format!(
            "Using your own API key at {}",
            object
                .get("base_url")
                .and_then(|v| v.as_str())
                .unwrap_or("(no base URL)")
        ));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn account_id_is_the_half_before_the_dot() {
        assert_eq!(
            account_id_from_token("ytclip_dev_01M2Z5WT8YVJ447X96ZNYT4HKZ.7f3a9c2e"),
            "01M2Z5WT8YVJ447X96ZNYT4HKZ"
        );
    }

    #[test]
    fn obvious_mispastes_are_rejected() {
        assert!(looks_like_token("ytclip_dev_01M2Z.7f3a"));
        assert!(!looks_like_token("ytclip_dev_01M2Z"));
        assert!(!looks_like_token("ytclip_dev_01M2Z."));
        assert!(!looks_like_token("sk-9d8c7b6a5f4e3d2c"));
        assert!(!looks_like_token("ytclip_dev_01M2Z.7f3a.extra"));
    }

    #[test]
    fn inapp_gets_its_credentials_and_loses_the_marker() {
        // Without a credential store this cannot reach the happy path, but the
        // custom branch must stay a pure pass-through.
        let mut ai = json!({ "source": "custom", "api_key": "sk-typed", "base_url": "https://x/v1", "model": "m" });
        resolve_ai(&mut ai).unwrap();
        assert_eq!(ai["api_key"], "sk-typed");
        assert_eq!(ai["base_url"], "https://x/v1");
        assert!(ai.get("source").is_none());
    }

    #[test]
    fn context_is_appended_once_and_then_merged() {
        let first = with_context("UPSTREAM_FAILED: rejected".into(), "POST /keys → 502");
        assert_eq!(first, "UPSTREAM_FAILED: rejected [POST /keys → 502]");

        // A second layer joins the same bracket rather than nesting, so the
        // frontend only ever has one tail to strip.
        let second = with_context(first, "while issuing an in-app AI key");
        assert_eq!(
            second,
            "UPSTREAM_FAILED: rejected [POST /keys → 502; while issuing an in-app AI key]"
        );
    }

    #[test]
    fn long_details_are_cut_on_a_character_boundary() {
        let long = "é".repeat(MAX_DETAIL_CHARS + 50);
        let cut = truncate(&long);
        assert_eq!(cut.chars().count(), MAX_DETAIL_CHARS + 1);
        assert!(cut.ends_with('…'));
    }

    #[test]
    fn a_missing_source_is_treated_as_custom() {
        let mut ai = json!({ "api_key": "sk-typed", "model": "m" });
        resolve_ai(&mut ai).unwrap();
        assert_eq!(ai["api_key"], "sk-typed");
    }
}
