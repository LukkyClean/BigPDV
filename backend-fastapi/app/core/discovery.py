import socket
from zeroconf import Zeroconf, ServiceInfo

import logging

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_startbig._tcp.local."

INSTANCE_NAME = "startbig-server"

PROPERTY = {
    "app": "startbig",
    "role": "server",
}

_zeroconf: Zeroconf | None = None
_service_info: ServiceInfo | None = None

def get_local_ip_address() -> str:
    # Discover the local IP address of the machine
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()
        
def register_service(server_ip: str, server_port: int) -> None:
    # Register the service with Zeroconf for discovery on the local network
    
    global _zeroconf, _service_info
    
    stop_discovery()
    
    if server_ip == "0.0.0.0":
        ip = get_local_ip_address()
    else:
        ip = server_ip
        
    try:
        _zeroconf = Zeroconf()
    except Exception as e:
        print(f"[discovery] Falha ao criar daemon mDNS: {e}")
        return
    
    hostname = f"{socket.gethostname()}.local."
    
    _service_info = ServiceInfo(
        type_=SERVICE_TYPE,
        name=f"{INSTANCE_NAME}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(ip)],
        port=server_port,
        properties=PROPERTY,
        server=hostname
    )
    
    try:
        _zeroconf.register_service(_service_info, allow_name_change=True)
        print(f"[discovery] Servidor anunciado via mDNS: {INSTANCE_NAME} em {ip}:{server_port}")
    except Exception as e:
        print(f"[discovery] Falha ao registrar serviço mDNS: {e}")
        stop_discovery()
        
def stop_discovery() -> None:
    global _zeroconf, _service_info
    
    if _zeroconf is not None:
        try:
            if _service_info is not None:
                _zeroconf.unregister_service(_service_info)
            _zeroconf.close()
            print("[discovery] Serviço mDNS encerrado")
        except Exception as e:
            print(f"[discovery] Erro ao encerrar mDNS: {e}")
            
    _zeroconf = None
    _service_info = None