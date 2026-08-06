import asyncio
import logging
import os
from typing import Any, Dict, Optional
 
import httpx
 
from app.services.backup import save_backup 
from app.services import cloud_journal as journal
 
logger = logging.getLogger(__name__)
 
API_BASE = "https://api.startbig.com.br"
API_BACKUP_STATUS_URL = f"{API_BASE}/erp/backup/status"
API_BACKUP_URL_UPLOAD = f"{API_BASE}/erp/backup/url-upload"
API_BACKUP_CONFIRMAR = f"{API_BASE}/erp/backup/confirmar"
API_BACKUP_DOWNLOAD = f"{API_BASE}/erp/backup/url-download"
 
API_TIMEOUT = httpx.Timeout(connect=10.0, read=15.0, write=15.0, pool=5.0)
# read/write generosos: o PUT sobe zips que podem ter centenas de MB.
PUT_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=600.0, pool=5.0)
GET_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=15.0, pool=5.0)
 
 
class CloudSyncError(Exception):
    """Erro do sincronizador. `code` carrega o código da API quando houver."""
 
    def __init__(self, message: str, code: Optional[str] = None,
                 http_status: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
 
 
def _client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    # Fábrica isolada para os testes substituírem por um MockTransport.
    return httpx.AsyncClient(timeout=timeout)
 
 
def _get_license_token(db) -> Optional[str]:
    from app.db.crud import configuracao_licenca as license_crud
    license = license_crud.get_licenca(db)
    return license.token if license else None
 
 
async def _renew_license(db) -> None:
    # 401 -> reusa a rotina de renovação que já existe no módulo de licença.
    from app.services.licenca import renovar_licenca_background
    await renovar_licenca_background(db)
 
 
def _safe_json(response: httpx.Response) -> dict:
    # Corpo JSON ou {} — evita que um corpo não-JSON vire segunda exceção.
    try:
        return response.json()
    except Exception:
        return {}
 
 
async def _request(db, method: str, url: str,
                   payload: Optional[dict] = None) -> httpx.Response:
    """
    Chamada autenticada com a política de 401: renova o token UMA vez e
    repete UMA vez. Qualquer outra resposta volta ao chamador para ser
    tratada pelo `codigo`. Falha de rede vira CloudSyncError sem code.
    """
    response: Optional[httpx.Response] = None
    for attempt in (1, 2):
        token = _get_license_token(db)
        if not token:
            raise CloudSyncError("Licença sem token válido - sync adiado.")
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with _client(API_TIMEOUT) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, json=payload, headers=headers)
        except httpx.RequestError as e:
            raise CloudSyncError(f"Falha de rede em {url}: {e}") from e
 
        if response.status_code == 401 and attempt == 1:
            logger.info("[SYNC] 401 - renovando token e repetindo uma vez.")
            await _renew_license(db)
            continue
        return response
    return response
 
 
# ===========================================================================
# ÁRVORE DE DECISÃO — função PURA (sem rede, sem disco): 100% testável
# ===========================================================================
 
def flow(status: Dict[str, Any], last_manifest: Optional[dict],
         last_local_backup: Optional[dict]) -> Dict[str, Any]:
    """
    Implementa o §2 da spec, na ordem exata.
    Ações: blocked | in_progress | up_to_date | no_local_backup | upload
    """
    # 1. plano permite backup em nuvem?
    if not status.get("planoPermiteBackup", False):
        return {"action": "blocked", "code": status.get("codigoBloqueio", "unknown")}
 
    # 2. outra máquina enviando? (resposta normal)
    if status.get("envioEmAndamento", False):
        return {"action": "in_progress"}
 
    # sem backup local ainda: não há O QUE enviar (ação de parada própria,
    # NÃO "upload" — senão o sync tentaria enviar o que não existe).
    if last_manifest is None or last_local_backup is None:
        return {"action": "no_local_backup"}
 
    # 3. PULAR ANTECIPADO: compara o codigoConteudo do último elo da nuvem
    #    com o do nosso manifest, ANTES de qualquer escrita.
    #    §5b: `corrente` pode vir vazia (ciclo novo aberto com PULAR); sem
    #    termo de comparação, seguimos e deixamos o servidor decidir.
    chain = status.get("corrente") or []
    if chain:
        cloud_code = chain[-1].get("codigoConteudo")
        if cloud_code and cloud_code == journal.code_content(last_manifest):
            return {"action": "up_to_date"}
 
    # 4. full ou fragmento? Decisão do SERVIDOR.
    #    spec: fullDoCicloConfirmado == False  => próximo envio é FULL.
    backup_type = "full" if not status.get("fullDoCicloConfirmado", False) else "fragmento"
 
    decision: Dict[str, Any] = {"action": "upload", "backup_type": backup_type,
                                "cycle": status.get("cicloCorrente")}
 
    # RECONCILIAÇÃO: servidor quer full e o backup local mais recente NÃO é
    # full -> gerar um full local antes de enviar.
    is_full_local = last_local_backup.get("completo", False)
    if backup_type == "full" and not is_full_local:
        decision["force_full_local"] = True
 
    return decision
 
 
# ===========================================================================
# TRÍADE DE ENVIO
# ===========================================================================
 
async def get_url_upload(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = await _request(db, "POST", API_BACKUP_URL_UPLOAD, payload)
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"url-upload recusado ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )
    return response.json()
 
 
def _read_zip(filepath: str) -> bytes:
    """
    Lê o zip INTEIRO em memória — deliberado. Streaming (data=open) ativa
    chunked encoding e omite o Content-Length, que está DENTRO da assinatura
    da presigned URL -> 403 SignatureDoesNotMatch. f.read() garante o header.
    """
    if not os.path.exists(filepath):
        raise CloudSyncError(f"Arquivo de backup não encontrado: {filepath}")
    with open(filepath, "rb") as f:
        return f.read()
 
 
async def send_zip_to_cloud(url: str, headers: Dict[str, str],
                            filepath: str) -> None:
    # Leitura de disco pesada roda em thread para não travar o event loop.
    content = await asyncio.to_thread(_read_zip, filepath)
    try:
        async with _client(PUT_TIMEOUT) as client:
            response = await client.put(url, headers=headers, content=content)
    except httpx.RequestError as e:
        raise CloudSyncError(f"Falha de rede no PUT para {url}: {e}") from e
    if response.status_code != 200:
        raise CloudSyncError(
            f"PUT ao R2 falhou ({response.status_code}): {response.text[:200]}",
            http_status=response.status_code,
        )
 
 
async def confirm_upload(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = await _request(db, "POST", API_BACKUP_CONFIRMAR, payload)
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"confirmar recusado ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )
    return response.json()
 
 
# ===========================================================================
# ORQUESTRADOR
# ===========================================================================
 
async def sync(db) -> Dict[str, Any]:
    from app.core.hwid import obter_hwid            # mesmo hwid da licença
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
        
        manifest = await asyncio.to_thread(
            backup_service._load_manifest, last_backup["arquivo"]
        )
 
    decision = flow(status, manifest, last_backup)
 
    # Ações de PARADA (tudo que não é "upload"): encerra o ciclo.
    if decision["action"] in ("blocked", "in_progress", "up_to_date", "no_local_backup"):
        logger.info("[SYNC] Ciclo encerrado sem envio: %s", decision)
        return {"status": decision["action"], "details": decision}
 
    # 2. RECONCILIAÇÃO: gerar full local se o servidor exige
    if decision.get("force_full_local"):
        logger.info("[SYNC] Servidor exige full; gerando full local forçado.")
        new = await asyncio.to_thread(backup_service.create_backup, True)
        last_backup = {"arquivo": new["arquivo"], "completo": True}
        manifest = await asyncio.to_thread(
            backup_service._load_manifest, last_backup["arquivo"]
        )
 
    file = last_backup["arquivo"]
    zip_path = os.path.join(backup_service.LOCAL_BACKUP, file)
    size = os.path.getsize(zip_path)
    content_code = journal.code_content(manifest)   # do MANIFEST, nunca do zip
    hwid = obter_hwid()
 
    # 3. URL-UPLOAD
    journal.update_journal_entry(file, status=journal.STATUS_PENDENTE,
                                 ciclo=decision["cycle"], codigoConteudo=content_code)
    try:
        authorization = await get_url_upload(db, payload={
            "hwid": hwid,
            "tipo": decision["backup_type"],
            "ciclo": decision["cycle"],
            "tamanhoBytes": size,
            "codigoConteudo": content_code,
            "origem": "AUTOMATICO",
        })
    except CloudSyncError as e:
        # Recusa de negócio: registra e ENCERRA (sem retry).
        journal.update_journal_entry(file, status=journal.STATUS_FALHOU, codigoErro=e.code)
        return {"status": "error", "details": str(e), "code": e.code,
                "http_status": e.http_status}
 
    action_api = authorization.get("acao")
    if action_api == "PULAR":
        # Servidor já tem este conteúdo. NÃO chamar /confirmar (spec §2).
        journal.update_journal_entry(file, status=journal.STATUS_ENVIADO,
                                     observacao="PULAR: conteudo ja na nuvem")
        return {"status": "skipped", "details": "Conteúdo já presente na nuvem."}
    if action_api == "AGUARDANDO_OUTRO_TERMINAL":
        return {"status": "waiting", "details": "Outro terminal está enviando."}
 
    upload_id = authorization.get("uploadId")
    journal.update_journal_entry(file, status=journal.STATUS_ENVIANDO,
                                 uploadId=upload_id, expiraEm=authorization.get("expiraEm"))
 
    # 4. PUT + CONFIRMAR (sempre, nos dois desfechos)
    try:
        await send_zip_to_cloud(authorization["url"],
                                authorization.get("headers", {}), zip_path)
    except CloudSyncError as e:
        # PUT falhou: confirmar ok:false devolve a cota e solta o lock.
        try:
            await confirm_upload(db, payload={
                "uploadId": upload_id, "hwid": hwid, "ok": False,
                "erro": str(e)[:500],
            })
        except CloudSyncError:
            logger.exception("[SYNC] confirmar(ok=false) também falhou")
        # Marca falha nos DOIS desfechos do confirmar (fora do except interno).
        journal.update_journal_entry(file, status=journal.STATUS_FALHOU,
                                     codigoErro=e.code or "PUT_FALHOU")
        return {"status": "error", "details": str(e), "code": e.code,
                "http_status": e.http_status}
 
    confirm = await confirm_upload(db, payload={
        "uploadId": upload_id, "hwid": hwid, "ok": True, "tamanhoBytes": size,
    })
    if confirm.get("confirmado"):
        journal.update_journal_entry(file, status=journal.STATUS_ENVIADO,
                                     confirmadoEm=confirm.get("confirmado_em")
                                     or confirm.get("confirmadoEm"))
        logger.info("[SYNC] Backup %s enviado e confirmado.", file)
        return {"status": "success", "details": "Backup enviado e confirmado."}
 
    journal.update_journal_entry(file, status=journal.STATUS_FALHOU,
                                 codigoErro="CONFIRMAR_NEGADA")
    return {"status": "error", "details": "Confirmação negada.", "code": "CONFIRMAR_NEGADA"}

async def get_cloud_plan(db, cycle: str) -> Dict[str, Any]:
    from app.core.hwid import obter_hwid
    
    payload: Dict[str, Any] = {"hwid": obter_hwid(),}
    if cycle:
        payload["ciclo"] = cycle
    
    response = await _request(db, "POST", API_BACKUP_DOWNLOAD, payload=payload)
    
    if response.status_code == 404:
        body = _safe_json(response)
        if body.get("codigo") == "BACKUP_INEXISTENTE" and not cycle:
            # §5b: nada NESTE ciclo, mas pode haver em ciclo anterior.
            return {"status": "needs_explicit_cycle",
                    "code": "BACKUP_INEXISTENTE",
                    "details": "Ciclo corrente vazio; reconsultar com ciclo explícito."}
        raise CloudSyncError(
            f"url-download 404: {body.get('codigo')}",
            code=body.get("codigo"), http_status=404,
        )
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"url-download falhou ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )
 
    plan = response.json()
    return {"status": "ok", "plan": plan}
 
async def download_chain(db, cycle: Optional[str] = None) -> Dict[str, Any]:
    from app.services import backup as backup_service

    planned = await get_cloud_plan(db, cycle)
    
    if planned["status"] == "needs_explicit_cycle":
        return {"status": "needs_explicit_cycle", "details": planned["details"]}
    
    plan = planned["plan"]
    files = plan.get("arquivos", [])
    resolved_cycle = plan.get("ciclo") or cycle
    
    if not files:
        return {"status": "no_files", "details": "Nenhum backup disponível na nuvem para este ciclo.", "ciclo": resolved_cycle}
    
    ordered_files: list[str] = []

    async with _client(GET_TIMEOUT) as client:
        for fileinfo in files:
            url = fileinfo.get("url")
            chave = fileinfo.get("chave", "")
            filename = os.path.basename(chave) or fileinfo.get("arquivo", "")
            
            try:
                download_response = await client.get(url)
            except httpx.RequestError as e:
                raise CloudSyncError(f"Falha de rede no GET para {url}: {e}") from e
            
            if download_response.status_code != 200:
                raise CloudSyncError(
                    f"Download de {filename} falhou ({download_response.status_code}).",
                    http_status=download_response.status_code,
                )
            
            await asyncio.to_thread(backup_service.save_backup, cycle, filename, download_response.content)
            ordered_files.append(filename)
            
    await asyncio.to_thread(backup_service.restore_from_chain, cycle, ordered_files)
    return {
        "status": "success",
        "ciclo": resolved_cycle,
        "ordered_files": ordered_files,
        "restaura_ate": plan.get("restauraAte"),
        "cadeia_completa": plan.get("cadeiaCompleta", False),
        "indisponiveis": plan.get("indisponiveis", []),
        "total_bytes": plan.get("totalBytes"),
    }
    
