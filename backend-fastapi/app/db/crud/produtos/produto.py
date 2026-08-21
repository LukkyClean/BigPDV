# ---------------------------------------------------------------------------
# ARQUIVO: crud/produto.py
# MÓDULO: Acesso a Dados (Repository)
# DESCRIÇÃO: Executa queries SQL via SQLAlchemy para Produtos e suas Fotos.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Sequence, Optional

from app.core.busca import filtro_busca, ordenacao_relevancia, por_similaridade
from app.db.models.produto import Produto as ProdutoModel

# ===========================================================================
# CONFIGURAÇÕES DE BUSCA
# ===========================================================================

_CAMPOS_BUSCA = (
    ProdutoModel.nome,
    ProdutoModel.codigo_produto,
    ProdutoModel.codigo_barras,
    ProdutoModel.marca,
    ProdutoModel.categoria,
)

_CAMPOS_EXATOS = (
    ProdutoModel.codigo_produto,
    ProdutoModel.codigo_barras,
)

_TETO_RESGATE = 2000
_LIMITE_RESGATE = 20


# ===========================================================================
# ENTIDADE: PRODUTO
# ===========================================================================

def _resgatar_por_similaridade(
    db: Session,
    search: str,
    apenas_ativos: bool,
    limite: int | None,
) -> Sequence[ProdutoModel]:
    """Rede de segurança para erro de digitação ("tnta" → "Tinta")."""
    colunas = select(
        ProdutoModel.id,
        ProdutoModel.nome,
        ProdutoModel.codigo_produto,
        ProdutoModel.marca,
    )
    if apenas_ativos:
        colunas = colunas.where(ProdutoModel.ativo == True)

    candidatos = db.execute(colunas.limit(_TETO_RESGATE)).all()
    parecidos = por_similaridade(
        search,
        candidatos,
        lambda linha: (linha.nome, linha.codigo_produto, linha.marca),
        limite=limite or _LIMITE_RESGATE,
    )
    if not parecidos:
        return []

    posicao_por_id = {linha.id: posicao for posicao, linha in enumerate(parecidos)}
    produtos = db.scalars(
        select(ProdutoModel).where(ProdutoModel.id.in_(posicao_por_id))
    ).all()

    return sorted(produtos, key=lambda produto: posicao_por_id[produto.id])


def get_produto_by_search(
    db: Session,
    search: str | None,
    limite: int | None = None,
) -> Sequence[ProdutoModel]:
    """Busca produtos por nome, código, código de barras, marca ou categoria."""
    filtro = filtro_busca(search, _CAMPOS_BUSCA)

    stmt = select(ProdutoModel)
    if filtro is not None:
        relevancia = ordenacao_relevancia(search, ProdutoModel.nome, _CAMPOS_EXATOS)
        stmt = stmt.where(filtro).order_by(
            ProdutoModel.ativo.desc(),
            relevancia,
            ProdutoModel.nome,
        )
    if limite is not None:
        stmt = stmt.limit(limite)

    produtos = db.scalars(stmt).all()

    if not produtos and filtro is not None:
        return _resgatar_por_similaridade(db, search, apenas_ativos=False, limite=limite)

    return produtos


def get_produto_simple_by_search(
    db: Session,
    search: str | None,
    limite: int | None = None,
) -> Sequence[ProdutoModel]:
    """Versão para o auto-complete do PDV: apenas ativos e requer termo de busca."""
    filtro = filtro_busca(search, _CAMPOS_BUSCA)
    if filtro is None:
        return []

    relevancia = ordenacao_relevancia(search, ProdutoModel.nome, _CAMPOS_EXATOS)
    stmt = (
        select(ProdutoModel)
        .where(and_(filtro, ProdutoModel.ativo == True))
        .order_by(relevancia, ProdutoModel.nome)
    )
    if limite is not None:
        stmt = stmt.limit(limite)

    produtos = db.scalars(stmt).all()

    if not produtos:
        return _resgatar_por_similaridade(db, search, apenas_ativos=True, limite=limite)

    return produtos


def get_produto_by_id(db: Session, produto_id: int) -> Optional[ProdutoModel]:
    """Busca produto pela chave primária (ID)."""
    stmt = select(ProdutoModel).where(ProdutoModel.id == produto_id)
    return db.scalar(stmt)


def get_produto_by_code(db: Session, produto_code: str) -> Optional[ProdutoModel]:
    """Busca produto ativo pelo código único (SKU)."""
    stmt = select(ProdutoModel).where(
        and_(
            ProdutoModel.codigo_produto == produto_code,
            ProdutoModel.ativo == True
        )
    )
    return db.scalar(stmt)


def create_produto(db: Session, produto_to_add: ProdutoModel) -> ProdutoModel:
    """Adiciona e persiste um novo produto no banco de dados."""
    db.add(produto_to_add)
    db.flush()
    db.refresh(produto_to_add)
    return produto_to_add


def update_produto(db: Session, produto_to_update: ProdutoModel) -> ProdutoModel:
    """Persiste alterações em um produto já rastreado pela sessão."""
    db.flush()
    db.refresh(produto_to_update)
    return produto_to_update