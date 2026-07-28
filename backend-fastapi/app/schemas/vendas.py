from pydantic import BaseModel, Field, model_validator, ConfigDict
from app.core.enum import VendaStatus
from datetime import datetime, date
from typing import Optional, Sequence

from app.schemas.cliente import ClienteRead, ClienteSimpleRead
from app.schemas.cargo import CargoBase

from app.core.enum import TipoProdutoVenda, JurosResponsavel

# Schemas para criação de venda, produtos e pagamentos relacionados a uma venda

class ProdutoVendaCreate(BaseModel):
    tipo_produto: TipoProdutoVenda = Field(..., description="Tipo do produto, obrigatório")
    produto_id: Optional[int] = Field(None, description="ID do produto, obrigatório se não for uma descrição avulsa")
    quantidade: int = Field(0, gt=0, description="Quantidade do produto, obrigatório")
    descricao_avulsa: Optional[str] = Field(None, max_length=100, description="Descrição do produto avulso, obrigatório se não for um produto cadastrado")
    valor_unitario: Optional[int] = Field(None, ge=0, description="Valor unitário do produto, obrigatório")
    desconto: int = Field(0, ge=0, description="Desconto do produto, obrigatório")

    @model_validator(mode='after')
    def check_produto_references(self) -> 'ProdutoVendaCreate':
        if self.tipo_produto == TipoProdutoVenda.AVULSO:
            if self.produto_id is not None:
                raise ValueError("O campo 'produto_id' não deve ser fornecido quando o tipo de produto é 'AVULSO'.")
            if self.descricao_avulsa is None:
                raise ValueError("O campo 'descricao_avulsa' é obrigatório quando o tipo de produto é 'AVULSO'.")
            if self.valor_unitario is None:
                raise ValueError("O campo 'valor_unitario' é obrigatório quando o tipo de produto é 'AVULSO'.")
            subtotal = (self.quantidade or 0) * (self.valor_unitario or 0) - (self.desconto or 0)
            if subtotal < 0:
                raise ValueError("O desconto não pode ser maior que o valor total do produto.", )
            return self

        if self.produto_id is None:
            raise ValueError("O campo 'produto_id' é obrigatório quando o tipo de produto é 'CADASTRADO'.")
        if self.descricao_avulsa is not None:
            raise ValueError("O campo 'descricao_avulsa' deve ser nulo quando o tipo de produto é 'CADASTRADO'.")
        if self.valor_unitario is not None:
            raise ValueError("O campo 'valor_unitario' deve ser nulo quando o tipo de produto é 'CADASTRADO'.")    
        return self
        

class PagamentoVendaCreate(BaseModel):
    forma_pagamento_id: int = Field(..., description="ID da forma de pagamento, obrigatório")
    parcelado: bool = Field(False, description="Indica se o pagamento é parcelado")
    qtd_parcelas: Optional[int] = Field(1, gt=0, description="Quantidade de parcelas")
    valor: int = Field(..., ge=0, description="Valor pago pelo cliente neste método (centavos), obrigatório")
    juros_valor: int = Field(0, ge=0, description="Juros calculados neste pagamento (centavos)")
    juros_responsavel: JurosResponsavel = Field(
        JurosResponsavel.CLIENTE,
        description="CLIENTE: juros embutido em `valor`. LOJA: juros absorvido, fora de `valor`.",
    )
    bandeira_cartao: Optional[str] = Field(None, max_length=50, description="Bandeira do cartão (VISA, MASTERCARD, etc.)")
    vencimento: Optional[date] = Field(None, description="Data de vencimento do pagamento (ex: boletos)")
    detalhes: Optional[dict] = Field(None, description="Dados adicionais do pagamento em formato JSON (ex: banco/NSU)")

    @model_validator(mode='after')
    def check_pagamento_fields(self) -> 'PagamentoVendaCreate':
        if self.parcelado:
            if self.qtd_parcelas is None:
                raise ValueError("O campo 'qtd_parcelas' é obrigatório quando o pagamento é parcelado.")
        if not self.parcelado and self.qtd_parcelas:
            raise ValueError("O campo 'qtd_parcelas' deve ser nulo quando o pagamento não é parcelado.")
        return self

class VendaCreate(BaseModel):
    cliente_id: Optional[int] = Field(None, description="ID do cliente")
    funcionario_id: int = Field(..., description="ID do funcionário")

# Schemas para atualização de venda, produtos e pagamentos relacionados a uma venda

class ProdutoVendaUpdate(BaseModel):
    quantidade: Optional[int] = Field(None, gt=0, description="Quantidade do produto")
    descricao_avulsa: Optional[str] = Field(None, max_length=100, description="Descrição do produto avulso")
    valor_unitario: Optional[int] = Field(None, ge=0, description="Valor unitário do produto")
    desconto: Optional[int] = Field(None, ge=0, description="Desconto do produto")
    codigo_gerente: Optional[str] = Field(None, description="PIN do gerente para aprovar alteração de preço")

    @model_validator(mode='after')
    def check_produto_references(self) -> 'ProdutoVendaUpdate':
        if self.valor_unitario and self.quantidade:
            subtotal = (self.quantidade or 0) * (self.valor_unitario or 0) - (self.desconto or 0)
            if subtotal < 0:
                raise ValueError("O desconto não pode ser maior que o valor total do produto.")
        return self

class VendaUpdate(BaseModel):
    cliente_id: Optional[int] = Field(None, description="ID do cliente")
    funcionario_id: Optional[int] = Field(None, description="ID do funcionário")
    entrega: Optional[int] = Field(None, ge=0, description="Valor da entrega")
    desconto: Optional[int] = Field(None, ge=0, description="Desconto da venda")
    observacao: Optional[str] = Field(None, max_length=500, description="Observação da venda")
    observacao_interna: Optional[str] = Field(None, max_length=500, description="Observação interna (não impressa no comprovante)")
    codigo_gerente: Optional[str] = Field(None, description="PIN do gerente para aprovar desconto acima do limite")

# Schemas para leitura de venda, produtos e pagamentos relacionados a uma venda

class ProdutoVendaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID do produto na venda")
    tipo_produto: TipoProdutoVenda = Field(..., description="Tipo do produto, obrigatório")
    produto_id: Optional[int] = Field(None, description="ID do produto, obrigatório se não for uma descrição avulsa")
    sku: Optional[str] = Field(None, description="SKU do produto, preenchido automaticamente com base no tipo do produto e suas referências")
    nome: str = Field(..., description="Nome do produto, preenchido automaticamente com base no tipo do produto e suas referências")
    quantidade: int = Field(0, gt=0, description="Quantidade do produto, obrigatório")
    valor_unitario: int = Field(0, ge=0, description="Valor unitário do produto, obrigatório")
    desconto: int = Field(0, ge=0, description="Desconto do produto, obrigatório")
    subtotal: int = Field(0, ge=0, description="Subtotal do produto (quantidade * valor_unitario - desconto)")
    total: int = Field(0, ge=0, description="Total do produto (subtotal - desconto)")
    imagem_url: Optional[str] = Field(None, description="URL da imagem do produto, preenchido automaticamente com base no tipo do produto e suas referências")
    unidade_medida: Optional[str] = Field(None, description="Unidade de medida do produto (ex: UN, KG, CX)")
    estoque_disponivel: Optional[int] = Field(None, description="Estoque atual do produto no momento da consulta")

class PagamentoVendaRead(PagamentoVendaCreate):
    id: int = Field(..., description="ID do pagamento na venda")
    data_pagamento: datetime = Field(..., description="Data do pagamento no formato ISO 8601")

class FuncionarioVendaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID do funcionário")
    nome: str = Field(..., description="Nome do funcionário")
    cargo: Optional[CargoBase] = Field(None, description="Cargo do funcionário")

class VendaSimpleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID da venda")
    numero_venda: Optional[int] = Field(None, description="Número sequencial oficial (atribuído ao finalizar)")

    sessao_caixa_id: Optional[int] = Field(None, description="ID da sessão de caixa associada à venda")
    cliente_id: Optional[int] = Field(None, description="ID do cliente associado à venda")
    funcionario_id: int = Field(..., description="ID do funcionário associado à venda")

    total: int = Field(0, ge=0, description="Total da venda")

    status: VendaStatus = Field("ATIVA", description="Status da venda")
    criado_em: datetime = Field(..., description="Data de criação da venda no formato ISO 8601")
    atualizado_em: datetime = Field(..., description="Data da última atualização da venda no formato ISO 8601")

    cliente: Optional[ClienteSimpleRead] = Field(None, description="Dados do cliente associado à venda, preenchido automaticamente com base no cliente_id")
    funcionario: Optional[FuncionarioVendaRead] = Field(None, description="Dados do funcionário responsável pela venda")

class VendaRead(VendaSimpleRead):
    entrega: int = Field(0, ge=0, description="Valor da entrega")
    subtotal: int = Field(0, ge=0, description="Subtotal da venda")
    descontos: int = Field(0, ge=0, description="Desconto da venda")
    acrescimo: int = Field(0, ge=0, description="Acréscimo de juros/cartão aplicado no checkout")
    troco: int = Field(0, ge=0, description="Valor do troco a ser devolvido ao cliente")
    observacao: Optional[str] = Field(None, max_length=500, description="Observação da venda")
    observacao_interna: Optional[str] = Field(None, max_length=500, description="Observação interna (não impressa no comprovante)")
    motivo_cancelamento: Optional[str] = Field(None, max_length=500, description="Motivo do cancelamento")
    produtos: Optional[Sequence[ProdutoVendaRead]] = Field(default_factory=list, validation_alias="itens", description="Lista de produtos relacionados à venda")
    pagamentos: Optional[Sequence[PagamentoVendaRead]] = Field(default_factory=list, description="Lista de pagamentos relacionados à venda")

class VendaFinanceSummary(BaseModel):
    subtotal: int = Field(0, ge=0, description="Subtotal atualizado da venda após alteração dos produtos")
    descontos: int = Field(0, ge=0, description="Desconto atualizado da venda após alteração dos produtos")
    entrega: int = Field(0, ge=0, description="Valor da entrega atualizado da venda após alteração dos produtos")
    total: int = Field(0, ge=0, description="Total atualizado da venda após alteração dos produtos")

class VendaStatusSummary(BaseModel):
    vendas_ativas: int = Field(0, ge=0, description="Quantidade de vendas ativas")
    vendas_finalizadas: int = Field(0, ge=0, description="Quantidade de vendas finalizadas")
    vendas_canceladas: int = Field(0, ge=0, description="Quantidade de vendas canceladas")
    ticket_medio: int = Field(0, ge=0, description="Valor médio dos tickets das vendas finalizadas")

class ProdutosAlterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_adicionado: ProdutoVendaRead
    financeiro_atualizado: VendaFinanceSummary

class FinalizarVendaPayload(BaseModel):
    pagamentos: list[PagamentoVendaCreate] = Field(..., min_length=1, description="Lista de pagamentos para finalizar a venda")
    acrescimo: Optional[int] = Field(0, ge=0, description="Acréscimo total de juros/cartão a ser somado ao total da venda (centavos)")

class CancelarVendaPayload(BaseModel):
    motivo: str = Field(..., min_length=10, max_length=500, description="Motivo do cancelamento da venda (mínimo 10 caracteres)")
    codigo_gerente: Optional[str] = Field(None, description="PIN do gerente para aprovar cancelamento")

class ReabrirVendaPayload(BaseModel):
    codigo_gerente: Optional[str] = Field(None, description="PIN do gerente para aprovar reabertura")

class VendaSearchFilters(BaseModel):
    search: Optional[str] = Field(None, max_length=255, description="Termo de busca para filtrar vendas por número da venda, nome do cliente ou nome do funcionário")
    status: Optional[VendaStatus] = Field(None, description="Status para filtrar as vendas")
    funcionario_id: Optional[int] = Field(None, description="Filtrar vendas pelo funcionário responsável")

class VendaListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filters: VendaSearchFilters = Field(..., description="Filtros para pesquisa de vendas")
    vendas: Sequence[VendaSimpleRead] = Field(default_factory=list, description="Lista de vendas retornadas para os filtros aplicados")
    total: int = Field(0, ge=0, description="Total de vendas encontradas para os filtros aplicados")
    page: int = Field(1, ge=1, description="Número da página atual")
    limit: int = Field(20, ge=1, le=100, description="Número máximo de vendas retornadas por página")
    total_pages: int = Field(1, ge=1, description="Número total de páginas disponíveis para os filtros aplicados")
    links: dict = Field(..., description="Links de navegação para a próxima e anterior página, se aplicável")