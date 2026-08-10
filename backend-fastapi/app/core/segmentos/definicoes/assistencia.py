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

SEGMENTO_ASSISTENCIA = "assistencia_tecnica"  # "informatica" no dia a dia


ASSISTENCIA = {
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
        campo("imei", "IMEI", "texto", escopo="objeto"),
        campo("senha_aparelho", "Senha do aparelho", "texto", escopo="os"),
        campo("acessorios", "Acessórios entregues", "texto", escopo="os"),
        campo("condicoes_aparelho", "Condições do aparelho", "texto", escopo="os"),
    ],
    "acessorios": [],
    "vistoria": [],
}
