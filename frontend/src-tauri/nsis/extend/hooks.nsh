!define FIREWALL_RULE_NAME "StartBigERP_API_Server"
!define FIREWALL_PING_RULE_NAME "StartBigERP_Ping_Server"

!macro NSIS_HOOK_POSTINSTALL
    DetailPrint "Configurando o Firewall do Windows para o Servidor API de Rede e Ping..."
    
    ; 1. Regra de Entrada TCP para a API (erp-api.exe)
    nsExec::Exec 'netsh advfirewall firewall add rule name="${FIREWALL_RULE_NAME}" dir=in action=allow program="$INSTDIR\erp-api.exe" profile=any description="Regra de Entrada TCP para permitir conexoes de terminais ao servidor StartBig."'
    Pop $0
    ${If} $0 != 0
        DetailPrint "AVISO: Nao foi possivel criar a regra de firewall da API automaticamente."
    ${EndIf}

    ; 2. Regra de Entrada ICMPv4 (Ping) para testar a conectividade do servidor
    nsExec::Exec 'netsh advfirewall firewall add rule name="${FIREWALL_PING_RULE_NAME}" protocol=icmpv4:8,any dir=in action=allow description="Permite recebimento de Ping (ICMPv4) dos terminais da rede."'
    Pop $0
    ${If} $0 != 0
        DetailPrint "AVISO: Nao foi possivel criar a regra de firewall para Ping automaticamente."
    ${EndIf}
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
    ; 1. Para e desinstala o servico do backend
    DetailPrint "Parando e desinstalando o servico do backend..."
    nsExec::Exec '"$INSTDIR\erp-api.exe" --stop --uninstall'
    Pop $0
    ${If} $0 != 0
        DetailPrint "AVISO: Nao foi possivel parar/desinstalar o servico do backend."
    ${EndIf}

    ; 2. Remove as regras do Firewall
    DetailPrint "Removendo regras do Firewall..."

    ; Remove a regra da API
    nsExec::Exec 'netsh advfirewall firewall delete rule name="${FIREWALL_RULE_NAME}"'
    Pop $0

    ; Remove a regra do Ping
    nsExec::Exec 'netsh advfirewall firewall delete rule name="${FIREWALL_PING_RULE_NAME}"'
    Pop $0
!macroend