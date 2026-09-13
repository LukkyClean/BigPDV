# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/cfop.py
# DESCRIÇÃO: Derivação do CFOP e da natureza da operação.
# ---------------------------------------------------------------------------
"""
CFOP derivado da OPERAÇÃO.

O problema conceitual que este módulo resolve: hoje o CFOP é gravado por
PRODUTO (`produto_fiscal.cfop_padrao`) e copiado verbatim para o payload. Mas
CFOP é atributo da operação, não da mercadoria — o mesmo item vendido no
balcão (5102) e entregue em outra UF (6102) tem CFOPs diferentes. Guardar por
produto só funciona hoje porque o motor bloqueia operação interestadual.

ESCOPO: CEARÁ, OPERAÇÃO INTERNA.
O primeiro dígito é sempre 5. Quando a operação interestadual sair do
bloqueio, `_grupo_por_destino` é o único ponto a mudar — e aí ele passa a
decidir junto com o `idDest`, que precisa sair da MESMA decisão, senão os dois
divergem e a nota é rejeitada.

Regras confirmadas com a contabilidade em 05/09/2026.
"""
from typing import Optional

from .types import CampoSugerido, Confianca, ContextoDerivacao, Fonte, TipoAtividade

# --- Grupos (1º dígito) ---
GRUPO_INTERNA = 5
GRUPO_INTERESTADUAL = 6

# --- Sufixos (3 últimos dígitos) ---
SUFIXO_PRODUCAO_PROPRIA = 101   # Venda de produção do estabelecimento
SUFIXO_REVENDA = 102            # Venda de mercadoria adquirida de terceiros
SUFIXO_DEVOLUCAO_COMPRA = 202   # Devolução de compra para comercialização
SUFIXO_SUBSTITUIDO = 405        # Venda de merc. sujeita a ST (substituído)
SUFIXO_SERVICO = 933            # Prestação de serviço tributado por ISSQN

# CST/CSOSN que indicam mercadoria com ICMS já retido por substituição.
SITUACOES_SUBSTITUIDO = frozenset({"60", "500"})

# Atividades em que a saída é de produção própria — indústria, panificação com
# produção própria, marcenaria, beneficiamento.
#
# MISTO SAIU DAQUI EM 12/09/2026, e o motivo é a etiqueta da tela.
# O cadastro de empresa oferece `MISTO` como **"Misto (Comércio + Serviços)"**
# (`empresa.constants.ts`) — é o que a loja de informática que vende peça e faz
# conserto escolhe, e foi o que aconteceu numa loja real. Com MISTO aqui, a
# sugestão vinha 5101 ("venda de produção do estabelecimento"), que é de quem
# FABRICA. Para revenda o certo é 5102.
#
# Vale a etiqueta que o usuário leu na hora de escolher, não a que o motor
# imaginou. Quem fabrica escolhe "Indústria" e continua recebendo 5101.
ATIVIDADES_PRODUCAO_PROPRIA = frozenset({TipoAtividade.INDUSTRIA})

NATUREZA_POR_CFOP = {
    "5101": "Venda de producao do estabelecimento",
    "5102": "Venda de mercadoria adquirida de terceiros",
    "5202": "Devolucao de compra para comercializacao",
    "5405": "Venda de merc. adq. de terceiros sujeita a ST",
    "5933": "Prestacao de servico",
    "6101": "Venda de producao do estabelecimento",
    "6102": "Venda de mercadoria adquirida de terceiros",
    "6202": "Devolucao de compra para comercializacao",
    "6933": "Prestacao de servico",
}

# Naturezas que DESLIGAM o cálculo do vTotTrib na integradora.
# Ver tributos_xml.py: a integradora dispensa o cálculo quando a natureza
# contém uma destas palavras — e o cupom sai sem a linha de tributos
# aproximados, o que infringe a Lei 12.741/2012.
PALAVRAS_QUE_DISPENSAM_TRIBUTOS = ("REMESSA", "EXPORTACAO", "DEVOLUCAO", "LANCAMENTO")


class DerivacaoAmbiguaError(ValueError):
    """
    A regra reconhece a situação e se recusa a chutar.

    Existe porque, em matéria fiscal, o silêncio é melhor que o palpite: uma
    nota ACEITA e errada custa multa e juros, enquanto uma emissão interrompida
    custa cinco minutos.
    """


def _grupo_por_destino(ctx: ContextoDerivacao) -> int:
    """
    1º dígito do CFOP: para onde a mercadoria vai.

    NFC-e é sempre interna. Venda presencial também: a mercadoria sai pelo
    balcão e não cruza fronteira, mesmo que o comprador more em outra UF —
    é o mesmo raciocínio da trava em `tax_engine/resolver.py`.
    """
    if ctx.modelo_documento == 65:
        return GRUPO_INTERNA
    if ctx.indicador_presenca == 1:
        return GRUPO_INTERNA
    if ctx.uf_destinatario and ctx.uf_destinatario.upper() != ctx.uf_emitente.upper():
        return GRUPO_INTERESTADUAL
    return GRUPO_INTERNA


def derivar_cfop(
    ctx: ContextoDerivacao,
    *,
    situacao_tributaria: Optional[str] = None,
    tipo_item: str = "PRODUTO",
) -> CampoSugerido:
    """
    CFOP de saída para um item.

    Args:
        ctx: Contexto da operação.
        situacao_tributaria: CST (regime normal) ou CSOSN (Simples) do item.
        tipo_item: "PRODUTO" ou "SERVICO".

    Raises:
        DerivacaoAmbiguaError: numa saída interestadual de item substituído.
            Não existe equivalente interestadual limpo do 5.405 — confirmado
            com a contabilidade. Nessa operação o remetente costuma assumir o
            papel de SUBSTITUTO (6.403/6.404) por forca de protocolo, e ainda
            cabe pedido de ressarcimento do ICMS-ST pago na compra. Quem decide
            isso é o contador, não uma tabela.
    """
    grupo = _grupo_por_destino(ctx)
    substituido = (situacao_tributaria or "") in SITUACOES_SUBSTITUIDO

    if tipo_item == "SERVICO":
        sufixo = SUFIXO_SERVICO
        motivo = "prestacao de servico em documento de mercadoria"
    elif ctx.finalidade_emissao == 4:
        sufixo = SUFIXO_DEVOLUCAO_COMPRA
        motivo = "finalidade de devolucao de compra, em operacao de SAIDA"
    elif substituido:
        if grupo == GRUPO_INTERESTADUAL:
            raise DerivacaoAmbiguaError(
                "Saida interestadual de mercadoria com ICMS-ST retido nao tem "
                "CFOP derivavel: nao existe equivalente limpo do 5.405. "
                "Dependendo do protocolo entre as UFs a operacao vira 6.102 ou "
                "6.403/6.404, com o remetente como substituto. Informe o CFOP "
                "manualmente, com orientacao da contabilidade."
            )
        sufixo = SUFIXO_SUBSTITUIDO
        motivo = f"mercadoria com ICMS retido por ST (situacao {situacao_tributaria})"
    elif ctx.tipo_atividade in ATIVIDADES_PRODUCAO_PROPRIA:
        sufixo = SUFIXO_PRODUCAO_PROPRIA
        motivo = f"saida de producao propria (atividade {ctx.tipo_atividade.value})"
    else:
        sufixo = SUFIXO_REVENDA
        motivo = "revenda de mercadoria adquirida de terceiros"

    cfop = f"{grupo}{sufixo}"
    onde = "interna" if grupo == GRUPO_INTERNA else "interestadual"

    # Produção própria depende do ITEM, não só da empresa: uma padaria vende
    # pão próprio (5101) e refrigerante revendido (5102) na mesma nota. O CNAE
    # decide o default; o produto sobrescreve.
    confianca = (
        Confianca.PROVAVEL
        if sufixo == SUFIXO_PRODUCAO_PROPRIA
        else Confianca.CERTA
    )

    return CampoSugerido(
        campo="cfop_padrao",
        valor=cfop,
        fonte=Fonte.DERIVADO,
        confianca=confianca,
        fundamentacao=f"CFOP {cfop} — operacao {onde}, {motivo}.",
        alternativas=(
            [(f"{grupo}{SUFIXO_REVENDA}", "Revenda de mercadoria de terceiros")]
            if sufixo == SUFIXO_PRODUCAO_PROPRIA
            else []
        ),
    )


def derivar_natureza_operacao(cfop: str) -> CampoSugerido:
    """
    Descrição oficial da operação, a partir do CFOP.

    ⚠️ ARMADILHA: naturezas com REMESSA / EXPORTACAO / DEVOLUCAO / LANCAMENTO
    fazem a integradora DISPENSAR o cálculo do `vTotTrib` (ver tributos_xml.py).
    O cupom sai sem a linha de tributos aproximados — infração à Lei
    12.741/2012. Por isso a devolução vem com `exige_confirmacao`.
    """
    descricao = NATUREZA_POR_CFOP.get(cfop, "Venda de Mercadoria")
    dispensa_tributos = any(
        palavra in descricao.upper() for palavra in PALAVRAS_QUE_DISPENSAM_TRIBUTOS
    )

    fundamentacao = f"Descricao oficial do CFOP {cfop}."
    if dispensa_tributos:
        fundamentacao += (
            " ATENCAO: esta natureza faz a integradora nao calcular os tributos "
            "aproximados (Lei 12.741/2012) — confira a linha no cupom."
        )

    return CampoSugerido(
        campo="natureza_operacao",
        valor=descricao,
        fonte=Fonte.DERIVADO,
        confianca=Confianca.CERTA,
        fundamentacao=fundamentacao,
        exige_confirmacao=dispensa_tributos,
    )
