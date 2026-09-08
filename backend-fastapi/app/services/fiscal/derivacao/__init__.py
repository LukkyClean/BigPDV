# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/__init__.py
# DESCRIÇÃO: API pública da camada de derivação fiscal.
# ---------------------------------------------------------------------------
"""
Derivação de campos fiscais.

POR QUE UM MÓDULO IRMÃO DO tax_engine, E NÃO DENTRO DELE
--------------------------------------------------------
O `tax_engine` calcula imposto sobre uma operação que já existe; a derivação
responde "o que preencher" e roda também no CADASTRO, sem venda nenhuma. São
momentos diferentes, e misturá-los obrigaria o cadastro a montar uma venda
falsa para perguntar qual CFOP usar.

Tudo aqui é função pura sobre `ContextoDerivacao`. A única ponte com o ORM é
`resolver_db`, espelhando a divisão que já funciona no tax_engine.

A REGRA QUE GOVERNA O MÓDULO
----------------------------
O pior desfecho de uma automação fiscal não é a nota rejeitada — é a nota
ACEITA E ERRADA. Rejeição custa cinco minutos; recolhimento a menor custa
multa, juros e responsabilidade do lojista. Por isso cada regra que poderia
chutar ou recusa (`DerivacaoAmbiguaError`) ou marca `exige_confirmacao`.
"""
from .cfop import (
    DerivacaoAmbiguaError,
    derivar_cfop,
    derivar_natureza_operacao,
)
from .operacao import derivar_consumidor_final, derivar_local_destino
from .situacao import (
    derivar_cst_pis_cofins,
    derivar_origem_mercadoria,
    derivar_situacao_icms,
)
from .types import (
    CampoSugerido,
    Confianca,
    ContextoDerivacao,
    Fonte,
    TipoAtividade,
)

__all__ = [
    "CampoSugerido",
    "Confianca",
    "ContextoDerivacao",
    "DerivacaoAmbiguaError",
    "Fonte",
    "TipoAtividade",
    "derivar_cfop",
    "derivar_consumidor_final",
    "derivar_cst_pis_cofins",
    "derivar_local_destino",
    "derivar_natureza_operacao",
    "derivar_origem_mercadoria",
    "derivar_produto",
    "derivar_situacao_icms",
]


def derivar_produto(ctx: ContextoDerivacao) -> list[CampoSugerido]:
    """
    Todas as sugestões para um produto novo, de uma vez.

    É o que alimenta o formulário de cadastro e o drawer de resolução de
    pendências em lote. Não persiste nada: quem decide o que aplicar é a
    camada de merge, que respeita o que o usuário já escolheu.

    O CFOP entra com a situação tributária derivada logo acima, para que os
    dois cheguem coerentes — sugerir CSOSN 500 com CFOP 5102 seria oferecer
    uma combinação que a SEFAZ recusa.
    """
    situacao = derivar_situacao_icms(ctx)

    sugestoes: list[CampoSugerido] = [
        situacao,
        derivar_origem_mercadoria(),
        *derivar_cst_pis_cofins(ctx),
    ]

    try:
        cfop = derivar_cfop(ctx, situacao_tributaria=situacao.valor)
    except DerivacaoAmbiguaError:
        # Sem CFOP derivável a resposta certa é não sugerir. O campo continua
        # obrigatório e o usuário preenche com a contabilidade.
        return sugestoes

    sugestoes.append(cfop)
    if cfop.valor:
        sugestoes.append(derivar_natureza_operacao(cfop.valor))

    return sugestoes
