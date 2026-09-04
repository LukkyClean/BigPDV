from datetime import datetime, UTC
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.empresa import Empresa


class ConfiguracaoOS(Base):
    """
    Configurações do módulo de Ordens de Serviço por empresa.
    Relacionamento 1:1 com Empresa.
    """
    __tablename__ = "configuracoes_os"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    prazo_entrega_padrao: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    garantia_padrao: Mapped[str] = mapped_column(String(20), default="90 dias", nullable=False)
    prazo_abandono_dias: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    taxa_diagnostico_padrao: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # -----------------------------------------------------------------------
    # APRESENTACAO DOS COMPROVANTES
    #
    # Só a FORMA. O conteúdo do comprovante é invariante: dados da empresa,
    # dados do cliente com endereço, itens discriminados e resumo exato do
    # pagamento saem SEMPRE, em qualquer empresa e qualquer segmento, porque
    # protegem o cliente. Nao existe configuracao que os remova — e e de
    # proposito: assim nenhuma combinacao produz uma via com a qual a loja nao
    # consiga provar o que entregou.
    #
    # Fica na empresa, e nao na maquina, porque a mesma OS impressa no balcao e
    # na oficina tem que sair igual. A maquina decide so ONDE imprime.
    #
    # Entrada e entrega sao separadas: a via de recebimento e a de entrega tem
    # conteudos quase disjuntos, e a loja costuma querer a entrada enxuta (so
    # protocolo) e a entrega completa.
    #
    # Ver backend-fastapi/docs/comprovantes-perfil-plano.md
    # -----------------------------------------------------------------------
    # 'A4' | 'A5'
    comprovante_entrada_folha: Mapped[str] = mapped_column(String(2), default="A4", nullable=False)
    # 'normal' | 'compacto'
    comprovante_entrada_densidade: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)
    comprovante_entrega_folha: Mapped[str] = mapped_column(String(2), default="A4", nullable=False)
    comprovante_entrega_densidade: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)

    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="config_os",
    )

    def __repr__(self) -> str:
        return f"<ConfiguracaoOS(id={self.id}, empresa_id={self.empresa_id})>"
