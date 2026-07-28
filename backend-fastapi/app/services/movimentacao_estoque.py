# ---------------------------------------------------------------------------
# ARQUIVO: services/movimentacao_estoque.py
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


# ===========================================================================
# REGISTRO CENTRAL DE MOVIMENTAÇÃO
#
# Este é o ÚNICO lugar que altera `estoque.quantidade`. Venda, OS, cadastro de
# produto e ajuste manual passam todos por aqui — antes cada um mexia na
# quantidade por conta própria, e um deles (a OS) simplesmente esquecia de
# mexer. Concentrando, a quantidade e o histórico não têm como divergir: ou as
# duas coisas acontecem, ou nenhuma.
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
) -> Optional[MovimentacaoEstoque]:
    """Altera o estoque do produto e registra a movimentação, numa operação só.

    `permitir_negativo` existe porque as duas frentes têm regras diferentes e
    ambas são deliberadas:
      - Venda (False): recusa a saída sem estoque. O produto ainda está na
        prateleira e dá para não vender.
      - OS (True): a peça já foi instalada no equipamento; travar a finalização
        não a devolve, só prende a OS. O saldo negativo é o sinal de que a
        contagem precisa ser acertada.

    Retorna None quando não há o que movimentar (produto sem estoque vinculado
    ou quantidade zero), para o chamador não precisar repetir essa checagem.
    """
    if produto is None or produto.estoque is None or quantidade <= 0:
        return None

    anterior = produto.estoque.quantidade or 0

    if tipo == MovimentacaoTipo.ENTRADA:
        posterior = anterior + quantidade
    elif tipo == MovimentacaoTipo.SAIDA:
        if not permitir_negativo and anterior < quantidade:
            raise estoque_insuficiente
        posterior = anterior - quantidade
    else:
        raise ValueError(f"registrar_movimentacao não trata o tipo {tipo}")

    produto.estoque.quantidade = posterior

    movimentacao = MovimentacaoEstoque(
        produto_id=produto.id,
        produto_nome=produto.nome,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        tipo=tipo,
        quantidade=quantidade,
        quantidade_anterior=anterior,
        quantidade_posterior=posterior,
        origem=origem.value,
        venda_id=venda_id,
        ordem_servico_id=ordem_servico_id,
        observacao=observacao,
    )
    return mov_crud.create_movimentacao(db, movimentacao)


def create_movimentacao(
    db: Session,
    produto_id: int,
    data: MovimentacaoCreate,
    usuario_token: Dict[str, Any],
) -> MovimentacaoEstoque:
    """
    Registra uma movimentação de estoque e atualiza a quantidade do produto.

    Regras:
    - ENTRADA: soma a quantidade ao estoque
    - SAIDA: subtrai; levanta 422 se o estoque for insuficiente
    - AJUSTE: define a quantidade final diretamente (quantidade = valor final desejado)
    """
    produto = produto_crud.get_produto_by_id(db, produto_id)
    if not produto:
        raise not_found_produto

    estoque = produto.estoque
    quantidade_anterior = estoque.quantidade

    if data.tipo == MovimentacaoTipo.ENTRADA:
        quantidade_posterior = quantidade_anterior + data.quantidade
    elif data.tipo == MovimentacaoTipo.SAIDA:
        if quantidade_anterior < data.quantidade:
            raise estoque_insuficiente
        quantidade_posterior = quantidade_anterior - data.quantidade
    elif data.tipo == MovimentacaoTipo.EDICAO_DADOS:
        quantidade_posterior = quantidade_anterior  # sem alteração de estoque
    else:  # AJUSTE
        quantidade_posterior = data.quantidade

    # Atualiza o estoque apenas para movimentações que afetam quantidade
    if data.tipo != MovimentacaoTipo.EDICAO_DADOS:
        estoque.quantidade = quantidade_posterior

    # Determina a quantidade real movimentada
    if data.tipo == MovimentacaoTipo.EDICAO_DADOS:
        quantidade_real = 0
    elif data.tipo == MovimentacaoTipo.AJUSTE:
        quantidade_real = abs(quantidade_posterior - quantidade_anterior)
    else:
        quantidade_real = data.quantidade

    movimentacao = MovimentacaoEstoque(
        produto_id=produto_id,
        produto_nome=produto.nome,
        usuario_id=int(usuario_token["sub"]),
        usuario_nome=usuario_token.get("nome", "Desconhecido"),
        tipo=data.tipo,
        quantidade=quantidade_real,
        quantidade_anterior=quantidade_anterior,
        quantidade_posterior=quantidade_posterior,
        origem=MovimentacaoOrigem.MANUAL.value,
        observacao=data.observacao,
    )

    return mov_crud.create_movimentacao(db, movimentacao)


def get_movimentacoes(
    db: Session,
    produto_id: Optional[int] = None,
    limit: int = 100,
) -> Sequence[MovimentacaoEstoque]:
    """Lista movimentações de estoque, opcionalmente por produto."""
    return mov_crud.get_movimentacoes(db, produto_id=produto_id, limit=limit)