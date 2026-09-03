# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/resolver.py
# DESCRIÇÃO: Ponte entre o banco de dados e os DTOs puros do tax_engine.
#            ÚNICO arquivo do tax_engine que importa modelos ORM.
#
# Responsabilidades:
#   - Resolver alíquotas: override do produto > default da UF
#   - Converter centavos (int) → Decimal reais
#   - Validar trava de operação interestadual
#   - Montar ItemEntrada e DadosNota para o engine
# ---------------------------------------------------------------------------

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.aliquota_uf import AliquotaUF
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.venda import Venda

from .constants import COFINS_PADRAO, CST_PIS_COFINS_SIMPLES, PIS_PADRAO
from .exceptions import (
    AliquotaNaoEncontradaError,
    DadosFiscaisAusentesError,
    OperacaoInterestadualError,
)
from .types import DadosNota, ItemEntrada


ZERO = Decimal("0")


def _centesimos_para_decimal(valor: Optional[int], padrao: Decimal) -> Decimal:
    """
    Converte centésimos de ponto percentual (int, ex: 1800) para Decimal (18.00).
    Se valor for None, retorna o padrão.
    """
    if valor is None:
        return padrao
    return Decimal(valor) / Decimal("100")


def _centavos_para_reais(centavos: int) -> Decimal:
    """Converte centavos (int) para Decimal em reais."""
    return Decimal(centavos) / Decimal("100")


# indPres da NF-e: 1 = operação presencial. Os demais (2=internet,
# 3=teleatendimento, 4=NFC-e entrega, 9=outros não presenciais) implicam
# circulação da mercadoria e podem ser interestaduais de verdade.
INDPRES_PRESENCIAL = 1


def _operacao_presencial(venda: Venda) -> bool:
    """
    Se a venda é de balcão.

    Sem dados fiscais preenchidos assume presencial — é o caso do PDV, que é
    o uso dominante do sistema.
    """
    nota_fiscal = getattr(venda, "nota_fiscal", None)
    if not nota_fiscal or nota_fiscal.indicador_presenca is None:
        return True
    return nota_fiscal.indicador_presenca == INDPRES_PRESENCIAL


def _obter_uf_cliente(venda: Venda) -> Optional[str]:
    """Obtém a UF do primeiro endereço do cliente da venda, se existir."""
    if not venda.cliente:
        return None

    enderecos = venda.cliente.endereco
    if not enderecos:
        return None

    estado = enderecos[0].estado
    if hasattr(estado, "value"):
        return str(estado.value)
    return str(estado) if estado else None


def resolver_aliquotas_venda(
    db: Session,
    venda: Venda,
    uf_emitente: str,
    simples_nacional: bool,
    excluir_icms_base_pis_cofins: bool = False,
) -> tuple[list[ItemEntrada], DadosNota]:
    """
    Converte uma Venda (ORM) em DTOs puros para o tax_engine.

    Resolução de alíquotas: ProdutoFiscal (override) > AliquotaUF (default).

    Args:
        db: Sessão SQLAlchemy.
        venda: Modelo Venda com itens e cliente carregados.
        uf_emitente: UF do emitente (ex: "SP").
        simples_nacional: Se empresa é do Simples Nacional.
        excluir_icms_base_pis_cofins: Flag STF Tema 69.

    Returns:
        Tupla (itens_entrada, dados_nota) pronta para calcular_impostos().

    Raises:
        OperacaoInterestadualError: se UF do cliente difere da UF do emitente.
        AliquotaNaoEncontradaError: se UF do emitente não tem registro na tabela.
        DadosFiscaisAusentesError: se produto não tem ProdutoFiscal.
    """
    # 0. Trava interestadual
    #
    # O critério é a operação, não o endereço cadastrado do cliente. Numa venda
    # presencial a mercadoria sai pelo balcão e não cruza fronteira — é interna
    # mesmo que o comprador more em outra UF. Travar por endereço impedia
    # faturar para qualquer cliente de fora, sem irregularidade alguma.
    #
    # A trava continua valendo para operação não presencial (entrega, internet,
    # teleatendimento), onde a mercadoria realmente circula entre estados e
    # DIFAL/FCP seriam devidos — e não estão implementados.
    if not _operacao_presencial(venda):
        uf_cliente = _obter_uf_cliente(venda)
        if uf_cliente and uf_cliente.upper() != uf_emitente.upper():
            raise OperacaoInterestadualError(
                f"Operação interestadual não presencial detectada (emitente: "
                f"{uf_emitente}, destinatário: {uf_cliente}). O motor fiscal "
                f"atual suporta apenas operações internas. DIFAL/FCP não "
                f"implementado.",
                campo="uf_destinatario",
            )

    # 1. Carregar defaults da UF
    from app.db.crud import fiscal as crud
    aliq_uf = crud.get_aliquota_uf(db, uf_emitente)

    if not aliq_uf and not simples_nacional:
        raise AliquotaNaoEncontradaError(
            f"Alíquota padrão não encontrada para UF '{uf_emitente}'. "
            f"Verifique a tabela aliquota_uf.",
            campo="uf_emitente",
        )

    # Defaults da UF (fallbacks se aliq_uf não existir)
    icms_padrao = _centesimos_para_decimal(
        aliq_uf.aliquota_icms_interna if aliq_uf else None, ZERO,
    )
    pis_padrao = _centesimos_para_decimal(
        aliq_uf.aliquota_pis_padrao if aliq_uf else None, PIS_PADRAO,
    )
    cofins_padrao = _centesimos_para_decimal(
        aliq_uf.aliquota_cofins_padrao if aliq_uf else None, COFINS_PADRAO,
    )

    # 2. Montar itens
    itens_entrada: list[ItemEntrada] = []

    for idx, item_venda in enumerate(venda.itens, start=1):
        produto = item_venda.produto
        fiscal: Optional[ProdutoFiscal] = produto.fiscal if produto else None

        if not fiscal and produto:
            raise DadosFiscaisAusentesError(
                f"Produto '{produto.nome}' (ID {produto.id}) não possui dados "
                f"fiscais preenchidos. Preencha NCM, CFOP e CST/CSOSN antes de emitir.",
                campo="dados_fiscais",
                item=idx,
            )

        # Resolver alíquotas: produto override > UF default
        aliq_icms = _centesimos_para_decimal(
            fiscal.aliquota_icms if fiscal else None, icms_padrao,
        )
        reducao = _centesimos_para_decimal(
            fiscal.reducao_base_icms if fiscal else None, ZERO,
        )
        if simples_nacional:
            # No Simples Nacional o PIS/COFINS já está embutido na guia única.
            # Destacar alíquota na nota gera bitributação aparente e diverge da
            # apuração. Saída sai como CST 49 (Outras Operações), zerada.
            #
            # Vale para CRT 1 e 4. O CRT 2 (excesso de sublimite) NÃO passa por
            # aqui: `simples_nacional` vem de usa_csosn(), que o exclui.
            cst_pis = CST_PIS_COFINS_SIMPLES
            cst_cofins = CST_PIS_COFINS_SIMPLES
            aliq_pis = ZERO
            aliq_cofins = ZERO
        else:
            aliq_pis = _centesimos_para_decimal(
                fiscal.aliquota_pis if fiscal else None, pis_padrao,
            )
            aliq_cofins = _centesimos_para_decimal(
                fiscal.aliquota_cofins if fiscal else None, cofins_padrao,
            )
            cst_pis = fiscal.cst_pis if fiscal and fiscal.cst_pis else "01"
            cst_cofins = fiscal.cst_cofins if fiscal and fiscal.cst_cofins else "01"

        itens_entrada.append(ItemEntrada(
            numero_item=idx,
            produto_id=item_venda.produto_id,
            descricao=produto.nome if produto else (item_venda.descricao_avulsa or "Item avulso"),
            quantidade=Decimal(str(item_venda.quantidade)),
            valor_unitario=_centavos_para_reais(item_venda.valor_unitario),
            valor_bruto=_centavos_para_reais(item_venda.subtotal),
            desconto_item=_centavos_para_reais(item_venda.desconto),
            ncm=fiscal.ncm if fiscal else None,
            cfop=fiscal.cfop_padrao if fiscal else None,
            origem_mercadoria=fiscal.origem_mercadoria if fiscal and fiscal.origem_mercadoria is not None else 0,
            cst_icms=fiscal.cst_icms if fiscal else None,
            csosn=fiscal.csosn if fiscal else None,
            aliquota_icms=aliq_icms,
            reducao_base_icms=reducao,
            codigo_beneficio_fiscal=fiscal.codigo_beneficio_fiscal if fiscal else None,
            aliquota_pis=aliq_pis,
            aliquota_cofins=aliq_cofins,
            cst_pis=cst_pis,
            cst_cofins=cst_cofins,
        ))

    # 3. Montar dados da nota
    dados_nota = DadosNota(
        uf_emitente=uf_emitente.upper(),
        simples_nacional=simples_nacional,
        frete=_centavos_para_reais(venda.entrega),
        seguro=ZERO,              # Venda não tem campo seguro ainda
        # O acréscimo (juros de cartão do checkout) entra em Venda.total e no
        # valor dos pagamentos. Sem ele aqui, o total da nota fica menor que a
        # soma dos vPag e a SEFAZ rejeita (767). Mapeado para vOutro — despesa
        # acessória rateada entre os itens, compondo a base de ICMS.
        outras_despesas=_centavos_para_reais(venda.acrescimo or 0),
        desconto_nota=ZERO,       # Descontos são por item no modelo atual
        excluir_icms_base_pis_cofins=excluir_icms_base_pis_cofins,
    )

    return itens_entrada, dados_nota
