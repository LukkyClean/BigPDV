# ---------------------------------------------------------------------------
# ARQUIVO: schemas/fornecedor.py
# DESCRIÇÃO: Schemas Pydantic para validação de dados de Fornecedor.
#            Define as estruturas de entrada (Create/Update) e saída (Read).
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List

from app.core.validators import validar_cnpj, validar_cpf
from app.schemas.endereco import Endereco, EnderecoRead, EnderecoUpdate
from app.core.enum import BankAccountType

# =========================
# Schema Pydantic: FornecedorCreate (Criação)
# =========================
class FornecedorCreate(BaseModel):
    """
    Schema para validar os dados de ENTRADA ao criar um novo Fornecedor.
    """
    tipo: Optional[str] = Field(
        'produto',
        max_length=20,
        description="Tipo do fornecedor: produto, transportadora ou entregador"
    )
    nome: str = Field(
        ...,
        max_length=255,
        description="Nome ou Razão Social do fornecedor/entregador"
    )
    cnpj: Optional[str] = Field(
        None,
        max_length=14,
        pattern=r"^\d{14}$",
        description="CNPJ do fornecedor (apenas números, 14 dígitos) — nulo para entregadores"
    )
    cpf: Optional[str] = Field(
        None,
        max_length=11,
        pattern=r"^\d{11}$",
        description="CPF do entregador (apenas números, 11 dígitos)"
    )
    nome_fantasia: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome fantasia da empresa fornecedora"
    )
    ie: Optional[str] = Field(
        None,
        max_length=14,
        description="Inscrição Estadual do fornecedor"
    )
    telefone: Optional[str] = Field(
        None,
        description="Telefone para contato"
    )
    celular: Optional[str] = Field(
        None,
        description="Celular para contato"
    )
    email: Optional[str] = Field(
        None,
        description="Email para contato"
    )
    representante: Optional[str] = Field(
        None,
        description="Nome do representante da empresa fornecedora"
    )
    veiculo: Optional[str] = Field(
        None,
        max_length=100,
        description="Veículo do entregador"
    )
    placa: Optional[str] = Field(
        None,
        max_length=10,
        description="Placa do veículo do entregador"
    )
    observacao: Optional[str] = Field(
        None,
        description="Observações gerais sobre o fornecedor"
    )
    banco: Optional[str] = Field(
        None,
        max_length=100,
        description="Nome do banco"
    )
    agencia: Optional[str] = Field(
        None,
        max_length=20,
        description="Número da agência bancária"
    )
    conta: Optional[str] = Field(
        None,
        max_length=20,
        description="Número da conta bancária"
    )
    tipo_conta: Optional[BankAccountType] = Field(
        None,
        description="Tipo da conta: CORRENTE ou POUPANCA"
    )
    pix: Optional[str] = Field(
        None,
        max_length=150,
        description="Chave PIX do fornecedor"
    )
    endereco: Optional[List[Endereco]] = Field(
        None,
        description="Endereço do fornecedor"
    )

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf_fornecedor(cls, v):
        return validar_cpf(v)

    @field_validator("cnpj", mode="before")
    @classmethod
    def validar_cnpj_fornecedor(cls, v):
        return validar_cnpj(v)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "tipo": "produto",
                "nome": "Distribuidora de Componentes LTDA",
                "cnpj": "72345734000113",
                "nome_fantasia": "BigTech Componentes",
                "ie": "123456789012",
                "telefone": "8535667788",
                "representante": "Mauro Filho",
            }
        }
    )

# =========================
# Schema Pydantic: FornecedorRead (Leitura/Resposta)
# =========================
class FornecedorRead(FornecedorCreate):
    """
    Schema para formatar os dados de SAÍDA (resposta da API) de um Fornecedor.
    """
    id: int = Field(..., description="ID do fornecedor")
    ativo: bool = Field(..., description="Status do fornecedor")
    endereco: Optional[List[EnderecoRead]] = Field(
        None,
        description="Endereço do fornecedor"
    )

# =========================
# Schema Pydantic: FornecedorUpdate (Atualização)
# =========================
class FornecedorUpdate(BaseModel):
    """
    Schema para ATUALIZAR um fornecedor existente.
    Todos os campos são opcionais, permitindo atualizações parciais.
    """
    tipo: Optional[str] = Field(None, max_length=20)
    nome: Optional[str] = Field(None, max_length=255)
    cnpj: Optional[str] = Field(None, max_length=14, pattern=r"^\d{14}$")
    cpf: Optional[str] = Field(None, max_length=11, pattern=r"^\d{11}$")
    nome_fantasia: Optional[str] = Field(None, max_length=255)
    ie: Optional[str] = Field(None, max_length=14)
    telefone: Optional[str] = Field(None)
    celular: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    representante: Optional[str] = Field(None)
    veiculo: Optional[str] = Field(None, max_length=100)
    placa: Optional[str] = Field(None, max_length=10)
    observacao: Optional[str] = Field(None)
    banco: Optional[str] = Field(None, max_length=100)
    agencia: Optional[str] = Field(None, max_length=20)
    conta: Optional[str] = Field(None, max_length=20)
    tipo_conta: Optional[BankAccountType] = Field(None)
    pix: Optional[str] = Field(None, max_length=150)
    endereco: Optional[List[EnderecoUpdate]] = Field(None)

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf_fornecedor(cls, v):
        return validar_cpf(v)

    @field_validator("cnpj", mode="before")
    @classmethod
    def validar_cnpj_fornecedor(cls, v):
        return validar_cnpj(v)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "nome_fantasia": "Novo Nome Fantasia Tech",
            }
        }
    )
