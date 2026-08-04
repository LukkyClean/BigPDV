<script setup lang="ts">
/**
 * @fileoverview Integrações e APIs.
 *
 * O bloco de Nota Fiscal Eletrônica foi removido: era maquete, e emissão de NF-e
 * não está no caminho deste produto nem desta categoria de cliente.
 *
 * PIX guarda apenas a CHAVE. Não há integração bancária aqui e não haverá por
 * ora: o QR do PIX é padrão aberto (BR Code) e se monta offline a partir da
 * chave, sem contrato, credencial ou internet. Por isso não existe segredo a
 * proteger nesta tela — o que se digita aqui é justamente o dado que vai
 * impresso no QR para o cliente ler.
 *
 * A consequência a ter em mente: QR estático COBRA, mas não confirma. O sistema
 * não fica sabendo que o cliente pagou; a conferência segue no app do banco.
 * Conciliação automática exigiria webhook de banco, e o backend roda na rede
 * local da loja — fica para o módulo financeiro.
 */
import { ref, computed, watch } from 'vue'
import { QrCode } from 'lucide-vue-next'

import { useEmpresaQuery } from '@/modules/enterprise/composables/useEmpresaQuery'
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue'

const { data: empresa } = useEmpresaQuery()

function valoresDaEmpresa() {
  return {
    chave_pix: empresa.value?.chave_pix ?? '',
    pix_ativo: empresa.value?.pix_ativo ?? false,
  }
}

// Contrato que o ConfiguracoesModal espera de uma seção funcional.
const form = ref(valoresDaEmpresa())

watch(empresa, () => { form.value = valoresDaEmpresa() })

const isDirty = computed(
  () => JSON.stringify(form.value) !== JSON.stringify(valoresDaEmpresa()),
)

function resetar() {
  form.value = valoresDaEmpresa()
}

defineExpose({ form, isDirty, resetar })

/**
 * Ligar sem chave não faz nada — o QR precisa da chave para existir. Em vez de
 * deixar o usuário salvar uma configuração inerte, o interruptor fica travado
 * até haver o que ativar.
 */
const temChave = computed(() => form.value.chave_pix.trim().length > 0)

watch(temChave, (tem) => {
  if (!tem) form.value.pix_ativo = false
})

function alternarPix() {
  if (!temChave.value) return
  form.value.pix_ativo = !form.value.pix_ativo
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Integrações e APIs</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Conecte o sistema com serviços externos</p>
    </div>

    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">PIX</p>

      <div class="border border-zinc-200 rounded-lg p-4 flex flex-col gap-4">
        <div class="flex items-start gap-2">
          <QrCode :size="16" class="text-zinc-400 shrink-0 mt-0.5" />
          <p class="text-xs text-zinc-500">
            Cadastre a chave que recebe os pagamentos. Na finalização da venda, o sistema
            gera o QR Code já com o valor — o cliente aponta a câmera e paga, sem digitar
            chave nem valor.
          </p>
        </div>

        <BaseInput
          v-model="form.chave_pix"
          label="Chave PIX"
          placeholder="CPF, CNPJ, telefone, e-mail ou chave aleatória"
          maxlength="77"
        />

        <div class="flex items-center justify-between border-t border-zinc-100 pt-3">
          <div>
            <p class="text-sm font-medium text-zinc-800">Exibir QR Code na venda</p>
            <p class="text-xs text-zinc-500 mt-0.5">
              {{ temChave ? 'Mostra o QR ao escolher PIX no pagamento' : 'Cadastre a chave para poder ativar' }}
            </p>
          </div>
          <button
            type="button"
            :disabled="!temChave"
            class="relative w-9 h-4.5 rounded-full shrink-0 transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
            :class="form.pix_ativo ? 'bg-brand-primary' : 'bg-zinc-200'"
            @click="alternarPix"
          >
            <span
              class="absolute top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-all"
              :class="form.pix_ativo ? 'left-4.5' : 'left-0.5'"
            />
          </button>
        </div>

        <p class="text-[11px] text-zinc-400 border-t border-zinc-100 pt-3">
          O QR cobra, mas não confirma: o sistema não fica sabendo que o cliente pagou.
          A conferência continua no aplicativo do banco.
        </p>
      </div>
    </div>
  </div>
</template>
