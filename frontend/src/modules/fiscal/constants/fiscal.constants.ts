import { REFETCH_DASHBOARD } from '@/core/config/queryIntervals';
import type { DocumentoFiscalFilters } from '../types/fiscal.types';

export const FISCAL_STALE_TIME = 1000 * 30;
export const FISCAL_REFETCH_INTERVAL = REFETCH_DASHBOARD;

/**
 * Timeouts de emissão — precisam ser MAIORES que o do backend.
 *
 * O `api` do axios tem timeout global de 10 s, mas o cliente HTTP que fala com
 * a SEFAZ espera até 30 s. Toda emissão lenta estourava no navegador antes de
 * a resposta chegar, e a mensagem que aparecia ("Tente novamente") mandava o
 * operador reemitir uma nota que podia já estar autorizada e com numeração
 * consumida — o caminho mais curto para duplicidade fiscal.
 *
 * Timeout numa emissão NÃO é falha: é incerteza. Ver `ehEmissaoIncerta`.
 */
export const TIMEOUT_EMISSAO = 45_000;
export const TIMEOUT_LOTE = 300_000;
export const TIMEOUT_CONSULTA = 20_000;

export const fiscalKeys = {
  /** Prefixo de todas as queries do modulo — invalida o fiscal inteiro. */
  all: ['fiscal'] as const,
  documentos: (filters?: DocumentoFiscalFilters, page?: number) =>
    ['fiscal', 'documentos', filters, page] as const,
  /**
   * Contadores. Sem `tipo` devolve o PREFIXO `['fiscal','resumo']`, e não
   * `[..., undefined]`: as mutations invalidam com `resumo()` e precisam
   * atingir também as variantes por modelo. Uma chave com `undefined` no fim
   * não é prefixo de `['fiscal','resumo','NFCE']` e deixaria os cartões
   * desatualizados depois de emitir ou cancelar.
   */
  resumo: (tipo?: string) =>
    (tipo ? ['fiscal', 'resumo', tipo] : ['fiscal', 'resumo']) as readonly unknown[],
  pendencias: () => ['fiscal', 'pendencias'] as const,
  documento: (id: number) => ['fiscal', 'documento', id] as const,
  configuracao: () => ['fiscal', 'configuracao'] as const,
  plataforma: () => ['fiscal', 'plataforma'] as const,
  historico: (id: number) => ['fiscal', 'historico', id] as const,
  verificacaoBatch: (ids: number[]) => ['fiscal', 'verificacao-batch', ...ids] as const,
};

/**
 * Cores por status do documento. `border` e usada pelo drawer de detalhes
 * (icone do cabecalho e os pontos da linha do tempo) — manter as tres chaves
 * em toda entrada nova, senao o Tailwind cai sem a classe de borda.
 */
export const STATUS_COLORS: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  PENDENTE: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
  PROCESSANDO: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
  AUTORIZADA: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200' },
  REJEITADA: { bg: 'bg-red-100', text: 'text-red-600', border: 'border-red-200' },
  CANCELADA: { bg: 'bg-zinc-100', text: 'text-zinc-500', border: 'border-zinc-200' },
  DENEGADA: { bg: 'bg-red-100', text: 'text-red-600', border: 'border-red-200' },
};

export const STATUS_FILTER_OPTIONS = [
  { value: 'PENDENTE', label: 'Pendentes' },
  { value: 'PROCESSANDO', label: 'Processando' },
  { value: 'AUTORIZADA', label: 'Autorizadas' },
  { value: 'REJEITADA', label: 'Rejeitadas' },
  { value: 'CANCELADA', label: 'Canceladas' },
  { value: 'DENEGADA', label: 'Denegadas' },
];

export const TIPO_FILTER_OPTIONS = [
  { value: 'NFE', label: 'NF-e' },
  { value: 'NFCE', label: 'NFC-e' },
  { value: 'NFSE', label: 'NFS-e' },
];

export const TIPO_LABELS: Record<string, string> = {
  NFE: 'NF-e',
  NFCE: 'NFC-e',
  NFSE: 'NFS-e',
};

export const ORIGEM_LABELS: Record<string, string> = {
  VENDA: 'Venda',
  ORDEM_SERVICO: 'OS',
};
