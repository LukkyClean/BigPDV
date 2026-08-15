"""adiciona colunas para configuracoes

Revision ID: 4600c632fe9b
Revises: c1d2e3f4a5b6
Create Date: 2026-06-20 16:55:02.534990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4600c632fe9b'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    )
    return result.fetchone() is not None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info('{table_name}')"))
    columns = [row[1] for row in result.fetchall()]
    return column_name in columns


def upgrade() -> None:
    """Upgrade schema."""
    # --- Criar tabelas apenas se não existirem ---
    if not _table_exists('contador_venda'):
        op.create_table('contador_venda',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('proximo_numero', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )

    if not _table_exists('configuracoes_os'):
        op.create_table('configuracoes_os',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('prazo_entrega_padrao', sa.Integer(), nullable=False),
        sa.Column('garantia_padrao', sa.String(length=20), nullable=False),
        sa.Column('prazo_abandono_dias', sa.Integer(), nullable=False),
        sa.Column('taxa_diagnostico_padrao', sa.Integer(), nullable=False),
        sa.Column('data_atualizacao', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id')
        )
        with op.batch_alter_table('configuracoes_os', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_configuracoes_os_id'), ['id'], unique=False)

    if not _table_exists('configuracoes_seguranca'):
        op.create_table('configuracoes_seguranca',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('pin_gerente', sa.String(length=255), nullable=True),
        sa.Column('secoes_protegidas', sa.JSON(), nullable=False),
        sa.Column('requer_pin_cancelar_venda', sa.Boolean(), nullable=False),
        sa.Column('requer_pin_reabrir_venda', sa.Boolean(), nullable=False),
        sa.Column('requer_pin_desconto_venda', sa.Boolean(), nullable=False),
        sa.Column('requer_pin_alterar_preco_venda', sa.Boolean(), nullable=False),
        sa.Column('requer_pin_cancelar_os', sa.Boolean(), nullable=False),
        sa.Column('requer_pin_reabrir_os', sa.Boolean(), nullable=False),
        sa.Column('requer_pin_desconto_os', sa.Boolean(), nullable=False),
        sa.Column('data_atualizacao', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id')
        )
        with op.batch_alter_table('configuracoes_seguranca', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_configuracoes_seguranca_id'), ['id'], unique=False)

    if not _table_exists('configuracoes_vendas'):
        op.create_table('configuracoes_vendas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('permitir_desconto', sa.Boolean(), nullable=False),
        sa.Column('desconto_maximo_percent', sa.Integer(), nullable=False),
        sa.Column('exigir_cliente_identificado', sa.Boolean(), nullable=False),
        sa.Column('valor_minimo_venda', sa.Integer(), nullable=False),
        sa.Column('permitir_parcelamento', sa.Boolean(), nullable=False),
        sa.Column('parcelas_maximas', sa.Integer(), nullable=False),
        sa.Column('data_atualizacao', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id')
        )
        with op.batch_alter_table('configuracoes_vendas', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_configuracoes_vendas_id'), ['id'], unique=False)

    if not _table_exists('comunicados'):
        op.create_table('comunicados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('funcionario_autor_id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=100), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['funcionario_autor_id'], ['funcionarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('comunicados', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_comunicados_empresa_id'), ['empresa_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_comunicados_id'), ['id'], unique=False)

    if not _table_exists('comunicados_leituras'):
        op.create_table('comunicados_leituras',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('comunicado_id', sa.Integer(), nullable=False),
        sa.Column('funcionario_id', sa.Integer(), nullable=False),
        sa.Column('lido_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['comunicado_id'], ['comunicados.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['funcionario_id'], ['funcionarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('comunicado_id', 'funcionario_id')
        )
        with op.batch_alter_table('comunicados_leituras', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_comunicados_leituras_id'), ['id'], unique=False)

    # --- Adicionar colunas apenas se não existirem ---
    empresas_new_cols = [
        ('indicador_ie', sa.String(length=1)),
        ('natureza_juridica', sa.String(length=50)),
        ('tipo_atividade', sa.String(length=20)),
        ('cnaes_secundarios', sa.String(length=500)),
        ('data_abertura', sa.String(length=10)),
        ('website', sa.String(length=255)),
    ]
    cols_to_add = [(name, typ) for name, typ in empresas_new_cols if not _column_exists('empresas', name)]
    if cols_to_add:
        with op.batch_alter_table('empresas', schema=None) as batch_op:
            for col_name, col_type in cols_to_add:
                batch_op.add_column(sa.Column(col_name, col_type, nullable=True))

    # ordem_servico_equipamentos — imei nullable (idempotente, batch recria a tabela)
    with op.batch_alter_table('ordem_servico_equipamentos', schema=None) as batch_op:
        batch_op.alter_column('imei',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)

    vendas_new_cols = [
        ('observacao_interna', sa.String(length=500)),
        ('motivo_cancelamento', sa.String(length=500)),
        ('numero_venda', sa.Integer()),
    ]
    cols_to_add_vendas = [(name, typ) for name, typ in vendas_new_cols if not _column_exists('vendas', name)]
    if cols_to_add_vendas:
        with op.batch_alter_table('vendas', schema=None) as batch_op:
            for col_name, col_type in cols_to_add_vendas:
                batch_op.add_column(sa.Column(col_name, col_type, nullable=True))
            if not _column_exists('vendas', 'numero_venda'):
                batch_op.create_unique_constraint('uq_vendas_numero_venda', ['numero_venda'])

    # Limpar tabela temporária órfã do alembic (se existir)
    if _table_exists('_alembic_tmp_ordem_servico_equipamentos'):
        op.drop_table('_alembic_tmp_ordem_servico_equipamentos')

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('vendas', schema=None) as batch_op:
        batch_op.drop_constraint('uq_vendas_numero_venda', type_='unique')
        batch_op.drop_column('numero_venda')
        batch_op.drop_column('motivo_cancelamento')
        batch_op.drop_column('observacao_interna')

    with op.batch_alter_table('ordem_servico_equipamentos', schema=None) as batch_op:
        batch_op.alter_column('imei',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)

    with op.batch_alter_table('empresas', schema=None) as batch_op:
        batch_op.drop_column('website')
        batch_op.drop_column('data_abertura')
        batch_op.drop_column('cnaes_secundarios')
        batch_op.drop_column('tipo_atividade')
        batch_op.drop_column('natureza_juridica')
        batch_op.drop_column('indicador_ie')

    with op.batch_alter_table('comunicados_leituras', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comunicados_leituras_id'))

    op.drop_table('comunicados_leituras')
    with op.batch_alter_table('comunicados', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comunicados_id'))
        batch_op.drop_index(batch_op.f('ix_comunicados_empresa_id'))

    op.drop_table('comunicados')
    with op.batch_alter_table('configuracoes_vendas', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_configuracoes_vendas_id'))

    op.drop_table('configuracoes_vendas')
    with op.batch_alter_table('configuracoes_seguranca', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_configuracoes_seguranca_id'))

    op.drop_table('configuracoes_seguranca')
    with op.batch_alter_table('configuracoes_os', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_configuracoes_os_id'))

    op.drop_table('configuracoes_os')
    op.drop_table('contador_venda')
    # ### end Alembic commands ###
