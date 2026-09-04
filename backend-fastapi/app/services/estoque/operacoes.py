# ---------------------------------------------------------------------------
# ARQUIVO: app/services/estoque/operacoes.py
# DESCRIÇÃO: Operações acionadas por outros módulos (baixa e estorno).
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.db.crud import produto as produto_crud
from app.db.crud import funcionario as funcionario_crud
from . import movimentacoes as mov_service
from app.core.enum import MovimentacaoTipo, MovimentacaoOrigem
from ._errors import not_found_exce, bad_request_exce

def _usuario_do_funcionario(db: Session, funcionario_id: int | None) -> tuple[int | None, str]:
    if not funcionario_id:
        return None, "Sistema"
    
    funcionario = funcionario_crud.get_funcionario_by_id(db, funcionario_id=funcionario_id)
    if not funcionario:
        return None, "Sistema"
        
    return funcionario.usuario_id, funcionario.nome or "Sistema"


def decrease_product_in_stock(db: Session, produto_id: int, quantidade: int, venda_id: int, funcionario_id: int):
    product_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not product_in_db:
        raise not_found_exce
        
    if quantidade > (product_in_db.estoque.quantidade or 0):
        raise bad_request_exce

    usuario_id, usuario_nome = _usuario_do_funcionario(db, funcionario_id)

    mov_service.registrar_movimentacao(
        db,
        produto=product_in_db,
        tipo=MovimentacaoTipo.SAIDA,
        quantidade=quantidade,
        origem=MovimentacaoOrigem.VENDA,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        venda_id=venda_id,
        observacao="Baixa por venda",
    )
    return produto_crud.update_produto(db, product_in_db)


def restore_product_to_stock(db: Session, produto_id: int, quantidade: int, venda_id: int, funcionario_id: int):
    product_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not product_in_db:
        raise not_found_exce

    usuario_id, usuario_nome = _usuario_do_funcionario(db, funcionario_id)

    mov_service.registrar_movimentacao(
        db,
        produto=product_in_db,
        tipo=MovimentacaoTipo.ENTRADA,
        quantidade=quantidade,
        origem=MovimentacaoOrigem.VENDA,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        venda_id=venda_id,
        observacao="Estorno por cancelamento de venda",
    )
    return produto_crud.update_produto(db, product_in_db)
