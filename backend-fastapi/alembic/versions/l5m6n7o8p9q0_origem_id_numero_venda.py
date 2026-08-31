"""converte documento_fiscal.origem_id de venda.id para venda.numero_venda

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-08-29 12:00:00.000000

CONTEXTO:
O campo origem_id dos DocumentoFiscal de tipo VENDA armazenava venda.id (PK).
Agora armazena venda.numero_venda (número real da venda finalizada).
Esta migration converte os registros existentes.

SEGURANÇA:
- Verifica existência da tabela antes de operar
- Vendas sem numero_venda (não finalizadas) têm origem_id setado para NULL
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'l5m6n7o8p9q0'
down_revision: Union[str, Sequence[str], None] = 'k4l5m6n7o8p9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table("documento_fiscal") or not insp.has_table("vendas"):
        return

    # Buscar todos os documentos fiscais de vendas com origem_id preenchido
    rows = conn.execute(
        sa.text(
            "SELECT df.id, df.origem_id, df.ref_api, v.numero_venda "
            "FROM documento_fiscal df "
            "LEFT JOIN vendas v ON v.id = df.origem_id "
            "WHERE df.origem_tipo = 'VENDA' AND df.origem_id IS NOT NULL"
        )
    ).fetchall()

    for doc_id, old_origem_id, ref_api, numero_venda in rows:
        if numero_venda is not None:
            new_ref = ref_api.replace(
                f"venda-{old_origem_id}", f"venda-{numero_venda}"
            ) if ref_api else ref_api
            conn.execute(
                sa.text(
                    "UPDATE documento_fiscal "
                    "SET origem_id = :numero_venda, ref_api = :ref_api "
                    "WHERE id = :doc_id"
                ),
                {"numero_venda": numero_venda, "ref_api": new_ref, "doc_id": doc_id},
            )
        else:
            # Venda sem numero_venda (não finalizada) — limpar referência
            conn.execute(
                sa.text(
                    "UPDATE documento_fiscal SET origem_id = NULL WHERE id = :doc_id"
                ),
                {"doc_id": doc_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table("documento_fiscal") or not insp.has_table("vendas"):
        return

    # Reverter: converter numero_venda de volta para venda.id
    rows = conn.execute(
        sa.text(
            "SELECT df.id, df.origem_id, df.ref_api, v.id as venda_id "
            "FROM documento_fiscal df "
            "LEFT JOIN vendas v ON v.numero_venda = df.origem_id "
            "WHERE df.origem_tipo = 'VENDA' AND df.origem_id IS NOT NULL"
        )
    ).fetchall()

    for doc_id, old_origem_id, ref_api, venda_id in rows:
        if venda_id is not None:
            new_ref = ref_api.replace(
                f"venda-{old_origem_id}", f"venda-{venda_id}"
            ) if ref_api else ref_api
            conn.execute(
                sa.text(
                    "UPDATE documento_fiscal "
                    "SET origem_id = :venda_id, ref_api = :ref_api "
                    "WHERE id = :doc_id"
                ),
                {"venda_id": venda_id, "ref_api": new_ref, "doc_id": doc_id},
            )
