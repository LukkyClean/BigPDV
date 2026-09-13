mod backend;
mod hwid;
mod impressao;
mod network;

use tauri::{Manager, RunEvent};

use backend::{
    cleanup_on_exit, reiniciar_backend_local, reparar_servico_local, status_backend, AppState,
};
use hwid::obter_hwid;
use impressao::{
    descobrir_servidores_impressao, imprimir_raw, imprimir_rede, iniciar_servidor_impressao,
    listar_impressoras, obter_ip_local, parar_servidor_impressao, EstadoServidorImpressao,
};
use network::{
    diagnostico_rede, get_api_url, get_config, iniciar_descoberta_servidores,
    parar_descoberta_servidores, set_role_client, set_role_server,
};

#[tauri::command]
fn is_dev_mode() -> bool {
    cfg!(debug_assertions)
}

#[tauri::command]
fn ler_log_rede(max_linhas: Option<usize>) -> String {
    network::ler_log(max_linhas.unwrap_or(200))
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
            status_backend,
            reiniciar_backend_local,
            reparar_servico_local,
            diagnostico_rede,
            ler_log_rede,
        ])
        .setup(move |app| {
            app.manage(AppState::default());
            app.manage(EstadoServidorImpressao::default());
            app.manage(network::EstadoDescoberta::default());

            let handle = app.app_handle();

            network::iniciar_log(network::get_config_dir(handle));
            network::log_rede(&format!(
                "app iniciado (versão {}, debug={})",
                app.package_info().version,
                cfg!(debug_assertions)
            ));

            // Corrige papel/porta antes de qualquer decisão de rede. Ver
            // network::config::resolver_papel_efetivo.
            let server_config = network::resolver_papel_efetivo(handle);
            network::log_rede(&format!(
                "papel: configured={} is_server={} server_ip={} porta={}",
                server_config.configured,
                server_config.is_server,
                server_config.server_ip,
                server_config.server_port
            ));

            #[cfg(not(debug_assertions))]
            {
                use crate::backend::ensure_backend;
                use network::{discover_servers, gen_network_config_txt};

                if server_config.configured {
                    if server_config.is_server {
                        // Nunca propagar erro daqui: com `panic = "abort"` e sem console,
                        // um `?` fazia o app simplesmente não abrir quando o sidecar
                        // falhava ao iniciar. O estado "falhou" chega à tela de erro.
                        if let Err(e) = ensure_backend(
                            handle,
                            &server_config.server_ip,
                            server_config.server_port,
                            server_config.data_dir.as_deref(),
                        ) {
                            network::log_rede(&format!("ensure_backend falhou no setup: {}", e));
                        }
                        gen_network_config_txt(
                            handle,
                            network::ip_lan_privado()
                                .map(|ip| ip.to_string())
                                .unwrap_or_default(),
                            server_config.server_port,
                        );
                    } else {
                        discover_servers(
                            &handle.state::<network::EstadoDescoberta>(),
                            handle.clone(),
                        );
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
