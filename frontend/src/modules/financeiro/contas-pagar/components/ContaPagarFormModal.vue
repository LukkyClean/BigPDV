<script setup lang="ts">
/**
 * Cadastro e edição de uma conta a pagar.
 *
 * Conta já PAGA não chega aqui: o backend recusa a edição, porque o valor já
 * virou lançamento no livro e mexer no documento faria a despesa do relatório
 * discordar do movimento. Para corrigir, estorna-se primeiro.
 */
import { computed, ref, watch } from 'vue';
import { X } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';
import { useToast } from '@/shared/composables/useToast';

import {
  useAtualizarContaPagar,
  useCriarContaPagar,
  usePlanoContasQuery,
} from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ aberto: boolean; conta?: ContaPagar | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const { data: categorias } = usePlanoContasQuery(true);
const criar = useCriarContaPagar();
const atualizar = useAtualizarContaPagar();

const editando = computed(() => !!props.conta);

const descricao = ref('');
// Em REAIS aqui, porque é o que o BaseMoneyInput manipula; a conversão para
// centavos acontece num ponto só, no envio.
const valorReais = ref(0);
const vencimento = ref('');
const planoContaId = ref<string | number>('');
const recorrente = ref(false);
const observacao = ref('');

const opcoesCategoria = computed(() => [
  { value: '', label: 'Sem categoria' },
  ...(categorias.value ?? []).map((c) => ({ value: c.id, label: c.nome })),
]);

function hojeLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// Repovoa a cada abertura. Sem isto, abrir para editar depois de ter criado
// deixaria os campos da conta anterior na tela.
watch(
  () => [props.aberto, props.conta] as const,
  ([aberto]) => {
    if (!aberto) return;
    const c = props.conta;
    descricao.value = c?.descricao ?? '';
    valorReais.value = c ? c.valor / 100 : 0;
    vencimento.value = c?.vencimento ?? hojeLocal();
    planoContaId.value = c?.plano_conta_id ?? '';
    recorrente.value = c?.recorrente ?? false;
    observacao.value = c?.observacao ?? '';
  },
  { immediate: true },
);

const salvando = computed(() => criar.isPending.value || atualizar.isPending.value);

const podeSalvar = computed(
  () => !!descricao.value.trim() && valorReais.value > 0 && !!vencimento.value,
);

function salvar() {
  if (!podeSalvar.value) return;

  const payload = {
    descricao: descricao.value.trim(),
    // Arredonda no fim: 12.34 * 100 dá 1233.9999... em ponto flutuante, e sem
    // o round a conta entraria um centavo menor.
    valor: Math.round(valorReais.value * 100),
    vencimento: vencimento.value,
    plano_conta_id: planoContaId.value === '' ? null : Number(planoContaId.value),
    recorrente: recorrente.value,
    observacao: observacao.value.trim() || null,
  };

  const aoErrar = (e: any) =>
    toast.error(e?.response?.data?.detail ?? 'Não foi possível salvar a conta');

  if (editando.value && props.conta) {
    atualizar.mutate(
      { id: props.conta.id, payload },
      { onSuccess: () => emit('fechar'), onError: aoErrar },
    );
  } else {
    criar.mutate(payload, { onSuccess: () => emit('fechar'), onError: aoErrar });
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="aberto"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click.self="emit('fechar')"
    >
      <div class="w-full max-w-lg rounded-2xl bg-white shadow-xl">
        <header class="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 class="text-lg font-bold text-gray-800">
            {{ editando ? 'Editar conta' : 'Nova conta a pagar' }}
          </h2>
          <button type="button" class="text-gray-400 hover:text-gray-600 cursor-pointer" @click="emit('fechar')" aria-label="Fechar">
            <X :size="20" />
          </button>
        </header>

        <form class="flex flex-col gap-4 px-6 py-5" @submit.prevent="salvar">
          <BaseInput v-model="descricao" label="Descrição" placeholder="Ex.: Aluguel de setembro" required />

          <div class="grid gap-4 sm:grid-cols-2">
            <BaseMoneyInput v-model="valorReais" label="Valor" />
            <BaseInput v-model="vencimento" type="date" label="Vencimento" required />
          </div>

          <BaseSelect v-model="planoContaId" :options="opcoesCategoria" label="Categoria" placeholder="Sem categoria" />

          <BaseCheckbox v-model="recorrente" label="Repete todo mês" />
          <p class="-mt-2 text-xs text-gray-400">
            Ao dar baixa, a conta do mês seguinte é criada automaticamente com o valor previsto.
          </p>

          <BaseInput v-model="observacao" label="Observação" placeholder="Opcional" />

          <footer class="mt-2 flex justify-end gap-3">
            <BaseButton type="button" variant="secondary" @click="emit('fechar')">Cancelar</BaseButton>
            <BaseButton type="submit" variant="primary" :disabled="!podeSalvar || salvando">
              {{ salvando ? 'Salvando…' : 'Salvar' }}
            </BaseButton>
          </footer>
        </form>
      </div>
    </div>
  </Teleport>
</template>
