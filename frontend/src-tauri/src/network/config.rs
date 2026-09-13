//! Papel da máquina (servidor × terminal) e endereço do backend.
//!
//! O arquivo `system-config.json` é a única fonte para `get_api_url`. Como ele é
//! por usuário do Windows e já foi visto virar "terminal apontando para o próprio
//! IP de LAN" (auto-descoberta achando o próprio serviço), este módulo:
//! - grava de forma atômica e mantém um `.bak`;
//! - nunca troca silenciosamente um JSON inválido por padrão;
//! - corrige o papel no startup quando há evidência de que o backend é local
//!   (`resolver_papel_efetivo`), com regra conjuntiva para não converter um
//!   terminal de verdade;
//! - recusa gravar como terminal um IP que é desta máquina.

use serde::{Deserialize, Serialize};
use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use tauri::AppHandle;
use tauri::Manager;

use super::discovery::EstadoDescoberta;
use super::local_ip::{ip_e_desta_maquina, ip_lan_privado, ips_locais};
use super::log::log_rede;
use crate::backend::{
    check_backend_health, consultar_tarefa, porta_com_backend_local, resolver_data_dir,
    tarefa_instalada, PORTAS_PADRAO,
};

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
    /// `true` quando `erp-api.exe --install` concluiu nesta máquina.
    #[serde(default)]
    pub servico_instalado: bool,
    /// Pasta de dados usada pela tarefa agendada; o sidecar de fallback usa a mesma.
    #[serde(default)]
    pub data_dir: Option<String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            is_server: false,
            server_ip: "0.0.0.0".to_string(),
            server_port: 8080,
            configured: false,
            servico_instalado: false,
            data_dir: None,
        }
    }
}

const AVISO_IP_FIXO: &str = "IMPORTANTE: configure um IP fixo (ou reserva DHCP) para este computador\n\
    no roteador e desative a \"Inicialização Rápida\" do Windows. Sem isso o IP pode\n\
    mudar ao ligar a máquina e os terminais perdem o servidor.";

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
            Endereço completo: {}:{}\n\n\
            {}\n\
            ============================================",
            data_hora, ip, port, ip, port, AVISO_IP_FIXO
        );

        if let Err(e) = fs::write(&path, content) {
            eprintln!("Erro ao gerar o arquivo de configuração: {}", e);
        } else {
            println!("Arquivo de configuração gerado em: {}", path.display());
        }
    }
}

pub fn get_config_dir(app: &AppHandle) -> PathBuf {
    let mut path = app
        .path()
        .app_data_dir()
        .expect("Não foi possível encontrar AppData");
    path.push("StartBigERP");
    let _ = fs::create_dir_all(&path);
    path
}

fn get_config_path(app: &AppHandle) -> PathBuf {
    get_config_dir(app).join("system-config.json")
}

/// Grava de forma atômica (tmp + rename) preservando a versão anterior em `.bak`.
pub fn salvar_config(app: &AppHandle, config: &AppConfig) -> Result<(), String> {
    let path = get_config_path(app);
    let tmp = path.with_extension("json.tmp");
    let bak = path.with_extension("json.bak");

    let json = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    fs::write(&tmp, json).map_err(|e| format!("falha ao gravar config temporário: {}", e))?;

    if path.exists() {
        let _ = fs::copy(&path, &bak);
    }
    fs::rename(&tmp, &path).map_err(|e| format!("falha ao substituir config: {}", e))?;

    log_rede(&format!(
        "config salvo: is_server={} server_ip={} porta={} configured={} servico_instalado={} data_dir={:?}",
        config.is_server,
        config.server_ip,
        config.server_port,
        config.configured,
        config.servico_instalado,
        config.data_dir
    ));
    Ok(())
}

fn ler_config_de(path: &PathBuf) -> Option<AppConfig> {
    let conteudo = fs::read_to_string(path).ok()?;
    serde_json::from_str(&conteudo).ok()
}

pub fn load_config(app: &AppHandle) -> AppConfig {
    let path = get_config_path(app);

    if !path.exists() {
        let default = AppConfig::default();
        if let Err(e) = salvar_config(app, &default) {
            log_rede(&format!("não foi possível criar config padrão: {}", e));
        }
        return default;
    }

    if let Some(config) = ler_config_de(&path) {
        return config;
    }

    // JSON inválido: preserva o arquivo ruim para diagnóstico e tenta o backup.
    let carimbo = chrono::Local::now().format("%Y%m%d-%H%M%S");
    let corrompido = path.with_extension(format!("json.corrompido-{}", carimbo));
    let _ = fs::rename(&path, &corrompido);
    log_rede(&format!(
        "system-config.json inválido; movido para {}",
        corrompido.display()
    ));

    let bak = path.with_extension("json.bak");
    if let Some(config) = ler_config_de(&bak) {
        log_rede("config restaurado a partir do .bak");
        let _ = fs::copy(&bak, &path);
        return config;
    }

    log_rede("sem backup válido; usando config padrão (não configurado)");
    let default = AppConfig::default();
    let _ = salvar_config(app, &default);
    default
}

/// Aplica as correções de papel que dependem só de evidências locais. É chamada no
/// `setup` e por `get_api_url`, então precisa ser barata no caminho comum
/// (servidor já correto ou terminal apontando para IP de outra máquina).
///
/// Regra conjuntiva de propósito: um terminal cujo `server_ip` antigo foi
/// realocado pelo DHCP para ele mesmo passaria no teste "IP é meu"; só convertemos
/// quando também há backend/tarefa nesta máquina.
pub fn resolver_papel_efetivo(app: &AppHandle) -> AppConfig {
    let mut config = load_config(app);

    if config.configured && config.is_server {
        return config;
    }

    if config.configured && !config.is_server {
        if !ip_e_desta_maquina(&config.server_ip) {
            return config;
        }
        let backend_local = check_backend_health(config.server_port);
        let tarefa = backend_local || tarefa_instalada(false);
        if !tarefa {
            log_rede(&format!(
                "terminal aponta para IP desta máquina ({}) mas não há backend/tarefa local; mantendo papel",
                config.server_ip
            ));
            return config;
        }
        log_rede(&format!(
            "papel corrigido: terminal apontava para IP desta máquina ({}:{}) e o backend é local → servidor",
            config.server_ip, config.server_port
        ));
        config.is_server = true;
        config.server_ip = "0.0.0.0".to_string();
        config.servico_instalado = config.servico_instalado || tarefa_instalada(false);
        if config.data_dir.is_none() {
            config.data_dir = resolver_data_dir(None, false);
        }
        let _ = salvar_config(app, &config);
        return config;
    }

    // Não configurado: se há um backend local (ou a tarefa instalada), esta máquina é
    // o servidor — cobre 2º usuário do Windows e config perdido.
    let porta = porta_com_backend_local();
    let tarefa = tarefa_instalada(false);
    if porta.is_none() && !tarefa {
        return config;
    }
    let porta = porta.unwrap_or(config.server_port);
    log_rede(&format!(
        "auto-configurado como servidor (porta {}): backend local respondeu={} tarefa instalada={}",
        porta,
        porta_com_backend_local().is_some(),
        tarefa
    ));
    config.is_server = true;
    config.server_ip = "0.0.0.0".to_string();
    config.server_port = porta;
    config.configured = true;
    config.servico_instalado = tarefa;
    config.data_dir = resolver_data_dir(None, false);
    let _ = salvar_config(app, &config);
    config
}

/// Escolhe a porta do servidor. Se um backend desta máquina já responde em alguma
/// porta padrão, adota-a — antes, "8080 ocupada pela própria tarefa" fazia o app
/// gravar 8081 e sondar a porta errada toda manhã.
fn escolher_porta(custom_port: Option<u16>) -> Result<u16, String> {
    if let Some(port) = custom_port {
        if check_backend_health(port) || is_port_available(port) {
            return Ok(port);
        }
        return Err(format!(
            "Porta {} já está em uso por outro programa. Por favor, escolha outra porta.",
            port
        ));
    }

    if let Some(port) = porta_com_backend_local() {
        log_rede(&format!("backend local já responde na porta {}; adotando-a", port));
        return Ok(port);
    }

    Ok(PORTAS_PADRAO
        .iter()
        .copied()
        .find(|p| is_port_available(*p))
        .unwrap_or_else(get_free_port))
}

#[tauri::command(async)]
pub fn set_role_server(app: AppHandle, custom_port: Option<u16>) -> Result<AppConfig, String> {
    let mut config = load_config(&app);
    config.is_server = true;
    config.server_ip = "0.0.0.0".to_string();
    config.configured = true;
    config.server_port = escolher_porta(custom_port)?;

    let data_dir = resolver_data_dir(config.data_dir.as_deref(), true)
        .ok_or_else(|| "Não foi possível determinar a pasta de dados.".to_string())?;
    config.data_dir = Some(data_dir.clone());
    config.servico_instalado = config.servico_instalado || tarefa_instalada(true);

    salvar_config(&app, &config)?;

    #[cfg(not(debug_assertions))]
    {
        let ja_responde = check_backend_health(config.server_port);
        if !ja_responde && !config.servico_instalado {
            match crate::backend::install_backend_config(&config.server_ip, config.server_port, &data_dir) {
                Ok(()) => {
                    config.servico_instalado = true;
                    salvar_config(&app, &config)?;
                }
                Err(e) => log_rede(&format!(
                    "instalação do serviço não concluída ({}); usando sidecar de fallback",
                    e
                )),
            }
        }
    }

    crate::backend::ensure_backend(
        &app,
        &config.server_ip,
        config.server_port,
        config.data_dir.as_deref(),
    )?;

    let ip_local = ip_lan_privado()
        .map(|ip| ip.to_string())
        .unwrap_or_default();
    gen_network_config_txt(&app, ip_local, config.server_port);

    Ok(config)
}

/// Código estável que o frontend usa para oferecer "configurar como Servidor".
pub const ERRO_IP_LOCAL: &str = "IP_LOCAL";

#[tauri::command]
pub fn set_role_client(
    app: AppHandle,
    estado: tauri::State<'_, EstadoDescoberta>,
    server_ip: String,
    server_port: u16,
) -> Result<AppConfig, String> {
    if ip_e_desta_maquina(&server_ip) {
        log_rede(&format!(
            "recusado gravar terminal apontando para IP desta máquina ({})",
            server_ip
        ));
        return Err(format!(
            "{}: o endereço {} é deste computador. Configure-o como Servidor.",
            ERRO_IP_LOCAL, server_ip
        ));
    }

    let mut config = AppConfig::default();
    config.is_server = false;
    config.server_ip = server_ip;
    config.server_port = server_port;
    config.configured = true;

    salvar_config(&app, &config)?;

    super::discovery::discover_servers(&estado, app);

    Ok(config)
}

#[tauri::command]
pub fn get_config(app: AppHandle) -> AppConfig {
    load_config(&app)
}

#[tauri::command]
pub fn get_api_url(app: AppHandle) -> String {
    // DEV (build debug): porta dedicada 8000, separada da faixa da loja (8080-8083).
    // Rode o backend com `fastapi dev app/main.py` (padrão 8000). Não afeta o release.
    #[cfg(debug_assertions)]
    {
        let _ = &app;
        return "http://127.0.0.1:8000/api".to_string();
    }

    #[cfg(not(debug_assertions))]
    {
        let config = resolver_papel_efetivo(&app);

        if config.is_server || ip_e_desta_maquina(&config.server_ip) {
            return format!("http://127.0.0.1:{}/api", config.server_port);
        }

        format!("http://{}:{}/api", config.server_ip, config.server_port)
    }
}

/// Snapshot para o painel "Diagnóstico de conexão".
#[derive(Serialize, Debug)]
pub struct DiagnosticoRede {
    pub papel: String,
    pub api_url: String,
    pub server_ip: String,
    pub server_port: u16,
    pub configured: bool,
    pub ips_locais: Vec<String>,
    pub data_dir: Option<String>,
    pub tarefa_instalada: Option<bool>,
    pub backend_local_responde: bool,
    pub config_path: String,
    pub log_path: Option<String>,
    pub log_recente: String,
}

#[tauri::command(async)]
pub fn diagnostico_rede(app: AppHandle) -> DiagnosticoRede {
    let config = load_config(&app);
    let api_url = get_api_url(app.clone());
    DiagnosticoRede {
        papel: if !config.configured {
            "nao_configurado".to_string()
        } else if config.is_server {
            "servidor".to_string()
        } else {
            "terminal".to_string()
        },
        api_url,
        server_ip: config.server_ip.clone(),
        server_port: config.server_port,
        configured: config.configured,
        ips_locais: ips_locais().iter().map(|ip| ip.to_string()).collect(),
        data_dir: config.data_dir.clone(),
        tarefa_instalada: consultar_tarefa(),
        backend_local_responde: check_backend_health(config.server_port),
        config_path: get_config_path(&app).display().to_string(),
        log_path: super::log::caminho_log().map(|p| p.display().to_string()),
        log_recente: super::log::ler_log(80),
    }
}
