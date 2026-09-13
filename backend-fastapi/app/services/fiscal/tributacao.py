# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tributacao.py
# DESCRIÇÃO: A cascata que decide a tributação efetiva de um produto.
# ---------------------------------------------------------------------------
"""
Tributação efetiva: produto → regra por NCM → padrão da loja.

COMO LER A CASCATA
------------------
Campo a campo, o primeiro valor PREENCHIDO vence:

    produto.fiscal.csosn = None  ┐
    regra_ncm.csosn      = None  ├→ efetivo = "102" (veio do padrão da loja)
    padrao.csosn         = "102" ┘

Vazio quer dizer "não decido isto", nunca "apague o que veio". Por isso um
produto pode ter só NCM preenchido e ainda assim emitir: todo o resto desce da
loja.

A PROPRIEDADE QUE PERMITE SUBIR ISTO EM PRODUÇÃO
------------------------------------------------
Sem regra por NCM e sem padrão configurado, `fiscal_efetivo` devolve o próprio
`produto.fiscal`, sem cópia e sem mudança. Três lojas emitem hoje com o modelo
antigo, e nenhuma delas tem linha nestas tabelas — para elas, este arquivo é
inerte. Há teste garantindo exatamente isso.

POR QUE NÃO MATERIALIZAR NO PRODUTO
-----------------------------------
Seria mais simples copiar o padrão para dentro de `produto_fiscal` na hora de
salvar. Mas aí corrigir a alíquota da loja não conserta os produtos já
cadastrados — o lojista teria de reabrir os quarenta. Resolver na leitura é o
que faz a correção valer para o catálogo inteiro, e é como TagPlus e Omie
funcionam.
"""

from dataclasses import dataclass, fields as dataclass_fields
from typing import Any, Optional

from sqlalchemy.orm import Session

# Campos que descem pela cascata. NCM, GTIN e unidade tributável NÃO estão
# aqui: são do produto e de mais ninguém.
CAMPOS_EM_CASCATA = (
    "cfop_padrao",
    "origem_mercadoria",
    "cst_icms",
    "csosn",
    "aliquota_icms",
    "reducao_base_icms",
    "codigo_beneficio_fiscal",
    "cst_pis",
    "cst_cofins",
    "aliquota_pis",
    "aliquota_cofins",
    "c_class_trib",
    "cst_ibs_cbs",
    "aliquota_ibs",
    "aliquota_cbs",
    "c_benef",
)

# O CEST desce junto, mas só a partir da regra por NCM — é o NCM que determina
# a substituição tributária, e o padrão da loja não tem opinião sobre isso.
CAMPO_CEST = "cest"

# Só do produto.
CAMPOS_DO_PRODUTO = ("ncm", "gtin_tributavel", "unidade_tributavel")


@dataclass
class FiscalEfetivo:
    """
    O fiscal do produto depois da cascata.

    Tem os mesmos nomes de atributo de `ProdutoFiscal` de propósito: quem lê
    (payload_builder, tax_engine, validators) não precisa saber se o valor veio
    do produto, do NCM ou da loja.

    `procedencia` guarda de onde cada campo veio — é o que permite a tela dizer
    "CSOSN 102, da tributação padrão da loja" em vez de mostrar um campo
    preenchido sem explicação.
    """

    ncm: Optional[str] = None
    cest: Optional[str] = None
    cfop_padrao: Optional[str] = None
    origem_mercadoria: Optional[int] = None
    unidade_tributavel: Optional[str] = None
    gtin_tributavel: Optional[str] = None
    cst_icms: Optional[str] = None
    csosn: Optional[str] = None
    aliquota_icms: Optional[int] = None
    reducao_base_icms: Optional[int] = None
    codigo_beneficio_fiscal: Optional[str] = None
    cst_pis: Optional[str] = None
    cst_cofins: Optional[str] = None
    aliquota_pis: Optional[int] = None
    aliquota_cofins: Optional[int] = None
    c_class_trib: Optional[str] = None
    cst_ibs_cbs: Optional[str] = None
    aliquota_ibs: Optional[int] = None
    aliquota_cbs: Optional[int] = None
    c_benef: Optional[str] = None

    procedencia: dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.procedencia is None:
            self.procedencia = {}


def _preenchido(valor: Any) -> bool:
    """
    Vazio é `None` e string em branco — zero NÃO é vazio.

    A distinção existe por causa da origem da mercadoria: `0` significa
    "Nacional", e tratá-lo como ausente faria a loja de produto nacional cair
    no padrão em vez de usar o que o produto diz. O mesmo vale para alíquota
    zero, que é uma decisão fiscal legítima.
    """
    if valor is None:
        return False
    if isinstance(valor, str) and valor.strip() == "":
        return False
    return True


def mesclar(
    produto_fiscal: Any = None,
    regra_ncm: Any = None,
    padrao: Any = None,
) -> Optional[FiscalEfetivo]:
    """
    Aplica a cascata. Função pura: recebe objetos com atributos, não Session.

    Returns:
        `FiscalEfetivo` com os valores resolvidos e a procedência de cada um,
        ou `None` quando as três fontes estão ausentes — o que mantém a
        mensagem "produto sem dados fiscais" do gate de emissão.
    """
    if produto_fiscal is None and regra_ncm is None and padrao is None:
        return None

    efetivo = FiscalEfetivo()
    procedencia: dict[str, str] = {}

    # Campos que só o produto responde.
    for campo in CAMPOS_DO_PRODUTO:
        valor = getattr(produto_fiscal, campo, None)
        if _preenchido(valor):
            setattr(efetivo, campo, valor)
            procedencia[campo] = "produto"

    # CEST: produto primeiro, depois a regra do NCM. O padrão da loja não opina.
    for fonte, nome in ((produto_fiscal, "produto"), (regra_ncm, "ncm")):
        valor = getattr(fonte, CAMPO_CEST, None)
        if _preenchido(valor):
            efetivo.cest = valor
            procedencia[CAMPO_CEST] = nome
            break

    # O resto desce pelos três níveis.
    for campo in CAMPOS_EM_CASCATA:
        for fonte, nome in ((produto_fiscal, "produto"), (regra_ncm, "ncm"), (padrao, "padrao")):
            valor = getattr(fonte, campo, None)
            if _preenchido(valor):
                setattr(efetivo, campo, valor)
                procedencia[campo] = nome
                break

    efetivo.procedencia = procedencia
    return efetivo


def fiscal_efetivo(db: Session, produto: Any) -> Any:
    """
    A tributação que vale para este produto, agora.

    Devolve o PRÓPRIO `produto.fiscal` quando não há nada a completar — sem
    cópia, sem objeto novo. É o caminho de toda loja que ainda não configurou
    tributação padrão, e é o que garante que esta mudança não altere o
    comportamento de quem já emite.

    Args:
        db: sessão aberta.
        produto: instância de `Produto` (ou None).

    Returns:
        `ProdutoFiscal`, `FiscalEfetivo` ou None.
    """
    if produto is None:
        return None

    from app.db.crud import tributacao as crud

    produto_fiscal = getattr(produto, "fiscal", None)
    empresa_id = _empresa_do_produto(db, produto)

    padrao = crud.get_tributacao_padrao(db, empresa_id) if empresa_id else None
    regra = None
    ncm = getattr(produto_fiscal, "ncm", None)
    if empresa_id and _preenchido(ncm):
        regra = crud.get_regra_ncm(db, empresa_id, ncm)

    # Nada configurado: devolve o objeto original e sai. Este `return` é o que
    # mantém as lojas em produção com o comportamento exato de antes.
    if padrao is None and regra is None:
        return produto_fiscal

    return mesclar(produto_fiscal=produto_fiscal, regra_ncm=regra, padrao=padrao)


def _empresa_do_produto(db: Session, produto: Any) -> Optional[int]:
    """
    A empresa dona do catálogo.

    O produto não tem `empresa_id`: o banco é local e a instalação atende uma
    empresa só. Perguntar à tabela é mais honesto do que assumir `1`, e é o
    mesmo caminho que o resto do fiscal usa.
    """
    from app.db.models.empresa import Empresa

    empresa = db.query(Empresa.id).first()
    return empresa[0] if empresa else None
