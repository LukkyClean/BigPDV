use mdns_sd::{ServiceDaemon, ServiceEvent};
use serde::{Deserialize, Serialize};
use std::net::IpAddr;

use super::local_ip::{ip_e_desta_maquina, ip_e_privado, ip_na_mesma_subrede};
use super::log::log_rede;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{AppHandle, Emitter};

const TIPO_SERVICO: &str = "_startbig._tcp.local.";

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct DiscoveryPayload {
    pub app: String,
    pub role: String,
    pub ip: String,
    pub port: u16,
    /// O IP anunciado é desta própria máquina — o wizard não deve auto-conectar
    /// como terminal a ele (é o caminho que transformava o servidor em terminal).
    pub local: bool,
}

#[derive(Default)]
pub struct EstadoDescoberta {
    daemon_cliente: Mutex<Option<ServiceDaemon>>,
    parar_cliente: Mutex<Option<Arc<AtomicBool>>>,
}

impl EstadoDescoberta {

    fn parar_cliente(&self) {
        if let Some(flag) = self.parar_cliente.lock().unwrap().take() {
            flag.store(false, Ordering::SeqCst);
        }

        if let Some(daemon) = self.daemon_cliente.lock().unwrap().take() {
            if let Err(e) = daemon.shutdown() {
                eprintln!("[discovery] Erro ao encerrar daemon cliente: {:?}", e);
            }
        }
    }
}

pub fn discover_servers(estado: &EstadoDescoberta, handle: AppHandle) {
    estado.parar_cliente();

    let daemon = match ServiceDaemon::new() {
        Ok(d) => d,
        Err(e) => {
            eprintln!("[discovery] Falha ao criar daemon mDNS cliente: {:?}", e);
            return;
        }
    };

    let receiver = match daemon.browse(TIPO_SERVICO) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("[discovery] Falha ao iniciar browse mDNS: {:?}", e);
            let _ = daemon.shutdown();
            return;
        }
    };

    let rodando = Arc::new(AtomicBool::new(true));

    *estado.parar_cliente.lock().unwrap() = Some(rodando.clone());
    *estado.daemon_cliente.lock().unwrap() = Some(daemon);

    println!("[discovery] Terminal buscando servidores via mDNS...");

    thread::spawn(move || {
        while rodando.load(Ordering::SeqCst) {
            match receiver.recv_timeout(Duration::from_secs(2)) {
                Ok(ServiceEvent::ServiceResolved(info)) => {
                    let port = info.get_port();
                    let Some(ip) = escolher_endereco(info.get_addresses().iter().copied()) else {
                        log_rede(&format!(
                            "anúncio mDNS de {} ignorado: só endereços loopback/link-local",
                            info.get_fullname()
                        ));
                        continue;
                    };
                    let ip = ip.to_string();
                    let local = ip_e_desta_maquina(&ip);

                    let app_prop = info
                        .get_property_val_str("app")
                        .unwrap_or("startbig");
                    let role_prop = info
                        .get_property_val_str("role")
                        .unwrap_or("server");

                    let payload = DiscoveryPayload {
                        app: app_prop.to_string(),
                        role: role_prop.to_string(),
                        ip: ip.clone(),
                        port,
                        local,
                    };

                    log_rede(&format!(
                        "servidor encontrado via mDNS: {}:{} (local={})",
                        ip, port, local
                    ));

                    handle.emit("server_discovered", &payload).unwrap_or_else(
                        |e| eprintln!("[discovery] Erro ao emitir evento: {}", e),
                    );
                }
                Ok(_) => {}
                Err(flume::RecvTimeoutError::Timeout) => continue,
                Err(flume::RecvTimeoutError::Disconnected) => {
                    println!("[discovery] Canal mDNS desconectado, encerrando thread");
                    break;
                }
            }
        }

        println!("[discovery] Thread de descoberta encerrada");
    });
}

#[tauri::command]
pub fn iniciar_descoberta_servidores(
    app: AppHandle,
    state: tauri::State<'_, EstadoDescoberta>,
) {
    discover_servers(&state, app);
}

#[tauri::command]
pub fn parar_descoberta_servidores(state: tauri::State<'_, EstadoDescoberta>) {
    state.parar_cliente();
    println!("[discovery] Comando recebido para parar a descoberta.");
}

/// Entre os endereços anunciados, descarta loopback/unspecified/link-local (um
/// servidor sem rota default anunciava `127.0.0.1`, e o terminal tentava falar
/// consigo mesmo) e prefere, nesta ordem: mesma sub-rede de uma interface local,
/// IPv4 privado, qualquer IPv4 restante.
fn escolher_endereco<I: Iterator<Item = IpAddr>>(enderecos: I) -> Option<IpAddr> {
    let candidatos: Vec<IpAddr> = enderecos
        .filter(|a| match a {
            IpAddr::V4(v4) => !v4.is_loopback() && !v4.is_unspecified() && !v4.is_link_local(),
            IpAddr::V6(_) => false,
        })
        .collect();

    candidatos
        .iter()
        .copied()
        .find(|a| matches!(a, IpAddr::V4(v4) if ip_na_mesma_subrede(*v4)))
        .or_else(|| candidatos.iter().copied().find(|a| ip_e_privado(*a)))
        .or_else(|| candidatos.first().copied())
}

#[cfg(test)]
mod tests {
    use super::escolher_endereco;
    use std::net::{IpAddr, Ipv4Addr};

    #[test]
    fn descarta_loopback() {
        let so_loopback = [IpAddr::V4(Ipv4Addr::LOCALHOST)];
        assert_eq!(escolher_endereco(so_loopback.into_iter()), None);
    }

    #[test]
    fn prefere_privado_a_publico() {
        let lista = [
            IpAddr::V4(Ipv4Addr::new(8, 8, 8, 8)),
            IpAddr::V4(Ipv4Addr::LOCALHOST),
            IpAddr::V4(Ipv4Addr::new(10, 0, 0, 5)),
        ];
        assert_eq!(
            escolher_endereco(lista.into_iter()),
            Some(IpAddr::V4(Ipv4Addr::new(10, 0, 0, 5)))
        );
    }
}
