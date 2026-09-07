import type { AxiosError } from 'axios';

import { fiscalService } from '../services/fiscal.service';
import type { DocumentoFiscalRead } from '../types/fiscal.types';

/**
 * Timeout ou queda de rede durante uma emissão NÃO é falha — é INCERTEZA.
 *
 * A requisição pode ter chegado à SEFAZ, a nota pode ter sido autorizada e a
 * numeração pode já ter sido consumida; o que faltou foi a resposta voltar.
 * Tratar isso como erro e oferecer "tentar de novo" é o caminho mais curto
 * para emitir a mesma venda duas vezes.
 *
 * Distinguimos pelo `response`: se o servidor respondeu (mesmo 4xx/5xx), houve
 * um veredito e não há incerteza. Sem resposta, não sabemos o que aconteceu.
 */
export function ehEmissaoIncerta(erro: unknown): boolean {
  const ax = erro as AxiosError;
  return !ax?.response && (ax?.code === 'ECONNABORTED' || ax?.code === 'ERR_NETWORK');
}

/**
 * Descobre o que de fato aconteceu com a emissão de uma venda, consultando os
 * documentos já registrados. É o que se faz no lugar de retentar.
 *
 * Devolve o documento mais recente daquela venda, ou null se nenhum foi criado
 * — aí sim a emissão não chegou a acontecer e pode ser refeita com segurança.
 */
export async function resolverEmissaoIncerta(
  vendaId: number,
): Promise<DocumentoFiscalRead | null> {
  try {
    // A API não filtra por `origem_id` — só por origem, status, tipo, busca e
    // data. Como a emissão que ficou incerta acabou de acontecer, a primeira
    // página de VENDA basta, e o recorte fino fica no cliente.
    const { documentos } = await fiscalService.listarDocumentos({ origem: 'VENDA' });

    const daVenda = (documentos ?? []).filter((d) => d.origem_id === vendaId);
    if (!daVenda.length) return null;

    // O maior id é a tentativa desta emissão.
    return daVenda.reduce((mais, atual) => (atual.id > mais.id ? atual : mais));
  } catch {
    // Se nem a consulta passa, a rede ainda está ruim. O chamador trata como
    // indeterminado — que é a verdade, e é melhor que afirmar qualquer coisa.
    return null;
  }
}

/** Mensagem para o operador quando a emissão fica indeterminada. */
export const MENSAGEM_EMISSAO_INCERTA = {
  titulo: 'Não recebemos a resposta da SEFAZ',
  descricao:
    'A nota pode ter sido autorizada. Confira no Centro Fiscal antes de emitir de novo.',
} as const;
