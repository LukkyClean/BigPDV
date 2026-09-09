<script setup lang="ts">
/**
 * @component EmissaoStatusSection
 * @description Diz, na tela da Empresa, se o cadastro já permite emitir NF-e.
 *
 * POR QUE AQUI, e não só no Centro Fiscal: as pendências do emitente são
 * exatamente os campos DESTA tela — CNPJ, Inscrição Estadual, regime
 * tributário, indicador de IE e o endereço. Quem precisa corrigi-las já está
 * com o formulário aberto; mandá-lo a outra tela para descobrir o que falta,
 * e voltar para preencher, é o caminho longo.
 *
 * SÓ APARECE COM O MÓDULO. Sem NF-e na licença o card continua sendo o upsell
 * de antes: um selo de "pronto para emitir" numa loja que não contratou
 * emissão não informa nada, e um de "faltam 4 dados" a assusta à toa.
 */

import { computed } from 'vue';
import { FileText, Lock, ChevronRight, CheckCircle2, AlertTriangle } from 'lucide-vue-next';
import { useRouter } from 'vue-router';

import { recursoDisponivel } from '@/shared/config/planos';
import { useFiscalPendenciasQuery } from '@/modules/fiscal/composables/useFiscalPendenciasQuery';

const router = useRouter();

// Computed, e não leitura única: se a licença for revalidada no meio da sessão
// (o `router.beforeEach` a checa a cada 5 min), o card acompanha sem F5.
const nfeDisponivel = computed(() => recursoDisponivel('nfe'));

// A rota /fiscal/pendencias exige o módulo NFE no backend — sem ele a consulta
// seria um 403 a cada visita a esta tela.
const { data: pendencias, isLoading } = useFiscalPendenciasQuery(nfeDisponivel);

const emitenteCompleto = computed(() => pendencias.value?.emitente_completo === true);

const faltantes = computed(() => {
  if (!pendencias.value || pendencias.value.emitente_completo) return [];
  return pendencias.value.emitente_pendencias;
});

/**
 * Enquanto não sabemos, não afirmamos nada.
 *
 * O selo verde é uma promessa ("pode emitir"); mostrá-lo no instante entre o
 * render e a resposta faria o lojista ler "está tudo certo" para logo depois a
 * lista de pendências aparecer embaixo.
 */
const estado = computed<'sem-modulo' | 'carregando' | 'ok' | 'pendente' | 'indefinido'>(() => {
  if (!nfeDisponivel.value) return 'sem-modulo';
  if (isLoading.value) return 'carregando';
  if (!pendencias.value) return 'indefinido';
  return emitenteCompleto.value ? 'ok' : 'pendente';
});
</script>

<template>
  <section
    class="bg-white rounded-xl shadow-sm border transition-all"
    :class="estado === 'pendente' ? 'border-amber-200' : 'border-gray-100'"
  >
    <button
      type="button"
      class="w-full flex items-center gap-4 p-5 text-left hover:bg-gray-50/60 rounded-xl transition-colors"
      @click="router.push('/fiscal')"
    >
      <div
        class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
        :class="estado === 'pendente' ? 'bg-amber-50 text-amber-600' : 'bg-brand-primary-light text-brand-primary'"
      >
        <FileText :size="20" />
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <h3 class="text-sm font-bold text-gray-800">Emissão de Notas Fiscais</h3>

          <span
            v-if="estado === 'sem-modulo'"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[10px] font-bold uppercase"
          >
            <Lock :size="10" /> Plano superior
          </span>

          <span
            v-else-if="estado === 'ok'"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase"
          >
            <CheckCircle2 :size="10" /> Pronto para emitir
          </span>

          <span
            v-else-if="estado === 'pendente'"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-[10px] font-bold uppercase"
          >
            <AlertTriangle :size="10" />
            {{ faltantes.length }}
            {{ faltantes.length === 1 ? 'dado faltando' : 'dados faltando' }}
          </span>

          <span
            v-else-if="estado === 'carregando'"
            class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-400 text-[10px] font-bold uppercase"
          >
            Verificando…
          </span>
        </div>

        <p class="text-xs text-gray-500 mt-0.5">
          <template v-if="estado === 'sem-modulo'">
            Não incluído no seu plano. Toque para fazer upgrade.
          </template>
          <template v-else-if="estado === 'ok'">
            Os dados da empresa atendem às exigências da SEFAZ.
          </template>
          <template v-else-if="estado === 'pendente'">
            A SEFAZ exige estes dados do emitente. Sem eles a nota é recusada.
          </template>
          <template v-else>
            Configure a emissão de NF-e, NFC-e e NFS-e.
          </template>
        </p>
      </div>

      <ChevronRight :size="18" class="text-gray-400 shrink-0" />
    </button>

    <!-- A lista fica FORA do <button>: conteúdo de botão é phrasing content,
         e uma <ul> dentro dele é markup inválido. -->
    <ul v-if="estado === 'pendente'" class="px-5 pb-5 pt-0 space-y-1.5">
      <li
        v-for="(mensagem, i) in faltantes"
        :key="i"
        class="flex items-start gap-2 text-xs text-amber-800 bg-amber-50/60 rounded-lg px-3 py-2"
      >
        <AlertTriangle :size="13" class="shrink-0 mt-0.5 text-amber-500" />
        <span>{{ mensagem }}</span>
      </li>
    </ul>
  </section>
</template>
