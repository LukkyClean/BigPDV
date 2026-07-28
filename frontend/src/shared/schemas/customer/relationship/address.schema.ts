import z from "zod";

export const AddressReadSchema = z.object({
    logradouro: z.string().max(255, 'Logradouro deve ter no máximo 255 caracteres'),
    numero: z.string().max(20, 'Número deve ter no máximo 255 caracteres').optional().nullable(),
    bairro: z.string().max(100, 'Bairro deve ter no máximo 255 caracteres'),
    cidade: z.string().max(100, 'Cidade deve ter no máximo 255 caracteres'),
    estado: z.string().max(2, 'Estado deve ter no máximo 255 caracteres'),
    cep: z.string().max(10, 'CEP deve ter no máximo 10 caracteres').optional().nullable(),
    complemento: z.string().max(100, 'Complemento deve ter no máximo 255 caracteres').optional().nullable()
})