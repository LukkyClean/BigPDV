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
from app.db.models.plano_conta import PlanoConta
from app.helpers.exceptions import BadRequestException, NotFoundException
from app.schemas.conta_bancaria import ContaBancariaCreate, ContaBancariaUpdate
from app.schemas.conta_pagar import (
    ContaPagarBaixa,
    ContaPagarCreate,
    ContaPagarEstorno,
    ContaPagarUpdate,
)
from app.schemas.financeiro import DespesaPorCategoria, ResumoFinanceiro
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
    _validar_referencias(db, empresa_id, dados.plano_conta_id)

    conta = financeiro_crud.criar_conta_pagar(
        db,
        ContaPagar(
            empresa_id=empresa_id,
            descricao=dados.descricao.strip(),
            valor=dados.valor,
            vencimento=dados.vencimento,
            plano_conta_id=dados.plano_conta_id,
            fornecedor_id=dados.fornecedor_id,
            recorrente=dados.recorrente,
            observacao=dados.observacao,
            status=ContaPagarStatus.PENDENTE.value,
        ),
    )

    func_id, func_nome = _funcionario_do_token(usuario_token)
    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="criacao", valor_antigo=None, valor_novo=conta.descricao,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


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

def _proximo_vencimento(vencimento: date) -> date:
    """Mesmo dia do mês seguinte, encolhendo quando o dia não existe.

    Vencimento dia 31 em mês de 30 cai no dia 30, e não vaza para o dia 1º do
    mês seguinte -- que atrasaria o alerta em um mês inteiro justamente na conta
    que vence no fim do mês.
    """
    ano = vencimento.year + (1 if vencimento.month == 12 else 0)
    mes = 1 if vencimento.month == 12 else vencimento.month + 1

    dia = vencimento.day
    while dia > 1:
        try:
            return date(ano, mes, dia)
        except ValueError:
            dia -= 1
    return date(ano, mes, 1)


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
    if conta.recorrente:
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

def get_resumo(db: Session, empresa_id: int, inicio: date, fim: date) -> ResumoFinanceiro:
    """Entrou, saiu, sobrou — em regime de caixa. Ver o docstring do schema."""
    hoje = hoje_local()
    dt_inicio, dt_fim = inicio_do_dia_utc(inicio), fim_do_dia_utc(fim)

    # Faturamento sai da MESMA fonte do dashboard e dos relatórios. Recalcular
    # aqui abriria a porta para o financeiro mostrar um número e o relatório
    # outro, para o mesmo mês.
    stats = dashboard_crud.get_stats_agregados(db, dt_inicio, dt_fim, empresa_id)
    faturamento = int(stats.vendas_total or 0) + int(stats.os_soma or 0)

    despesas = financeiro_crud.total_despesas_pagas(db, empresa_id, dt_inicio, dt_fim)
    pendente, _pago, vencido = financeiro_crud.totais_contas_pagar(db, empresa_id, hoje=hoje)

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
        despesas_pagas=despesas,
        resultado=faturamento - despesas,
        a_pagar_pendente=pendente,
        a_pagar_vencido=vencido,
        despesas_por_categoria=categorias,
        proximas_a_vencer=[_serializar_conta(c, hoje) for c in proximas],
    )
