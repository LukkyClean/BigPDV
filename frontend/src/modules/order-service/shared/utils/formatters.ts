import type {
  OsStatusEnumDataType,
  OsPriorityEnumDataType,
  OsEquipSituacaoEnumDataType,
} from '../../ordens/schemas/enums/osEnums.schema';
import type { OsEstadoConfig } from '../../ordens/constants/ordemServico.constants';
import { OS_ESTADO_CONFIG, OS_PRIORIDADE_OPTIONS } from '../../ordens/constants/ordemServico.constants';

// Re-export shared utilities for backward compatibility
export { getClienteNome, getPaymentDisplayName, inferPaymentType, inferPermiteParcelamento } from '@/shared/utils/print.utils';

/**
 * Rótulo e cores do estado que a OS mostra ao usuário, cruzando o status do
 * fluxo com o desfecho do objeto.
 *
 * É por aqui que "Condenado" e "Sem Reparo" chegam à tela: eles são gravados em
 * `situacao_equipamento` e nunca aparecem em `status` (que fica FINALIZADA), então
 * ler só o status faria uma OS condenada se anunciar como "Finalizada".
 */
export function getEstadoOS(
  status: OsStatusEnumDataType | null | undefined,
  situacao?: OsEquipSituacaoEnumDataType | null,
): OsEstadoConfig {
  // O desfecho só substitui o rótulo de uma OS de fato encerrada. Reabrir NÃO
  // limpa `situacao_equipamento` (é o último desfecho conhecido do objeto), e sem
  // esta guarda uma OS reaberta continuaria se exibindo como "Condenado" enquanto
  // já está de volta à bancada.
  if (status === 'FINALIZADA' && situacao && situacao !== 'REPARADO') {
    return OS_ESTADO_CONFIG[situacao];
  }
  return OS_ESTADO_CONFIG[status ?? 'ABERTA'] ?? OS_ESTADO_CONFIG.ABERTA;
}

export function getPrioridadeLabel(prioridade: OsPriorityEnumDataType): string {
  const found = OS_PRIORIDADE_OPTIONS.find((p) => p.value === prioridade);
  return found?.label || prioridade;
}

export function getPrioridadeColor(prioridade: OsPriorityEnumDataType): string {
  const found = OS_PRIORIDADE_OPTIONS.find((p) => p.value === prioridade);
  return found?.color || 'gray';
}

export function formatOSNumber(numero: string): string {
  if (!numero) return '';
  const parts = numero.split('-');
  return parts.length >= 3 ? parts[2] : numero;
}

export function formatDataEntrada(data: string | Date | undefined): string {
  if (!data) return '-';
  const date = typeof data === 'string' ? new Date(data) : data;
  return date.toLocaleDateString('pt-BR');
}

export function formatDataPrevisao(data: string | Date | undefined): string {
  if (!data) return 'Não definida';
  const date = typeof data === 'string' ? new Date(data) : data;
  return date.toLocaleDateString('pt-BR');
}
