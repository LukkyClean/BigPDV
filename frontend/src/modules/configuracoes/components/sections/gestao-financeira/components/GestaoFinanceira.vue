<script setup lang="ts">
/**
 * Quando o dinheiro de cada forma de pagamento cai na conta.
 *
 * O PROBLEMA QUE ISTO RESOLVE: dinheiro de cartão não está na conta no dia da
 * venda — a maquininha deposita depois. Até 02/09/2026 o sistema tratava todo
 * recebimento como dinheiro que já entrou, e o Fluxo de Caixa mostrava na conta
 * um valor que só chegaria amanhã.
 *
 * SALVA SOZINHA, campo a campo, e por isso esta seção fica fora de
 * `secoesFuncionais` no modal (não tem botão "Aplicar"). Cada forma é um
 * registro independente: juntá-las num formulário único faria salvar o cartão
 * gravar por cima do PIX que outro terminal acabou de mudar.
 *
 * ZERO É O PADRÃO e zero é o comportamento de sempre. Quem não mexer aqui não
 * vê diferença nenhuma — condição para isto poder entrar numa versão que já
 * roda em três lojas.
 */
import { computed, ref, watch } from 'vue'
import { Info } from 'lucide-vue-next'

import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue'
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue'
import { useContasBancariasQuery } from '@/modules/financeiro/shared/composables/useFinanceiro'

import { useFormasPagamentoQuery } from '../../../../composables/queries/useFormasPagamentoQuery'
import { useAtualizarFormaPagamentoMutation } from '../../../../composables/mutates/useAtualizarFormaPagamentoMutation'

const { data: formas, isLoading } = useFormasPagamentoQuery()
const { data: contas } = useContasBancariasQuery()
const atualizar = useAtualizarFormaPagamentoMutation()

/**
 * Rascunho local por forma, chaveado por id.
 *
 * Não se escreve direto no objeto da query: o cache do TanStack é a verdade do
 * servidor, e editá-lo à mão faria a tela mostrar como salvo um número que
 * ainda não saiu daqui.
 */
const dias = ref<Record<number, number>>({})
const conta = ref<Record<number, number>>({})

watch(
  formas,
  (lista) => {
    if (!lista) return
    const d: Record<number, number> = {}
    const c: Record<number, number> = {}
    for (const forma of lista) {
      d[forma.id] = forma.dias_para_receber ?? 0
      c[forma.id] = forma.conta_bancaria_id ?? 0
    }
    dias.value = d
    conta.value = c
  },
  { immediate: true },
)

const opcoesConta = computed(() => [
  { value: 0, label: 'Conta principal' },
  ...(contas.value ?? []).map((c) => ({ value: c.id, label: c.nome })),
])

/** Ativas primeiro; dentro de cada grupo, a ordem que veio do servidor. */
const ordenadas = computed(() =>
  [...(formas.value ?? [])].sort((a, b) => Number(b.ativo) - Number(a.ativo)),
)

function frase(id: number): string {
  const d = Number(dias.value[id] ?? 0)
  if (d <= 0) return 'Entra no caixa na hora da venda.'
  if (d === 1) return 'Entra no caixa no dia seguinte, sozinho.'
  return `Entra no caixa ${d} dias depois, sozinho.`
}

function salvarDias(id: number) {
  const valor = Math.max(0, Math.min(90, Math.trunc(Number(dias.value[id]) || 0)))
  dias.value[id] = valor
  const atual = formas.value?.find((f) => f.id === id)
  if ((atual?.dias_para_receber ?? 0) === valor) return
  atualizar.mutate({ id, dados: { dias_para_receber: valor } })
}

function salvarConta(id: number) {
  const valor = Number(conta.value[id] ?? 0)
  const atual = formas.value?.find((f) => f.id === id)
  if ((atual?.conta_bancaria_id ?? 0) === valor) return
  // Zero limpa a escolha e volta para a principal — `undefined` já significa
  // "não mexe" no PATCH parcial, então sobrou o zero para desfazer.
  atualizar.mutate({ id, dados: { conta_bancaria_id: valor } })
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-semibold text-gray-800">Formas de recebimento</h3>
      <p class="mt-1 max-w-2xl text-sm text-gray-500">
        Diga em quantos dias o dinheiro de cada forma cai na sua conta. O Fluxo de Caixa passa
        a mostrar essa entrada no dia certo, em vez de somar hoje um dinheiro que ainda está
        na maquininha — e no dia ele entra sozinho, sem você precisar confirmar.
      </p>
    </div>

    <div class="flex gap-2.5 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
      <Info :size="16" class="mt-0.5 shrink-0 text-blue-500" />
      <p class="text-xs text-blue-800">
        Deixe <strong>0</strong> no que entra na hora: dinheiro, PIX, débito que cai na mesma
        hora. Só o que demora precisa de prazo.
      </p>
    </div>

    <p v-if="isLoading" class="text-sm text-gray-500">Carregando…</p>

    <ul v-else class="flex flex-col divide-y divide-gray-100 rounded-2xl border border-gray-100 bg-white">
      <li
        v-for="forma in ordenadas"
        :key="forma.id"
        class="flex flex-wrap items-end gap-4 px-5 py-4"
        :class="!forma.ativo && 'bg-gray-50'"
      >
        <div class="min-w-40 flex-1">
          <p class="text-sm font-medium" :class="forma.ativo ? 'text-gray-800' : 'text-gray-400'">
            {{ forma.nome }}
            <span v-if="!forma.ativo" class="ml-1 text-xs font-normal">(desativada)</span>
          </p>
          <p class="mt-0.5 text-xs" :class="dias[forma.id] > 0 ? 'text-emerald-600' : 'text-gray-400'">
            {{ frase(forma.id) }}
          </p>
        </div>

        <div class="w-28">
          <!-- type="text" + inputmode: o type="number" do BaseInput ja mordeu
               esta base antes (vírgula decimal virava campo vazio). Aqui é
               inteiro, mas a regra da casa vale igual. -->
          <BaseInput
            v-model="dias[forma.id]"
            label="Cai em (dias)"
            type="text"
            inputmode="numeric"
            @blur="salvarDias(forma.id)"
            @keyup.enter="salvarDias(forma.id)"
          />
        </div>

        <div class="w-52">
          <BaseSelect
            v-model="conta[forma.id]"
            label="Cai na conta"
            :options="opcoesConta"
            @update:model-value="salvarConta(forma.id)"
          />
        </div>
      </li>
    </ul>

    <div class="flex flex-col gap-1.5 text-xs text-gray-400">
      <p>
        Com prazo declarado, a venda vira uma cobrança a receber e aparece em
        <strong class="text-gray-500">Vai entrar</strong> no Fluxo de Caixa. No dia, ela entra
        no caixa sozinha.
      </p>
      <p>
        Se o valor depositado vier diferente do previsto — a taxa da maquininha —, é na tela de
        <strong class="text-gray-500">Conciliação</strong> que você acerta, conferindo o lote do
        dia contra o extrato.
      </p>
      <p>
        Isto <strong class="text-gray-500">não vale para fiado</strong>: venda a prazo combinada
        com o cliente nunca entra sozinha, porque cliente não paga por agendamento.
      </p>
    </div>
  </div>
</template>
