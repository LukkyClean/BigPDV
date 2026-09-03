from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy import select, func, cast, String, extract, nullslast
from datetime import datetime

from calendar import monthrange

from app.core.tempo import hoje_local, intervalo_utc
from app.db.models.venda import Venda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.cliente import ClientePF, ClientePJ
from app.db.models.funcionario import Funcionario

from app.schemas.vendas import VendaStatusSummary

from app.core.busca import filtro_busca
from app.core.enum import VendaStatus

from typing import Sequence

def create_sale(db: Session, sale_data: Venda) -> Venda:
    db.add(sale_data)
    db.flush()
    db.refresh(sale_data)
    return sale_data

def add_product_to_sale(db: Session, product_data: ProdutoVenda) -> ProdutoVenda:
    db.add(product_data)
    db.flush()
    db.refresh(product_data)
    return product_data

def get_sale_by_id(db: Session, sale_id: int) -> Venda:
    stmt = (
        select(Venda)
        .where(Venda.id == sale_id)
        .options(joinedload(Venda.funcionario).joinedload(Funcionario.cargo))
    )
    return db.scalar(stmt)

def update_sale(db: Session, sale: Venda) -> Venda:
    db.flush()
    db.refresh(sale)
    return sale

def update_product_in_sale(db: Session, product: ProdutoVenda) -> ProdutoVenda:
    db.flush()
    db.refresh(product)
    return product

def get_product_by_id(db: Session, item_id: int) -> ProdutoVenda:
    stmt = select(ProdutoVenda).where(ProdutoVenda.id == item_id)
    return db.scalar(stmt)

def remove_product_from_sale(db: Session, product: ProdutoVenda) -> None:
    db.delete(product)
    db.flush()

def get_sales_by_search(
    db: Session,
    filters: dict,
    skip: int = 0,
    limit: int = 20,
) -> tuple[Sequence[Venda], int]:
    
    query = select(Venda).options(
        joinedload(Venda.funcionario).joinedload(Funcionario.cargo)
    )

    funcionario_id = filters.get("funcionario_id")
    if funcionario_id:
        query = query.where(Venda.funcionario_id == funcionario_id)

    search = filters.get("search")
    if search:
        cliente_pj = aliased(ClientePJ)
        cliente_pf = aliased(ClientePF)

        query = (
            query
            .join(Funcionario, Funcionario.id == Venda.funcionario_id)
            .outerjoin(Venda.cliente)
            .outerjoin(cliente_pj, cliente_pj.id == Venda.cliente_id)
            .outerjoin(cliente_pf, cliente_pf.id == Venda.cliente_id)
        )

        # Os números são convertidos para texto porque a busca é uma só: o
        # operador digita "312" ou "maria" no mesmo campo.
        filtro = filtro_busca(search, (
            cast(Venda.numero_venda, String),
            cast(Venda.id, String),
            cliente_pf.nome,
            cliente_pj.razao_social,
            cliente_pj.nome_fantasia,
            Funcionario.nome,
        ))
        if filtro is not None:
            query = query.where(filtro)

    status = filters.get("status")
    if status:
        query = query.where(Venda.status == status)

    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0   

    stmt = query.order_by(
        Venda.atualizado_em.desc(),
        nullslast(Venda.numero_venda.desc()),
    ).offset(skip).limit(limit)
    sales = db.scalars(stmt).unique().all()

    return sales, total 

def get_sales_status(db: Session, funcionario_id: int | None = None) -> VendaStatusSummary:
    payments_subq = (
        select(
            PagamentoVenda.venda_id,
            func.sum(PagamentoVenda.valor).label("total_pago")
        )
        .group_by(PagamentoVenda.venda_id)
        .subquery()
    )

    stmt = (
        select(
            func.count(Venda.id)
                .filter(Venda.status == VendaStatus.ATIVA)
                .label("rascunho"),

            func.count(Venda.id)
                .filter(Venda.status == VendaStatus.FINALIZADA)
                .label("finalizada"),

            func.count(Venda.id)
                .filter(Venda.status == VendaStatus.CANCELADA)
                .label("cancelada"),

            func.avg(payments_subq.c.total_pago)
                .filter(Venda.status == VendaStatus.FINALIZADA)
                .label("ticket_medio"),
        )
        .outerjoin(payments_subq, payments_subq.c.venda_id == Venda.id)
    )

    if funcionario_id:
        # Mes corrente pelo calendario LOCAL da loja, convertido para os
        # limites UTC da coluna. Extrair mes/ano direto da coluna jogaria as
        # vendas do fim do ultimo dia do mes para o mes seguinte.
        hoje = hoje_local()
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        inicio_mes, fim_mes = intervalo_utc(
            hoje.replace(day=1), hoje.replace(day=ultimo_dia),
        )
        stmt = stmt.where(
            Venda.funcionario_id == funcionario_id,
            Venda.criado_em >= inicio_mes,
            Venda.criado_em <= fim_mes,
        )

    result = db.execute(stmt).first()

    ticket_medio = result.ticket_medio or 0

    return VendaStatusSummary(
        vendas_ativas=result.rascunho or 0,
        vendas_finalizadas=result.finalizada or 0,
        vendas_canceladas=result.cancelada or 0,
        ticket_medio=int(round(ticket_medio)),
    )
 

def reservar_proximo_numero_venda(db: Session) -> int:
    """
    Reserva atomicamente o próximo número de venda e o devolve.

    Um único UPDATE ... RETURNING: não existe janela entre ler o contador e
    gravá-lo, então dois caixas finalizando ao mesmo tempo nunca disputam o
    mesmo número.

    Por que não `with_for_update()`: o dialeto SQLite do SQLAlchemy aceita a
    chamada e não emite FOR UPDATE nenhum — o lock fica decorativo. Como o
    banco do StartBig é SQLite embarcado, a corrida permanecia aberta, e o
    segundo terminal só descobria pela violação de unicidade de numero_venda,
    justamente no fechamento da venda.
    """
    from sqlalchemy import text

    linha = db.execute(
        text(
            "UPDATE contador_venda "
            "SET proximo_numero = proximo_numero + 1 "
            "WHERE id = 1 "
            "RETURNING proximo_numero - 1"
        )
    ).fetchone()

    if linha is None:
        return None

    from app.db.models.contador_venda import ContadorVenda
    contador = db.get(ContadorVenda, 1)
    if contador is not None:
        db.expire(contador, ["proximo_numero"])

    return int(linha[0])
