# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos.py
# DESCRICAO: Registry (fonte de verdade) dos campos dinamicos de cada segmento
#            de negocio. Define quais chaves vao dentro de `dados_adicionais`
#            do objeto de servico e da OS, por segmento.
#
#            Este modulo NAO altera nenhuma tabela. Ele apenas descreve, de
#            forma declarativa, os campos que cada segmento usa dentro do JSON
#            `dados_adicionais` ja existente. E consumido por:
#              - services/segmentos.py  -> validacao (gated por segmento)
#              - endpoint de definicao  -> contrato para o frontend renderizar
#
#            IMPORTANTE (regra do projeto): informatica/assistencia_tecnica ja
#            esta em producao. Adicionar/alterar segmentos aqui e ADITIVO e nao
#            pode mudar o comportamento de quem nao for do segmento em questao.
# ---------------------------------------------------------------------------

import re
from typing import Any, Dict, List, Optional

from app.core.busca import compactar

# --- Identificadores de segmento (espelham auth.SEGMENTOS_VALIDOS) ---
SEGMENTO_OFICINA = "oficina_mecanica"
SEGMENTO_ASSISTENCIA = "assistencia_tecnica"  # "informatica" no dia a dia


# ===========================================================================
# CAPACIDADES
# ===========================================================================
# O que um segmento FAZ, em oposicao a quais campos ele tem. Existe porque o
# frontend precisava perguntar "quem e o cliente?" (if segmento == oficina) para
# decidir se mostrava a aprovacao de itens, a vistoria, etc. Isso obrigava a
# editar o frontend a cada segmento novo.
#
# Com capacidades, o frontend pergunta "o que este segmento faz?" e liga a UI
# pelo contrato. Ligar uma capacidade para um segmento novo passa a ser uma
# linha AQUI, sem tocar em Vue.
#
# NAO sao exclusivas de nenhum segmento: aprovacao de orcamento e garantia
# servem qualquer negocio de servico. Hoje so a oficina as usa porque foi para
# ela que foram construidas -- nao porque sejam "de oficina".

CAP_VISTORIA = "vistoria"                # checklist de inspecao (DVI) na entrada
CAP_REVISOES = "revisoes"                # lembrete de manutencao por data/KM
CAP_APROVACAO_ITENS = "aprovacao_itens"  # cliente aprova/reprova item do orcamento
CAP_GARANTIA_ITENS = "garantia_itens"    # garantia (dias/KM) por item

CAPACIDADES_CONHECIDAS = [
    CAP_VISTORIA,
    CAP_REVISOES,
    CAP_APROVACAO_ITENS,
    CAP_GARANTIA_ITENS,
]

# Regex de placa: aceita padrao antigo (ABC-1234 / ABC1234) e Mercosul (ABC1D23).
# A validacao real normaliza (uppercase, sem hifen) antes de aplicar.
PLACA_REGEX = r"^(?:[A-Z]{3}\d{4}|[A-Z]{3}\d[A-Z]\d{2})$"


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
# registry, e nao num `if segmento ==` espalhado: cada segmento ja declara seu
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


# ===========================================================================
# HELPERS DE CONSTRUCAO (apenas para montar as estruturas de forma legivel)
# ===========================================================================

def _campo(
    nome: str,
    label: str,
    tipo: str,
    obrigatorio: bool = False,
    opcoes: Optional[List[str]] = None,
    escopo: str = "objeto",
) -> Dict[str, Any]:
    """Descreve um campo dinamico.

    tipo: 'texto' | 'numero' | 'inteiro' | 'opcao' | 'booleano'
    escopo: 'objeto' (dados do veiculo) | 'os' (dados da OS/check-in)
    """
    campo: Dict[str, Any] = {
        "nome": nome,
        "label": label,
        "tipo": tipo,
        "obrigatorio": obrigatorio,
        "escopo": escopo,
    }
    if opcoes is not None:
        campo["opcoes"] = opcoes
    return campo


def _grupo_vistoria(titulo: str, itens: List[str]) -> Dict[str, Any]:
    """Grupo de itens de inspecao. Cada item e avaliado como OK / N_OK / REPARAR."""
    return {
        "titulo": titulo,
        "estados": ["OK", "N_OK", "REPARAR"],
        "itens": itens,
    }


# ===========================================================================
# DEFINICAO: OFICINA MECANICA (baseado na ficha de vistoria de entrada)
# ===========================================================================

_OFICINA = {
    "segmento": SEGMENTO_OFICINA,
    # Rotulos que o frontend usa para nomear a entidade no lugar de "Objeto".
    "rotulo_objeto_singular": "Veículo",
    "rotulo_objeto_plural": "Veículos",
    # Campo do objeto que serve de identificador principal (mapeia numero_serie).
    "identificador": {"nome": "placa", "label": "Placa", "regex": PLACA_REGEX},

    # O que o segmento faz (ver bloco CAPACIDADES no topo).
    "capacidades": [
        CAP_VISTORIA,
        CAP_REVISOES,
        CAP_APROVACAO_ITENS,
        CAP_GARANTIA_ITENS,
    ],

    # --- Dados do veiculo (escopo=objeto) ---
    "veiculo": [
        _campo("placa", "Placa", "texto", obrigatorio=True, escopo="objeto"),
        _campo("marca", "Marca", "texto", escopo="objeto"),
        _campo("modelo", "Modelo", "texto", escopo="objeto"),
        _campo("cor", "Cor", "texto", escopo="objeto"),
        _campo("ano", "Ano", "inteiro", escopo="objeto"),
        _campo("chassi", "Chassi", "texto", escopo="objeto"),
    ],

    # --- Check-in de entrada (escopo=os) ---
    "checkin": [
        _campo("km_entrada", "KM de entrada", "inteiro", escopo="os"),
        _campo("prisma", "Prisma", "texto", escopo="os"),
        _campo("ct", "CT", "texto", escopo="os"),
        _campo("estacao_radio", "Estação do rádio", "texto", escopo="os"),
        _campo("combustivel_nivel", "Nível de combustível", "opcao",
               opcoes=["VAZIO", "1/4", "1/2", "3/4", "CHEIO"], escopo="os"),
        _campo("combustivel_tipo", "Tipo de combustível", "opcao",
               opcoes=["ALCOOL", "GASOLINA", "DIESEL"], escopo="os"),
        _campo("pneus_estado", "Estado dos pneus", "opcao",
               opcoes=["BOM", "REGULAR", "RUIM"], escopo="os"),
        _campo("estepe_estado", "Estado do estepe", "opcao",
               opcoes=["BOM", "REGULAR", "RUIM"], escopo="os"),
    ],

    # --- Acessorios presentes (checklist sim/nao) ---
    "acessorios": [
        "acendedor", "calota", "chave_de_roda", "estepe", "extintor",
        "gps", "haste_antena", "macaco", "manual", "radio_cd_dvd",
        "pen_drive", "roda_liga_leve", "triangulo", "outros",
    ],

    # --- Vistoria de inspecao (3 blocos, cada item = OK / N_OK / REPARAR) ---
    "vistoria": [
        _grupo_vistoria("Inspeção externa (carro no chão)", [
            "antena_teto", "pintura_manchas_riscos_amassados", "bagageiro",
            "farois", "frisos_laterais", "lanternas", "portas",
            "rodas_calotas", "percepcoes_de_uso",
        ]),
        _grupo_vistoria("Inspeção interna", [
            "antena_interna", "bancos_dianteiros_revestimentos_cintos",
            "bancos_traseiros_revestimentos_cintos",
            "comutadores_consumidores_eletricos_comandos", "contem_som",
            "direcao", "sinais_de_criancas", "sinais_odores_cigarro",
            "vidros_eletricos", "uso_de_celular", "percepcoes_de_uso",
        ]),
        _grupo_vistoria("Inspeção externa (carro no elevador)", [
            "escapamento", "estribos_laterais", "pneus", "protetor_de_carter",
            "rodas", "sinais_de_impacto", "suspensao_coifas",
            "vazamentos_oleo_agua_fluidos", "percepcoes_de_uso",
        ]),
    ],
}


# ===========================================================================
# DEFINICAO: ASSISTENCIA TECNICA / INFORMATICA (ja em producao)
# Descrita aqui apenas como documentacao/contrato. NAO adiciona validacao
# nova ao fluxo de informatica (a validacao continua sendo a que ja existe).
# ===========================================================================

_ASSISTENCIA = {
    "segmento": SEGMENTO_ASSISTENCIA,
    "rotulo_objeto_singular": "Equipamento",
    "rotulo_objeto_plural": "Equipamentos",
    "identificador": {"nome": "numero_serie", "label": "Nº de série / IMEI", "regex": None},

    # Vazio preserva exatamente a tela de informatica que esta em producao hoje.
    # Nao e uma afirmacao de que informatica "nao pode" ter aprovacao de itens:
    # o dia que o produto quiser, e acrescentar CAP_APROVACAO_ITENS nesta lista.
    "capacidades": [],
    "veiculo": [],  # nao se aplica
    "checkin": [
        _campo("imei", "IMEI", "texto", escopo="objeto"),
        _campo("senha_aparelho", "Senha do aparelho", "texto", escopo="os"),
        _campo("acessorios", "Acessórios entregues", "texto", escopo="os"),
        _campo("condicoes_aparelho", "Condições do aparelho", "texto", escopo="os"),
    ],
    "acessorios": [],
    "vistoria": [],
}


# ===========================================================================
# API DO REGISTRY
# ===========================================================================

DEFINICOES: Dict[str, Dict[str, Any]] = {
    SEGMENTO_OFICINA: _OFICINA,
    SEGMENTO_ASSISTENCIA: _ASSISTENCIA,
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


def normalizar_identificador(valor: Optional[str]) -> str:
    """Forma canonica para casar contra o `regex` do segmento: sem espaco nem
    hifen, em maiusculo. Ex: 'abc-1d23' -> 'ABC1D23'."""
    return re.sub(r"[\s\-]", "", (valor or "")).upper()


def identificador_pesquisavel(valor: Optional[str], segmento: Optional[str] = None) -> bool:
    """
    True se `valor` identifica um bem de verdade -- ou seja, se vale como chave
    para reaproveitar objeto e para avisar duplicidade.

    False para o que o atendente digita quando nao tem o dado: "S/N", "nao sei",
    "----", "0000". Ver o bloco IDENTIFICADOR PESQUISAVEL no topo.

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
