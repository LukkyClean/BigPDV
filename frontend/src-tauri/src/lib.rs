mod backend;
mod hwid;
mod impressao;
mod network;

use tauri::{Manager, RunEvent};

use backend::{cleanup_on_exit, AppState};
use impressao::{
    descobrir_servidores_impressao, imprimir_raw, imprimir_rede, iniciar_servidor_impressao,
    listar_impressoras, obter_ip_local, parar_servidor_impressao, EstadoServidorImpressao,
};
use network::{
    get_api_url, get_config, iniciar_descoberta_servidores, parar_descoberta_servidores,
    set_role_client, set_role_server
};
use hwid::obter_hwid;

#[tauri::command]
fn is_dev_mode() -> bool {
    cfg!(debug_assertions)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            listar_impressoras,
            imprimir_raw,
            iniciar_servidor_impressao,
            parar_servidor_impressao,
            descobrir_servidores_impressao,
            obter_ip_local,
            imprimir_rede,
            set_role_server,
            set_role_client,
            get_api_url,
            obter_hwid,
            get_config,
            is_dev_mode,
            iniciar_descoberta_servidores,
            parar_descoberta_servidores,
        ])
        .setup(move |app| {
            app.manage(AppState {
                mode: std::sync::Mutex::new(backend::BackendMode::Nothing),
            });

            app.manage(EstadoServidorImpressao::default());

            app.manage(network::EstadoDescoberta::default());

            use crate::backend::ensure_backend;
            use network::{
                discover_servers, gen_network_config_txt, load_config
            };

            let handle = app.app_handle();

            let server_config = load_config(&handle);
            #[cfg(not(debug_assertions))]
            {
                if server_config.configured {
                    if server_config.is_server {
                        ensure_backend(
                            &handle,
                            &server_config.server_ip,
                            server_config.server_port,
                        )?;
                        gen_network_config_txt(
                            &handle,
                            obter_ip_local().unwrap_or_default(),
                            server_config.server_port,
                        );
                    } else {
                        discover_servers(&handle.state::<network::EstadoDescoberta>(), handle.clone());
                    }
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            cleanup_on_exit(app_handle);
        }
    });
}
