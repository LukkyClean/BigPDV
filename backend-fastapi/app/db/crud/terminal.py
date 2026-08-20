# ---------------------------------------------------------------------------
# ARQUIVO: crud/terminal.py
# MÓDULO: Acesso a Dados (Repository)
# DESCRIÇÃO: Queries do cadastro durável de terminais.
# ---------------------------------------------------------------------------

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.terminal import Terminal


def get_por_hwid(db: Session, hwid: str) -> Optional[Terminal]:
    return db.scalars(select(Terminal).where(Terminal.hwid == hwid)).first()


def get_por_id(db: Session, terminal_id: int, empresa_id: int) -> Optional[Terminal]:
    return db.scalars(
        select(Terminal).where(
            Terminal.id == terminal_id,
            Terminal.empresa_id == empresa_id,
        )
    ).first()


def listar(db: Session, empresa_id: int) -> Sequence[Terminal]:
    """Os terminais da loja, os batizados primeiro.

    Máquina sem nome vai para o fim: a lista existe para ser conferida, e o que
    falta configurar tem que ser o que salta aos olhos — mas depois do que já
    está pronto, senão o dono não reconhece a própria loja na primeira olhada.
    """
    return db.scalars(
        select(Terminal)
        .where(Terminal.empresa_id == empresa_id, Terminal.ativo.is_(True))
        .order_by(Terminal.nome.is_(None), Terminal.nome, Terminal.id)
    ).all()


def nomes_por_hwid(db: Session, hwids: Sequence[str]) -> dict[str, Optional[str]]:
    """Resolve vários HWIDs de uma vez.

    Uma consulta por linha viraria N+1 no relatório de caixa, que o dono abre
    todo dia e que lista um turno por linha.
    """
    if not hwids:
        return {}
    encontrados = db.scalars(select(Terminal).where(Terminal.hwid.in_(list(hwids)))).all()
    return {t.hwid: t.nome for t in encontrados}


def criar(db: Session, terminal: Terminal) -> Terminal:
    db.add(terminal)
    db.flush()
    db.refresh(terminal)
    return terminal
