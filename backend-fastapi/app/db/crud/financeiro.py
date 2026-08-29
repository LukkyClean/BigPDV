# ---------------------------------------------------------------------------
# ARQUIVO: db/crud/financeiro.py
# DESCRIÇÃO: Acesso a dados do módulo financeiro — plano de contas, contas
#            bancárias, contas a pagar e a trilha de auditoria.
# ---------------------------------------------------------------------------

from datetime import date
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.enum import (
    ContaPagarStatus,
    ContaReceberStatus,
    MovimentacaoFinanceiraOrigem,
    MovimentacaoFinanceiraTipo,
)
from app.db.models.alerta_dispensado import AlertaDispensado
from app.db.models.conta_bancaria import ContaBancaria
from app.db.models.conta_pagar import ContaPagar
from app.db.models.conta_receber import ContaReceber
from app.db.models.forma_pagamento import FormaPagamento
from app.db.models.funcionario import Funcionario
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira
from app.db.models.ordem_servico import OrdemServico
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento
from app.db.models.venda import Venda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.historico_financeiro import HistoricoFinanceiro
from app.db.models.plano_conta import PlanoConta


# ===========================================================================
# PLANO DE CONTAS
# ===========================================================================

def listar_planos_conta(
    db: Session, empresa_id: int, apenas_ativos: bool = False
) -> Sequence[PlanoConta]:
    q = db.query(PlanoConta).filter(PlanoConta.empresa_id == empresa_id)
    if apenas_ativos:
        q = q.filter(PlanoConta.ativo.is_(True))
    return q.order_by(PlanoConta.tipo.asc(), PlanoConta.nome.asc()).all()


def get_plano_conta(db: Session, empresa_id: int, plano_id: int) -> Optional[PlanoConta]:
    return (
        db.query(PlanoConta)
        .filter(PlanoConta.id == plano_id, PlanoConta.empresa_id == empresa_id)
        .first()
    )


def get_plano_conta_por_nome(
    db: Session, empresa_id: int, nome: str
) -> Optional[PlanoConta]:
    return (
        db.query(PlanoConta)
        .filter(PlanoConta.empresa_id == empresa_id, func.lower(PlanoConta.nome) == nome.lower())
        .first()
    )


def criar_plano_conta(db: Session, plano: PlanoConta) -> PlanoConta:
    db.add(plano)
    db.flush()
    return plano


def ids_de_planos_em_uso(db: Session, empresa_id: int) -> set[int]:
    """Categorias que já classificam alguma conta.

    Uma consulta só para a lista inteira, e não uma por categoria: a tela do
    plano de contas mostra dezenas de linhas, e perguntar "esta está em uso?"
    uma a uma seria o N+1 clássico.
    """
    linhas = (
        db.query(ContaPagar.plano_conta_id)
        .filter(
            ContaPagar.empresa_id == empresa_id,
            ContaPagar.plano_conta_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return {linha[0] for linha in linhas}


# ===========================================================================
# CONTAS BANCÁRIAS
# ===========================================================================

def listar_contas_bancarias(
    db: Session, empresa_id: int, apenas_ativas: bool = False
) -> Sequence[ContaBancaria]:
    q = db.query(ContaBancaria).filter(ContaBancaria.empresa_id == empresa_id)
    if apenas_ativas:
        q = q.filter(ContaBancaria.ativo.is_(True))
    return q.order_by(ContaBancaria.principal.desc(), ContaBancaria.nome.asc()).all()


def get_conta_bancaria(
    db: Session, empresa_id: int, conta_id: int
) -> Optional[ContaBancaria]:
    return (
        db.query(ContaBancaria)
        .filter(ContaBancaria.id == conta_id, ContaBancaria.empresa_id == empresa_id)
        .first()
    )


def criar_conta_bancaria(db: Session, conta: ContaBancaria) -> ContaBancaria:
    db.add(conta)
    db.flush()
    return conta


def limpar_principal(db: Session, empresa_id: int, exceto_id: Optional[int] = None) -> None:
    """Tira a marca de principal das demais contas.

    Só uma conta pode ser a sugerida. Sem isto, marcar a segunda deixaria duas
    principais e a tela escolheria pela ordem do banco, que é arbitrária.
    """
    q = db.query(ContaBancaria).filter(
        ContaBancaria.empresa_id == empresa_id,
        ContaBancaria.principal.is_(True),
    )
    if exceto_id is not None:
        q = q.filter(ContaBancaria.id != exceto_id)
    q.update({ContaBancaria.principal: False}, synchronize_session=False)


# ===========================================================================
# CONTAS A PAGAR
# ===========================================================================

def _query_contas(
    db: Session,
    empresa_id: int,
    *,
    status: Optional[str] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    plano_conta_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
    sem_categoria: bool = False,
    hoje: Optional[date] = None,
):
    """Base compartilhada pela listagem e pelos totais.

    Os dois PRECISAM sair da mesma query: se a soma usasse um filtro e a lista
    outro, o rodapé mostraria um total que não corresponde ao que está na tela —
    e ninguém confia num módulo financeiro depois de ver isso uma vez.
    """
    q = db.query(ContaPagar).filter(ContaPagar.empresa_id == empresa_id)

    if status:
        q = q.filter(ContaPagar.status == status)
    # O período filtra por VENCIMENTO, não por criação: a pergunta da tela é
    # "o que vence neste mês", não "o que eu digitei neste mês".
    if inicio:
        q = q.filter(ContaPagar.vencimento >= inicio)
    if fim:
        q = q.filter(ContaPagar.vencimento <= fim)
    if plano_conta_id:
        q = q.filter(ContaPagar.plano_conta_id == plano_conta_id)
    if fornecedor_id:
        q = q.filter(ContaPagar.fornecedor_id == fornecedor_id)
    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(ContaPagar.descricao.ilike(termo))

    # Os dois recortes que o painel de atenção usa para levar o dono DIRETO às
    # linhas do alerta. Sem eles, "Ver contas a pagar" abre a lista inteira e o
    # dono procura a agulha que o sistema já sabia apontar.
    if vencidas:
        q = q.filter(
            ContaPagar.status == ContaPagarStatus.PENDENTE.value,
            ContaPagar.vencimento < (hoje or date.today()),
        )
    if sem_categoria:
        q = q.filter(ContaPagar.plano_conta_id.is_(None))

    return q


def listar_contas_pagar(
    db: Session,
    empresa_id: int,
    *,
    status: Optional[str] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    plano_conta_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
    sem_categoria: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> Tuple[Sequence[ContaPagar], int]:
    """Devolve a página e a contagem TOTAL do filtro (não a da página)."""
    q = _query_contas(
        db, empresa_id, status=status, inicio=inicio, fim=fim,
        plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
        vencidas=vencidas, sem_categoria=sem_categoria,
    )
    total = q.count()

    itens = (
        q.options(
            # Sem isto a serialização dispara uma consulta por linha só para ler
            # o nome da categoria e do fornecedor.
            joinedload(ContaPagar.plano_conta),
            joinedload(ContaPagar.fornecedor),
            joinedload(ContaPagar.conta_bancaria),
        )
        # Mais urgente primeiro: quem abre a tela quer ver o que vence antes.
        .order_by(ContaPagar.vencimento.asc(), ContaPagar.id.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return itens, total


def totais_contas_pagar(
    db: Session,
    empresa_id: int,
    *,
    hoje: date,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    plano_conta_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
    sem_categoria: bool = False,
) -> Tuple[int, int, int]:
    """(pendente, pago, vencido) do filtro — sem o recorte de status.

    O status é excluído aqui de propósito: o rodapé mostra os três números lado
    a lado, e aplicar o filtro de status faria dois deles virarem zero sempre
    que o usuário filtrasse por um.
    """
    def _soma(coluna, *extra):
        q = _query_contas(
            db, empresa_id, inicio=inicio, fim=fim,
            plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
            vencidas=vencidas, sem_categoria=sem_categoria, hoje=hoje,
        )
        for condicao in extra:
            q = q.filter(condicao)
        return q.with_entities(func.coalesce(func.sum(coluna), 0)).scalar() or 0

    pendente = _soma(ContaPagar.valor, ContaPagar.status == ContaPagarStatus.PENDENTE.value)
    # Soma `valor_pago` e não `valor`: o que interessa no realizado é o que saiu
    # do bolso, com juros de atraso e desconto já dentro.
    pago = _soma(ContaPagar.valor_pago, ContaPagar.status == ContaPagarStatus.PAGA.value)
    vencido = _soma(
        ContaPagar.valor,
        ContaPagar.status == ContaPagarStatus.PENDENTE.value,
        ContaPagar.vencimento < hoje,
    )
    return int(pendente), int(pago), int(vencido)


def get_conta_pagar(db: Session, empresa_id: int, conta_id: int) -> Optional[ContaPagar]:
    return (
        db.query(ContaPagar)
        .options(
            joinedload(ContaPagar.plano_conta),
            joinedload(ContaPagar.fornecedor),
            joinedload(ContaPagar.conta_bancaria),
        )
        .filter(ContaPagar.id == conta_id, ContaPagar.empresa_id == empresa_id)
        .first()
    )


def criar_conta_pagar(db: Session, conta: ContaPagar) -> ContaPagar:
    db.add(conta)
    db.flush()
    return conta


def get_ocorrencia_gerada(
    db: Session, empresa_id: int, conta_id: int
) -> Optional[ContaPagar]:
    """A ocorrência que a baixa desta conta gerou pela recorrência, se houver.

    Serve para os dois lados do problema: impedir que pagar de novo crie uma
    segunda, e permitir que o estorno remova a que aquele pagamento criou.
    """
    return (
        db.query(ContaPagar)
        .filter(
            ContaPagar.empresa_id == empresa_id,
            ContaPagar.gerada_por_id == conta_id,
        )
        .first()
    )


def apagar_conta(db: Session, conta: ContaPagar) -> None:
    """Remove a linha de vez.

    EXCEÇÃO ÚNICA à regra de "cancela, não exclui" -- e as três condições são
    verificadas pelo serviço antes de chegar aqui: a conta foi criada pelo
    SISTEMA (não por uma pessoa), continua PENDENTE (nenhum dinheiro andou), e
    está sendo removida ao desfazer exatamente o pagamento que a criou.

    Cancelar em vez de apagar deixaria um fantasma "Cancelada" na lista a cada
    estorno, de uma conta que ninguém lançou -- ruído sem verdade nenhuma dentro.
    """
    db.delete(conta)
    db.flush()


def proximas_a_vencer(
    db: Session, empresa_id: int, *, ate: date, limite: int = 5
) -> Sequence[ContaPagar]:
    """Pendentes vencendo até `ate`, incluindo as JÁ vencidas.

    As atrasadas entram na mesma lista porque são as mais urgentes de todas —
    separá-las num painel próprio esconderia justamente o que não pode ser
    esquecido.
    """
    return (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.plano_conta), joinedload(ContaPagar.fornecedor))
        .filter(
            ContaPagar.empresa_id == empresa_id,
            ContaPagar.status == ContaPagarStatus.PENDENTE.value,
            ContaPagar.vencimento <= ate,
        )
        .order_by(ContaPagar.vencimento.asc(), ContaPagar.id.asc())
        .limit(limite)
        .all()
    )


def despesas_por_categoria(
    db: Session, empresa_id: int, inicio: date, fim: date
) -> List[Tuple[Optional[int], Optional[str], int]]:
    """(plano_conta_id, nome, total) do que foi PAGO no período.

    Agrupa pela data de PAGAMENTO e não de vencimento: a pergunta é "para onde
    o dinheiro foi neste mês", e uma conta de março paga em abril saiu do caixa
    em abril.
    """
    linhas = (
        db.query(
            ContaPagar.plano_conta_id,
            PlanoConta.nome,
            func.coalesce(func.sum(ContaPagar.valor_pago), 0),
        )
        .outerjoin(PlanoConta, PlanoConta.id == ContaPagar.plano_conta_id)
        .filter(
            ContaPagar.empresa_id == empresa_id,
            ContaPagar.status == ContaPagarStatus.PAGA.value,
            ContaPagar.pago_em >= inicio,
            ContaPagar.pago_em <= fim,
        )
        .group_by(ContaPagar.plano_conta_id, PlanoConta.nome)
        .all()
    )
    return [(linha[0], linha[1], int(linha[2] or 0)) for linha in linhas]


def total_despesas_pagas(db: Session, empresa_id: int, inicio, fim) -> int:
    total = (
        db.query(func.coalesce(func.sum(ContaPagar.valor_pago), 0))
        .filter(
            ContaPagar.empresa_id == empresa_id,
            ContaPagar.status == ContaPagarStatus.PAGA.value,
            ContaPagar.pago_em >= inicio,
            ContaPagar.pago_em <= fim,
        )
        .scalar()
    )
    return int(total or 0)


# ===========================================================================
# AUDITORIA
# ===========================================================================

def registrar_historico(
    db: Session,
    *,
    empresa_id: int,
    entidade: str,
    entidade_id: int,
    campo: str,
    valor_antigo: Optional[str],
    valor_novo: Optional[str],
    funcionario_id: Optional[int],
    funcionario_nome: Optional[str],
) -> HistoricoFinanceiro:
    """O ÚNICO lugar que escreve na trilha de auditoria."""
    linha = HistoricoFinanceiro(
        empresa_id=empresa_id,
        entidade=entidade,
        entidade_id=entidade_id,
        campo=campo,
        valor_antigo=valor_antigo,
        valor_novo=valor_novo,
        funcionario_id=funcionario_id,
        funcionario_nome=funcionario_nome,
    )
    db.add(linha)
    db.flush()
    return linha


def listar_historico(
    db: Session, empresa_id: int, entidade: str, entidade_id: int
) -> Sequence[HistoricoFinanceiro]:
    return (
        db.query(HistoricoFinanceiro)
        .filter(
            HistoricoFinanceiro.empresa_id == empresa_id,
            HistoricoFinanceiro.entidade == entidade,
            HistoricoFinanceiro.entidade_id == entidade_id,
        )
        .order_by(HistoricoFinanceiro.criado_em.desc(), HistoricoFinanceiro.id.desc())
        .all()
    )


# ===========================================================================
# CONTAS A RECEBER
#
# Espelho do contas a pagar. As consultas sao deliberadamente as mesmas, com os
# nomes trocados: quem ler uma entende a outra, e o dia em que a regra do
# "vencido" mudar, muda igual dos dois lados.
# ===========================================================================

def _query_receber(
    db: Session,
    empresa_id: int,
    *,
    status: Optional[str] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    cliente_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
    hoje: Optional[date] = None,
):
    q = db.query(ContaReceber).filter(ContaReceber.empresa_id == empresa_id)
    if status:
        q = q.filter(ContaReceber.status == status)
    if inicio:
        q = q.filter(ContaReceber.vencimento >= inicio)
    if fim:
        q = q.filter(ContaReceber.vencimento <= fim)
    if cliente_id:
        q = q.filter(ContaReceber.cliente_id == cliente_id)
    if busca:
        q = q.filter(ContaReceber.descricao.ilike(f"%{busca.strip()}%"))
    # O mesmo recorte do a pagar, para o alerta de fiado atrasado cair na lista
    # de quem realmente está devendo.
    if vencidas:
        q = q.filter(
            ContaReceber.status == ContaReceberStatus.PENDENTE.value,
            ContaReceber.vencimento < (hoje or date.today()),
        )
    return q


def listar_contas_receber(
    db: Session,
    empresa_id: int,
    *,
    status: Optional[str] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    cliente_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> Tuple[Sequence[ContaReceber], int]:
    q = _query_receber(
        db, empresa_id, status=status, inicio=inicio, fim=fim,
        cliente_id=cliente_id, busca=busca, vencidas=vencidas,
    )
    total = q.count()
    itens = (
        q.options(joinedload(ContaReceber.cliente), joinedload(ContaReceber.conta_bancaria))
        .order_by(ContaReceber.vencimento.asc(), ContaReceber.id.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return itens, total


def totais_contas_receber(
    db: Session,
    empresa_id: int,
    *,
    hoje: date,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    cliente_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
) -> Tuple[int, int, int]:
    """(pendente, recebido, vencido) — sem o recorte de status, como no pagar."""
    def _soma(coluna, *extra):
        q = _query_receber(
            db, empresa_id, inicio=inicio, fim=fim, cliente_id=cliente_id, busca=busca,
            vencidas=vencidas, hoje=hoje,
        )
        for condicao in extra:
            q = q.filter(condicao)
        return q.with_entities(func.coalesce(func.sum(coluna), 0)).scalar() or 0

    pendente = _soma(ContaReceber.valor, ContaReceber.status == ContaReceberStatus.PENDENTE.value)
    recebido = _soma(
        ContaReceber.valor_recebido, ContaReceber.status == ContaReceberStatus.RECEBIDA.value
    )
    vencido = _soma(
        ContaReceber.valor,
        ContaReceber.status == ContaReceberStatus.PENDENTE.value,
        ContaReceber.vencimento < hoje,
    )
    return int(pendente), int(recebido), int(vencido)


def pendentes_por_vencimento(
    db: Session, empresa_id: int, *, inicio: date, fim: date
) -> Tuple[Sequence[ContaPagar], Sequence[ContaReceber]]:
    """As duas pontas do fluxo no mesmo recorte de vencimento, já ordenadas.

    Sai das MESMAS queries base da listagem e dos totais (`_query_contas` e
    `_query_receber`): se o fluxo filtrasse por conta própria, um documento
    poderia aparecer na tela de Contas a Pagar e sumir da projeção — e um fluxo
    de caixa que discorda da lista não serve para decidir nada.
    """
    pagar = (
        _query_contas(db, empresa_id, status=ContaPagarStatus.PENDENTE.value,
                      inicio=inicio, fim=fim)
        .order_by(ContaPagar.vencimento.asc(), ContaPagar.id.asc())
        .all()
    )
    receber = (
        _query_receber(db, empresa_id, status=ContaReceberStatus.PENDENTE.value,
                       inicio=inicio, fim=fim)
        .order_by(ContaReceber.vencimento.asc(), ContaReceber.id.asc())
        .all()
    )
    return pagar, receber


def formas_de_origem(
    db: Session, *, venda_pagamento_ids: Sequence[int], os_pagamento_ids: Sequence[int]
) -> Tuple[dict, dict]:
    """Nome da forma que originou cada cobranca, em DUAS consultas para a lista toda.

    A conta a receber nao guarda a forma de origem -- ela nasce do pagamento, e
    e o pagamento que sabe se foi cartao, PIX ou dinheiro a prazo. Perguntar
    item a item seria o N+1 classico numa tela que lista o mes inteiro.
    """
    por_venda: dict = {}
    por_os: dict = {}

    if venda_pagamento_ids:
        linhas = (
            db.query(PagamentoVenda.id, FormaPagamento.nome)
            .join(FormaPagamento, FormaPagamento.id == PagamentoVenda.forma_pagamento_id)
            .filter(PagamentoVenda.id.in_(venda_pagamento_ids))
            .all()
        )
        por_venda = {pid: nome for pid, nome in linhas}

    if os_pagamento_ids:
        linhas = (
            db.query(OrdemServicoPagamento.id, FormaPagamento.nome)
            .join(FormaPagamento, FormaPagamento.id == OrdemServicoPagamento.forma_pagamento_id)
            .filter(OrdemServicoPagamento.id.in_(os_pagamento_ids))
            .all()
        )
        por_os = {pid: nome for pid, nome in linhas}

    return por_venda, por_os


def get_conta_receber(db: Session, empresa_id: int, conta_id: int) -> Optional[ContaReceber]:
    return (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.cliente), joinedload(ContaReceber.conta_bancaria))
        .filter(ContaReceber.id == conta_id, ContaReceber.empresa_id == empresa_id)
        .first()
    )


def criar_conta_receber(db: Session, conta: ContaReceber) -> ContaReceber:
    db.add(conta)
    db.flush()
    return conta


def get_receber_do_pagamento(
    db: Session,
    empresa_id: int,
    *,
    venda_pagamento_id: Optional[int] = None,
    ordem_servico_pagamento_id: Optional[int] = None,
) -> Optional[ContaReceber]:
    """A conta a receber que este pagamento ja originou, se houver.

    E o que torna a geracao IDEMPOTENTE: uma OS reaberta e refinalizada passa de
    novo pelos mesmos pagamentos, e sem esta checagem a divida do cliente
    dobraria a cada refinalizacao.
    """
    q = db.query(ContaReceber).filter(ContaReceber.empresa_id == empresa_id)
    if venda_pagamento_id is not None:
        q = q.filter(ContaReceber.venda_pagamento_id == venda_pagamento_id)
    elif ordem_servico_pagamento_id is not None:
        q = q.filter(ContaReceber.ordem_servico_pagamento_id == ordem_servico_pagamento_id)
    else:
        return None
    return q.first()


def total_recebido(db: Session, empresa_id: int, inicio, fim) -> int:
    total = (
        db.query(func.coalesce(func.sum(ContaReceber.valor_recebido), 0))
        .filter(
            ContaReceber.empresa_id == empresa_id,
            ContaReceber.status == ContaReceberStatus.RECEBIDA.value,
            ContaReceber.recebido_em >= inicio,
            ContaReceber.recebido_em <= fim,
        )
        .scalar()
    )
    return int(total or 0)


# ===========================================================================
# EXTRATO — o livro do dinheiro, linha a linha
# ===========================================================================

def _query_extrato(
    db: Session,
    empresa_id: int,
    *,
    inicio=None,
    fim=None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
):
    """Base do extrato, com o recorte de empresa feito à mão.

    `movimentacoes_financeiras` NÃO TEM `empresa_id` -- ela nasceu para o
    fechamento de caixa, onde a sessão já dizia de quem era. Aqui a empresa é
    alcançada pelo funcionário ou pela conta bancária da linha.

    A linha SEM funcionário E SEM conta bancária entra assim mesmo, e isso é
    deliberado: uma instalação atende UMA loja (a licença é por máquina), e
    esconder dinheiro de um extrato é pior do que o risco teórico de mostrar
    dinheiro de outra empresa num banco que nunca vai existir em campo. Um
    extrato que omite linha em silêncio não serve para auditoria nenhuma.
    """
    q = (
        db.query(MovimentacaoFinanceira)
        .outerjoin(
            Funcionario, Funcionario.id == MovimentacaoFinanceira.funcionario_id
        )
        .outerjoin(
            ContaBancaria,
            ContaBancaria.id == MovimentacaoFinanceira.conta_bancaria_id,
        )
        .filter(
            or_(
                Funcionario.empresa_id == empresa_id,
                ContaBancaria.empresa_id == empresa_id,
                and_(
                    MovimentacaoFinanceira.funcionario_id.is_(None),
                    MovimentacaoFinanceira.conta_bancaria_id.is_(None),
                ),
            )
        )
    )

    # Filtra por `criado_em`, que é o instante em que o dinheiro ANDOU. O
    # extrato não tem "vencimento": aqui tudo já aconteceu.
    if inicio is not None:
        q = q.filter(MovimentacaoFinanceira.criado_em >= inicio)
    if fim is not None:
        q = q.filter(MovimentacaoFinanceira.criado_em <= fim)
    if tipo:
        q = q.filter(MovimentacaoFinanceira.tipo == tipo)
    if origem:
        q = q.filter(MovimentacaoFinanceira.origem == origem)

    return q


def listar_extrato(
    db: Session,
    empresa_id: int,
    *,
    inicio=None,
    fim=None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> Tuple[Sequence[MovimentacaoFinanceira], int]:
    q = _query_extrato(db, empresa_id, inicio=inicio, fim=fim, tipo=tipo, origem=origem)
    total = q.count()
    itens = (
        q.options(joinedload(MovimentacaoFinanceira.forma_pagamento))
        # Mais recente primeiro: quem abre um extrato quer ver o que acabou de
        # acontecer. O `id` desempata o mesmo instante, que é comum num lote.
        .order_by(
            MovimentacaoFinanceira.criado_em.desc(), MovimentacaoFinanceira.id.desc()
        )
        .limit(limit)
        .offset(offset)
        .all()
    )
    return itens, total


def totais_extrato(
    db: Session,
    empresa_id: int,
    *,
    inicio=None,
    fim=None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
) -> Tuple[int, int]:
    """(entradas, saidas) do MESMO filtro da lista, pela mesma query base."""
    def _soma(valor_tipo: str) -> int:
        return int(
            _query_extrato(
                db, empresa_id, inicio=inicio, fim=fim, tipo=tipo, origem=origem
            )
            .filter(MovimentacaoFinanceira.tipo == valor_tipo)
            .with_entities(func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0))
            .scalar()
            or 0
        )

    return _soma(MovimentacaoFinanceiraTipo.ENTRADA.value), _soma(
        MovimentacaoFinanceiraTipo.SAIDA.value
    )


def documentos_de_origem(
    db: Session, *, venda_pagamento_ids: Sequence[int], os_pagamento_ids: Sequence[int]
) -> Tuple[dict, dict]:
    """Numero da venda / da OS que originou cada movimento, em duas consultas.

    "Entrou R$ 25" nao serve para auditoria; "entrou R$ 25 da venda 3" serve.
    """
    por_venda: dict = {}
    por_os: dict = {}

    if venda_pagamento_ids:
        linhas = (
            db.query(PagamentoVenda.id, Venda.numero_venda)
            .join(Venda, Venda.id == PagamentoVenda.venda_id)
            .filter(PagamentoVenda.id.in_(venda_pagamento_ids))
            .all()
        )
        por_venda = {pid: numero for pid, numero in linhas}

    if os_pagamento_ids:
        linhas = (
            db.query(OrdemServicoPagamento.id, OrdemServico.numero_os)
            .join(
                OrdemServico,
                OrdemServico.id == OrdemServicoPagamento.ordem_servico_id,
            )
            .filter(OrdemServicoPagamento.id.in_(os_pagamento_ids))
            .all()
        )
        por_os = {pid: numero for pid, numero in linhas}

    return por_venda, por_os


# Origens que representam dinheiro de CLIENTE. Abertura, sangria e suprimento
# ficam de fora: são movimento da gaveta, não receita -- somar o troco inicial
# faria a loja "receber" o próprio dinheiro toda manhã.
ORIGENS_DE_RECEITA = (
    MovimentacaoFinanceiraOrigem.VENDA.value,
    MovimentacaoFinanceiraOrigem.ORDEM_SERVICO.value,
    MovimentacaoFinanceiraOrigem.RECEBIMENTO.value,
)


def total_entrou_no_caixa(db: Session, empresa_id: int, inicio, fim) -> int:
    """Quanto dinheiro de cliente ANDOU no período, pelo livro.

    É o contraponto de `faturamento` (que sai das tabelas de venda e OS, por
    COMPETÊNCIA): aqui só conta o que passou pelo caixa, venha da venda de hoje
    ou do fiado do mês passado.

    Desconta as SAÍDAS das mesmas origens, que são os estornos -- sem isso, uma
    OS reaberta deixaria para trás dinheiro que voltou para o cliente.
    """
    def _soma(tipo: str) -> int:
        return int(
            _query_extrato(db, empresa_id, inicio=inicio, fim=fim, tipo=tipo)
            .filter(MovimentacaoFinanceira.origem.in_(ORIGENS_DE_RECEITA))
            .with_entities(func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0))
            .scalar()
            or 0
        )

    return _soma(MovimentacaoFinanceiraTipo.ENTRADA.value) - _soma(
        MovimentacaoFinanceiraTipo.SAIDA.value
    )


# ===========================================================================
# ALERTAS — o atraso mais antigo e o silenciamento
# ===========================================================================

def vencimento_mais_antigo_pendente(
    db: Session, empresa_id: int, *, hoje: date, receber: bool = False
) -> Optional[date]:
    """A conta vencida há mais tempo. É o que gradua a gravidade.

    Business Central deixa o admin digitar o limiar do indicador; aqui a
    pergunta "isto é grave?" se responde com o próprio dado -- e o tempo de
    atraso é metade da resposta (a outra metade é o valor).
    """
    if receber:
        q = db.query(func.min(ContaReceber.vencimento)).filter(
            ContaReceber.empresa_id == empresa_id,
            ContaReceber.status == ContaReceberStatus.PENDENTE.value,
            ContaReceber.vencimento < hoje,
        )
    else:
        q = db.query(func.min(ContaPagar.vencimento)).filter(
            ContaPagar.empresa_id == empresa_id,
            ContaPagar.status == ContaPagarStatus.PENDENTE.value,
            ContaPagar.vencimento < hoje,
        )
    return q.scalar()


def codigos_dispensados(db: Session, empresa_id: int, hoje: date) -> set:
    """Alertas silenciados que ainda não venceram o prazo."""
    linhas = (
        db.query(AlertaDispensado.codigo)
        .filter(
            AlertaDispensado.empresa_id == empresa_id,
            AlertaDispensado.dispensado_ate >= hoje,
        )
        .all()
    )
    return {linha[0] for linha in linhas}


def dispensar_alerta(
    db: Session,
    empresa_id: int,
    *,
    codigo: str,
    ate: date,
    funcionario_id: Optional[int] = None,
    funcionario_nome: Optional[str] = None,
) -> AlertaDispensado:
    """Silencia (ou re-silencia) um alerta até a data.

    Uma linha por empresa/código: adiar de novo ESTENDE o prazo em vez de
    empilhar linhas. Histórico de quem calou o quê é assunto da trilha de
    auditoria, não desta tabela, que existe só para responder "mostrar ou não".
    """
    existente = (
        db.query(AlertaDispensado)
        .filter(
            AlertaDispensado.empresa_id == empresa_id,
            AlertaDispensado.codigo == codigo,
        )
        .first()
    )
    if existente:
        existente.dispensado_ate = ate
        existente.funcionario_id = funcionario_id
        existente.funcionario_nome = funcionario_nome
        db.flush()
        return existente

    registro = AlertaDispensado(
        empresa_id=empresa_id, codigo=codigo, dispensado_ate=ate,
        funcionario_id=funcionario_id, funcionario_nome=funcionario_nome,
    )
    db.add(registro)
    db.flush()
    return registro


def prazo_medio_recebimento(db: Session, empresa_id: int, inicio, fim):
    """Quantos dias, em média, o cliente demorou para pagar.

    Média de (recebido_em - criado_em) das cobranças RECEBIDAS no período.

    Escolhi este cálculo, e não o DSO clássico (recebíveis ÷ receita × dias),
    por uma razão só: o dono precisa poder conferir. "Seus clientes demoram 23
    dias para pagar" se prova abrindo três cobranças e contando no calendário;
    o DSO clássico exige acreditar numa fórmula.

    Feito em Python e não em SQL porque diferença de datas muda de dialeto
    (SQLite não tem DATEDIFF), e o volume de um mês cabe na memória sem
    esforço. Se um dia não couber, vira SQL -- não antes.
    """
    linhas = (
        db.query(ContaReceber.criado_em, ContaReceber.recebido_em)
        .filter(
            ContaReceber.empresa_id == empresa_id,
            ContaReceber.status == ContaReceberStatus.RECEBIDA.value,
            ContaReceber.recebido_em.isnot(None),
            ContaReceber.recebido_em >= inicio,
            ContaReceber.recebido_em <= fim,
        )
        .all()
    )
    dias = [
        (recebido - criado).days
        for criado, recebido in linhas
        if criado is not None and recebido is not None
    ]
    if not dias:
        return None
    # Negativo não existe aqui: recebimento lançado com data anterior à criação
    # da cobrança é digitação, e contá-lo puxaria a média para baixo mentindo
    # que a loja recebe rápido.
    dias = [d for d in dias if d >= 0]
    if not dias:
        return None
    return round(sum(dias) / len(dias))
