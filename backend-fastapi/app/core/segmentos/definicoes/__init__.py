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
from .serigrafia import SEGMENTO_SERIGRAFIA, SERIGRAFIA

# Cada definicao carrega o proprio identificador na chave "segmento", entao o
# mapa se monta sozinho -- nao ha uma segunda lista de nomes para esquecer de
# atualizar.
DEFINICOES: Dict[str, Dict[str, Any]] = {
    d["segmento"]: d
    for d in (OFICINA, ASSISTENCIA, SERIGRAFIA)
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


def identificador_e_gerado(segmento: Optional[str]) -> bool:
    """True se o SISTEMA cria o identificador, em vez de pedir ao usuario.

    Placa e numero de serie existem no mundo -- estao escritos no bem, e o
    atendente so copia. Codigo de arte nao existe ate alguem inventar, e campo
    obrigatorio que o usuario nao tem como preencher vira lixo ("1", "teste").
    """
    return bool((get_identificador_segmento(segmento) or {}).get("gerado"))


def gerar_identificador(segmento: Optional[str], numero_os: str) -> Optional[str]:
    """Identificador derivado do numero da OS. Ex: ART-0042.

    Nasce do numero da OS de proposito: ele ja e sequencial e unico, entao nao
    ha contador novo para manter nem corrida entre terminais para tratar.
    """
    identificador = get_identificador_segmento(segmento) or {}
    if not identificador.get("gerado"):
        return None
    prefixo = identificador.get("prefixo") or "ID"
    return f"{prefixo}-{numero_os}"


__all__ = [
    "DEFINICOES",
    "OFICINA",
    "ASSISTENCIA",
    "SERIGRAFIA",
    "PLACA_REGEX",
    "SEGMENTO_OFICINA",
    "SEGMENTO_ASSISTENCIA",
    "SEGMENTO_SERIGRAFIA",
    "get_definicao_segmento",
    "segmento_tem_definicao",
    "get_identificador_segmento",
    "identificador_e_gerado",
    "gerar_identificador",
]
