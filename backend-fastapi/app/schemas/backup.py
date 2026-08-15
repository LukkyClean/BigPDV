# ---------------------------------------------------------------------------
# ARQUIVO: schemas/backup.py
# DESCRIÇÃO: Schemas Pydantic para backup local, sincronização com a nuvem
#            e journal de envios.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


# ===========================================================================
# Backup Local
# ===========================================================================

class BackupInfo(BaseModel):
    """Informações de um arquivo de backup listado no diretório local."""
    arquivo: str = Field(..., description="Nome do arquivo ZIP de backup")
    criado_em: str = Field(..., description="Data de criação em formato ISO 8601")
    tamanho_bytes: int = Field(..., description="Tamanho do arquivo em bytes")
    completo: bool = Field(..., description="True se for backup completo (full)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "arquivo": "backup_2026-08-06_143000_full.zip",
                "criado_em": "2026-08-06T14:30:00",
                "tamanho_bytes": 524288,
                "completo": True,
            }
        }
    }


class BackupCriado(BaseModel):
    """Resposta da criação de um novo backup."""
    arquivo: str = Field(..., description="Nome do arquivo ZIP criado")
    criado_em: str = Field(..., description="Data de criação em formato ISO 8601")
    tamanho_bytes: int = Field(..., description="Tamanho do arquivo em bytes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "arquivo": "backup_2026-08-06_143000_full.zip",
                "criado_em": "2026-08-06T14:30:00",
                "tamanho_bytes": 524288,
            }
        }
    }


class BackupCriadoComCota(BackupCriado):
    """Resposta da criação de backup manual com informação de cota diária."""
    backups_restantes_hoje: int = Field(..., description="Backups manuais restantes hoje (limite de 2/dia)")


class BackupVerificacao(BaseModel):
    """Resultado da verificação de integridade de um backup."""
    arquivo: str = Field(..., description="Nome do arquivo verificado")
    criado_em: str = Field(..., description="Data de criação registrada no manifest")
    valido: bool = Field(..., description="True se o backup passou na verificação")
    modo: str = Field(..., description="Modo de verificação: 'raso' ou 'profundo'")
    arquivos_verificados: int = Field(..., description="Quantidade de arquivos verificados")
    total_no_manifest: int = Field(..., description="Total de arquivos listados no manifest")

    model_config = {
        "json_schema_extra": {
            "example": {
                "arquivo": "backup_2026-08-06_143000_full.zip",
                "criado_em": "2026-08-06T14:30:00",
                "valido": True,
                "modo": "raso",
                "arquivos_verificados": 5,
                "total_no_manifest": 5,
            }
        }
    }


# ===========================================================================
# Árvore de Decisão da Sincronização (flow)
# ===========================================================================

class FlowDecision(BaseModel):
    """
    Resultado da árvore de decisão pura que determina a ação de sync.
    O campo 'action' é o discriminador; campos adicionais dependem da ação.
    """
    action: Literal["blocked", "in_progress", "no_local_backup", "up_to_date", "upload"] = Field(
        ..., description="Ação decidida pela árvore de decisão"
    )
    code: Optional[str] = Field(None, description="Código de bloqueio (quando action='blocked')")
    backup_type: Optional[str] = Field(None, description="Tipo de backup a enviar: 'full' ou 'fragmento'")
    cycle: Optional[str] = Field(None, description="Identificador do ciclo corrente na nuvem")
    force_full_local: Optional[bool] = Field(None, description="True se precisar gerar full local antes do envio")


# ===========================================================================
# Resposta do Orquestrador de Sync
# ===========================================================================

class SyncResponse(BaseModel):
    """
    Resposta unificada do orquestrador sync(). O campo 'status' indica
    o resultado; campos adicionais variam conforme o status.
    """
    status: str = Field(..., description="Resultado: blocked | in_progress | up_to_date | no_local_backup | skipped | waiting | success | error")
    details: Optional[str] = Field(None, description="Mensagem descritiva ou detalhes da ação")
    code: Optional[str] = Field(None, description="Código de erro da API (quando status='error')")
    http_status: Optional[int] = Field(None, description="Status HTTP da falha (quando status='error')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "details": "Backup enviado e confirmado.",
            }
        }
    }


# ===========================================================================
# Download de Cadeia de Backups
# ===========================================================================

class DownloadChainResponse(BaseModel):
    """
    Resposta do download de cadeia de backups da nuvem. O campo 'status'
    discrimina o resultado; campos adicionais variam.
    """
    status: str = Field(..., description="Resultado: needs_explicit_cycle | no_files | success")
    details: Optional[str] = Field(None, description="Mensagem descritiva")
    ciclo: Optional[str] = Field(None, description="Identificador do ciclo resolvido")
    ordered_files: Optional[List[str]] = Field(None, description="Lista ordenada de arquivos baixados")
    restaura_ate: Optional[str] = Field(None, description="Data limite da restauração (ISO 8601)")
    cadeia_completa: Optional[bool] = Field(None, description="True se a cadeia está completa")
    indisponiveis: Optional[List[str]] = Field(None, description="Arquivos indisponíveis na nuvem")
    total_bytes: Optional[int] = Field(None, description="Tamanho total em bytes dos arquivos baixados")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "ciclo": "2026-08",
                "ordered_files": ["backup_2026-08-01_010000_full.zip", "backup_2026-08-05_010000_incr.zip"],
                "cadeia_completa": True,
                "indisponiveis": [],
            }
        }
    }
    
class PrepareRestoreResponse(BaseModel):
    """
    Resposta do preparo para restauração de backups. O campo 'status'
    indica o resultado; campos adicionais variam.
    """
    status: str = Field(..., description="Resultado: restore_backup_outdated | equals | ready")
    details: Optional[str] = Field(None, description="Mensagem descritiva")
    ciclo: Optional[str] = Field(None, description="Identificador do ciclo resolvido")
    pre_restore_backup: Optional[str] = Field(None, description="backup local usado para comparação (quando status='restore_backup_outdated')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "restore_backup_outdated",
                "details": "O backup local de restauração está desatualizado em relação ao backup restaurado do ciclo.",
                "ciclo": "2026-08",
                "pre_restore_backup": "backup_2026-08-01_010000_full.zip",
            }
        }
    }
    
class ConfirmRestoreResponse(BaseModel):
    status: str = Field(..., description="Resultado: confirmed | error")
    details: Optional[str] = Field(None, description="Mensagem descritiva")
    ciclo: Optional[str] = Field(None, description="Identificador do ciclo resolvido")

# ===========================================================================
# Plano de Download (get_cloud_plan)
# ===========================================================================

class CloudPlanResponse(BaseModel):
    """Resposta do planejamento de download de backups da nuvem."""
    status: Literal["needs_explicit_cycle", "ok"] = Field(
        ..., description="Resultado: 'ok' com plano ou 'needs_explicit_cycle' se ciclo vazio"
    )
    code: Optional[str] = Field(None, description="Código da situação (quando needs_explicit_cycle)")
    details: Optional[str] = Field(None, description="Mensagem descritiva")
    plan: Optional[Dict[str, Any]] = Field(None, description="Plano de download retornado pela API (quando status='ok')")


# ===========================================================================
# Journal de Envios (cloud_journal)
# ===========================================================================

class CicloNuvemInfo(BaseModel):
    """Informações de um ciclo de backup disponível na nuvem (via journal local)."""
    ciclo: str = Field(..., description="Identificador do ciclo (ex: 2026-08)")
    quantidade_backups: int = Field(..., description="Total de arquivos enviados neste ciclo")
    ultimo_envio: str = Field(..., description="Data do último envio confirmado (ISO 8601)")
    arquivos: List[str] = Field(..., description="Nomes dos arquivos enviados")


class JournalEntry(BaseModel):
    """Entrada individual do journal de sincronização com a nuvem."""
    status: str = Field(..., description="Status do envio: pendente | enviando | enviado | falhou | descartado")
    ciclo: Optional[str] = Field(None, description="Identificador do ciclo de backup")
    codigoConteudo: Optional[str] = Field(None, description="Hash SHA-256 do conteúdo do manifest")
    uploadId: Optional[str] = Field(None, description="ID do upload na API")
    expiraEm: Optional[str] = Field(None, description="Data de expiração da URL de upload (ISO 8601)")
    confirmadoEm: Optional[str] = Field(None, description="Data de confirmação do envio (ISO 8601)")
    codigoErro: Optional[str] = Field(None, description="Código de erro (quando status='falhou')")
    observacao: Optional[str] = Field(None, description="Observação adicional")
    atualizado_em: str = Field(..., description="Data da última atualização da entrada (ISO 8601)")
