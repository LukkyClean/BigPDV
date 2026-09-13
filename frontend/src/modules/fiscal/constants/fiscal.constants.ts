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
  /** Mapa de campos do cadastro de produto — muda só com o regime da empresa. */
  camposProduto: () => ['fiscal', 'campos', 'produto'] as const,
  /** Tributação padrão da loja — muda a nota de todo produto que herda dela. */
  tributacaoPadrao: () => ['fiscal', 'tributacao-padrao'] as const,
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
  // Transmitida, desfecho desconhecido. Nao e vermelho de proposito: nao houve
  // recusa nenhuma, e pintar de vermelho convidaria a reemitir — que e
  // exatamente o que produz nota duplicada.
  INDETERMINADA: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200' },
  // Nunca chegou na SEFAZ. Cinza, e nao vermelho, porque nao ha rejeicao:
  // separar as duas na cor e metade do motivo de este status existir.
  NAO_TRANSMITIDA: { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200' },
};

/**
 * Rotulo humano por status.
 *
 * O badge mostrava `doc.status` cru quando o status nao estava no mapa de
 * filtros — entao INDETERMINADA ja aparecia assim, em caixa alta, e
 * NAO_TRANSMITIDA apareceria com o underline no meio.
 */
export const STATUS_LABELS: Record<string, string> = {
  PENDENTE: 'Pendente',
  PROCESSANDO: 'Processando',
  AUTORIZADA: 'Autorizada',
  REJEITADA: 'Rejeitada',
  CANCELADA: 'Cancelada',
  DENEGADA: 'Denegada',
  INDETERMINADA: 'Sem retorno',
  NAO_TRANSMITIDA: 'Nao transmitida',
};

export const STATUS_FILTER_OPTIONS = [
  { value: 'PENDENTE', label: 'Pendentes' },
  { value: 'PROCESSANDO', label: 'Processando' },
  { value: 'AUTORIZADA', label: 'Autorizadas' },
  { value: 'REJEITADA', label: 'Rejeitadas' },
  { value: 'CANCELADA', label: 'Canceladas' },
  { value: 'DENEGADA', label: 'Denegadas' },
  // Os dois que faltavam, e que sao justamente os que respondem "quais
  // chegaram na SEFAZ?" — a pergunta que uma lista so de "rejeitadas" nao
  // conseguia responder.
  { value: 'INDETERMINADA', label: 'Sem retorno' },
  { value: 'NAO_TRANSMITIDA', label: 'Nao transmitidas' },
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
