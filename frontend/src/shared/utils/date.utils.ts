/**
 * Datas vindas do backend.
 *
 * O backend grava tudo em UTC (`func.now()` no SQLite e `datetime.utcnow()`) e
 * serializa SEM marcador de fuso. O JavaScript, ao receber uma data-com-hora sem
 * fuso, assume que já é local — então o valor UTC aparecia cru e tudo saía 3
 * horas adiantado no Brasil: uma OS finalizada 10:38 exibia "13:38".
 *
 * Há DOIS tipos de data no sistema, e tratá-los igual quebra um dos dois:
 *
 * - **Timestamp de evento** (`data_criacao`, `data_finalizacao`, `criado_em`):
 *   momento real, gravado em UTC. Precisa converter para a hora local.
 * - **Data pura** (`data_previsao`, `proxima_revisao_data`, validade de
 *   certificado): o usuário escolheu um dia no calendário e chega como
 *   meia-noite. Converter jogaria para o dia ANTERIOR.
 *
 * Por isso as funções são separadas por intenção, e não por formato. Um mesmo
 * componente pode precisar das duas — o painel de notificações mostra
 * `criado_em` (evento) e `data_previsao` (prazo) lado a lado.
 */

/** Já traz fuso? ("...Z" ou "...+00:00"). */
const TEM_FUSO = /(?:Z|[+-]\d{2}:?\d{2})$/;
/** "2026-08-06T13:38:11" ou "2026-08-06 13:38:11" — data COM hora. */
const TIMESTAMP_SEM_FUSO = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/;
/** "2026-08-08" — data sem hora nenhuma. */
const SO_DATA = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * Interpreta um timestamp de evento do backend como UTC e devolve o instante
 * correto. Vale também para os registros antigos: nada precisa ser reconvertido
 * no banco.
 */
export function parseTimestampBackend(valor: string | Date): Date {
  if (valor instanceof Date) return valor;
  const precisaDeFuso = TIMESTAMP_SEM_FUSO.test(valor) && !TEM_FUSO.test(valor);
  return new Date(precisaDeFuso ? `${valor.replace(' ', 'T')}Z` : valor);
}

/**
 * Interpreta uma data pura como o dia que o usuário escolheu, sem conversão.
 *
 * `new Date('2026-08-08')` é armadilha: o padrão manda tratar data sem hora como
 * UTC, e no Brasil isso exibe 07/08. Aqui a data é montada no fuso local.
 */
export function parseDataPura(valor: string | Date): Date {
  if (valor instanceof Date) return valor;
  const m = SO_DATA.exec(valor);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return new Date(valor);
}

type Entrada = string | Date | null | undefined;

/** Timestamp de evento → "06/08/2026, 10:38". */
export function formatDataHora(valor: Entrada, vazio = '-'): string {
  if (!valor) return vazio;
  return parseTimestampBackend(valor).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Timestamp de evento → "06/08/2026" (o dia certo no fuso local). */
export function formatData(valor: Entrada, vazio = '-'): string {
  if (!valor) return vazio;
  return parseTimestampBackend(valor).toLocaleDateString('pt-BR');
}

/** Timestamp de evento → "10:38". */
export function formatHora(valor: Entrada, vazio = ''): string {
  if (!valor) return vazio;
  return parseTimestampBackend(valor).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Data pura (prazo, revisão, validade) → "08/08/2026", sem conversão de fuso. */
export function formatDataPura(valor: Entrada, vazio = '-'): string {
  if (!valor) return vazio;
  return parseDataPura(valor).toLocaleDateString('pt-BR');
}
