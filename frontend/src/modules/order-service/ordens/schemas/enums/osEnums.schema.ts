import z from 'zod';

export const OsStatusEnum = z.enum([
  'ABERTA',
  'EM_ANDAMENTO',
  'AGUARDANDO_PECAS',
  'AGUARDANDO_APROVACAO',
  'AGUARDANDO_RETIRADA',
  'FINALIZADA',
  'CANCELADA',
]);

export const OsPriorityEnum = z.enum(['BAIXA', 'NORMAL', 'ALTA', 'URGENTE']);

export const OsItemTypeEnum = z.enum(['PRODUTO', 'SERVICO']);

export const OsEquipTypeEnum = z.enum([
  'COMPUTADOR',
  'NOTEBOOK',
  'CELULAR',
  'TABLET',
  'IMPRESSORA',
  'MONITOR',
  'PRINTER',
  'SCANNER',
  'OUTROS',
]);

export const OsItemMeasureEnum = z.enum([
  'UN',
  'KG',
  'G',
  'L',
  'ML',
  'M',
  'CM',
  'M2',
  'M3',
  'H',
  'D',
  'MES',
  'OUTROS',
]);

export const OsCardsFlagEnum = z.enum([
  'MASTERCARD',
  'VISA',
  'ELO',
  'OUTROS',
])

export const OsEquipSituacaoEnum = z.enum([
  'REPARADO',
  'SEM_REPARO',
  'CONDENADO',
])

// --- Segmento oficina: check-in do veículo ---
export const OsCombustivelNivelEnum = z.enum([
  'VAZIO',
  '1/4',
  '1/2',
  '3/4',
  'CHEIO',
])

export const OsCombustivelTipoEnum = z.enum([
  'ALCOOL',
  'GASOLINA',
  'DIESEL',
])

export const OsEstadoConservacaoEnum = z.enum([
  'BOM',
  'REGULAR',
  'RUIM',
])

// --- Aprovação por item (fluxo de orçamento) ---
export const OsItemAprovacaoEnum = z.enum([
  'PENDENTE',
  'APROVADO',
  'REPROVADO',
])

export type OsStatusEnumDataType = z.infer<typeof OsStatusEnum>
export type OsPriorityEnumDataType = z.infer<typeof OsPriorityEnum>
export type OsItemTypeEnumDataType = z.infer<typeof OsItemTypeEnum>
export type OsEquipTypeEnumDataType = z.infer<typeof OsEquipTypeEnum>
export type OsItemMeasureEnumDataType = z.infer<typeof OsItemMeasureEnum>
export type OsCardsFlagEnumDataType = z.infer<typeof OsCardsFlagEnum>
export type OsEquipSituacaoEnumDataType = z.infer<typeof OsEquipSituacaoEnum>
export type OsCombustivelNivelEnumDataType = z.infer<typeof OsCombustivelNivelEnum>
export type OsCombustivelTipoEnumDataType = z.infer<typeof OsCombustivelTipoEnum>
export type OsEstadoConservacaoEnumDataType = z.infer<typeof OsEstadoConservacaoEnum>
export type OsItemAprovacaoEnumDataType = z.infer<typeof OsItemAprovacaoEnum>
