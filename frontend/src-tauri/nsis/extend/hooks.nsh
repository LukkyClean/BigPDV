!define FIREWALL_RULE_NAME "StartBigERP_API_Server"
!define FIREWALL_PING_RULE_NAME "StartBigERP_Ping_Server"

!macro NSIS_HOOK_PREINSTALL
    ; O backend NAO e filho do app: roda como tarefa agendada (StartBigServer, como
    ; SYSTEM) a partir de $INSTDIR\erp-api.exe -- ver app/core/system.py.
    ;
    ; O template so mata o MAINBINARYNAME (CheckIfAppIsRunning), nunca o erp-api.
    ; Com o processo vivo, o Windows trava o .exe e o `File /a "/oname=erp-api.exe"`
    ; da Section Install nao consegue sobrescrever: o instalador conclui "com
    ; sucesso" e o cliente segue rodando o BACKEND ANTIGO. Foi o que segurou o fix
    ; do IMEI na loja em 01/08/2026 -- reinstalar o app nao adiantava nada.
    DetailPrint "Parando o servidor StartBig antes de atualizar..."

    ; /End encerra a instancia da task. Nao espera o processo morrer, e uma
    ; instalacao anterior pode ter deixado um erp-api orfao (sem task nenhuma),
    ; entao o taskkill logo abaixo cobre os dois casos.
    nsExec::Exec 'schtasks /End /TN "StartBigServer"'
    Pop $0

    nsExec::Exec 'taskkill /F /T /IM "erp-api.exe"'
    Pop $0

    ; Da tempo do Windows liberar o lock do arquivo antes da copia.
    Sleep 2000
!macroend

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

    ; 3. Religa o servidor que o PREINSTALL parou, ja com o binario novo.
    ; Falha (e nao faz nada) quando a task nao existe -- caso das maquinas de
    ; terminal, que nao rodam backend proprio.
    DetailPrint "Reiniciando o servidor StartBig..."
    nsExec::Exec 'schtasks /Run /TN "StartBigServer"'
    Pop $0
    ${If} $0 != 0
        DetailPrint "INFO: Nenhum servidor local para reiniciar (instalacao de terminal)."
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