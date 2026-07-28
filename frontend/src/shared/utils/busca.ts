/**
 * @fileoverview Busca textual "inteligente" no cliente
 * @description Espelho de `backend-fastapi/app/core/busca.py`.
 *
 * Algumas telas refiltram no navegador uma lista que o backend já filtrou
 * (a de Produtos é a principal). Se as duas pontas usarem regras diferentes,
 * o filtro local descarta em silêncio o que o servidor achou — foi exatamente
 * o que acontecia com o `startsWith` daqui contra o LIKE de lá.
 *
 * As regras precisam continuar iguais nos dois lados:
 *   - minúsculo, sem acento, pontuação virando espaço
 *   - todas as palavras digitadas precisam aparecer, em qualquer ordem,
 *     cada uma em qualquer um dos campos
 *   - o termo todo colado também vale, para documentos e códigos digitados
 *     com pontuação
 *
 * O que NÃO está aqui é a tolerância a erro de digitação: ela só existe no
 * backend, como resgate para quando a busca não devolveu nada. Replicá-la
 * aqui faria o filtro local descartar justamente esse resgate.
 */

/** Teto de palavras consideradas (mesmo valor do backend). */
const MAXIMO_TERMOS = 8;

const NAO_ALFANUMERICO = /[^0-9a-z]+/g;
/** Marcas de acento que o NFKD separa da letra base ("á" → "a" + acento). */
const MARCAS_DE_ACENTO = /[̀-ͯ]/g;

/**
 * Reduz o texto à forma comparável: "Tinta Azul-Metálica" → "tinta azul metalica".
 */
export function normalizarBusca(texto: string | null | undefined): string {
  if (!texto) return '';

  return String(texto)
    .normalize('NFKD')
    .replace(MARCAS_DE_ACENTO, '')
    .toLowerCase()
    .replace(NAO_ALFANUMERICO, ' ')
    .trim();
}

/** Como `normalizarBusca`, mas sem espaço algum — para documentos e códigos. */
export function compactarBusca(texto: string | null | undefined): string {
  return normalizarBusca(texto).replace(/ /g, '');
}

/** Quebra o que foi digitado nas palavras que serão exigidas, sem repetir. */
export function extrairTermos(termo: string | null | undefined): string[] {
  const normalizado = normalizarBusca(termo);
  if (!normalizado) return [];

  return [...new Set(normalizado.split(' '))].slice(0, MAXIMO_TERMOS);
}

/**
 * Decide se um registro atende ao termo digitado.
 *
 * @param termo  O que o usuário escreveu.
 * @param campos Os textos do registro que valem a busca (nome, código, ...).
 * @returns true também quando o termo está vazio — sem busca, nada é filtrado.
 */
export function correspondeBusca(
  termo: string | null | undefined,
  campos: (string | null | undefined)[],
): boolean {
  const termos = extrairTermos(termo);
  if (termos.length === 0) return true;

  const normalizados = campos.map(normalizarBusca).filter(Boolean);
  if (normalizados.length === 0) return false;

  const todasAsPalavras = termos.every((palavra) =>
    normalizados.some((campo) => campo.includes(palavra)),
  );
  if (todasAsPalavras) return true;

  if (termos.length > 1) {
    const colado = termos.join('');
    return campos.map(compactarBusca).some((campo) => campo.includes(colado));
  }

  return false;
}
