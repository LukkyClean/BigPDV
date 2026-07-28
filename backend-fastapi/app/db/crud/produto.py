# ---------------------------------------------------------------------------
# ARQUIVO: crud/produto.py
# MÓDULO: Acesso a Dados (Repository)
# DESCRIÇÃO: Executa queries SQL via SQLAlchemy para Produtos.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Sequence, Optional

from app.core.busca import filtro_busca, ordenacao_relevancia, por_similaridade
from app.db.models.produto import Produto as ProdutoModel
from app.db.models.produto_fotos import ProdutoFoto as ProdutoFotoModel

# Campos varridos pela busca de produto. O código de barras entra na lista
# porque o balcão usa leitor — sem ele, bipar não acha nada.
_CAMPOS_BUSCA = (
    ProdutoModel.nome,
    ProdutoModel.codigo_produto,
    ProdutoModel.codigo_barras,
    ProdutoModel.marca,
    ProdutoModel.categoria,
)

# Campos que, batendo exatamente, mandam o produto para o topo da lista.
_CAMPOS_EXATOS = (
    ProdutoModel.codigo_produto,
    ProdutoModel.codigo_barras,
)

# Quantos produtos varrer no resgate por similaridade. É um teto de proteção:
# só é atingido em catálogos grandes, e só quando a busca não achou nada.
_TETO_RESGATE = 2000

# Quantos produtos o resgate devolve quando o chamador não pediu limite.
_LIMITE_RESGATE = 20

# ===========================================================================
# LEITURA (READ)
# ===========================================================================

def _resgatar_por_similaridade(
    db: Session,
    search: str,
    apenas_ativos: bool,
    limite: int | None,
) -> Sequence[ProdutoModel]:
    """
    Rede de segurança para erro de digitação ("tnta" → "Tinta").

    Roda somente quando a busca normal voltou vazia, então o custo de varrer
    o catálogo em Python é pago apenas no caso em que o operador já estava
    sem resposta nenhuma.

    A varredura carrega só as colunas que entram na comparação — hidratar
    milhares de objetos ORM completos custava mais que a comparação em si.
    Os produtos de verdade são buscados depois, apenas para os que venceram.
    """
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

    # O IN devolve na ordem do banco; a ordem que importa é a da parecença.
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
    """
    Busca produtos por nome, código, código de barras, marca ou categoria.

    Aceita as palavras em qualquer ordem e ignora acentos: "azul tinta"
    encontra "Tinta Azul Metálica". Se nada casar, tenta um resgate
    tolerante a erro de digitação.

    Args:
        search: Termo de busca. Vazio devolve o catálogo inteiro.
        limite: Teto de resultados. None (padrão) não limita — a tela de
                Produtos depende disso para listar tudo.

    Returns:
        Sequence[ProdutoModel]: Produtos encontrados, mais relevantes primeiro.
    """
    filtro = filtro_busca(search, _CAMPOS_BUSCA)

    stmt = select(ProdutoModel)
    if filtro is not None:
        relevancia = ordenacao_relevancia(search, ProdutoModel.nome, _CAMPOS_EXATOS)
        # Ativos primeiro: esta rota devolve inativos também, e quem consome
        # com limite (o modal de item da OS) os descarta no cliente. Sem esta
        # ordenação, um punhado de inativos ocuparia as vagas do corte.
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
    """
    Versão para o auto-complete do PDV: só produtos ativos e sem termo, sem
    resultado (o campo não deve despejar o catálogo ao ganhar foco).
    """
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
    return db.scalars(stmt).first()

def get_produto_by_code(db: Session, produto_code: str) -> Optional[ProdutoModel]:
    """Busca produto pelo código único (SKU)."""
    stmt = select(ProdutoModel).where(
        and_(
            ProdutoModel.codigo_produto == produto_code,
            ProdutoModel.ativo == True
        )
    )
    return db.scalars(stmt).first()

def get_produto_image_by_id(db: Session, image_id: int) -> ProdutoFotoModel:
    stmt = select(ProdutoFotoModel).where(ProdutoFotoModel.id == image_id)
    return db.scalars(stmt).first()

def get_produto_principal_image(db: Session, produto_id: int) -> Optional[ProdutoFotoModel]:
    stmt = select(ProdutoFotoModel).where(
        and_(
            ProdutoFotoModel.produto_id == produto_id,
            ProdutoFotoModel.principal == True
        )
    )
    return db.scalars(stmt).first()

# ===========================================================================
# ESCRITA (CREATE / UPDATE)
# ===========================================================================

def create_produto(db: Session, produto_to_add: ProdutoModel) -> ProdutoModel:
    """Adiciona e persiste um novo produto (cascade para estoque)."""
    db.add(produto_to_add)
    db.flush()
    db.refresh(produto_to_add)
    return produto_to_add

def create_produto_image(db: Session, image_to_add: ProdutoFotoModel) -> ProdutoFotoModel:
    db.add(image_to_add)
    db.flush()
    db.refresh(image_to_add)
    return image_to_add

def update_produto(db: Session, produto_to_update: ProdutoModel) -> ProdutoModel:
    """Persiste alterações em um produto rastreado pela sessão."""
    db.flush()
    db.refresh(produto_to_update)
    return produto_to_update

# ===========================================================================
# DELEÇÃO (DELETE)
# ===========================================================================

def delete_produto_image(db: Session, image_to_delete: ProdutoFotoModel) -> ProdutoFotoModel:
    db.delete(image_to_delete)
    db.flush()