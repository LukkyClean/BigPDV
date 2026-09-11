//! Ciclo de vida do backend local (`erp-api.exe`) na máquina servidora.
//!
//! Em produção o backend normalmente roda como tarefa agendada do Windows
//! (`StartBigServer`, conta SYSTEM, dispara no boot/logon). O sidecar gerenciado
//! por este módulo é só um *fallback* para quando a tarefa não existe ou não subiu.
//!
//! Regras que este módulo garante (ver plano "Conexão local servidor/terminal"):
//! - nunca competir com a tarefa pela porta: se ela está instalada, espera por ela;
//! - nunca subir um sidecar sem saber o `data_dir` — abriria outro banco, e o
//!   sintoma seria "o sistema não reconhece mais meu usuário e senha";
//! - um erro ao subir o sidecar nunca derruba o app: vira estado `Falhou` e a tela
//!   de "Serviço local não respondeu";
//! - sidecar que morre sozinho é religado com backoff.

use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::{process::CommandChild, process::CommandEvent, ShellExt};
use ureq::config::Config;

use crate::network::log_rede;

pub const NOME_TAREFA: &str = "StartBigServer";
pub const PORTAS_PADRAO: [u16; 4] = [8080, 8081, 8082, 8083];

/// Quanto tempo esperar a tarefa agendada subir antes de recorrer ao sidecar.
/// Boot + 30 s de atraso da tarefa + extração do onefile + migrations em HDD
/// passam fácil de 60 s; 90 s cobre o caso comum sem deixar o operador esperando
/// indefinidamente.
const ESPERA_TAREFA: Duration = Duration::from_secs(90);
const INTERVALO_SONDA: Duration = Duration::from_secs(2);
/// Aos 20 s tentamos um `schtasks /Run` sem elevação (funciona quando o usuário é
/// admin local; caso contrário falha em silêncio e seguimos esperando).
const MOMENTO_RUN_TAREFA: Duration = Duration::from_secs(20);
const MAX_RESPAWNS: u32 = 5;
const BACKOFF_RESPAWN_SEGUNDOS: [u64; 5] = [5, 10, 20, 40, 60];

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

pub enum BackendMode {
    Nothing,
    /// Backend responde e não é nosso (tarefa agendada ou processo externo).
    ExternalProcessRunning,
    /// Tarefa instalada; estamos esperando ela responder.
    WaitingForService { desde: Instant },
    /// Sidecar gerenciado por nós. `geracao` identifica o spawn — o loop de eventos
    /// de um filho que já foi substituído/morto de propósito ignora o próprio
    /// `Terminated`.
    ManagementProcessRuning { child: CommandChild, geracao: u64 },
    Failed(String),
}

pub struct AppState {
    pub mode: Mutex<BackendMode>,
    pub geracao: AtomicU64,
    pub respawns: AtomicU32,
}

impl Default for AppState {
    fn default() -> Self {
        AppState {
            mode: Mutex::new(BackendMode::Nothing),
            geracao: AtomicU64::new(0),
            respawns: AtomicU32::new(0),
        }
    }
}

/// Snapshot para o frontend (evento `backend-status` e command `status_backend`).
#[derive(Serialize, Clone, Debug)]
pub struct StatusBackend {
    /// `nenhum` | `externo` | `aguardando_tarefa` | `sidecar` | `falhou`
    pub modo: String,
    pub detalhe: Option<String>,
    pub porta: u16,
    pub saudavel: bool,
    pub tarefa_instalada: Option<bool>,
    pub data_dir: Option<String>,
    pub segundos_aguardando: Option<u64>,
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

pub fn check_backend_health(port: u16) -> bool {
    // O endpoint é /api/health (app/main.py), não /health. Enquanto isto apontou
    // para /health o probe recebia 404 e devolvia `false` SEMPRE.
    let url = format!("http://127.0.0.1:{}/api/health", port);

    let config = Config::builder()
        .timeout_global(Some(Duration::from_secs(2)))
        .build();

    let agent = config.new_agent();

    match agent.get(&url).call() {
        Ok(response) => response.status() == 200,
        Err(_) => false,
    }
}

pub fn await_backend_health(port: u16, tentativas: u32) -> bool {
    for tentativa in 1..=tentativas {
        if check_backend_health(port) {
            log_rede(&format!(
                "backend respondeu na porta {} (tentativa {}/{})",
                port, tentativa, tentativas
            ));
            return true;
        }
        std::thread::sleep(Duration::from_secs(1));
    }
    false
}

/// Primeira porta padrão em que um backend local responde.
pub fn porta_com_backend_local() -> Option<u16> {
    PORTAS_PADRAO.iter().copied().find(|p| check_backend_health(*p))
}

// ---------------------------------------------------------------------------
// Tarefa agendada
// ---------------------------------------------------------------------------

static TAREFA_CACHE: Mutex<Option<bool>> = Mutex::new(None);

#[cfg(target_os = "windows")]
fn schtasks(args: &[&str]) -> Option<std::process::Output> {
    use std::os::windows::process::CommandExt;
    std::process::Command::new("schtasks")
        .args(args)
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .ok()
}

#[cfg(not(target_os = "windows"))]
fn schtasks(_args: &[&str]) -> Option<std::process::Output> {
    None
}

/// Consulta o agendador. `None` = não foi possível consultar (não confundir com
/// "não existe").
pub fn consultar_tarefa() -> Option<bool> {
    let saida = schtasks(&["/Query", "/TN", NOME_TAREFA])?;
    Some(saida.status.success())
}

/// Versão cacheada por sessão; `forcar` refaz a consulta.
pub fn tarefa_instalada(forcar: bool) -> bool {
    let mut cache = TAREFA_CACHE.lock().unwrap();
    if !forcar {
        if let Some(v) = *cache {
            return v;
        }
    }
    let existe = consultar_tarefa().unwrap_or(false);
    *cache = Some(existe);
    existe
}

pub fn marcar_tarefa_instalada() {
    *TAREFA_CACHE.lock().unwrap() = Some(true);
}

/// `--data-dir` gravado nos argumentos da tarefa (instalações já existentes, feitas
/// antes de o config guardar o `data_dir`).
pub fn data_dir_da_tarefa() -> Option<String> {
    let saida = schtasks(&["/Query", "/TN", NOME_TAREFA, "/XML"])?;
    if !saida.status.success() {
        return None;
    }
    // A saída é XML "UTF-16" só no cabeçalho; os bytes vêm na codepage do console.
    let texto = String::from_utf8_lossy(&saida.stdout);
    extrair_data_dir(&texto)
}

fn extrair_data_dir(texto: &str) -> Option<String> {
    let texto = texto.replace("&quot;", "\"");
    let pos = texto.find("--data-dir")?;
    let resto = &texto[pos + "--data-dir".len()..];
    let resto = resto.trim_start();
    let valor = if let Some(sem_aspas) = resto.strip_prefix('"') {
        sem_aspas.split('"').next()?
    } else {
        resto
            .split(|c: char| c.is_whitespace() || c == '<')
            .next()?
    };
    let valor = valor.trim();
    if valor.is_empty() {
        None
    } else {
        Some(valor.to_string())
    }
}

/// `%LOCALAPPDATA%\StartBigERP\data` — o mesmo padrão de `app/core/config.py`
/// quando `BIGPDV_DATA_DIR` não está definido.
pub fn data_dir_padrao() -> Option<String> {
    let base = std::env::var("LOCALAPPDATA").ok()?;
    Some(format!("{}\\StartBigERP\\data", base.trim_end_matches('\\')))
}

/// Resolve o `data_dir` a usar para sidecar/instalação: config → tarefa → padrão.
pub fn resolver_data_dir(config_data_dir: Option<&str>, permitir_padrao: bool) -> Option<String> {
    if let Some(d) = config_data_dir.filter(|d| !d.trim().is_empty()) {
        return Some(d.to_string());
    }
    if let Some(d) = data_dir_da_tarefa() {
        return Some(d);
    }
    if permitir_padrao {
        return data_dir_padrao();
    }
    None
}

// ---------------------------------------------------------------------------
// Processo
// ---------------------------------------------------------------------------

fn kill_process(process: CommandChild) {
    let pid = process.pid();

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", &pid.to_string()])
            .creation_flags(CREATE_NO_WINDOW)
            .output();
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = process.kill();
    }
}

fn definir_modo(app: &AppHandle, novo: BackendMode) {
    let state = app.state::<AppState>();
    let anterior = {
        let mut guard = state.mode.lock().unwrap();
        std::mem::replace(&mut *guard, novo)
    };
    if let BackendMode::ManagementProcessRuning { child, .. } = anterior {
        kill_process(child);
    }
    emitir_status(app);
}

pub fn status_atual(app: &AppHandle) -> StatusBackend {
    let config = crate::network::load_config(app);
    let state = app.state::<AppState>();
    let guard = state.mode.lock().unwrap();
    let (modo, detalhe, segundos) = match &*guard {
        BackendMode::Nothing => ("nenhum", None, None),
        BackendMode::ExternalProcessRunning => ("externo", None, None),
        BackendMode::WaitingForService { desde } => {
            ("aguardando_tarefa", None, Some(desde.elapsed().as_secs()))
        }
        BackendMode::ManagementProcessRuning { .. } => ("sidecar", None, None),
        BackendMode::Failed(motivo) => ("falhou", Some(motivo.clone()), None),
    };
    drop(guard);

    StatusBackend {
        modo: modo.to_string(),
        detalhe,
        porta: config.server_port,
        saudavel: config.is_server && check_backend_health(config.server_port),
        tarefa_instalada: if config.servico_instalado {
            Some(true)
        } else {
            consultar_tarefa()
        },
        data_dir: config.data_dir.clone(),
        segundos_aguardando: segundos,
    }
}

fn emitir_status(app: &AppHandle) {
    let status = status_atual(app);
    let _ = app.emit("backend-status", &status);
}

/// Sobe o sidecar e registra o loop de eventos (logs + respawn em morte inesperada).
fn spawn_sidecar(app: &AppHandle, ip_address: &str, port: u16, data_dir: &str) -> Result<(), String> {
    let state = app.state::<AppState>();
    let geracao = state.geracao.fetch_add(1, Ordering::SeqCst) + 1;

    let comando = app
        .shell()
        .sidecar("erp-api")
        .map_err(|e| format!("sidecar erp-api indisponível: {}", e))?
        .env("APP_ENV", "production")
        .args([ip_address, &port.to_string(), "--data-dir", data_dir]);

    let (mut rx, child) = comando
        .spawn()
        .map_err(|e| format!("falha ao iniciar erp-api: {}", e))?;

    log_rede(&format!(
        "sidecar iniciado (geração {}) em {}:{} data_dir={}",
        geracao, ip_address, port, data_dir
    ));

    definir_modo(app, BackendMode::ManagementProcessRuning { child, geracao });

    let app_eventos = app.clone();
    let ip_eventos = ip_address.to_string();
    let data_dir_eventos = data_dir.to_string();

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("FastAPI [LOG]: {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    println!("FastAPI [ERR]: {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Terminated(payload) => {
                    tratar_termino(
                        &app_eventos,
                        geracao,
                        payload.code,
                        &ip_eventos,
                        port,
                        &data_dir_eventos,
                    );
                }
                _ => {}
            }
        }
    });

    Ok(())
}

/// Chamado quando o processo do sidecar termina. Se foi morte inesperada (a
/// geração ainda é a corrente), tenta religar com backoff.
fn tratar_termino(app: &AppHandle, geracao: u64, code: Option<i32>, ip: &str, port: u16, data_dir: &str) {
    let state = app.state::<AppState>();
    {
        let guard = state.mode.lock().unwrap();
        match &*guard {
            BackendMode::ManagementProcessRuning { geracao: atual, .. } if *atual == geracao => {}
            _ => return, // substituído ou encerrado de propósito
        }
    }

    log_rede(&format!(
        "sidecar (geração {}) terminou inesperadamente, código {:?}",
        geracao, code
    ));

    if check_backend_health(port) {
        // A tarefa agendada assumiu a porta — é o desfecho desejado.
        log_rede("outro backend respondeu na porta; assumindo processo externo");
        definir_modo(app, BackendMode::ExternalProcessRunning);
        return;
    }

    let tentativa = state.respawns.fetch_add(1, Ordering::SeqCst);
    if tentativa >= MAX_RESPAWNS {
        log_rede("limite de religadas do sidecar atingido");
        definir_modo(app, BackendMode::Failed("sidecar_encerrou_repetidamente".to_string()));
        return;
    }

    let indice = (tentativa as usize).min(BACKOFF_RESPAWN_SEGUNDOS.len() - 1);
    let espera = BACKOFF_RESPAWN_SEGUNDOS[indice];
    log_rede(&format!("religando sidecar em {} s (tentativa {})", espera, tentativa + 1));

    // Marca como "sem processo" para que `definir_modo` não tente matar um pid morto.
    {
        let mut guard = state.mode.lock().unwrap();
        *guard = BackendMode::Nothing;
    }

    let app = app.clone();
    let ip = ip.to_string();
    let data_dir = data_dir.to_string();
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_secs(espera));
        if check_backend_health(port) {
            definir_modo(&app, BackendMode::ExternalProcessRunning);
            return;
        }
        if let Err(e) = spawn_sidecar(&app, &ip, port, &data_dir) {
            log_rede(&format!("religada do sidecar falhou: {}", e));
            definir_modo(&app, BackendMode::Failed(e));
        }
    });
}

/// Garante um backend respondendo em `port`. Nunca bloqueia por mais que a sonda
/// inicial (2 s): a espera pela tarefa acontece em thread própria e o frontend
/// acompanha pelo evento `backend-status` e pelo `/api/health`.
pub fn ensure_backend(
    app_handle: &AppHandle,
    ip_address: &str,
    port: u16,
    data_dir: Option<&str>,
) -> Result<(), String> {
    if check_backend_health(port) {
        log_rede(&format!("backend já responde na porta {}; nenhuma ação necessária", port));
        definir_modo(app_handle, BackendMode::ExternalProcessRunning);
        return Ok(());
    }

    app_handle.state::<AppState>().respawns.store(0, Ordering::SeqCst);

    if tarefa_instalada(false) {
        log_rede(&format!(
            "tarefa {} instalada e porta {} sem resposta; aguardando até {} s",
            NOME_TAREFA,
            port,
            ESPERA_TAREFA.as_secs()
        ));
        definir_modo(app_handle, BackendMode::WaitingForService { desde: Instant::now() });

        let app = app_handle.clone();
        let ip = ip_address.to_string();
        let data_dir = data_dir.map(|d| d.to_string());
        std::thread::spawn(move || aguardar_tarefa(app, ip, port, data_dir));
        return Ok(());
    }

    log_rede(&format!("nenhuma tarefa instalada e porta {} sem resposta; subindo sidecar", port));
    let data_dir = resolver_data_dir(data_dir, true)
        .ok_or_else(|| "não foi possível determinar a pasta de dados".to_string())?;
    spawn_sidecar(app_handle, ip_address, port, &data_dir).map_err(|e| {
        definir_modo(app_handle, BackendMode::Failed(e.clone()));
        e
    })
}

fn aguardar_tarefa(app: AppHandle, ip: String, port: u16, data_dir: Option<String>) {
    let inicio = Instant::now();
    let mut tentou_run = false;

    while inicio.elapsed() < ESPERA_TAREFA {
        if check_backend_health(port) {
            log_rede(&format!("tarefa respondeu após {} s", inicio.elapsed().as_secs()));
            definir_modo(&app, BackendMode::ExternalProcessRunning);
            return;
        }

        if !tentou_run && inicio.elapsed() >= MOMENTO_RUN_TAREFA {
            tentou_run = true;
            match schtasks(&["/Run", "/TN", NOME_TAREFA]) {
                Some(s) if s.status.success() => log_rede("schtasks /Run aceito"),
                _ => log_rede("schtasks /Run sem elevação não foi aceito; seguindo a esperar"),
            }
        }

        emitir_status(&app);
        std::thread::sleep(INTERVALO_SONDA);
    }

    // Só sobe o fallback se souber o data_dir da tarefa; caso contrário abriria
    // outro banco (sintoma "não reconhece usuário e senha").
    match resolver_data_dir(data_dir.as_deref(), false) {
        Some(dir) => {
            log_rede("tarefa não respondeu; subindo sidecar de fallback com o mesmo data_dir");
            if let Err(e) = spawn_sidecar(&app, &ip, port, &dir) {
                log_rede(&format!("fallback falhou: {}", e));
                definir_modo(&app, BackendMode::Failed(e));
            }
        }
        None => {
            log_rede("tarefa não respondeu e data_dir é desconhecido; não subindo fallback");
            definir_modo(&app, BackendMode::Failed("servico_nao_subiu".to_string()));
        }
    }
}

// ---------------------------------------------------------------------------
// Instalação / reinício elevados
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
fn executar_elevado(exe: &str, argumentos: &str) -> Result<(), String> {
    use std::os::windows::process::CommandExt;

    // Aspas simples dentro de string PowerShell single-quoted escapam-se dobrando.
    let exe = exe.replace('\'', "''");
    let argumentos = argumentos.replace('\'', "''");
    let ps = format!(
        "Start-Process -FilePath '{}' -ArgumentList '{}' -Verb RunAs -Wait -WindowStyle Hidden",
        exe, argumentos
    );

    let status = std::process::Command::new("powershell")
        .args(["-NoProfile", "-WindowStyle", "Hidden", "-Command", &ps])
        .creation_flags(CREATE_NO_WINDOW)
        .status()
        .map_err(|e| format!("Falha ao executar o PowerShell: {}", e))?;

    if status.success() {
        Ok(())
    } else {
        Err("Operação cancelada ou negada pelo usuário (UAC).".to_string())
    }
}

#[cfg(not(target_os = "windows"))]
fn executar_elevado(_exe: &str, _argumentos: &str) -> Result<(), String> {
    Err("Só suportado no Windows.".to_string())
}

fn caminho_erp_api() -> Result<String, String> {
    let exe_path = std::env::current_exe()
        .map_err(|e| format!("Falha ao obter o caminho do executável: {}", e))?;
    let dir = exe_path
        .parent()
        .ok_or("Falha ao obter o diretório do executável")?;
    let erp_api = dir.join("erp-api.exe");
    if !erp_api.exists() {
        return Err(format!("O arquivo erp-api.exe não foi encontrado em {}", dir.display()));
    }
    Ok(erp_api.display().to_string())
}

/// `erp-api.exe --install` elevado: firewall + tarefa agendada com o `data_dir`
/// do usuário logado (e não o da conta que respondeu ao UAC).
pub fn install_backend_config(host: &str, port: u16, data_dir: &str) -> Result<(), String> {
    let erp_api = caminho_erp_api()?;
    let argumentos = format!("--install --host {} --port {} --data-dir \"{}\"", host, port, data_dir);

    log_rede("solicitando elevação (UAC) para instalar a tarefa do backend");
    executar_elevado(&erp_api, &argumentos)?;

    if await_backend_health(port, 20) {
        marcar_tarefa_instalada();
        log_rede(&format!("tarefa instalada e respondendo na porta {}", port));
        Ok(())
    } else {
        Err("Serviço instalado, mas o backend não respondeu ao health check.".to_string())
    }
}

/// Command: religa o backend local. Com tarefa instalada, pede `schtasks /Run`
/// elevado; senão (ou se ainda assim não responder) recorre ao sidecar.
#[tauri::command(async)]
pub fn reiniciar_backend_local(app: AppHandle) -> Result<StatusBackend, String> {
    let config = crate::network::load_config(&app);
    if !config.is_server {
        return Err("Esta máquina não está configurada como servidor.".to_string());
    }
    let port = config.server_port;

    if check_backend_health(port) {
        definir_modo(&app, BackendMode::ExternalProcessRunning);
        return Ok(status_atual(&app));
    }

    if tarefa_instalada(true) {
        log_rede("reinício solicitado: schtasks /Run elevado");
        if let Err(e) = executar_elevado("schtasks", &format!("/Run /TN {}", NOME_TAREFA)) {
            log_rede(&format!("schtasks /Run elevado falhou: {}", e));
        }
        if await_backend_health(port, 30) {
            definir_modo(&app, BackendMode::ExternalProcessRunning);
            return Ok(status_atual(&app));
        }
    }

    let data_dir = resolver_data_dir(config.data_dir.as_deref(), !tarefa_instalada(false))
        .ok_or_else(|| {
            "A pasta de dados do servidor é desconhecida; use \"Reparar serviço\".".to_string()
        })?;

    app.state::<AppState>().respawns.store(0, Ordering::SeqCst);
    spawn_sidecar(&app, "0.0.0.0", port, &data_dir).map_err(|e| {
        definir_modo(&app, BackendMode::Failed(e.clone()));
        e
    })?;

    await_backend_health(port, 30);
    Ok(status_atual(&app))
}

/// Command: reinstala a tarefa (aplica triggers/argumentos novos em instalações
/// antigas). Reaproveita `install_backend_config`.
#[tauri::command(async)]
pub fn reparar_servico_local(app: AppHandle) -> Result<StatusBackend, String> {
    let mut config = crate::network::load_config(&app);
    if !config.is_server {
        return Err("Esta máquina não está configurada como servidor.".to_string());
    }
    let data_dir = resolver_data_dir(config.data_dir.as_deref(), true)
        .ok_or_else(|| "não foi possível determinar a pasta de dados".to_string())?;

    install_backend_config("0.0.0.0", config.server_port, &data_dir)?;

    config.servico_instalado = true;
    config.data_dir = Some(data_dir);
    crate::network::salvar_config(&app, &config)?;
    definir_modo(&app, BackendMode::ExternalProcessRunning);
    Ok(status_atual(&app))
}

#[tauri::command(async)]
pub fn status_backend(app: AppHandle) -> StatusBackend {
    status_atual(&app)
}

pub fn cleanup_on_exit(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<AppState>();

    if let Ok(mut mode_guard) = state.inner().mode.lock() {
        match std::mem::replace(&mut *mode_guard, BackendMode::Nothing) {
            BackendMode::ManagementProcessRuning { child, .. } => {
                log_rede("encerrando sidecar gerenciado");
                kill_process(child);
            }
            BackendMode::ExternalProcessRunning => {
                log_rede("backend externo continua rodando");
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::extrair_data_dir;

    #[test]
    fn extrai_data_dir_com_aspas() {
        let xml = r#"<Arguments>--host 0.0.0.0 --port 8080 --data-dir "C:\Users\Loja\AppData\Local\StartBigERP\data"</Arguments>"#;
        assert_eq!(
            extrair_data_dir(xml).as_deref(),
            Some(r"C:\Users\Loja\AppData\Local\StartBigERP\data")
        );
    }

    #[test]
    fn extrai_data_dir_com_quot() {
        let xml = "<Arguments>--port 8080 --data-dir &quot;C:\\dados&quot;</Arguments>";
        assert_eq!(extrair_data_dir(xml).as_deref(), Some("C:\\dados"));
    }

    #[test]
    fn sem_data_dir() {
        assert_eq!(extrair_data_dir("<Arguments>--port 8080</Arguments>"), None);
    }
}
