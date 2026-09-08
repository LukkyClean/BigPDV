# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/operacao.py
# DESCRIÇÃO: Campos que descrevem a operação — indFinal e idDest.
# ---------------------------------------------------------------------------
"""
Indicadores da operação.

O que NÃO está aqui, de propósito: `indPres`. Ele descreve o CANAL pelo qual a
venda chegou (balcão, delivery, internet, telefone), e isso não é derivável do
que o sistema guarda — `venda.entrega` diz que há frete, não distingue entrega
a domicílio de venda de balcão com frete contratado. Por isso o PDV passou a
PERGUNTAR, no fechamento, em vez de adivinhar.

Vale insistir no motivo: `indPres` alimenta a trava interestadual do
`tax_engine/resolver.py`, que trata 1 como venda de balcão e, por definição,
interna. Derivar 1 por engano numa venda pela internet desliga a trava e
libera uma nota interestadual sem DIFAL, que o motor não calcula.
"""
from .types import CampoSugerido, Confianca, ContextoDerivacao, Fonte

# idDest da NF-e: 1 = operação interna, 2 = interestadual, 3 = exterior.
IDDEST_INTERNA = 1
IDDEST_INTERESTADUAL = 2


def derivar_consumidor_final(ctx: ContextoDerivacao) -> CampoSugerido:
    """
    indFinal: 0 quando o destinatário compra para revender, 1 nos demais.

    Usa exatamente o dado que o `indIEDest` já deriva no payload_builder — PJ
    com inscrição estadual é contribuinte de ICMS, e contribuinte que compra
    mercadoria normalmente está revendendo.

    `PROVAVEL` e não `CERTA` porque a inferência tem uma exceção comum e
    legítima: uma PJ com IE pode comprar para consumo próprio (um mercado
    comprando material de limpeza para a própria loja). Nesse caso indFinal é
    1 mesmo com IE, e quem sabe disso é quem faz a venda.
    """
    revenda = ctx.destinatario_pj_com_ie

    return CampoSugerido(
        campo="consumidor_final",
        valor="0" if revenda else "1",
        fonte=Fonte.DERIVADO,
        confianca=Confianca.PROVAVEL,
        fundamentacao=(
            "Destinatario e PJ com inscricao estadual (contribuinte de ICMS): "
            "a compra normalmente e para revenda."
            if revenda
            else "Destinatario e consumidor final: pessoa fisica, PJ sem "
                 "inscricao estadual, ou venda sem destinatario identificado."
        ),
        alternativas=(
            [("1", "Consumidor final — a PJ esta comprando para consumo proprio")]
            if revenda
            else []
        ),
    )


def derivar_local_destino(ctx: ContextoDerivacao) -> CampoSugerido:
    """
    idDest — interna ou interestadual.

    Precisa sair da MESMA decisão que o primeiro dígito do CFOP. Se os dois
    divergirem (idDest 1 com CFOP 6.102, por exemplo) a nota é rejeitada. Hoje
    o payload chumba 1 e isso é correto porque o motor bloqueia interestadual;
    quando o bloqueio sair, este é o par que precisa mudar junto.
    """
    interna = not (
        ctx.uf_destinatario
        and ctx.uf_destinatario.upper() != ctx.uf_emitente.upper()
        and ctx.indicador_presenca != 1
        and ctx.modelo_documento != 65
    )

    return CampoSugerido(
        campo="local_destino",
        valor=str(IDDEST_INTERNA if interna else IDDEST_INTERESTADUAL),
        fonte=Fonte.DERIVADO,
        confianca=Confianca.CERTA,
        fundamentacao=(
            "Operacao interna: a mercadoria nao cruza fronteira estadual."
            if interna
            else f"Operacao interestadual: {ctx.uf_emitente} -> "
                 f"{ctx.uf_destinatario}."
        ),
    )
