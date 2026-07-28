from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy import select, func, cast, String

from app.core.busca import filtro_busca
from app.db.models.orcamento import Orcamento
from app.db.models.orcamento_produto import OrcamentoProduto
from app.db.models.funcionario import Funcionario

from app.schemas.orcamentos import OrcamentoStatusSummary

from typing import Sequence


def create_orcamento(db: Session, orcamento_data: Orcamento) -> Orcamento:
    db.add(orcamento_data)
    db.flush()
    db.refresh(orcamento_data)
    return orcamento_data


def add_product_to_orcamento(db: Session, product_data: OrcamentoProduto) -> OrcamentoProduto:
    db.add(product_data)
    db.flush()
    db.refresh(product_data)
    return product_data


def get_orcamento_by_id(db: Session, orcamento_id: int) -> Orcamento:
    stmt = (
        select(Orcamento)
        .where(Orcamento.id == orcamento_id)
        .options(joinedload(Orcamento.funcionario).joinedload(Funcionario.cargo))
    )
    return db.scalar(stmt)


def update_orcamento(db: Session, orcamento: Orcamento) -> Orcamento:
    db.flush()
    db.refresh(orcamento)
    return orcamento


def update_product_in_orcamento(db: Session, product: OrcamentoProduto) -> OrcamentoProduto:
    db.flush()
    db.refresh(product)
    return product


def get_product_by_id(db: Session, item_id: int) -> OrcamentoProduto:
    stmt = select(OrcamentoProduto).where(OrcamentoProduto.id == item_id)
    return db.scalar(stmt)


def remove_product_from_orcamento(db: Session, product: OrcamentoProduto) -> None:
    db.delete(product)
    db.flush()


def delete_orcamento(db: Session, orcamento: Orcamento) -> None:
    db.delete(orcamento)
    db.flush()


def get_orcamentos_by_search(
    db: Session,
    filters: dict,
    skip: int = 0,
    limit: int = 20,
) -> tuple[Sequence[Orcamento], int]:

    query = select(Orcamento).options(
        joinedload(Orcamento.funcionario).joinedload(Funcionario.cargo)
    )

    funcionario_id = filters.get("funcionario_id")
    if funcionario_id:
        query = query.where(Orcamento.funcionario_id == funcionario_id)

    search = filters.get("search")
    if search:
        query = query.join(Funcionario, Funcionario.id == Orcamento.funcionario_id)

        filtro = filtro_busca(search, (
            cast(Orcamento.id, String),
            Funcionario.nome,
        ))
        if filtro is not None:
            query = query.where(filtro)

    convertido = filters.get("convertido")
    if convertido is not None:
        query = query.where(Orcamento.convertido == convertido)

    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    stmt = query.order_by(Orcamento.id.desc()).offset(skip).limit(limit)
    orcamentos = db.scalars(stmt).unique().all()

    return orcamentos, total


def get_orcamentos_status(db: Session, funcionario_id: int | None = None) -> OrcamentoStatusSummary:
    stmt = (
        select(
            func.count(Orcamento.id)
                .filter(Orcamento.convertido == False)
                .label("ativos"),
            func.count(Orcamento.id)
                .filter(Orcamento.convertido == True)
                .label("convertidos"),
        )
    )

    if funcionario_id:
        stmt = stmt.where(Orcamento.funcionario_id == funcionario_id)

    result = db.execute(stmt).first()

    return OrcamentoStatusSummary(
        orcamentos_ativos=result.ativos or 0,
        orcamentos_convertidos=result.convertidos or 0,
    )
