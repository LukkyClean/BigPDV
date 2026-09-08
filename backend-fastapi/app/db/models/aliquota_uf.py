# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/aliquota_uf.py
# DESCRIÇÃO: Tabela de alíquotas padrão por UF.
#            Serve como fallback quando o ProdutoFiscal não define override.
#            Admin pode atualizar quando a legislação mudar.
# ---------------------------------------------------------------------------

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AliquotaUF(Base):
    """
    Alíquotas tributárias padrão por Unidade Federativa.

    Resolução de alíquota: ProdutoFiscal.aliquota_* (override) > AliquotaUF (default).
    Valores em centésimos de ponto percentual (1800 = 18,00%).
    """
    __tablename__ = "aliquota_uf"

    uf: Mapped[str] = mapped_column(
        String(2), primary_key=True,
        doc="Sigla da UF (ex: SP, RJ, MG)"
    )
    aliquota_icms_interna: Mapped[int] = mapped_column(
        Integer, nullable=False,
        doc="Alíquota ICMS interna padrão em centésimos de pp (1800 = 18,00%)"
    )
    aliquota_pis_padrao: Mapped[int] = mapped_column(
        Integer, nullable=False, default=165,
        doc="Alíquota PIS padrão em centésimos de pp (165 = 1,65%)"
    )
    aliquota_cofins_padrao: Mapped[int] = mapped_column(
        Integer, nullable=False, default=760,
        doc="Alíquota COFINS padrão em centésimos de pp (760 = 7,60%)"
    )

    def __repr__(self) -> str:
        return f"<AliquotaUF(uf={self.uf!r}, icms={self.aliquota_icms_interna})>"
