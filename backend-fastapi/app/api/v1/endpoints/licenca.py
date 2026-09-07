# ---------------------------------------------------------------------------
# ARQUIVO: api/v1/endpoints/licenca.py
# DESCRIÇÃO: Endpoints públicos de verificação de licença.
#            Não requer autenticação (executa antes do login).
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.depends import get_current_master_user
from app.db.session import get_db
from app.schemas.licenca import (
    CobrancaCreate,
    CobrancaRead,
    CobrancaStatusRead,
    LicencaStatusResponse,
    RenovacaoPlanosRead,
)
from app.services import licenca as licenca_service
from app.services import licenca_renovacao as renovacao_service

router = APIRouter()


@router.get(
    "/status",
    response_model=LicencaStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Verifica se a licença está ativa",
    responses={
        403: {
            "description": "Licença inválida, expirada ou requer conexão",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "codigo": "REQUISITA_CONEXAO_INTERNET",
                            "mensagem": "Conecte-se à internet para revalidar.",
                        }
                    }
                }
            },
        }
    },
)
def verificar_status_licenca(db: Session = Depends(get_db)):
    """
    Endpoint público (sem autenticação) chamado pelo frontend
    a cada inicialização para verificar a validade da licença.

    - **200**: Licença válida (online ou offline).
    - **403**: Licença inválida com código de erro estruturado.
    """
    from app.db.crud import empresa as empresa_crud
    from app.services.plano import RECURSO_NFE, plano_tem_recurso

    resultado = licenca_service.verificar_licenca_ativa(db)

    # Recursos contratados viajam junto com o status porque o router do
    # frontend já chama este endpoint a cada 5 minutos — hidratar o store daqui
    # não custa requisição nenhuma, e funciona antes do login, então a UI nunca
    # pisca mostrando um módulo que o cliente não tem.
    #
    # Instalação é singleton (uma empresa por banco), então a empresa atual é a
    # única que existe. Sem ela, só o claim do JWT decide.
    empresa = empresa_crud.get_empresa_atual(db)
    resultado["recursos"] = {
        RECURSO_NFE: plano_tem_recurso(
            db, RECURSO_NFE, empresa_id=empresa.id if empresa else None,
        ),
    }
    return resultado


@router.post(
    "/desconectar",
    status_code=status.HTTP_200_OK,
    summary="Desconecta um terminal da licença na API StartBig",
)
async def desconectar_licenca(
    hwid: str = Query(..., max_length=255, description="Hardware ID do terminal"),
    db: Session = Depends(get_db),
):
    """
    Endpoint público chamado no encerramento da aplicação ou logout.
    Remove o terminal de terminais_conectados e notifica a API StartBig.

    Aceita HWID via query parameter para compatibilidade com sendBeacon.
    Sempre retorna 200 — falhas de rede são tratadas internamente.
    """
    return await licenca_service.desconectar_terminal(db, hwid)


# ===========================================================================
# RENOVACAO DE ASSINATURA (PIX e cartao)
#
# Diferente das rotas acima, estas exigem MASTER: e a conta e o dinheiro do
# dono. E, tambem diferente delas, rodam depois do login -- com a licenca
# vencida o usuario entra, o sistema fica inativo e so a cobranca funciona.
# ===========================================================================


@router.get(
    "/renovacao/periodos",
    response_model=RenovacaoPlanosRead,
    status_code=status.HTTP_200_OK,
    summary="Periodos que esta licenca pode renovar",
    description=(
        "Preco e periodos vem do servidor — nada e decidido aqui. "
        "Responde `disponivel=false` (sem erro) enquanto a API de cobranca nao "
        "estiver no ar, para a tela mostrar 'indisponivel' em vez de quebrar."
    ),
)
def listar_periodos_renovacao(
    user_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
):
    return renovacao_service.listar_periodos(db)


@router.post(
    "/renovacao/cobranca",
    response_model=CobrancaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar cobranca de renovacao (PIX ou cartao)",
    description=(
        "PIX devolve o copia-e-cola (o app desenha o QR). Cartao devolve a URL "
        "do checkout, para o app abrir no navegador — cartao nao e processado "
        "dentro do sistema."
    ),
)
def criar_cobranca_renovacao(
    payload: CobrancaCreate,
    user_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
):
    return renovacao_service.criar_cobranca(db, payload.metodo, payload.periodo)


@router.get(
    "/renovacao/cobranca/{cobranca_id}",
    response_model=CobrancaStatusRead,
    status_code=status.HTTP_200_OK,
    summary="Status da cobranca",
    description=(
        "Consultado a cada poucos segundos com a tela de pagamento aberta. "
        "Quando o servidor responde PAGA, este backend ja revalida a licenca "
        "antes de responder: `licenca_renovada=true` significa que o vencimento "
        "novo JA esta gravado nesta maquina."
    ),
)
def consultar_cobranca_renovacao(
    cobranca_id: str = Path(..., max_length=120, description="ID devolvido ao criar a cobranca"),
    user_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
):
    return renovacao_service.consultar_cobranca(db, cobranca_id)


@router.post(
    "/renovacao/revalidar",
    status_code=status.HTTP_200_OK,
    summary="Forcar a revalidacao da licenca agora",
    description=(
        "Atalho para quem pagou e nao quer esperar o loop de uma hora. "
        "Devolve `{renovada: true}` quando o vencimento gravado mudou."
    ),
)
def revalidar_licenca_agora(
    user_token: dict = Depends(get_current_master_user),
    db: Session = Depends(get_db),
):
    return {"renovada": renovacao_service.revalidar_agora(db)}

