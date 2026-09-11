//! Interfaces de rede desta máquina.
//!
//! Centraliza a pergunta "este IP é meu?" — usada para impedir que a máquina
//! servidora se grave como terminal apontando para o próprio IP de LAN (que muda
//! com o DHCP) e para escolher, entre os endereços anunciados por mDNS, o que está
//! na mesma sub-rede. Usa `if-addrs` (já vinha no `Cargo.lock` via `mdns-sd`), em
//! vez do truque de `connect(8.8.8.8)`, que depende de rota para a internet.

use std::net::{IpAddr, Ipv4Addr};

#[derive(Debug, Clone, Copy)]
pub struct InterfaceLocal {
    pub ip: Ipv4Addr,
    pub mascara: Ipv4Addr,
}

/// IPv4 das interfaces ativas, sem loopback nem link-local (169.254/16).
pub fn interfaces_locais() -> Vec<InterfaceLocal> {
    let Ok(ifaces) = if_addrs::get_if_addrs() else {
        return Vec::new();
    };

    ifaces
        .into_iter()
        .filter_map(|iface| match iface.addr {
            if_addrs::IfAddr::V4(v4) if !v4.ip.is_loopback() && !v4.ip.is_link_local() => {
                Some(InterfaceLocal {
                    ip: v4.ip,
                    mascara: v4.netmask,
                })
            }
            _ => None,
        })
        .collect()
}

pub fn ips_locais() -> Vec<Ipv4Addr> {
    interfaces_locais().into_iter().map(|i| i.ip).collect()
}

pub fn ip_e_privado(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => v4.is_private(),
        IpAddr::V6(_) => false,
    }
}

/// Loopback, `0.0.0.0`, `localhost` ou IPv4 de alguma interface desta máquina.
pub fn ip_e_desta_maquina(ip: &str) -> bool {
    let ip = ip.trim();
    if ip.eq_ignore_ascii_case("localhost") {
        return true;
    }
    let Ok(addr) = ip.parse::<IpAddr>() else {
        return false;
    };
    if addr.is_loopback() || addr.is_unspecified() {
        return true;
    }
    match addr {
        IpAddr::V4(v4) => ips_locais().contains(&v4),
        IpAddr::V6(_) => false,
    }
}

/// Verdadeiro se `ip` cai na sub-rede de alguma interface local.
pub fn ip_na_mesma_subrede(ip: Ipv4Addr) -> bool {
    interfaces_locais().iter().any(|iface| {
        let m = u32::from(iface.mascara);
        (u32::from(ip) & m) == (u32::from(iface.ip) & m)
    })
}

/// Primeiro IP privado desta máquina, preferindo interfaces com gateway típico
/// de LAN (192.168/16, 10/8, 172.16/12). Substitui o antigo `ip_lan_privado`.
pub fn ip_lan_privado() -> Option<Ipv4Addr> {
    let ips = ips_locais();
    ips.iter()
        .copied()
        .find(|ip| ip.octets()[0] == 192 && ip.octets()[1] == 168)
        .or_else(|| ips.iter().copied().find(|ip| ip.is_private()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loopback_e_unspecified_sao_locais() {
        assert!(ip_e_desta_maquina("127.0.0.1"));
        assert!(ip_e_desta_maquina("0.0.0.0"));
        assert!(ip_e_desta_maquina("localhost"));
        assert!(ip_e_desta_maquina(" LOCALHOST "));
    }

    #[test]
    fn ip_de_documentacao_nao_e_local() {
        // TEST-NET-3 (RFC 5737) nunca está atribuído a uma interface real.
        assert!(!ip_e_desta_maquina("203.0.113.1"));
        assert!(!ip_e_desta_maquina("nao-e-ip"));
    }

    #[test]
    fn todos_os_ips_das_interfaces_sao_locais() {
        for ip in ips_locais() {
            assert!(ip_e_desta_maquina(&ip.to_string()), "{} deveria ser local", ip);
            assert!(ip_na_mesma_subrede(ip));
        }
    }
}
