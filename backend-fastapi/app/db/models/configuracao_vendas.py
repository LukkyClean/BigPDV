from datetime import datetime, UTC
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.empresa import Empresa


class ConfiguracaoVendas(Base):
    __tablename__ = "configuracoes_vendas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    permitir_desconto: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    desconto_maximo_percent: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    exigir_cliente_identificado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    valor_minimo_venda: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    permitir_parcelamento: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parcelas_maximas: Mapped[int] = mapped_column(Integer, default=12, nullable=False)

    # =======================================================================
    # CONTROLE DE CAIXA
    # =======================================================================
    # Chaves por EMPRESA, e nao por segmento: e assim que o mercado faz (o Bling
    # tem "Utilizar controle de caixa"; o ERP da Aliare, "Controlar
    # abertura/fechamento de caixa"). Nenhum deles pergunta o ramo do cliente --
    # pergunta se aquela empresa quer o controle. Tem oficina com balcao que quer
    # e tem loja de PDV que nao quer.
    #
    # TODO padrao abaixo reproduz o comportamento de HOJE. Loja que atualiza e
    # nao mexe em nada continua vendendo exatamente como vendia: nenhuma tela
    # nova, nenhuma trava nova. E isso que permite estas colunas chegarem as tres
    # lojas em producao sem risco.

    # Liga o caixa: abertura, sangria, suprimento e fechamento.
    controlar_caixa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # Sem sessao aberta, nao finaliza venda. Separado de `controlar_caixa` porque
    # a loja pode querer o registro sem a trava enquanto se acostuma.
    exigir_caixa_aberto: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # Fechamento cego: o operador digita o que contou SEM ver o esperado, e a
    # diferenca so aparece depois. Desligado por padrao porque na loja pequena o
    # dono e o proprio caixa -- esconder dele o numero que ele mesmo confere e
    # atrito sem ganho. A chave existe desde ja para o dia em que entrar
    # funcionario, sem precisar mexer numa tela que ja roda.
    fechamento_cego: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # Sangria pede permissao ou autorizacao de supervisor na hora. LIGADO por
    # padrao, ao contrario das outras: e a unica que protege dinheiro saindo.
    # Suprimento fica livre de proposito -- por dinheiro na gaveta nao cria risco
    # de desvio, e travar os dois faria o operador chamar o gerente para colocar
    # troco, que e o atrito que faz loja desligar o controle.
    sangria_exige_autorizacao: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="config_vendas",
    )
