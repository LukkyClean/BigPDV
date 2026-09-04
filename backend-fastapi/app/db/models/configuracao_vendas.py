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
    # Abertura do caixa exige PIN do gerente. Mora AQUI, e nao em
    # `configuracoes_seguranca` junto das irmas de PIN: e uma regra do caixa, e
    # o lojista a procura no bloco do caixa, ao lado de "exigir caixa aberto
    # para vender". A sangria ficou do outro lado (c4d5e6f7a8b9) e a linha de
    # rodape daquele bloco aponta para la -- decisao do dono, registrada aqui
    # para ninguem "arrumar" isso achando que foi descuido.
    #
    # O SEGREDO CONTINUA SENDO UM SO: a validacao le o `pin_gerente` de
    # `configuracoes_seguranca`. Um segundo PIN seria mais uma coisa para
    # esquecer.
    #
    # Padrao False, como todas as outras: loja que atualiza e nao mexe em nada
    # continua abrindo o caixa como abria.
    requer_pin_abrir_caixa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # A fila do caixa: o atendente monta a venda e entrega, outra pessoa recebe.
    #
    # Separada de `controlar_caixa` porque so faz sentido onde ha MAIS DE UMA
    # PESSOA. Numa loja de um PC so, quem monta e quem recebe sao a mesma
    # pessoa, e o botao "Enviar para o caixa" seria um comando que nunca serve --
    # ruido permanente na tela mais usada do sistema.
    #
    # Padrao False, como todas as outras: loja que atualiza e nao mexe em nada
    # nao ve o botao, nem o selo na lista, nem o filtro.
    usar_fila_do_caixa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
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
