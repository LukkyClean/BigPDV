import { SaleSearch } from "./schemas/sale.schema"
import { OrcamentoSearch } from "./schemas/orcamento.schema"
import { PRODUTOS_KEY, CLIENTES_KEY } from "@/shared/constants/entityKeys"

export const saleKeys = {
    all: ['sales'] as const,
    lists: () => [...saleKeys.all, 'list'] as const,
    list: (filters?: SaleSearch, page: number = 1) => [...saleKeys.lists(), filters ?? {}, page] as const,
    detail: (saleId: number) => [...saleKeys.all, 'detail', saleId] as const,
    draft: (saleId: number) => [...saleKeys.all, 'draft', saleId] as const,
    status: () => [...saleKeys.all, 'status'] as const
}

export const orcamentoKeys = {
    all: ['orcamentos'] as const,
    lists: () => [...orcamentoKeys.all, 'list'] as const,
    list: (filters?: OrcamentoSearch, page: number = 1) => [...orcamentoKeys.lists(), filters ?? {}, page] as const,
    detail: (orcamentoId: number) => [...orcamentoKeys.all, 'detail', orcamentoId] as const,
    draft: (orcamentoId: number) => [...orcamentoKeys.all, 'draft', orcamentoId] as const,
    status: () => [...orcamentoKeys.all, 'status'] as const
}

// Pende do prefixo canônico 'produtos' (era 'products', ilha isolada): cadastro de
// produto e movimentação de estoque invalidam esse prefixo, então produto novo
// entra na busca da venda sem F5. O queryFn e o formato do dado seguem os de
// vendas — só a chave passou a ser vizinha das outras.
export const productKeys = {
    all: [PRODUTOS_KEY] as const,
    search: (term: string) => [...productKeys.all, 'venda-busca', term] as const,
}

// Mesmo racional de productKeys: pende do prefixo canônico, então cliente
// cadastrado em qualquer módulo entra nesta busca sem F5.
export const customerKeys = {
    all: [CLIENTES_KEY] as const,
    search: (term: string) => [...customerKeys.all, 'venda-busca', term] as const,
}

export const vendaNotaFiscalKeys = {
    detail: (vendaId: number) => ['venda-nota-fiscal', vendaId] as const,
}