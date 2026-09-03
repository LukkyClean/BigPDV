# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/inutilizacao.py
# DESCRIÇÃO: Detecção de buracos na numeração e inutilização de faixas.
#
# Desde que a emissão parou de devolver o número ao contador em caso de falha
# (achado C3), buraco na sequência passou a ser um resultado esperado — é o
# preço de nunca arriscar Rejeição 204 por duplicidade.
#
# A contrapartida é esta: a SEFAZ exige que os números reservados e não usados
# sejam formalmente declarados como inutilizados. Sem isso a empresa acumula
# lacunas e fica irregular perante o fisco.
# ---------------------------------------------------------------------------

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.crud import fiscal as crud
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.inutilizacao_fiscal import InutilizacaoFiscal

logger = logging.getLogger(__name__)


JUSTIFICATIVA_MINIMA = 15

# Um número só é considerado consumido de verdade nestes estados.
# INDETERMINADA entra aqui de propósito: enquanto não sabemos se a nota foi
# autorizada, inutilizar o número seria declarar à SEFAZ que ele não foi usado
# — e ele pode ter sido.
_STATUS_QUE_CONSOMEM_NUMERO = (
    "AUTORIZADA", "CANCELADA", "PROCESSANDO", "PENDENTE", "INDETERMINADA",
)


def _agrupar_em_faixas(numeros: list[int]) -> list[tuple[int, int]]:
    """[3, 4, 5, 9, 11, 12] -> [(3, 5), (9, 9), (11, 12)]"""
    if not numeros:
        return []

    ordenados = sorted(set(numeros))
    faixas: list[tuple[int, int]] = []
    inicio = anterior = ordenados[0]

    for n in ordenados[1:]:
        if n == anterior + 1:
            anterior = n
            continue
        faixas.append((inicio, anterior))
        inicio = anterior = n

    faixas.append((inicio, anterior))
    return faixas


def listar_gaps_numeracao(db: Session, empresa_id: int) -> list[dict]:
    """
    Lista as faixas de numeração que precisam ser inutilizadas.

    Um número entra na lista quando:
      - está abaixo do contador (já foi reservado), e
      - nenhum documento vivo o ocupa, e
      - ainda não há inutilização registrada cobrindo ele.
    """
    fs = crud.get_fiscal_settings(db, empresa_id)
    if not fs or fs.ultimo_numero_nfe < 1:
        return []

    serie = fs.serie_nfe
    ultimo = fs.ultimo_numero_nfe

    ocupados = {
        n for (n,) in db.query(DocumentoFiscal.numero_documento).filter(
            DocumentoFiscal.tipo_documento == "NFE",
            DocumentoFiscal.serie == serie,
            DocumentoFiscal.numero_documento.isnot(None),
            DocumentoFiscal.status.in_(_STATUS_QUE_CONSOMEM_NUMERO),
        ).all()
    }

    # Faixas já declaradas (ou em declaração) não voltam para a lista.
    ja_tratados: set[int] = set()
    for inut in db.query(InutilizacaoFiscal).filter(
        InutilizacaoFiscal.empresa_id == empresa_id,
        InutilizacaoFiscal.serie == serie,
        InutilizacaoFiscal.status.in_(("PENDENTE", "PROCESSANDO", "HOMOLOGADA", "INDETERMINADA")),
    ).all():
        ja_tratados.update(range(inut.numero_inicial, inut.numero_final + 1))

    buracos = [
        n for n in range(1, ultimo + 1)
        if n not in ocupados and n not in ja_tratados
    ]

    return [
        {
            "serie": serie,
            "numero_inicial": inicio,
            "numero_final": fim,
            "quantidade": fim - inicio + 1,
        }
        for inicio, fim in _agrupar_em_faixas(buracos)
    ]


def _validar_faixa(
    db: Session, empresa_id: int, serie: int, inicial: int, final: int
) -> None:
    """Recusa faixas malformadas ou que contenham número realmente usado."""
    if inicial < 1 or final < inicial:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Faixa inválida: {inicial} a {final}.",
        )

    fs = crud.get_fiscal_settings(db, empresa_id)
    if not fs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configurações fiscais não cadastradas para esta empresa.",
        )

    if final > fs.ultimo_numero_nfe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Não é possível inutilizar até {final}: o contador da série "
                f"{serie} está em {fs.ultimo_numero_nfe}. Só números já "
                f"reservados podem ser inutilizados."
            ),
        )

    conflito = db.query(DocumentoFiscal).filter(
        DocumentoFiscal.tipo_documento == "NFE",
        DocumentoFiscal.serie == serie,
        DocumentoFiscal.numero_documento >= inicial,
        DocumentoFiscal.numero_documento <= final,
        DocumentoFiscal.status.in_(_STATUS_QUE_CONSOMEM_NUMERO),
    ).first()

    if conflito:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "codigo": "NUMERO_EM_USO",
                "mensagem": (
                    f"O número {conflito.numero_documento} da faixa está ocupado por "
                    f"um documento em estado {conflito.status}. Inutilizar declararia "
                    f"à SEFAZ que ele não foi usado."
                ),
                "documento_id": conflito.id,
            },
        )


def solicitar_inutilizacao(
    db: Session,
    empresa_id: int,
    serie: int,
    numero_inicial: int,
    numero_final: int,
    justificativa: str,
) -> InutilizacaoFiscal:
    """Registra e transmite um pedido de inutilização de faixa."""
    justificativa = (justificativa or "").strip()
    if len(justificativa) < JUSTIFICATIVA_MINIMA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"A justificativa deve ter ao menos {JUSTIFICATIVA_MINIMA} "
                f"caracteres (a SEFAZ exige)."
            ),
        )

    _validar_faixa(db, empresa_id, serie, numero_inicial, numero_final)

    fs = crud.get_fiscal_settings(db, empresa_id)
    ano = datetime.now(timezone.utc).year

    registro = InutilizacaoFiscal(
        empresa_id=empresa_id,
        modelo=55,
        serie=serie,
        ano=ano,
        numero_inicial=numero_inicial,
        numero_final=numero_final,
        justificativa=justificativa,
        status="PROCESSANDO",
        ref_api=f"inut-{serie}-{numero_inicial}-{numero_final}-{ano}",
        idempotency_key=str(uuid.uuid4()),
        ambiente_emissao=fs.ambiente_emissao,
        data_solicitacao=datetime.now(timezone.utc),
    )
    db.add(registro)
    db.flush()

    from .http import get_fiscal_client

    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fs.ambiente_emissao, token)

    payload = {
        "modelo": 55,
        "serie": serie,
        "ano": ano,
        "numero_inicial": numero_inicial,
        "numero_final": numero_final,
        "justificativa": justificativa,
    }

    try:
        resultado = client.inutilizar_numeracao(
            registro.ref_api, payload, idempotency_key=registro.idempotency_key,
        )
        _aplicar_resultado_inutilizacao(registro, resultado)
    except NotImplementedError as e:
        registro.status = "REJEITADA"
        registro.mensagem_sefaz = str(e)
    except Exception as e:
        # Mesma regra da emissão: sem resposta não é recusa. Manter
        # INDETERMINADA impede que a faixa volte para a lista de gaps e seja
        # solicitada duas vezes.
        logger.error("[FISCAL] Falha ao inutilizar faixa %s: %s", registro.ref_api, e)
        registro.status = "INDETERMINADA"
        registro.mensagem_sefaz = (
            f"Não foi possível confirmar a inutilização junto à SEFAZ: {str(e)[:300]}."
        )

    return registro


def _aplicar_resultado_inutilizacao(registro: InutilizacaoFiscal, resultado: dict) -> None:
    """Traduz a resposta da API para o registro local."""
    status_api = resultado.get("status", "")

    if status_api in ("homologado", "autorizado"):
        registro.status = "HOMOLOGADA"
        registro.data_homologacao = datetime.now(timezone.utc)
    elif status_api == "processando":
        registro.status = "PROCESSANDO"
    else:
        registro.status = "REJEITADA"

    registro.protocolo = resultado.get("protocolo")
    registro.codigo_status_sefaz = resultado.get("codigo_sefaz")
    registro.mensagem_sefaz = resultado.get("mensagem_sefaz")
    registro.url_xml = resultado.get("url_xml")


def listar_inutilizacoes(db: Session, empresa_id: int) -> list[InutilizacaoFiscal]:
    return (
        db.query(InutilizacaoFiscal)
        .filter(InutilizacaoFiscal.empresa_id == empresa_id)
        .order_by(InutilizacaoFiscal.data_criacao.desc())
        .all()
    )
