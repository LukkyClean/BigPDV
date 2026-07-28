<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { AlertTriangle, Printer, RefreshCw } from 'lucide-vue-next'
import { storeToRefs } from 'pinia'

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import { useImpressaoStore } from '@/shared/stores/impressao.store'
import { useImpressao } from '@/shared/composables/useImpressao'
import { useToast } from '@/shared/composables/useToast'
import {
  impressaoDisponivel,
  listarImpressoras,
  descobrirServidoresImpressao,
  obterIpLocal,
} from '@/shared/services/impressao.service'
import type { ImpressoraInfo, ServidorDescoberto } from '@/shared/services/impressao.service'
import type { ConfigImpressao } from '@/shared/stores/impressao.store'

const impressaoStore = useImpressaoStore()
const { config } = storeToRefs(impressaoStore)
const impressao = useImpressao()
const toast = useToast()

const isTauriApp = impressaoDisponivel()

function valoresDoStore(): ConfigImpressao {
  return { ...config.value }
}

const form = ref<ConfigImpressao>(valoresDoStore())

function resetar() {
  Object.assign(form.value, valoresDoStore())
}

watch(config, resetar, { deep: true })

const isDirty = computed(() => JSON.stringify(form.value) !== JSON.stringify(valoresDoStore()))

defineExpose({ form, isDirty, resetar })

// ── Lista de impressoras do Windows ──
const impressoras = ref<ImpressoraInfo[]>([])
const carregandoImpressoras = ref(false)

async function carregarImpressoras() {
  if (!isTauriApp) return
  carregandoImpressoras.value = true
  try {
    impressoras.value = await listarImpressoras()
  } catch (error) {
    console.error('[Impressão] Falha ao listar impressoras:', error)
    toast.error('Não foi possível listar as impressoras do Windows')
    impressoras.value = []
  } finally {
    carregandoImpressoras.value = false
  }
}

onMounted(carregarImpressoras)

// Impressora salva que não está mais instalada aparece como opção extra
const impressoraSalvaAusente = computed(() =>
  form.value.impressora_termica && !impressoras.value.some((i) => i.nome === form.value.impressora_termica)
    ? form.value.impressora_termica
    : null,
)

// ── Teste de impressão / gaveta (usa os valores do FORM, antes de salvar) ──
const testando = ref(false)

const podeTestar = computed(() => {
  if (!isTauriApp || testando.value) return false
  if (form.value.tipo_conexao === 'rede') return !!form.value.ip_impressora
  return !!form.value.impressora_termica
})

async function imprimirTeste() {
  testando.value = true
  try {
    await impressao.imprimirTeste(form.value)
    toast.success('Cupom de teste enviado à impressora!')
  } catch (error: any) {
    toast.error('Falha no teste de impressão', String(error?.message ?? error))
  } finally {
    testando.value = false
  }
}

async function testarGaveta() {
  testando.value = true
  try {
    await impressao.abrirGaveta(form.value)
    toast.success('Pulso de gaveta enviado!')
  } catch (error: any) {
    toast.error('Falha ao acionar a gaveta', String(error?.message ?? error))
  } finally {
    testando.value = false
  }
}

const OPCOES_AUTO = [
  { value: 'automatico', label: 'Imprimir automaticamente' },
  { value: 'nao', label: 'Não imprimir' },
] as const

// ── Compartilhamento da impressora na LAN ──
const ipLocal = ref<string | null>(null)

onMounted(async () => {
  if (!isTauriApp) return
  try {
    ipLocal.value = await obterIpLocal()
  } catch {
    ipLocal.value = null
  }
})

// ── Descoberta de servidores de impressão (modo rede) ──
const procurando = ref(false)
const servidoresEncontrados = ref<ServidorDescoberto[]>([])
const buscaRealizada = ref(false)

async function procurarNaRede() {
  procurando.value = true
  buscaRealizada.value = false
  try {
    servidoresEncontrados.value = await descobrirServidoresImpressao()
  } catch (error) {
    console.error('[Impressão] Falha na descoberta:', error)
    toast.error('Não foi possível procurar na rede')
    servidoresEncontrados.value = []
  } finally {
    procurando.value = false
    buscaRealizada.value = true
  }
}

function usarServidor(servidor: ServidorDescoberto) {
  form.value.ip_impressora = servidor.ip
  form.value.porta_impressora = servidor.porta
  toast.success(`Impressora de "${servidor.nome}" selecionada!`)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Impressão e Periféricos</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Configure a impressora térmica, bobina e comportamento de impressão deste computador</p>
    </div>

    <!-- Aviso fora do app desktop -->
    <div v-if="!isTauriApp" class="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-100 rounded-xl">
      <AlertTriangle :size="16" class="text-amber-500 shrink-0 mt-0.5" />
      <p class="text-xs text-amber-700 leading-snug">
        A impressão térmica direta está disponível apenas no <strong>aplicativo desktop</strong>.
        No navegador, a impressão usa o diálogo padrão do sistema.
      </p>
    </div>

    <!-- Conexão da impressora -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1">Impressora Térmica</p>
      <p class="text-xs text-zinc-500 mb-3">Esta configuração vale apenas para este computador</p>

      <div class="flex gap-2 mb-3">
        <button
          type="button"
          :class="[
            'flex-1 p-3 border rounded-xl text-left transition-colors cursor-pointer',
            form.tipo_conexao === 'windows' ? 'border-brand-primary bg-brand-primary/5' : 'border-zinc-200 hover:border-zinc-300',
          ]"
          @click="form.tipo_conexao = 'windows'"
        >
          <p class="text-sm font-medium text-zinc-800">Impressora do Windows</p>
          <p class="text-xs text-zinc-500 mt-0.5">USB ou compartilhada na rede (\\PC\impressora)</p>
        </button>
        <button
          type="button"
          :class="[
            'flex-1 p-3 border rounded-xl text-left transition-colors cursor-pointer',
            form.tipo_conexao === 'rede' ? 'border-brand-primary bg-brand-primary/5' : 'border-zinc-200 hover:border-zinc-300',
          ]"
          @click="form.tipo_conexao = 'rede'"
        >
          <p class="text-sm font-medium text-zinc-800">Impressora de rede (IP)</p>
          <p class="text-xs text-zinc-500 mt-0.5">Térmica com Ethernet/Wi-Fi, porta 9100</p>
        </button>
      </div>

      <!-- Modo Windows: dropdown -->
      <div v-if="form.tipo_conexao === 'windows'" class="py-2">
        <label class="text-xs font-medium text-zinc-600">Impressora</label>
        <div class="flex items-center gap-2 mt-1.5">
          <select
            v-model="form.impressora_termica"
            :disabled="!isTauriApp"
            class="flex-1 border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 disabled:opacity-50"
          >
            <option :value="null">Selecione uma impressora...</option>
            <option v-if="impressoraSalvaAusente" :value="impressoraSalvaAusente">
              {{ impressoraSalvaAusente }} (não encontrada)
            </option>
            <option v-for="imp in impressoras" :key="imp.nome" :value="imp.nome">
              {{ imp.nome }}{{ imp.padrao ? ' (Padrão do Windows)' : '' }}
            </option>
          </select>
          <button
            type="button"
            :disabled="!isTauriApp || carregandoImpressoras"
            class="p-2.5 border border-zinc-200 rounded-lg text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 cursor-pointer"
            title="Atualizar lista"
            @click="carregarImpressoras"
          >
            <RefreshCw :size="15" :class="carregandoImpressoras ? 'animate-spin' : ''" />
          </button>
        </div>
      </div>

      <!-- Modo rede: IP + porta + descoberta -->
      <div v-else class="py-2">
        <div class="flex gap-2">
          <div class="flex-1">
            <label class="text-xs font-medium text-zinc-600">Endereço IP da impressora ou do caixa que compartilha</label>
            <input
              v-model="form.ip_impressora"
              type="text"
              placeholder="192.168.0.50"
              :disabled="!isTauriApp"
              class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 disabled:opacity-50"
            />
          </div>
          <div class="w-28">
            <label class="text-xs font-medium text-zinc-600">Porta</label>
            <input
              v-model.number="form.porta_impressora"
              type="number"
              min="1"
              max="65535"
              :disabled="!isTauriApp"
              class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 disabled:opacity-50"
            />
          </div>
        </div>

        <div class="mt-2">
          <BaseButton variant="secondary" size="sm" :disabled="!isTauriApp" :is-loading="procurando" @click="procurarNaRede">
            <RefreshCw :size="14" class="mr-1.5" />
            Procurar na rede
          </BaseButton>

          <div v-if="servidoresEncontrados.length" class="mt-2 flex flex-col gap-1.5">
            <button
              v-for="servidor in servidoresEncontrados"
              :key="servidor.ip"
              type="button"
              :class="[
                'flex items-center justify-between p-2.5 border rounded-xl text-left transition-colors cursor-pointer',
                form.ip_impressora === servidor.ip ? 'border-brand-primary bg-brand-primary/5' : 'border-zinc-200 hover:border-zinc-300',
              ]"
              @click="usarServidor(servidor)"
            >
              <div>
                <p class="text-sm font-medium text-zinc-800">{{ servidor.nome }}</p>
                <p class="text-xs text-zinc-500">{{ servidor.ip }} — porta {{ servidor.porta }}</p>
              </div>
              <Printer :size="15" class="text-zinc-400" />
            </button>
          </div>
          <p v-else-if="buscaRealizada && !procurando" class="text-xs text-zinc-400 mt-2">
            Nenhum caixa compartilhando impressora foi encontrado na rede.
          </p>
        </div>
      </div>

      <!-- Bobina -->
      <div class="py-2">
        <label class="text-xs font-medium text-zinc-600">Largura da bobina</label>
        <div class="flex gap-2 mt-1.5">
          <button
            type="button"
            :class="[
              'flex-1 p-2.5 border rounded-xl text-center transition-colors cursor-pointer',
              form.bobina === '80' ? 'border-brand-primary bg-brand-primary/5 text-brand-primary font-medium' : 'border-zinc-200 text-zinc-600 hover:border-zinc-300',
            ]"
            @click="form.bobina = '80'"
          >
            <span class="text-sm">Bobina 80mm</span>
            <span class="block text-[10px] text-zinc-400">48 colunas — padrão</span>
          </button>
          <button
            type="button"
            :class="[
              'flex-1 p-2.5 border rounded-xl text-center transition-colors cursor-pointer',
              form.bobina === '58' ? 'border-brand-primary bg-brand-primary/5 text-brand-primary font-medium' : 'border-zinc-200 text-zinc-600 hover:border-zinc-300',
            ]"
            @click="form.bobina = '58'"
          >
            <span class="text-sm">Bobina 58mm</span>
            <span class="block text-[10px] text-zinc-400">32 colunas — compacta</span>
          </button>
        </div>
      </div>

      <!-- Teste -->
      <div class="py-2 flex flex-wrap gap-2">
        <BaseButton variant="secondary" size="sm" :disabled="!podeTestar" :is-loading="testando" @click="imprimirTeste">
          <Printer :size="14" class="mr-1.5" />
          Imprimir Cupom de Teste
        </BaseButton>
      </div>
    </div>

    <!-- Compartilhamento na LAN (só faz sentido com impressora local do Windows) -->
    <div v-if="form.tipo_conexao === 'windows'" class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Compartilhar Impressora na Rede</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Permitir que outros caixas usem esta impressora</p>
          <p class="text-xs text-zinc-500 mt-0.5">O StartBig deste PC vira um servidor de impressão — sem compartilhamento do Windows</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.compartilhar_impressora ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.compartilhar_impressora = !form.compartilhar_impressora"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.compartilhar_impressora ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <template v-if="form.compartilhar_impressora">
        <div class="flex gap-2 py-2">
          <div class="flex-1">
            <label class="text-xs font-medium text-zinc-600">Nome deste caixa</label>
            <p class="text-[11px] text-zinc-400 mt-0.5 mb-1">Como ele aparece na busca dos outros PCs</p>
            <input
              v-model="form.nome_terminal"
              type="text"
              placeholder="Caixa Principal"
              maxlength="40"
              class="w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
            />
          </div>
          <div class="w-28">
            <label class="text-xs font-medium text-zinc-600">Porta</label>
            <p class="text-[11px] text-zinc-400 mt-0.5 mb-1">Padrão 9100</p>
            <input
              v-model.number="form.porta_compartilhamento"
              type="number"
              min="1"
              max="65535"
              class="w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
            />
          </div>
        </div>

        <div class="flex items-start gap-2.5 p-3 my-2 bg-blue-50 border border-blue-100 rounded-xl">
          <Printer :size="16" class="text-blue-500 shrink-0 mt-0.5" />
          <p class="text-xs text-blue-700 leading-snug">
            Após salvar, os outros caixas encontram este PC pelo botão <strong>"Procurar na rede"</strong>
            <template v-if="ipLocal"> — ou manualmente pelo IP <strong>{{ ipLocal }}</strong>, porta <strong>{{ form.porta_compartilhamento }}</strong></template>.
          </p>
        </div>

        <div class="flex items-start gap-2.5 p-3 mb-2 bg-amber-50 border border-amber-100 rounded-xl">
          <AlertTriangle :size="16" class="text-amber-500 shrink-0 mt-0.5" />
          <p class="text-xs text-amber-700 leading-snug">
            Na primeira ativação o Windows pedirá permissão de firewall — clique em <strong>"Permitir acesso"</strong>
            para que os outros caixas consigam imprimir.
          </p>
        </div>
      </template>
    </div>

    <!-- Documentos -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Documentos</p>

      <div class="py-2 border-b border-zinc-100">
        <p class="text-sm font-medium text-zinc-800 mb-1.5">Vendas</p>
        <div class="flex gap-2">
          <div class="flex-1">
            <label class="text-xs font-medium text-zinc-600">Ao finalizar a venda</label>
            <select
              v-model="form.auto_imprimir_venda"
              class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
            >
              <option v-for="op in OPCOES_AUTO" :key="op.value" :value="op.value">{{ op.label }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="py-2 border-b border-zinc-100">
        <p class="text-sm font-medium text-zinc-800 mb-1.5">Ordens de Serviço</p>
        <div class="flex gap-2">
          <div class="flex-1">
            <label class="text-xs font-medium text-zinc-600">Ao criar ou finalizar a OS</label>
            <select
              v-model="form.auto_imprimir_os"
              class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
            >
              <option v-for="op in OPCOES_AUTO" :key="op.value" :value="op.value">{{ op.label }}</option>
            </select>
          </div>
        </div>
      </div>

      <p class="text-[11px] text-zinc-400 mt-1.5">
        Cupom térmico imprime direto, sem janelas (exige impressora configurada acima; sem ela, o sistema pergunta).
        Folha A4 abre o diálogo de impressão do Windows com o documento pronto.
        Orçamentos e reimpressões sempre perguntam o formato.
      </p>
    </div>

    <!-- Gaveta de dinheiro -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Gaveta de Dinheiro</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Ativar gaveta de dinheiro</p>
          <p class="text-xs text-zinc-500 mt-0.5">Gaveta conectada à impressora térmica (RJ-11)</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.gaveta_ativa ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.gaveta_ativa = !form.gaveta_ativa"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.gaveta_ativa ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100" :class="{ 'opacity-60': !form.gaveta_ativa }">
        <div>
          <p class="text-sm font-medium text-zinc-800">Abrir ao finalizar venda em dinheiro</p>
          <p class="text-xs text-zinc-500 mt-0.5">A gaveta abre junto com a impressão do cupom</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.abrir_gaveta_na_venda ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.abrir_gaveta_na_venda = !form.abrir_gaveta_na_venda"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.abrir_gaveta_na_venda ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="py-2">
        <BaseButton variant="ghost" size="sm" :disabled="!podeTestar || !form.gaveta_ativa" :is-loading="testando" @click="testarGaveta">
          Testar Gaveta
        </BaseButton>
      </div>
    </div>
  </div>
</template>
