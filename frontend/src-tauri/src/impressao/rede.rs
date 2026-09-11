use std::io::Read;
use std::net::{IpAddr, TcpStream, UdpSocket};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

const PORTA_DESCOBERTA: u16 = 9101;
const MENSAGEM_DESCOBERTA: &[u8] = b"STARTBIG_DISCOVER";
// Sonda anterior ao rename do produto. Continua sendo aceita ao escutar e enviada no
// broadcast para que um caixa ainda nao atualizado responda a descoberta de impressora.
// Pode sair quando todos os terminais estiverem na versao nova.
const MENSAGEM_DESCOBERTA_LEGADA: &[u8] = b"BIGPDV_DISCOVER";

#[derive(Default)]
pub struct EstadoServidorImpressao(pub(crate) Mutex<Option<Arc<AtomicBool>>>);

#[derive(serde::Serialize)]
pub struct ServidorDescoberto {
    nome: String,
    ip: String,
    porta: u16,
}

// IP LAN privado deste PC. Delegado a `network::local_ip` (enumera as interfaces
// com `if-addrs`) — o truque antigo de `connect(8.8.8.8)` falhava sem rota para a
// internet, exatamente o cenário de loja sem link.
fn ip_lan_privado() -> Option<IpAddr> {
    crate::network::ip_lan_privado().map(IpAddr::V4)
}

fn atender_conexao_impressao(
    mut conexao: TcpStream,
    nome_impressora: &str,
) -> Result<(), String> {
    conexao
        .set_read_timeout(Some(Duration::from_secs(10)))
        .map_err(|e| e.to_string())?;
    let mut dados: Vec<u8> = Vec::new();
    let mut buffer = [0u8; 4096];
    loop {
        match conexao.read(&mut buffer) {
            Ok(0) => break,
            Ok(n) => {
                dados.extend_from_slice(&buffer[..n]);
                if dados.len() > 1_000_000 {
                    return Err("Trabalho de impressão excede 1MB".into());
                }
            }
            Err(e) => return Err(e.to_string()),
        }
    }
    if dados.is_empty() {
        return Ok(());
    }
    let impressora = printers::get_printer_by_name(nome_impressora)
        .ok_or_else(|| format!("Impressora '{}' não encontrada", nome_impressora))?;
    impressora
        .print(&dados, printers::common::base::job::PrinterJobOptions::none())
        .map(|_| ())
        .map_err(|e| format!("{:?}", e))
}

#[tauri::command(async)]
pub fn iniciar_servidor_impressao(
    state: tauri::State<'_, EstadoServidorImpressao>,
    porta: u16,
    nome_impressora: String,
    nome_terminal: String,
) -> Result<(), String> {
    // Para o servidor anterior, se houver
    if let Some(flag) = state.0.lock().unwrap().take() {
        flag.store(false, Ordering::SeqCst);
    }

    let listener = std::net::TcpListener::bind(("0.0.0.0", porta))
        .map_err(|_| format!("Porta {} já está em uso neste PC", porta))?;
    listener.set_nonblocking(true).map_err(|e| e.to_string())?;

    let udp = UdpSocket::bind(("0.0.0.0", PORTA_DESCOBERTA))
        .map_err(|_| format!("Porta de descoberta {} já está em uso", PORTA_DESCOBERTA))?;
    udp.set_read_timeout(Some(Duration::from_millis(500)))
        .map_err(|e| e.to_string())?;

    let rodando = Arc::new(AtomicBool::new(true));
    *state.0.lock().unwrap() = Some(rodando.clone());

    // Thread TCP: recebe os bytes e imprime
    {
        let rodando = rodando.clone();
        let nome_impressora = nome_impressora.clone();
        std::thread::spawn(move || {
            while rodando.load(Ordering::SeqCst) {
                match listener.accept() {
                    Ok((conexao, _origem)) => {
                        if let Err(e) = atender_conexao_impressao(conexao, &nome_impressora) {
                            eprintln!("[servidor-impressao] erro ao imprimir: {}", e);
                        }
                    }
                    Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                        std::thread::sleep(Duration::from_millis(200));
                    }
                    Err(e) => {
                        eprintln!("[servidor-impressao] erro no accept: {}", e);
                        std::thread::sleep(Duration::from_millis(500));
                    }
                }
            }
        });
    }

    // Thread UDP: responde à descoberta dos outros caixas
    {
        let rodando = rodando.clone();
        std::thread::spawn(move || {
            let mut buffer = [0u8; 64];
            while rodando.load(Ordering::SeqCst) {
                match udp.recv_from(&mut buffer) {
                    Ok((n, origem))
                        if &buffer[..n] == MENSAGEM_DESCOBERTA
                            || &buffer[..n] == MENSAGEM_DESCOBERTA_LEGADA =>
                    {
                        let ip_lan = ip_lan_privado()
                            .map(|ip| ip.to_string())
                            .unwrap_or_default();
                        let resposta = format!(
                            "{{\"nome\":{:?},\"porta\":{},\"ip\":\"{}\"}}",
                            nome_terminal, porta, ip_lan
                        );
                        let _ = udp.send_to(resposta.as_bytes(), origem);
                    }
                    _ => {}
                }
            }
        });
    }

    Ok(())
}

#[tauri::command(async)]
pub fn parar_servidor_impressao(state: tauri::State<'_, EstadoServidorImpressao>) -> Result<(), String> {
    if let Some(flag) = state.0.lock().unwrap().take() {
        flag.store(false, Ordering::SeqCst);
    }
    Ok(())
}

#[tauri::command(async)]
pub fn descobrir_servidores_impressao() -> Result<Vec<ServidorDescoberto>, String> {
    use std::time::Instant;

    let udp = UdpSocket::bind(("0.0.0.0", 0)).map_err(|e| e.to_string())?;
    udp.set_broadcast(true).map_err(|e| e.to_string())?;
    udp.set_read_timeout(Some(Duration::from_millis(300)))
        .map_err(|e| e.to_string())?;
    udp.send_to(MENSAGEM_DESCOBERTA, ("255.255.255.255", PORTA_DESCOBERTA))
        .map_err(|e| format!("Falha ao enviar broadcast de descoberta: {}", e))?;
    // Segunda sonda para caixas ainda na versao antiga. Respostas duplicadas do mesmo
    // terminal caem na deduplicacao por IP mais abaixo.
    let _ = udp.send_to(MENSAGEM_DESCOBERTA_LEGADA, ("255.255.255.255", PORTA_DESCOBERTA));

    let mut servidores: Vec<ServidorDescoberto> = Vec::new();
    let inicio = Instant::now();
    let mut buffer = [0u8; 256];
    while inicio.elapsed() < Duration::from_millis(1500) {
        if let Ok((n, origem)) = udp.recv_from(&mut buffer) {
            let texto = String::from_utf8_lossy(&buffer[..n]);
            let ip = texto
                .split("\"ip\":\"")
                .nth(1)
                .and_then(|s| s.split('"').next())
                .filter(|s| !s.is_empty())
                .map(|s| s.to_string())
                .unwrap_or_else(|| origem.ip().to_string());
            if servidores.iter().any(|s| s.ip == ip) {
                continue;
            }
            let nome = texto
                .split("\"nome\":")
                .nth(1)
                .and_then(|s| s.split('"').nth(1))
                .unwrap_or("Caixa")
                .to_string();
            let porta = texto
                .split("\"porta\":")
                .nth(1)
                .and_then(|s| s.split(|c| c == ',' || c == '}').next())
                .and_then(|n| n.trim().parse::<u16>().ok())
                .unwrap_or(9100);
            servidores.push(ServidorDescoberto { nome, ip, porta });
        }
    }
    Ok(servidores)
}

#[tauri::command(async)]
pub fn obter_ip_local() -> Result<String, String> {
    ip_lan_privado()
        .map(|ip| ip.to_string())
        .ok_or_else(|| "Nenhum IP privado encontrado".to_string())
}

#[tauri::command(async)]
pub fn imprimir_rede(ip: String, porta: u16, dados: Vec<u8>) -> Result<(), String> {
    use std::io::Write;
    use std::net::SocketAddr;

    let endereco: SocketAddr = format!("{}:{}", ip, porta)
        .parse()
        .map_err(|_| format!("Endereço inválido: {}:{}", ip, porta))?;
    let mut conexao = TcpStream::connect_timeout(&endereco, Duration::from_secs(3))
        .map_err(|e| format!("Não foi possível conectar à impressora {}:{} ({})", ip, porta, e))?;
    conexao
        .set_write_timeout(Some(Duration::from_secs(5)))
        .map_err(|e| e.to_string())?;
    conexao
        .write_all(&dados)
        .and_then(|_| conexao.flush())
        .map_err(|e| format!("Falha ao enviar dados à impressora de rede: {}", e))
}
