<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { AlertTriangle, X, Loader2, CheckCircle, Info, Cloud, Calendar } from 'lucide-vue-next'
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import { useToast } from '@/shared/composables/useToast'
import { listarCiclosNuvem, baixarBackupNuvem, prepararRestauracao, confirmarRestauracao } from '@/modules/configuracoes/services/backup.service'
import type { CicloNuvemInfoType, PrepareRestoreResponseType } from '@/modules/configuracoes/types/backup.types'
import { getErrorMessage } from '@/shared/utils/error.utils'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits<{ close: [] }>()

const toast = useToast()

type Etapa = 'selecao' | 'aviso' | 'download' | 'preparacao' | 'decisao' | 'confirmado'

const etapa = ref<Etapa>('selecao')
const ciclos = ref<CicloNuvemInfoType[]>([])
const cicloSelecionado = ref<string | null>(null)
const palavraChave = ref('')
const isProcessando = ref(false)
const isCarregandoCiclos = ref(false)
const prepareResult = ref<PrepareRestoreResponseType | null>(null)

const palavraCorreta = computed(() => palavraChave.value.trim().toUpperCase() === 'RESTAURAR')

watch(() => props.isOpen, async (aberto) => {
  if (aberto) {
    etapa.value = 'selecao'
    cicloSelecionado.value = null
    palavraChave.value = ''
    prepareResult.value = null
    isProcessando.value = false
    await carregarCiclos()
  }
})

async function carregarCiclos() {
  isCarregandoCiclos.value = true
  try {
    ciclos.value = await listarCiclosNuvem()
  } catch (e: any) {
    toast.error('Erro ao buscar backups na nuvem', getErrorMessage(e))
    ciclos.value = []
  } finally {
    isCarregandoCiclos.value = false
  }
}

function selecionarCiclo(ciclo: string) {
  cicloSelecionado.value = ciclo
  palavraChave.value = ''
  etapa.value = 'aviso'
}

function voltarParaSelecao() {
  etapa.value = 'selecao'
  cicloSelecionado.value = null
  palavraChave.value = ''
  prepareResult.value = null
}

async function iniciarRestauracao() {
  if (!cicloSelecionado.value) return
  isProcessando.value = true

  // Etapa 3: Download da nuvem
  etapa.value = 'download'
  try {
    const download = await baixarBackupNuvem(cicloSelecionado.value)
    if (download.status !== 'success') {
      toast.error('Falha ao baixar backup', download.details ?? 'Tente novamente.')
      voltarParaSelecao()
      isProcessando.value = false
      return
    }
  } catch (e: any) {
    toast.error('Erro ao baixar backup da nuvem', getErrorMessage(e))
    voltarParaSelecao()
    isProcessando.value = false
    return
  }

  // Etapa 4: Preparação
  etapa.value = 'preparacao'
  try {
    prepareResult.value = await prepararRestauracao(cicloSelecionado.value)
    etapa.value = 'decisao'
  } catch (e: any) {
    toast.error('Erro ao preparar restauração', getErrorMessage(e))
    voltarParaSelecao()
  } finally {
    isProcessando.value = false
  }
}

async function confirmar() {
  if (!prepareResult.value?.pre_restore_backup || !prepareResult.value?.ciclo) return

  isProcessando.value = true
  try {
    const resultado = await confirmarRestauracao(
      prepareResult.value.ciclo,
      prepareResult.value.pre_restore_backup,
    )
    if (resultado.status === 'confirmed') {
      etapa.value = 'confirmado'
    } else {
      toast.error('Erro ao confirmar restauração', resultado.details ?? 'Tente novamente.')
    }
  } catch (e: any) {
    toast.error('Erro ao confirmar restauração', getErrorMessage(e))
  } finally {
    isProcessando.value = false
  }
}

function formatarCiclo(ciclo: string): string {
  const [ano, mes] = ciclo.split('-')
  const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
  return `${meses[parseInt(mes) - 1]} ${ano}`
}

function formatarData(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' +
    d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Restaurar Backup" size="md" @close="emit('close')">
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100 shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
            <AlertTriangle :size="16" class="text-red-600" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-zinc-900">Restaurar Backup</h2>
            <p class="text-[11px] text-zinc-400 leading-tight">Restaurar dados a partir de um backup na nuvem</p>
          </div>
        </div>
        <button
          type="button"
          class="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X :size="18" />
        </button>
      </div>
    </template>

    <div class="min-h-[300px] flex flex-col justify-center">
      <!-- Etapa 1: Seleção de ciclo -->
      <div v-if="etapa === 'selecao'">
        <!-- Loading -->
        <div v-if="isCarregandoCiclos" class="flex flex-col items-center justify-center gap-3 py-8">
          <Loader2 :size="32" class="text-brand-primary animate-spin" />
          <p class="text-sm text-zinc-600">Buscando backups na nuvem...</p>
        </div>

        <!-- Vazio -->
        <div v-else-if="!ciclos.length" class="flex flex-col items-center justify-center gap-3 py-8 text-zinc-400">
          <Cloud :size="32" />
          <p class="text-sm font-medium text-zinc-600">Nenhum backup na nuvem</p>
          <p class="text-xs text-zinc-400 text-center max-w-[260px]">
            Nenhum backup foi enviado à nuvem ainda. Configure o backup automático para manter cópias seguras.
          </p>
        </div>

        <!-- Lista de ciclos -->
        <div v-else class="flex flex-col gap-2">
          <p class="text-xs font-medium text-zinc-500 mb-1">Selecione o período para restaurar:</p>
          <button
            v-for="ciclo in ciclos"
            :key="ciclo.ciclo"
            type="button"
            class="flex items-center gap-3 px-4 py-3 border border-zinc-200 rounded-lg hover:border-brand-primary/40 hover:bg-brand-primary/4 transition-colors cursor-pointer text-left"
            @click="selecionarCiclo(ciclo.ciclo)"
          >
            <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
              <Calendar :size="14" class="text-blue-600" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-zinc-800">{{ formatarCiclo(ciclo.ciclo) }}</p>
              <p class="text-[11px] text-zinc-500">
                {{ ciclo.quantidade_backups }} backup(s)
                <span class="text-zinc-300 mx-1">|</span>
                Último envio: {{ formatarData(ciclo.ultimo_envio) }}
              </p>
            </div>
          </button>
        </div>
      </div>

      <!-- Etapa 2: Aviso -->
      <div v-else-if="etapa === 'aviso'" class="flex flex-col gap-4">
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
          <div class="flex gap-3">
            <AlertTriangle :size="20" class="text-red-500 shrink-0 mt-0.5" />
            <div>
              <p class="text-sm font-medium text-red-800">Atenção: Ação Destrutiva</p>
              <p class="text-xs text-red-700 mt-1 leading-relaxed">
                A restauração irá <strong>substituir todos os dados atuais</strong> do sistema pelos dados do backup
                de <strong>{{ formatarCiclo(cicloSelecionado!) }}</strong>.
                Um backup de segurança dos dados atuais será criado automaticamente antes da restauração.
                O aplicativo precisará ser reiniciado para aplicar as alterações.
              </p>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-zinc-600">
            Digite <strong class="text-red-600">RESTAURAR</strong> para confirmar
          </label>
          <input
            v-model="palavraChave"
            type="text"
            placeholder="RESTAURAR"
            class="border border-zinc-200 rounded-lg px-3 py-2.5 text-sm text-zinc-700 outline-none focus:border-red-400 transition-colors uppercase tracking-widest"
          />
        </div>
      </div>

      <!-- Etapa 3: Download -->
      <div v-else-if="etapa === 'download'" class="flex flex-col items-center justify-center gap-3 py-8">
        <Loader2 :size="32" class="text-brand-primary animate-spin" />
        <p class="text-sm text-zinc-600">Baixando backup da nuvem...</p>
        <p class="text-xs text-zinc-400">Isso pode levar alguns minutos</p>
      </div>

      <!-- Etapa 4: Preparação -->
      <div v-else-if="etapa === 'preparacao'" class="flex flex-col items-center justify-center gap-3 py-8">
        <Loader2 :size="32" class="text-brand-primary animate-spin" />
        <p class="text-sm text-zinc-600">Preparando restauração...</p>
        <p class="text-xs text-zinc-400">Validando integridade e criando backup de segurança</p>
      </div>

      <!-- Etapa 5: Decisão -->
      <div v-else-if="etapa === 'decisao' && prepareResult" class="flex flex-col gap-4">
        <!-- Iguais -->
        <div v-if="prepareResult.status === 'equals'" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex gap-3">
            <Info :size="20" class="text-blue-500 shrink-0 mt-0.5" />
            <div>
              <p class="text-sm font-medium text-blue-800">Dados já estão atualizados</p>
              <p class="text-xs text-blue-700 mt-1">{{ prepareResult.details }}</p>
            </div>
          </div>
        </div>

        <!-- Outdated -->
        <div v-else-if="prepareResult.status === 'restore_backup_outdated'" class="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div class="flex gap-3">
            <AlertTriangle :size="20" class="text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p class="text-sm font-medium text-amber-800">Backup mais antigo que os dados atuais</p>
              <p class="text-xs text-amber-700 mt-1 leading-relaxed">{{ prepareResult.details }}</p>
              <p class="text-xs text-amber-600 mt-2 font-medium">Deseja continuar mesmo assim?</p>
            </div>
          </div>
        </div>

        <!-- Ready -->
        <div v-else class="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
          <div class="flex gap-3">
            <CheckCircle :size="20" class="text-emerald-500 shrink-0 mt-0.5" />
            <div>
              <p class="text-sm font-medium text-emerald-800">Pronto para restaurar</p>
              <p class="text-xs text-emerald-700 mt-1">{{ prepareResult.details }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Etapa 6: Confirmado -->
      <div v-else-if="etapa === 'confirmado'" class="flex flex-col items-center justify-center gap-3 py-8">
        <div class="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center">
          <CheckCircle :size="24" class="text-emerald-600" />
        </div>
        <p class="text-sm font-medium text-zinc-800">Restauração confirmada</p>
        <p class="text-xs text-zinc-500 text-center leading-relaxed max-w-[280px]">
          Reinicie o aplicativo para aplicar a restauração. Os dados atuais foram salvos em um backup de segurança.
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <!-- Etapa 1: Seleção -->
        <template v-if="etapa === 'selecao'">
          <BaseButton variant="ghost" size="sm" @click="emit('close')">
            Fechar
          </BaseButton>
        </template>

        <!-- Etapa 2: Aviso -->
        <template v-else-if="etapa === 'aviso'">
          <BaseButton variant="ghost" size="sm" @click="voltarParaSelecao">
            Voltar
          </BaseButton>
          <BaseButton variant="danger" size="sm" :disabled="!palavraCorreta" @click="iniciarRestauracao">
            Prosseguir
          </BaseButton>
        </template>

        <!-- Etapas 3, 4 (loading) -->
        <template v-else-if="etapa === 'download' || etapa === 'preparacao'">
          <BaseButton variant="ghost" size="sm" disabled>
            Processando...
          </BaseButton>
        </template>

        <!-- Etapa 5: Decisão -->
        <template v-else-if="etapa === 'decisao'">
          <BaseButton variant="ghost" size="sm" @click="voltarParaSelecao">
            Cancelar
          </BaseButton>
          <BaseButton
            v-if="prepareResult?.status !== 'equals'"
            variant="danger"
            size="sm"
            :isLoading="isProcessando"
            @click="confirmar"
          >
            Confirmar Restauração
          </BaseButton>
        </template>

        <!-- Etapa 6: Confirmado -->
        <template v-else-if="etapa === 'confirmado'">
          <BaseButton variant="primary" size="sm" @click="emit('close')">
            Fechar
          </BaseButton>
        </template>
      </div>
    </template>
  </BaseModal>
</template>
