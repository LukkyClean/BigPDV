<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Component } from 'vue'
import {
  Settings,
  X,
  Tag,
  Package,
  ClipboardList,
  Users,
  Plug,
  Printer,
  Monitor,
  HardDrive,
  Headphones,
  ShieldCheck,
} from 'lucide-vue-next'

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue'
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue'

import { useConfiguracoesModal } from '../composables/useConfiguracoesModal'
import { useSalvarConfiguracoesClientesMutation } from '../composables/mutates/useSalvarConfiguracoesClientesMutation'
import { useSalvarConfiguracoesEstoqueMutation } from '../composables/mutates/useSalvarConfiguracoesEstoqueMutation'
import { useSalvarConfiguracoesOSMutation } from '../composables/mutates/useSalvarConfiguracoesOSMutation'
import { useSalvarConfiguracoesVendasMutation } from '../composables/mutates/useSalvarConfiguracoesVendasMutation'
import { useSalvarConfiguracoesSegurancaMutation } from '../composables/mutates/useSalvarConfiguracoesSegurancaMutation'
import { useUpdateEmpresaMutation } from '@/modules/enterprise/composables/useEmpresaQuery'
import { guardarCorLocalmente } from '@/shared/theme/aplicar'
import type { SecaoConfiguracao, SecaoExposta, SecaoId } from '../types/configuracoes.types'
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao'
import { useConfirmacao } from '@/shared/composables/useConfirmacao'
import { verificarPinSeguranca } from '../services/configuracoes.service'
import { sincronizarServidorImpressao } from '@/shared/services/impressao.service'
import { useToast } from '@/shared/composables/useToast'
import { storeToRefs } from 'pinia'
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store'
import { useImpressaoStore } from '@/shared/stores/impressao.store'

import RegrasDeVendas from './sections/regras-de-vendas/components/RegrasDeVendas.vue'
import Seguranca from './sections/seguranca/components/Seguranca.vue'
import ProdutosEstoque from './sections/produtos-estoque/components/ProdutosEstoque.vue'
import OrdensDeServico from './sections/ordens-de-servico/components/OrdensDeServico.vue'
import ClientesCadastro from './sections/clientes-cadastro/components/ClientesCadastro.vue'
import IntegracoesAPIs from './sections/integracoes-apis/components/IntegracoesAPIs.vue'
import ImpressaoPeriferico from './sections/impressao/components/ImpressaoPeriferico.vue'
import FormatosExibicao from './sections/formatos-exibicao/components/FormatosExibicao.vue'
import BackupDados from './sections/backup-dados/components/BackupDados.vue'
import Suporte from './sections/suporte/components/Suporte.vue'

const props = defineProps<{ isOpen: boolean; secaoInicial?: SecaoId }>()
const emit = defineEmits<{ close: [] }>()

const { secaoAtiva, irPara } = useConfiguracoesModal()
const { mutate: salvarClientes, isPending: isPendingClientes } = useSalvarConfiguracoesClientesMutation()
const { mutate: salvarEstoque, mutateAsync: salvarEstoqueAsync, isPending: isPendingEstoque } = useSalvarConfiguracoesEstoqueMutation()
const { mutate: salvarOS, isPending: isPendingOS } = useSalvarConfiguracoesOSMutation()
const { mutateAsync: salvarVendasAsync, isPending: isPendingVendas } = useSalvarConfiguracoesVendasMutation()
const { mutate: salvarSeguranca, isPending: isPendingSeguranca } = useSalvarConfiguracoesSegurancaMutation()
// O tema mora na empresa (junto do logo), então reaproveita a mutation dela —
// que já invalida o cache e sincroniza o auth store.
const { mutate: salvarTema, isPending: isPendingTema } = useUpdateEmpresaMutation()

const configuracoesStore = useConfiguracoesStore()
const impressaoStore = useImpressaoStore()
const { secoesProtegidas, temPinConfigurado } = storeToRefs(configuracoesStore)
const gerenteConfig = useGerenteAprovacao()
const confirmacao = useConfirmacao()
const toast = useToast()

function precisaPin(secaoId: SecaoId): boolean {
  if (!temPinConfigurado.value) return false
  if (secaoId === 'seguranca') return true
  return secoesProtegidas.value.includes(secaoId)
}

async function verificarPinComRetry(pin: string): Promise<boolean> {
  try {
    gerenteConfig.isLoading.value = true
    await verificarPinSeguranca(pin)
    return true
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    if (detail === 'PIN_GERENTE_INVALIDO') {
      toast.error('PIN do gerente inválido. Tente novamente.')
      const novoPIN = await gerenteConfig.pedirPin()
      if (novoPIN) return verificarPinComRetry(novoPIN)
    }
    return false
  } finally {
    gerenteConfig.isLoading.value = false
  }
}

async function navegarParaSecao(secaoId: SecaoId): Promise<void> {
  if (secaoId === secaoAtiva.value) return
  if (!(await confirmarDescarteSeNecessario())) return
  if (!precisaPin(secaoId)) {
    irPara(secaoId)
    return
  }
  const pin = await gerenteConfig.pedirPin()
  if (!pin) return
  if (await verificarPinComRetry(pin)) irPara(secaoId)
}

const isPending = computed(() => isPendingClientes.value || isPendingEstoque.value || isPendingOS.value || isPendingVendas.value || isPendingSeguranca.value || isPendingTema.value)

const activeComponentRef = ref<SecaoExposta | null>(null)
const isDirtyAtivo = computed(() => activeComponentRef.value?.isDirty === true)

async function confirmarDescarteSeNecessario(): Promise<boolean> {
  if (!isDirtyAtivo.value) return true
  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Descartar alterações?',
    descricao: `Você tem alterações não salvas em <strong>${labelSecaoAtiva.value}</strong>. Se continuar, elas serão perdidas.`,
    confirmLabel: 'Descartar',
    cancelLabel: 'Continuar editando',
    variant: 'warning',
  })
  if (ok) activeComponentRef.value?.resetar?.()
  return ok
}

async function fecharModal(): Promise<void> {
  if (isPending.value) return
  if (!(await confirmarDescarteSeNecessario())) return
  emit('close')
}

watch(() => props.isOpen, (aberto) => {
  if (aberto) {
    // Garante dados frescos mesmo se o carregamento do boot tiver falhado
    configuracoesStore.carregarConfiguracoes()
    irPara(props.secaoInicial ?? 'regras-de-vendas')
  }
})

const secoesFuncionais: SecaoId[] = ['seguranca', 'clientes-cadastro', 'produtos-estoque', 'ordens-de-servico', 'regras-de-vendas', 'impressao', 'formatos-exibicao', 'integracoes-apis']
const secaoFuncional = computed(() => secoesFuncionais.includes(secaoAtiva.value))

async function salvar(): Promise<void> {
  const comp = activeComponentRef.value
  if (!comp?.form || !isDirtyAtivo.value) return

  const ok = await confirmacao.pedirConfirmacao({
    titulo: `Aplicar alterações de ${labelSecaoAtiva.value}?`,
    descricao: `As alterações de <strong>${labelSecaoAtiva.value}</strong> serão aplicadas imediatamente.`,
    confirmLabel: 'Aplicar',
    variant: 'warning',
  })
  if (!ok) return

  const fecharComDelay = () => setTimeout(() => emit('close'), 600)
  const fecharAposSalvar = { onSuccess: fecharComDelay }

  switch (secaoAtiva.value) {
    case 'clientes-cadastro':
      salvarClientes(comp.form as any, fecharAposSalvar)
      break
    case 'produtos-estoque':
      salvarEstoque(comp.form as any, fecharAposSalvar)
      break
    case 'ordens-de-servico':
      salvarOS(comp.form as any, fecharAposSalvar)
      break
    case 'seguranca':
      salvarSeguranca(comp.form as any, fecharAposSalvar)
      break
    case 'impressao':
      // Config local deste PC (localStorage) — sem chamada ao backend
      impressaoStore.salvar(comp.form as any)
      try {
        await sincronizarServidorImpressao(impressaoStore.config)
      } catch (error: any) {
        toast.warning('Configuração salva, mas o compartilhamento falhou', String(error))
      }
      toast.success('Configurações de impressão salvas!')
      fecharComDelay()
      break
    case 'formatos-exibicao': {
      // Só o tema é gravável aqui (data e hora são informativos). A cor mora na
      // empresa, junto do logo, e o PUT /empresas/ já exige master — a regra de
      // "só o dono decide a identidade visual" vem da rota, não da tela.
      const { cor_tema } = comp.form as { cor_tema: string | null }
      salvarTema({ data: { cor_tema } }, {
        // A mutation de empresa já emite o toast de sucesso e invalida o cache.
        onSuccess: () => {
          // Guardar ANTES de recarregar: é daqui que o boot tira a cor, e é o que
          // faz a tela de login já abrir colorida.
          guardarCorLocalmente(cor_tema)

          // Recarrega ao salvar. É rede de segurança, não a correção: a prévia ao
          // vivo continua sendo reativa (não dá para recarregar a cada movimento
          // do mouse). O reload existe porque `<canvas>` não reage a CSS — o
          // gráfico lê a cor uma vez ao montar — e garante que QUALQUER coisa que
          // tenha capturado uma cor na montagem apareça correta, inclusive o que
          // ainda não mapeamos.
          //
          // Custo aceito: perde-se o cache do TanStack e o toast. Tolerável porque
          // trocar o tema é ação rara, feita pelo dono, a partir de um modal de
          // configuração — não há trabalho em andamento para perder.
          setTimeout(() => window.location.reload(), 600)
        },
      })
      break
    }
    case 'integracoes-apis': {
      // A chave PIX mora na empresa, como o logo e a cor: dado de identidade, não
      // regra de negócio. Reaproveita a mutation dela, que já exige master.
      const { chave_pix, pix_ativo } = comp.form as { chave_pix: string; pix_ativo: boolean }
      salvarTema({ data: { chave_pix: chave_pix.trim() || null, pix_ativo } }, fecharAposSalvar)
      break
    }
    case 'regras-de-vendas': {
      const { vendas, estoque } = comp.form as { vendas: Record<string, unknown>; estoque: Record<string, unknown> }
      const resultados = await Promise.allSettled([
        salvarVendasAsync(vendas as any),
        salvarEstoqueAsync(estoque as any),
      ])
      if (resultados.every((r) => r.status === 'fulfilled')) fecharComDelay()
      break
    }
  }
}

const secoes: SecaoConfiguracao[] = [
  { id: 'seguranca',         label: 'Segurança',             icone: ShieldCheck },
  { id: 'regras-de-vendas',  label: 'Regras de Vendas',      icone: Tag },
  { id: 'produtos-estoque',  label: 'Produtos e Estoque',    icone: Package },
  { id: 'ordens-de-servico', label: 'Ordens de Serviço',     icone: ClipboardList },
  { id: 'clientes-cadastro', label: 'Clientes e Cadastro',   icone: Users },
  { id: 'integracoes-apis',  label: 'Integrações e APIs',    icone: Plug },
  { id: 'impressao',         label: 'Impressão e Periféricos', icone: Printer },
  { id: 'formatos-exibicao', label: 'Formatos e Exibição',   icone: Monitor },
  { id: 'backup-dados',      label: 'Backup dos Dados',      icone: HardDrive },
  { id: 'suporte',           label: 'Suporte',               icone: Headphones },
]

const componenteMap: Record<SecaoId, Component> = {
  'seguranca':         Seguranca,
  'regras-de-vendas':  RegrasDeVendas,
  'produtos-estoque':  ProdutosEstoque,
  'ordens-de-servico': OrdensDeServico,
  'clientes-cadastro': ClientesCadastro,
  'integracoes-apis':  IntegracoesAPIs,
  'impressao':         ImpressaoPeriferico,
  'formatos-exibicao': FormatosExibicao,
  'backup-dados':      BackupDados,
  'suporte':           Suporte,
}

const componenteAtivo = computed(() => componenteMap[secaoAtiva.value])
const labelSecaoAtiva = computed(() => secoes.find((s) => s.id === secaoAtiva.value)?.label ?? '')
</script>

<template>
  <GerenteAprovacaoModal
    :is-open="gerenteConfig.isOpen.value"
    :is-loading="gerenteConfig.isLoading.value"
    @confirmar="gerenteConfig.confirmar"
    @cancelar="gerenteConfig.cancelar"
  />
  <BaseConfirmModal
    :is-open="confirmacao.isOpen.value"
    :title="confirmacao.opcoes.value.titulo"
    :description="confirmacao.opcoes.value.descricao"
    :confirm-label="confirmacao.opcoes.value.confirmLabel"
    :cancel-label="confirmacao.opcoes.value.cancelLabel"
    :variant="confirmacao.opcoes.value.variant"
    overlay
    @confirm="confirmacao.confirmar"
    @close="confirmacao.cancelar"
  />
  <BaseModal :is-open="isOpen" size="xl" title="Configurações Gerais" @close="fecharModal">
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100 shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 bg-zinc-100 rounded-lg flex items-center justify-center">
            <Settings :size="16" class="text-zinc-600" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-zinc-900">Configurações Gerais</h2>
            <p class="text-[11px] text-zinc-400 leading-tight">Gerencie as configurações do sistema</p>
          </div>
        </div>
        <button
          type="button"
          class="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
          @click="fecharModal"
        >
          <X :size="18" />
        </button>
      </div>
    </template>

    <!-- Layout sidebar + conteúdo -->
    <div class="-mx-6 -my-6 flex overflow-hidden" style="height: 560px">

      <!-- Sidebar -->
      <nav class="w-52 border-r border-zinc-100 py-2 flex flex-col overflow-y-auto shrink-0 no-scrollbar">
        <p class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest px-4 mb-1.5">
          Painel do Sistema
        </p>

        <button
          v-for="secao in secoes"
          :key="secao.id"
          type="button"
          :class="[
            'w-full flex items-center gap-2.5 px-4 py-2 text-left transition-colors cursor-pointer',
            secao.id === 'suporte' ? 'mt-1 border-t border-zinc-100 pt-3' : '',
            secaoAtiva === secao.id
              ? 'bg-brand-primary/8 text-brand-primary'
              : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-800',
          ]"
          @click="navegarParaSecao(secao.id)"
        >
          <component
            :is="secao.icone"
            :size="14"
            :class="secaoAtiva === secao.id ? 'text-brand-primary' : 'text-zinc-400'"
          />
          <span class="text-xs font-medium truncate">{{ secao.label }}</span>
        </button>
      </nav>

      <!-- Área de conteúdo -->
      <div class="flex-1 overflow-y-auto p-6 no-scrollbar">
        <component
          :is="componenteAtivo"
          ref="activeComponentRef"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <BaseButton variant="ghost" size="sm" :disabled="isPending" @click="fecharModal">
          Cancelar
        </BaseButton>
        <BaseButton variant="primary" size="sm" :isLoading="isPending" :disabled="!secaoFuncional || isPending || !isDirtyAtivo" @click="salvar">
          Salvar Alterações
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
.no-scrollbar {
  scrollbar-width: none;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
</style>
