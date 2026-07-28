# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/checklist_mobile.py
# DESCRICAO: Endpoints para o checklist mobile (formulario web acessado pelo
#            celular via QR code). Combina autenticacao JWT (para gerar token)
#            com autenticacao por token HMAC (para acesso publico ao form).
#
# Rotas:
#   GET  /token/{os_number}            → Gera URL com token HMAC (requer JWT)
#   GET  /dados/{os_number}?token=     → Retorna definicao + dados da OS
#   PUT  /dados/{os_number}?token=     → Atualiza dados_adicionais da OS
# ---------------------------------------------------------------------------

import socket
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.checklist_token import gerar_token_checklist, validar_token_checklist
from app.core.depends import check_permission
from app.core.enum import OrdemServicoStatus
from app.db.crud import ordem_servico as os_crud
from app.db.session import get_db
from app.services import segmentos as segmentos_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChecklistTokenResponse(BaseModel):
    url: str
    token: str


class ChecklistDadosResponse(BaseModel):
    numero_os: str
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    definicao: Optional[Dict[str, Any]] = None
    dados_adicionais: Dict[str, Any] = {}


class ChecklistDadosUpdate(BaseModel):
    dados_adicionais: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_lan_ip() -> str:
    """Descobre o IP da maquina na rede local (mesmo truque do Rust)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _validar_token_ou_403(token: str, os_number: str) -> None:
    """Valida o token HMAC ou lanca HTTP 403."""
    if not token or not validar_token_checklist(token, os_number):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido ou expirado. Gere um novo QR code no sistema.",
        )


# ---------------------------------------------------------------------------
# ROTA 1: Gerar token e URL do checklist (requer JWT)
# ---------------------------------------------------------------------------

@router.get(
    "/token/{os_number}",
    response_model=ChecklistTokenResponse,
    summary="Gerar URL do checklist mobile",
    description=(
        "Gera um token HMAC temporário (8h) e retorna a URL completa para "
        "acesso ao checklist mobile. Requer autenticação JWT."
    ),
)
def gerar_url_checklist(
    request: Request,
    os_number: str = Path(..., description="Número da OS"),
    user_token: dict = Depends(check_permission(required_permission="servico")),
    db: Session = Depends(get_db),
):
    # Verifica se a OS existe
    os_in_db = os_crud.get_ordem_servico_by_numero_os(db, numero_os=os_number)
    if not os_in_db:
        raise HTTPException(status_code=404, detail="OS não encontrada.")

    token = gerar_token_checklist(os_number)

    # Monta a URL usando o IP da LAN e a porta do request
    lan_ip = _get_lan_ip()
    port = request.url.port or 8080
    url = f"http://{lan_ip}:{port}/form/?os={os_number}&token={quote(token, safe='')}"

    return ChecklistTokenResponse(url=url, token=token)


# ---------------------------------------------------------------------------
# ROTA 2: Buscar dados do checklist (autenticado por token HMAC)
# ---------------------------------------------------------------------------

@router.get(
    "/dados/{os_number}",
    response_model=ChecklistDadosResponse,
    summary="Buscar dados do checklist",
    description=(
        "Retorna a definição de campos do segmento e os dados_adicionais "
        "atuais da OS. Autenticado por token HMAC (query param)."
    ),
)
def get_checklist_dados(
    os_number: str = Path(..., description="Número da OS"),
    token: str = Query(..., description="Token HMAC de acesso"),
    db: Session = Depends(get_db),
):
    _validar_token_ou_403(token, os_number)

    os_in_db = os_crud.get_ordem_servico_by_numero_os(db, numero_os=os_number)
    if not os_in_db:
        raise HTTPException(status_code=404, detail="OS não encontrada.")

    # Busca definicao do segmento
    definicao_resp = segmentos_service.get_definicao_campos(db)
    definicao = definicao_resp.get("definicao")

    # Extrai dados do veiculo/objeto
    objeto = os_in_db.objeto
    placa = getattr(objeto, "numero_serie", None) if objeto else None
    marca = getattr(objeto, "marca", None) if objeto else None
    modelo = getattr(objeto, "modelo", None) if objeto else None

    return ChecklistDadosResponse(
        numero_os=os_in_db.numero_os,
        placa=placa,
        marca=marca,
        modelo=modelo,
        definicao=definicao,
        dados_adicionais=os_in_db.dados_adicionais or {},
    )


# ---------------------------------------------------------------------------
# ROTA 3: Atualizar dados do checklist (autenticado por token HMAC)
# ---------------------------------------------------------------------------

@router.put(
    "/dados/{os_number}",
    response_model=ChecklistDadosResponse,
    summary="Atualizar checklist via mobile",
    description=(
        "Faz merge dos dados_adicionais enviados pelo formulário mobile "
        "na OS. Bloqueia se a OS estiver FINALIZADA ou CANCELADA."
    ),
)
def update_checklist_dados(
    payload: ChecklistDadosUpdate,
    os_number: str = Path(..., description="Número da OS"),
    token: str = Query(..., description="Token HMAC de acesso"),
    db: Session = Depends(get_db),
):
    _validar_token_ou_403(token, os_number)

    os_in_db = os_crud.get_ordem_servico_by_numero_os(db, numero_os=os_number)
    if not os_in_db:
        raise HTTPException(status_code=404, detail="OS não encontrada.")

    # Bloqueia OS trancada
    status_bloqueados = {OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA}
    if os_in_db.status in status_bloqueados:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"OS com status {os_in_db.status.value} não pode ser editada.",
        )

    # Merge: preserva dados existentes e atualiza com os novos
    dados_atuais = dict(os_in_db.dados_adicionais or {})
    dados_atuais.update(payload.dados_adicionais)
    os_in_db.dados_adicionais = dados_atuais

    db.commit()
    db.refresh(os_in_db)

    # Retorna o estado atualizado
    objeto = os_in_db.objeto
    placa = getattr(objeto, "numero_serie", None) if objeto else None
    marca = getattr(objeto, "marca", None) if objeto else None
    modelo = getattr(objeto, "modelo", None) if objeto else None

    definicao_resp = segmentos_service.get_definicao_campos(db)

    return ChecklistDadosResponse(
        numero_os=os_in_db.numero_os,
        placa=placa,
        marca=marca,
        modelo=modelo,
        definicao=definicao_resp.get("definicao"),
        dados_adicionais=os_in_db.dados_adicionais or {},
    )
