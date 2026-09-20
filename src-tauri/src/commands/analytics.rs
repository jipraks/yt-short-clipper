//! Product analytics via the GA4 Measurement Protocol.
//!
//! This runs in Rust rather than the webview on purpose. The `gtag.js` snippet
//! assumes a real web origin — in Tauri the page is served from
//! `http://tauri.localhost`, so its cookies, `page_location` and referrer all
//! come out wrong and GA4 files the app as a broken website. The Measurement
//! Protocol is the supported path for a non-browser client, and sending it from
//! here also keeps the API secret out of the JS bundle.
//!
//! Nothing in this module is allowed to fail loudly: analytics must never cost
//! a user their render.

use serde_json::json;
use std::sync::OnceLock;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// GA4 measurement ID for the project's own property.
///
/// Not a secret: it ships in the page source of every site that uses GA, so it
/// lives here rather than in the build environment. `GA_MEASUREMENT_ID`
/// overrides it, which is what a fork wants — though a fork that only sets its
/// own `GA_API_SECRET` still sends nothing anywhere, since a secret minted on
/// another property is rejected rather than accepted into this one.
const MEASUREMENT_ID: &str = match option_env!("GA_MEASUREMENT_ID") {
    Some(value) => value,
    None => "G-Q85RTZ06HJ",
};

/// The Measurement Protocol secret, injected at build time.
///
/// Deliberately not a committed constant: this repository is public, and a
/// secret in it can be found by anyone reading the source rather than only by
/// somebody willing to unpack a binary. Google treats this value as
/// low-sensitivity — worst case is somebody posting junk events — but there is
/// no reason to publish it. Set `GA_API_SECRET` in the release build
/// environment; leaving it unset disables analytics entirely, which is what
/// developer builds want anyway.
const API_SECRET: Option<&str> = option_env!("GA_API_SECRET");

const ENDPOINT: &str = "https://www.google-analytics.com/mp/collect";

/// Short: a dropped event is worth far less than a responsive app.
const TIMEOUT: Duration = Duration::from_secs(5);

/// The gate, as a pure function so it can be tested without depending on how
/// the test runner happened to be invoked.
///
/// The secret is the whole gate: the measurement ID is compiled in, so a build
/// that was never given a secret is exactly a build that must stay silent.
fn credentials(api_secret: Option<&'static str>) -> Option<&'static str> {
    api_secret.filter(|secret| !secret.trim().is_empty())
}

/// Whether this build was given a secret. None in any dev build.
fn configured() -> Option<&'static str> {
    credentials(API_SECRET)
}

/// One id per app launch, which is what GA4 means by a session.
///
/// GA4 will happily accept events without `session_id`, then attribute them to
/// no session at all — events land, and every user- and session-scoped metric
/// in the reports stays empty. It is the most common way this integration looks
/// like it works while reporting nothing.
fn session_id() -> &'static str {
    static SESSION: OnceLock<String> = OnceLock::new();
    SESSION.get_or_init(|| {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs().to_string())
            .unwrap_or_else(|_| "0".to_string())
    })
}

/// Sends one GA4 event. Never returns an error to the caller.
///
/// `client_id` is the app's installation UUID — the same stable per-install id
/// the update and notification checks used to send, which is exactly what GA4
/// wants a client id to be.
#[tauri::command]
pub async fn analytics_track(
    client_id: String,
    name: String,
    params: serde_json::Value,
) -> Result<(), String> {
    let _ = tauri::async_runtime::spawn_blocking(move || send(&client_id, &name, params)).await;
    Ok(())
}

/// Builds the Measurement Protocol body, injecting the two fields GA4 needs to
/// attribute an event to a session at all.
fn build_payload(client_id: &str, name: &str, params: serde_json::Value) -> serde_json::Value {
    let mut params = match params {
        serde_json::Value::Object(map) => map,
        _ => serde_json::Map::new(),
    };
    params.insert("session_id".into(), json!(session_id()));
    // Without this GA4 counts the event but not the engagement behind it, and
    // the user is never marked active for the session.
    params.insert("engagement_time_msec".into(), json!("1"));

    json!({
        "client_id": client_id,
        "events": [{ "name": name, "params": params }],
    })
}

fn send(client_id: &str, name: &str, params: serde_json::Value) {
    let Some(secret) = configured() else {
        return;
    };

    let body = build_payload(client_id, name, params);
    let url = format!("{ENDPOINT}?measurement_id={MEASUREMENT_ID}&api_secret={secret}");

    // Every failure path is a no-op: no network, a 4xx, a malformed reply. GA4
    // answers 204 on success and, unhelpfully, 2xx for most bad payloads too,
    // so there is nothing useful to branch on even when it does reply.
    let _ = reqwest::blocking::Client::builder()
        .timeout(TIMEOUT)
        .build()
        .and_then(|client| client.post(url).json(&body).send());
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Asserted on the gate itself rather than on this build's env, so the
    /// suite passes both in a dev checkout and in a release build that really
    /// does carry credentials.
    #[test]
    fn analytics_stays_off_until_a_secret_is_supplied() {
        assert!(credentials(None).is_none());
        assert!(credentials(Some("")).is_none());
        assert!(credentials(Some("   ")).is_none());
        assert_eq!(credentials(Some("secret")), Some("secret"));
    }

    #[test]
    fn the_measurement_id_is_a_real_ga4_id() {
        assert!(MEASUREMENT_ID.starts_with("G-"));
        assert!(MEASUREMENT_ID.len() > 3);
    }

    #[test]
    fn every_event_carries_what_ga4_needs_to_attribute_a_session() {
        let body = build_payload("install-uuid", "clip_rendered", json!({ "duration_seconds": 91.5 }));
        let params = &body["events"][0]["params"];

        assert_eq!(body["client_id"], "install-uuid");
        assert_eq!(body["events"][0]["name"], "clip_rendered");
        // The caller's own parameters survive.
        assert_eq!(params["duration_seconds"], 91.5);
        // GA4 drops these events into no session without both of these.
        assert!(params["session_id"].is_string());
        assert_eq!(params["engagement_time_msec"], "1");
    }

    #[test]
    fn a_non_object_params_value_does_not_produce_a_malformed_event() {
        let body = build_payload("install-uuid", "clip_rendered", json!("nonsense"));
        assert!(body["events"][0]["params"]["session_id"].is_string());
    }

    #[test]
    fn the_session_id_is_stable_within_a_process() {
        assert_eq!(session_id(), session_id());
    }
}
