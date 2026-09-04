<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue'
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store'
import { useConfiguracoesOSQuery } from '@/modules/configuracoes/composables/queries/useConfiguracoesOSQuery'
import { GARANTIA_OPTIONS } from '@/modules/configuracoes/schemas/configuracoes.schema'
import type { ConfiguracaoOSUpdate } from '@/modules/configuracoes/schemas/configuracoes.schema'

const configStore = useConfiguracoesStore()
const {
  prazoEntregaPadrao,
  garantiaPadrao,
  prazoAbandonoDias,
  taxaDiagnosticoPadrao,
  comprovanteEntradaFolha,
  comprovanteEntradaDensidade,
  comprovanteEntregaFolha,
  comprovanteEntregaDensidade,
} = storeToRefs(configStore)

useConfiguracoesOSQuery()

function valoresDoStore(): ConfiguracaoOSUpdate {
  return {
    prazo_entrega_padrao: prazoEntregaPadrao.value,
    garantia_padrao: garantiaPadrao.value as typeof GARANTIA_OPTIONS[number],
    prazo_abandono_dias: prazoAbandonoDias.value,
    taxa_diagnostico_padrao: taxaDiagnosticoPadrao.value,
    comprovante_entrada_folha: comprovanteEntradaFolha.value,
    comprovante_entrada_densidade: comprovanteEntradaDensidade.value,
    comprovante_entrega_folha: comprovanteEntregaFolha.value,
    comprovante_entrega_densidade: comprovanteEntregaDensidade.value,
  }
}

/** Rótulos dos comprovantes. O texto é o que ensina o lojista, não a documentação. */
const DOCUMENTOS = [
  {
    chave: 'entrada' as const,
    titulo: 'Via de entrada',
    ajuda: 'Impressa ao abrir a OS — o protocolo que o cliente leva.',
    campoFolha: 'comprovante_entrada_folha' as const,
    campoDensidade: 'comprovante_entrada_densidade' as const,
  },
  {
    chave: 'entrega' as const,
    titulo: 'Via de entrega',
    ajuda: 'Impressa ao finalizar — leva os itens e o resumo do pagamento.',
    campoFolha: 'comprovante_entrega_folha' as const,
    campoDensidade: 'comprovante_entrega_densidade' as const,
  },
]

const form = ref<ConfiguracaoOSUpdate>(valoresDoStore())

const taxaReais = ref(taxaDiagnosticoPadrao.value / 100)
watch(taxaReais, (val) => {
  form.value.taxa_diagnostico_padrao = Math.round((val || 0) * 100)
})
watch(taxaDiagnosticoPadrao, (val) => {
  taxaReais.value = val / 100
})

function resetar() {
  Object.assign(form.value, valoresDoStore())
  taxaReais.value = taxaDiagnosticoPadrao.value / 100
}

watch(() => configStore.configOS, resetar)

const isDirty = computed(() => JSON.stringify(form.value) !== JSON.stringify(valoresDoStore()))

defineExpose({ form, isDirty, resetar })
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Ordens de Serviço</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Configure os padrões e fluxos das ordens de serviço</p>
    </div>

    <!-- PRAZOS -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Prazos</p>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Prazo padrão de entrega (dias)</label>
        <p class="text-[11px] text-zinc-400 mt-0.5 mb-2">
          Ao criar uma nova OS, o campo "Previsão" será preenchido automaticamente com esta quantidade de dias
        </p>
        <input
          v-model.number="form.prazo_entrega_padrao"
          type="number"
          min="1"
          max="365"
          class="mt-1 w-24 border border-zinc-200 rounded-lg px-3 py-2 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
        />
        <span class="ml-2 text-xs text-zinc-400">dias</span>
      </div>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Prazo de abandono (dias)</label>
        <p class="text-[11px] text-zinc-400 mt-0.5 mb-2">
          Dias após a conclusão para considerar o equipamento abandonado. Exibido nos comprovantes de entrada.
        </p>
        <input
          v-model.number="form.prazo_abandono_dias"
          type="number"
          min="1"
          max="365"
          class="mt-1 w-24 border border-zinc-200 rounded-lg px-3 py-2 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
        />
        <span class="ml-2 text-xs text-zinc-400">dias</span>
      </div>
    </div>

    <!-- PADRÕES -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Padrões</p>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Garantia padrão</label>
        <p class="text-[11px] text-zinc-400 mt-0.5 mb-2">
          Opção pré-selecionada ao finalizar uma OS. Pode ser alterada durante a finalização.
        </p>
        <select
          v-model="form.garantia_padrao"
          class="mt-1 border border-zinc-200 rounded-lg px-3 py-2 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
        >
          <option v-for="opcao in GARANTIA_OPTIONS" :key="opcao" :value="opcao">{{ opcao }}</option>
        </select>
      </div>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Taxa de diagnóstico padrão</label>
        <p class="text-[11px] text-zinc-400 mt-0.5 mb-2">
          Adicionada automaticamente como primeiro item ao criar uma nova OS. Defina R$ 0,00 para desativar.
        </p>
        <div class="mt-1 w-36">
          <BaseMoneyInput v-model="taxaReais" />
        </div>
      </div>
    </div>

    <!-- COMPROVANTES -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Comprovantes</p>

      <!--
        Só a FORMA é configurável. O aviso abaixo existe porque a primeira
        pergunta do lojista vai ser "e dá pra tirar tal informação?" — melhor
        responder antes de ele procurar a opção que não existe.
      -->
      <p class="text-[11px] text-zinc-500 mb-3 leading-relaxed">
        Dados da empresa, dados do cliente com endereço, os itens e o resumo do pagamento
        aparecem sempre — eles protegem o cliente e não podem ser removidos.
        Aqui você escolhe apenas <strong>como</strong> a via é montada no papel.
      </p>

      <div
        v-for="doc in DOCUMENTOS"
        :key="doc.chave"
        class="py-3 border-b border-zinc-100"
      >
        <p class="text-sm font-medium text-zinc-800">{{ doc.titulo }}</p>
        <p class="text-[11px] text-zinc-400 mt-0.5 mb-2">{{ doc.ajuda }}</p>

        <div class="flex flex-wrap gap-4">
          <div>
            <label class="text-xs font-medium text-zinc-600">Papel</label>
            <select
              v-model="form[doc.campoFolha]"
              class="mt-1 block w-56 rounded-md border-2 border-zinc-200 px-2 py-1.5 text-sm focus:outline-none focus:border-brand-primary"
            >
              <option value="A4">Folha inteira (A4)</option>
              <option value="A5">Meia folha — metade de uma A4</option>
            </select>
          </div>

          <div>
            <label class="text-xs font-medium text-zinc-600">Layout</label>
            <!--
              Na meia folha o layout não é uma escolha: o Normal custa 209mm já
              com um item, contra 148mm de metade de folha. Trancar o campo é
              mais honesto do que deixar o lojista escolher Normal e receber
              silenciosamente a via encolhida.
            -->
            <select
              v-model="form[doc.campoDensidade]"
              :disabled="form[doc.campoFolha] === 'A5'"
              class="mt-1 block w-40 rounded-md border-2 border-zinc-200 px-2 py-1.5 text-sm focus:outline-none focus:border-brand-primary disabled:bg-zinc-50 disabled:text-zinc-400 disabled:cursor-not-allowed"
            >
              <option value="normal">Normal</option>
              <option value="compacto">Compacto</option>
            </select>
            <p v-if="form[doc.campoFolha] === 'A5'" class="text-[10px] text-zinc-400 mt-1">
              Meia folha usa sempre o compacto.
            </p>
          </div>
        </div>
      </div>

      <p class="text-[11px] text-zinc-400 mt-3 leading-relaxed">
        O <strong>Compacto</strong> aproveita melhor a folha reduzindo molduras e espaços,
        sem tirar informação. É o caminho quando a via está passando para a segunda página.
        Em impressora térmica esta escolha não se aplica — o cupom já sai condensado.
      </p>
      <p class="text-[11px] text-zinc-400 mt-2 leading-relaxed">
        Na <strong>meia folha</strong> a impressora continua usando papel A4: a via ocupa a
        metade de cima, em letra menor, e sai uma linha de corte. Se tiver itens demais para
        caber na metade, a via cresce para baixo — a letra é sempre a mesma, e ela continua
        saindo em uma folha só.
      </p>
    </div>

    <!-- NOTIFICAÇÕES (visual only) -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">
        Notificações
        <span class="ml-2 text-[9px] text-zinc-300 normal-case font-normal">(em breve)</span>
      </p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100 opacity-40 cursor-not-allowed">
        <div>
          <p class="text-sm font-medium text-zinc-800">Notificar cliente ao criar OS</p>
          <p class="text-xs text-zinc-500 mt-0.5">Envia mensagem automática ao abrir a ordem</p>
        </div>
        <div class="relative w-9 h-4.5 bg-zinc-200 rounded-full shrink-0">
          <span class="absolute left-0.5 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow" />
        </div>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100 opacity-40 cursor-not-allowed">
        <div>
          <p class="text-sm font-medium text-zinc-800">Notificar cliente ao concluir OS</p>
          <p class="text-xs text-zinc-500 mt-0.5">Envia mensagem automática ao finalizar</p>
        </div>
        <div class="relative w-9 h-4.5 bg-zinc-200 rounded-full shrink-0">
          <span class="absolute left-0.5 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow" />
        </div>
      </div>
    </div>

    <!-- FLUXO (visual only) -->
    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
        Fluxo
        <span class="ml-2 text-[9px] text-zinc-300 normal-case font-normal">(em breve)</span>
      </p>

      <div class="flex items-center justify-between py-3 border-t border-zinc-100 opacity-40 cursor-not-allowed">
        <div>
          <p class="text-sm font-medium text-zinc-800">Exigir aprovação do cliente</p>
          <p class="text-xs text-zinc-500 mt-0.5">Cliente deve aprovar o orçamento antes de iniciar</p>
        </div>
        <div class="relative w-9 h-4.5 bg-zinc-200 rounded-full shrink-0">
          <span class="absolute left-0.5 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow" />
        </div>
      </div>
    </div>
  </div>
</template>
