# ---------------------------------------------------------------------------
# ARQUIVO: app/db/crud/tributacao.py
# MÓDULO: Repository — Tributação padrão da loja e regras por NCM
# ---------------------------------------------------------------------------

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db.models.tributacao import RegraTributariaNcm, TributacaoPadrao


# =========================
# Tributação padrão da loja
# =========================

def get_tributacao_padrao(db: Session, empresa_id: int) -> Optional[TributacaoPadrao]:
    """A linha da empresa, ou None enquanto ninguém configurou."""
    return (
        db.query(TributacaoPadrao)
        .filter(TributacaoPadrao.empresa_id == empresa_id)
        .first()
    )


def upsert_tributacao_padrao(db: Session, empresa_id: int, dados) -> TributacaoPadrao:
    """
    Cria ou atualiza a tributação padrão.

    `exclude_unset` de propósito: quem manda só o CSOSN não apaga o CFOP que
    já estava lá.
    """
    registro = get_tributacao_padrao(db, empresa_id)
    valores = dados.model_dump(exclude_unset=True)

    if registro is None:
        registro = TributacaoPadrao(empresa_id=empresa_id, **valores)
        db.add(registro)
    else:
        for campo, valor in valores.items():
            setattr(registro, campo, valor)

    db.flush()
    db.refresh(registro)
    return registro


# =========================
# Regras por NCM
# =========================

def get_regra_ncm(db: Session, empresa_id: int, ncm: str) -> Optional[RegraTributariaNcm]:
    return (
        db.query(RegraTributariaNcm)
        .filter(
            RegraTributariaNcm.empresa_id == empresa_id,
            RegraTributariaNcm.ncm == ncm,
        )
        .first()
    )


def listar_regras_ncm(db: Session, empresa_id: int) -> Sequence[RegraTributariaNcm]:
    return (
        db.query(RegraTributariaNcm)
        .filter(RegraTributariaNcm.empresa_id == empresa_id)
        .order_by(RegraTributariaNcm.ncm)
        .all()
    )


def upsert_regra_ncm(db: Session, empresa_id: int, ncm: str, dados) -> RegraTributariaNcm:
    registro = get_regra_ncm(db, empresa_id, ncm)
    valores = dados.model_dump(exclude_unset=True, exclude={"ncm"})

    if registro is None:
        registro = RegraTributariaNcm(empresa_id=empresa_id, ncm=ncm, **valores)
        db.add(registro)
    else:
        for campo, valor in valores.items():
            setattr(registro, campo, valor)

    db.flush()
    db.refresh(registro)
    return registro


def deletar_regra_ncm(db: Session, empresa_id: int, ncm: str) -> bool:
    """
    Apaga a regra. Os produtos daquele NCM voltam a seguir o padrão da loja —
    nenhum produto é alterado, porque a cascata é resolvida na leitura.
    """
    registro = get_regra_ncm(db, empresa_id, ncm)
    if registro is None:
        return False
    db.delete(registro)
    db.flush()
    return True
