<script setup lang="ts">
import { computed, nextTick, ref, reactive, watch } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { storeToRefs } from 'pinia'
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import PinGerenteModal from '@/modules/configuracoes/components/PinGerenteModal.vue'
import type { ModoPinGerente } from '@/modules/configuracoes/components/PinGerenteModal.vue'
import type { ConfiguracaoSegurancaRead } from '@/modules/configuracoes/schemas/configuracoes.schema'

const configStore = useConfiguracoesStore()
const {
  requerPinDescontoVenda,
  requerPinAlterarPreco,
  requerPinSangria,
  requerPinCancelarVenda,
  requerPinReabrirVenda,
  requerPinCancelarOS,
  requerPinReabrirOS,
  secoesProtegidas,
  temPinConfigurado,
} = storeToRefs(configStore)

// Seções do painel que podem ser protegidas por PIN
// (Segurança é sempre protegida quando há PIN; Suporte nunca é)
const SECOES_PROTEGIVEIS = [
  { id: 'regras-de-vendas', label: 'Regras de Vendas' },
  { id: 'gestao-financeira', label: 'Gestão Financeira' },
  { id: 'produtos-estoque', label: 'Produtos e Estoque' },
  { id: 'ordens-de-servico', label: 'Ordens de Serviço' },
  { id: 'clientes-cadastro', label: 'Clientes e Cadastro' },
  { id: 'integracoes-apis', label: 'Integrações e APIs' },
  { id: 'impressao', label: 'Impressão e Periféricos' },
  { id: 'formatos-exibicao', label: 'Formatos e Exibição' },
  { id: 'backup-dados', label: 'Backup dos Dados' },
] as const

function valoresDoStore() {
  return {
    secoes_protegidas: Object.fromEntries(
      SECOES_PROTEGIVEIS.map((s) => [s.id, secoesProtegidas.value.includes(s.id)]),
    ) as Record<string, boolean>,
    requer_pin_desconto_venda: requerPinDescontoVenda.value,
    requer_pin_alterar_preco_venda: requerPinAlterarPreco.value,
    requer_pin_sangria: requerPinSangria.value,
    requer_pin_cancelar_venda: requerPinCancelarVenda.value,
    requer_pin_reabrir_venda: requerPinReabrirVenda.value,
    requer_pin_cancelar_os: requerPinCancelarOS.value,
    requer_pin_reabrir_os: requerPinReabrirOS.value,
  }
}

const form = reactive(valoresDoStore())

function resetar() {
  Object.assign(form, valoresDoStore())
}

watch(() => configStore.configSeguranca, resetar)

const isDirty = computed(() => JSON.stringify({ ...form }) !== JSON.stringify(valoresDoStore()))

// ── Modal de PIN (definir/alterar/remover) ──
const pinModalAberto = ref(false)
const pinModalModo = ref<ModoPinGerente>('definir')

function abrirPinModal(modo: ModoPinGerente) {
  pinModalModo.value = modo
  pinModalAberto.value = true
}

function aoSalvarPin(config: ConfiguracaoSegurancaRead) {
  // Atualiza o store sem perder os toggles ainda não salvos:
  // o watch acima reseta o form ao trocar configSeguranca, então
  // capturamos as edições atuais e restauramos após o flush
  const edicoes = JSON.parse(JSON.stringify(form))
  configStore.configSeguranca = config
  void nextTick(() => Object.assign(form, edicoes))
}

defineExpose({
  get form() {
    return {
      secoes_protegidas: SECOES_PROTEGIVEIS.filter((s) => form.secoes_protegidas[s.id]).map((s) => s.id),
      requer_pin_desconto_venda: form.requer_pin_desconto_venda,
      requer_pin_alterar_preco_venda: form.requer_pin_alterar_preco_venda,
      requer_pin_sangria: form.requer_pin_sangria,
      requer_pin_cancelar_venda: form.requer_pin_cancelar_venda,
      requer_pin_reabrir_venda: form.requer_pin_reabrir_venda,
      requer_pin_cancelar_os: form.requer_pin_cancelar_os,
      requer_pin_reabrir_os: form.requer_pin_reabrir_os,
    }
  },
  isDirty,
  resetar,
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Segurança</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Configure o PIN do gerente e defina quais ações exigem aprovação</p>
    </div>

    <!-- PIN do Gerente -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">PIN do Gerente</p>

      <div class="flex items-center justify-between gap-3 p-4 border border-zinc-200 rounded-xl">
        <div>
          <div class="flex items-center gap-2">
            <p class="text-sm font-medium text-zinc-800">PIN de aprovação</p>
            <span v-if="temPinConfigurado" class="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full">
              ✓ Configurado
            </span>
            <span v-else class="text-[10px] text-zinc-400 bg-zinc-100 px-1.5 py-0.5 rounded-full">
              Não configurado
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">Exigido nas ações de aprovação e nas seções protegidas abaixo</p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <template v-if="temPinConfigurado">
            <BaseButton variant="secondary" size="sm" @click="abrirPinModal('alterar')">
              Alterar PIN
            </BaseButton>
            <BaseButton
              variant="ghost"
              size="sm"
              class="text-red-500 hover:text-red-600"
              @click="abrirPinModal('remover')"
            >
              Remover
            </BaseButton>
          </template>
          <BaseButton v-else variant="primary" size="sm" @click="abrirPinModal('definir')">
            Definir PIN
          </BaseButton>
        </div>
      </div>
    </div>

    <PinGerenteModal
      :is-open="pinModalAberto"
      :modo="pinModalModo"
      @close="pinModalAberto = false"
      @sucesso="aoSalvarPin"
    />

    <!-- Aviso: proteções sem efeito enquanto não houver PIN -->
    <div v-if="!temPinConfigurado" class="flex items-start gap-2.5 p-3 -mt-2 bg-amber-50 border border-amber-100 rounded-xl">
      <AlertTriangle :size="16" class="text-amber-500 shrink-0 mt-0.5" />
      <p class="text-xs text-amber-700 leading-snug">
        Sem um PIN configurado, as proteções e aprovações abaixo <strong>não têm efeito</strong>.
        Você pode deixá-las marcadas, mas elas só passam a valer depois de definir um PIN.
      </p>
    </div>

    <!-- Seções protegidas -->
    <div class="flex flex-col" :class="{ 'opacity-60': !temPinConfigurado }">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1">Seções Protegidas</p>
      <p class="text-xs text-zinc-500 mb-2">
        Cada seção marcada exigirá o PIN do gerente para ser acessada.
        A seção Segurança é sempre protegida quando há um PIN configurado.
      </p>

      <div
        v-for="secao in SECOES_PROTEGIVEIS"
        :key="secao.id"
        class="flex items-center justify-between py-3 border-b border-zinc-100"
      >
        <p class="text-sm font-medium text-zinc-800">{{ secao.label }}</p>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.secoes_protegidas[secao.id] ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.secoes_protegidas[secao.id] = !form.secoes_protegidas[secao.id]"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.secoes_protegidas[secao.id] ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>
    </div>

    <!-- Vendas -->
    <div class="flex flex-col" :class="{ 'opacity-60': !temPinConfigurado }">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Vendas</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Desconto acima do limite</p>
          <p class="text-xs text-zinc-500 mt-0.5">Pede PIN quando o desconto ultrapassar o máximo configurado</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_desconto_venda ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_desconto_venda = !form.requer_pin_desconto_venda"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_desconto_venda ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Alterar preço de produto cadastrado</p>
          <p class="text-xs text-zinc-500 mt-0.5">OFF = bloqueado; ON = permite com PIN do gerente</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_alterar_preco_venda ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_alterar_preco_venda = !form.requer_pin_alterar_preco_venda"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_alterar_preco_venda ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <!-- Sangria: retirada de dinheiro da gaveta. Suprimento NAO pede PIN de
           proposito -- por dinheiro na gaveta nao cria risco de desvio, e travar
           os dois faria o operador chamar o gerente so para colocar troco. -->
      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Sangria do caixa</p>
          <p class="text-xs text-zinc-500 mt-0.5">Exige PIN para retirar dinheiro da gaveta</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_sangria ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_sangria = !form.requer_pin_sangria"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_sangria ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Cancelar venda finalizada</p>
          <p class="text-xs text-zinc-500 mt-0.5">Exige PIN para cancelar uma venda já finalizada</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_cancelar_venda ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_cancelar_venda = !form.requer_pin_cancelar_venda"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_cancelar_venda ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Reabrir venda cancelada</p>
          <p class="text-xs text-zinc-500 mt-0.5">Exige PIN para reabrir uma venda cancelada</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_reabrir_venda ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_reabrir_venda = !form.requer_pin_reabrir_venda"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_reabrir_venda ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>
    </div>

    <!-- Ordens de Serviço -->
    <div class="flex flex-col" :class="{ 'opacity-60': !temPinConfigurado }">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Ordens de Serviço</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Cancelar OS</p>
          <p class="text-xs text-zinc-500 mt-0.5">Exige PIN para cancelar uma ordem de serviço</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_cancelar_os ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_cancelar_os = !form.requer_pin_cancelar_os"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_cancelar_os ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Reabrir OS finalizada ou cancelada</p>
          <p class="text-xs text-zinc-500 mt-0.5">Exige PIN para reabrir uma OS</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.requer_pin_reabrir_os ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.requer_pin_reabrir_os = !form.requer_pin_reabrir_os"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.requer_pin_reabrir_os ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>
    </div>
  </div>
</template>
