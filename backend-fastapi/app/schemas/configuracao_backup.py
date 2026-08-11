from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConfiguracaoBackupRead(BaseModel):
    id: int
    empresa_id: int

    backup_automatico_ativo: bool
    frequencia: str
    horario: str

    data_atualizacao: datetime

    model_config = {"from_attributes": True}


class ConfiguracaoBackupUpdate(BaseModel):
    backup_automatico_ativo: Optional[bool] = None
    frequencia: Optional[str] = Field(None, pattern=r"^(diario|8horas|12horas)$")
    horario: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
