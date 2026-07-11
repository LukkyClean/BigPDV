"""refactor equipamento para objeto_servico

Revision ID: 965c71a2da9a
Revises: 814b4383d91e
Create Date: 2026-07-11 15:30:34.544249

Transforma o schema antigo (tabela ordem_servico_equipamentos + FK
equipamento_id + colunas legadas em ordens_servico) no schema novo
(tabela objetos_servico + FK objeto_id + campos dinamicos em
dados_adicionais JSON), PRESERVANDO os dados existentes.

Movimentacoes de dados:
  ordem_servico_equipamentos.imei             -> objetos_servico.dados_adicionais["imei"]
  ordem_servico_equipamentos.tipo_equipamento -> objetos_servico.dados_adicionais["tipo_equipamento"]
  ordens_servico.senha_aparelho     -> ordens_servico.dados_adicionais["senha_aparelho"]
  ordens_servico.acessorios         -> ordens_servico.dados_adicionais["acessorios"]
  ordens_servico.condicoes_aparelho -> ordens_servico.dados_adicionais["condicoes_aparelho"]

Os IDs sao preservados 1:1 (equipamento.id == objeto.id), entao
ordens_servico.objeto_id recebe o antigo equipamento_id diretamente.
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '965c71a2da9a'
down_revision: Union[str, Sequence[str], None] = '814b4383d91e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    """Upgrade: schema antigo (equipamento) -> novo (objeto_servico).

    IMPORTANTE: no startup, create_all() roda ANTES das migrations e pode criar
    a tabela objetos_servico (vazia) numa base de produção que ainda tem o schema
    antigo. Por isso a decisão de migrar é baseada na presença do schema ANTIGO
    (tabela ordem_servico_equipamentos + coluna equipamento_id), e não na ausência
    de objetos_servico.
    """
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # A migração de dados só é necessária/possível quando o schema ANTIGO ainda
    # está presente. Numa instalação nova (só schema novo), nada disso existe.
    if not _tem_tabela(insp, "ordem_servico_equipamentos"):
        return
    if not _tem_coluna(insp, "ordens_servico", "equipamento_id"):
        return

    # -----------------------------------------------------------------
    # 1) Garante a tabela objetos_servico (create_all pode já tê-la criado)
    # -----------------------------------------------------------------
    if not _tem_tabela(insp, "objetos_servico"):
        op.create_table(
            "objetos_servico",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
            sa.Column("marca", sa.String(length=100), nullable=False),
            sa.Column("modelo", sa.String(length=100), nullable=False),
            sa.Column("cor", sa.String(length=50), nullable=True),
            sa.Column("numero_serie", sa.String(length=100), nullable=False),
            sa.Column("dados_adicionais", sa.JSON(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("data_criacao", sa.DateTime(), nullable=False),
            sa.Column("data_atualizacao", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_objetos_servico_id", "objetos_servico", ["id"])
        op.create_index("ix_objetos_servico_cliente_id", "objetos_servico", ["cliente_id"])
        op.create_index("ix_objetos_servico_numero_serie", "objetos_servico", ["numero_serie"])
    else:
        # Criada por create_all (vazia): limpa antes de popular para evitar duplicidade.
        conn.execute(sa.text("DELETE FROM objetos_servico"))

    # -----------------------------------------------------------------
    # 2) Copia equipamentos -> objetos_servico (imei/tipo -> dados_adicionais)
    # -----------------------------------------------------------------
    equipamentos = conn.execute(sa.text(
        "SELECT id, cliente_id, tipo_equipamento, marca, modelo, numero_serie, "
        "imei, cor, ativo, data_criacao, data_atualizacao "
        "FROM ordem_servico_equipamentos"
    )).mappings().all()

    for eq in equipamentos:
        dados = {}
        if eq["tipo_equipamento"]:
            dados["tipo_equipamento"] = eq["tipo_equipamento"]
        if eq["imei"]:
            dados["imei"] = eq["imei"]
        conn.execute(sa.text(
            "INSERT INTO objetos_servico "
            "(id, cliente_id, marca, modelo, cor, numero_serie, dados_adicionais, "
            " ativo, data_criacao, data_atualizacao) "
            "VALUES (:id, :cliente_id, :marca, :modelo, :cor, :numero_serie, :dados, "
            " :ativo, :data_criacao, :data_atualizacao)"
        ), {
            "id": eq["id"],
            "cliente_id": eq["cliente_id"],
            "marca": eq["marca"],
            "modelo": eq["modelo"],
            "cor": eq["cor"],
            "numero_serie": eq["numero_serie"],
            "dados": json.dumps(dados) if dados else None,
            "ativo": eq["ativo"],
            "data_criacao": eq["data_criacao"],
            "data_atualizacao": eq["data_atualizacao"],
        })

    # -----------------------------------------------------------------
    # 3) ordens_servico: adiciona objeto_id + dados_adicionais e faz backfill
    # -----------------------------------------------------------------
    if not _tem_coluna(insp, "ordens_servico", "objeto_id"):
        op.add_column("ordens_servico", sa.Column("objeto_id", sa.Integer(), nullable=True))
    if not _tem_coluna(insp, "ordens_servico", "dados_adicionais"):
        op.add_column("ordens_servico", sa.Column("dados_adicionais", sa.JSON(), nullable=True))

    ordens = conn.execute(sa.text(
        "SELECT id, equipamento_id, senha_aparelho, acessorios, condicoes_aparelho "
        "FROM ordens_servico"
    )).mappings().all()

    for os_row in ordens:
        dados = {}
        if os_row["senha_aparelho"]:
            dados["senha_aparelho"] = os_row["senha_aparelho"]
        if os_row["acessorios"]:
            dados["acessorios"] = os_row["acessorios"]
        if os_row["condicoes_aparelho"]:
            dados["condicoes_aparelho"] = os_row["condicoes_aparelho"]
        conn.execute(sa.text(
            "UPDATE ordens_servico SET objeto_id = :oid, dados_adicionais = :dados WHERE id = :id"
        ), {
            "oid": os_row["equipamento_id"],
            "dados": json.dumps(dados) if dados else None,
            "id": os_row["id"],
        })

    # -----------------------------------------------------------------
    # 4) ordens_servico: torna objeto_id NOT NULL + FK, remove colunas legadas
    #    (batch mode: SQLite recria a tabela)
    # -----------------------------------------------------------------
    with op.batch_alter_table("ordens_servico", schema=None) as batch_op:
        batch_op.alter_column("objeto_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_ordens_servico_objeto_id", "objetos_servico", ["objeto_id"], ["id"]
        )
        batch_op.drop_column("equipamento_id")
        batch_op.drop_column("senha_aparelho")
        batch_op.drop_column("acessorios")
        batch_op.drop_column("condicoes_aparelho")

    # -----------------------------------------------------------------
    # 5) Remove a tabela antiga
    # -----------------------------------------------------------------
    op.drop_table("ordem_servico_equipamentos")


def downgrade() -> None:
    """Downgrade: schema novo (objeto_servico) -> antigo (equipamento)."""
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if _tem_tabela(insp, "ordem_servico_equipamentos") or not _tem_tabela(insp, "objetos_servico"):
        return

    # 1) Recria a tabela antiga ordem_servico_equipamentos
    op.create_table(
        "ordem_servico_equipamentos",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("tipo_equipamento", sa.String(length=20), nullable=False, server_default="OUTROS"),
        sa.Column("marca", sa.String(length=100), nullable=False),
        sa.Column("modelo", sa.String(length=100), nullable=False),
        sa.Column("numero_serie", sa.String(length=100), nullable=False),
        sa.Column("imei", sa.String(length=20), nullable=True),
        sa.Column("cor", sa.String(length=50), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("data_criacao", sa.DateTime(), nullable=False),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ordem_servico_equipamentos_id", "ordem_servico_equipamentos", ["id"])

    # 2) Copia objetos_servico -> ordem_servico_equipamentos (extrai imei/tipo do JSON)
    objetos = conn.execute(sa.text(
        "SELECT id, cliente_id, marca, modelo, cor, numero_serie, dados_adicionais, "
        "ativo, data_criacao, data_atualizacao FROM objetos_servico"
    )).mappings().all()

    for obj in objetos:
        dados = json.loads(obj["dados_adicionais"]) if obj["dados_adicionais"] else {}
        conn.execute(sa.text(
            "INSERT INTO ordem_servico_equipamentos "
            "(id, cliente_id, tipo_equipamento, marca, modelo, numero_serie, imei, cor, "
            " ativo, data_criacao, data_atualizacao) "
            "VALUES (:id, :cliente_id, :tipo, :marca, :modelo, :numero_serie, :imei, :cor, "
            " :ativo, :data_criacao, :data_atualizacao)"
        ), {
            "id": obj["id"],
            "cliente_id": obj["cliente_id"],
            "tipo": dados.get("tipo_equipamento") or "OUTROS",
            "marca": obj["marca"],
            "modelo": obj["modelo"],
            "numero_serie": obj["numero_serie"],
            "imei": dados.get("imei"),
            "cor": obj["cor"],
            "ativo": obj["ativo"],
            "data_criacao": obj["data_criacao"],
            "data_atualizacao": obj["data_atualizacao"],
        })

    # 3) ordens_servico: readiciona colunas legadas
    op.add_column("ordens_servico", sa.Column("equipamento_id", sa.Integer(), nullable=True))
    op.add_column("ordens_servico", sa.Column("senha_aparelho", sa.String(length=100), nullable=True))
    op.add_column("ordens_servico", sa.Column("acessorios", sa.Text(), nullable=True))
    op.add_column("ordens_servico", sa.Column("condicoes_aparelho", sa.Text(), nullable=True))

    ordens = conn.execute(sa.text(
        "SELECT id, objeto_id, dados_adicionais FROM ordens_servico"
    )).mappings().all()

    for os_row in ordens:
        dados = json.loads(os_row["dados_adicionais"]) if os_row["dados_adicionais"] else {}
        conn.execute(sa.text(
            "UPDATE ordens_servico SET equipamento_id = :eid, senha_aparelho = :senha, "
            "acessorios = :acess, condicoes_aparelho = :cond WHERE id = :id"
        ), {
            "eid": os_row["objeto_id"],
            "senha": dados.get("senha_aparelho"),
            "acess": dados.get("acessorios"),
            "cond": dados.get("condicoes_aparelho"),
            "id": os_row["id"],
        })

    # 4) ordens_servico: FK equipamento_id NOT NULL, remove objeto_id/dados_adicionais
    with op.batch_alter_table("ordens_servico", schema=None) as batch_op:
        batch_op.alter_column("equipamento_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_ordens_servico_equipamento_id", "ordem_servico_equipamentos",
            ["equipamento_id"], ["id"]
        )
        batch_op.drop_column("objeto_id")
        batch_op.drop_column("dados_adicionais")

    # 5) Remove a tabela nova
    op.drop_table("objetos_servico")
