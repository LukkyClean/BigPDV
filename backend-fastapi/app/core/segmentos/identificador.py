# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/identificador.py
# DESCRICAO: Decide se um identificador digitado vale como chave (motor).
# ---------------------------------------------------------------------------

import re
from typing import Optional

from app.core.busca import compactar

from .definicoes import get_identificador_segmento

# ===========================================================================
# IDENTIFICADOR PESQUISAVEL
# ===========================================================================
# `numero_serie` e obrigatorio no schema da OS, entao quem nao tem o dado em
# maos digita alguma coisa: "S/N", "nao sei", "-". Isso NAO identifica o bem, e
# tratar como se identificasse causa dois estragos:
#
#   1. dedup errado -- dois notebooks do mesmo cliente com "S/N" viravam UM
#      registro so, e o segundo sobrescrevia marca/modelo do primeiro;
#   2. aviso de duplicidade inutil -- todo "S/N" bateria com todo "S/N" da loja.
#
# A regra abaixo decide se um identificador vale como chave. Ela mora aqui, no
# motor, e nao num `if segmento ==` espalhado: cada segmento ja declara seu
# `identificador`, e a oficina ganha o filtro de graca porque tem `regex`.

# Comparados na forma compactada (sem acento, sem separador, minusculo), entao
# "S/N", "s / n" e "SN" caem todos em "sn".
IDENTIFICADORES_GENERICOS = frozenset({
    "sn", "s", "n", "na", "nd", "ni", "nt",
    "sem", "semnumero", "semnumerodeserie", "semserie", "semserial",
    "semidentificacao", "semplaca", "semregistro",
    "naosei", "naotem", "naopossui", "naoinformado", "naoidentificado",
    "nenhum", "nenhuma", "desconhecido", "indefinido", "ausente",
    "teste", "test", "generico", "avulso", "diverso", "diversos",
})

# Abaixo disso nao ha identificador real: "AB", "123". Serial curto de verdade e
# raro, e o custo de errar aqui e so nao avisar -- nunca bloquear.
IDENTIFICADOR_MIN_CARACTERES = 4


def normalizar_identificador(valor: Optional[str]) -> str:
    """Forma canonica para casar contra o `regex` do segmento: sem espaco nem
    hifen, em maiusculo. Ex: 'abc-1d23' -> 'ABC1D23'."""
    return re.sub(r"[\s\-]", "", (valor or "")).upper()


def identificador_pesquisavel(valor: Optional[str], segmento: Optional[str] = None) -> bool:
    """
    True se `valor` identifica um bem de verdade -- ou seja, se vale como chave
    para reaproveitar objeto e para avisar duplicidade.

    False para o que o atendente digita quando nao tem o dado: "S/N", "nao sei",
    "----", "0000". Ver o bloco IDENTIFICADOR PESQUISAVEL acima.

    Nunca bloqueia nada: quem responde False so deixa de ser usado como chave, e
    a OS e criada normalmente com o texto que o usuario escreveu.
    """
    compacto = compactar(valor)

    if not compacto:
        return False
    if compacto in IDENTIFICADORES_GENERICOS:
        return False
    if len(compacto) < IDENTIFICADOR_MIN_CARACTERES:
        return False
    # Um caractere repetido nao identifica nada: "xxxx", "0000", "-----".
    if len(set(compacto)) == 1:
        return False

    # Segmento com formato conhecido (oficina) decide pelo proprio padrao: o que
    # nao e placa nao e identificador, e nem chega a ser pesquisado.
    regex = (get_identificador_segmento(segmento) or {}).get("regex")
    if regex:
        return bool(re.match(regex, normalizar_identificador(valor)))

    return True
