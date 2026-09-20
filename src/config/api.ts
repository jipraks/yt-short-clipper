/**
 * The public device API — the endpoints the app calls at launch, without auth.
 *
 * Mirrors `API_BASE` in `src-tauri/src/commands/account.rs`, which serves the
 * authenticated half of the same API from Rust. Anything here is reachable by
 * an app too old to authenticate, which is the point: it has to be able to
 * learn that it is too old.
 */
export const PUBLIC_API_BASE = "https://api-v2.ytclip.org/api/public/v1";
