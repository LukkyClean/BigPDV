<script setup lang="ts">
/**
 * @component FiscalPlataformaCard
 * @description Mostra o OUTRO lado do cano de emissão.
 *
 * A emissão passa por ERP → plataforma → Focus → SEFAZ, e quando ela é recusada
 * o lojista só via a mensagem final — que parece da SEFAZ, porque o corpo do
 * 4xx da plataforma vira `mensagem_sefaz`. Não havia como olhar o degrau do
 * meio, e descobrir "de quem é o problema" custou um dia de investigação.
 *
 * A regra que rege este card: "não sei" nunca vira "não configurado". Se a
 * plataforma não responde, dizemos que não deu para consultar.
 */

import { computed } from 'vue';
import { CheckCircle2, XCircle, AlertTriangle, CloudOff, RefreshCw, Server } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useFiscalPlataformaQuery } from '../../composables/useFiscalPlataformaQuery';
import type { FiscalConfiguracao } from '../../types/fiscal.types';

const props = defineProps<{ configuracao: FiscalConfiguracao | undefined }>();

const { data: diagnostico, isLoading, isFetching, refetch } = useFiscalPlataformaQuery();

const respondeu = computed(() => diagnostico.value?.consultou === true);

/** Linhas de "sim/não" que a plataforma responde sobre si mesma. */
const itens = computed(() => {
  const d = diagnostico.value;
  if (!d?.consultou) return [];
  return [
    { rotulo: 'Empresa configurada', valor: d.configurado },
    { rotulo: 'Token da emissora', valor: d.token_configurado },
    { rotulo: 'CSC (necessário para NFC-e)', valor: d.csc_configurado },
  ];
});

/**
 * O ambiente da PLATAFORMA é o que vale — o daqui só trava localmente.
 *
 * Divergir não é detalhe: se lá está em produção e a tela daqui diz
 * homologação, o lojista emite nota real achando que testa.
 */
const ambienteDivergente = computed(() => {
  const daPlataforma = diagnostico.value?.ambiente;
  const daqui = props.configuracao?.ambiente;
  if (!respondeu.value || daPlataforma == null || daqui == null) return false;
  return daPlataforma !== daqui;
});

const nomeAmbiente = (valor: number | null | undefined) =>
  valor === 1 ? 'Produção' : valor === 2 ? 'Homologação' : '—';

function formatarCnpj(valor: string | null | undefined) {
  if (!valor) return null;
  if (valor.length !== 14) return valor;
  return valor.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}
</script>

<template>
  <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
    <div class="flex items-start justify-between gap-4 mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary shrink-0">
          <Server :size="18" />
        </div>
        <div>
          <h3 class="text-base font-bold text-zinc-900">Plataforma de Emissão</h3>
          <p class="text-xs text-zinc-500">O que o servidor de emissão enxerga desta loja</p>
        </div>
      </div>

      <BaseButton
        variant="ghost"
        class="shrink-0 text-xs"
        :is-loading="isFetching"
        @click="refetch()"
      >
        <RefreshCw :size="14" class="mr-1.5" />
        Verificar
      </BaseButton>
    </div>

    <div v-if="isLoading" class="h-24 rounded-xl bg-zinc-100 animate-pulse"></div>

    <!-- Nao respondeu: indisponibilidade, e nao "nao configurado" -->
    <div
      v-else-if="!respondeu"
      class="flex items-start gap-3 p-4 rounded-xl bg-zinc-50 border border-zinc-200"
    >
      <CloudOff :size="18" class="text-zinc-400 shrink-0 mt-0.5" />
      <div class="text-sm text-zinc-600">
        <p class="font-semibold text-zinc-700">Não foi possível consultar a plataforma agora.</p>
        <p class="text-xs mt-1 leading-relaxed">
          Isso não quer dizer que a emissão esteja mal configurada — quer dizer que
          não deu para verificar. Confira a internet da loja e tente de novo.
        </p>
      </div>
    </div>

    <div v-else class="space-y-4">
      <!-- Ambiente: quem manda e a plataforma -->
      <div
        class="p-4 rounded-xl border"
        :class="ambienteDivergente ? 'bg-red-50 border-red-200' : 'bg-zinc-50 border-zinc-200'"
      >
        <div class="flex items-center justify-between gap-3">
          <span class="text-xs text-zinc-500">Ambiente de emissão (definido pela plataforma)</span>
          <strong class="text-sm text-zinc-900">
            {{ diagnostico?.ambiente_nome || nomeAmbiente(diagnostico?.ambiente) }}
          </strong>
        </div>
        <p v-if="ambienteDivergente" class="flex items-start gap-2 text-xs text-red-700 mt-2 leading-relaxed">
          <AlertTriangle :size="14" class="shrink-0 mt-0.5" />
          <span>
            Esta tela está mostrando <strong>{{ nomeAmbiente(props.configuracao?.ambiente) }}</strong>,
            mas quem decide é a plataforma. Enquanto estiverem diferentes, uma emissão
            de teste pode virar <strong>nota real</strong>.
          </span>
        </p>
      </div>

      <!-- Sim/nao do outro lado -->
      <ul class="space-y-2">
        <li
          v-for="item in itens"
          :key="item.rotulo"
          class="flex items-center justify-between gap-3 text-sm"
        >
          <span class="text-zinc-600">{{ item.rotulo }}</span>
          <span v-if="item.valor === true" class="inline-flex items-center gap-1 text-emerald-700 font-semibold text-xs">
            <CheckCircle2 :size="14" /> Sim
          </span>
          <span v-else-if="item.valor === false" class="inline-flex items-center gap-1 text-amber-700 font-semibold text-xs">
            <XCircle :size="14" /> Não
          </span>
          <span v-else class="text-zinc-400 text-xs">não informado</span>
        </li>

        <li v-if="diagnostico?.certificado_status" class="flex items-center justify-between gap-3 text-sm">
          <span class="text-zinc-600">Certificado na plataforma</span>
          <strong class="text-xs text-zinc-900">{{ diagnostico.certificado_status }}</strong>
        </li>
      </ul>

      <!-- A comparacao que encerra a duvida -->
      <div class="p-4 rounded-xl bg-zinc-50 border border-zinc-200 space-y-2">
        <p class="text-xs font-semibold text-zinc-500 uppercase tracking-wide">CNPJ do emitente</p>

        <div class="flex items-center justify-between gap-3 text-sm">
          <span class="text-zinc-600">Enviado por este sistema</span>
          <strong class="text-zinc-900">{{ formatarCnpj(diagnostico?.cnpj_erp) || '—' }}</strong>
        </div>

        <div class="flex items-center justify-between gap-3 text-sm">
          <span class="text-zinc-600">Cadastrado na plataforma</span>
          <strong v-if="diagnostico?.cnpj_plataforma" class="text-zinc-900">
            {{ formatarCnpj(diagnostico.cnpj_plataforma) }}
          </strong>
          <span v-else class="text-zinc-400 text-xs">a plataforma não informa</span>
        </div>

        <p
          v-if="diagnostico?.cnpj_confere === false"
          class="flex items-start gap-2 text-xs text-red-700 leading-relaxed pt-1"
        >
          <AlertTriangle :size="14" class="shrink-0 mt-0.5" />
          <span>
            Os dois são diferentes. Enquanto não forem o mesmo número, a emissão é
            recusada antes de chegar à SEFAZ.
          </span>
        </p>
        <p
          v-else-if="diagnostico?.cnpj_confere === true"
          class="flex items-center gap-2 text-xs text-emerald-700 pt-1"
        >
          <CheckCircle2 :size="14" class="shrink-0" />
          Os dois conferem.
        </p>
      </div>

      <!-- Pendencias que a propria plataforma aponta -->
      <ul v-if="diagnostico?.pendencias?.length" class="space-y-1.5">
        <li
          v-for="(p, i) in diagnostico.pendencias"
          :key="i"
          class="flex items-start gap-2 text-xs text-amber-800 bg-amber-50/60 rounded-lg px-3 py-2"
        >
          <AlertTriangle :size="13" class="shrink-0 mt-0.5 text-amber-500" />
          <span>{{ p }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>
