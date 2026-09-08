<script setup lang="ts">
/**
 * A trilha de auditoria de um documento financeiro.
 *
 * Idêntica para contas a pagar e a receber, por isso mora em `shared/`: as duas
 * lêem a mesma tabela `historico_financeiro`, com as mesmas colunas.
 *
 * O backend guarda o campo com o nome TÉCNICO (`plano_conta_id`, `baixa`) e o
 * valor como TEXTO CRU (centavos, ISO). Traduzir é trabalho da tela — guardar
 * já formatado no banco amarraria o histórico ao idioma e ao formato de hoje.
 */
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataHora, formatDataPura } from '@/shared/utils/date.utils';

import type { HistoricoFinanceiro } from '../schemas/financeiro.schema';

const props = defineProps<{ historico: HistoricoFinanceiro[]; carregando?: boolean }>();

const ROTULOS: Record<string, string> = {
  criacao: 'Lançamento',
  baixa: 'Pagamento registrado',
  estorno: 'Estorno',
  status: 'Situação',
  valor: 'Valor',
  vencimento: 'Vencimento',
  plano_conta_id: 'Categoria',
  fornecedor_id: 'Fornecedor',
  cliente_id: 'Cliente',
  taxa: 'Taxa da operadora',
};

function rotulo(campo: string): string {
  return ROTULOS[campo] ?? campo;
}

/** Campos que guardam centavos — o resto é texto ou data. */
const EM_CENTAVOS = new Set(['valor', 'taxa']);

function valorLegivel(campo: string, bruto?: string | null): string {
  if (bruto === null || bruto === undefined || bruto === '') return '—';
  if (EM_CENTAVOS.has(campo)) {
    const n = Number(bruto);
    return Number.isFinite(n) ? formatCurrency(n) : bruto;
  }
  if (campo === 'vencimento') return formatDataPura(bruto);
  return bruto;
}

/**
 * Alteração de campo mostra "de X para Y"; evento (criação, baixa, estorno) tem
 * só o lado novo, e mostrar "de — para ..." nesses casos só polui.
 */
function ehEvento(campo: string): boolean {
  return ['criacao', 'baixa', 'estorno'].includes(campo);
}
</script>

<template>
  <div>
    <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
      Histórico
    </h4>

    <p v-if="carregando" class="text-sm text-zinc-400">Carregando…</p>

    <p v-else-if="!props.historico.length" class="text-sm text-zinc-400">
      Nada foi alterado desde o lançamento.
    </p>

    <ul v-else class="flex flex-col divide-y divide-zinc-100">
      <li v-for="linha in props.historico" :key="linha.id" class="py-2.5">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <span class="text-sm font-medium text-zinc-800">{{ rotulo(linha.campo) }}</span>
          <span class="text-[11px] text-zinc-400">
            {{ formatDataHora(linha.criado_em) }}
            <template v-if="linha.funcionario_nome"> · {{ linha.funcionario_nome }}</template>
          </span>
        </div>

        <p class="mt-0.5 text-xs text-zinc-500">
          <template v-if="ehEvento(linha.campo)">
            {{ valorLegivel(linha.campo, linha.valor_novo) }}
          </template>
          <template v-else>
            de <span class="text-zinc-700">{{ valorLegivel(linha.campo, linha.valor_antigo) }}</span>
            para <span class="text-zinc-700">{{ valorLegivel(linha.campo, linha.valor_novo) }}</span>
          </template>
        </p>
      </li>
    </ul>
  </div>
</template>
