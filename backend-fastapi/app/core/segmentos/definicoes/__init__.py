# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/definicoes/__init__.py
# DESCRICAO: Reune as definicoes declaradas e responde consultas sobre elas.
#
#            ACRESCENTAR UM SEGMENTO = criar o arquivo ao lado e somar duas
#            linhas aqui (o import e a entrada na tupla). Nada mais no projeto
#            precisa saber que ele existe.
# ---------------------------------------------------------------------------

from typing import Any, Dict, Optional

from .assistencia import ASSISTENCIA, SEGMENTO_ASSISTENCIA
from .oficina import OFICINA, PLACA_REGEX, SEGMENTO_OFICINA

# Cada definicao carrega o proprio identificador na chave "segmento", entao o
# mapa se monta sozinho -- nao ha uma segunda lista de nomes para esquecer de
# atualizar.
DEFINICOES: Dict[str, Dict[str, Any]] = {
    d["segmento"]: d
    for d in (OFICINA, ASSISTENCIA)
}


def get_definicao_segmento(segmento: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retorna a definicao de campos de um segmento, ou None se nao houver
    definicao especifica (segmentos genericos usam apenas dados_adicionais livre)."""
    if not segmento:
        return None
    return DEFINICOES.get(segmento)


def segmento_tem_definicao(segmento: Optional[str]) -> bool:
    """True se o segmento possui uma definicao dedicada de campos."""
    return get_definicao_segmento(segmento) is not None


def get_identificador_segmento(segmento: Optional[str]) -> Optional[Dict[str, Any]]:
    """Descricao do identificador principal do segmento (nome/label/regex), se houver."""
    definicao = get_definicao_segmento(segmento)
    return definicao.get("identificador") if definicao else None


__all__ = [
    "DEFINICOES",
    "OFICINA",
    "ASSISTENCIA",
    "PLACA_REGEX",
    "SEGMENTO_OFICINA",
    "SEGMENTO_ASSISTENCIA",
    "get_definicao_segmento",
    "segmento_tem_definicao",
    "get_identificador_segmento",
]
