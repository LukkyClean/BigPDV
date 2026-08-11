from datetime import datetime, UTC
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.empresa import Empresa


class ConfiguracaoBackup(Base):
    __tablename__ = "configuracoes_backup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    backup_automatico_ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    frequencia: Mapped[str] = mapped_column(String(20), default="8horas", nullable=False)
    horario: Mapped[str] = mapped_column(String(5), default="02:00", nullable=False)

    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="config_backup",
    )
