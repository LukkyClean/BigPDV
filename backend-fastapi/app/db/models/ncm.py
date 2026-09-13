# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/ncm.py
# DESCRIÇÃO: A tabela NCM, para o lojista achar o código pela descrição.
# ---------------------------------------------------------------------------
"""
NCM pesquisável.

O PROBLEMA
----------
O NCM era um `<input>` de 8 dígitos. Quem cadastra mouse não decora
`8471.60.53`, e errar o NCM não é detalhe: ele determina o imposto, o CEST e
o valor aproximado dos tributos que sai na nota (a Focus calcula o `vTotTrib`
cruzando a tabela IBPT com ele).

POR QUE NO BANCO, E NÃO NUM ARQUIVO LIDO A CADA BUSCA
-----------------------------------------------------
Para reusar `core/busca.py` — o motor de quatro camadas que já atende produto,
cliente e serviço (contém → palavras soltas → acentos e relevância → erro de
digitação). Ler CSV e filtrar em Python seria um segundo mecanismo de busca,
com outro comportamento, na mesma tela.

POR QUE EMBARCADO, E NÃO POR API
--------------------------------
A loja trabalha com internet ruim e o app é offline-first. Cadastrar produto é
tarefa de todo dia; depender de rede para escolher NCM travaria o balcão.

A ORIGEM DOS DADOS
------------------
`app/data/ncm.csv.gz` (253 KB), gerado da tabela oficial. A `descricao_completa`
é a cadeia de ancestrais — capítulo / posição / subposição / item —, porque a
descrição própria de um NCM costuma ser um fragmento: a do 9608.10.00 é apenas
"Canetas esferográficas", e sozinha ela não é encontrável por quem procura
"caneta esferográfica azul".

ATENÇÃO (PyArmor): os dados NÃO podem virar literal Python. O `build:sidecar`
morre com *out of license* quando um módulo passa de ~18 KB de bytecode, e uma
tabela de 10 mil linhas estouraria isso com folga. Por isso arquivo de dados,
declarado no `run.spec`.
"""

from typing import Optional

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Ncm(Base):
    """Um código NCM de 8 dígitos e o que ele descreve."""

    __tablename__ = "ncm"

    codigo: Mapped[str] = mapped_column(
        String(8), primary_key=True, doc="NCM de 8 dígitos, sem pontuação"
    )
    descricao: Mapped[str] = mapped_column(
        String(500), nullable=False, doc="A descrição própria do código"
    )
    descricao_completa: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True,
        doc="A cadeia de ancestrais — é o que a busca varre e o que o usuário lê",
    )

    __table_args__ = (
        # A busca varre a descrição completa; sem índice, cada tecla digitada
        # varreria 10 mil linhas.
        Index("ix_ncm_descricao", "descricao"),
    )

    def __repr__(self) -> str:
        return f"<Ncm({self.codigo} {self.descricao[:40]!r})>"
