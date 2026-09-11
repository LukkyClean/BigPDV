"""Anúncio do servidor na rede local via mDNS (`_startbig._tcp.local.`).

Os terminais (Tauri, crate `mdns-sd`) descobrem o servidor por este anúncio quando o
IP salvo deixa de responder — é o que permite sobreviver a uma troca de IP por DHCP.

Regras:
- anunciar TODAS as IPv4 das interfaces (exceto loopback e link-local), enumeradas
  com `ifaddr` (dependência do próprio zeroconf). O truque antigo de
  `connect(("8.8.8.8", 80))` devolvia `127.0.0.1` numa loja sem internet ou quando a
  placa ainda não tinha IP em boot + 30 s — e os terminais tentavam falar consigo
  mesmos;
- nunca anunciar `127.0.0.1`: sem endereço utilizável, não registra e tenta no
  próximo ciclo do watchdog;
- `atualizar_anuncio()` é chamada periodicamente (app/core/tarefas.py) e re-registra
  quando o conjunto de IPs muda, com "goodbye" explícito para os clientes não
  esperarem o TTL.
"""

import ipaddress
import logging
import socket

import ifaddr
from zeroconf import InterfaceChoice, ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_startbig._tcp.local."

INSTANCE_NAME = "startbig-server"

PROPERTY = {
    "app": "startbig",
    "role": "server",
}

_zeroconf: Zeroconf | None = None
_service_info: ServiceInfo | None = None
_ips_anunciados: tuple[str, ...] = ()
_host: str = "0.0.0.0"
_port: int = 8080


def listar_ipv4_locais() -> list[str]:
    """IPv4 das interfaces ativas, sem loopback nem link-local (169.254/16).

    Prefere endereços privados (RFC 1918) e, entre eles, os de 192.168/16 — o
    padrão de roteador de loja — para o primeiro da lista ser o mais provável.
    """
    encontrados: list[str] = []
    try:
        adaptadores = ifaddr.get_adapters()
    except Exception as e:  # pragma: no cover - depende do SO
        logger.warning("[discovery] Falha ao enumerar interfaces: %s", e)
        return encontrados

    for adaptador in adaptadores:
        for ip in adaptador.ips:
            if not isinstance(ip.ip, str):  # IPv6 vem como tupla
                continue
            try:
                addr = ipaddress.IPv4Address(ip.ip)
            except ipaddress.AddressValueError:
                continue
            if addr.is_loopback or addr.is_link_local or addr.is_unspecified:
                continue
            if ip.ip not in encontrados:
                encontrados.append(ip.ip)

    def prioridade(valor: str) -> tuple[int, str]:
        addr = ipaddress.IPv4Address(valor)
        if valor.startswith("192.168."):
            return (0, valor)
        if addr.is_private:
            return (1, valor)
        return (2, valor)

    return sorted(encontrados, key=prioridade)


def get_local_ip_address() -> str:
    """Compatibilidade: primeiro IP utilizável, ou `127.0.0.1` se não houver rede."""
    ips = listar_ipv4_locais()
    return ips[0] if ips else "127.0.0.1"


def _enderecos_para_anunciar(server_ip: str) -> list[str]:
    if server_ip and server_ip not in ("0.0.0.0", "127.0.0.1", "localhost"):
        return [server_ip]
    return listar_ipv4_locais()


def _registrar(ips: list[str]) -> None:
    global _zeroconf, _service_info, _ips_anunciados

    if _zeroconf is None:
        try:
            _zeroconf = Zeroconf(interfaces=InterfaceChoice.All)
        except Exception as e:
            print(f"[discovery] Falha ao criar daemon mDNS: {e}")
            return

    hostname = f"{socket.gethostname()}.local."

    info = ServiceInfo(
        type_=SERVICE_TYPE,
        name=f"{INSTANCE_NAME}.{SERVICE_TYPE}",
        parsed_addresses=ips,
        port=_port,
        properties=PROPERTY,
        server=hostname,
    )

    try:
        _zeroconf.register_service(info, allow_name_change=True)
        _service_info = info
        _ips_anunciados = tuple(ips)
        print(f"[discovery] Servidor anunciado via mDNS: {INSTANCE_NAME} em {', '.join(ips)}:{_port}")
    except Exception as e:
        print(f"[discovery] Falha ao registrar serviço mDNS: {e}")
        _service_info = None
        _ips_anunciados = ()


def _cancelar_registro() -> None:
    global _service_info, _ips_anunciados
    if _zeroconf is not None and _service_info is not None:
        try:
            _zeroconf.unregister_service(_service_info)
        except Exception as e:
            print(f"[discovery] Erro ao cancelar anúncio mDNS: {e}")
    _service_info = None
    _ips_anunciados = ()


def register_service(server_ip: str, server_port: int) -> None:
    """Primeiro anúncio, no startup. Sem IP utilizável, deixa para o watchdog."""
    global _host, _port

    stop_discovery()
    _host = server_ip
    _port = server_port

    ips = _enderecos_para_anunciar(server_ip)
    if not ips:
        print("[discovery] Nenhum IP de rede disponível ainda; anúncio mDNS adiado")
        return

    _registrar(ips)


def atualizar_anuncio() -> None:
    """Watchdog: re-anuncia se o conjunto de IPs mudou (DHCP, placa que subiu depois)."""
    global _zeroconf

    ips = _enderecos_para_anunciar(_host)

    if _zeroconf is not None:
        try:
            # Abre sockets em interfaces novas e fecha as que sumiram; no-op se nada mudou.
            _zeroconf.update_interfaces()
        except Exception as e:
            print(f"[discovery] Falha ao atualizar interfaces do mDNS: {e}")

    if tuple(ips) == _ips_anunciados:
        return

    if not ips:
        if _ips_anunciados:
            print("[discovery] Rede indisponível; cancelando anúncio mDNS")
        _cancelar_registro()
        return

    print(f"[discovery] IPs mudaram ({', '.join(_ips_anunciados) or 'nenhum'} -> {', '.join(ips)}); re-anunciando")
    _cancelar_registro()
    _registrar(ips)


def stop_discovery() -> None:
    global _zeroconf

    _cancelar_registro()
    if _zeroconf is not None:
        try:
            _zeroconf.close()
            print("[discovery] Serviço mDNS encerrado")
        except Exception as e:
            print(f"[discovery] Erro ao encerrar mDNS: {e}")

    _zeroconf = None
