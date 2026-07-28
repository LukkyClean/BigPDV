"""add segmento empresa, cpf nullable funcionario, funcionario master

Revision ID: b4c5d6e7f8a9
Revises: 6b6dda97d4a0
Create Date: 2026-05-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = '6b6dda97d4a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    1. Adiciona coluna 'segmento' na tabela 'empresas'.
    2. Torna 'cpf' nullable na tabela 'funcionarios' (via SQL direto para SQLite).
    3. Cria Funcionario para cada Usuario Master sem funcionario vinculado.
    """
    connection = op.get_bind()

    # --- 1. Adicionar coluna segmento na tabela empresas ---
    op.add_column('empresas', sa.Column('segmento', sa.String(50), nullable=True))

    # --- 2. Tornar cpf nullable na tabela funcionarios ---
    # SQLite não suporta ALTER COLUMN. O batch_alter_table recria a tabela,
    # mas falha com FK constraints de outras tabelas que referenciam funcionarios.
    # Solução: desabilitar FK checks temporariamente.
    connection.execute(sa.text("PRAGMA foreign_keys=OFF"))

    with op.batch_alter_table('funcionarios') as batch_op:
        batch_op.alter_column(
            'cpf',
            existing_type=sa.String(11),
            nullable=True,
        )

    connection.execute(sa.text("PRAGMA foreign_keys=ON"))

    # --- 3. Data migration: criar Funcionario para Master Users sem funcionario ---
    masters_sem_funcionario = connection.execute(
        sa.text("""
            SELECT u.id, u.nome, u.email, u.empresa_id
            FROM usuarios u
            LEFT JOIN funcionarios f ON f.usuario_id = u.id
            WHERE u.is_master = 1
              AND f.id IS NULL
              AND u.empresa_id IS NOT NULL
        """)
    ).fetchall()

    for master in masters_sem_funcionario:
        connection.execute(
            sa.text("""
                INSERT INTO funcionarios (empresa_id, usuario_id, nome, email, cpf, ativo)
                VALUES (:empresa_id, :usuario_id, :nome, :email, NULL, 1)
            """),
            {
                "empresa_id": master.empresa_id,
                "usuario_id": master.id,
                "nome": master.nome,
                "email": master.email,
            }
        )


def downgrade() -> None:
    """Reverte as alterações."""
    connection = op.get_bind()

    # 1. Remover funcionarios criados para masters (cpf IS NULL)
    connection.execute(
        sa.text("""
            DELETE FROM funcionarios
            WHERE cpf IS NULL
              AND usuario_id IN (SELECT id FROM usuarios WHERE is_master = 1)
        """)
    )

    # 2. Tornar cpf NOT NULL novamente
    connection.execute(sa.text("PRAGMA foreign_keys=OFF"))

    with op.batch_alter_table('funcionarios') as batch_op:
        batch_op.alter_column(
            'cpf',
            existing_type=sa.String(11),
            nullable=False,
        )

    connection.execute(sa.text("PRAGMA foreign_keys=ON"))

    # 3. Remover coluna segmento
    op.drop_column('empresas', 'segmento')
