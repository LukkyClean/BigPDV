# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/terminal_conectado.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'terminais_conectados'.
#            Armazena os terminais (máquinas) com sessão ativa no sistema.
#            Usado como pivô para envio de heartbeat por terminal.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TerminalConectado(Base):
    """
    Registra cada terminal (máquina) com login ativo no sistema.
    O heartbeat itera sobre esta tabela para enviar POST por HWID.

    - hwid: UNIQUE — um registro por máquina, sem duplicatas.
    - ultima_sinc: atualizado a cada heartbeat bem-sucedido.
    - Sem FK para usuarios — rastreia máquinas, não usuários.
    """
    __tablename__ = "terminais_conectados"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True,
    )
    hwid: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
        doc="Hardware ID do terminal remoto",
    )
    # --- Identidade para gente (não para a máquina) ---
    # O HWID acima é a identidade real; estas duas existem para o dia a dia da
    # loja com mais de um computador. O fechamento precisa dizer "Caixa 02 —
    # João, diferença de R$ 5,00" — um hash não é acionável para o dono.
    #
    # Ambas nullable, e ausência tem significado: terminal sem papel definido se
    # comporta como PDV. É o que faz a loja de um PC só funcionar sem configurar
    # nada, e é por isso que estas colunas não mudam nada para quem já roda.
    nome: Mapped[Optional[str]] = mapped_column(
        String(60), nullable=True,
        doc="Nome amigável do terminal (ex: 'Caixa 01', 'Balcão', 'Escritório')",
    )
    # 'PDV' abre caixa e é cobrado por exigir_caixa_aberto; 'RETAGUARDA' não.
    # A máquina do dono não é um caixa: obrigá-la a abrir turno para consultar
    # relatório criaria uma sessão fantasma que nunca fecha direito.
    papel: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        doc="Papel do terminal: 'PDV' ou 'RETAGUARDA'. NULL = comporta-se como PDV",
    )

    ultima_sinc: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False,
        doc="Timestamp do último heartbeat enviado com sucesso",
    )
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TerminalConectado(id={self.id}, hwid={self.hwid[:8]}...)>"
