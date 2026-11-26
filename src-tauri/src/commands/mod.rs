pub mod account;
pub mod analytics;
pub mod config_store;

use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use tauri::ipc::Channel;
use tauri::Manager;

const REQUIRED_COOKIES: [&str; 6] = ["SID", "HSID", "SSID", "APISID", "SAPISID", "LOGIN_INFO"];
const SECURE_COOKIE_PREFIXES: [&str; 2] = ["__Secure-1P", "__Secure-3P"];

#[cfg(windows)]
const SIDECAR_BINARY: &str = "ytclip-sidecar-x86_64-pc-windows-msvc.exe";
#[cfg(windows)]
const SIDECAR_BINARY_BARE: &str = "ytclip-sidecar.exe";
#[cfg(target_os = "macos")]
const SIDECAR_BINARY: &str = "ytclip-sidecar-x86_64-apple-darwin";
#[cfg(target_os = "macos")]
const SIDECAR_BINARY_BARE: &str = "ytclip-sidecar";
#[cfg(target_os = "linux")]
const SIDECAR_BINARY: &str = "ytclip-sidecar-x86_64-unknown-linux-gnu";
#[cfg(target_os = "linux")]
const SIDECAR_BINARY_BARE: &str = "ytclip-sidecar";

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CookiesStatus {
    exists: bool,
    valid: bool,
    path: String,
    found_cookies: Vec<String>,
    error: Option<String>,
}

#[derive(Serialize, Deserialize)]
pub struct SubtitleItem {
    code: String,
    name: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SubtitleListResponse {
    subtitles: Vec<SubtitleItem>,
    #[serde(alias = "automatic_captions")]
    automatic_captions: Vec<SubtitleItem>,
    /// Original-language auto-caption code (the `*-orig` track), or null.
    /// Word-by-word captions are only possible when this is present.
    #[serde(default, alias = "caption_orig_code")]
    caption_orig_code: Option<String>,
    error: Option<String>,
}

#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to YT Short Clipper v2.", name)
}

#[tauri::command]
pub fn load_app_config(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    config_store::load(&cookies_dir(&app)?, default_app_config(), &config_store::OsSecretStore)
}

#[tauri::command]
pub fn save_app_config(app: tauri::AppHandle, config: serde_json::Value) -> Result<serde_json::Value, String> {
    config_store::save(&cookies_dir(&app)?, config, &config_store::OsSecretStore)
}

#[tauri::command]
pub fn save_cookies(app: tauri::AppHandle, content: String) -> Result<CookiesStatus, String> {
    let cookies_dir = cookies_dir(&app)?;
    fs::create_dir_all(&cookies_dir).map_err(|e| format!("Failed to create app data directory: {e}"))?;

    let cookies_path = cookies_dir.join("cookies.txt");

    // Check before writing: a wrong file (another site's cookies, a logged-out
    // export) must not overwrite cookies that still work.
    if find_auth_cookies(&content).is_empty() {
        return Ok(CookiesStatus {
            exists: cookies_path.exists(),
            valid: false,
            path: cookies_path.to_string_lossy().to_string(),
            found_cookies: vec![],
            error: Some(
                "Invalid cookies.txt - missing YouTube authentication cookies. Please export fresh cookies while logged into YouTube."
                    .to_string(),
            ),
        });
    }

    fs::write(&cookies_path, content).map_err(|e| format!("Failed to save cookies.txt: {e}"))?;

    read_cookies_status_for_path(cookies_path)
}

#[tauri::command]
pub fn get_cookies_status(app: tauri::AppHandle) -> Result<CookiesStatus, String> {
    let cookies_path = cookies_dir(&app)?.join("cookies.txt");
    read_cookies_status_for_path(cookies_path)
}

#[derive(Deserialize)]
struct SidecarResponse {
    ok: bool,
    #[serde(default)]
    result: Option<serde_json::Value>,
    #[serde(default)]
    error: Option<String>,
}

#[tauri::command]
pub async fn detect_gpu(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || call_sidecar(&app, "detect_gpu", serde_json::json!({})))
        .await
        .map_err(|e| format!("Task failed: {e}"))?
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
#[serde(tag = "type")]
pub enum FindHighlightsEvent {
    Log { message: String },
}

#[tauri::command]
pub async fn find_highlights(
    app: tauri::AppHandle,
    url: String,
    num_clips: u32,
    subtitle_language: String,
    mut ai: serde_json::Value,
    // Optional free-text steer typed on the Create page; empty means "none".
    user_direction: Option<String>,
    // Language code for titles and hooks; "auto"/None follows the video.
    output_language: Option<String>,
    on_event: Channel<FindHighlightsEvent>,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        account::resolve_ai_with(&mut ai, |message| {
            let _ = on_event.send(FindHighlightsEvent::Log { message });
        })?;

        let cookies_path = cookies_dir(&app)?.join("cookies.txt");
        let cookies_status = read_cookies_status_for_path(cookies_path.clone())?;
        if !cookies_status.valid {
            return Err(cookies_status
                .error
                .unwrap_or_else(|| "Invalid cookies".to_string()));
        }

        let output_dir = cookies_dir(&app)?.join("output");

        let payload = serde_json::json!({
            "url": url,
            "num_clips": num_clips,
            "subtitle_language": subtitle_language,
            "cookies_path": cookies_path.to_string_lossy(),
            "output_dir": output_dir.to_string_lossy(),
            "ai": ai,
            "user_direction": user_direction
                .as_deref()
                .map(str::trim)
                .filter(|s| !s.is_empty()),
            "output_language": output_language
                .as_deref()
                .map(str::trim)
                .filter(|s| !s.is_empty()),
        });

        call_sidecar_streaming(&app, "find_highlights", payload, &on_event)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[tauri::command]
pub async fn list_ai_models(app: tauri::AppHandle, api_key: String, base_url: String) -> Result<Vec<String>, String> {
    if api_key.trim().is_empty() {
        return Err("API key is required".to_string());
    }

    tauri::async_runtime::spawn_blocking(move || {
        let payload = serde_json::json!({
            "api_key": api_key,
            "base_url": base_url,
        });

        let result_value = call_sidecar(&app, "list_ai_models", payload)?;
        serde_json::from_value::<Vec<String>>(result_value)
            .map_err(|e| format!("Failed to parse model list: {e}"))
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[tauri::command]
pub async fn get_available_subtitles(app: tauri::AppHandle, url: String) -> Result<SubtitleListResponse, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let cookies_path = cookies_dir(&app)?.join("cookies.txt");
        let cookies_status = read_cookies_status_for_path(cookies_path.clone())?;

        if !cookies_status.valid {
            return Ok(SubtitleListResponse {
                subtitles: vec![],
                automatic_captions: vec![],
                caption_orig_code: None,
                error: cookies_status.error,
            });
        }

        let payload = serde_json::json!({
            "url": url,
            "cookies_path": cookies_path.to_string_lossy(),
        });

        let result_value = call_sidecar(&app, "get_subtitles", payload)?;

        serde_json::from_value::<SubtitleListResponse>(result_value)
            .map_err(|e| format!("Failed to parse subtitle result: {e}"))
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

fn cookies_dir(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map_err(|e| format!("Failed to resolve app data directory: {e}"))
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionSummary {
    /// The session folder's name (e.g. 20261126_123301): stable, and what
    /// clips point back to.
    id: String,
    session_dir: String,
    url: String,
    title: String,
    channel: String,
    highlight_count: usize,
    /// Clips on disk with a finished video, counted from the folder rather
    /// than trusted from session_data.json.
    rendered_count: usize,
    status: String,
    created_at: String,
}

/// One finished clip, read from clips/clip_NNN/data.json next to its video.
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ClipSummary {
    session_id: String,
    session_dir: String,
    session_title: String,
    channel: String,
    url: String,
    highlight_index: i64,
    clip_path: String,
    title: String,
    hook_text: String,
    description: String,
    start_time: String,
    end_time: String,
    duration_seconds: f64,
    reframe_mode: String,
    processed_at: String,
}

/// Finished clip folders in a session, oldest highlight first.
fn finished_clip_dirs(session_path: &std::path::Path) -> Vec<PathBuf> {
    let clips = session_path.join("clips");
    let Ok(entries) = fs::read_dir(&clips) else {
        return vec![];
    };
    let mut dirs: Vec<PathBuf> = entries
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.is_dir() && p.join("master.mp4").exists())
        .collect();
    dirs.sort();
    dirs
}

fn sessions_dir(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    Ok(cookies_dir(app)?.join("output").join("sessions"))
}

#[tauri::command]
pub fn list_sessions(app: tauri::AppHandle) -> Result<Vec<SessionSummary>, String> {
    let dir = sessions_dir(&app)?;
    if !dir.exists() {
        return Ok(vec![]);
    }

    let mut summaries: Vec<SessionSummary> = Vec::new();

    let entries = fs::read_dir(&dir).map_err(|e| format!("Failed to read sessions dir: {e}"))?;
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let data_file = path.join("session_data.json");
        if !data_file.exists() {
            continue;
        }

        let content = match fs::read_to_string(&data_file) {
            Ok(c) => c,
            Err(_) => continue,
        };
        let value: serde_json::Value = match serde_json::from_str(&content) {
            Ok(v) => v,
            Err(_) => continue,
        };

        let video_info = value.get("video_info").cloned().unwrap_or_default();
        let highlights = value.get("highlights").and_then(|h| h.as_array());

        summaries.push(SessionSummary {
            id: entry.file_name().to_string_lossy().to_string(),
            rendered_count: finished_clip_dirs(&path).len(),
            session_dir: value
                .get("session_dir")
                .and_then(|v| v.as_str())
                .unwrap_or_else(|| path.to_str().unwrap_or(""))
                .to_string(),
            url: value
                .get("url")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            title: video_info
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("Untitled")
                .to_string(),
            channel: video_info
                .get("channel")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            highlight_count: highlights.map(|h| h.len()).unwrap_or(0),
            status: value
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .to_string(),
            created_at: value
                .get("created_at")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
        });
    }

    // Newest first by created_at (ISO strings sort lexicographically)
    summaries.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(summaries)
}

/// Every finished clip across all sessions, newest first, each pointing back
/// to the session it came from.
#[tauri::command]
pub fn list_clips(app: tauri::AppHandle) -> Result<Vec<ClipSummary>, String> {
    let dir = sessions_dir(&app)?;
    if !dir.exists() {
        return Ok(vec![]);
    }
    let str_of = |v: &serde_json::Value, key: &str| v.get(key).and_then(|x| x.as_str()).unwrap_or("").to_string();

    let mut clips: Vec<ClipSummary> = Vec::new();
    let entries = fs::read_dir(&dir).map_err(|e| format!("Failed to read sessions dir: {e}"))?;
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let clip_dirs = finished_clip_dirs(&path);
        if clip_dirs.is_empty() {
            continue;
        }
        let session: serde_json::Value = fs::read_to_string(path.join("session_data.json"))
            .ok()
            .and_then(|c| serde_json::from_str(&c).ok())
            .unwrap_or_default();
        let video_info = session.get("video_info").cloned().unwrap_or_default();
        let session_id = entry.file_name().to_string_lossy().to_string();

        for clip_dir in clip_dirs {
            let data: serde_json::Value = fs::read_to_string(clip_dir.join("data.json"))
                .ok()
                .and_then(|c| serde_json::from_str(&c).ok())
                .unwrap_or_default();
            // Older clips have no data.json; the folder name still gives the index.
            let index_from_name = clip_dir
                .file_name()
                .and_then(|n| n.to_str())
                .and_then(|n| n.strip_prefix("clip_"))
                .and_then(|n| n.parse::<i64>().ok())
                .unwrap_or(-1);
            let description = {
                let d = str_of(&data, "youtube_description");
                if d.is_empty() { str_of(&data, "description") } else { d }
            };
            clips.push(ClipSummary {
                session_id: session_id.clone(),
                session_dir: path.to_string_lossy().to_string(),
                session_title: video_info.get("title").and_then(|v| v.as_str()).unwrap_or("Untitled").to_string(),
                channel: str_of(&video_info, "channel"),
                url: str_of(&session, "url"),
                highlight_index: data.get("highlight_index").and_then(|v| v.as_i64()).unwrap_or(index_from_name),
                clip_path: clip_dir.join("master.mp4").to_string_lossy().to_string(),
                title: str_of(&data, "title"),
                hook_text: str_of(&data, "hook_text"),
                description,
                start_time: str_of(&data, "start_time"),
                end_time: str_of(&data, "end_time"),
                duration_seconds: data.get("duration_seconds").and_then(|v| v.as_f64()).unwrap_or(0.0),
                reframe_mode: str_of(&data, "reframe_mode"),
                processed_at: str_of(&data, "processed_at"),
            });
        }
    }

    // Newest first; ISO timestamps sort as strings. Ties keep highlight order.
    clips.sort_by(|a, b| {
        b.processed_at
            .cmp(&a.processed_at)
            .then_with(|| b.session_id.cmp(&a.session_id))
            .then_with(|| a.highlight_index.cmp(&b.highlight_index))
    });
    Ok(clips)
}

#[tauri::command]
pub fn load_session(session_dir: String) -> Result<serde_json::Value, String> {
    let data_file = PathBuf::from(&session_dir).join("session_data.json");
    if !data_file.exists() {
        return Err("Session data not found".to_string());
    }
    let content =
        fs::read_to_string(&data_file).map_err(|e| format!("Failed to read session: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Failed to parse session: {e}"))
}

/// Replace the highlights in a session's session_data.json, keeping every other
/// field. The highlight editor uses this to persist trimmed start/end times.
#[tauri::command]
pub fn save_session_highlights(
    session_dir: String,
    highlights: serde_json::Value,
) -> Result<(), String> {
    if !highlights.is_array() {
        return Err("highlights must be an array".to_string());
    }
    let data_file = PathBuf::from(&session_dir).join("session_data.json");
    if !data_file.exists() {
        return Err("Session data not found".to_string());
    }
    let content =
        fs::read_to_string(&data_file).map_err(|e| format!("Failed to read session: {e}"))?;
    let mut data: serde_json::Value =
        serde_json::from_str(&content).map_err(|e| format!("Failed to parse session: {e}"))?;
    let obj = data
        .as_object_mut()
        .ok_or("Session data is not an object")?;
    obj.insert("highlights".to_string(), highlights);

    let serialized = serde_json::to_string_pretty(&data)
        .map_err(|e| format!("Failed to serialize session: {e}"))?;
    // Write to a sibling temp file first so a crash mid-write cannot truncate
    // the session.
    let tmp_file = data_file.with_extension("json.tmp");
    fs::write(&tmp_file, serialized).map_err(|e| format!("Failed to write session: {e}"))?;
    fs::rename(&tmp_file, &data_file).map_err(|e| format!("Failed to save session: {e}"))
}

#[tauri::command]
pub fn delete_session(session_dir: String) -> Result<(), String> {
    let path = PathBuf::from(&session_dir);
    if !path.exists() {
        return Ok(());
    }
    // Safety: only allow deleting a directory that contains session_data.json
    if !path.join("session_data.json").exists() {
        return Err("Refusing to delete: not a session directory".to_string());
    }
    fs::remove_dir_all(&path).map_err(|e| format!("Failed to delete session: {e}"))
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SavedWatermark {
    path: String,
    data_url: String,
}

#[tauri::command]
pub fn save_watermark(
    app: tauri::AppHandle,
    file_name: String,
    bytes: Vec<u8>,
) -> Result<SavedWatermark, String> {
    let watermarks_dir = cookies_dir(&app)?.join("watermarks");
    fs::create_dir_all(&watermarks_dir)
        .map_err(|e| format!("Failed to create watermarks directory: {e}"))?;

    // Sanitize filename to its file name component only
    let safe_name = PathBuf::from(&file_name)
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "watermark.png".to_string());

    let dest = watermarks_dir.join(&safe_name);
    fs::write(&dest, &bytes).map_err(|e| format!("Failed to save watermark: {e}"))?;

    let data_url = bytes_to_data_url(&safe_name, &bytes);

    Ok(SavedWatermark {
        path: dest.to_string_lossy().to_string(),
        data_url,
    })
}

#[tauri::command]
pub fn read_watermark(path: String) -> Result<String, String> {
    let p = PathBuf::from(&path);
    if !p.exists() {
        return Err("Watermark file not found".to_string());
    }
    let bytes = fs::read(&p).map_err(|e| format!("Failed to read watermark: {e}"))?;
    let name = p
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    Ok(bytes_to_data_url(&name, &bytes))
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct HookFontInfo {
    name: String,
    path: String,
}

#[tauri::command]
pub fn list_hook_fonts(app: tauri::AppHandle) -> Result<Vec<HookFontInfo>, String> {
    // Try multiple strategies to find the fonts directory
    let mut candidates: Vec<PathBuf> = Vec::new();

    // 1. From manifest dir (dev)
    candidates.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fonts"));

    // 2. Relative to current executable (bundled)
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(exe_dir) = current_exe.parent() {
            candidates.push(exe_dir.join("fonts"));
            if let Some(parent) = exe_dir.parent() {
                candidates.push(parent.join("fonts"));
            }
        }
    }

    // 3. From app resources dir
    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("fonts"));
    }

    let fonts_dir = candidates.into_iter().find(|d| d.exists());

    if fonts_dir.is_none() {
        eprintln!("[DEBUG] No fonts dir found. Candidates: {:?}", {
            let mut c: Vec<PathBuf> = Vec::new();
            c.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fonts"));
            if let Ok(current_exe) = std::env::current_exe() {
                if let Some(exe_dir) = current_exe.parent() {
                    c.push(exe_dir.join("fonts"));
                }
            }
            if let Ok(resource_dir) = app.path().resource_dir() {
                c.push(resource_dir.join("fonts"));
            }
            c
        });
        return Ok(vec![]);
    }

    let fonts_dir = fonts_dir.unwrap();
    eprintln!("[DEBUG] Found fonts dir: {:?}", fonts_dir);

    let entries = fs::read_dir(&fonts_dir)
        .map_err(|e| { eprintln!("[DEBUG] read_dir error: {}", e); format!("Failed to read fonts dir: {e}") });

    let entries = match entries {
        Ok(e) => e,
        Err(err) => return Err(err),
    };

    eprintln!("[DEBUG] read_dir OK, iterating entries...");
    let mut items: Vec<(String, String)> = Vec::new();

    for entry in entries.flatten() {
        let path = entry.path();
        eprintln!("[DEBUG] Entry: {:?} is_file={}", path, path.is_file());
        if !path.is_file() {
            continue;
        }
        let ext = path
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase());
        eprintln!("[DEBUG] ext = {:?} bytes={:?}", ext, ext.as_ref().map(|s| s.as_bytes()));
        let is_valid = ext.as_ref().map(|e| e == "ttf" || e == "otf") == Some(true);
        if !is_valid {
            eprintln!("[DEBUG] SKIP: ext not valid");
            continue;
        }
        eprintln!("[DEBUG] ext PASSED");
        let stem = path.file_stem();
        eprintln!("[DEBUG] file_stem = {:?}", stem);
        let name = stem
            .and_then(|s| s.to_str())
            .map(|s| s.replace('_', " ").replace('-', " "))
            .filter(|s| !s.is_empty())
            .unwrap_or_default();
        eprintln!("[DEBUG] name = '{}'", name);
        if name.is_empty() {
            continue;
        }
        eprintln!("[DEBUG] Found font: {} -> {}", name, path.display());
        items.push((name, path.to_string_lossy().to_string()));
    }

    items.sort_by_key(|(name, _)| name.to_lowercase());

    Ok(items
        .into_iter()
        .map(|(name, path)| HookFontInfo { name, path })
        .collect())
}

#[tauri::command]
pub fn read_file_as_base64(path: String) -> Result<String, String> {
    let p = PathBuf::from(&path);
    if !p.exists() {
        return Err("File not found".to_string());
    }
    let bytes = fs::read(&p).map_err(|e| format!("Failed to read: {e}"))?;
    let encoded = base64_encode(&bytes);
    let ext = p.extension().and_then(|e| e.to_str()).map(|e| e.to_lowercase()).unwrap_or_default();
    let mime = if ext == "otf" { "font/otf" } else { "font/ttf" };
    Ok(format!("data:{mime};base64,{encoded}"))
}

fn bytes_to_data_url(file_name: &str, bytes: &[u8]) -> String {
    let mime = if file_name.to_lowercase().ends_with(".jpg")
        || file_name.to_lowercase().ends_with(".jpeg")
    {
        "image/jpeg"
    } else {
        "image/png"
    };
    let encoded = base64_encode(bytes);
    format!("data:{mime};base64,{encoded}")
}

fn base64_encode(data: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity((data.len() + 2) / 3 * 4);
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = if chunk.len() > 1 { chunk[1] as u32 } else { 0 };
        let b2 = if chunk.len() > 2 { chunk[2] as u32 } else { 0 };
        let n = (b0 << 16) | (b1 << 8) | b2;
        out.push(TABLE[((n >> 18) & 63) as usize] as char);
        out.push(TABLE[((n >> 12) & 63) as usize] as char);
        if chunk.len() > 1 {
            out.push(TABLE[((n >> 6) & 63) as usize] as char);
        } else {
            out.push('=');
        }
        if chunk.len() > 2 {
            out.push(TABLE[(n & 63) as usize] as char);
        } else {
            out.push('=');
        }
    }
    out
}

/// Mirrors `DEFAULT_CONFIG` in `src/hooks/appConfig.ts`.
///
/// Returned only when config.json does not exist yet. The frontend's
/// `mergeConfig` is the real source of truth — it layers whatever comes back
/// from here over its own defaults, so a key added there and forgotten here
/// still resolves. Keeping the two in step matters anyway: the first save
/// writes this shape to disk, and a drifting copy is how the old
/// `aiProviders` / `whisper-1` block survived long after it stopped meaning
/// anything.
fn default_app_config() -> serde_json::Value {
    serde_json::json!({
        "ai": {
            "source": "inapp",
            "custom": {
                "baseUrl": "https://ai-api.ytclip.org/v1",
                "apiKey": "",
                "model": ""
            },
            "inapp": { "model": "" },
            "systemMessage": ""
        },
        "account": { "keyBackupConfirmedAt": null },
        "gpuAcceleration": { "enabled": false },
        "watermark": {
            "enabled": false,
            "imagePath": "",
            "positionX": 0.85,
            "positionY": 0.05,
            "opacity": 0.8,
            "scale": 0.15
        },
        "creditWatermark": {
            "enabled": false,
            "text": "Source: {channel}",
            "color": "#FFFFFF",
            "fontSize": 24,
            "opacity": 0.7,
            "positionX": 0.03,
            "positionY": 0.92
        },
        "hookStyle": {
            "fontName": "Arial",
            "fontPath": "",
            "fontSize": 0.054,
            "fontColor": "#FFD700",
            "bgColor": "#FFFFFF",
            "cornerRadius": 0,
            "positionX": 0.5,
            "positionY": 0.333,
            "durationSeconds": 5
        },
        "clipPadding": {
            "leadIn": 1.5,
            "tailOut": 2.5
        },
        "repliz": {
            "accessKey": "",
            "secretKey": ""
        },
        "installationId": ""
    })
}

fn read_cookies_status_for_path(cookies_path: PathBuf) -> Result<CookiesStatus, String> {
    if !cookies_path.exists() {
        return Ok(CookiesStatus {
            exists: false,
            valid: false,
            path: cookies_path.to_string_lossy().to_string(),
            found_cookies: vec![],
            error: Some("cookies.txt not found".to_string()),
        });
    }

    let content = fs::read_to_string(&cookies_path)
        .map_err(|e| format!("Failed to read cookies.txt: {e}"))?;
    let found_cookies = find_auth_cookies(&content);
    let valid = !found_cookies.is_empty();

    Ok(CookiesStatus {
        exists: true,
        valid,
        path: cookies_path.to_string_lossy().to_string(),
        found_cookies,
        error: if valid {
            None
        } else {
            Some(
                "Invalid cookies.txt - missing YouTube authentication cookies. Please export fresh cookies while logged into YouTube."
                    .to_string(),
            )
        },
    })
}

fn find_auth_cookies(content: &str) -> Vec<String> {
    let mut found = Vec::new();

    for cookie in REQUIRED_COOKIES {
        if has_cookie(content, cookie) {
            found.push(cookie.to_string());
            continue;
        }

        for prefix in SECURE_COOKIE_PREFIXES {
            let secure_name = format!("{prefix}{cookie}");
            if has_cookie(content, &secure_name) {
                found.push(secure_name);
                break;
            }
        }
    }

    found
}

fn has_cookie(content: &str, cookie_name: &str) -> bool {
    content.contains(&format!("\t{cookie_name}\t")) || content.ends_with(&format!("\t{cookie_name}"))
}

fn call_sidecar(
    app: &tauri::AppHandle,
    command: &str,
    payload: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let request = serde_json::json!({
        "id": "tauri-request",
        "command": command,
        "payload": payload,
    });

    let mut child = spawn_sidecar(app)?;

    {
        let stdin = child
            .stdin
            .as_mut()
            .ok_or("Failed to open sidecar stdin")?;
        writeln!(stdin, "{}", request).map_err(|e| format!("Failed to write sidecar request: {e}"))?;
    }

    let output = child
        .wait_with_output()
        .map_err(|e| format!("Failed to read sidecar response: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    // The final response is the line that parses as a SidecarResponse (has "ok").
    // Streaming "event" log lines are ignored here.
    let response_line = stdout
        .lines()
        .filter(|line| !line.trim().is_empty())
        .rev()
        .find(|line| line.contains("\"ok\""))
        .ok_or_else(|| format!("Sidecar returned no response. stderr:\n{stderr}"))?;

    let response: SidecarResponse = serde_json::from_str(response_line).map_err(|e| {
        format!(
            "Failed to parse sidecar response: {e}\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}"
        )
    })?;

    if response.ok {
        response.result.ok_or("Sidecar response missing result".to_string())
    } else {
        Err(format!(
            "Sidecar error: {}\n\nstderr:\n{}",
            response.error.unwrap_or_else(|| "Unknown error".to_string()),
            stderr
        ))
    }
}

#[tauri::command]
pub async fn generate_social_title(
    app: tauri::AppHandle,
    title: String,
    hook_text: String,
    description: String,
    // Same shape the other AI calls take, so the in-app account resolves here
    // too instead of the renderer having to hand over a key.
    mut ai: serde_json::Value,
    // Lets the sidecar read the session's output language so the social post
    // matches the language the clip's own title and hook were written in.
    session_dir: Option<String>,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        account::resolve_ai(&mut ai)?;

        let payload = serde_json::json!({
            "title": title,
            "hook_text": hook_text,
            "description": description,
            "api_key": ai.get("api_key").and_then(|v| v.as_str()).unwrap_or_default(),
            "base_url": ai.get("base_url").and_then(|v| v.as_str()).unwrap_or_default(),
            "model": ai.get("model").and_then(|v| v.as_str()).unwrap_or_default(),
            "session_dir": session_dir,
        });

        call_sidecar(&app, "generate_social_title", payload)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[tauri::command]
pub async fn repliz_list_accounts(
    app: tauri::AppHandle,
    access_key: String,
    secret_key: String,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let payload = serde_json::json!({
            "access_key": access_key,
            "secret_key": secret_key,
        });
        call_sidecar(&app, "repliz_list_accounts", payload)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[tauri::command]
pub async fn repliz_upload(
    app: tauri::AppHandle,
    access_key: String,
    secret_key: String,
    video_path: String,
    title: String,
    description: String,
    account_ids: Vec<String>,
    schedule_at: Option<String>,
    on_event: Channel<ProcessClipsEvent>,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let payload = serde_json::json!({
            "access_key": access_key,
            "secret_key": secret_key,
            "video_path": video_path,
            "title": title,
            "description": description,
            "account_ids": account_ids,
            "schedule_at": schedule_at,
        });
        call_sidecar_streaming_process(&app, "repliz_upload", payload, &on_event)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[tauri::command]
pub fn open_path_in_explorer(path: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    if !p.exists() {
        return Err(format!("Path does not exist: {path}"));
    }
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        if p.is_dir() {
            Command::new("explorer")
                .arg(&path)
                .spawn()
                .map_err(|e| format!("Failed to open explorer: {e}"))?;
        } else {
            Command::new("explorer")
                .args(["/select,", &path])
                .spawn()
                .map_err(|e| format!("Failed to open explorer: {e}"))?;
        }
    }
    #[cfg(target_os = "macos")]
    {
        use std::process::Command;
        if p.is_dir() {
            Command::new("open")
                .arg(&path)
                .spawn()
                .map_err(|e| format!("Failed to open Finder: {e}"))?;
        } else {
            Command::new("open")
                .args(["-R", &path])
                .spawn()
                .map_err(|e| format!("Failed to open Finder: {e}"))?;
        }
    }
    #[cfg(target_os = "linux")]
    {
        use std::process::Command;
        Command::new("xdg-open")
            .arg(if p.is_dir() { &path } else { p.parent().unwrap().to_str().unwrap() })
            .spawn()
            .map_err(|e| format!("Failed to open file manager: {e}"))?;
    }
    Ok(())
}

#[tauri::command]
pub async fn process_clips(
    app: tauri::AppHandle,
    url: String,
    highlights: serde_json::Value,
    session_dir: String,
    options: serde_json::Value,
    mut ai: serde_json::Value,
    on_event: Channel<ProcessClipsEvent>,
) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        account::resolve_ai_with(&mut ai, |message| {
            let _ = on_event.send(ProcessClipsEvent::Log { message });
        })?;

        let cookies_path = cookies_dir(&app)?.join("cookies.txt");
        let cookies_status = read_cookies_status_for_path(cookies_path.clone())?;
        if !cookies_status.valid {
            return Err(cookies_status
                .error
                .unwrap_or_else(|| "Invalid cookies".to_string()));
        }

        let payload = serde_json::json!({
            "url": url,
            "highlights": highlights,
            "session_dir": session_dir,
            "options": options,
            "ai": ai,
        });

        call_sidecar_streaming_process(&app, "process_selected_highlights", payload, &on_event)
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
#[serde(tag = "type")]
pub enum ProcessClipsEvent {
    Log { message: String },
}

fn call_sidecar_streaming_process(
    app: &tauri::AppHandle,
    command: &str,
    payload: serde_json::Value,
    on_event: &Channel<ProcessClipsEvent>,
) -> Result<serde_json::Value, String> {
    let request = serde_json::json!({
        "id": "tauri-request",
        "command": command,
        "payload": payload,
    });

    let mut child = spawn_sidecar(app)?;

    {
        let mut stdin = child
            .stdin
            .take()
            .ok_or("Failed to open sidecar stdin")?;
        writeln!(stdin, "{}", request)
            .map_err(|e| format!("Failed to write sidecar request: {e}"))?;
    }

    let stdout = child.stdout.take().ok_or("Failed to open sidecar stdout")?;
    let reader = BufReader::new(stdout);

    let mut final_response: Option<SidecarResponse> = None;

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let value: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(_) => continue,
        };

        if value.get("event").and_then(|e| e.as_str()) == Some("log") {
            if let Some(message) = value.get("message").and_then(|m| m.as_str()) {
                let _ = on_event.send(ProcessClipsEvent::Log {
                    message: message.to_string(),
                });
            }
            continue;
        }

        if value.get("ok").is_some() {
            final_response = serde_json::from_value(value).ok();
            break;
        }
    }

    let mut stderr = String::new();
    if let Some(mut err_pipe) = child.stderr.take() {
        use std::io::Read;
        let _ = err_pipe.read_to_string(&mut stderr);
    }
    let _ = child.kill();
    let _ = child.wait();

    let response =
        final_response.ok_or_else(|| format!("Sidecar returned no response. stderr:\n{stderr}"))?;

    if response.ok {
        response
            .result
            .ok_or("Sidecar response missing result".to_string())
    } else {
        Err(format!(
            "Sidecar error: {}\n\nstderr:\n{}",
            response.error.unwrap_or_else(|| "Unknown error".to_string()),
            stderr
        ))
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
#[serde(tag = "type")]
pub enum ProxyEvent {
    Log { message: String },
    Progress { percent: f64 },
}

/// Download a low-resolution copy of the whole source video into the session
/// folder, so the highlight editor can play and scrub it before anything is
/// rendered. Returns the proxy's absolute path. Reuses an existing proxy.
#[tauri::command]
pub async fn download_proxy(
    app: tauri::AppHandle,
    url: String,
    session_dir: String,
    on_event: Channel<ProxyEvent>,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        if !PathBuf::from(&session_dir).join("session_data.json").exists() {
            return Err("Not a session directory".to_string());
        }

        let cookies_path = cookies_dir(&app)?.join("cookies.txt");
        let cookies_status = read_cookies_status_for_path(cookies_path.clone())?;
        if !cookies_status.valid {
            return Err(cookies_status
                .error
                .unwrap_or_else(|| "Invalid cookies".to_string()));
        }

        let payload = serde_json::json!({
            "url": url,
            "session_dir": session_dir,
            "cookies_path": cookies_path.to_string_lossy(),
        });

        let result = call_sidecar_streaming_proxy(&app, "download_proxy", payload, &on_event)?;
        result
            .get("path")
            .and_then(|p| p.as_str())
            .map(|p| p.to_string())
            .ok_or_else(|| "Sidecar did not return a proxy path".to_string())
    })
    .await
    .map_err(|e| format!("Task failed: {e}"))?
}

fn call_sidecar_streaming_proxy(
    app: &tauri::AppHandle,
    command: &str,
    payload: serde_json::Value,
    on_event: &Channel<ProxyEvent>,
) -> Result<serde_json::Value, String> {
    let request = serde_json::json!({
        "id": "tauri-request",
        "command": command,
        "payload": payload,
    });

    let mut child = spawn_sidecar(app)?;

    // Drop stdin after the request so the sidecar's stdin loop ends.
    {
        let mut stdin = child
            .stdin
            .take()
            .ok_or("Failed to open sidecar stdin")?;
        writeln!(stdin, "{}", request)
            .map_err(|e| format!("Failed to write sidecar request: {e}"))?;
    }

    let stdout = child.stdout.take().ok_or("Failed to open sidecar stdout")?;
    let reader = BufReader::new(stdout);

    let mut final_response: Option<SidecarResponse> = None;

    for line in reader.lines() {
        let Ok(line) = line else { continue };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let Ok(value) = serde_json::from_str::<serde_json::Value>(trimmed) else {
            continue;
        };

        match value.get("event").and_then(|e| e.as_str()) {
            Some("log") => {
                if let Some(message) = value.get("message").and_then(|m| m.as_str()) {
                    let _ = on_event.send(ProxyEvent::Log {
                        message: message.to_string(),
                    });
                }
                continue;
            }
            Some("progress") => {
                if let Some(percent) = value.get("percent").and_then(|p| p.as_f64()) {
                    let _ = on_event.send(ProxyEvent::Progress { percent });
                }
                continue;
            }
            _ => {}
        }

        if value.get("ok").is_some() {
            final_response = serde_json::from_value(value).ok();
            break;
        }
    }

    let mut stderr = String::new();
    if let Some(mut err_pipe) = child.stderr.take() {
        use std::io::Read;
        let _ = err_pipe.read_to_string(&mut stderr);
    }
    let _ = child.kill();
    let _ = child.wait();

    let response =
        final_response.ok_or_else(|| format!("Sidecar returned no response. stderr:\n{stderr}"))?;

    if response.ok {
        response
            .result
            .ok_or("Sidecar response missing result".to_string())
    } else {
        Err(format!(
            "Sidecar error: {}\n\nstderr:\n{}",
            response.error.unwrap_or_else(|| "Unknown error".to_string()),
            stderr
        ))
    }
}

fn call_sidecar_streaming(
    app: &tauri::AppHandle,
    command: &str,
    payload: serde_json::Value,
    on_event: &Channel<FindHighlightsEvent>,
) -> Result<serde_json::Value, String> {
    let request = serde_json::json!({
        "id": "tauri-request",
        "command": command,
        "payload": payload,
    });

    let mut child = spawn_sidecar(app)?;

    // Write the request, then DROP stdin so the sidecar's stdin loop ends.
    // Without this, the sidecar keeps waiting for more input and never exits,
    // so stdout never reaches EOF and we would block forever.
    {
        let mut stdin = child
            .stdin
            .take()
            .ok_or("Failed to open sidecar stdin")?;
        writeln!(stdin, "{}", request)
            .map_err(|e| format!("Failed to write sidecar request: {e}"))?;
        // stdin dropped here at end of scope
    }

    let stdout = child.stdout.take().ok_or("Failed to open sidecar stdout")?;
    let reader = BufReader::new(stdout);

    let mut final_response: Option<SidecarResponse> = None;

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let value: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(_) => continue,
        };

        if value.get("event").and_then(|e| e.as_str()) == Some("log") {
            if let Some(message) = value.get("message").and_then(|m| m.as_str()) {
                let _ = on_event.send(FindHighlightsEvent::Log {
                    message: message.to_string(),
                });
            }
            continue;
        }

        if value.get("ok").is_some() {
            final_response = serde_json::from_value(value).ok();
            // Final response received — stop reading immediately.
            break;
        }
    }

    // Read any stderr and ensure the process is reaped.
    let mut stderr = String::new();
    if let Some(mut err_pipe) = child.stderr.take() {
        use std::io::Read;
        let _ = err_pipe.read_to_string(&mut stderr);
    }
    let _ = child.kill();
    let _ = child.wait();

    let response =
        final_response.ok_or_else(|| format!("Sidecar returned no response. stderr:\n{stderr}"))?;

    if response.ok {
        response
            .result
            .ok_or("Sidecar response missing result".to_string())
    } else {
        Err(format!(
            "Sidecar error: {}\n\nstderr:\n{}",
            response.error.unwrap_or_else(|| "Unknown error".to_string()),
            stderr
        ))
    }
}

fn spawn_command(program: impl AsRef<std::ffi::OsStr>, args: &[&str]) -> Result<std::process::Child, std::io::Error> {
    let mut cmd = Command::new(program);
    cmd.args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW

    cmd.spawn()
}

fn spawn_sidecar(app: &tauri::AppHandle) -> Result<std::process::Child, String> {
    // Debug builds only: YTCLIP_SIDECAR_SOURCE=1 runs the Python sources
    // directly, so sidecar changes can be tried without a PyInstaller rebuild.
    let force_source = cfg!(debug_assertions) && std::env::var_os("YTCLIP_SIDECAR_SOURCE").is_some();
    if let Some(path) = resolve_sidecar_binary(app).filter(|_| !force_source) {
        return spawn_command(path, &[])
            .map_err(|e| format!("Failed to start bundled sidecar: {e}"));
    }

    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or("Failed to resolve project root")?
        .to_path_buf();

    let program = if cfg!(windows) { "py" } else { "python3" };
    let mut cmd = Command::new(program);
    cmd.arg("-m").arg("yt_short_clipper_core.sidecar");
    cmd.current_dir(project_root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW

    cmd.spawn()
        .map_err(|e| format!("Failed to start dev Python sidecar: {e}"))
}

fn resolve_sidecar_binary(app: &tauri::AppHandle) -> Option<PathBuf> {
    let mut candidates = Vec::new();

    let dev_binary = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("binaries")
        .join(SIDECAR_BINARY);
    candidates.push(dev_binary);

    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join(SIDECAR_BINARY));
        candidates.push(resource_dir.join("binaries").join(SIDECAR_BINARY));
        candidates.push(resource_dir.join(SIDECAR_BINARY_BARE));
        candidates.push(resource_dir.join("binaries").join(SIDECAR_BINARY_BARE));
    }

    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(exe_dir) = current_exe.parent() {
            candidates.push(exe_dir.join(SIDECAR_BINARY));
            candidates.push(exe_dir.join("resources").join(SIDECAR_BINARY));
            candidates.push(exe_dir.join("binaries").join(SIDECAR_BINARY));
            candidates.push(exe_dir.join(SIDECAR_BINARY_BARE));
            candidates.push(exe_dir.join("resources").join(SIDECAR_BINARY_BARE));
            candidates.push(exe_dir.join("binaries").join(SIDECAR_BINARY_BARE));
        }
    }

    candidates.into_iter().find(|path| path.exists())
}
