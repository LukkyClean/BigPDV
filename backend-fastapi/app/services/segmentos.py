# ---------------------------------------------------------------------------
# ARQUIVO: app/services/segmentos.py
# DESCRICAO: Regras de negocio ligadas ao segmento da empresa.
#
#            Responsavel por:
#              - descobrir o segmento da instalacao (empresa single-tenant);
#              - validar os dados dinamicos (dados_adicionais) conforme o
#                segmento, de forma GATED: se o segmento nao tiver regra
#                especifica (ex: informatica/assistencia_tecnica), NADA e
#                validado aqui e o comportamento existente permanece intacto.
#
#            Regra do projeto: informatica ja esta em producao. A validacao de
#            veiculo (placa) SO roda quando o segmento e oficina_mecanica.
# ---------------------------------------------------------------------------

import re
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.crud import empresa as empresa_crud
from app.core import segmentos as reg


def get_segmento_atual(db: Session) -> Optional[str]:
    """Retorna o segmento da empresa da instalacao, ou None se nao houver."""
    empresa = empresa_crud.get_empresa_atual(db)
    return empresa.segmento if empresa else None


def get_definicao_campos(db: Session) -> Dict[str, Any]:
    """
    Monta o contrato de campos dinamicos do segmento atual, para o frontend
    renderizar o formulario de OS/objeto adequado.

    Sempre retorna um dicionario. Quando o segmento nao possui definicao
    dedicada, `tem_definicao=False` e o frontend usa o formulario generico.
    """
    segmento = get_segmento_atual(db)
    definicao = reg.get_definicao_segmento(segmento)
    return {
        "segmento": segmento,
        "tem_definicao": definicao is not None,
        "definicao": definicao,
    }


def normalizar_placa(valor: str) -> str:
    """Normaliza uma placa para validacao/armazenamento: remove espacos/hifens
    e coloca em maiusculo. Ex: 'abc-1d23' -> 'ABC1D23'."""
    return re.sub(r"[\s\-]", "", (valor or "")).upper()


def placa_valida(valor: str) -> bool:
    """True se a placa (apos normalizar) casar com o padrao antigo ou Mercosul."""
    return bool(re.match(reg.PLACA_REGEX, normalizar_placa(valor)))


def validar_objeto_por_segmento(
    db: Session,
    numero_serie: Optional[str],
    dados_adicionais: Optional[Dict[str, Any]],
) -> None:
    """
    Valida os dados do objeto de servico conforme o segmento da empresa.

    - Segmento SEM definicao dedicada (informatica, mercado, etc.): no-op.
    - Segmento oficina_mecanica: exige placa valida (o `numero_serie` do
      objeto e a placa do veiculo).

    Lanca HTTP 422 quando invalido. Nao levanta nada quando nao ha o que validar.
    """
    segmento = get_segmento_atual(db)

    # Gating: so o segmento de oficina tem validacao dedicada nesta onda.
    if segmento != reg.SEGMENTO_OFICINA:
        return

    # A placa e o identificador principal do veiculo (numero_serie do objeto).
    placa = numero_serie or (dados_adicionais or {}).get("placa")
    if not placa or not str(placa).strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A placa do veículo é obrigatória para abrir uma OS de oficina.",
        )

    if not placa_valida(str(placa)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Placa inválida: '{placa}'. Use o formato antigo (ABC-1234) "
                "ou Mercosul (ABC1D23)."
            ),
        )
