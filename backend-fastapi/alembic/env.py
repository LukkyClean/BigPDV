import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Garante que o diretório backend-fastapi/ está no sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.base import Base

# Importa todos os models para que o autogenerate detecte as tabelas
import app.db.models.cargo
import app.db.models.cliente
import app.db.models.configuracao_clientes
import app.db.models.configuracao_os
import app.db.models.configuracao_produtos
import app.db.models.empresa
import app.db.models.empresa_fiscal_settings
import app.db.models.endereco
import app.db.models.estoque
import app.db.models.forma_pagamento
import app.db.models.fornecedor
import app.db.models.funcionario
import app.db.models.log_produto
import app.db.models.movimentacao_estoque
import app.db.models.orcamento
import app.db.models.orcamento_produto
import app.db.models.ordem_servico
import app.db.models.objeto_servico
import app.db.models.ordem_servico_foto
import app.db.models.ordem_servico_item
import app.db.models.ordem_servico_pagamento
import app.db.models.produto
import app.db.models.produto_fotos
import app.db.models.servico
import app.db.models.sessao_caixa
import app.db.models.token
import app.db.models.usuario
import app.db.models.venda
import app.db.models.venda_pagamento
import app.db.models.venda_produto

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # necessário para SQLite (ALTER TABLE limitado)
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # necessário para SQLite (ALTER TABLE limitado)
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
