# ---------------------------------------------------------------------------
# ARQUIVO: app/services/estoque/movimentacoes.py
# DESCRIÇÃO: Lógica de negócio para movimentações de estoque.
# ---------------------------------------------------------------------------

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Sequence, Optional, Dict, Any

from app.schemas.movimentacao_estoque import MovimentacaoCreate
from app.db.models.movimentacao_estoque import MovimentacaoEstoque
from app.db.crud import movimentacao_estoque as mov_crud
from app.db.crud import produto as produto_crud
from app.core.enum import MovimentacaoTipo, MovimentacaoOrigem


not_found_produto = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Produto não encontrado"
)

estoque_insuficiente = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Estoque insuficiente para realizar a saída"
)

quantidade_invalida = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Entrada e saída exigem quantidade maior que zero"
)

produto_sem_estoque = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Produto não possui controle de estoque vinculado"
)


# ===========================================================================
# CUSTO — média ponderada
# ===========================================================================

def custo_atual(estoque) -> Optional[int]:
    if estoque is None:
        return None
    if estoque.custo_medio is not None:
        return estoque.custo_medio
    return estoque.valor_entrada


def calcular_custo_medio(
    quantidade_anterior: int,
    custo_anterior: Optional[int],
    quantidade_entrada: int,
    custo_entrada: int,
) -> int:
    base = max(0, quantidade_anterior)
    if custo_anterior is None or base == 0:
        return custo_entrada
    total = (base * custo_anterior) + (quantidade_entrada * custo_entrada)
    return round(total / (base + quantidade_entrada))


# ===========================================================================
# REGISTRO CENTRAL DE MOVIMENTAÇÃO
# ===========================================================================

def registrar_movimentacao(
    db: Session,
    *,
    produto,
    tipo: MovimentacaoTipo,
    quantidade: int,
    origem: MovimentacaoOrigem,
    usuario_id: Optional[int] = None,
    usuario_nome: str = "Sistema",
    venda_id: Optional[int] = None,
    ordem_servico_id: Optional[int] = None,
    observacao: Optional[str] = None,
    permitir_negativo: bool = False,
    custo_unitario: Optional[int] = None,
) -> Optional[MovimentacaoEstoque]:
    if produto is None or produto.estoque is None:
        return None
    if tipo in (MovimentacaoTipo.ENTRADA, MovimentacaoTipo.SAIDA) and quantidade <= 0:
        return None

    estoque = produto.estoque
    anterior = estoque.quantidade or 0

    if tipo == MovimentacaoTipo.ENTRADA:
        posterior = anterior + quantidade
        movimentada = quantidade
    elif tipo == MovimentacaoTipo.SAIDA:
        if not permitir_negativo and anterior < quantidade:
            raise estoque_insuficiente
        posterior = anterior - quantidade
        movimentada = quantidade
    elif tipo == MovimentacaoTipo.AJUSTE:
        posterior = quantidade
        movimentada = abs(posterior - anterior)
    elif tipo == MovimentacaoTipo.EDICAO_DADOS:
        posterior = anterior
        movimentada = 0
    else:
        raise ValueError(f"registrar_movimentacao não trata o tipo {tipo}")

    custo_movimento = _resolver_custo(
        estoque=estoque,
        tipo=tipo,
        quantidade=movimentada,
        quantidade_anterior=anterior,
        custo_unitario=custo_unitario,
    )

    if tipo != MovimentacaoTipo.EDICAO_DADOS:
        estoque.quantidade = posterior

    movimentacao = MovimentacaoEstoque(
        produto_id=produto.id,
        produto_nome=produto.nome,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        tipo=tipo,
        quantidade=movimentada,
        quantidade_anterior=anterior,
        quantidade_posterior=posterior,
        origem=origem.value,
        venda_id=venda_id,
        ordem_servico_id=ordem_servico_id,
        observacao=observacao,
        custo_unitario=custo_movimento,
    )
    return mov_crud.create_movimentacao(db, movimentacao)


def _resolver_custo(
    *,
    estoque,
    tipo: MovimentacaoTipo,
    quantidade: int,
    quantidade_anterior: int,
    custo_unitario: Optional[int],
) -> Optional[int]:
    if tipo == MovimentacaoTipo.EDICAO_DADOS:
        return None

    if tipo == MovimentacaoTipo.ENTRADA and custo_unitario is not None:
        estoque.custo_medio = calcular_custo_medio(
            quantidade_anterior=quantidade_anterior,
            custo_anterior=custo_atual(estoque),
            quantidade_entrada=quantidade,
            custo_entrada=custo_unitario,
        )
        return custo_unitario

    return custo_atual(estoque)


# ===========================================================================
# MOVIMENTAÇÃO MANUAL (endpoint)
# ===========================================================================

def create_movimentacao(
    db: Session,
    produto_id: int,
    data: MovimentacaoCreate,
    usuario_token: Dict[str, Any],
) -> MovimentacaoEstoque:
    produto = produto_crud.get_produto_by_id(db, produto_id)
    if not produto:
        raise not_found_produto
    if produto.estoque is None:
        raise produto_sem_estoque
    if data.tipo in (MovimentacaoTipo.ENTRADA, MovimentacaoTipo.SAIDA) and data.quantidade <= 0:
        raise quantidade_invalida

    movimentacao = registrar_movimentacao(
        db,
        produto=produto,
        tipo=data.tipo,
        quantidade=data.quantidade,
        origem=MovimentacaoOrigem.MANUAL,
        usuario_id=int(usuario_token["sub"]),
        usuario_nome=usuario_token.get("nome", "Desconhecido"),
        observacao=data.observacao,
        custo_unitario=data.custo_unitario,
    )
    assert movimentacao is not None
    return movimentacao


def get_movimentacoes(
    db: Session,
    produto_id: Optional[int] = None,
    limit: int = 100,
) -> Sequence[MovimentacaoEstoque]:
    return mov_crud.get_movimentacoes(db, produto_id=produto_id, limit=limit)
