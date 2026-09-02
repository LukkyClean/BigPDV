import api from '@/api/axios';

import {
  PaymentFormReadSchema,
  type PaymentFormReadDataType,
  type PaymentFormUpdateDataType,
} from '@/shared/schemas/payments/payment.schema';

const BASE_URL = '/formas-pagamento';

export async function getPaymentMethodsAll(): Promise<PaymentFormReadDataType[]> {
  const { data } = await api.get<PaymentFormReadDataType[]>(`${BASE_URL}/`);
  const result = PaymentFormReadSchema.array().safeParse(data);
  if (!result.success) {
    console.warn('[getPaymentMethodsAll] Zod validation warning:', result.error.issues);
    return data as PaymentFormReadDataType[];
  }
  return result.data;
}

/**
 * Altera uma forma de pagamento.
 *
 * PUT e nao PATCH: e o verbo que a rota expoe, ainda que o corpo seja parcial.
 * Ela respondeu 500 desde sempre ate 02/09/2026 (passava o `db` duas vezes para
 * o servico) e ninguem viu, porque nao havia tela nenhuma chamando isto.
 */
export async function updatePaymentMethod(
  id: number,
  dados: PaymentFormUpdateDataType,
): Promise<PaymentFormReadDataType> {
  const { data } = await api.put<PaymentFormReadDataType>(`${BASE_URL}/${id}`, dados);
  const result = PaymentFormReadSchema.safeParse(data);
  if (!result.success) {
    console.warn('[updatePaymentMethod] Zod validation warning:', result.error.issues);
    return data as PaymentFormReadDataType;
  }
  return result.data;
}
