# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/definicoes/assistencia.py
# DESCRICAO: Definicao do segmento ASSISTENCIA TECNICA / INFORMATICA
#            ("informatica" no dia a dia). Dado, nao motor.
#
#            EM PRODUCAO desde antes da existencia deste registry. Descrito
#            aqui como documentacao/contrato: NAO adiciona validacao nova ao
#            fluxo de informatica (a validacao continua sendo a que ja existe).
# ---------------------------------------------------------------------------

from ..campos import campo
from ..capacidades import CAP_DIAGNOSTICO

SEGMENTO_ASSISTENCIA = "assistencia_tecnica"  # "informatica" no dia a dia

# Cabecalhos das secoes do formulario (ver oficina.py).
GRUPO_EQUIPAMENTO = "Dados do Equipamento"
GRUPO_DETALHES = "Detalhes & Segurança"


ASSISTENCIA = {
    "segmento": SEGMENTO_ASSISTENCIA,
    "rotulo_objeto_singular": "Equipamento",
    "rotulo_objeto_plural": "Equipamentos",
    "identificador": {"nome": "numero_serie", "label": "Nº de série / IMEI", "regex": None},

    # So o diagnostico: informatica recebe aparelho com defeito, investiga e
    # emite laudo -- e o que a tela dela ja faz hoje, agora declarado. Nao e uma
    # afirmacao de que informatica "nao pode" ter aprovacao de itens: o dia que
    # o produto quiser, e acrescentar CAP_APROVACAO_ITENS nesta lista.
    "capacidades": [CAP_DIAGNOSTICO],
    "veiculo": [],  # nao se aplica
    # Todos em dados_adicionais (o padrao de `campo`): `imei` deixou de ser
    # coluna na refatoracao Equipamento -> ObjetoServico e hoje e uma property
    # sobre o JSON -- ver db/models/objeto_servico.py.
    "checkin": [
        campo("imei", "IMEI", "texto", escopo="objeto", grupo=GRUPO_EQUIPAMENTO),
        campo("senha_aparelho", "Senha do aparelho", "texto", escopo="os",
              grupo=GRUPO_DETALHES),
        campo("acessorios", "Acessórios entregues", "texto", escopo="os",
              grupo=GRUPO_DETALHES, largura="inteira"),
        campo("condicoes_aparelho", "Condições do aparelho", "texto", escopo="os",
              grupo=GRUPO_DETALHES, largura="inteira"),
    ],
    "acessorios": [],
    "vistoria": [],
}
