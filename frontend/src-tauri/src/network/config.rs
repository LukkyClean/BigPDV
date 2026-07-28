use serde::{Deserialize, Serialize};
use std::fs;
use std::net::TcpListener;
use tauri::AppHandle;
use tauri::Manager;

use super::discovery::EstadoDescoberta;

pub fn get_free_port() -> u16 {
    TcpListener::bind("0.0.0.0:0")
        .expect("Falha ao busca uma porta livre no sistema")
        .local_addr()
        .unwrap()
        .port()
}

fn is_port_available(port: u16) -> bool {
    TcpListener::bind(("0.0.0.0", port)).is_ok()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub is_server: bool,
    pub server_ip: String,
    pub server_port: u16,
    #[serde(default)]
    pub configured: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            is_server: false,
            server_ip: "0.0.0.0".to_string(),
            server_port: 8080,
            configured: false,
        }
    }
}

pub fn gen_network_config_txt(app: &AppHandle, ip: String, port: u16) {
    if let Ok(mut path) = app.path().desktop_dir() {
        path.push("StartBigERP-server-config.txt");

        let data_hora = chrono::Local::now().format("%d/%m/%Y %H:%M:%S");

        let content = format!(
            "=== INFORMAÇÕES DO SERVIDOR STARTBIG ERP ===\n\
            Gerado em: {}\n\n\
            O servidor central está rodando nesta máquina de forma ativa.\n\n\
            -> IP DA REDE: {}\n\
            -> PORTA DE CONEXÃO: {}\n\n\
            Para configurar os terminais clientes, insira exatamente o endereço abaixo:\n\
            Endereço completo: {}:{}\n\
            ============================================",
            data_hora, ip, port, ip, port
        );

        if let Err(e) = fs::write(&path, content) {
            eprintln!("Erro ao gerar o arquivo de configuração: {}", e);
        } else {
            println!("Arquivo de configuração gerado em: {}", path.display());
        }
    }
}

fn get_config_path(app: &AppHandle) -> std::path::PathBuf {
    let mut path = app
        .path()
        .app_data_dir()
        .expect("Não foi possível encontrar AppData");
    path.push("StartBigERP");
    fs::create_dir_all(&path).unwrap();
    path.push("system-config.json");
    path
}

pub fn load_config(app: &AppHandle) -> AppConfig {
    let path = get_config_path(app);

    if path.exists() {
        let content = fs::read_to_string(&path).unwrap();
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        let default = AppConfig::default();
        let json = serde_json::to_string_pretty(&default).unwrap();
        fs::write(&path, json).unwrap();
        default
    }
}

#[tauri::command]
pub fn set_role_server(
    app: AppHandle,
    custom_port: Option<u16>,
) -> Result<AppConfig, String> {
    let mut config = load_config(&app);
    config.is_server = true;
    config.server_ip = "0.0.0.0".to_string();
    config.configured = true;

    let setted_port = match custom_port {
        Some(port) => {
            if is_port_available(port) {
                port
            } else {
                return Err(format!(
                    "Porta {} já está em uso. Por favor, escolha outra porta.",
                    port
                ));
            }
        }
        None => {
            let fallbacks: [u16; 4] = [8080, 8081, 8082, 8083];
            match fallbacks.iter().find(|&&port| is_port_available(port)) {
                Some(oppend_port) => *oppend_port,
                None => get_free_port(),
            }
        }
    };

    config.server_port = setted_port;

    let path = get_config_path(&app);
    let json = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    fs::write(&path, json).map_err(|e| e.to_string())?;

    #[cfg(not(debug_assertions))]
    {
        match crate:: backend::install_backend_config(&config.server_ip, config.server_port) {
            Ok(()) => {
                crate::backend::ensure_backend(&app, &config.server_ip, config.server_port)
                    .map_err(|e| e.to_string())?;
            }
            Err(e) => {
                eprintln!(
                    "[backend] Instalação do serviço não concluída ({}). Usando sidecar de fallback.",
                    e
                );
                crate::backend::ensure_backend(&app, &config.server_ip, config.server_port)
                    .map_err(|e| e.to_string())?;
            }
        }
    }

    #[cfg(debug_assertions)]
    {
        crate::backend::ensure_backend(&app, &config.server_ip, config.server_port)
            .map_err(|e| e.to_string())?;
    }

    let ip_local = crate::impressao::obter_ip_local().unwrap_or_default();
    gen_network_config_txt(&app, ip_local.clone(), config.server_port);

    Ok(config)
}

#[tauri::command]
pub fn set_role_client(
    app: AppHandle,
    estado: tauri::State<'_, EstadoDescoberta>,
    server_ip: String,
    server_port: u16,
) -> Result<AppConfig, String> {
    let mut config = AppConfig::default();
    config.is_server = false;
    config.server_ip = server_ip;
    config.server_port = server_port;
    config.configured = true;

    let path = get_config_path(&app);
    let json = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    fs::write(&path, json).map_err(|e| e.to_string())?;

    super::discovery::discover_servers(&estado, app);

    Ok(config)
}

#[tauri::command]
pub fn get_config(app: AppHandle) -> AppConfig {
    load_config(&app)
}

#[tauri::command]
pub fn get_api_url(app: AppHandle) -> String {

    #[cfg(debug_assertions)] {
        return format!("http://127.0.0.1:8080/api")
    }

    #[cfg(not(debug_assertions))]
    {
        let config = load_config(&app);

        if config.is_server {
            return format!("http://127.0.0.1:{}/api", config.server_port);
        }

        format!("http://{}:{}/api", config.server_ip, config.server_port)
    }
}
