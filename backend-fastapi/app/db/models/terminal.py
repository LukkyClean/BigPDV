# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/terminal.py
# DESCRIÇÃO: Cadastro DURÁVEL de terminais (máquinas), por HWID.
# ---------------------------------------------------------------------------

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Terminal(Base):
    """
    O que a loja sabe sobre cada máquina — e continua sabendo amanhã.

    POR QUE ESTA TABELA EXISTE, SE JÁ HÁ `terminais_conectados`.
    Aquela é tabela de PRESENÇA: é esvaziada no boot, no shutdown e perde a
    linha no logout. Nome e papel moravam lá e evaporavam junto — o dono
    marcava o PC dele como retaguarda, saía no fim do dia, e amanhã a máquina
    voltava a ser um caixa qualquer. A configuração se desfazia sozinha.

    São dois tempos de vida diferentes na mesma máquina:

        Terminal (aqui)                TerminalConectado (presença)
        ├── hwid                       ├── hwid
        ├── nome                       ├── ultima_sinc
        └── papel                      └── vive enquanto há login

    Misturar os dois obrigaria a tabela de heartbeat a ser durável — e ela é
    esvaziada de propósito, porque presença velha é pior que presença nenhuma.

    O HWID é a identidade real da máquina; `nome` existe para gente. O
    fechamento precisa dizer "Caixa 02 — João, diferença de R$ 5,00", e um hash
    não é acionável para o dono.
    """

    __tablename__ = "terminais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    hwid: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
        doc="Hardware ID da máquina — a identidade real, a mesma de terminais_conectados",
    )

    nome: Mapped[Optional[str]] = mapped_column(
        String(60), nullable=True,
        doc="Nome amigável ('Caixa 01', 'Balcão', 'Escritório'). NULL = ainda não batizado",
    )

    # NULL e 'PDV' significam a MESMA coisa, e é a coisa segura: cobra turno.
    #
    # RETAGUARDA é exceção EXPLÍCITA, nunca padrão. Uma máquina que ninguém
    # configurou tem que continuar sendo tratada como caixa — errar para "cobra
    # turno demais" custa um clique de configuração; errar para "não cobra"
    # custa o controle da gaveta, e falha em silêncio: nada quebra, o dinheiro
    # só não bate no fim do dia.
    papel: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        doc="'PDV' ou 'RETAGUARDA'. NULL comporta-se como PDV",
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False,
        doc="Máquina aposentada some da lista sem perder o histórico de turnos",
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False,
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
