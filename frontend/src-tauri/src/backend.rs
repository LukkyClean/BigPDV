use std::sync::Mutex;

use std::time::Duration;
use ureq::config::Config;

use tauri::{AppHandle, Manager};
use tauri_plugin_shell::{ShellExt, process::CommandChild};

pub enum BackendMode {
    Nothing,
    ExternalProcessRunning,
    ManagementProcessRuning(CommandChild),
}

pub struct AppState {
    pub mode: Mutex<BackendMode>,
}

pub fn check_backend_health(port: u16) -> bool {
    // O endpoint e /api/health (app/main.py), nao /health. Enquanto isto apontou
    // para /health o probe recebia 404 e devolvia `false` SEMPRE: o app nunca
    // reconhecia o backend no ar, tentava subir um sidecar que morria com a porta
    // ocupada, e `install_backend_config` sempre falhava o await_backend_health.
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

pub fn await_backend_health(port: u16, repeat: u32) -> bool {
    for retry in 1..repeat {
        if check_backend_health(port) {
            println!("[backend] Encontrado na tentativa {}/{}", retry, repeat);
            return true;
        }

        std::thread::sleep(Duration::from_secs(1));
    }
    false
}

fn kill_process(process: CommandChild) {
    let pid = process.pid();

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;

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

pub fn ensure_backend(
    app_handle: &AppHandle,
    ip_address: &str,
    port: u16,
) -> Result<(), Box<dyn std::error::Error>> {
    let state = app_handle.state::<AppState>();
    let mut mode_guard = state.mode.lock().unwrap();

    if check_backend_health(port) {
        println!(
            "[backend] Backend já está rodando na porta {}. Nenhuma ação necessária.",
            port
        );

        if let BackendMode::ManagementProcessRuning(process) = std::mem::replace(&mut *mode_guard, BackendMode::ExternalProcessRunning) {
                kill_process(process);
        }

        return Ok(());
    }

    println!("[backend] Nenhum backend respondeu na porta {} — iniciando sidecar de fallback.", port);

    if let BackendMode::ManagementProcessRuning(process) = std::mem::replace(&mut *mode_guard, BackendMode::Nothing) {
        kill_process(process);
    }

    let sidecar_command = app_handle
        .shell()
        .sidecar("erp-api")?
        .env("APP_ENV", "production")
        .args([ip_address, &port.to_string()]);

    let (mut rx, child) = sidecar_command.spawn()?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                    println!("FastAPI [LOG]: {}", String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                    println!("FastAPI [ERR]: {}", String::from_utf8_lossy(&line));
                }
                _ => {} // ignora outros eventos (ex.: encerramento)
            }
        }
    });

    *mode_guard = BackendMode::ManagementProcessRuning(child);

    Ok(())
}

#[cfg(target_os = "windows")]
pub fn install_backend_config(host: &str, port: u16) -> Result<(), String> {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    let exe_path = std::env::current_exe().map_err(|e| format!("Falha ao obter o caminho do executável: {}", e))?;

    let dir = exe_path.parent().ok_or("Falha ao obter o diretório do executável")?;
    let erp_api_path = dir.join("erp-api.exe");

    if !erp_api_path.exists() {
        return Err(format!(
            "O arquivo erp-api.exe não foi encontrado no diretório: {}",
            dir.display()
        ));
    }

    let backend_args = format!("--install --host {} --port {}", host, port);
    let ps_commmand = format!(
        "Start-Process -FilePath '{}' -ArgumentList '{}' -Verb RunAs -Wait -WindowStyle Hidden",
        erp_api_path.display(),
        backend_args
    );

    println!("[backend] Solicitando elevação (UAC) para instalar o serviço...");

    let status = std::process::Command::new("powershell")
        .args(["-NoProfile", "-WindowStyle", "Hidden", "-Command", &ps_commmand])
        .creation_flags(CREATE_NO_WINDOW)
        .status()
        .map_err(|e| format!("Falha ao executar o comando do PowerShell: {}", e))?;

    if !status.success() {
        return Err("Instalação cancelada ou negada pelo usuário (UAC).".to_string());
    }

    if await_backend_health(port,20) {
        println!("[backend] Serviço instalado e respondendo na porta {}.", port);
        Ok(())
    } else {
        Err("Serviço instalado, mas o backend não respondeu ao health check.".to_string())
    }
}

#[cfg(not(target_os = "windows"))]
pub fn instalar_servico_elevado(_host: &str, _port: u16) -> Result<(), String> {
    Err("Instalação como serviço só é suportada no Windows.".to_string())
}

pub fn cleanup_on_exit(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<AppState>();

    if let Ok(mut mode_guard) = state.inner().mode.lock() {
        match std::mem::replace(&mut *mode_guard, BackendMode::Nothing) {
            BackendMode::ManagementProcessRuning(process) => {
                println!("[backend] Encerrando processo de backend gerenciado...");
                kill_process(process);
            }
            BackendMode::ExternalProcessRunning => {
                println!("[backend] Backend externo estava rodando. Nenhuma ação necessária.");
            }
            _ => {}
        }
    }
}

