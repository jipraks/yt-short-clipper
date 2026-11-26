//! How config.json is kept on disk.
//!
//! - Secrets (Repliz keys, a custom AI API key) live in the OS credential
//!   store, not in the file. The frontend still sees one config object: they
//!   are taken out on save and put back on load.
//! - Saves are atomic: written to a temp file, flushed, then renamed over
//!   config.json, so a crash mid-save cannot leave half a file.
//! - The last good config is kept as config.backup.json. A config.json that
//!   no longer parses is set aside (never deleted) and the backup is used, so
//!   one bad write cannot reset every setting to defaults.
//! - The file carries a schemaVersion for future migrations.

use std::fs;
use std::io::Write;
use std::path::Path;

pub const SCHEMA_VERSION: u64 = 1;
const BACKUP_NAME: &str = "config.backup.json";
const TEMP_NAME: &str = "config.json.tmp";
const KEYRING_SERVICE: &str = "com.jipraks.ytshortclipper-v2";

/// Config fields that hold secrets, and the credential-store entry for each.
const SECRET_FIELDS: [(&[&str], &str); 3] = [
    (&["repliz", "accessKey"], "repliz-access-key"),
    (&["repliz", "secretKey"], "repliz-secret-key"),
    (&["ai", "custom", "apiKey"], "custom-ai-api-key"),
];

/// Where secrets are kept. The OS credential store in the app; a map in tests.
pub trait SecretStore {
    fn read(&self, name: &str) -> Result<Option<String>, String>;
    fn write(&self, name: &str, value: &str) -> Result<(), String>;
    fn delete(&self, name: &str) -> Result<(), String>;
}

/// Windows Credential Manager (or the platform's equivalent) via `keyring`.
pub struct OsSecretStore;

impl OsSecretStore {
    fn entry(name: &str) -> Result<keyring::Entry, String> {
        keyring::Entry::new(KEYRING_SERVICE, name).map_err(|e| format!("credential store: {e}"))
    }
}

impl SecretStore for OsSecretStore {
    fn read(&self, name: &str) -> Result<Option<String>, String> {
        match Self::entry(name)?.get_password() {
            Ok(v) if v.is_empty() => Ok(None),
            Ok(v) => Ok(Some(v)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(format!("credential store: {e}")),
        }
    }
    fn write(&self, name: &str, value: &str) -> Result<(), String> {
        Self::entry(name)?.set_password(value).map_err(|e| format!("credential store: {e}"))
    }
    fn delete(&self, name: &str) -> Result<(), String> {
        match Self::entry(name)?.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(format!("credential store: {e}")),
        }
    }
}

fn get_str<'a>(value: &'a serde_json::Value, path: &[&str]) -> Option<&'a str> {
    let mut cur = value;
    for key in path {
        cur = cur.get(*key)?;
    }
    cur.as_str()
}

fn set_str(value: &mut serde_json::Value, path: &[&str], text: &str) {
    let mut cur = value;
    for (i, key) in path.iter().enumerate() {
        let Some(obj) = cur.as_object_mut() else { return };
        if i == path.len() - 1 {
            obj.insert((*key).to_string(), serde_json::Value::String(text.to_string()));
            return;
        }
        cur = obj
            .entry((*key).to_string())
            .or_insert_with(|| serde_json::Value::Object(Default::default()));
    }
}

/// Move every non-empty secret in `config` into the store and blank it in the
/// copy that goes to disk. An empty field clears the stored secret. If the
/// store refuses a write, that secret stays in the file rather than being lost.
fn take_secrets(config: &mut serde_json::Value, store: &dyn SecretStore) {
    for (path, name) in SECRET_FIELDS {
        let Some(value) = get_str(config, path).map(str::to_string) else { continue };
        if value.is_empty() {
            if let Err(e) = store.delete(name) {
                eprintln!("[config] could not clear {name}: {e}");
            }
            continue;
        }
        match store.write(name, &value) {
            Ok(()) => set_str(config, path, ""),
            Err(e) => eprintln!("[config] kept {name} in config.json, credential store failed: {e}"),
        }
    }
}

/// Move secrets an older version left in the file into the store. Unlike
/// `take_secrets`, an empty field means "nothing to move", never "clear it":
/// in a current file every secret field is empty because the secret is in the
/// store, and clearing those would wipe them on the next schema bump.
fn move_plaintext_secrets(config: &mut serde_json::Value, store: &dyn SecretStore) {
    for (path, name) in SECRET_FIELDS {
        let Some(value) = get_str(config, path).map(str::to_string) else { continue };
        if value.is_empty() {
            continue;
        }
        match store.write(name, &value) {
            Ok(()) => set_str(config, path, ""),
            Err(e) => eprintln!("[config] kept {name} in config.json, credential store failed: {e}"),
        }
    }
}

/// Fill blank secret fields from the store, for the frontend.
fn put_secrets(config: &mut serde_json::Value, store: &dyn SecretStore) {
    for (path, name) in SECRET_FIELDS {
        let current = get_str(config, path).unwrap_or("");
        if !current.is_empty() {
            continue;
        }
        match store.read(name) {
            Ok(Some(secret)) => set_str(config, path, &secret),
            Ok(None) => {}
            Err(e) => eprintln!("[config] could not read {name}: {e}"),
        }
    }
}

fn has_plaintext_secret(config: &serde_json::Value) -> bool {
    SECRET_FIELDS
        .iter()
        .any(|(path, _)| get_str(config, path).is_some_and(|v| !v.is_empty()))
}

fn read_json(path: &Path) -> Option<serde_json::Value> {
    let text = fs::read_to_string(path).ok()?;
    let value: serde_json::Value = serde_json::from_str(&text).ok()?;
    value.is_object().then_some(value)
}

/// Write `value` to `path` via a temp file and a rename, keeping the file
/// being replaced as the backup when it is still valid.
fn write_atomic(dir: &Path, path: &Path, value: &serde_json::Value) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|e| format!("Failed to create app data directory: {e}"))?;
    let text = serde_json::to_string_pretty(value).map_err(|e| format!("Failed to serialize config: {e}"))?;

    let temp = dir.join(TEMP_NAME);
    {
        let mut file = fs::File::create(&temp).map_err(|e| format!("Failed to save config.json: {e}"))?;
        file.write_all(text.as_bytes()).map_err(|e| format!("Failed to save config.json: {e}"))?;
        file.sync_all().map_err(|e| format!("Failed to save config.json: {e}"))?;
    }

    if read_json(path).is_some() {
        if let Err(e) = fs::copy(path, dir.join(BACKUP_NAME)) {
            eprintln!("[config] could not refresh the backup: {e}");
        }
    }
    fs::rename(&temp, path).map_err(|e| format!("Failed to save config.json: {e}"))
}

/// Read the config: config.json, or the backup if config.json is unreadable,
/// or `defaults` on a first run. Plaintext secrets left by older versions are
/// moved to the store. Returns the config with secrets filled in.
pub fn load(dir: &Path, defaults: serde_json::Value, store: &dyn SecretStore) -> Result<serde_json::Value, String> {
    let path = dir.join("config.json");
    let mut config = if !path.exists() {
        defaults
    } else if let Some(config) = read_json(&path) {
        config
    } else {
        // Set the unreadable file aside so nothing overwrites it, then fall
        // back to the last good copy.
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let aside = dir.join(format!("config.corrupt-{stamp}.json"));
        if let Err(e) = fs::rename(&path, &aside) {
            return Err(format!("config.json is unreadable and could not be set aside: {e}"));
        }
        eprintln!("[config] config.json was unreadable; moved to {}", aside.display());
        match read_json(&dir.join(BACKUP_NAME)) {
            Some(backup) => {
                write_atomic(dir, &path, &backup)?;
                backup
            }
            None => defaults,
        }
    };

    let outdated = config.get("schemaVersion").and_then(|v| v.as_u64()).unwrap_or(0) < SCHEMA_VERSION;
    if path.exists() && (has_plaintext_secret(&config) || outdated) {
        // Older versions kept secrets in the file. Move them out now.
        let mut on_disk = config.clone();
        move_plaintext_secrets(&mut on_disk, store);
        stamp_version(&mut on_disk);
        write_atomic(dir, &path, &on_disk)?;
        config = on_disk;
    }

    put_secrets(&mut config, store);
    Ok(config)
}

/// Persist `config` from the frontend. Secrets go to the store; the rest is
/// written atomically. Returns `config` unchanged, secrets included.
pub fn save(dir: &Path, config: serde_json::Value, store: &dyn SecretStore) -> Result<serde_json::Value, String> {
    let mut on_disk = config.clone();
    take_secrets(&mut on_disk, store);
    stamp_version(&mut on_disk);
    write_atomic(dir, &dir.join("config.json"), &on_disk)?;
    Ok(config)
}

fn stamp_version(config: &mut serde_json::Value) {
    if let Some(obj) = config.as_object_mut() {
        obj.insert("schemaVersion".to_string(), serde_json::Value::from(SCHEMA_VERSION));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::cell::RefCell;
    use std::collections::HashMap;
    use std::path::PathBuf;

    #[derive(Default)]
    struct MemStore {
        map: RefCell<HashMap<String, String>>,
        fail_writes: bool,
    }
    impl SecretStore for MemStore {
        fn read(&self, name: &str) -> Result<Option<String>, String> {
            Ok(self.map.borrow().get(name).cloned())
        }
        fn write(&self, name: &str, value: &str) -> Result<(), String> {
            if self.fail_writes {
                return Err("locked".into());
            }
            self.map.borrow_mut().insert(name.into(), value.into());
            Ok(())
        }
        fn delete(&self, name: &str) -> Result<(), String> {
            self.map.borrow_mut().remove(name);
            Ok(())
        }
    }

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("cuplik-config-test-{tag}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn sample() -> serde_json::Value {
        json!({
            "language": "id",
            "repliz": { "accessKey": "AK", "secretKey": "SK" },
            "ai": { "source": "custom", "custom": { "apiKey": "sk-123", "baseUrl": "u", "model": "m" } }
        })
    }

    #[test]
    fn save_keeps_secrets_out_of_the_file_and_load_puts_them_back() {
        let dir = temp_dir("roundtrip");
        let store = MemStore::default();
        save(&dir, sample(), &store).unwrap();

        let text = fs::read_to_string(dir.join("config.json")).unwrap();
        assert!(!text.contains("SK") && !text.contains("sk-123") && !text.contains("\"AK\""), "{text}");
        assert!(text.contains("\"schemaVersion\": 1"));
        assert_eq!(store.read("repliz-secret-key").unwrap().as_deref(), Some("SK"));

        let loaded = load(&dir, json!({}), &store).unwrap();
        assert_eq!(loaded, {
            let mut v = sample();
            v["schemaVersion"] = json!(1);
            v
        });
    }

    #[test]
    fn clearing_a_secret_removes_it_from_the_store() {
        let dir = temp_dir("clear");
        let store = MemStore::default();
        save(&dir, sample(), &store).unwrap();
        let mut cleared = sample();
        cleared["repliz"]["secretKey"] = json!("");
        save(&dir, cleared, &store).unwrap();
        assert_eq!(store.read("repliz-secret-key").unwrap(), None);
        assert_eq!(store.read("repliz-access-key").unwrap().as_deref(), Some("AK"));
    }

    #[test]
    fn plaintext_secrets_from_an_older_version_are_migrated_on_load() {
        let dir = temp_dir("migrate");
        fs::write(dir.join("config.json"), serde_json::to_string(&sample()).unwrap()).unwrap();
        let store = MemStore::default();

        let loaded = load(&dir, json!({}), &store).unwrap();
        assert_eq!(loaded["repliz"]["secretKey"], json!("SK"));
        let text = fs::read_to_string(dir.join("config.json")).unwrap();
        assert!(!text.contains("SK") && !text.contains("sk-123"), "{text}");
        assert_eq!(store.read("custom-ai-api-key").unwrap().as_deref(), Some("sk-123"));
    }

    #[test]
    fn a_corrupt_file_is_set_aside_and_the_backup_is_used() {
        let dir = temp_dir("corrupt");
        let store = MemStore::default();
        save(&dir, sample(), &store).unwrap(); // first save: no backup yet
        let mut second = sample();
        second["language"] = json!("en");
        save(&dir, second, &store).unwrap(); // backup now holds language "id"

        fs::write(dir.join("config.json"), "{ half a fi").unwrap();
        let loaded = load(&dir, json!({ "language": null }), &store).unwrap();

        assert_eq!(loaded["language"], json!("id"), "falls back to the last good copy");
        assert_eq!(loaded["repliz"]["secretKey"], json!("SK"));
        let aside: Vec<_> = fs::read_dir(&dir)
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_name().to_string_lossy().starts_with("config.corrupt-"))
            .collect();
        assert_eq!(aside.len(), 1, "the broken file is kept, not deleted");
        assert!(read_json(&dir.join("config.json")).is_some(), "config.json is valid again");
    }

    #[test]
    fn a_corrupt_file_with_no_backup_falls_back_to_defaults_without_deleting_it() {
        let dir = temp_dir("corrupt-nobackup");
        fs::write(dir.join("config.json"), "not json").unwrap();
        let loaded = load(&dir, json!({ "language": null }), &MemStore::default()).unwrap();
        assert_eq!(loaded["language"], json!(null));
        assert!(fs::read_dir(&dir).unwrap().any(|e| e
            .unwrap()
            .file_name()
            .to_string_lossy()
            .starts_with("config.corrupt-")));
    }

    #[test]
    fn a_failing_credential_store_keeps_the_secret_in_the_file() {
        let dir = temp_dir("store-fails");
        let store = MemStore { fail_writes: true, ..Default::default() };
        save(&dir, sample(), &store).unwrap();
        let text = fs::read_to_string(dir.join("config.json")).unwrap();
        assert!(text.contains("SK"), "secret must not be lost when the store refuses it");
    }

    #[test]
    fn loading_an_outdated_file_never_clears_stored_secrets() {
        // A current file has blank secret fields because the secrets are in
        // the store. A schema bump must not read those blanks as "cleared".
        let dir = temp_dir("schema-bump");
        let store = MemStore::default();
        save(&dir, sample(), &store).unwrap();
        let mut on_disk = read_json(&dir.join("config.json")).unwrap();
        on_disk["schemaVersion"] = json!(0); // pretend it predates the current schema
        fs::write(dir.join("config.json"), serde_json::to_string(&on_disk).unwrap()).unwrap();

        let loaded = load(&dir, json!({}), &store).unwrap();
        assert_eq!(loaded["repliz"]["secretKey"], json!("SK"));
        assert_eq!(store.read("custom-ai-api-key").unwrap().as_deref(), Some("sk-123"));
        assert_eq!(read_json(&dir.join("config.json")).unwrap()["schemaVersion"], json!(1));
    }

    #[test]
    fn first_run_returns_defaults_and_writes_nothing() {
        let dir = temp_dir("first-run");
        let loaded = load(&dir, json!({ "language": null }), &MemStore::default()).unwrap();
        assert_eq!(loaded["language"], json!(null));
        assert!(!dir.join("config.json").exists());
    }
}
