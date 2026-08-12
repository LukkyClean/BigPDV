from typing import Any, Dict, Optional

from app.schemas.backup import BackupInfo, FlowDecision


class CloudSyncError(Exception):
    """Erro do sincronizador. `code` carrega o código da API quando houver."""

    def __init__(self, message: str, code: Optional[str] = None,
                 http_status: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def flow(status: Dict[str, Any], last_manifest: Optional[dict],
         last_local_backup: Optional[BackupInfo]) -> FlowDecision:
    """
    Implementa o §2 da spec, na ordem exata. Função pura: sem rede, sem disco.
    Ações: blocked | in_progress | up_to_date | no_local_backup | upload
    """
    # Import local evita ciclo: flow → journal → (chain)
    from .journal import code_content

    # 1. plano permite backup em nuvem?
    if not status.get("planoPermiteBackup", False):
        return FlowDecision(action="blocked", code=status.get("codigoBloqueio", "unknown"))

    # 2. outra máquina enviando?
    if status.get("envioEmAndamento", False):
        return FlowDecision(action="in_progress")

    # sem backup local ainda: não há O QUE enviar.
    if last_manifest is None or last_local_backup is None:
        return FlowDecision(action="no_local_backup")

    # 3. PULAR ANTECIPADO: compara o codigoConteudo do último elo da nuvem
    #    com o do nosso manifest, ANTES de qualquer escrita.
    #    §5b: `corrente` pode vir vazia; sem termo de comparação, seguimos.
    chain = status.get("corrente") or []
    if chain:
        cloud_code = chain[-1].get("codigoConteudo")
        if cloud_code and cloud_code == code_content(last_manifest):
            return FlowDecision(action="up_to_date")

    # 4. full ou fragmento? Decisão do SERVIDOR.
    #    spec: fullDoCicloConfirmado == False  => próximo envio é FULL.
    backup_type = "full" if not status.get("fullDoCicloConfirmado", False) else "fragmento"

    # RECONCILIAÇÃO: servidor quer full e o backup local mais recente NÃO é full.
    force_full = backup_type == "full" and not last_local_backup.completo

    return FlowDecision(
        action="upload",
        backup_type=backup_type,
        cycle=status.get("cicloCorrente"),
        force_full_local=force_full or None,
    )
