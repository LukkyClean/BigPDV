# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/tributacao.py
# DESCRIÇÃO: A tributação da loja e as exceções por NCM.
# ---------------------------------------------------------------------------
"""
Onde a tributação mora.

O PROBLEMA QUE ISTO RESOLVE
---------------------------
Até aqui, CSOSN, CFOP, origem e CST de PIS/COFINS eram perguntados em CADA
produto. São a mesma resposta para a loja inteira: perguntar quarenta vezes o
que se responde uma vez é o que fazia o cadastro parecer impossível de
entender — e o dono da loja, ao ver o campo "CSOSN" com dez opções em
linguagem de lei, não sabia sequer qual procurar.

Nenhum sistema profissional faz isso (pesquisa em 12/09/2026, ver
`docs/cadastro-produto-plano.md` §3.2): TagPlus e Omie guardam a tributação
**por NCM**, o Bling guarda na Natureza de Operação mais grupos de produto, e
em todos eles o produto carrega apenas o que é dele — NCM, origem, CEST.

A CASCATA
---------
    produto (exceção)  →  regra por NCM  →  tributação padrão da loja

Lê-se da esquerda para a direita: o primeiro valor preenchido vence. O produto
continua podendo ter tudo, e nada do que já está cadastrado se perde — o que
existe hoje vira exceção e continua valendo.

SEM CONFIGURAÇÃO, NADA MUDA. Loja que nunca abriu a tela de tributação padrão
não tem linha nenhuma aqui, a cascata não encontra nada para completar e o
comportamento é exatamente o de antes. É o que permite subir isto para três
lojas em produção sem tocar no que elas fazem hoje.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CamposTributacaoMixin:
    """
    Os campos que se repetem no catálogo inteiro.

    NCM, CEST e GTIN **não** estão aqui: são do produto (ou, no caso do CEST,
    do NCM — por isso ele aparece só na regra por NCM, abaixo).

    Todos nullable: vazio significa "não decido isto, pergunte ao próximo nível
    da cascata". É o que permite uma regra de NCM que só diz "este produto tem
    ST" sem repetir CFOP, PIS e COFINS.
    """

    cfop_padrao: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    origem_mercadoria: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ICMS — um OU outro, conforme o CRT. Guardar os dois é permitido de
    # propósito: uma loja que muda de regime não perde a configuração antiga.
    cst_icms: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    csosn: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    aliquota_icms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reducao_base_icms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    codigo_beneficio_fiscal: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # PIS/COFINS
    cst_pis: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    cst_cofins: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    aliquota_pis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aliquota_cofins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Reforma Tributária
    c_class_trib: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cst_ibs_cbs: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    aliquota_ibs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aliquota_cbs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c_benef: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)


class TributacaoPadrao(CamposTributacaoMixin, Base):
    """
    A resposta padrão da loja — uma linha por empresa.

    É o equivalente ao NCM `00000099` ("TODOS NCMs") do TagPlus, cuja ajuda
    diz que empresa do Simples normalmente usa uma única tributação para todos
    os produtos. Aqui ela é uma linha, não um NCM falso.
    """

    __tablename__ = "tributacao_padrao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="Uma tributação padrão por empresa",
    )

    # Quem confirmou, e quando. A confirmação importa: o padrão nasce sugerido
    # pelo motor de derivação, e emitir nota com valor que ninguém olhou é
    # justamente o risco da nota aceita e errada.
    confirmado_em: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    confirmado_por: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    data_atualizacao: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<TributacaoPadrao(empresa_id={self.empresa_id}, csosn={self.csosn!r}, cst={self.cst_icms!r})>"


class RegraTributariaNcm(CamposTributacaoMixin, Base):
    """
    A exceção por NCM — o produto que foge do padrão da loja.

    Quem tem dez pneus cadastra a regra do NCM uma vez e os dez obedecem. É a
    forma do TagPlus e do Omie, e é o que faz o NCM valer mais do que campo
    preenchido: escolher o NCM certo passa a escolher a tributação.

    O CEST mora aqui (e não no padrão da loja) porque é o NCM que determina se
    o produto está em substituição tributária.
    """

    __tablename__ = "regra_tributaria_ncm"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ncm: Mapped[str] = mapped_column(
        String(8), nullable=False, index=True, doc="NCM de 8 dígitos ao qual a regra se aplica"
    )
    cest: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True, doc="CEST do NCM — obrigatório sob substituição tributária"
    )
    descricao: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, doc="Para o usuário reconhecer a regra na lista"
    )

    data_atualizacao: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("empresa_id", "ncm", name="uq_regra_tributaria_empresa_ncm"),
    )

    def __repr__(self) -> str:
        return f"<RegraTributariaNcm(empresa_id={self.empresa_id}, ncm={self.ncm!r})>"
