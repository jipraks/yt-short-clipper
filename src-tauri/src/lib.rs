mod commands;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::greet,
            commands::save_cookies,
            commands::get_cookies_status,
            commands::get_available_subtitles,
            commands::load_app_config,
            commands::save_app_config,
            commands::list_ai_models,
            commands::detect_gpu,
            commands::find_highlights,
            commands::list_sessions,
            commands::load_session,
            commands::delete_session,
            commands::save_watermark,
            commands::read_watermark,
            commands::list_hook_fonts,
            commands::read_file_as_base64,
            commands::process_clips,
            commands::open_path_in_explorer,
            commands::generate_social_title,
            commands::repliz_list_accounts,
            commands::repliz_upload
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
