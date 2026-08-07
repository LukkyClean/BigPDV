import api from '@/api/axios';

import {
  type EmployeeReadSchemaDataType,
} from '../../schemas/relationship/employee/employee.schema';

import type { CustomerUnionReadSchemaDataType } from '../../schemas/relationship/customer/customer.schema';

import {
  CustomerPaginationSchema,
  type CustomerPaginationDataType,
} from '@/modules/customers/schemas/customerQuery.schema';

import { BASE_EMPLOYEE_OS_URL, BASE_CUSTOMER_OS_URL } from '../../constants/core.constant';

export async function getEmployeesAll(): Promise<EmployeeReadSchemaDataType> {
  const { data } = await api.get<EmployeeReadSchemaDataType>(`${BASE_EMPLOYEE_OS_URL}/`);
  return data;
}

/** Teto da rota `/clientes` (`limit` tem `le=100`). Busca boa não devolve 100. */
const LIMITE_BUSCA_CLIENTE = 100;

/**
 * Busca cliente para o seletor da OS — no SERVIDOR, pelo termo digitado.
 *
 * A versão anterior pedia `/clientes/` sem `page` nem `limit` e tratava a
 * resposta como "todos os clientes". Não era: a rota é paginada e o padrão dela
 * é `limit=20` ordenado por `id DESC`, então chegavam só os 20 cadastros MAIS
 * RECENTES — e o seletor filtrava esses 20 no navegador. Cliente antigo ficava
 * impossível de achar por mais certo que se digitasse o nome, e a loja
 * descobria isso na frente do cliente.
 *
 * Buscar no servidor também herda o motor de busca de verdade (acento, ordem
 * das palavras), em vez do `includes()` que rodava aqui.
 */
export async function getCustomersBySearch(
  search: string,
): Promise<CustomerUnionReadSchemaDataType[]> {
  const termo = search.trim();
  if (!termo) return [];

  const { data } = await api.get<CustomerPaginationDataType>(
    `${BASE_CUSTOMER_OS_URL}/`,
    { params: { buscar: termo, only_active: true, limit: LIMITE_BUSCA_CLIENTE } },
  );

  const result = CustomerPaginationSchema.safeParse(data);
  if (!result.success) {
    console.warn('[getCustomersBySearch] Zod validation warning:', result.error.issues);
    return ((data as any).items ?? []) as CustomerUnionReadSchemaDataType[];
  }
  return result.data.items;
}

/**
 * Um cliente pelo id.
 *
 * Existe porque procurar por id dentro de uma lista em cache só funciona quando
 * a lista tem o cliente — e a da OS nunca teve todos. Quem chega aqui já sabe o
 * id (veio de um conflito de placa/série), então perguntar ao servidor é uma
 * requisição barata que sempre responde.
 */
export async function getCustomerByIdForOS(
  id: number,
): Promise<CustomerUnionReadSchemaDataType> {
  const { data } = await api.get<CustomerUnionReadSchemaDataType>(
    `${BASE_CUSTOMER_OS_URL}/${id}`,
  );
  return data;
}
