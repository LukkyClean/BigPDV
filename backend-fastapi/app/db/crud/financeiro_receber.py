# ---------------------------------------------------------------------------
# ARQUIVO: db/crud/financeiro_receber.py
# DESCRICAO: Acesso a dados do outro lado do dinheiro -- contas a receber, o
#            livro do dinheiro (extrato) e os alertas dispensados.
# ---------------------------------------------------------------------------
"""
Separado de `crud/financeiro.py` em 02/09/2026, pelo MESMO motivo que ja tinha
quebrado o service em quatro tres dias antes: o PyArmor da licenca trial recusa
ofuscar modulo acima de um teto de bytecode, e o crud passou dele.

O teto foi MEDIDO, nao chutado: `ordem_servico.py` (53 KB, 17.900 bytes de
bytecode) passa; o crud com 41 KB e 22.300 de bytecode e recusado com "out of
license". Ou seja, a conta nao e o tamanho do arquivo -- e quanto codigo ele
tem. Comentario e docstring nao contam.

Quando o PyArmor virar licenca paga, nada disto precisa voltar: a divisao
segue a mesma costura dos services (pagar de um lado, receber e leitura do
outro) e continua fazendo sentido sozinha.
"""

from datetime import date, datetime
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

# A UNICA coisa que este modulo busca do outro lado, e de mao unica: o de la nao
# volta aqui, entao nao ha ciclo de import.
#
# E de proposito. `pendentes_por_vencimento` junta as duas pontas do fluxo, e a
# ponta de PAGAR tem que sair da mesma query base da tela de Contas a Pagar --
# um fluxo de caixa que filtrasse por conta propria poderia esconder um
# documento que a lista mostra, e aí nenhum dos dois numeros serve.
from app.db.crud.financeiro import _query_contas

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


def listar_baixas_automaticas_vencidas(
    db: Session, *, hoje: date, limite: int = 500
) -> Sequence[ContaReceber]:
    """Cobrancas marcadas para entrar sozinhas cujo dia ja chegou.

    `<= hoje` e nao `== hoje`: e o que permite a tarefa se recuperar sozinha
    depois de um fim de semana com a maquina desligada. Ver
    `financeiro_receber.baixar_automaticas`.

    ORDENADAS PELO VENCIMENTO, da mais antiga para a mais nova, para o extrato
    contar a historia na ordem em que ela aconteceu.

    O limite existe para o primeiro boot depois de a loja declarar um prazo: se
    houver represa, ela escoa em levas em vez de uma transacao gigante.
    """
    return (
        db.query(ContaReceber)
        .filter(
            ContaReceber.status == ContaReceberStatus.PENDENTE.value,
            ContaReceber.baixa_automatica.is_(True),
            ContaReceber.vencimento <= hoje,
        )
        .order_by(ContaReceber.vencimento.asc(), ContaReceber.id.asc())
        .limit(limite)
        .all()
    )


def formas_de_origem_completas(
    db: Session, *, venda_pagamento_ids: Sequence[int], os_pagamento_ids: Sequence[int]
) -> dict:
    """pagamento_id -> a FormaPagamento inteira (nao so o nome).

    A gemea `formas_de_origem` devolve o nome, que e o que a tela mostra. A
    baixa automatica precisa do OBJETO: e nele que estao `conta_bancaria_id` (em
    que conta o dinheiro cai) e o proprio id, para o movimento nascer sabendo
    como o cliente pagou.

    Chave unica para os dois lados porque ids de pagamento de venda e de OS
    vivem em tabelas diferentes e podem colidir -- quem chama sabe qual dos dois
    a cobranca tem, e so um deles e nao-nulo em cada linha.
    """
    mapa: dict = {}

    if venda_pagamento_ids:
        linhas = (
            db.query(PagamentoVenda.id, FormaPagamento)
            .join(FormaPagamento, FormaPagamento.id == PagamentoVenda.forma_pagamento_id)
            .filter(PagamentoVenda.id.in_(venda_pagamento_ids))
            .all()
        )
        mapa.update({pid: forma for pid, forma in linhas})

    if os_pagamento_ids:
        linhas = (
            db.query(OrdemServicoPagamento.id, FormaPagamento)
            .join(
                FormaPagamento,
                FormaPagamento.id == OrdemServicoPagamento.forma_pagamento_id,
            )
            .filter(OrdemServicoPagamento.id.in_(os_pagamento_ids))
            .all()
        )
        mapa.update({pid: forma for pid, forma in linhas})

    return mapa


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

# As origens que MUDAM QUANTO A LOJA TEM. É a receita mais a despesa paga.
#
# O QUE FICA DE FORA, e é a regra inteira desta lista: ABERTURA, SANGRIA e
# SUPRIMENTO são TRANSFERÊNCIA, não dinheiro entrando ou saindo da loja. O troco
# da abertura já estava no cofre ontem; a sangria tira da gaveta e põe no cofre.
# Somá-los ao saldo criaria dinheiro do nada todo dia em que o caixa abre, e o
# erro cresceria sem parar -- porque o troco de abertura entra de novo amanhã.
#
# E é pior no caso da sangria feita para pagar um boleto: o pagamento já sai
# como DESPESA, então contar a sangria também tiraria o mesmo dinheiro duas
# vezes. É a mesma razão pela qual `pagar_conta` deixa `sessao_caixa_id` nulo de
# propósito -- "pagar fornecedor não é sangria".
ORIGENS_DE_SALDO = ORIGENS_DE_RECEITA + (MovimentacaoFinanceiraOrigem.DESPESA.value,)


def entradas_e_saidas_desde(
    db: Session,
    empresa_id: int,
    *,
    conta_id: int,
    desde: datetime,
    incluir_sem_conta: bool = False,
) -> Tuple[int, int]:
    """(entrou, saiu) nesta conta DEPOIS de `desde`. Os dois positivos.

    DEVOLVE AS DUAS METADES, e nao o liquido, porque a tela mostra as duas: o
    dono perguntou "cade o dinheiro que entrou?" olhando um card que so dizia
    quanto o saldo tinha mudado no total. Um numero liquido de zero pode ser
    "nada aconteceu" ou "entraram 500 e sairam 500", e as duas leituras exigem
    reacoes opostas.

    É a segunda metade do saldo: a primeira é a âncora que o dono declarou, e
    esta é tudo que aconteceu desde então. Entrada soma, saída subtrai.

    `incluir_sem_conta` recolhe as linhas com `conta_bancaria_id` NULO. Elas
    existem por dois motivos e nenhum deles é dinheiro de mentira: as antigas,
    lançadas quando `registrar_movimento` nem aceitava conta, e as de uma loja
    que apagou a conta para onde apontavam (a FK é SET NULL, para linha de
    dinheiro nunca sumir). Descartá-las faria o saldo derivado ficar ABAIXO do
    real, que é justamente o defeito que este código veio corrigir -- então elas
    caem na conta PRINCIPAL, que é para onde os lançamentos novos vão.

    O corte é EXCLUSIVO (`>`), não inclusivo: o movimento do mesmo instante da
    declaração já está dentro do número que o dono contou na gaveta.
    """
    alvo = MovimentacaoFinanceira.conta_bancaria_id == conta_id
    if incluir_sem_conta:
        alvo = or_(alvo, MovimentacaoFinanceira.conta_bancaria_id.is_(None))

    def _soma(tipo: str) -> int:
        return int(
            db.query(func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0))
            .filter(
                alvo,
                MovimentacaoFinanceira.criado_em > desde,
                MovimentacaoFinanceira.tipo == tipo,
                MovimentacaoFinanceira.origem.in_(ORIGENS_DE_SALDO),
            )
            .scalar()
            or 0
        )

    return (
        _soma(MovimentacaoFinanceiraTipo.ENTRADA.value),
        _soma(MovimentacaoFinanceiraTipo.SAIDA.value),
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


def total_saiu_do_caixa(db: Session, empresa_id: int, inicio, fim) -> int:
    """Quanto dinheiro SAIU da loja no período, pelo livro.

    O espelho de `total_entrou_no_caixa`, e lido do livro pelo mesmo motivo:
    somar `contas_pagar.valor_pago` responderia quase igual, mas erraria no
    estorno -- o pagamento desfeito continuaria contado como saída até alguém
    reparar. Aqui a saída volta sozinha, porque o estorno é uma ENTRADA com a
    mesma origem.

    Sangria fica de fora: ver `ORIGENS_DE_SALDO`.
    """
    def _soma(tipo: str) -> int:
        return int(
            _query_extrato(db, empresa_id, inicio=inicio, fim=fim, tipo=tipo)
            .filter(
                MovimentacaoFinanceira.origem
                == MovimentacaoFinanceiraOrigem.DESPESA.value
            )
            .with_entities(func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0))
            .scalar()
            or 0
        )

    return _soma(MovimentacaoFinanceiraTipo.SAIDA.value) - _soma(
        MovimentacaoFinanceiraTipo.ENTRADA.value
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
