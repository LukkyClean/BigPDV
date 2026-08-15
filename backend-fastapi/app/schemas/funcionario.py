# ---------------------------------------------------------------------------
# ARQUIVO: schemas/funcionario_schema.py
# MÓDULO: Schemas Pydantic (DTOs)
# DESCRIÇÃO: Definição de contratos de entrada e saída para Funcionários.
# ---------------------------------------------------------------------------

from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from app.schemas.endereco import Endereco, EnderecoRead, EnderecoUpdate
from app.schemas.usuario import UsuarioCreate, UsuarioRead
from app.schemas.cargo import ComissaoModo
from app.core.enum import Gender, BankAccountType

# ===========================================================================
# SCHEMA BASE
# ===========================================================================

class FuncionarioBase(BaseModel):
    """Atributos comuns do perfil de Funcionário."""
    
    nome: str = Field(..., max_length=255, description="Nome completo.")
    telefone: Optional[str] = Field(None, max_length=20, description="Telefone para contato")
    celular: Optional[str] = Field(None, max_length=20, description="Celular para contato.")
    email: Optional[str] = Field(None, description="Email corporativo ou pessoal.")

    # Documentos e identidade
    cpf: Optional[str] = Field(None, pattern=r"^\d{11}$", description="CPF (11 dígitos numéricos). Nullable para Usuário Master.")
    rg: Optional[str] = Field(None, max_length=20, description="Registro Geral.")
    carteira_trabalho: Optional[str] = Field(None, max_length=50, description="Número da CTPS.")
    cnh: Optional[str] = Field(None, max_length=20, description="Carteira de Motorista.")
    genero: Optional[Gender] = Field(None, description="Gênero do funcionário.")
 
    # Financeiro
    banco: Optional[str] = Field(None, max_length=50, description="Nome do banco da conta")
    titular_conta: Optional[str] = Field(None, max_length=255, description="Nome do Titular da conta")
    agencia: Optional[str] = Field(None, max_length=10, description="Agencia do banco")
    conta: Optional[str] = Field(None, max_length=20, description="Numero da conta do banco") 
    tipo_conta: Optional[BankAccountType] = Field(None, description="Tipo de conta do banco")

    # Pessoal
    data_nascimento: Optional[date] = Field(None, description="Data de nascimento do funcionário.")
    mae: Optional[str] = Field(None, max_length=255, description="Nome da mãe.")
    pai: Optional[str] = Field(None, max_length=255, description="Nome do pai.")
    observacao: Optional[str] = Field(None, max_length=500)

    #Empresa
    jornada_trabalho: Optional[str] = Field(None, description="Jornada de trabalho do funcionário.")
    salario_bruto: Optional[int] = Field(None, description="Salário bruto mensal.")
    tipo_contrato: Optional[str] = Field(None, description="Tipo de contrato do funcionário.")
    data_admissao: Optional[date] = Field(None, description="Data de admissão no cargo.")

    # Comissão (override do padrão do Cargo). Vazio = herda do cargo (cascata).
    # Percentuais em BASIS POINTS (500 = 5,00%); meta em centavos.
    comissao_venda_percentual: Optional[int] = Field(None, ge=0, le=10000, description="Override: comissão sobre vendas (basis points). Vazio herda do cargo.")
    comissao_servico_percentual: Optional[int] = Field(None, ge=0, le=10000, description="Override: comissão sobre serviços/OS (basis points). Vazio herda do cargo.")
    meta_mensal: Optional[int] = Field(None, ge=0, description="Override: meta mensal (centavos). Vazio herda do cargo.")
    comissao_modo: Optional[ComissaoModo] = Field(None, description="Override: 'direto' | 'meta'. Vazio herda do cargo.")

    model_config = ConfigDict(from_attributes=True)

# ===========================================================================
# CREATE (Entrada)
# ===========================================================================

class FuncionarioCreate(FuncionarioBase):
    """Payload para criação de novo funcionário."""
    
    usuario: UsuarioCreate = Field(..., description="Dados para criar o login do funcionário.")
    cargo_id: Optional[int] = Field(None, description="ID do cargo inicial (opcional).")
    endereco: Optional[List[Endereco]] = Field(None, description="Lista de endereços residenciais.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Ricardo Oliveira Santos",
                "cpf": "12345678901",
                "email": "ricardo.santos@empresa.com.br",
                "telefone": "1133445566",
                "celular": "11988776655",
                "genero": "MASCULINO",
                "data_nascimento": "1990-05-15",
                "jornada_trabalho": "44h semanais",
                "salario_bruto": 4500,
                "tipo_contrato": "CLT",
                "data_admissao": "2024-01-10",
                "banco": "Banco do Brasil",
                "agencia": "1234",
                "conta": "56789-0",
                "tipo_conta": "CORRENTE",
                "usuario": {
                    "nome": "ricardo.santos",
                    "email": "ricardo.santos@empresa.com.br",
                    "senha": "Password@123!"
                },
                "endereco": [
                    {
                        "logradouro": "Avenida Paulista",
                        "numero": "1000",
                        "bairro": "Bela Vista",
                        "cidade": "São Paulo",
                        "estado": "SP",
                        "cep": "01310-100",
                        "complemento": "Apto 42"
                    }
                ]
            }
        }
    )

# ===========================================================================
# READ (Saída)
# ===========================================================================

class FuncionarioRead(FuncionarioBase):
    """Payload de resposta com dados persistidos."""
    
    id: int = Field(..., description="ID único do funcionário.")
    ativo: bool = Field(..., description="Status do cadastro.")
    cargo_id: Optional[int] = Field(None)

    usuario: UsuarioRead = Field(..., description="Dados do usuário de login associado.")
    endereco: Optional[List[EnderecoRead]] = Field(None, description="Endereços vinculados.")

# ===========================================================================
# UPDATE (Edição)
# ===========================================================================

class FuncionarioUpdate(BaseModel):
    """Payload para atualização parcial (PATCH behavior)."""
    
    # Dados Funcionario (Base)
    nome: Optional[str] = Field(None, max_length=255)
    telefone: Optional[str] = Field(None, max_length=20)
    celular: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None)
    
    # Documentos e Identidade
    cpf: Optional[str] = Field(None, pattern=r"^\d{11}$")
    rg: Optional[str] = Field(None, max_length=20)
    carteira_trabalho: Optional[str] = Field(None, max_length=50)
    cnh: Optional[str] = Field(None, max_length=20)
    genero: Optional[Gender] = Field(None)
 
    # Financeiro
    banco: Optional[str] = Field(None, max_length=50)
    titular_conta: Optional[str] = Field(None, max_length=255)
    agencia: Optional[str] = Field(None, max_length=10)
    conta: Optional[str] = Field(None, max_length=20) 
    tipo_conta: Optional[BankAccountType] = Field(None)

    # Pessoal
    data_nascimento: Optional[date] = Field(None)
    mae: Optional[str] = Field(None, max_length=255)
    pai: Optional[str] = Field(None, max_length=255)
    observacao: Optional[str] = Field(None, max_length=500)

    # Empresa
    jornada_trabalho: Optional[str] = Field(None)
    salario_bruto: Optional[int] = Field(None)
    tipo_contrato: Optional[str] = Field(None)
    data_admissao: Optional[date] = Field(None)
    cargo_id: Optional[int] = Field(None)

    # Comissão (override do cargo). Vazio = herda.
    comissao_venda_percentual: Optional[int] = Field(None, ge=0, le=10000)
    comissao_servico_percentual: Optional[int] = Field(None, ge=0, le=10000)
    meta_mensal: Optional[int] = Field(None, ge=0)
    comissao_modo: Optional[ComissaoModo] = Field(None)

    # Status
    ativo: Optional[bool] = Field(None)

    # Relacionamentos (Endereços)
    endereco: Optional[List[EnderecoUpdate]] = Field(
        None, 
        description="Lista de endereços. Envie ID para editar, sem ID para criar."
    )

    model_config = ConfigDict(from_attributes=True)