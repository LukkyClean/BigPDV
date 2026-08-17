import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';

export const CST_ICMS_OPTIONS: SelectOption[] = [
  { value: '00', label: '00 - Tributada integralmente' },
  { value: '10', label: '10 - Tributada com cobrança de ICMS por ST' },
  { value: '20', label: '20 - Com redução de base de cálculo' },
  { value: '30', label: '30 - Isenta/não tributada com cobrança de ICMS por ST' },
  { value: '40', label: '40 - Isenta' },
  { value: '41', label: '41 - Não tributada' },
  { value: '50', label: '50 - Suspensão' },
  { value: '51', label: '51 - Diferimento' },
  { value: '60', label: '60 - ICMS cobrado anteriormente por ST' },
  { value: '70', label: '70 - Com redução da BC e cobrança do ICMS por ST' },
  { value: '90', label: '90 - Outros' },
];

export const CSOSN_OPTIONS: SelectOption[] = [
  { value: '101', label: '101 - Tributada com permissão de crédito' },
  { value: '102', label: '102 - Tributada sem permissão de crédito' },
  { value: '103', label: '103 - Isenção do ICMS para faixa de receita bruta' },
  { value: '201', label: '201 - Tributada com permissão de crédito e cobrança do ICMS por ST' },
  { value: '202', label: '202 - Tributada sem permissão de crédito e cobrança do ICMS por ST' },
  { value: '203', label: '203 - Isenção do ICMS para faixa de receita bruta e cobrança do ICMS por ST' },
  { value: '300', label: '300 - Imune' },
  { value: '400', label: '400 - Não tributada pelo Simples Nacional' },
  { value: '500', label: '500 - ICMS cobrado anteriormente por ST ou por antecipação' },
  { value: '900', label: '900 - Outros' },
];

// Baseado na legislação em tramitação — atualizar quando SEFAZ publicar tabela definitiva
export const CST_IBS_CBS_OPTIONS: SelectOption[] = [
  { value: '00', label: '00 - Tributação integral' },
  { value: '10', label: '10 - Tributação com alíquota diferenciada' },
  { value: '20', label: '20 - Imunidade' },
  { value: '30', label: '30 - Isenção' },
  { value: '40', label: '40 - Não incidência' },
  { value: '50', label: '50 - Redução de alíquota' },
  { value: '60', label: '60 - Suspensão' },
  { value: '70', label: '70 - Diferimento' },
  { value: '90', label: '90 - Outros' },
];

export const UNIDADE_PRODUTO_OPTIONS: SelectOption[] = [
  { value: 'UN', label: 'UN - Unidade' },
  { value: 'KG', label: 'KG - Quilograma' },
  { value: 'CX', label: 'CX - Caixa' },
  { value: 'PCT', label: 'PCT - Pacote' },
  { value: 'L', label: 'L - Litro' },
  { value: 'M', label: 'M - Metro' },
  { value: 'M2', label: 'M2 - Metro quadrado' },
  { value: 'PAR', label: 'PAR - Par' },
];

export const UNIDADE_SERVICO_OPTIONS: SelectOption[] = [
  { value: 'SV', label: 'SV - Serviço' },
  { value: 'HR', label: 'HR - Hora' },
  { value: 'UN', label: 'UN - Unidade' },
];
