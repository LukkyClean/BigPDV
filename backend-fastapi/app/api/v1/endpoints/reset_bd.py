from alembic import command
from fastapi import APIRouter, status

from app.db.base import Base
from app.db.migrations import _criar_alembic_config
from app.db.session import engine

router = APIRouter()

@router.get(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Reseta o banco de dados"
)
def reset_db():
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        alembic_cfg = _criar_alembic_config()
        command.stamp(alembic_cfg, "head")
        return "Banco de dados resetado com sucesso!"
    except Exception as e:
        raise(e)
