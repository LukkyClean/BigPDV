import z from 'zod';

export const ProductSaleBaseSchema = z.object({
  tipo_produto: z.enum(['CADASTRADO', 'AVULSO']),
  produto_id: z.number().nullable().optional(),
  descricao_avulsa: z.string().max(100).optional(),
  // Quanto a loja PAGOU por unidade. Só para item AVULSO — o cadastrado tem o
  // custo no livro de estoque. Campo INTERNO: nenhum template de impressão o
  // exibe, por decisão explícita.
  custo_unitario: z.number().min(0).nullable().optional(),
  quantidade: z.number({ required_error: 'Quantidade é obrigatória' }).min(1),
  valor_unitario: z
    .number()
    .min(0)
    .optional()
    .transform((val) => (!!val ? 0 : val)),
  desconto: z.number().nullable().optional(),
});

export const ProductSaleCreateSchema = ProductSaleBaseSchema.superRefine((data, ctx) => {
  if (data.tipo_produto === 'AVULSO') {
    if (!data.descricao_avulsa) {
      ctx.addIssue({
        code: 'custom',
        path: ['descricao_avulsa'],
        message: 'Descrição avulsa é obrigatória para produtos avulsos',
      });
    }
    if (!data.valor_unitario || data.valor_unitario <= 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['valor_unitario'],
        message: 'Valor unitário é obrigatório para produtos avulsos',
      });
    }
  }

  if (data.desconto) {
    if (data.desconto > (data.valor_unitario || 0) * data.quantidade) {
      ctx.addIssue({
        code: 'custom',
        path: ['desconto'],
        message: 'Desconto não pode ser maior que o subtotal do item',
      });
    }
  }
});

export type ProductSaleCreate = z.infer<typeof ProductSaleCreateSchema>;

export const ProductSaleUpdateSchema = ProductSaleBaseSchema
  .omit({
    tipo_produto: true,
    produto_id: true,
  })
  .partial()
  .refine(
    (data) => {
      return (data.desconto || 0) <= (data.valor_unitario || 0) * (data.quantidade || 0);
    },
    {
      message: 'O desconto não pode ser maior que o subtotal',
      path: ['desconto'],
    },
  );

export type ProductSaleUpdate = z.infer<typeof ProductSaleUpdateSchema> & { codigo_gerente?: string };

export const ProductSaleReadSchema = ProductSaleBaseSchema.extend({
  id: z.number(),
  sku: z.string().nullable().optional(),
  nome: z.string(),
  subtotal: z.number().min(0),
  total: z.number().min(0),
  imagem_url: z.string().nullable().optional(),
  unidade_medida: z.string().nullable().optional(),
  estoque_disponivel: z.number().nullable().optional(),
  valor_unitario: z.number().transform((val) => (!val ? 0 : val)),
  desconto: z.number().transform((val) => (!val ? 0 : val)),
}).omit({ descricao_avulsa: true });

export type ProductSaleRead = z.infer<typeof ProductSaleReadSchema>;

export const SaleFinanceSummarySchema = z.object({
  subtotal: z.number(),
  descontos: z.number(),
  entrega: z.number(),
  total: z.number(),
});

export const ProductAlterationSchema = z.object({
  produto_adicionado: ProductSaleReadSchema,
  financeiro_atualizado: SaleFinanceSummarySchema,
});

export type ProductAlteration = z.infer<typeof ProductAlterationSchema>;

export const ProductSaleListItemSchema = z
  .object({
    id: z.number(),
    nome: z.string(),
    sku: z.string().nullable().optional(),
    preco: z.number(),
    estoque: z.number(),
    quantidade_minima: z.number().nullable().optional(),
    imagem_url: z.string().nullable().optional(),
  })
  .array();

export type ProductSaleListItem = z.infer<typeof ProductSaleListItemSchema>;

export const ItemSaleFormSchema = z.object({
  descricao: z.string().min(1, 'Informe a descrição do produto'),
  valor_unitario: z.number().min(0.01, 'Informe um valor unitário válido'),
  quantidade: z.number().min(1, 'A quantidade deve ser pelo menos 1'),
  desconto: z.number().min(0).default(0),
  // Custo interno do avulso (em reais no form, centavos no envio). Opcional:
  // deixar zerado só significa "não sei/não quero declarar", e aí o item entra
  // no relatório sem custo.
  custo: z.number().min(0).default(0),
}).refine((data) => {
  return data.desconto <= data.valor_unitario * data.quantidade;
}, {
  path: ['desconto'],
  message: 'O desconto não pode ser maior que o subtotal',
})

export type ItemSaleForm = z.infer<typeof ItemSaleFormSchema>;