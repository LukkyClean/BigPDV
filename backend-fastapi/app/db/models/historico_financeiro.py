# ---------------------------------------------------------------------------
# ARQUIVO: db/models/historico_financeiro.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'historico_financeiro'.
#            Trilha de auditoria dos DOCUMENTOS financeiros.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HistoricoFinanceiro(Base):
    """Quem mudou o quê, quando, de qual valor para qual.

    É a metade que falta da regra das duas camadas. O livro do dinheiro é
    imutável e não precisa de auditoria -- ele É a auditoria. Já o DOCUMENTO
    (uma conta a pagar) muda de propósito: prorrogar vencimento e corrigir valor
    são operações legítimas. Sem esta tabela, "o aluguel era R$ 2.000 e agora
    está R$ 3.500" não teria resposta.

    Genérica por `entidade` + `entidade_id`, e não uma FK: contas a receber
    chegam na Onda 2 e vão precisar do mesmo rastro. Uma tabela por documento
    seria a mesma estrutura copiada, e a consulta "o que mexeram esta semana"
    teria que unir todas.

    Só INSERT. Uma trilha de auditoria que pode ser editada não é trilha de
    auditoria.
    """

    __tablename__ = "historico_financeiro"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- O que foi mexido ---
    entidade: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        doc="Tipo do documento: 'CONTA_PAGAR' (e 'CONTA_RECEBER' na Onda 2)",
    )
    entidade_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True,
        doc="ID do documento. Sem FK de propósito: aponta para tabelas diferentes",
    )

    # --- A mudança ---
    # Texto, não o tipo original: a mesma coluna guarda data, centavos e nome de
    # categoria. Converter para exibir é trabalho da tela; guardar tipado exigiria
    # uma coluna por tipo, e nenhuma delas preenchida na maioria das linhas.
    campo: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Nome do campo alterado, ex.: 'vencimento'"
    )
    valor_antigo: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Como estava, em texto. NULL = campo estava vazio"
    )
    valor_novo: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Como ficou, em texto. NULL = campo foi esvaziado"
    )

    # --- Quem ---
    funcionario_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("funcionarios.id", ondelete="SET NULL"),
        nullable=True,
        doc="Quem fez a alteração",
    )
    # Desnormalizado pela mesma razão do livro do dinheiro e do de estoque:
    # "quem prorrogou o aluguel" precisa sobreviver ao desligamento da pessoa.
    funcionario_nome: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Nome de quem alterou, no momento da alteração"
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True,
        doc="Instante da alteração, em UTC",
    )

    def __repr__(self) -> str:
        return (
            f"<HistoricoFinanceiro({self.entidade}#{self.entidade_id} "
            f"{self.campo}: {self.valor_antigo!r} -> {self.valor_novo!r})>"
        )
