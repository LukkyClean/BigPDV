import z from 'zod';

import { ProductSaleReadSchema } from './productSale.schema';
import { PaymentSaleReadSchema } from './paymentSale.schema';
import { CustomerDiscriminatedSchema } from './customers.schema';
import { parseTimestampBackend } from '@/shared/utils/date.utils';

export const FuncionarioVendaReadSchema = z.object({
  id: z.number(),
  nome: z.string(),
  cargo: z.object({ nome: z.string() }).nullable().optional(),
});

export type FuncionarioVendaRead = z.infer<typeof FuncionarioVendaReadSchema>;

export const SaleCreateSchema = z.object({
  cliente_id: z.number().nullable().optional(),
  funcionario_id: z.number({ required_error: 'Funcionário é obrigatório' }),
});

export type SaleCreate = z.infer<typeof SaleCreateSchema>;

export const SaleUpdateSchema = SaleCreateSchema.extend({
  entrega: z
    .number()
    .min(0)
    .optional()
    .default(0)
    .transform((val) => val * 100),
  desconto: z
    .number()
    .min(0)
    .optional()
    .default(0)
    .transform((val) => val * 100),
  observacao: z.string().max(500).nullable().optional(),
  observacao_interna: z.string().max(500).nullable().optional(),
  codigo_gerente: z.string().nullable().optional(),
}).partial();

export type SaleUpdate = z.infer<typeof SaleUpdateSchema>;

export const SaleSimpleReadSchema = z.object({
  id: z.number(),
  numero_venda: z.number().nullable().optional(),

  cliente_id: z.number().nullable().optional(),
  funcionario_id: z.number(),

  total: z.number(),

  status: z.enum(['ATIVA', 'FINALIZADA', 'CANCELADA']),

  criado_em: z.string(),

  // Timestamp de evento: gravado em UTC no backend.
  atualizado_em: z.string().transform((dateTimeStamp) =>
    parseTimestampBackend(dateTimeStamp).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    }),
  ),

  /**
   * A fila do caixa. Nulo = ainda em montagem; preenchido = entregue ao caixa.
   *
   * Fica CRU, sem o `transform` do `atualizado_em`, porque a tela precisa do
   * instante para calcular há quanto tempo a venda espera — uma data formatada
   * em dd/mm/aa não serve para essa conta. É timestamp de evento: UTC no
   * backend, convertido só na exibição.
   *
   * `.optional()` cobre o backend mais antigo que o frontend: campo ausente vira
   * `undefined` em vez de reprovar a venda inteira e derrubar a lista.
   *
   * Sem `.catch()` aqui de propósito — ele tipa a ENTRADA como `unknown` e
   * contamina o `z.infer` de tudo que aninha este schema. É a mesma armadilha
   * do `z.preprocess` que já custou uma faxina de TypeScript neste repositório.
   */
  enviada_ao_caixa_em: z.string().nullable().optional(),

  cliente: CustomerDiscriminatedSchema.nullable().optional(),
  funcionario: FuncionarioVendaReadSchema.nullable().optional(),
});

export type SaleSimpleRead = z.infer<typeof SaleSimpleReadSchema>;

export const SaleReadSchema = SaleSimpleReadSchema.extend({
  entrega: z.number(),
  descontos: z.number(),
  subtotal: z.number(),
  acrescimo: z.number(),
  troco: z.number(),

  observacao: z.string().nullable().optional(),
  observacao_interna: z.string().nullable().optional(),
  motivo_cancelamento: z.string().nullable().optional(),

  produtos: z.array(ProductSaleReadSchema),
  pagamentos: z.array(PaymentSaleReadSchema),
});

export type SaleRead = z.infer<typeof SaleReadSchema>;

export const SaleSearchSchema = z.object({
  search: z.string().max(255).nullable().optional(),
  status: z.enum(['ATIVA', 'FINALIZADA', 'CANCELADA']).nullable().optional(),
  // true traz só a fila do caixa, false só as em montagem, ausente traz tudo.
  na_fila: z.boolean().nullable().optional(),
});

export type SaleSearch = z.infer<typeof SaleSearchSchema>;

export const SaleListSchema = z.object({
  filters: SaleSearchSchema,
  vendas: SaleSimpleReadSchema.array(),
  total: z.number(),
  page: z.number(),
  limit: z.number(),
  total_pages: z.number(),
  links: z.object({
    next: z.string().nullable().optional(),
    prev: z.string().nullable().optional(),
  }),
});

export type SaleList = z.infer<typeof SaleListSchema>;

export const SalesStatusSchema = z.object({
  vendas_ativas: z.number(),
  // Subconjunto das ativas, não uma quarta categoria — somar tudo daria mais
  // que o total. `.default(0)` cobre o backend mais antigo, que não manda o
  // campo, sem transformar a entrada em `unknown` como o `.catch()` faria.
  vendas_na_fila: z.number().default(0),
  vendas_finalizadas: z.number(),
  vendas_canceladas: z.number(),
  ticket_medio: z.number(),
});

export type SalesStatus = z.infer<typeof SalesStatusSchema>;

// ---------------------------------------------------------------------------
// Nota Fiscal por Venda
// ---------------------------------------------------------------------------

export const VendaNotaFiscalUpdateSchema = z.object({
  natureza_operacao: z.string().max(60).nullable().optional(),
  // 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno
  finalidade_emissao: z.number().int().min(1).max(4).nullable().optional(),
  consumidor_final: z.boolean().nullable().optional(),
  // 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domiciliar, 9=Outros
  indicador_presenca: z.number().int().refine((v) => [1, 2, 3, 4, 9].includes(v), {
    message: 'indicador_presenca deve ser 1, 2, 3, 4 ou 9',
  }).nullable().optional(),
  // CPF/CNPJ do "quer CPF na nota?" — consumidor de passagem, sem cadastro.
  // Só dígitos; o backend revalida e recusa documento com DV errado.
  documento_consumidor: z.string().max(14).nullable().optional(),
});

export type VendaNotaFiscalUpdate = z.infer<typeof VendaNotaFiscalUpdateSchema>;

export const VendaNotaFiscalReadSchema = VendaNotaFiscalUpdateSchema.extend({
  id: z.number(),
  venda_id: z.number(),
  status_nota: z.string().nullable().optional(),
  chave_acesso: z.string().nullable().optional(),
  numero_nota: z.number().nullable().optional(),
  serie: z.number().nullable().optional(),
  protocolo_autorizacao: z.string().nullable().optional(),
  data_autorizacao: z.string().nullable().optional(),
  url_danfe: z.string().nullable().optional(),
  mensagem_sefaz: z.string().nullable().optional(),
  qrcode: z.string().nullable().optional(),
  data_atualizacao: z.string(),
});

export type VendaNotaFiscalRead = z.infer<typeof VendaNotaFiscalReadSchema>;
