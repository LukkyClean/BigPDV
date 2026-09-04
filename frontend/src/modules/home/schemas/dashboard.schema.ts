import { z } from 'zod';

// ===========================================================================
// Stats Cards
// ===========================================================================

export const DashboardStatsSchema = z.object({
  faturamento_total: z.number(),
  faturamento_total_variacao: z.number(),
  vendas_total: z.number(),
  vendas_total_variacao: z.number(),

  // OPCIONAL de proposito: backend mais antigo que o frontend nao devolve o
  // campo, e um `.default(0)` faria a tela afirmar "0 vendas" — mentira pior
  // que a informacao que faltava. Ausente, o card volta a mostrar o valor.
  vendas_count: z.number().optional(),
  vendas_count_variacao: z.number().optional(),
  os_total: z.number(),
  os_total_variacao: z.number(),
  os_count: z.number(),
  os_count_variacao: z.number(),
  novos_clientes: z.number(),
  novos_clientes_variacao: z.number(),
  ticket_medio: z.number(),
  ticket_medio_variacao: z.number(),
});

export type DashboardStatsData = z.infer<typeof DashboardStatsSchema>;

// ===========================================================================
// Tendência — série de faturamento por dia (gráfico)
// ===========================================================================

export const TendenciaDiaItemSchema = z.object({
  dia: z.string(),
  total_vendas: z.number(),
  total_os: z.number(),
  total_geral: z.number(),
});

export type TendenciaDiaItemData = z.infer<typeof TendenciaDiaItemSchema>;

export const TendenciaResponseSchema = z.object({
  items: z.array(TendenciaDiaItemSchema),
});

export type TendenciaResponseData = z.infer<typeof TendenciaResponseSchema>;

// ===========================================================================
// OS Vencendo
// ===========================================================================

export const OSVencendoItemSchema = z.object({
  numero_os: z.string(),
  cliente_nome: z.string(),
  defeito_relatado: z.string(),
  data_previsao: z.string(),
  urgencia: z.enum(['vermelho', 'amarelo', 'verde']),
});

export type OSVencendoItemData = z.infer<typeof OSVencendoItemSchema>;

export const OSVencendoResponseSchema = z.object({
  items: z.array(OSVencendoItemSchema),
});

export type OSVencendoResponseData = z.infer<typeof OSVencendoResponseSchema>;

// ===========================================================================
// Estoque Baixo
// ===========================================================================

export const EstoqueBaixoItemSchema = z.object({
  produto_id: z.number(),
  nome: z.string(),
  quantidade: z.number(),
  quantidade_minima: z.number().nullable(),
  status: z.enum(['zerado', 'baixo']),
});

export type EstoqueBaixoItemData = z.infer<typeof EstoqueBaixoItemSchema>;

export const EstoqueBaixoResponseSchema = z.object({
  items: z.array(EstoqueBaixoItemSchema),
});

export type EstoqueBaixoResponseData = z.infer<typeof EstoqueBaixoResponseSchema>;

// ===========================================================================
// Ultimas Vendas
// ===========================================================================

export const UltimaVendaItemSchema = z.object({
  id: z.number(),
  cliente_nome: z.string().nullable(),
  total: z.number(),
  status: z.string(),
  criado_em: z.string(),
});

export type UltimaVendaItemData = z.infer<typeof UltimaVendaItemSchema>;

export const UltimasVendasResponseSchema = z.object({
  items: z.array(UltimaVendaItemSchema),
});

export type UltimasVendasResponseData = z.infer<typeof UltimasVendasResponseSchema>;

// ===========================================================================
// Meu Resumo (Dashboard do Funcionário)
// ===========================================================================

export const MeuResumoStatsSchema = z.object({
  meu_faturamento: z.number(),
  minhas_vendas_valor: z.number(),
  minhas_vendas_count: z.number(),
  minhas_os_valor: z.number(),
  minhas_os_abertas: z.number(),
  minhas_os_concluidas: z.number(),
});

export type MeuResumoStatsData = z.infer<typeof MeuResumoStatsSchema>;

// ===========================================================================
// Minha Fila
// ===========================================================================

export const MinhaFilaItemSchema = z.object({
  numero_os: z.string(),
  cliente_nome: z.string(),
  defeito_relatado: z.string(),
  prioridade: z.string(),
  status: z.string(),
  data_previsao: z.string().nullable(),
});

export type MinhaFilaItemData = z.infer<typeof MinhaFilaItemSchema>;

export const MinhaFilaResponseSchema = z.object({
  items: z.array(MinhaFilaItemSchema),
});

export type MinhaFilaResponseData = z.infer<typeof MinhaFilaResponseSchema>;

// ===========================================================================
// OS Atrasadas
// ===========================================================================

export const OSAtrasadaItemSchema = z.object({
  numero_os: z.string(),
  cliente_nome: z.string(),
  defeito_relatado: z.string(),
  data_previsao: z.string(),
  dias_atraso: z.number(),
});

export type OSAtrasadaItemData = z.infer<typeof OSAtrasadaItemSchema>;

export const OSAtrasadaResponseSchema = z.object({
  items: z.array(OSAtrasadaItemSchema),
  total: z.number(),
});

export type OSAtrasadaResponseData = z.infer<typeof OSAtrasadaResponseSchema>;

// ===========================================================================
// OS Aguardando Retirada
// ===========================================================================

export const OSAguardandoRetiradaItemSchema = z.object({
  numero_os: z.string(),
  cliente_nome: z.string(),
  equipamento: z.string(),
  data_finalizacao: z.string().nullable(),
});

export type OSAguardandoRetiradaItemData = z.infer<typeof OSAguardandoRetiradaItemSchema>;

export const OSAguardandoRetiradaResponseSchema = z.object({
  items: z.array(OSAguardandoRetiradaItemSchema),
});

export type OSAguardandoRetiradaResponseData = z.infer<typeof OSAguardandoRetiradaResponseSchema>;

// ===========================================================================
// Atividade de Hoje
// ===========================================================================

export const AtividadeItemSchema = z.object({
  tipo: z.enum(['venda', 'os']),
  referencia: z.string(),
  cliente_nome: z.string().nullable(),
  valor: z.number(),
  status: z.string(),
  horario: z.string(),
});

export type AtividadeItemData = z.infer<typeof AtividadeItemSchema>;

export const AtividadeHojeResponseSchema = z.object({
  items: z.array(AtividadeItemSchema),
});

export type AtividadeHojeResponseData = z.infer<typeof AtividadeHojeResponseSchema>;

// ===========================================================================
// Master — Ranking de Funcionários
// ===========================================================================

export const RankingFuncionarioItemSchema = z.object({
  posicao: z.number(),
  id: z.number(),
  nome: z.string(),
  total_vendas_valor: z.number(),
  total_os_valor: z.number(),
  total_geral: z.number(),
  qtd_vendas: z.number(),
  qtd_os_fechadas: z.number(),
});

export type RankingFuncionarioItemData = z.infer<typeof RankingFuncionarioItemSchema>;

export const RankingFuncionariosResponseSchema = z.object({
  items: z.array(RankingFuncionarioItemSchema),
});

export type RankingFuncionariosResponseData = z.infer<typeof RankingFuncionariosResponseSchema>;

// ===========================================================================
// Master — OS por Status
// ===========================================================================

export const OSPorStatusItemSchema = z.object({
  status: z.string(),
  status_label: z.string(),
  count: z.number(),
});

export type OSPorStatusItemData = z.infer<typeof OSPorStatusItemSchema>;

export const OSPorStatusResponseSchema = z.object({
  items: z.array(OSPorStatusItemSchema),
  total_ativas: z.number(),
});

export type OSPorStatusResponseData = z.infer<typeof OSPorStatusResponseSchema>;

// ===========================================================================
// Master — Formas de Pagamento
// ===========================================================================

export const FormaPagamentoItemSchema = z.object({
  nome: z.string(),
  valor_total: z.number(),
});

export type FormaPagamentoItemData = z.infer<typeof FormaPagamentoItemSchema>;

export const FormasPagamentoResponseSchema = z.object({
  items: z.array(FormaPagamentoItemSchema),
  total: z.number(),
});

export type FormasPagamentoResponseData = z.infer<typeof FormasPagamentoResponseSchema>;

// ===========================================================================
// Master — OS Atrasadas da Empresa
// ===========================================================================

export const OSAtrasadaEmpresaItemSchema = z.object({
  numero_os: z.string(),
  cliente_nome: z.string(),
  funcionario_nome: z.string().nullable(),
  defeito_relatado: z.string(),
  data_previsao: z.string(),
  dias_atraso: z.number(),
});

export type OSAtrasadaEmpresaItemData = z.infer<typeof OSAtrasadaEmpresaItemSchema>;

export const OSAtrasadaEmpresaResponseSchema = z.object({
  items: z.array(OSAtrasadaEmpresaItemSchema),
  total: z.number(),
});

export type OSAtrasadaEmpresaResponseData = z.infer<typeof OSAtrasadaEmpresaResponseSchema>;
