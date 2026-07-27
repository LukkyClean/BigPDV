import z from 'zod';

// Bandeiras de cartão aceitas (espelha o enum usado na OS).
export const CardFlagSchema = z.enum(['VISA', 'MASTERCARD', 'ELO', 'OUTROS']);
export type CardFlag = z.infer<typeof CardFlagSchema>;

// Quem arca com o juros do cartão. CLIENTE = repassado (embutido em `valor`);
// LOJA = absorvido pela loja (fora de `valor`, e não entra no total da venda).
export const JurosResponsavelSchema = z.enum(['CLIENTE', 'LOJA']);

export const PaymentSaleBaseSchema = z.object({
  forma_pagamento_id: z.number({required_error: 'Forma de pagamento é obrigatória'}),
  parcelado: z.boolean(),
  qtd_parcelas: z.number().nullable(),
  // `valor` é o que o CLIENTE paga neste método. Só inclui o juros quando repassado.
  valor: z.number({required_error: 'Valor é obrigatório'}).min(0),
  // Opcionais de propósito: `.default()` faria o tipo de entrada do Zod divergir
  // do de saída, e o `parseSchema` (ZodSchema<T>) exige que sejam iguais.
  // Ausente é lido como CLIENTE — que é o comportamento dos pagamentos antigos.
  juros_valor: z.number().min(0).optional(),
  juros_responsavel: JurosResponsavelSchema.optional(),
  // Detalhes por forma de pagamento (todos opcionais)
  bandeira_cartao: CardFlagSchema.nullable().optional(),
  vencimento: z.string().nullable().optional(),
  detalhes: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const PaymentSaleCreateSchema = PaymentSaleBaseSchema.superRefine((data, ctx) => {
  if (data.parcelado && !data.qtd_parcelas) {
    ctx.addIssue({
      code: 'custom',
      path: ['qtd_parcelas'],
      message: 'Quantidade de parcelas é obrigatória para pagamentos parcelados',
    });
  }
});

export const PaymentSaleReadSchema = PaymentSaleBaseSchema.extend({
  id: z.number(),
  data_pagamento: z.string(),
}).merge(PaymentSaleBaseSchema);

export const FinishPaymentSaleSchema = z.object({
  pagamentos: PaymentSaleCreateSchema.array(),
});

export type PaymentSaleCreate = z.infer<typeof PaymentSaleCreateSchema>;

export type FinishPaymentSale = z.infer<typeof FinishPaymentSaleSchema>;
