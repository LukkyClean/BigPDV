# ---------------------------------------------------------------------------
# ARQUIVO: db/crud/financeiro.py
# DESCRIÇÃO: Acesso a dados do módulo financeiro — plano de contas, contas
#            bancárias, contas a pagar e a trilha de auditoria.
# ---------------------------------------------------------------------------

from datetime import date
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.enum import ContaPagarStatus
from app.db.models.conta_bancaria import ContaBancaria
from app.db.models.conta_pagar import ContaPagar
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
    limit: int = 200,
    offset: int = 0,
) -> Tuple[Sequence[ContaPagar], int]:
    """Devolve a página e a contagem TOTAL do filtro (não a da página)."""
    q = _query_contas(
        db, empresa_id, status=status, inicio=inicio, fim=fim,
        plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
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
