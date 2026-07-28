import os
import sys
import argparse
import multiprocessing

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR
    
os.chdir(BASE_DIR)

os.environ["STARTBIG_BASE_DIR"] = BASE_DIR
os.environ["STARTBIG_BUNDLE_DIR"] = BUNDLE_DIR

APP_ENV = os.getenv("APP_ENV", "development").lower()

if not getattr(sys, "frozen", False):
    print(f"[INFO] Ambiente de execução: {APP_ENV}")
    
    DIST_DIR = os.path.join(BASE_DIR, "dist")
    
    if APP_ENV == "production":
        if not os.path.exists(DIST_DIR):
            print("[ERROR] O diretório 'dist' não foi encontrado. Certifique-se de que o código foi empacotado corretamente.")
            sys.exit(1)
        
        sys.path.insert(0, DIST_DIR)
        print("[INFO] Rodando o Backend em modo Protegido (PyArmor)...")
    else:
        print("[INFO] Rodando o Backend em modo Desenvolvimento (Código Aberto)...")

def mount_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="startbig-backend",
        description="Backend do STARTBIG",
    )
    
    p.add_argument("host_pos", nargs="?", default=None, help=argparse.SUPPRESS)
    p.add_argument("port_pos", nargs="?", default=None, help=argparse.SUPPRESS)
    
    p.add_argument("--host", default=None, help="Endereço IP do servidor (padrão: 0.0.0.0)")
    p.add_argument("--port", type=int, default=None, help="Porta do servidor (padrão: 8080)")

    p.add_argument("--install", action="store_true",
                   help="Configura firewall e inicializacao automatica")
    p.add_argument("--uninstall", action="store_true",
                   help="Remove firewall e inicializacao automatica")
    p.add_argument("--status", action="store_true",
                   help="Mostra o estado da instalacao")
    p.add_argument("--init", action="store_true",
                   help="Inicia o servidor em segundo plano")
    p.add_argument("--stop", action="store_true",
                   help="Para o servidor em segundo plano")
    return p

def main() -> int:
    args = mount_parser().parse_args()
    
    host = args.host or args.host_pos or "0.0.0.0"
    port = args.port or (int(args.port_pos) if args.port_pos else None) or 8080

    if args.install or args.uninstall or args.status or args.init or args.stop:
        from app.core import system
        
        if args.install:
            return system.install(host, port)
        if args.uninstall:
            return system.uninstall()
        if args.status:
            return system.status()
        if args.init:
            system.init_now()
            return 0
        if args.stop:
            system.stop_service()
            return 0
        
    os.environ["STARTBIG_HOST"] = host
    os.environ["STARTBIG_PORT"] = str(port)
    
    print(f"[INFO] Pasta de trabalho: {BASE_DIR}")
    print(f"[INFO] Iniciando o servidor FastAPI no ip {host} na porta {port}...")

    import uvicorn
    from app.main import app
    
    uvicorn.run(app, host=host, port=port, reload=False)
    return 0

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    sys.exit(main())

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DIST_DIR = os.path.join(BASE_DIR, "dist")

# print(f"[INFO] Ambiente de execução: {APP_ENV}")

# if APP_ENV == "production":
#     if not os.path.exists(DIST_DIR):
#         print("[ERROR] O diretório 'dist' não foi encontrado. Certifique-se de que o código foi empacotado corretamente.")
#         sys.exit(1)
    
#     sys.path.insert(0, DIST_DIR)
#     print("[INFO] Rodando o Backend em modo Protegido (PyArmor)...")
# else:
#     print("[INFO] Rodando o Backend em modo Desenvolvimento (Código Aberto)...")
    
# if __name__ == "__main__":
#     ip_address = "0.0.0.0"
#     port = 8080
    
#     if len(sys.argv) > 2:
#        ip_address = sys.argv[1]
#        port = int(sys.argv[2])
        
#     print(f"[INFO] Iniciando o servidor FastAPI no ip {ip_address} na porta {port}...")
    
    
