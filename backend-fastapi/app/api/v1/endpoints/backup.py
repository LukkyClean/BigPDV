# ---------------------------------------------------------------------------
# ACESSO: TODAS as rotas sao EXCLUSIVAS do Master -> get_current_master_user.
#
# Nao afrouxar para get_current_active_user. `/download/{ciclo}` entrega o banco
# INTEIRO da empresa, e `/confirmar-restauracao` agenda a troca do arquivo do
# banco de producao no proximo boot. Com o backend escutando em 0.0.0.0, um
# funcionario logado de qualquer terminal alcancaria as duas coisas.
# ---------------------------------------------------------------------------

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.core.depends import get_current_master_user, _handle_db_transaction
from app.db.session import get_db
from app.schemas.backup import (
    BackupCriadoComCota,
    BackupInfo,
    CicloNuvemInfo,
    ConfirmRestoreResponse,
    DownloadChainResponse,
    PrepareRestoreResponse,
)
from app.schemas.configuracao_backup import ConfiguracaoBackupRead, ConfiguracaoBackupUpdate
from app.services import backup as backup_service
from app.services.cloud import journal as cloud_journal
from app.services.cloud import download as cloud_download
from app.services import configuracao_backup as configuracao_backup_service

router = APIRouter()

LIMITE_BACKUP_MANUAL_DIARIO = 2


@router.get(
    "/",
    response_model=list[BackupInfo],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os backups locais",
)
def listar_backups(
    usuario_token: dict = Depends(get_current_master_user),
):
    return backup_service.list_backups()


@router.get(
    "/ultimo",
    response_model=BackupInfo,
    status_code=status.HTTP_200_OK,
    summary="Obter informações do último backup",
    responses={204: {"description": "Nenhum backup encontrado"}},
)
def ultimo_backup(
    usuario_token: dict = Depends(get_current_master_user),
):
    ultimo = backup_service.get_last_backup()
    if ultimo is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return ultimo


@router.post(
    "/criar",
    response_model=BackupCriadoComCota,
    status_code=status.HTTP_201_CREATED,
    summary="Criar backup manual",
)
async def criar_backup(
    usuario_token: dict = Depends(get_current_master_user),
):
    backups_hoje = backup_service.count_backups_today()

    if backups_hoje >= LIMITE_BACKUP_MANUAL_DIARIO:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="LIMITE_BACKUP_DIARIO",
        )

    try:
        criado = await asyncio.to_thread(backup_service.create_backup)
    except backup_service.BackupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    restantes = max(0, LIMITE_BACKUP_MANUAL_DIARIO - backups_hoje - 1)

    return BackupCriadoComCota(
        arquivo=criado.arquivo,
        criado_em=criado.criado_em,
        tamanho_bytes=criado.tamanho_bytes,
        backups_restantes_hoje=restantes,
    )


@router.get(
    "/configuracao",
    response_model=ConfiguracaoBackupRead,
    status_code=status.HTTP_200_OK,
    summary="Buscar configurações de backup",
)
def get_configuracao_backup(
    usuario_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
):
    empresa_id = int(usuario_token.get("empresa_id"))
    return _handle_db_transaction(
        db,
        configuracao_backup_service.get_or_create_configuracao_backup,
        empresa_id,
    )


@router.put(
    "/configuracao",
    response_model=ConfiguracaoBackupRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar configurações de backup",
)
def update_configuracao_backup(
    data: ConfiguracaoBackupUpdate,
    usuario_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
):
    empresa_id = int(usuario_token.get("empresa_id"))
    return _handle_db_transaction(
        db,
        configuracao_backup_service.update_configuracao_backup,
        empresa_id,
        data,
    )


@router.get(
    "/ciclos-nuvem",
    response_model=list[CicloNuvemInfo],
    status_code=status.HTTP_200_OK,
    summary="Listar ciclos de backup disponíveis na nuvem (via journal local)",
)
def listar_ciclos_nuvem(
    usuario_token: dict = Depends(get_current_master_user),
):
    return cloud_journal.get_ciclos_enviados()


@router.get(
    "/download/{ciclo}",
    response_model=DownloadChainResponse,
    status_code=status.HTTP_200_OK,
    summary="Baixa e restaura cadeia de backups da nuvem",
)
async def backup_download(
    usuario_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
    *,
    ciclo: str = Path(..., description="ID do ciclo de backup a ser baixado"),
):
    return await cloud_download.download_chain(db, ciclo)


@router.post(
    "/preparar-restauracao/{ciclo}",
    response_model=PrepareRestoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Preparar restauração de backup",
)
def preparar_restauracao(
    usuario_token: dict = Depends(get_current_master_user),
    *,
    ciclo: str = Path(..., description="ID do ciclo de backup"),
):
    try:
        return backup_service.prepare_restore(ciclo)
    except backup_service.BackupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/confirmar-restauracao/{ciclo}",
    response_model=ConfirmRestoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirmar restauração de backup",
)
def confirmar_restauracao(
    usuario_token: dict = Depends(get_current_master_user),
    *,
    ciclo: str = Path(..., description="ID do ciclo de backup"),
    pre_restore_backup: str,
):
    try:
        return backup_service.confirm_restore(ciclo, pre_restore_backup)
    except backup_service.BackupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
