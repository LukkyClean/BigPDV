# ---------------------------------------------------------------------------
# ARQUIVO: services/sessao_caixa.py
# DESCRIÇÃO: Regras do turno de caixa: abrir, suprir, sangrar, fechar e conferir.
# ---------------------------------------------------------------------------

# TUDO AQUI SÓ ACONTECE COM `controlar_caixa` LIGADO.
#
# A chave é por empresa (configuracoes_vendas) e nasce DESLIGADA. Loja que não a
# liga nunca chega a este arquivo: continua vendendo como sempre vendeu, sem
# turno, sem sangria e sem nada gravado no livro do dinheiro. É essa porta
# fechada que permite o caixa existir sem incomodar as lojas que já rodam.

from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.enum import (
    MovimentacaoFinanceiraOrigem,
    MovimentacaoFinanceiraTipo,
    SessaoCaixaStatus,
)
from app.core.depends import is_visao_gerencial
from app.core.security import verify_password
from app.core.tempo import fim_do_dia_utc, inicio_do_dia_utc
from app.helpers.exceptions import BadRequestException, NotFoundException
from app.db.crud import configuracao_seguranca as config_seg_crud
from app.db.crud import configuracao_vendas as config_vendas_crud
from app.db.crud import sessao_caixa as caixa_crud
from app.db.models.forma_pagamento import FormaPagamento
from app.db.models.sessao_caixa import SessaoCaixa
from app.schemas.sessao_caixa import (
    MovimentoCaixaCreate,
    SessaoCaixaHistoricoItem,
    MovimentoCaixaRead,
    SessaoCaixaAbrir,
    SessaoCaixaFechar,
    SessaoCaixaResumo,
    TotalPorForma,
)

# Formas que ficam FISICAMENTE na gaveta. Só elas entram na conta do que o
# operador conta na mão — cartão e PIX faturam, mas não estão lá.
# Casadas por nome porque a tabela é catálogo livre: a loja pode renomear ou
# criar as suas, e "Dinheiro" é o nome semeado no startup.
NOMES_DE_ESPECIE = ("dinheiro",)


# ===========================================================================
# HELPERS
# ===========================================================================

def _config(db: Session, empresa_id: int):
    return config_vendas_crud.get_configuracao_vendas(db, empresa_id=empresa_id)


def caixa_esta_ligado(db: Session, empresa_id: int) -> bool:
    """Porta de entrada de tudo. Sem isso, o caixa não existe para a loja."""
    config = _config(db, empresa_id)
    return bool(config and config.controlar_caixa)


def _exigir_caixa_ligado(db: Session, empresa_id: int) -> None:
    if not caixa_esta_ligado(db, empresa_id):
        raise BadRequestException(
            detail="O controle de caixa está desligado nas configurações de vendas"
        )


def _funcionario_do_token(usuario_token: Dict[str, Any]) -> int:
    funcionario_id = usuario_token.get("funcionario_id")
    if not funcionario_id:
        raise BadRequestException(
            detail="Apenas funcionários podem operar o caixa"
        )
    return funcionario_id


def _ids_das_formas_em_especie(db: Session) -> List[int]:
    formas = db.query(FormaPagamento).all()
    return [f.id for f in formas if (f.nome or "").strip().lower() in NOMES_DE_ESPECIE]


def _validar_autorizacao_sangria(
    db: Session,
    empresa_id: int,
    usuario_token: Dict[str, Any],
    codigo_gerente: Optional[str],
) -> None:
    """Sangria travada: ou quem opera é gerente, ou um supervisor libera na hora.

    Suprimento NÃO passa por aqui de propósito. Pôr dinheiro na gaveta não cria
    risco de desvio; tirar, sim. Travar os dois faria o operador chamar o gerente
    para colocar troco — o atrito que faz loja desligar o controle e voltar para
    o caderno.
    """
    config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
    if not (config_seg and config_seg.requer_pin_sangria):
        return
    # A partir daqui a loja EXIGE autorização para sangrar.

    # Master e quem tem permissão ampla não precisam pedir licença a ninguém.
    if usuario_token.get("is_master") is True:
        return
    permissoes = usuario_token.get("permissoes") or {}
    if permissoes.get("all") or permissoes.get("manage_sales"):
        return

    pin = getattr(config_seg, "pin_gerente", None)
    if not pin:
        # Exigir autorização sem PIN configurado travaria a sangria para sempre.
        # A loja que ligou a trava e não cadastrou o PIN precisa saber disso.
        raise BadRequestException(
            detail="A sangria exige autorização, mas nenhum PIN de gerente está "
                   "configurado em Configurações > Segurança"
        )
    # Sentinelas, e não frases: é o contrato que o frontend já usa para abrir o
    # modal de PIN em cancelamento, reabertura e desconto
    # (shared/composables/useGerenteAprovacao). Inventar mensagem nova aqui
    # deixaria a sangria de fora do fluxo que já existe.
    if not codigo_gerente:
        raise BadRequestException(detail="REQUER_APROVACAO_GERENTE")
    if not verify_password(codigo_gerente, pin):
        raise BadRequestException(detail="PIN_GERENTE_INVALIDO")


# ===========================================================================
# ABRIR
# ===========================================================================

def abrir_caixa(
    db: Session,
    dados: SessaoCaixaAbrir,
    usuario_token: Dict[str, Any],
) -> SessaoCaixaResumo:
    empresa_id = usuario_token["empresa_id"]
    _exigir_caixa_ligado(db, empresa_id)
    funcionario_id = _funcionario_do_token(usuario_token)

    # Um operador, um caixa. É o que permite a finalização da venda descobrir o
    # turno sem receber o HWID no checkout — ninguém está em dois caixas de uma
    # vez.
    if caixa_crud.get_sessao_aberta_do_funcionario(db, funcionario_id):
        raise BadRequestException(
            detail="Você já tem um caixa aberto. Feche-o antes de abrir outro."
        )

    # Uma máquina, um caixa. O banco também garante isso (índice único parcial);
    # a checagem aqui existe para devolver uma mensagem que o operador entenda,
    # em vez do erro cru de constraint.
    if dados.terminal_hwid:
        ocupada = caixa_crud.get_sessao_aberta_do_terminal(db, dados.terminal_hwid)
        if ocupada:
            raise BadRequestException(
                detail="Este terminal já tem um caixa aberto por outro operador. "
                       "Ele precisa ser fechado antes."
            )

    sessao = caixa_crud.criar_sessao(
        db,
        funcionario_id=funcionario_id,
        saldo_inicial=dados.saldo_inicial,
        terminal_hwid=dados.terminal_hwid,
    )

    # O troco inicial é dinheiro que entra na gaveta sem venda por trás — logo,
    # é movimento. Sem registrá-lo, o fechamento acusaria sobra todo dia.
    if dados.saldo_inicial > 0:
        formas_especie = _ids_das_formas_em_especie(db)
        caixa_crud.registrar_movimento(
            db,
            tipo=MovimentacaoFinanceiraTipo.ENTRADA,
            origem=MovimentacaoFinanceiraOrigem.ABERTURA,
            valor=dados.saldo_inicial,
            sessao_caixa_id=sessao.id,
            forma_pagamento_id=formas_especie[0] if formas_especie else None,
            funcionario_id=funcionario_id,
            funcionario_nome=usuario_token.get("nome"),
            motivo="Troco de abertura",
        )

    return montar_resumo(db, sessao, usuario_token)


# ===========================================================================
# SANGRIA E SUPRIMENTO
# ===========================================================================

def _sessao_aberta_obrigatoria(db: Session, funcionario_id: int) -> SessaoCaixa:
    sessao = caixa_crud.get_sessao_aberta_do_funcionario(db, funcionario_id)
    if not sessao:
        raise BadRequestException(detail="Nenhum caixa aberto para este operador")
    return sessao


def registrar_suprimento(
    db: Session,
    dados: MovimentoCaixaCreate,
    usuario_token: Dict[str, Any],
) -> SessaoCaixaResumo:
    empresa_id = usuario_token["empresa_id"]
    _exigir_caixa_ligado(db, empresa_id)
    funcionario_id = _funcionario_do_token(usuario_token)
    sessao = _sessao_aberta_obrigatoria(db, funcionario_id)

    formas_especie = _ids_das_formas_em_especie(db)
    caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.ENTRADA,
        origem=MovimentacaoFinanceiraOrigem.SUPRIMENTO,
        valor=dados.valor,
        sessao_caixa_id=sessao.id,
        forma_pagamento_id=formas_especie[0] if formas_especie else None,
        funcionario_id=funcionario_id,
        funcionario_nome=usuario_token.get("nome"),
        motivo=dados.motivo,
    )
    return montar_resumo(db, sessao, usuario_token)


def registrar_sangria(
    db: Session,
    dados: MovimentoCaixaCreate,
    usuario_token: Dict[str, Any],
) -> SessaoCaixaResumo:
    empresa_id = usuario_token["empresa_id"]
    _exigir_caixa_ligado(db, empresa_id)
    funcionario_id = _funcionario_do_token(usuario_token)
    sessao = _sessao_aberta_obrigatoria(db, funcionario_id)

    _validar_autorizacao_sangria(db, empresa_id, usuario_token, dados.codigo_gerente)

    formas_especie = _ids_das_formas_em_especie(db)
    caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.SAIDA,
        origem=MovimentacaoFinanceiraOrigem.SANGRIA,
        valor=dados.valor,
        sessao_caixa_id=sessao.id,
        forma_pagamento_id=formas_especie[0] if formas_especie else None,
        funcionario_id=funcionario_id,
        funcionario_nome=usuario_token.get("nome"),
        motivo=dados.motivo,
    )
    return montar_resumo(db, sessao, usuario_token)


# ===========================================================================
# FECHAR
# ===========================================================================

def fechar_caixa(
    db: Session,
    dados: SessaoCaixaFechar,
    usuario_token: Dict[str, Any],
) -> SessaoCaixaResumo:
    empresa_id = usuario_token["empresa_id"]
    _exigir_caixa_ligado(db, empresa_id)
    funcionario_id = _funcionario_do_token(usuario_token)
    sessao = _sessao_aberta_obrigatoria(db, funcionario_id)

    esperado = calcular_saldo_esperado_em_especie(db, sessao)

    sessao.saldo_final_esperado = esperado
    sessao.saldo_final_informado = dados.saldo_contado
    sessao.status = SessaoCaixaStatus.FECHADO
    from app.core.tempo import agora_utc
    sessao.data_fechamento = agora_utc()
    db.flush()

    # No fechamento o esperado SEMPRE volta, mesmo no modo cego: cego é não ver
    # ANTES de contar. Esconder depois só impediria o operador de assinar o que
    # ele mesmo conferiu.
    return montar_resumo(db, sessao, usuario_token, ocultar_esperado=False)


# ===========================================================================
# CONSULTA
# ===========================================================================

def get_sessao_atual(
    db: Session,
    usuario_token: Dict[str, Any],
) -> Optional[SessaoCaixaResumo]:
    """O turno aberto deste operador, ou None. Não explode se não houver."""
    empresa_id = usuario_token["empresa_id"]
    if not caixa_esta_ligado(db, empresa_id):
        return None
    funcionario_id = usuario_token.get("funcionario_id")
    if not funcionario_id:
        return None
    sessao = caixa_crud.get_sessao_aberta_do_funcionario(db, funcionario_id)
    if not sessao:
        return None

    config = _config(db, empresa_id)
    ocultar = bool(config and config.fechamento_cego)
    return montar_resumo(db, sessao, usuario_token, ocultar_esperado=ocultar)


def get_resumo_de_sessao(
    db: Session,
    sessao_id: int,
    usuario_token: Dict[str, Any],
) -> SessaoCaixaResumo:
    sessao = caixa_crud.get_sessao_by_id(db, sessao_id)
    if not sessao:
        raise NotFoundException(detail="Sessão de caixa não encontrada")
    # Turno já fechado não tem o que esconder: a conferência acabou.
    ocultar = False
    if sessao.status == SessaoCaixaStatus.ABERTO:
        config = _config(db, usuario_token["empresa_id"])
        ocultar = bool(config and config.fechamento_cego)
    return montar_resumo(db, sessao, usuario_token, ocultar_esperado=ocultar)


def listar_historico(
    db: Session,
    usuario_token: Dict[str, Any],
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    limit: int = 50,
) -> List[SessaoCaixaHistoricoItem]:
    """O histórico de turnos como o DONO precisa ver.

    Responde as duas perguntas dele: quem fechou faltando dinheiro e quem fechou
    sobrando. As duas saem de `diferenca` — negativa é falta, positiva é sobra —
    e as duas merecem atenção: sobra costuma ser troco não registrado ou venda
    não lançada.

    VISÃO GERENCIAL APENAS. O operador vê o próprio turno pelo PDV; o histórico
    de quem fechou com quanto é do dono. Sem isso, um operador veria a diferença
    dos colegas.
    """
    if not is_visao_gerencial(usuario_token):
        raise BadRequestException(
            detail="Apenas o responsável pela loja pode ver o histórico de caixas"
        )

    dt_inicio = inicio_do_dia_utc(inicio) if inicio else None
    dt_fim = fim_do_dia_utc(fim) if fim else None

    sessoes = caixa_crud.listar_sessoes(
        db,
        empresa_id=usuario_token["empresa_id"],
        inicio=dt_inicio,
        fim=dt_fim,
        limit=limit,
    )

    # Nome do terminal resolvido de uma vez: uma consulta por linha viraria N+1
    # numa lista que o dono abre todo dia.
    #
    # Lido do CADASTRO (`terminais`), não da tabela de presença: o relatório
    # olha para trás, e a máquina que fechou o turno de ontem pode estar
    # desligada agora. Enquanto o nome vinha da presença, a coluna Terminal
    # ficava vazia justamente nos turnos antigos — que são os que o dono abre o
    # relatório para ver.
    from app.db.crud import terminal as terminal_crud

    hwids = {s.terminal_hwid for s in sessoes if s.terminal_hwid}
    nomes_terminal: Dict[str, Optional[str]] = terminal_crud.nomes_por_hwid(
        db, sorted(hwids)
    )

    itens: List[SessaoCaixaHistoricoItem] = []
    for sessao in sessoes:
        esperado = sessao.saldo_final_esperado
        contado = sessao.saldo_final_informado
        # Só há diferença depois do fechamento: turno aberto ainda não foi
        # conferido, e mostrar um número ali sugeriria uma quebra que não existe.
        diferenca = None if (esperado is None or contado is None) else int(contado - esperado)

        itens.append(
            SessaoCaixaHistoricoItem(
                sessao_id=sessao.id,
                status=sessao.status,
                funcionario_id=sessao.funcionario_id,
                funcionario_nome=getattr(sessao.funcionario, "nome", None),
                terminal_hwid=sessao.terminal_hwid,
                terminal_nome=nomes_terminal.get(sessao.terminal_hwid or ""),
                data_abertura=sessao.data_abertura,
                data_fechamento=sessao.data_fechamento,
                saldo_inicial=sessao.saldo_inicial,
                saldo_esperado=esperado,
                saldo_contado=contado,
                diferenca=diferenca,
            )
        )
    return itens


# ===========================================================================
# A CONTA DA GAVETA
# ===========================================================================

def calcular_saldo_esperado_em_especie(db: Session, sessao: SessaoCaixa) -> int:
    """saldo_inicial + entradas em dinheiro + suprimentos - sangrias.

    A abertura e o suprimento já entram como movimento em espécie, então somar
    `saldo_inicial` de novo contaria o troco duas vezes: o que se soma aqui são
    os movimentos, e o saldo inicial já está entre eles.
    """
    formas_especie = _ids_das_formas_em_especie(db)
    entradas_especie = caixa_crud.somar_dinheiro_em_especie(db, sessao.id, formas_especie)
    totais = caixa_crud.somar_por_origem(db, sessao.id)
    sangrias = totais.get(MovimentacaoFinanceiraOrigem.SANGRIA.value, 0)
    return int(entradas_especie - sangrias)


def montar_resumo(
    db: Session,
    sessao: SessaoCaixa,
    usuario_token: Dict[str, Any],
    ocultar_esperado: bool = False,
) -> SessaoCaixaResumo:
    totais = caixa_crud.somar_por_origem(db, sessao.id)
    vendas = totais.get(MovimentacaoFinanceiraOrigem.VENDA.value, 0)
    vendas += totais.get(MovimentacaoFinanceiraOrigem.ORDEM_SERVICO.value, 0)
    vendas += totais.get(MovimentacaoFinanceiraOrigem.RECEBIMENTO.value, 0)
    suprimentos = totais.get(MovimentacaoFinanceiraOrigem.SUPRIMENTO.value, 0)
    sangrias = totais.get(MovimentacaoFinanceiraOrigem.SANGRIA.value, 0)

    esperado = calcular_saldo_esperado_em_especie(db, sessao)
    contado = sessao.saldo_final_informado
    diferenca = None if contado is None else int(contado - esperado)

    por_forma = [
        TotalPorForma(
            forma_pagamento_id=forma_id,
            forma_pagamento_nome=nome,
            total=int(total),
        )
        for forma_id, nome, total in caixa_crud.somar_por_forma_pagamento(db, sessao.id)
    ]

    movimentos = [
        MovimentoCaixaRead.model_validate(m)
        for m in caixa_crud.listar_movimentos_da_sessao(db, sessao.id)
    ]

    # Do cadastro durável, não da presença: o resumo de um turno FECHADO é lido
    # depois, com a máquina possivelmente desligada.
    terminal_nome = None
    if sessao.terminal_hwid:
        from app.db.crud import terminal as terminal_crud

        terminal = terminal_crud.get_por_hwid(db, sessao.terminal_hwid)
        terminal_nome = getattr(terminal, "nome", None)

    return SessaoCaixaResumo(
        sessao_id=sessao.id,
        status=sessao.status,
        funcionario_id=sessao.funcionario_id,
        funcionario_nome=getattr(sessao.funcionario, "nome", None),
        terminal_hwid=sessao.terminal_hwid,
        terminal_nome=terminal_nome,
        data_abertura=sessao.data_abertura,
        data_fechamento=sessao.data_fechamento,
        saldo_inicial=sessao.saldo_inicial,
        total_vendas=int(vendas),
        total_suprimentos=int(suprimentos),
        total_sangrias=int(sangrias),
        # No modo cego o operador não vê o esperado ANTES de contar — é o que
        # torna a conferência uma conferência de verdade. `None` diz "oculto";
        # devolver `0` dizia "a gaveta está vazia", que é outra coisa e é falso.
        saldo_esperado_dinheiro=None if ocultar_esperado else esperado,
        saldo_contado=contado,
        diferenca=diferenca,
        por_forma=por_forma,
        movimentos=movimentos,
    )


# ===========================================================================
# INTEGRAÇÃO COM A VENDA
# ===========================================================================

def registrar_pagamentos_de_venda(
    db: Session,
    venda,
    operador_funcionario_id: Optional[int] = None,
) -> None:
    """Lança no livro os pagamentos de uma venda finalizada.

    NÃO FAZ NADA se o controle de caixa estiver desligado — e é essa saída
    imediata que mantém as lojas de hoje com o comportamento de sempre.

    QUEM RECEBE ≠ QUEM VENDE. `operador_funcionario_id` é quem está no caixa
    finalizando; `venda.funcionario_id` é o VENDEDOR, que existe para a comissão.
    Numa loja onde um atende e outro recebe, o dinheiro tem que cair no turno de
    quem recebeu — senão some do fechamento de quem está com a gaveta na mão.
    O vendedor fica como reserva para a loja de uma pessoa só, em que os dois
    são a mesma.

    SÓ ENTRA O QUE FOI RECEBIDO. Pagamento com vencimento no futuro (boleto,
    prazo, fiado) é promessa, não dinheiro: vira conta a receber e o movimento
    nasce no dia em que for pago de fato. Sem essa regra, o fechamento acusaria
    sobra em toda venda a prazo.
    """
    funcionario = getattr(venda, "funcionario", None)
    empresa_id = getattr(funcionario, "empresa_id", None)
    if not empresa_id or not caixa_esta_ligado(db, empresa_id):
        return

    sessao = None
    if operador_funcionario_id:
        sessao = caixa_crud.get_sessao_aberta_do_funcionario(db, operador_funcionario_id)
    if not sessao:
        sessao = caixa_crud.get_sessao_aberta_do_funcionario(db, venda.funcionario_id)
    if not sessao:
        return

    from app.core.tempo import hoje_local

    hoje = hoje_local()
    venda.sessao_caixa_id = sessao.id

    for pagamento in venda.pagamentos:
        if pagamento.vencimento and pagamento.vencimento > hoje:
            continue  # promessa: é conta a receber, não gaveta
        pagamento.sessao_caixa_id = sessao.id
        caixa_crud.registrar_movimento(
            db,
            tipo=MovimentacaoFinanceiraTipo.ENTRADA,
            origem=MovimentacaoFinanceiraOrigem.VENDA,
            valor=pagamento.valor,
            sessao_caixa_id=sessao.id,
            forma_pagamento_id=pagamento.forma_pagamento_id,
            venda_pagamento_id=pagamento.id,
            funcionario_id=venda.funcionario_id,
            funcionario_nome=getattr(funcionario, "nome", None),
        )


def exigir_caixa_aberto_para_vender(
    db: Session,
    funcionario,
    operador_funcionario_id: Optional[int] = None,
) -> None:
    """Bloqueia a finalização quando a loja exige turno aberto.

    As duas chaves são separadas de propósito: `controlar_caixa` registra,
    `exigir_caixa_aberto` obriga. A loja pode querer o registro sem a trava
    enquanto a equipe se acostuma.

    A cobrança é sobre o turno de QUEM RECEBE (mesma razão de
    `registrar_pagamentos_de_venda`): não faz sentido exigir caixa aberto do
    vendedor que só atendeu.
    """
    empresa_id = getattr(funcionario, "empresa_id", None)
    if not empresa_id:
        return
    config = _config(db, empresa_id)
    if not (config and config.controlar_caixa and config.exigir_caixa_aberto):
        return

    candidatos = [operador_funcionario_id, getattr(funcionario, "id", None)]
    if any(
        caixa_crud.get_sessao_aberta_do_funcionario(db, fid)
        for fid in candidatos
        if fid
    ):
        return

    raise BadRequestException(detail="Abra o caixa antes de finalizar vendas")
