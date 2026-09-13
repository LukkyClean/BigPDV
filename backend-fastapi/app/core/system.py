import os
import sys
import ctypes

import tempfile
import subprocess

TASK_NAME = "StartBigServer"
TCP_LAW = "StartBig-Server"
MDSN_LAW = "StartBig-mDNS"

MDNS_PORT = 5353

def app_is_adm() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
    
def _exec(comm: list[str], desc: str) -> bool:
    try:
        result = subprocess.run(
            comm,
            capture_output=True,
            encoding="cp850",
            errors="replace",
            timeout=30,
        )
        
        if result.returncode == 0:
            print(f"[OK] {desc}")
            return True
        
        err = (result.stderr or result.stdout).strip()
        print(f"[ERRO] {desc} -> {err}")
        return False
    except Exception as e:
        print(f"[ERRO] {desc} -> {type(e).__name__}: {e}")
        return False
    
def exec_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])

def firewall_cfg(port: int) -> None:
    print(f"[firewall] Configurando firewall para porta {port}...")
    
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={TCP_LAW}"],
        capture_output=True,
    )
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={MDSN_LAW}"],
        capture_output=True,
    )
    
    _exec(
        [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={TCP_LAW}",
            "dir=in", "action=allow", "protocol=TCP",
            f"localport={port}", "profile=any"
        ],
        f"Regra de firewall TCP para porta {port} (STARTBIG API)"
    )
    
    _exec(
        [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={MDSN_LAW}",
            "dir=in", "action=allow", "protocol=UDP",
            f"localport={MDNS_PORT}", "profile=any"
        ],
        f"Regra de firewall UDP para porta {MDNS_PORT} (STARTBIG mDNS)"
    )
    
def remove_firewall_rules() -> None:
    print("[firewall] Removendo regras de firewall...")
    
    _exec(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={TCP_LAW}"],
        f"Removendo regra de firewall TCP ({TCP_LAW})"
    )
    _exec(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={MDSN_LAW}"],
        f"Removendo regra de firewall UDP ({MDSN_LAW})"
    )
        
_XML_TASK = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Servidor StartBig - inicia automaticamente com o Windows</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </BootTrigger>
    <!-- "Desligar" com Inicialização Rápida do Windows é hibernação: o BootTrigger
         não dispara ao religar. O LogonTrigger cobre esse caso; com
         MultipleInstancesPolicy=IgnoreNew é no-op se o serviço já está no ar. -->
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT15S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>5</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{comando}</Command>
      <Arguments>{argumentos}</Arguments>
      <WorkingDirectory>{pasta}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

# Handlers functions for autostart and firewall configuration on Windows systems.

def install_autostart(host: str, port: int, data_dir: str | None = None) -> None:
    print("[autostart] Instalando tarefa de inicialização automática...")

    exe = exec_path()
    exe_dir = os.path.dirname(exe)

    # O --data-dir fixa a pasta de dados que a task (rodando como SYSTEM) vai usar.
    # Preferir o valor recebido na linha de comando: o app Tauri passa o
    # LOCALAPPDATA do usuário LOGADO. Sem ele, cairíamos no LOCALAPPDATA do
    # processo elevado — que é o da conta que respondeu ao UAC, e pode ser outro
    # usuário → outro banco → "não reconhece usuário e senha".
    if not data_dir:
        from app.core.config import data_dir as data_dir_padrao
        data_dir = data_dir_padrao

    print(f"[autostart] Pasta de dados da tarefa: {data_dir}")

    xml = _XML_TASK.format(
        comando=exe,
        argumentos=f'--host {host} --port {port} --data-dir "{data_dir}"',
        pasta=exe_dir
    )
    
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-16") as file:
        file.write(xml)
        xml_path = file.name
        
    try:
        ok = _exec(
            ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"],
            f"Instalando tarefa de inicialização automática ({TASK_NAME})"
        )
        
        if ok:
            print("[autostart] Tarefa de inicialização automática instalada com sucesso")
    finally:
        try:
            os.unlink(xml_path)
        except OSError:
            pass
        
def remove_autostart() -> None:
    print("[autostart] Removendo tarefa de inicialização automática...")
    
    _exec(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        f"Removendo tarefa de inicialização automática ({TASK_NAME})"
    )
    
def init_now() -> None:
    _exec(
        ["schtasks", "/Run", "/TN", TASK_NAME],
        f"Iniciando tarefa de inicialização automática ({TASK_NAME})"
    )
    
def stop_service() -> None:
    _exec(
        ["schtasks", "/End", "/TN", TASK_NAME],
        f"Parando tarefa de inicialização automática ({TASK_NAME})"
    )
    
# Main commands

def install(host: str, port: int, data_dir: str | None = None) -> int:
    print("=" * 60)
    print("\nINSTALANDO SERVIÇO STARTBIG\n")
    print("=" * 60)
    
    if not app_is_adm():
        print("\n[ERRO] É necessário executar este comando como administrador.")
        print("        Clique com o botão direito no terminal e selecione 'Executar como administrador'.")
        return 1
    
    firewall_cfg(port)
    install_autostart(host, port, data_dir)
    
    init_now()
    
    print("\n" + "=" * 60)
    print("\n[OK] Instalação concluída com sucesso.")
    print("\nO serviço StartBig Server foi instalado e subira automaticamente no proximo boot.")
    print("\nPara iniciar o serviço imediatamente, execute: startbig.exe --init")
    print("\n" + "=" * 60)
    return 0

def uninstall() -> int:
    print("=" * 60)
    print("\nDESINSTALANDO SERVIÇO STARTBIG\n")
    print("=" * 60)
    
    if not app_is_adm():
        print("\n[ERRO] É necessário executar este comando como administrador.")
        print("        Clique com o botão direito no terminal e selecione 'Executar como administrador'.")
        return 1
    
    stop_service()
    remove_autostart()
    remove_firewall_rules()
    
    print("\n" + "=" * 60)
    print("\n[OK] Desinstalação concluída com sucesso.")
    print("\nO serviço StartBig Server foi removido do sistema.")
    print("\n" + "=" * 60)
    return 0

def status() -> int:
    print("=" * 60)
    print("\nSTATUS DO SERVIÇO STARTBIG\n")
    print("=" * 60)
    
    print("\n[INFO] Verificando status do serviço StartBig Server...")
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True,
        text=True,
    )
    print("\n" + result.stdout.strip() if result.returncode == 0 else "\n[INFO] O serviço StartBig Server não está instalado.")

    print("\n" + "=" * 60)
    print("\n[INFO] Veficando regras de firewall...")
    for law in [TCP_LAW, MDSN_LAW]:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={law}"],
            capture_output=True,
            text=True,
        )
        print("\n" + result.stdout.strip() if result.returncode == 0 else f"\n[INFO] A regra de firewall '{law}' não está instalada.")
    print("\n" + "=" * 60)
    
    return 0