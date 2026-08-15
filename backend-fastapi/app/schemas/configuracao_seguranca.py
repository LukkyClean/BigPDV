import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field, field_validator

# Seções do painel de configurações que podem ser protegidas por PIN
# ("seguranca" é sempre protegida quando há PIN; "suporte" nunca é)
SECOES_PROTEGIVEIS = {
    "regras-de-vendas",
    "produtos-estoque",
    "ordens-de-servico",
    "clientes-cadastro",
    "financeiro-taxas",
    "integracoes-apis",
    "impressao",
    "formatos-exibicao",
    "backup-dados",
}


class ConfiguracaoSegurancaRead(BaseModel):
    id: int
    empresa_id: int

    pin_gerente: Optional[str] = Field(None, exclude=True)

    @computed_field
    @property
    def tem_pin_configurado(self) -> bool:
        return bool(self.pin_gerente)

    secoes_protegidas: List[str] = []

    requer_pin_cancelar_venda: bool
    requer_pin_reabrir_venda: bool
    requer_pin_desconto_venda: bool
    requer_pin_alterar_preco_venda: bool

    requer_pin_sangria: bool

    requer_pin_cancelar_os: bool
    requer_pin_reabrir_os: bool
    requer_pin_desconto_os: bool

    data_atualizacao: datetime

    model_config = {"from_attributes": True}


class VerificarPinPayload(BaseModel):
    pin: str = Field(..., description="PIN do gerente a verificar")


class ConfiguracaoSegurancaUpdate(BaseModel):
    pin_gerente: Optional[str] = None

    @field_validator("pin_gerente")
    @classmethod
    def validar_formato_pin(cls, v: Optional[str]) -> Optional[str]:
        # None ou vazio enviados explicitamente = remover o PIN;
        # campo ausente do payload = manter o PIN atual
        if v is None or v == "":
            return v
        if not re.fullmatch(r"\d{4,6}", v):
            raise ValueError(
                "PIN_GERENTE_FORMATO_INVALIDO: o PIN deve ter de 4 a 6 dígitos numéricos"
            )
        return v

    secoes_protegidas: Optional[List[str]] = None

    @field_validator("secoes_protegidas")
    @classmethod
    def validar_secoes_protegidas(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        invalidas = set(v) - SECOES_PROTEGIVEIS
        if invalidas:
            raise ValueError(
                f"SECOES_PROTEGIDAS_INVALIDAS: seções desconhecidas: {sorted(invalidas)}"
            )
        return v

    requer_pin_cancelar_venda: Optional[bool] = None
    requer_pin_reabrir_venda: Optional[bool] = None
    requer_pin_desconto_venda: Optional[bool] = None
    requer_pin_alterar_preco_venda: Optional[bool] = None

    requer_pin_sangria: Optional[bool] = None

    requer_pin_cancelar_os: Optional[bool] = None
    requer_pin_reabrir_os: Optional[bool] = None
    requer_pin_desconto_os: Optional[bool] = None
