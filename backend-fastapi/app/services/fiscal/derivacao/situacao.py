# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/situacao.py
# DESCRIÇÃO: Defaults de CST/CSOSN, origem e CST de PIS/COFINS por regime.
# ---------------------------------------------------------------------------
"""
Situação tributária padrão do produto típico do varejo.

Tudo aqui é `if` sobre dados que já estão no banco — nenhuma tabela externa,
nenhuma rede. São os defaults que fazem um produto novo nascer utilizável, e
todos podem ser sobrescritos.

O QUE ESTE MÓDULO SE RECUSA A FAZER
-----------------------------------
- **CSOSN 101** nunca é derivado. O percentual creditável depende da FAIXA DE
  RECEITA do mês (Anexos da LC 123/2006), que o sistema não conhece. Derivar
  faz a loja transferir crédito indevido ao cliente e responder por ele. Pior:
  o cálculo atual usa a alíquota interna da UF, que não é o `pCredSN` correto.
- **CST 60 / CSOSN 500** nunca são derivados por inferência de ST. Se o item
  não está em ST na UF, a nota sai com ICMS zerado e é AUTORIZADA — o imposto
  simplesmente não foi recolhido, e isso aparece na fiscalização, com multa.
  Sujeição a ST depende do RICMS do estado e é assunto de contador.
"""
from .types import CampoSugerido, Confianca, ContextoDerivacao, Fonte

# CRT 1 (Simples) e 4 (MEI) usam CSOSN; 2 e 3 usam CST.
CRT_QUE_USAM_CSOSN = frozenset({1, 4})

CSOSN_TRIBUTADO_SEM_CREDITO = "102"
CST_TRIBUTADO_INTEGRALMENTE = "00"

CST_PIS_COFINS_SIMPLES = "49"
CST_PIS_COFINS_TRIBUTADO = "01"

ORIGEM_NACIONAL = "0"


def _usa_csosn(crt: int) -> bool:
    return crt in CRT_QUE_USAM_CSOSN


def derivar_situacao_icms(ctx: ContextoDerivacao) -> CampoSugerido:
    """
    CSOSN 102 no Simples, CST 00 no regime normal.

    102 = "tributada sem permissão de crédito", o default seguro do varejo do
    Simples: não transfere crédito nenhum, então não há como transferir a
    mais. O 101 fica de fora por decisão explícita (ver docstring do módulo).
    """
    if _usa_csosn(ctx.crt):
        return CampoSugerido(
            campo="csosn",
            valor=CSOSN_TRIBUTADO_SEM_CREDITO,
            fonte=Fonte.DEFAULT_REGIME,
            confianca=Confianca.PROVAVEL,
            fundamentacao=(
                f"CSOSN 102 (tributada sem permissao de credito) — padrao do "
                f"varejo no Simples Nacional (CRT {ctx.crt}). O 101, que "
                f"transfere credito, depende da faixa de receita do mes e "
                f"precisa ser escolhido pela contabilidade."
            ),
            alternativas=[
                ("101", "Com permissao de credito — exige pCredSN da contabilidade"),
                ("500", "ICMS ja retido por ST — so se o item estiver em ST na UF"),
            ],
        )

    return CampoSugerido(
        campo="cst_icms",
        valor=CST_TRIBUTADO_INTEGRALMENTE,
        fonte=Fonte.DEFAULT_REGIME,
        confianca=Confianca.PROVAVEL,
        fundamentacao=(
            f"CST 00 (tributada integralmente) — padrao do regime normal "
            f"(CRT {ctx.crt})."
        ),
        alternativas=[
            ("20", "Com reducao de base — exige o percentual de reducao"),
            ("40", "Isenta"),
            ("60", "ICMS ja retido por ST — so se o item estiver em ST na UF"),
        ],
    )


def derivar_cst_pis_cofins(ctx: ContextoDerivacao) -> list[CampoSugerido]:
    """
    CST 49 zerado no Simples; 01 no regime normal.

    No Simples isto é `CERTA` e não sugestão: o resolver já força 49
    independentemente do que estiver gravado, porque os tributos vão na guia
    única. A sugestão só existe para o campo nascer coerente com o que a nota
    vai levar.
    """
    if _usa_csosn(ctx.crt):
        return [
            CampoSugerido(
                campo=campo,
                valor=CST_PIS_COFINS_SIMPLES,
                fonte=Fonte.DEFAULT_REGIME,
                confianca=Confianca.CERTA,
                fundamentacao=(
                    "CST 49 zerado — no Simples Nacional o PIS/COFINS vai na "
                    "guia unica. O motor forca este valor na emissao."
                ),
            )
            for campo in ("cst_pis", "cst_cofins")
        ]

    return [
        CampoSugerido(
            campo=campo,
            valor=CST_PIS_COFINS_TRIBUTADO,
            fonte=Fonte.DEFAULT_REGIME,
            confianca=Confianca.PROVAVEL,
            fundamentacao=(
                "CST 01 (aliquota normal) — padrao fora do Simples. Produtos "
                "monofasicos (farma, autopecas, bebidas frias) usam 04 ou 06."
            ),
            alternativas=[
                ("04", "Monofasico — tributacao concentrada na industria"),
                ("06", "Aliquota zero"),
            ],
        )
        for campo in ("cst_pis", "cst_cofins")
    ]


def derivar_origem_mercadoria() -> CampoSugerido:
    """
    Origem 0 (Nacional).

    Cobre ~95% do varejo. As origens 3 e 5 (conteúdo de importação) dependem
    da FCI declarada pela indústria — sem esse documento, marcar seria chute,
    e por isso não entram como sugestão nem como alternativa automática.
    """
    return CampoSugerido(
        campo="origem_mercadoria",
        valor=ORIGEM_NACIONAL,
        fonte=Fonte.DERIVADO,
        confianca=Confianca.PROVAVEL,
        fundamentacao=(
            "Origem 0 (Nacional) — o caso da esmagadora maioria do varejo. "
            "Mercadoria importada ou com conteudo de importacao precisa da "
            "origem correta, e as origens 3 e 5 dependem da FCI da industria."
        ),
        alternativas=[
            ("1", "Estrangeira — importacao direta"),
            ("2", "Estrangeira — adquirida no mercado interno"),
        ],
    )
