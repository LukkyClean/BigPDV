# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/terminal.py
# DESCRIÇÃO: Cadastro dos terminais da loja — nome e papel por máquina.
# ---------------------------------------------------------------------------

from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.orm import Session

from app.core.depends import _handle_db_transaction, check_permission
from app.db.session import get_db
from app.schemas.terminal import TerminalEsteRead, TerminalRead, TerminalUpdate
from app.services import terminal as terminal_service

router = APIRouter()

# A mesma permissão do caixa, pela mesma razão: quem opera o balcão precisa
# saber se a máquina dele é um caixa. A trava de quem pode CONFIGURAR é outra e
# mora no service (visão gerencial) — permissão diz "pode ver esta área",
# hierarquia diz "pode mexer na loja inteira".
PERMISSAO = "view_sales"


@router.get(
    "/",
    response_model=List[TerminalRead],
    status_code=status.HTTP_200_OK,
    summary="Os terminais cadastrados da loja (visão gerencial)",
)
def listar_terminais(
    x_terminal_hwid: Optional[str] = Header(None, alias="X-Terminal-HWID"),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, terminal_service.garantir_e_listar, usuario_token, x_terminal_hwid
    )


@router.get(
    "/este",
    response_model=Optional[TerminalEsteRead],
    status_code=status.HTTP_200_OK,
    summary="Quem é ESTA máquina (null se ainda não cadastrada)",
)
def get_este_terminal(
    x_terminal_hwid: Optional[str] = Header(
        None,
        alias="X-Terminal-HWID",
        description="HWID desta máquina — o mesmo enviado no login",
    ),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    """Devolve `null` em vez de 404 quando a máquina não está cadastrada.

    "Não sei quem é esta máquina" é resposta normal — acontece no intervalo
    entre a atualização e o primeiro login — e a tela trata isso como "sou um
    caixa", que é o lado seguro.
    """
    return _handle_db_transaction(
        db, terminal_service.get_este_terminal, usuario_token, x_terminal_hwid
    )


@router.patch(
    "/{terminal_id}",
    response_model=TerminalRead,
    status_code=status.HTTP_200_OK,
    summary="Batiza a máquina e define o papel dela",
)
def atualizar_terminal(
    dados: TerminalUpdate,
    terminal_id: int = Path(..., description="ID do terminal"),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, terminal_service.atualizar, usuario_token, terminal_id, dados
    )
