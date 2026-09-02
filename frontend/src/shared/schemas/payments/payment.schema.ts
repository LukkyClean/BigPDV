import z from "zod";

export const PaymentFormCreateSchema = z.object({
    nome: z.string().min(2, 'O nome deve ter no mínimo 2 caracteres').max(50, 'O nome deve ter no máximo 50 caracteres'),
    ativo: z.boolean(),
})

export const PaymentFormReadSchema = z.object({
    ...PaymentFormCreateSchema.shape,
    id: z.number().int().positive(),
    tipo: z.string().optional(),
    permite_parcelamento: z.boolean().optional(),
    /**
     * Dias ate o dinheiro DESTA forma cair na conta.
     *
     * Zero (o padrao) e o comportamento de sempre: entra na hora. Com prazo, a
     * venda vira conta a receber com vencimento em D+n e entra sozinha naquele
     * dia -- e o Fluxo de Caixa para de mostrar na conta um dinheiro que ainda
     * esta na maquininha.
     *
     * `.catch()` e nao `.optional()`: um backend mais antigo que este frontend
     * nao manda o campo, e a lista de formas de pagamento aparece na
     * finalizacao de toda venda. Derrubar essa lista por causa disto seria
     * trocar um numero errado por uma tela que nao abre.
     */
    dias_para_receber: z.number().int().nonnegative().catch(0),
    conta_bancaria_id: z.number().int().positive().nullable().catch(null),
})

export type PaymentFormReadDataType = z.infer<typeof PaymentFormReadSchema>

export const PaymentFormUpdateSchema = z.object({
    nome: z.string().min(2, 'O nome deve ter no mínimo 2 caracteres').max(50, 'O nome deve ter no máximo 50 caracteres').optional(),
    ativo: z.boolean().optional(),
    dias_para_receber: z.number().int().min(0).max(90).optional(),
    // Zero limpa a escolha e volta para a conta principal. `undefined` ja quer
    // dizer "nao mexe" num PATCH parcial, entao sobrou o zero para desfazer.
    conta_bancaria_id: z.number().int().nonnegative().nullable().optional(),
})

export type PaymentFormUpdateDataType = z.infer<typeof PaymentFormUpdateSchema>

