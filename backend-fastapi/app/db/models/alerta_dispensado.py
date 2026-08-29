# ---------------------------------------------------------------------------
# ARQUIVO: db/models/alerta_dispensado.py
# DESCRIÇÃO: Alerta que o dono mandou calar — por um tempo.
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertaDispensado(Base):
    """Um alerta silenciado até uma data.

    POR QUE EXISTE. É o que o NetSuite chama de snooze no portlet de lembretes,
    e é a peça que decide se um painel de alertas sobrevive ao segundo mês. Sem
    ela, "R$ 300 gastos sem categoria" grita todo dia para quem já decidiu não
    categorizar -- e quando o dono aprende a ignorar o painel, some junto o
    aviso que importava.

    ADIAR, NUNCA APAGAR. Não existe "dispensar para sempre": alerta financeiro
    que some de vez vira problema escondido. O prazo devolve o aviso à tela, e
    se o problema tiver sido resolvido no meio tempo ele nem reaparece -- some
    sozinho, porque a regra deixou de valer.

    Uma linha por empresa/código: o alerta é da LOJA, não de quem clicou. Se o
    dono silenciou "sem categoria", o gerente não precisa silenciar de novo --
    e é o mesmo problema em cima da mesma conta.
    """

    __tablename__ = "alertas_dispensados"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_alerta_dispensado_empresa_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    codigo: Mapped[str] = mapped_column(
        String(40), nullable=False, doc="Código do alerta (CONTAS_VENCIDAS, ...)"
    )

    # DATA PURA: não converte fuso. O alerta volta no dia, não no horário.
    dispensado_ate: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        doc="Último dia em que o alerta fica calado; a partir do seguinte, volta",
    )

    # Quem calou, pelo mesmo motivo do `funcionario_nome` no livro do dinheiro:
    # a resposta a "por que ninguém viu isso?" precisa sobreviver ao
    # desligamento de quem clicou.
    funcionario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("funcionarios.id", ondelete="SET NULL"), nullable=True
    )
    funcionario_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
        doc="Instante em que foi silenciado, em UTC",
    )

    def __repr__(self) -> str:
        return f"<AlertaDispensado({self.codigo} até {self.dispensado_ate})>"
