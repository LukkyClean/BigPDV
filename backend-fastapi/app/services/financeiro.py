# ---------------------------------------------------------------------------
# ARQUIVO: services/financeiro.py
# DESCRIÇÃO: Regras do módulo de gestão financeira — plano de contas, contas
#            bancárias, contas a pagar, baixa, estorno e o resumo do mês.
# ---------------------------------------------------------------------------
"""
A REGRA QUE ATRAVESSA TUDO AQUI: documento muda, lançamento não.

`contas_pagar` é DOCUMENTO. Prorrogar vencimento e corrigir valor digitado
errado são operações legítimas, e cada uma deixa rastro em
`historico_financeiro`.

`movimentacoes_financeiras` é LANÇAMENTO. Só insere. Um pagamento lançado por
engano não se apaga: estorna-se, com um movimento contrário na data de HOJE.

Confundir as duas camadas é o que faz ERP virar planilha com senha.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.enum import (
    ContaBancariaTipo,
    ContaPagarStatus,
    ContaReceberStatus,
    MovimentacaoFinanceiraOrigem,
    MovimentacaoFinanceiraTipo,
    PlanoContaTipo,
)
from app.core.tempo import agora_utc, fim_do_dia_utc, hoje_local, inicio_do_dia_utc
from app.db.crud import dashboard as dashboard_crud
from app.db.crud import financeiro as financeiro_crud
from app.db.crud import sessao_caixa as caixa_crud
from app.db.models.conta_bancaria import ContaBancaria
from app.db.models.conta_pagar import ContaPagar
from app.db.models.conta_receber import ContaReceber
from app.db.models.plano_conta import PlanoConta
from app.helpers.exceptions import BadRequestException, NotFoundException
from app.schemas.conta_bancaria import ContaBancariaCreate, ContaBancariaUpdate
from app.schemas.conta_pagar import (
    ContaPagarBaixa,
    ContaPagarCreate,
    ContaPagarEstorno,
    ContaPagarUpdate,
)
# `ContaReceberBaixa` é construído AQUI, no lote: cada cobrança do depósito é
# baixada pelo mesmo caminho da baixa manual, com o mesmo schema de entrada.
from app.schemas.conta_receber import ContaReceberBaixa
from app.schemas.financeiro import (
    AlertaFinanceiro,
    Conciliacao,
    ConciliacaoDia,
    ConciliacaoItem,
    ConciliacaoResultado,
    DespesaPorCategoria,
    Extrato,
    ExtratoLinha,
    FluxoCaixa,
    FluxoDia,
    FluxoLancamento,
    ResumoFinanceiro,
)
from app.schemas.plano_conta import PlanoContaCreate, PlanoContaUpdate

ENTIDADE_CONTA_PAGAR = "CONTA_PAGAR"


# ===========================================================================
# PLANO DE CONTAS
# ===========================================================================

# Semeadas no primeiro acesso. Não é adivinhação de negócio: são as despesas que
# TODA loja tem, independente do segmento -- a oficina, a assistência e a
# serigrafia pagam aluguel, luz e fornecedor igual.
#
# Existem porque um plano de contas vazio trava o módulo no primeiro uso: o
# lojista abre Contas a Pagar, vê que precisa de categoria, vai criar categoria,
# e desiste no meio. Ele pode apagar as que não usa; ver a lista e cortar é
# muito mais fácil do que encarar o branco.
PLANO_CONTAS_PADRAO: List[tuple[str, PlanoContaTipo]] = [
    ("Fornecedores / Mercadoria", PlanoContaTipo.DESPESA),
    ("Aluguel", PlanoContaTipo.DESPESA),
    ("Água, luz e internet", PlanoContaTipo.DESPESA),
    ("Salários e encargos", PlanoContaTipo.DESPESA),
    ("Impostos e taxas", PlanoContaTipo.DESPESA),
    ("Manutenção e equipamentos", PlanoContaTipo.DESPESA),
    ("Marketing", PlanoContaTipo.DESPESA),
    ("Outras despesas", PlanoContaTipo.DESPESA),
]


def _semear_plano_padrao(db: Session, empresa_id: int) -> None:
    """Cria as categorias padrão, uma única vez na vida da empresa.

    Roda na LISTAGEM, e não na criação da empresa, para alcançar também as lojas
    que já existem -- nenhuma delas passou por um `setup` que soubesse do módulo
    financeiro.

    A condição é "nunca semeou", e não "a lista está vazia": semear pela lista
    vazia faria as categorias ressuscitarem toda vez que o lojista apagasse
    todas, e ele nunca conseguiria dizer "não quero nenhuma dessas".
    """
    ja_semeou = (
        db.query(PlanoConta)
        .filter(PlanoConta.empresa_id == empresa_id, PlanoConta.padrao.is_(True))
        .first()
    )
    if ja_semeou:
        return

    # Se a loja já criou categoria à mão, ela não é uma instalação virgem —
    # semear por cima só empurraria itens que ela não pediu.
    tem_alguma = (
        db.query(PlanoConta).filter(PlanoConta.empresa_id == empresa_id).first()
    )
    if tem_alguma:
        return

    for nome, tipo in PLANO_CONTAS_PADRAO:
        financeiro_crud.criar_plano_conta(
            db,
            PlanoConta(
                empresa_id=empresa_id, nome=nome, tipo=tipo.value, padrao=True, ativo=True
            ),
        )


def listar_planos_conta(
    db: Session, empresa_id: int, apenas_ativos: bool = False
) -> List[Dict[str, Any]]:
    _semear_plano_padrao(db, empresa_id)

    planos = financeiro_crud.listar_planos_conta(db, empresa_id, apenas_ativos)
    em_uso = financeiro_crud.ids_de_planos_em_uso(db, empresa_id)

    return [
        {
            "id": p.id,
            "nome": p.nome,
            "tipo": p.tipo,
            "padrao": p.padrao,
            "ativo": p.ativo,
            "criado_em": p.criado_em,
            "em_uso": p.id in em_uso,
        }
        for p in planos
    ]


def criar_plano_conta(
    db: Session, empresa_id: int, dados: PlanoContaCreate
) -> Dict[str, Any]:
    nome = dados.nome.strip()
    if financeiro_crud.get_plano_conta_por_nome(db, empresa_id, nome):
        raise BadRequestException(detail=f"Já existe uma categoria chamada '{nome}'.")

    plano = financeiro_crud.criar_plano_conta(
        db, PlanoConta(empresa_id=empresa_id, nome=nome, tipo=dados.tipo.value)
    )
    return {
        "id": plano.id, "nome": plano.nome, "tipo": plano.tipo, "padrao": plano.padrao,
        "ativo": plano.ativo, "criado_em": plano.criado_em, "em_uso": False,
    }


def atualizar_plano_conta(
    db: Session, empresa_id: int, plano_id: int, dados: PlanoContaUpdate
) -> Dict[str, Any]:
    plano = financeiro_crud.get_plano_conta(db, empresa_id, plano_id)
    if not plano:
        raise NotFoundException(detail="Categoria não encontrada")

    if dados.nome is not None:
        nome = dados.nome.strip()
        existente = financeiro_crud.get_plano_conta_por_nome(db, empresa_id, nome)
        if existente and existente.id != plano.id:
            raise BadRequestException(detail=f"Já existe uma categoria chamada '{nome}'.")
        plano.nome = nome

    if dados.ativo is not None:
        plano.ativo = dados.ativo

    db.flush()
    em_uso = plano.id in financeiro_crud.ids_de_planos_em_uso(db, empresa_id)
    return {
        "id": plano.id, "nome": plano.nome, "tipo": plano.tipo, "padrao": plano.padrao,
        "ativo": plano.ativo, "criado_em": plano.criado_em, "em_uso": em_uso,
    }


# ===========================================================================
# CONTAS BANCÁRIAS
# ===========================================================================

def _semear_conta_padrao(db: Session, empresa_id: int) -> None:
    """Garante ao menos 'Caixa da loja'.

    Sem nenhuma conta cadastrada, dar baixa exigiria criar uma antes -- e o
    lojista que só usa dinheiro nunca vai querer cadastrar banco nenhum. A
    gaveta é o mínimo que toda loja tem.
    """
    if db.query(ContaBancaria).filter(ContaBancaria.empresa_id == empresa_id).first():
        return
    financeiro_crud.criar_conta_bancaria(
        db,
        ContaBancaria(
            empresa_id=empresa_id,
            nome="Caixa da loja",
            tipo=ContaBancariaTipo.CAIXA.value,
            principal=True,
        ),
    )


def listar_contas_bancarias(
    db: Session, empresa_id: int, apenas_ativas: bool = False
) -> Sequence[ContaBancaria]:
    _semear_conta_padrao(db, empresa_id)
    return financeiro_crud.listar_contas_bancarias(db, empresa_id, apenas_ativas)


def criar_conta_bancaria(
    db: Session, empresa_id: int, dados: ContaBancariaCreate
) -> ContaBancaria:
    nome = dados.nome.strip()
    ja_existe = any(
        c.nome.lower() == nome.lower()
        for c in financeiro_crud.listar_contas_bancarias(db, empresa_id)
    )
    if ja_existe:
        raise BadRequestException(detail=f"Já existe uma conta chamada '{nome}'.")

    if dados.principal:
        financeiro_crud.limpar_principal(db, empresa_id)

    return financeiro_crud.criar_conta_bancaria(
        db,
        ContaBancaria(
            empresa_id=empresa_id, nome=nome, tipo=dados.tipo.value,
            principal=dados.principal,
        ),
    )


def atualizar_conta_bancaria(
    db: Session, empresa_id: int, conta_id: int, dados: ContaBancariaUpdate
) -> ContaBancaria:
    conta = financeiro_crud.get_conta_bancaria(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")

    if dados.nome is not None:
        conta.nome = dados.nome.strip()
    if dados.tipo is not None:
        conta.tipo = dados.tipo.value
    if dados.ativo is not None:
        conta.ativo = dados.ativo
    if dados.principal is not None:
        if dados.principal:
            financeiro_crud.limpar_principal(db, empresa_id, exceto_id=conta.id)
        conta.principal = dados.principal

    if dados.saldo_informado is not None:
        # A data é carimbada AQUI, e não recebida do cliente: ela é a prova de
        # quando o retrato foi tirado, e o Fluxo de Caixa avisa quando envelhece.
        # Deixar o cliente mandar a data permitiria declarar hoje um saldo
        # "de ontem" e o aviso nunca aparecer.
        conta.saldo_informado = dados.saldo_informado
        conta.saldo_informado_em = hoje_local()

    db.flush()
    return conta


# ===========================================================================
# CONTAS A PAGAR — leitura
# ===========================================================================

def _serializar_conta(conta: ContaPagar, hoje: date) -> Dict[str, Any]:
    """Monta o dicionário da tela, com os campos derivados de hoje.

    `vencida` e `dias_para_vencer` são calculados na leitura, nunca guardados:
    uma coluna "está vencida" precisaria de alguém rodando à meia-noite para
    acertá-la, e ficaria errada em toda máquina que passou a noite desligada --
    que é o caso de praticamente toda loja.
    """
    pendente = conta.status == ContaPagarStatus.PENDENTE.value
    dias = (conta.vencimento - hoje).days if pendente else None

    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "valor": conta.valor,
        "vencimento": conta.vencimento,
        "status": conta.status,
        "plano_conta_id": conta.plano_conta_id,
        "plano_conta_nome": conta.plano_conta.nome if conta.plano_conta else None,
        "fornecedor_id": conta.fornecedor_id,
        "fornecedor_nome": getattr(conta.fornecedor, "nome", None),
        "valor_pago": conta.valor_pago,
        "pago_em": conta.pago_em,
        "conta_bancaria_id": conta.conta_bancaria_id,
        "conta_bancaria_nome": conta.conta_bancaria.nome if conta.conta_bancaria else None,
        "forma_pagamento_id": conta.forma_pagamento_id,
        "recorrente": conta.recorrente,
        "parcelamento_id": conta.parcelamento_id,
        "parcela_numero": conta.parcela_numero,
        "parcela_total": conta.parcela_total,
        "observacao": conta.observacao,
        "criado_em": conta.criado_em,
        "vencida": bool(pendente and conta.vencimento < hoje),
        "dias_para_vencer": dias,
    }


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
) -> Dict[str, Any]:
    hoje = hoje_local()

    itens, total_itens = financeiro_crud.listar_contas_pagar(
        db, empresa_id, status=status, inicio=inicio, fim=fim,
        plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
        limit=limit, offset=offset,
    )
    pendente, pago, vencido = financeiro_crud.totais_contas_pagar(
        db, empresa_id, hoje=hoje, inicio=inicio, fim=fim,
        plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
    )

    return {
        "itens": [_serializar_conta(c, hoje) for c in itens],
        "total_itens": total_itens,
        "total_pendente": pendente,
        "total_pago": pago,
        "total_vencido": vencido,
    }


def get_conta_pagar(db: Session, empresa_id: int, conta_id: int) -> Dict[str, Any]:
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    return _serializar_conta(conta, hoje_local())


def listar_historico_da_conta(db: Session, empresa_id: int, conta_id: int):
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    return financeiro_crud.listar_historico(
        db, empresa_id, ENTIDADE_CONTA_PAGAR, conta_id
    )


# ===========================================================================
# CONTAS A PAGAR — escrita
# ===========================================================================

def _funcionario_do_token(usuario_token: Dict[str, Any]) -> tuple[Optional[int], Optional[str]]:
    """(id, nome) de quem está operando, para o rastro.

    Tolerante a ausência: o Master pode não ter funcionário vinculado, e recusar
    o lançamento por isso deixaria o dono sem conseguir usar o próprio módulo.
    """
    return usuario_token.get("funcionario_id"), usuario_token.get("nome")


def _validar_referencias(
    db: Session, empresa_id: int, plano_conta_id: Optional[int]
) -> None:
    """Impede pendurar a conta numa categoria de OUTRA empresa.

    A FK do banco garante que o ID existe, não que ele é desta loja. Sem esta
    checagem, um ID chutado vazaria o nome da categoria alheia na listagem.
    """
    if plano_conta_id is not None:
        if not financeiro_crud.get_plano_conta(db, empresa_id, plano_conta_id):
            raise BadRequestException(detail="Categoria não encontrada")


def criar_conta_pagar(
    db: Session, empresa_id: int, dados: ContaPagarCreate, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cria a conta — ou TODAS as parcelas, quando `parcelas > 1`.

    Parcelamento gera tudo de uma vez, e não uma parcela por baixa como faz a
    recorrência. O motivo é que as dez parcelas JÁ SÃO dívida hoje: se nascessem
    conforme o pagamento, o fluxo de caixa de dezembro ficaria cego para a
    parcela de dezembro e diria que sobra dinheiro já comprometido.

    É também o que os ERPs fazem — o Odoo gera "um item contábil para cada data
    de vencimento" no momento em que a fatura é lançada.

    Devolve a PRIMEIRA parcela: é ela que a tela acabou de criar do ponto de
    vista do usuário, e é o começo do grupo.
    """
    _validar_referencias(db, empresa_id, dados.plano_conta_id)
    func_id, func_nome = _funcionario_do_token(usuario_token)

    descricao = dados.descricao.strip()
    total = dados.parcelas
    parcelado = total > 1

    primeira: Optional[ContaPagar] = None

    for numero in range(1, total + 1):
        # Sempre a partir do vencimento ORIGINAL, nunca da parcela anterior:
        # ancorar é o que impede o dia encolhido de ficar encolhido.
        vencimento = _somar_meses(dados.vencimento, numero - 1)

        conta = financeiro_crud.criar_conta_pagar(
            db,
            ContaPagar(
                empresa_id=empresa_id,
                descricao=descricao,
                valor=dados.valor,
                vencimento=vencimento,
                plano_conta_id=dados.plano_conta_id,
                fornecedor_id=dados.fornecedor_id,
                recorrente=dados.recorrente,
                observacao=dados.observacao,
                status=ContaPagarStatus.PENDENTE.value,
                parcela_numero=numero if parcelado else None,
                parcela_total=total if parcelado else None,
                # A primeira parcela aponta para si mesma; as demais para ela.
                # É o que dispensa tabela-pai e sequência — o grupo é o id da
                # primeira linha, que o flush do CRUD já devolveu.
                parcelamento_id=(primeira.id if primeira else None) if parcelado else None,
            ),
        )

        if primeira is None:
            primeira = conta
            if parcelado:
                conta.parcelamento_id = conta.id
                db.flush()

        # Só a primeira entra na auditoria: dez linhas de "criação" para uma
        # única compra afogariam a trilha, e o grupo já diz que são a mesma.
        if numero == 1:
            financeiro_crud.registrar_historico(
                db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR,
                entidade_id=conta.id, campo="criacao", valor_antigo=None,
                valor_novo=f"{descricao} ({total}x)" if parcelado else descricao,
                funcionario_id=func_id, funcionario_nome=func_nome,
            )


    db.refresh(primeira)
    return _serializar_conta(primeira, hoje_local())


# Campos cuja alteração o histórico registra. Descrição e observação ficam de
# fora: corrigir uma vírgula na descrição não é fato financeiro, e encher a
# trilha de ruído faz ninguém ler a trilha.
CAMPOS_AUDITADOS = ("valor", "vencimento", "plano_conta_id", "fornecedor_id")


def atualizar_conta_pagar(
    db: Session,
    empresa_id: int,
    conta_id: int,
    dados: ContaPagarUpdate,
    usuario_token: Dict[str, Any],
) -> Dict[str, Any]:
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")

    # Conta paga não se edita: o valor já virou lançamento no livro, e mexer no
    # documento faria a despesa do relatório discordar do movimento. Para
    # corrigir, estorna-se primeiro.
    if conta.status == ContaPagarStatus.PAGA.value:
        raise BadRequestException(
            detail="Esta conta já foi paga. Estorne o pagamento antes de alterá-la."
        )

    _validar_referencias(db, empresa_id, dados.plano_conta_id)
    func_id, func_nome = _funcionario_do_token(usuario_token)

    alteracoes = dados.model_dump(exclude_unset=True)
    for campo, novo in alteracoes.items():
        antigo = getattr(conta, campo)
        if antigo == novo:
            continue

        if campo in CAMPOS_AUDITADOS:
            financeiro_crud.registrar_historico(
                db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR,
                entidade_id=conta.id, campo=campo,
                valor_antigo=str(antigo) if antigo is not None else None,
                valor_novo=str(novo) if novo is not None else None,
                funcionario_id=func_id, funcionario_nome=func_nome,
            )

        setattr(conta, campo, novo.strip() if isinstance(novo, str) else novo)

    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


def cancelar_conta_pagar(
    db: Session, empresa_id: int, conta_id: int, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cancela em vez de excluir.

    Excluir apagaria o rastro de que a conta existiu, e "sumiu uma conta de
    R$ 3.000" é exatamente o tipo de pergunta que o módulo tem que responder.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaPagarStatus.PAGA.value:
        raise BadRequestException(
            detail="Esta conta já foi paga. Estorne o pagamento antes de cancelá-la."
        )

    func_id, func_nome = _funcionario_do_token(usuario_token)
    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="status", valor_antigo=conta.status,
        valor_novo=ContaPagarStatus.CANCELADA.value,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    conta.status = ContaPagarStatus.CANCELADA.value
    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


# ===========================================================================
# BAIXA E ESTORNO — onde o documento vira lançamento
# ===========================================================================

def _somar_meses(base: date, meses: int) -> date:
    """`base` mais N meses, ANCORADO no dia de `base`.

    Encolhe quando o dia não existe no mês de destino (31 em fevereiro vira 28),
    e nunca vaza para o dia 1º do mês seguinte -- vazar atrasaria o alerta em um
    mês inteiro justamente na conta que vence no fim do mês.

    ANCORAR IMPORTA. Calcular cada parcela a partir da ANTERIOR faz o dia
    encolhido ficar encolhido: 31/jan viraria 28/fev e depois 28/mar, quando o
    correto é 31/mar. O erro cresce em silêncio ao longo do parcelamento.
    """
    total = base.month - 1 + meses
    ano = base.year + total // 12
    mes = total % 12 + 1

    dia = base.day
    while dia > 1:
        try:
            return date(ano, mes, dia)
        except ValueError:
            dia -= 1
    return date(ano, mes, 1)


def _proximo_vencimento(vencimento: date) -> date:
    """O mês seguinte, para a RECORRÊNCIA.

    Aqui a âncora é mesmo a conta anterior, e não há outra: a recorrência não
    tem começo guardado -- cada ocorrência nasce da baixa da anterior. A
    consequência é que uma conta de dia 31 encolhe para 28 em fevereiro e assim
    permanece. É uma imprecisão conhecida e aceita: acertá-la exigiria guardar o
    dia original numa coluna, e ninguém contratou aluguel para o dia 31.

    No PARCELAMENTO isso não acontece -- lá existe a primeira parcela como
    âncora, e `_somar_meses` a usa.
    """
    return _somar_meses(vencimento, 1)


def pagar_conta(
    db: Session,
    empresa_id: int,
    conta_id: int,
    dados: ContaPagarBaixa,
    usuario_token: Dict[str, Any],
) -> Dict[str, Any]:
    """Dá baixa: marca a conta como PAGA e escreve no livro do dinheiro.

    As duas coisas na MESMA transação. Uma conta marcada como paga sem o
    lançamento correspondente deixaria o resultado do mês mentindo, e um
    lançamento sem a conta deixaria a despesa órfã no livro.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaPagarStatus.PAGA.value:
        raise BadRequestException(detail="Esta conta já está paga.")
    if conta.status == ContaPagarStatus.CANCELADA.value:
        raise BadRequestException(detail="Esta conta foi cancelada e não pode ser paga.")

    valor_pago = dados.valor_pago if dados.valor_pago is not None else conta.valor
    dia_pagamento = dados.pago_em or hoje_local()

    if dados.conta_bancaria_id is not None:
        if not financeiro_crud.get_conta_bancaria(db, empresa_id, dados.conta_bancaria_id):
            raise BadRequestException(detail="Conta bancária não encontrada")

    func_id, func_nome = _funcionario_do_token(usuario_token)

    # O LANÇAMENTO. Passa pelo mesmo `registrar_movimento` que a venda e a
    # sangria usam: é o único lugar que escreve no livro, e concentrar a escrita
    # é o que impede uma linha de dinheiro nascer sem origem.
    #
    # `sessao_caixa_id` fica NULO de propósito, mesmo quando há caixa aberto:
    # pagar fornecedor não é sangria. Se o dinheiro saiu fisicamente da gaveta, a
    # sangria é lançada à parte pelo operador, e contar as duas coisas faria a
    # gaveta fechar com falta.
    movimento = caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.SAIDA,
        origem=MovimentacaoFinanceiraOrigem.DESPESA,
        valor=valor_pago,
        forma_pagamento_id=dados.forma_pagamento_id,
        funcionario_id=func_id,
        funcionario_nome=func_nome,
        motivo=f"Pagamento: {conta.descricao}",
    )
    movimento.conta_bancaria_id = dados.conta_bancaria_id

    conta.status = ContaPagarStatus.PAGA.value
    conta.valor_pago = valor_pago
    # Guardado como início do dia em UTC: é timestamp de evento e converte
    # (ver core/tempo.py), diferente de `vencimento`, que é data pura.
    conta.pago_em = inicio_do_dia_utc(dia_pagamento)
    conta.conta_bancaria_id = dados.conta_bancaria_id
    conta.forma_pagamento_id = dados.forma_pagamento_id
    conta.movimentacao_financeira_id = movimento.id
    if dados.observacao:
        conta.observacao = dados.observacao

    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="baixa", valor_antigo=ContaPagarStatus.PENDENTE.value,
        valor_novo=f"PAGA {valor_pago}",
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    # Recorrência: a próxima nasce agora, com o valor ORIGINAL da conta e não o
    # pago. A luz veio R$ 80 mais cara este mês por causa do calor; repetir esse
    # valor viraria previsão errada todo mês seguinte.
    #
    # IDEMPOTENTE. Sem a checagem, estornar e pagar de novo criava uma SEGUNDA
    # ocorrência do mês seguinte, e a dívida se multiplicava a cada repetição do
    # ciclo. `gerada_por_id` é o que permite perguntar "já gerei a partir desta?".
    if conta.recorrente and not financeiro_crud.get_ocorrencia_gerada(
        db, empresa_id, conta.id
    ):
        financeiro_crud.criar_conta_pagar(
            db,
            ContaPagar(
                empresa_id=empresa_id,
                descricao=conta.descricao,
                valor=conta.valor,
                vencimento=_proximo_vencimento(conta.vencimento),
                plano_conta_id=conta.plano_conta_id,
                fornecedor_id=conta.fornecedor_id,
                recorrente=True,
                status=ContaPagarStatus.PENDENTE.value,
                gerada_por_id=conta.id,
            ),
        )

    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


def estornar_pagamento(
    db: Session,
    empresa_id: int,
    conta_id: int,
    dados: ContaPagarEstorno,
    usuario_token: Dict[str, Any],
) -> Dict[str, Any]:
    """Desfaz a baixa sem apagar nada do livro.

    O movimento de estorno é lançado com a data de HOJE, jamais na data original.
    `sessao_caixa` PERSISTE `saldo_final_esperado` e `saldo_final_informado`: um
    lançamento retroativo faria a quebra de caixa gravada discordar da
    recalculada, e aí nenhum dos dois números serve para nada.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status != ContaPagarStatus.PAGA.value:
        raise BadRequestException(detail="Só é possível estornar uma conta paga.")

    func_id, func_nome = _funcionario_do_token(usuario_token)
    valor_estornado = conta.valor_pago or conta.valor

    # ENTRADA, o espelho da SAIDA original. Origem segue DESPESA: o par
    # saída + entrada com o mesmo motivo é o que a auditoria lê como estorno,
    # e uma origem própria faria o total de despesas do período ignorá-lo.
    caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.ENTRADA,
        origem=MovimentacaoFinanceiraOrigem.DESPESA,
        valor=valor_estornado,
        forma_pagamento_id=conta.forma_pagamento_id,
        funcionario_id=func_id,
        funcionario_nome=func_nome,
        motivo=f"Estorno de pagamento: {conta.descricao} — {dados.motivo}",
    )

    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="estorno", valor_antigo=f"PAGA {valor_estornado}",
        valor_novo=f"PENDENTE — {dados.motivo}",
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    # Desfaz também a CONSEQUÊNCIA do pagamento: a ocorrência do mês seguinte
    # que a recorrência criou ao dar a baixa.
    #
    # Sem isto, estornar deixava a loja aparentando dever duas contas de
    # internet -- a de setembro, de volta a pendente, e a de outubro, que só
    # existia por causa do pagamento que acabou de ser desfeito.
    #
    # Apaga em vez de cancelar, e é a única exceção à regra da casa: a linha foi
    # criada pelo SISTEMA, nunca teve dinheiro andando, e some ao desfazer
    # exatamente o que a criou. Um fantasma "Cancelada" por estorno seria ruído
    # de uma conta que ninguém lançou.
    #
    # Se a ocorrência JÁ FOI PAGA ou cancelada, fica onde está: aí houve decisão
    # de gente no meio, e apagá-la levaria junto um pagamento de verdade.
    gerada = financeiro_crud.get_ocorrencia_gerada(db, empresa_id, conta.id)
    if gerada is not None and gerada.status == ContaPagarStatus.PENDENTE.value:
        financeiro_crud.apagar_conta(db, gerada)

    # Volta a PENDENTE e limpa a baixa. A CHECK do banco exige coerência: conta
    # não-PAGA não pode carregar `pago_em` nem `valor_pago`.
    conta.status = ContaPagarStatus.PENDENTE.value
    conta.valor_pago = None
    conta.pago_em = None
    conta.conta_bancaria_id = None
    conta.forma_pagamento_id = None
    conta.movimentacao_financeira_id = None

    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


# ===========================================================================
# RESUMO — a Visão Geral
# ===========================================================================

# Uma semana é o ponto em que o retrato do saldo deixa de servir: nele já
# couberam um fim de semana de vendas e as contas do começo do mês.
DIAS_ATE_O_SALDO_ENVELHECER = 7

# ---------------------------------------------------------------------------
# COMO A GRAVIDADE É DECIDIDA
#
# Business Central resolve isto com os "Cues": o indicador muda de cor por
# LIMIAR, e não pelo tipo do dado. Copiamos a ideia e jogamos fora a execução —
# lá o administrador DIGITA os limiares numa tela de setup, e lojista nenhum vai
# abrir uma tela para digitar quanto é muito dinheiro. Aqui o limiar sai do
# porte da própria loja: uma padaria e uma concessionária ganham gravidades
# diferentes sem ninguém configurar nada.
#
# Do Odoo vem a segunda metade: nas atividades dele a cor vem do PRAZO (verde no
# futuro, laranja hoje, vermelho atrasado). Por isso valor e tempo decidem
# juntos — R$ 80 vencidos há três meses é grave, e R$ 80 vencidos ontem não é.
# ---------------------------------------------------------------------------

# 10% do que a loja fatura no mês. Abaixo disso, é ruído para ela.
FRACAO_MATERIAL_DO_FATURAMENTO = 0.10

# Piso, para a loja parada (ou no primeiro mês de uso): sem ele, 10% de zero
# faria QUALQUER centavo vencido virar alerta crítico.
PISO_VALOR_MATERIAL = 20000  # R$ 200,00

# Um mês de atraso é grave por si só, custe o que custar: já passou de
# esquecimento para inadimplência.
DIAS_DE_ATRASO_GRAVE = 30

# Dentro de uma semana já não dá para "resolver depois" — é o horizonte em que
# adiar uma conta ou cobrar um cliente ainda muda o desfecho.
DIAS_ATE_O_APERTO_SER_URGENTE = 7


def _montar_alertas(
    db: Session,
    empresa_id: int,
    *,
    faturamento: int,
    resultado: int,
    a_pagar_vencido: int,
    a_receber_vencido: int,
    categorias: List[DespesaPorCategoria],
    com_projecao: bool,
) -> List[AlertaFinanceiro]:
    """O que precisa de atenção, do mais grave para o menos.

    TODO alerta daqui tem ação possível e uma tela para onde ir. A tentação é
    somar sinal ("faturamento caiu 3%"), e é exatamente assim que um painel de
    alertas morre: quem vê aviso todo dia para de ler, e some junto o aviso que
    importava. Na dúvida, fica de fora.

    Não é IA e não deve ser vendido como tal: são regras explícitas, com limiar
    escrito e defensável -- ver o bloco de constantes acima.
    """
    alertas: List[AlertaFinanceiro] = []
    hoje = hoje_local()

    # O que é "muito dinheiro" PARA ESTA LOJA. É o limiar do Business Central,
    # só que derivado em vez de digitado.
    material = max(
        int(faturamento * FRACAO_MATERIAL_DO_FATURAMENTO), PISO_VALOR_MATERIAL
    )

    def _dias_de_atraso(*, receber: bool) -> int:
        mais_antigo = financeiro_crud.vencimento_mais_antigo_pendente(
            db, empresa_id, hoje=hoje, receber=receber
        )
        return (hoje - mais_antigo).days if mais_antigo else 0

    def _gravidade(valor: int, dias: int) -> str:
        """Valor material OU atraso longo. Qualquer um dos dois basta."""
        if valor >= material or dias >= DIAS_DE_ATRASO_GRAVE:
            return "CRITICO"
        return "ATENCAO"

    # 1. O DINHEIRO VAI ACABAR. O mais grave que o módulo sabe dizer, e o único
    #    que olha para frente. Só existe com FINANCEIRO_PRO (é o Fluxo de Caixa
    #    respondendo) e só faz sentido com saldo declarado -- sem ponto de
    #    partida, "ficar negativo" não significa nada.
    if com_projecao:
        fluxo = get_fluxo_caixa(db, empresa_id, dias=30)
        if fluxo.saldo_declarado and fluxo.primeiro_dia_negativo:
            faltam = (fluxo.primeiro_dia_negativo - hoje).days
            alertas.append(
                AlertaFinanceiro(
                    codigo="CAIXA_NEGATIVO",
                    # Longe ainda dá para resolver sem susto; dentro da semana,
                    # não. A urgência vem do prazo, como nas atividades do Odoo.
                    severidade=(
                        "CRITICO" if faltam <= DIAS_ATE_O_APERTO_SER_URGENTE else "ATENCAO"
                    ),
                    data=fluxo.primeiro_dia_negativo,
                    valor=fluxo.menor_saldo,
                    quantidade=faltam,
                )
            )

    # 2. Dívida vencida: já passou do prazo e continua devida.
    if a_pagar_vencido > 0:
        dias = _dias_de_atraso(receber=False)
        alertas.append(
            AlertaFinanceiro(
                codigo="CONTAS_VENCIDAS",
                severidade=_gravidade(a_pagar_vencido, dias),
                valor=a_pagar_vencido,
                quantidade=dias,
            )
        )

    # 3. Fiado atrasado: dinheiro na rua que já deveria ter voltado.
    if a_receber_vencido > 0:
        dias = _dias_de_atraso(receber=True)
        alertas.append(
            AlertaFinanceiro(
                codigo="FIADO_ATRASADO",
                severidade=_gravidade(a_receber_vencido, dias),
                valor=a_receber_vencido,
                quantidade=dias,
            )
        )

    # 4. O mês fechou no vermelho. Sem link para "resolver" -- a ação é olhar
    #    para onde o dinheiro foi, que está logo abaixo na mesma tela.
    if resultado < 0:
        alertas.append(
            AlertaFinanceiro(
                codigo="MES_NO_VERMELHO",
                severidade="CRITICO" if -resultado >= material else "ATENCAO",
                valor=resultado,
            )
        )

    # 5 e 6. O saldo é a base de toda projeção. Nunca informado é pior que
    #        desatualizado, e por isso são dois alertas e não um. Nenhum dos
    #        dois é CRÍTICO: é falta de informação, não perda de dinheiro.
    contas = financeiro_crud.listar_contas_bancarias(db, empresa_id, apenas_ativas=True)
    datas = [c.saldo_informado_em for c in contas if c.saldo_informado_em]
    if not datas:
        alertas.append(
            AlertaFinanceiro(codigo="SALDO_NUNCA_INFORMADO", severidade="ATENCAO")
        )
    else:
        # A conta mais ANTIGA é a que envelhece o número: quem atualizou o banco
        # hoje e esqueceu a gaveta há um mês tem um saldo de um mês atrás.
        mais_antiga = min(datas)
        dias = (hoje - mais_antiga).days
        if dias >= DIAS_ATE_O_SALDO_ENVELHECER:
            alertas.append(
                AlertaFinanceiro(
                    codigo="SALDO_DESATUALIZADO", severidade="ATENCAO",
                    data=mais_antiga, quantidade=dias,
                )
            )

    # 7. Gasto sem categoria: o gráfico "para onde o dinheiro foi" não responde
    #    nada enquanto a maior fatia se chamar "Sem categoria". Nunca crítico --
    #    é organização, não dinheiro em risco.
    sem_categoria = next(
        (c for c in categorias if c.plano_conta_id is None and c.total > 0), None
    )
    if sem_categoria:
        alertas.append(
            AlertaFinanceiro(
                codigo="DESPESA_SEM_CATEGORIA", severidade="ATENCAO",
                valor=sem_categoria.total,
            )
        )

    # O SILÊNCIO PEDIDO PELO DONO, aplicado no fim de propósito: o alerta é
    # calculado de qualquer jeito e só então some da lista. Assim, quando o
    # prazo expira, ele volta com o número de HOJE -- e não com o de quando foi
    # silenciado.
    calados = financeiro_crud.codigos_dispensados(db, empresa_id, hoje)
    alertas = [a for a in alertas if a.codigo not in calados]

    # Crítico antes de atenção, preservando a ordem de urgência dentro de cada
    # grupo (o `sorted` do Python é estável).
    return sorted(alertas, key=lambda a: 0 if a.severidade == "CRITICO" else 1)


# Só estes códigos podem ser silenciados. Lista fechada para a rota não virar
# porta de entrada de linha inventada na tabela.
CODIGOS_DE_ALERTA = (
    "CAIXA_NEGATIVO",
    "CONTAS_VENCIDAS",
    "FIADO_ATRASADO",
    "MES_NO_VERMELHO",
    "SALDO_NUNCA_INFORMADO",
    "SALDO_DESATUALIZADO",
    "DESPESA_SEM_CATEGORIA",
)


def adiar_alerta(
    db: Session, empresa_id: int, codigo: str, dias: int, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cala um alerta por `dias`. Nunca para sempre.

    "Dispensar de vez" não existe aqui, e a diferença é de propósito: alerta
    financeiro que some para sempre vira problema escondido. O prazo devolve o
    aviso; se o problema tiver sido resolvido no meio tempo, ele nem reaparece,
    porque a regra deixou de valer.
    """
    if codigo not in CODIGOS_DE_ALERTA:
        raise BadRequestException(detail="Alerta desconhecido.")

    func_id, func_nome = _funcionario_do_token(usuario_token)
    ate = hoje_local() + timedelta(days=dias)
    registro = financeiro_crud.dispensar_alerta(
        db, empresa_id, codigo=codigo, ate=ate,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    return {"codigo": registro.codigo, "dispensado_ate": registro.dispensado_ate}


def get_resumo(
    db: Session,
    empresa_id: int,
    inicio: date,
    fim: date,
    com_projecao: bool = False,
) -> ResumoFinanceiro:
    """Entrou, saiu, sobrou — em regime de caixa. Ver o docstring do schema."""
    hoje = hoje_local()
    dt_inicio, dt_fim = inicio_do_dia_utc(inicio), fim_do_dia_utc(fim)

    # Faturamento sai da MESMA fonte do dashboard e dos relatórios. Recalcular
    # aqui abriria a porta para o financeiro mostrar um número e o relatório
    # outro, para o mesmo mês.
    stats = dashboard_crud.get_stats_agregados(db, dt_inicio, dt_fim, empresa_id)
    faturamento = int(stats.vendas_total or 0) + int(stats.os_soma or 0)

    despesas = financeiro_crud.total_despesas_pagas(db, empresa_id, dt_inicio, dt_fim)

    # A OUTRA LEITURA do que entrou: pelo livro, não pelas tabelas de venda.
    #
    # `faturamento` responde "quanto a loja vendeu"; este responde "quanto
    # dinheiro passou pelo caixa". Os dois divergem por motivo legítimo (fiado
    # vendido agora, fiado antigo quitado agora) e a tela mostra os dois em vez
    # de escolher um -- trocar o faturamento por este apagaria da tela o mês
    # inteiro de quem vende a prazo.
    entrou_caixa = financeiro_crud.total_entrou_no_caixa(
        db, empresa_id, dt_inicio, dt_fim
    )

    # Em aberto ATÉ O FIM DO MÊS VISTO, sem piso de data.
    #
    # Sem o teto, este era o único número da tela que ignorava o mês: olhando
    # agosto, o card somava contas de outubro. Foi assim que o primeiro uso real
    # pegou o defeito -- pagar a internet de setembro criou a de outubro pela
    # recorrência, e o total "em aberto" não se moveu, porque uma saiu e a outra
    # entrou na mesma soma.
    #
    # Sem o piso porque conta atrasada de mês anterior continua sendo devida:
    # ela precisa aparecer aqui, não sumir junto com o mês que passou.
    pendente, _pago, vencido = financeiro_crud.totais_contas_pagar(
        db, empresa_id, hoje=hoje, fim=fim
    )

    # O outro lado da rua: SEM o teto de data que o a pagar tem.
    #
    # Não é descuido. O teto do a pagar nasceu da recorrência (pagar a de
    # setembro criava a de outubro, e o total não se movia), e cobrança não se
    # reproduz na baixa. Do outro lado, fiado quase sempre vence no mês
    # seguinte: com teto, o card mostraria zero em todo mês que o dono
    # consegue abrir -- a Visão Geral trava o botão de avançar.
    #
    # Não entra no resultado: a venda fiado já está em `faturamento`, e somá-la
    # de novo contaria o mesmo dinheiro duas vezes. O card responde outra
    # pergunta -- quanto do que já vendi ainda não recebi.
    a_receber, _recebido, a_receber_vencido = financeiro_crud.totais_contas_receber(
        db, empresa_id, hoje=hoje
    )

    categorias = [
        DespesaPorCategoria(
            plano_conta_id=plano_id,
            nome=nome or "Sem categoria",
            total=total,
        )
        for plano_id, nome, total in financeiro_crud.despesas_por_categoria(
            db, empresa_id, dt_inicio, dt_fim
        )
    ]
    categorias.sort(key=lambda c: c.total, reverse=True)

    # Uma semana para frente: prazo em que ainda dá para agir (pedir prazo,
    # remanejar dinheiro). Um mês encheria o painel de coisa que não é urgente.
    proximas = financeiro_crud.proximas_a_vencer(
        db, empresa_id, ate=hoje + timedelta(days=7), limite=5
    )

    return ResumoFinanceiro(
        periodo_inicio=inicio,
        periodo_fim=fim,
        faturamento=faturamento,
        entrou_caixa=entrou_caixa,
        despesas_pagas=despesas,
        resultado=faturamento - despesas,
        a_pagar_pendente=pendente,
        a_pagar_vencido=vencido,
        a_receber_pendente=a_receber,
        a_receber_vencido=a_receber_vencido,
        despesas_por_categoria=categorias,
        proximas_a_vencer=[_serializar_conta(c, hoje) for c in proximas],
        alertas=_montar_alertas(
            db, empresa_id,
            faturamento=faturamento,
            resultado=faturamento - despesas,
            a_pagar_vencido=vencido,
            a_receber_vencido=a_receber_vencido,
            categorias=categorias,
            com_projecao=com_projecao,
        ),
    )


# ===========================================================================
# CONTAS A RECEBER — geração a partir da promessa
# ===========================================================================

ENTIDADE_CONTA_RECEBER = "CONTA_RECEBER"


def _nome_do_cliente(cliente) -> Optional[str]:
    return getattr(cliente, "nome", None) if cliente else None


def _criar_promessa(
    db: Session,
    empresa_id: int,
    *,
    descricao: str,
    cliente_id: Optional[int],
    valor: int,
    vencimento: date,
    venda_pagamento_id: Optional[int] = None,
    ordem_servico_pagamento_id: Optional[int] = None,
) -> Optional[ContaReceber]:
    """Cria a conta a receber de UM pagamento prometido.

    IDEMPOTENTE. Uma OS reaberta e refinalizada passa de novo pelos mesmos
    pagamentos; sem a checagem, a dívida do cliente dobraria a cada
    refinalização. Mesma lição do `gerada_por_id` na recorrência.
    """
    if financeiro_crud.get_receber_do_pagamento(
        db,
        empresa_id,
        venda_pagamento_id=venda_pagamento_id,
        ordem_servico_pagamento_id=ordem_servico_pagamento_id,
    ):
        return None

    return financeiro_crud.criar_conta_receber(
        db,
        ContaReceber(
            empresa_id=empresa_id,
            descricao=descricao,
            cliente_id=cliente_id,
            valor=valor,
            vencimento=vencimento,
            status=ContaReceberStatus.PENDENTE.value,
            venda_pagamento_id=venda_pagamento_id,
            ordem_servico_pagamento_id=ordem_servico_pagamento_id,
        ),
    )


def registrar_promessas_de_venda(db: Session, venda) -> None:
    """Transforma em conta a receber cada pagamento de venda com vencimento futuro.

    NÃO decide o que é promessa — só registra. Quem decide já existia:
    `registrar_pagamentos_de_venda` pula o pagamento com vencimento futuro no
    livro do dinheiro, com a regra escrita lá ("promessa: é conta a receber, não
    gaveta"). Esta função é o outro lado dessa frase, que faltava.

    Roda com o caixa LIGADO OU DESLIGADO, ao contrário da irmã do livro: fiado é
    fiado em qualquer loja, e amarrar o contas a receber ao controle de caixa
    esconderia a dívida de quem não usa gaveta.
    """
    funcionario = getattr(venda, "funcionario", None)
    empresa_id = getattr(funcionario, "empresa_id", None)
    if not empresa_id:
        return

    hoje = hoje_local()
    cliente = getattr(venda, "cliente", None)
    nome = _nome_do_cliente(cliente)
    referencia = venda.numero_venda or venda.id

    for pagamento in venda.pagamentos:
        if not pagamento.vencimento or pagamento.vencimento <= hoje:
            continue
        _criar_promessa(
            db,
            empresa_id,
            descricao=f"Venda {referencia}" + (f" — {nome}" if nome else ""),
            cliente_id=venda.cliente_id,
            valor=pagamento.valor,
            vencimento=pagamento.vencimento,
            venda_pagamento_id=pagamento.id,
        )


def registrar_promessas_de_os(db: Session, ordem_servico, pagamentos) -> None:
    """Gêmea da de venda, para a OS.

    `pagamentos` são os desta finalização. A idempotência cobre a refinalização
    de qualquer forma, mas passar só os novos evita consulta à toa.
    """
    funcionario = getattr(ordem_servico, "funcionario", None)
    empresa_id = getattr(funcionario, "empresa_id", None)
    if not empresa_id:
        return

    hoje = hoje_local()
    objeto = getattr(ordem_servico, "equipamento", None)
    cliente = getattr(objeto, "cliente", None)
    nome = _nome_do_cliente(cliente)
    cliente_id = getattr(cliente, "id", None)

    for pagamento in pagamentos:
        if not pagamento.vencimento or pagamento.vencimento <= hoje:
            continue
        _criar_promessa(
            db,
            empresa_id,
            descricao=f"OS {ordem_servico.numero_os}" + (f" — {nome}" if nome else ""),
            cliente_id=cliente_id,
            valor=pagamento.valor,
            vencimento=pagamento.vencimento,
            ordem_servico_pagamento_id=pagamento.id,
        )


# ===========================================================================
# CONTAS A RECEBER — leitura, baixa e estorno
#
# Espelho do contas a pagar. Onde a regra é a mesma, o código é o mesmo com os
# nomes trocados -- de propósito: quem entende um lado entende o outro, e o dia
# em que a regra mudar, muda igual nos dois.
# ===========================================================================

def _serializar_receber(conta: ContaReceber, hoje: date) -> Dict[str, Any]:
    pendente = conta.status == ContaReceberStatus.PENDENTE.value
    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "valor": conta.valor,
        "taxa": conta.taxa,
        "juros": conta.juros,
        "juros_destino": conta.juros_destino,
        "vencimento": conta.vencimento,
        "status": conta.status,
        "cliente_id": conta.cliente_id,
        "cliente_nome": _nome_do_cliente(conta.cliente),
        "valor_recebido": conta.valor_recebido,
        "recebido_em": conta.recebido_em,
        "conta_bancaria_id": conta.conta_bancaria_id,
        "conta_bancaria_nome": conta.conta_bancaria.nome if conta.conta_bancaria else None,
        "forma_pagamento_id": conta.forma_pagamento_id,
        "venda_pagamento_id": conta.venda_pagamento_id,
        "ordem_servico_pagamento_id": conta.ordem_servico_pagamento_id,
        # "Automática" = reflexo de um documento fechado. A tela usa para não
        # oferecer edição livre de algo que a venda ou a OS já decidiu.
        "automatica": bool(conta.venda_pagamento_id or conta.ordem_servico_pagamento_id),
        "observacao": conta.observacao,
        "criado_em": conta.criado_em,
        "vencida": bool(pendente and conta.vencimento < hoje),
        "dias_para_vencer": (conta.vencimento - hoje).days if pendente else None,
    }


def listar_contas_receber(
    db: Session,
    empresa_id: int,
    *,
    status: Optional[str] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    cliente_id: Optional[int] = None,
    busca: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    hoje = hoje_local()
    itens, total_itens = financeiro_crud.listar_contas_receber(
        db, empresa_id, status=status, inicio=inicio, fim=fim,
        cliente_id=cliente_id, busca=busca, limit=limit, offset=offset,
    )
    pendente, recebido, vencido = financeiro_crud.totais_contas_receber(
        db, empresa_id, hoje=hoje, inicio=inicio, fim=fim,
        cliente_id=cliente_id, busca=busca,
    )
    return {
        "itens": [_serializar_receber(c, hoje) for c in itens],
        "total_itens": total_itens,
        "total_pendente": pendente,
        "total_recebido": recebido,
        "total_vencido": vencido,
    }


def get_conta_receber(db: Session, empresa_id: int, conta_id: int) -> Dict[str, Any]:
    conta = financeiro_crud.get_conta_receber(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    return _serializar_receber(conta, hoje_local())


def criar_conta_receber(
    db: Session, empresa_id: int, dados, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Lançamento manual — o que não passou pela venda nem pela OS.

    A maioria das contas a receber nasce sozinha, do fecho. Esta porta existe
    para o cliente que já devia antes do módulo existir, ou para um acerto
    combinado fora do balcão.
    """
    conta = financeiro_crud.criar_conta_receber(
        db,
        ContaReceber(
            empresa_id=empresa_id,
            descricao=dados.descricao.strip(),
            valor=dados.valor,
            taxa=dados.taxa,
            vencimento=dados.vencimento,
            cliente_id=dados.cliente_id,
            observacao=dados.observacao,
            status=ContaReceberStatus.PENDENTE.value,
        ),
    )
    func_id, func_nome = _funcionario_do_token(usuario_token)
    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_RECEBER, entidade_id=conta.id,
        campo="criacao", valor_antigo=None, valor_novo=conta.descricao,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    db.refresh(conta)
    return _serializar_receber(conta, hoje_local())


CAMPOS_AUDITADOS_RECEBER = ("valor", "vencimento", "cliente_id", "taxa")


def atualizar_conta_receber(
    db: Session, empresa_id: int, conta_id: int, dados, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    conta = financeiro_crud.get_conta_receber(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaReceberStatus.RECEBIDA.value:
        raise BadRequestException(
            detail="Esta conta já foi recebida. Estorne o recebimento antes de alterá-la."
        )

    func_id, func_nome = _funcionario_do_token(usuario_token)
    for campo, novo in dados.model_dump(exclude_unset=True).items():
        antigo = getattr(conta, campo)
        if antigo == novo:
            continue
        if campo in CAMPOS_AUDITADOS_RECEBER:
            financeiro_crud.registrar_historico(
                db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_RECEBER,
                entidade_id=conta.id, campo=campo,
                valor_antigo=str(antigo) if antigo is not None else None,
                valor_novo=str(novo) if novo is not None else None,
                funcionario_id=func_id, funcionario_nome=func_nome,
            )
        setattr(conta, campo, novo.strip() if isinstance(novo, str) else novo)

    db.flush()
    db.refresh(conta)
    return _serializar_receber(conta, hoje_local())


def cancelar_conta_receber(
    db: Session, empresa_id: int, conta_id: int, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cancela em vez de excluir. Dívida perdoada continua sendo história."""
    conta = financeiro_crud.get_conta_receber(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaReceberStatus.RECEBIDA.value:
        raise BadRequestException(
            detail="Esta conta já foi recebida. Estorne o recebimento antes de cancelá-la."
        )

    func_id, func_nome = _funcionario_do_token(usuario_token)
    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_RECEBER, entidade_id=conta.id,
        campo="status", valor_antigo=conta.status,
        valor_novo=ContaReceberStatus.CANCELADA.value,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    conta.status = ContaReceberStatus.CANCELADA.value
    db.flush()
    db.refresh(conta)
    return _serializar_receber(conta, hoje_local())


def receber_conta(
    db: Session, empresa_id: int, conta_id: int, dados, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Dá baixa: a promessa vira dinheiro, e o livro registra a ENTRADA.

    É o momento que o fecho da venda já deixava marcado no código -- "o
    movimento nasce no dia em que o cliente pagar". Origem RECEBIMENTO,
    reservada para isto desde a primeira versão do enum.

    `sessao_caixa_id` fica NULO, como no pagamento de conta a pagar: quitar uma
    dívida antiga não é venda no PDV. Se o dinheiro entrou na gaveta, o operador
    lança um suprimento -- contar as duas coisas faria a gaveta fechar com sobra.
    """
    conta = financeiro_crud.get_conta_receber(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaReceberStatus.RECEBIDA.value:
        raise BadRequestException(detail="Esta conta já foi recebida.")
    if conta.status == ContaReceberStatus.CANCELADA.value:
        raise BadRequestException(detail="Esta conta foi cancelada e não pode ser recebida.")

    # O padrão já soma os juros: quem cobrou multa quer receber o total, e
    # obrigar a redigitar a soma convida ao erro de conta na hora do balcão.
    juros = dados.juros or 0
    destino = getattr(dados.juros_destino, "value", dados.juros_destino) or "LOJA"
    valor_recebido = (
        dados.valor_recebido if dados.valor_recebido is not None else conta.valor + juros
    )
    dia = dados.recebido_em or hoje_local()

    # QUANTO ENTROU DE FATO NA LOJA. Quando o juros é da maquininha, o cliente
    # desembolsa o total mas esse pedaço vai para a operadora -- lançar tudo
    # faria o sistema mostrar saldo que a conta bancária não tem, e o caixa
    # fecharia com sobra todo dia em que houvesse parcelamento.
    valor_para_a_loja = (
        valor_recebido - juros if destino == "OPERADORA" else valor_recebido
    )

    if dados.conta_bancaria_id is not None:
        if not financeiro_crud.get_conta_bancaria(db, empresa_id, dados.conta_bancaria_id):
            raise BadRequestException(detail="Conta bancária não encontrada")

    func_id, func_nome = _funcionario_do_token(usuario_token)

    movimento = caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.ENTRADA,
        origem=MovimentacaoFinanceiraOrigem.RECEBIMENTO,
        valor=valor_para_a_loja,
        forma_pagamento_id=dados.forma_pagamento_id,
        funcionario_id=func_id,
        funcionario_nome=func_nome,
        motivo=(
            f"Recebimento: {conta.descricao}"
            + (f" (juros de {juros} retido pela operadora)" if destino == "OPERADORA" else "")
        ),
    )
    movimento.conta_bancaria_id = dados.conta_bancaria_id

    conta.status = ContaReceberStatus.RECEBIDA.value
    # `valor_recebido` é o que o CLIENTE desembolsou; o livro guarda o que
    # entrou na loja. Os dois só divergem quando o juros é da operadora, e
    # guardar os dois é o que permite explicar a diferença depois.
    conta.valor_recebido = valor_recebido
    conta.juros = juros
    conta.juros_destino = destino
    conta.recebido_em = inicio_do_dia_utc(dia)
    conta.conta_bancaria_id = dados.conta_bancaria_id
    conta.forma_pagamento_id = dados.forma_pagamento_id
    conta.movimentacao_financeira_id = movimento.id
    if dados.observacao:
        conta.observacao = dados.observacao

    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_RECEBER, entidade_id=conta.id,
        campo="baixa", valor_antigo=ContaReceberStatus.PENDENTE.value,
        valor_novo=f"RECEBIDA {valor_recebido}",
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    db.flush()
    db.refresh(conta)
    return _serializar_receber(conta, hoje_local())


def estornar_recebimento(
    db: Session, empresa_id: int, conta_id: int, dados, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Desfaz a baixa sem apagar o lançamento. Ver o gêmeo em contas a pagar."""
    conta = financeiro_crud.get_conta_receber(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status != ContaReceberStatus.RECEBIDA.value:
        raise BadRequestException(detail="Só é possível estornar uma conta recebida.")

    func_id, func_nome = _funcionario_do_token(usuario_token)
    # Devolve o que ENTROU na loja, não o que o cliente desembolsou: o juros da
    # operadora nunca virou movimento, então estorná-lo tiraria do caixa
    # dinheiro que nunca esteve lá.
    valor = conta.valor_recebido or conta.valor
    if conta.juros_destino == "OPERADORA":
        valor -= conta.juros

    caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.SAIDA,
        origem=MovimentacaoFinanceiraOrigem.RECEBIMENTO,
        valor=valor,
        forma_pagamento_id=conta.forma_pagamento_id,
        funcionario_id=func_id,
        funcionario_nome=func_nome,
        motivo=f"Estorno de recebimento: {conta.descricao} — {dados.motivo}",
    )

    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_RECEBER, entidade_id=conta.id,
        campo="estorno", valor_antigo=f"RECEBIDA {valor}",
        valor_novo=f"PENDENTE — {dados.motivo}",
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    conta.status = ContaReceberStatus.PENDENTE.value
    conta.valor_recebido = None
    # O juros some junto: ele foi cobrado por causa daquele recebimento, e
    # deixá-lo para trás faria a próxima baixa somar multa duas vezes.
    conta.juros = 0
    conta.juros_destino = "LOJA"
    conta.recebido_em = None
    conta.conta_bancaria_id = None
    conta.forma_pagamento_id = None
    conta.movimentacao_financeira_id = None

    db.flush()
    db.refresh(conta)
    return _serializar_receber(conta, hoje_local())


def listar_historico_do_recebimento(db: Session, empresa_id: int, conta_id: int):
    conta = financeiro_crud.get_conta_receber(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    return financeiro_crud.listar_historico(db, empresa_id, ENTIDADE_CONTA_RECEBER, conta_id)


# ===========================================================================
# FLUXO DE CAIXA (Onda 3)
# ===========================================================================

def get_fluxo_caixa(db: Session, empresa_id: int, dias: int = 30) -> FluxoCaixa:
    """A projeção dos próximos `dias`, a partir do saldo declarado pelo dono.

    Três decisões que sustentam a tela, e o motivo de cada uma:

    O SALDO DE PARTIDA É DECLARADO. Ver `ContaBancaria.saldo_informado`: o
    livro do dinheiro só recebe venda e OS onde `controlar_caixa` está ligado,
    então calcular o saldo daria um número falso -- e fundo negativo -- na loja
    que não usa caixa. Enquanto ninguém declarar, `saldo_declarado` sai False e
    a tela pede o número em vez de desenhar uma linha que parte de zero.

    O ATRASADO NÃO ENTRA NA RÉGUA. Conta vencida não tem dia futuro para
    ocupar. Empurrá-la para hoje inventaria um aperto que talvez não aconteça
    (o fiado atrasado pode nunca chegar; o boleto vencido pode já ter sido
    pago no banco sem alguém dar baixa aqui). Vai num balde à parte, como
    aviso, e o dono decide.

    SÓ DIAS COM MOVIMENTO. Sessenta linhas de zero escondem as cinco que
    importam. A régua contínua é trabalho da tela, que sabe o tamanho dela.
    """
    hoje = hoje_local()
    # `dias` conta a partir de HOJE inclusive: "próximos 30 dias" para o dono da
    # loja começa hoje de manhã, não amanhã.
    fim = hoje + timedelta(days=dias - 1)

    # Só contas ATIVAS: uma conta desativada é dinheiro que a loja não usa mais,
    # e somar o saldo dela faria a projeção inteira partir de um número alto
    # demais.
    contas = financeiro_crud.listar_contas_bancarias(db, empresa_id, apenas_ativas=True)
    saldo_inicial = sum(int(c.saldo_informado or 0) for c in contas)
    datas = [c.saldo_informado_em for c in contas if c.saldo_informado_em]

    pagar, receber = financeiro_crud.pendentes_por_vencimento(
        db, empresa_id, inicio=hoje, fim=fim
    )

    por_dia: Dict[date, Dict[str, Any]] = {}

    def _bucket(dia: date) -> Dict[str, Any]:
        return por_dia.setdefault(
            dia, {"entradas": 0, "saidas": 0, "lancamentos": []}
        )

    for conta in receber:
        b = _bucket(conta.vencimento)
        b["entradas"] += int(conta.valor or 0)
        b["lancamentos"].append(
            FluxoLancamento(
                conta_id=conta.id, tipo=MovimentacaoFinanceiraTipo.ENTRADA.value,
                descricao=conta.descricao, valor=int(conta.valor or 0),
            )
        )

    for conta in pagar:
        b = _bucket(conta.vencimento)
        b["saidas"] += int(conta.valor or 0)
        b["lancamentos"].append(
            FluxoLancamento(
                conta_id=conta.id, tipo=MovimentacaoFinanceiraTipo.SAIDA.value,
                descricao=conta.descricao, valor=int(conta.valor or 0),
            )
        )

    saldo = saldo_inicial
    # O fundo do poço começa no próprio saldo de hoje: numa loja sem nada
    # agendado, o menor saldo do período é o que ela já tem.
    menor_saldo, menor_saldo_em = saldo_inicial, None
    primeiro_negativo: Optional[date] = None
    total_entradas = total_saidas = 0
    linha: List[FluxoDia] = []

    for data_dia in sorted(por_dia):
        dados = por_dia[data_dia]
        saldo += dados["entradas"] - dados["saidas"]
        total_entradas += dados["entradas"]
        total_saidas += dados["saidas"]

        if saldo < menor_saldo:
            menor_saldo, menor_saldo_em = saldo, data_dia
        # O PRIMEIRO dia negativo, e não o último: é a data em que o dono
        # precisa ter feito alguma coisa, e depois dela o resto é consequência.
        if saldo < 0 and primeiro_negativo is None:
            primeiro_negativo = data_dia

        linha.append(
            FluxoDia(
                data=data_dia,
                entradas=dados["entradas"],
                saidas=dados["saidas"],
                saldo=saldo,
                # Entrada antes de saída no mesmo dia: é a ordem em que o dono
                # lê ("entrou tanto, saiu tanto"), e o saldo do dia não depende
                # da ordem dentro dele.
                lancamentos=sorted(
                    dados["lancamentos"],
                    key=lambda item: (item.tipo != MovimentacaoFinanceiraTipo.ENTRADA.value,
                                      -item.valor),
                ),
            )
        )

    _p, _pg, atrasado_a_pagar = financeiro_crud.totais_contas_pagar(
        db, empresa_id, hoje=hoje
    )
    _r, _rc, atrasado_a_receber = financeiro_crud.totais_contas_receber(
        db, empresa_id, hoje=hoje
    )

    return FluxoCaixa(
        inicio=hoje,
        fim=fim,
        dias=dias,
        saldo_inicial=saldo_inicial,
        saldo_declarado=bool(datas),
        # A data MAIS ANTIGA entre as contas: é ela que envelhece o número. Uma
        # loja que atualizou o Nubank hoje e esqueceu a gaveta há um mês tem um
        # saldo de um mês atrás, não de hoje.
        saldo_informado_em=min(datas) if datas else None,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        saldo_final=saldo,
        primeiro_dia_negativo=primeiro_negativo,
        menor_saldo=menor_saldo,
        menor_saldo_em=menor_saldo_em,
        atrasado_a_receber=atrasado_a_receber,
        atrasado_a_pagar=atrasado_a_pagar,
        linha=linha,
    )


# ===========================================================================
# CONCILIAÇÃO (Onda 4)
# ===========================================================================

def _formas_de_origem(db: Session, contas: Sequence[ContaReceber]) -> Dict[int, Optional[str]]:
    """Mapa conta_id -> nome da forma que originou a cobrança."""
    por_venda, por_os = financeiro_crud.formas_de_origem(
        db,
        venda_pagamento_ids=[c.venda_pagamento_id for c in contas if c.venda_pagamento_id],
        os_pagamento_ids=[
            c.ordem_servico_pagamento_id for c in contas if c.ordem_servico_pagamento_id
        ],
    )
    return {
        c.id: (
            por_venda.get(c.venda_pagamento_id)
            if c.venda_pagamento_id
            else por_os.get(c.ordem_servico_pagamento_id)
            if c.ordem_servico_pagamento_id
            else None
        )
        for c in contas
    }


def get_conciliacao(
    db: Session, empresa_id: int, inicio: date, fim: date
) -> Conciliacao:
    """O que a loja espera receber, agrupado por DIA.

    O agrupamento por dia não é estética: é o formato em que o dinheiro chega.
    A operadora não deposita venda a venda -- deposita o lote do dia, um valor
    só. Conferir item a item contra o extrato é exatamente o trabalho que esta
    tela existe para evitar.

    Só PENDENTES: o que já foi recebido saiu da fila de conferência.
    """
    itens, _total = financeiro_crud.listar_contas_receber(
        db, empresa_id, status=ContaReceberStatus.PENDENTE.value,
        inicio=inicio, fim=fim, limit=1000,
    )
    formas = _formas_de_origem(db, itens)

    por_dia: Dict[date, List[ContaReceber]] = {}
    for conta in itens:
        por_dia.setdefault(conta.vencimento, []).append(conta)

    dias = [
        ConciliacaoDia(
            data=dia,
            quantidade=len(contas),
            total_previsto=sum(int(c.valor or 0) for c in contas),
            itens=[
                ConciliacaoItem(
                    conta_id=c.id,
                    descricao=c.descricao,
                    valor=int(c.valor or 0),
                    cliente_nome=_nome_do_cliente(c.cliente),
                    forma_origem=formas.get(c.id),
                )
                for c in contas
            ],
        )
        for dia, contas in sorted(por_dia.items())
    ]

    return Conciliacao(
        inicio=inicio,
        fim=fim,
        total_previsto=sum(d.total_previsto for d in dias),
        dias=dias,
    )


def baixar_lote(
    db: Session, empresa_id: int, dados, usuario_token: Dict[str, Any]
) -> ConciliacaoResultado:
    """Confere o depósito do dia e dá baixa em TODAS as cobranças daquele lote.

    O depósito é um valor só; as cobranças são várias. O rateio é
    PROPORCIONAL ao previsto de cada uma, e o CENTAVO QUE SOBRA do arredondamento
    vai para a última -- assim a soma das baixas é exatamente o que caiu no
    banco. Dividir igual entre as contas faria uma venda de R$ 20 e outra de
    R$ 400 absorverem a mesma taxa, e o histórico de cada uma mentiria.

    A diferença NÃO vira lançamento à parte: cada conta fica com
    `valor_recebido` menor que o previsto, que é o mesmo mecanismo do
    recebimento parcial já existente ("o cliente devia 200 e trouxe 150"). É o
    que mantém o livro do dinheiro igual ao extrato do banco -- inventar uma
    despesa de taxa por cima faria o sistema mostrar entrada e saída que a
    conta bancária nunca viu.

    Reusa `receber_conta` uma vez por cobrança, e não um caminho próprio: é o
    que garante que o lote gere o mesmo movimento, a mesma trilha de auditoria
    e o mesmo estorno que a baixa feita à mão.
    """
    itens, _total = financeiro_crud.listar_contas_receber(
        db, empresa_id, status=ContaReceberStatus.PENDENTE.value,
        inicio=dados.data, fim=dados.data, limit=1000,
    )
    if not itens:
        raise BadRequestException(
            detail="Não há cobranças pendentes com vencimento nesse dia."
        )

    total_previsto = sum(int(c.valor or 0) for c in itens)
    if total_previsto <= 0:
        raise BadRequestException(detail="O lote deste dia não tem valor a conferir.")

    partes: List[int] = []
    restante = int(dados.valor_recebido)
    for conta in itens[:-1]:
        parte = round(dados.valor_recebido * int(conta.valor or 0) / total_previsto)
        partes.append(parte)
        restante -= parte
    partes.append(restante)

    if any(parte <= 0 for parte in partes):
        raise BadRequestException(
            detail=(
                "O valor informado é pequeno demais para o lote deste dia: alguma "
                "cobrança ficaria com zero. Confira o depósito ou dê baixa nas contas "
                "uma a uma."
            )
        )

    for conta, parte in zip(itens, partes):
        receber_conta(
            db, empresa_id, conta.id,
            ContaReceberBaixa(
                valor_recebido=parte,
                # A data do LOTE, não a de hoje: o dinheiro caiu no dia do
                # repasse, e conciliar com atraso não muda quando ele entrou.
                recebido_em=dados.data,
                conta_bancaria_id=dados.conta_bancaria_id,
                forma_pagamento_id=dados.forma_pagamento_id,
            ),
            usuario_token,
        )

    return ConciliacaoResultado(
        data=dados.data,
        quantidade=len(itens),
        total_previsto=total_previsto,
        total_recebido=int(dados.valor_recebido),
        diferenca=int(dados.valor_recebido) - total_previsto,
    )


# ===========================================================================
# EXTRATO (Onda 5)
# ===========================================================================

def listar_extrato(
    db: Session,
    empresa_id: int,
    *,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> Extrato:
    """O livro do dinheiro linha a linha — o que JÁ aconteceu.

    O Fluxo de Caixa olha para frente e só enxerga documento em aberto; conta
    paga SAI da régua dele. Este é o outro lado: aqui nada sai nunca, porque
    `movimentacoes_financeiras` só recebe INSERT. Estorno não apaga o
    lançamento original, cria o contrário -- e as duas linhas ficam.

    O período filtra por `criado_em` (o instante em que o dinheiro andou), e
    não por vencimento: no extrato não existe futuro.
    """
    dt_inicio = inicio_do_dia_utc(inicio) if inicio else None
    dt_fim = fim_do_dia_utc(fim) if fim else None

    itens, total = financeiro_crud.listar_extrato(
        db, empresa_id, inicio=dt_inicio, fim=dt_fim, tipo=tipo, origem=origem,
        limit=limit, offset=offset,
    )
    entradas, saidas = financeiro_crud.totais_extrato(
        db, empresa_id, inicio=dt_inicio, fim=dt_fim, tipo=tipo, origem=origem
    )

    por_venda, por_os = financeiro_crud.documentos_de_origem(
        db,
        venda_pagamento_ids=[m.venda_pagamento_id for m in itens if m.venda_pagamento_id],
        os_pagamento_ids=[
            m.ordem_servico_pagamento_id for m in itens if m.ordem_servico_pagamento_id
        ],
    )

    def _documento(mov) -> Optional[str]:
        if mov.venda_pagamento_id:
            numero = por_venda.get(mov.venda_pagamento_id)
            return f"Venda {numero}" if numero else "Venda"
        if mov.ordem_servico_pagamento_id:
            return por_os.get(mov.ordem_servico_pagamento_id)
        return None

    # A conta bancária é lida do relacionamento por linha e não por join com
    # `joinedload`: nem toda linha tem conta, e o extrato de um mês cabe numa
    # página. Se um dia a tela paginar milhares, isto vira joinedload.
    contas = {
        c.id: c.nome for c in financeiro_crud.listar_contas_bancarias(db, empresa_id)
    }

    return Extrato(
        total_itens=total,
        total_entradas=entradas,
        total_saidas=saidas,
        saldo=entradas - saidas,
        itens=[
            ExtratoLinha(
                id=m.id,
                criado_em=m.criado_em,
                tipo=m.tipo,
                origem=m.origem,
                valor=int(m.valor or 0),
                motivo=m.motivo,
                funcionario_nome=m.funcionario_nome,
                conta_bancaria_nome=contas.get(m.conta_bancaria_id),
                forma_pagamento_nome=(
                    m.forma_pagamento.nome if m.forma_pagamento else None
                ),
                sessao_caixa_id=m.sessao_caixa_id,
                documento=_documento(m),
            )
            for m in itens
        ],
    )
