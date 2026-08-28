# ---------------------------------------------------------------------------
# ARQUIVO: db/crud/sessao_caixa.py
# DESCRIÇÃO: Acesso a dados do turno de caixa e do livro do dinheiro.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enum import (
    MovimentacaoFinanceiraOrigem,
    MovimentacaoFinanceiraTipo,
    SessaoCaixaStatus,
)
from app.db.models.forma_pagamento import FormaPagamento
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira
from app.db.models.sessao_caixa import SessaoCaixa


# ===========================================================================
# SESSÃO
# ===========================================================================

def get_sessao_by_id(db: Session, sessao_id: int) -> Optional[SessaoCaixa]:
    return db.query(SessaoCaixa).filter(SessaoCaixa.id == sessao_id).first()


def get_sessao_aberta_do_funcionario(db: Session, funcionario_id: int) -> Optional[SessaoCaixa]:
    """O turno aberto de um operador.

    É por aqui que a finalização da venda descobre em qual turno o dinheiro cai,
    sem precisar receber o HWID do terminal no checkout. Funciona porque o
    serviço garante que um operador não tem dois turnos abertos ao mesmo tempo:
    ninguém está em dois caixas de uma vez.
    """
    return (
        db.query(SessaoCaixa)
        .filter(
            SessaoCaixa.funcionario_id == funcionario_id,
            SessaoCaixa.status == SessaoCaixaStatus.ABERTO,
        )
        .order_by(SessaoCaixa.data_abertura.desc())
        .first()
    )


def get_sessao_aberta_do_terminal(db: Session, terminal_hwid: str) -> Optional[SessaoCaixa]:
    """O turno aberto de uma máquina. O índice único do banco garante no máximo um."""
    return (
        db.query(SessaoCaixa)
        .filter(
            SessaoCaixa.terminal_hwid == terminal_hwid,
            SessaoCaixa.status == SessaoCaixaStatus.ABERTO,
        )
        .first()
    )


def criar_sessao(
    db: Session,
    funcionario_id: int,
    saldo_inicial: int,
    terminal_hwid: Optional[str],
) -> SessaoCaixa:
    sessao = SessaoCaixa(
        funcionario_id=funcionario_id,
        saldo_inicial=saldo_inicial,
        terminal_hwid=terminal_hwid,
        status=SessaoCaixaStatus.ABERTO,
    )
    db.add(sessao)
    db.flush()
    return sessao


def listar_sessoes(
    db: Session,
    empresa_id: int,
    inicio: Optional[datetime] = None,
    fim: Optional[datetime] = None,
    limit: int = 50,
) -> Sequence[SessaoCaixa]:
    """Histórico de turnos da empresa, mais recentes primeiro.

    O filtro é pela ABERTURA do turno: é o que o dono tem na cabeça quando
    pergunta "o caixa de ontem". Um turno que virou a madrugada aparece no dia em
    que começou, e não no dia em que foi fechado.

    `inicio` e `fim` já chegam em UTC (ver app/core/tempo.py) — quem converte o
    dia da loja é quem chama.
    """
    from app.db.models.funcionario import Funcionario

    consulta = (
        db.query(SessaoCaixa)
        .join(Funcionario, Funcionario.id == SessaoCaixa.funcionario_id)
        .filter(Funcionario.empresa_id == empresa_id)
    )
    if inicio is not None:
        consulta = consulta.filter(SessaoCaixa.data_abertura >= inicio)
    if fim is not None:
        consulta = consulta.filter(SessaoCaixa.data_abertura <= fim)

    return (
        consulta.order_by(SessaoCaixa.data_abertura.desc())
        .limit(limit)
        .all()
    )


# ===========================================================================
# LIVRO DO DINHEIRO
# ===========================================================================

def registrar_movimento(
    db: Session,
    tipo: MovimentacaoFinanceiraTipo,
    origem: MovimentacaoFinanceiraOrigem,
    valor: int,
    sessao_caixa_id: Optional[int] = None,
    forma_pagamento_id: Optional[int] = None,
    venda_pagamento_id: Optional[int] = None,
    ordem_servico_pagamento_id: Optional[int] = None,
    funcionario_id: Optional[int] = None,
    funcionario_nome: Optional[str] = None,
    motivo: Optional[str] = None,
) -> MovimentacaoFinanceira:
    """O ÚNICO lugar que escreve no livro do dinheiro.

    Mesmo papel do `registrar_movimentacao()` no estoque: concentrar a escrita
    num ponto só é o que impede uma linha de dinheiro nascer sem origem ou sem
    dono, e é o que permite auditar depois.
    """
    movimento = MovimentacaoFinanceira(
        tipo=tipo.value,
        origem=origem.value,
        valor=valor,
        sessao_caixa_id=sessao_caixa_id,
        forma_pagamento_id=forma_pagamento_id,
        venda_pagamento_id=venda_pagamento_id,
        ordem_servico_pagamento_id=ordem_servico_pagamento_id,
        funcionario_id=funcionario_id,
        funcionario_nome=funcionario_nome,
        motivo=motivo,
    )
    db.add(movimento)
    db.flush()
    return movimento


def listar_movimentos_da_sessao(db: Session, sessao_id: int) -> Sequence[MovimentacaoFinanceira]:
    return (
        db.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.sessao_caixa_id == sessao_id)
        .order_by(MovimentacaoFinanceira.criado_em.asc(), MovimentacaoFinanceira.id.asc())
        .all()
    )


def somar_por_origem(db: Session, sessao_id: int) -> dict:
    """Totais do turno agrupados por origem. Chaves ausentes valem zero."""
    linhas = (
        db.query(
            MovimentacaoFinanceira.origem,
            func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0),
        )
        .filter(MovimentacaoFinanceira.sessao_caixa_id == sessao_id)
        .group_by(MovimentacaoFinanceira.origem)
        .all()
    )
    return {origem: total for origem, total in linhas}


def somar_por_forma_pagamento(db: Session, sessao_id: int) -> List[tuple]:
    """(forma_id, nome, total) das ENTRADAS do turno.

    Só entradas: é o que o operador confere contra o que recebeu. Sangria e
    suprimento aparecem separados no resumo, porque não são recebimento de
    ninguém.
    """
    return (
        db.query(
            MovimentacaoFinanceira.forma_pagamento_id,
            func.coalesce(FormaPagamento.nome, "Não informada"),
            func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0),
        )
        .outerjoin(
            FormaPagamento,
            FormaPagamento.id == MovimentacaoFinanceira.forma_pagamento_id,
        )
        .filter(
            MovimentacaoFinanceira.sessao_caixa_id == sessao_id,
            MovimentacaoFinanceira.tipo == MovimentacaoFinanceiraTipo.ENTRADA.value,
            MovimentacaoFinanceira.origem.in_(
                [
                    MovimentacaoFinanceiraOrigem.VENDA.value,
                    MovimentacaoFinanceiraOrigem.ORDEM_SERVICO.value,
                    MovimentacaoFinanceiraOrigem.RECEBIMENTO.value,
                ]
            ),
        )
        .group_by(MovimentacaoFinanceira.forma_pagamento_id, FormaPagamento.nome)
        .all()
    )


def somar_dinheiro_em_especie(db: Session, sessao_id: int, formas_dinheiro: Sequence[int]) -> int:
    """Entradas do turno que foram em DINHEIRO — as únicas que estão na gaveta.

    Cartão e PIX entram no faturamento mas não no que se conta na mão. Sem essa
    separação o fechamento acusaria diferença todo dia.
    """
    return _somar_em_especie(
        db, sessao_id, formas_dinheiro, MovimentacaoFinanceiraTipo.ENTRADA
    )


def somar_saidas_em_especie(
    db: Session, sessao_id: int, formas_dinheiro: Sequence[int]
) -> int:
    """Saídas do turno que tiraram dinheiro da gaveta.

    A sangria é a mais comum, mas não é a única: o estorno de uma OS reaberta
    sem pagamento real também devolve dinheiro que nunca entrou. Somar por TIPO
    em vez de por origem faz qualquer saída futura já entrar na conta certa,
    sem alguém precisar lembrar de acrescentá-la aqui.
    """
    return _somar_em_especie(
        db, sessao_id, formas_dinheiro, MovimentacaoFinanceiraTipo.SAIDA
    )


def _somar_em_especie(
    db: Session,
    sessao_id: int,
    formas_dinheiro: Sequence[int],
    tipo: MovimentacaoFinanceiraTipo,
) -> int:
    if not formas_dinheiro:
        return 0
    total = (
        db.query(func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0))
        .filter(
            MovimentacaoFinanceira.sessao_caixa_id == sessao_id,
            MovimentacaoFinanceira.tipo == tipo.value,
            MovimentacaoFinanceira.forma_pagamento_id.in_(formas_dinheiro),
        )
        .scalar()
    )
    return int(total or 0)
