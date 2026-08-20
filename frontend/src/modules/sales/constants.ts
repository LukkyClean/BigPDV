import type { FilterOption } from "@/shared/types/filter.types";

export const SALES_TAB_OPTIONS = [
    { id: 'vendas', label: 'Vendas' },
    { id: 'orcamentos', label: 'Orçamentos' },
];

export const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
    ATIVA: { bg: 'bg-blue-50', text: 'text-blue-700' },
    FINALIZADA: { bg: 'bg-green-50', text: 'text-green-700' },
    CANCELADA: { bg: 'bg-red-50', text: 'text-red-700' },
};

export const SALE_FILTERS: Record<string, FilterOption> = {
    ATIVA: { label: 'Ativa', class: 'bg-blue-100 text-blue-800', color: 'bg-blue-500' },
    FINALIZADA: { label: 'Finalizada', class: 'bg-green-100 text-green-800', color: 'bg-green-500' },
    CANCELADA: { label: 'Cancelada', class: 'bg-red-100 text-red-800', color: 'bg-red-500' },
};

export const SALE_FILTER_CONFIG: Record<string, FilterOption> = {
    ATIVA: { label: 'Ativa', class: 'bg-blue-50 text-blue-700', color: 'bg-blue-500' },
    FINALIZADA: { label: 'Finalizada', class: 'bg-green-50 text-green-700', color: 'bg-green-500' },
    CANCELADA: { label: 'Cancelada', class: 'bg-red-50 text-red-700', color: 'bg-red-500' },
};

export const ORCAMENTO_FILTER_CONFIG: Record<string, FilterOption> = {
    ATIVO: { label: 'Ativo', class: 'bg-blue-50 text-blue-700', color: 'bg-blue-500' },
    CONVERTIDO: { label: 'Convertido', class: 'bg-green-50 text-green-700', color: 'bg-green-500' },
};

export interface ShortcutItem {
    keys: string;
    description: string;
}

/**
 * A lista que o operador le no botao de teclado da venda.
 *
 * Ela e a UNICA documentacao do caminho de teclado, entao um atalho descrito
 * errado custa mais caro que um atalho que falta: o operador tenta, nao
 * acontece o que ele leu, e para de confiar na lista inteira.
 *
 * Ordem = ordem do fluxo, do produto ate o cupom. Onde a tecla so age em OUTRA
 * tela, a descricao diz qual — a lista abre dentro da venda, e sem isso o
 * `F6` parece quebrado (ele so tem efeito com o pagamento aberto).
 */
export const SALE_SHORTCUTS: ShortcutItem[] = [
    { keys: 'Enter', description: 'Adicionar o produto destacado' },
    { keys: '↑+↓', description: 'Escolher na lista de produtos' },
    // O ciclo do Tab é uma regra só, com três paradas fixas — descrever cada
    // parada numa linha faria parecer três atalhos diferentes.
    { keys: 'Tab', description: 'Quantidade do item → Finalizar → busca' },
    { keys: 'Ctrl+F', description: 'Voltar para a busca de produto' },
    // O nome e o do BOTAO e o do titulo da modal ("Adicionar Produto"); o que
    // vem entre parenteses e o motivo de ela existir, ja que a busca rapida da
    // venda sempre soma 1. Descrever so o motivo deixava a tecla sem dono: a
    // palavra que o operador ve na tela nao aparecia na lista.
    { keys: 'F3', description: 'Adicionar Produto (quantidade e desconto)' },
    { keys: 'F4', description: 'Produto avulso' },
    { keys: 'Ctrl+D', description: 'Focar desconto' },
    { keys: 'Ctrl+E', description: 'Focar entrega' },
    // NAO finaliza: abre a tela de pagamento. Quem finaliza e o Enter no botao
    // Finalizar Venda, ja com o troco na tela.
    { keys: 'Ctrl+Enter', description: 'Ir para o pagamento' },
    { keys: '←+↑+↓+→', description: 'Pagamento: escolher a forma' },
    { keys: 'F6', description: 'Pagamento: focar as formas' },
    { keys: 'Ctrl+Backspace', description: 'Descartar a venda' },
    { keys: 'Esc', description: 'Fechar a tela atual' },
    // Vive na LISTA de vendas (`SalesView`), nao aqui dentro: com a venda
    // aberta o F2 e inerte de proposito.
    { keys: 'F2', description: 'Nova venda (na lista de vendas)' },
];

export const PRODUCT_TYPES = [
    {value: 'CADASTRADO', label: 'Cadastrado'},
    {value: 'AVULSO', label: 'Avulso'},
] as const;

// --- Orcamento ---

export const ORCAMENTO_SHORTCUTS: ShortcutItem[] = [
    { keys: 'F2', description: 'Novo orçamento' },
    { keys: 'Ctrl+E', description: 'Focar entrega' },
    { keys: 'Ctrl+D', description: 'Focar desconto' },
    { keys: 'F4', description: 'Produto avulso' },
    { keys: 'Ctrl+F', description: 'Buscar produto' },
    { keys: 'Ctrl+Enter', description: 'Converter em venda' },
    { keys: 'Esc', description: 'Fechar modal atual' },
];

export const PAYMENT_METHODS = [
    {value: 'DINHEIRO', label: 'Dinheiro'},
    {value: 'CARTAO_CREDITO', label: 'Cartão de Crédito'},
    {value: 'CARTAO_DEBITO', label: 'Cartão de Débito'},
    {value: 'PIX', label: 'Pix'},
    {value: 'BOLETO', label: 'Boleto'},
] as const;