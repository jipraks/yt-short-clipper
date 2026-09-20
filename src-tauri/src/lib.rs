mod commands;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
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
            commands::repliz_upload,
            commands::account::account_state,
            commands::account::account_register,
            commands::account::account_me,
            commands::account::account_export_token,
            commands::account::account_export_to_file,
            commands::account::account_restore,
            commands::account::account_forget,
            commands::account::account_fee_rate,
            commands::account::account_models,
            commands::account::account_topup_create,
            commands::account::account_topup_get,
            commands::account::account_topups,
            commands::account::account_usage,
            commands::account::account_app_info
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
