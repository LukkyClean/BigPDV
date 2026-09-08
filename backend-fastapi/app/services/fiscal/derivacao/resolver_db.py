# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/resolver_db.py
# DESCRIÇÃO: ÚNICA porta ORM da camada de derivação.
# ---------------------------------------------------------------------------
"""
Ponte banco → contexto puro.

Espelha a divisão que já funciona no `tax_engine`: um arquivo só toca em
Session, e todo o resto do pacote é função pura. É isso que permite testar a
tabela de decisão do CFOP sem levantar banco.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.empresa import Empresa
from app.services.fiscal.helpers import obter_crt

from .types import ContextoDerivacao, TipoAtividade


def _tipo_atividade(empresa: Empresa) -> Optional[TipoAtividade]:
    """
    Lê `empresas.tipo_atividade`, que já existe no cadastro.

    É a chave do 5101 vs 5102 e não precisou de coluna nova: indústria,
    panificação com produção própria, marcenaria e beneficiamento já são
    distinguidos ali.
    """
    bruto = (getattr(empresa, "tipo_atividade", None) or "").strip().upper()
    try:
        return TipoAtividade(bruto)
    except ValueError:
        return None


def contexto_do_cadastro(db: Session, empresa_id: int) -> ContextoDerivacao:
    """
    Contexto para sugerir campos no CADASTRO de produto.

    Sem venda: o que existe aqui é a empresa. Por isso `uf_destinatario` e
    `indicador_presenca` ficam vazios e o CFOP cai na operação interna, que é
    o caso do cadastro — o produto nasce com o CFOP da venda típica da loja.
    """
    from app.db.crud import fiscal as crud

    empresa = crud.get_empresa(db, empresa_id)
    endereco = crud.get_endereco_empresa(db, empresa_id)

    uf = ""
    if endereco is not None:
        estado = endereco.estado
        uf = estado.value if hasattr(estado, "value") else str(estado)

    return ContextoDerivacao(
        uf_emitente=uf,
        crt=obter_crt(empresa),
        tipo_atividade=_tipo_atividade(empresa) if empresa else None,
    )
