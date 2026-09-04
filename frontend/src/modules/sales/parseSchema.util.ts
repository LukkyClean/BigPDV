import { ZodType, ZodTypeDef } from 'zod';

/**
 * Valida a resposta da API contra o schema, ou explode com contexto no console.
 *
 * A assinatura separa ENTRADA de SAÍDA (`ZodType<Saida, _, Entrada>`) em vez do
 * antigo `ZodSchema<T>`, que amarrava as duas ao mesmo tipo. Amarradas, nenhum
 * campo do módulo podia usar `.default()` ou `.transform()` — e é justamente
 * `.default()` que permite tolerar um backend mais velho que o frontend, que
 * neste projeto acontece toda vez que alguém esquece de reiniciar o servidor.
 *
 * A mudança é só de tipo: mais permissiva, sem efeito em runtime. Todo schema
 * que compilava antes continua compilando.
 */
export function parseSchema<Saida, Entrada = Saida>(
  schema: ZodType<Saida, ZodTypeDef, Entrada>,
  data: unknown,
  context?: string,
): Saida {
  const result = schema.safeParse(data);

  if (!result.success) {
    console.error(
      `[Schema Validation Error] Context: ${context ?? 'Unknown'}`,
      result.error.flatten(),
    );

    throw new Error(`Invalid API response schema${context ? ` in ${context}` : ''}`);
  }

  return result.data;
}
