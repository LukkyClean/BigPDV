import asyncio
import logging
import os

from app.schemas.backup import BackupInfo, SyncResponse

from ._constants import API_BACKUP_STATUS_URL
from ._http import _request, _safe_json
from . import journal
from .flow import CloudSyncError, flow
from .upload import confirm_upload, get_url_upload, send_zip_to_cloud

logger = logging.getLogger(__name__)


async def sync(db) -> SyncResponse:
    # Imports locais evitam importações circulares entre services e core
    from app.core.hwid import obter_hwid
    from app.services import backup as backup_service

    # 1. STATUS + DECISÃO
    response = await _request(db, "GET", API_BACKUP_STATUS_URL)
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"get status falhou ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )
    status = response.json()

    last_backup = await asyncio.to_thread(backup_service.get_last_backup)
    manifest = None
    if last_backup:
        manifest = await asyncio.to_thread(backup_service.load_manifest, last_backup.arquivo)

    decision = flow(status, manifest, last_backup)

    # Ações de PARADA (tudo que não é "upload"): encerra o ciclo.
    if decision.action in ("blocked", "in_progress", "up_to_date", "no_local_backup"):
        logger.info("[SYNC] Ciclo encerrado sem envio: %s", decision)
        return SyncResponse(status=decision.action, details=str(decision.action))

    # 2. RECONCILIAÇÃO: gerar full local se o servidor exige
    if decision.force_full_local:
        logger.info("[SYNC] Servidor exige full; gerando full local forçado.")
        new = await asyncio.to_thread(backup_service.create_backup, True)
        last_backup = BackupInfo(
            arquivo=new.arquivo, criado_em=new.criado_em,
            tamanho_bytes=new.tamanho_bytes, completo=True,
        )
        manifest = await asyncio.to_thread(backup_service.load_manifest, last_backup.arquivo)

    file = last_backup.arquivo
    zip_path = os.path.join(backup_service.LOCAL_BACKUP, file)
    size = os.path.getsize(zip_path)
    content_code = journal.code_content(manifest)  # do MANIFEST, nunca do zip
    hwid = obter_hwid()

    # 3. URL-UPLOAD
    journal.update_journal_entry(file, status=journal.STATUS_PENDENTE,
                                 ciclo=decision.cycle, codigoConteudo=content_code)
    try:
        authorization = await get_url_upload(db, payload={
            "hwid": hwid,
            "tipo": decision.backup_type,
            "ciclo": decision.cycle,
            "tamanhoBytes": size,
            "codigoConteudo": content_code,
            "origem": "AUTOMATICO",
        })
    except CloudSyncError as e:
        # Recusa de negócio: registra e ENCERRA (sem retry).
        journal.update_journal_entry(file, status=journal.STATUS_FALHOU, codigoErro=e.code)
        return SyncResponse(status="error", details=str(e), code=e.code,
                            http_status=e.http_status)

    action_api = authorization.get("acao")
    if action_api == "PULAR":
        # Servidor já tem este conteúdo. NÃO chamar /confirmar (spec §2).
        journal.update_journal_entry(file, status=journal.STATUS_ENVIADO,
                                     observacao="PULAR: conteudo ja na nuvem")
        return SyncResponse(status="skipped", details="Conteúdo já presente na nuvem.")
    if action_api == "AGUARDANDO_OUTRO_TERMINAL":
        return SyncResponse(status="waiting", details="Outro terminal está enviando.")

    upload_id = authorization.get("uploadId")
    journal.update_journal_entry(file, status=journal.STATUS_ENVIANDO,
                                 uploadId=upload_id, expiraEm=authorization.get("expiraEm"))

    # 4. PUT + CONFIRMAR (sempre, nos dois desfechos)
    try:
        await send_zip_to_cloud(authorization["url"], authorization.get("headers", {}), zip_path)
    except CloudSyncError as e:
        # PUT falhou: confirmar ok:false devolve a cota e solta o lock.
        try:
            await confirm_upload(db, payload={
                "uploadId": upload_id, "hwid": hwid, "ok": False, "erro": str(e)[:500],
            })
        except CloudSyncError:
            logger.exception("[SYNC] confirmar(ok=false) também falhou")
        journal.update_journal_entry(file, status=journal.STATUS_FALHOU,
                                     codigoErro=e.code or "PUT_FALHOU")
        return SyncResponse(status="error", details=str(e), code=e.code,
                            http_status=e.http_status)

    confirm = await confirm_upload(db, payload={
        "uploadId": upload_id, "hwid": hwid, "ok": True, "tamanhoBytes": size,
    })
    if confirm.get("confirmado"):
        journal.update_journal_entry(file, status=journal.STATUS_ENVIADO,
                                     confirmadoEm=confirm.get("confirmado_em")
                                     or confirm.get("confirmadoEm"))
        logger.info("[SYNC] Backup %s enviado e confirmado.", file)
        return SyncResponse(status="success", details="Backup enviado e confirmado.")

    journal.update_journal_entry(file, status=journal.STATUS_FALHOU,
                                 codigoErro="CONFIRMAR_NEGADA")
    return SyncResponse(status="error", details="Confirmação negada.", code="CONFIRMAR_NEGADA")
