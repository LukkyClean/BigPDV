// ============================================================================
// COMPONENTE: ModalMovimentacaoEstoque
// PROJETO: Start Big - Gestão de Hardware
// RESPONSABILIDADE: Registrar entradas, saídas e ajustes de inventário.
// FUNCIONALIDADES: 
//   - Cálculo automático de estoque atual via computed.
//   - Feedback visual dinâmico (Badges) conforme o tipo de operação.
//   - Validação de quantidade mínima e tratamento de erros de API.
// ============================================================================
<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { ArrowDownCircle, ArrowUpCircle, SlidersHorizontal } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useCreateMovimentacaoMutation } from '../composables/useMovimentacoesQuery';
import type { MovimentacaoTipo, ProdutoRead } from '../types/products.types';

interface Props {
  isOpen: boolean;
  produtos: ProdutoRead[];
  initialProdutoId?: number;
  initialTipo?: MovimentacaoTipo;
}

const props = defineProps<Props>();
const emit = defineEmits<{ (e: 'close'): void }>();

const mutation = useCreateMovimentacaoMutation();

const produtoId = ref<string>('');
const tipo = ref<MovimentacaoTipo>('ENTRADA');
const quantidade = ref<number | ''>('');
// Valor pago por unidade nesta compra, em reais (vira centavos no envio).
// É este número que recalcula o custo médio do produto — e sem ele o relatório
// de lucro não tem de onde tirar o custo da peça.
const valorPago = ref<string>('');
const observacao = ref('');
const erro = ref('');

// Pré-preenche quando aberto com produto/tipo específico
watch(() => props.isOpen, (open) => {
  if (open) {
    produtoId.value = props.initialProdutoId ? String(props.initialProdutoId) : '';
    tipo.value = props.initialTipo ?? 'ENTRADA';
    quantidade.value = '';
    valorPago.value = '';
    observacao.value = '';
    erro.value = '';
  }
});

const produtoOptions = computed<SelectOption[]>(() =>
  props.produtos
    .filter((p) => p.ativo)
    .map((p) => ({ value: String(p.id), label: p.nome })),
);

const tipoOptions: SelectOption[] = [
  { value: 'ENTRADA', label: 'Entrada (adicionar ao estoque)' },
  { value: 'SAIDA', label: 'Saída (retirar do estoque)' },
  { value: 'AJUSTE', label: 'Ajuste (definir quantidade final)' },
];

const tipoBadge = computed(() => {
  if (tipo.value === 'ENTRADA') return { icon: ArrowDownCircle, class: 'text-brand-primary bg-brand-primary/10', label: 'Entrada' };
  if (tipo.value === 'SAIDA') return { icon: ArrowUpCircle, class: 'text-red-600 bg-red-50', label: 'Saída' };
  return { icon: SlidersHorizontal, class: 'text-amber-600 bg-amber-50', label: 'Ajuste' };
});

const produtoSelecionado = computed(() =>
  props.produtos.find((p) => String(p.id) === produtoId.value),
);

// Custo que o sistema conhece hoje: a média calculada, ou o preço de referência
// do cadastro enquanto nunca houve compra registrada com valor pago.
const custoConhecido = computed<number | null>(() => {
  const estoque = produtoSelecionado.value?.estoque;
  if (!estoque) return null;
  return estoque.custo_medio ?? estoque.valor_entrada ?? null;
});

// Só a compra recalcula o custo. Numa devolução (que também é entrada), o campo
// fica de fora de propósito: devolver não é comprar, e preencher ali mexeria na
// média sem que nada tenha sido pago.
const pedeValorPago = computed(() => tipo.value === 'ENTRADA');

// Prévia da média resultante — deixa visível, antes de gravar, que comprar mais
// caro não joga o custo todo para o preço novo.
const novaMediaPrevista = computed<number | null>(() => {
  if (!pedeValorPago.value) return null;
  const pago = paraCentavos(valorPago.value);
  const qtd = Number(quantidade.value);
  if (pago === undefined || !qtd || qtd < 1) return null;

  const anterior = Math.max(0, produtoSelecionado.value?.estoque.quantidade ?? 0);
  const custoAnterior = custoConhecido.value;
  if (custoAnterior == null || anterior === 0) return pago;
  return Math.round((anterior * custoAnterior + qtd * pago) / (anterior + qtd));
});

function paraCentavos(valor: string): number | undefined {
  const limpo = valor.replace(/\s/g, '').replace(',', '.');
  if (!limpo) return undefined;
  const numero = Number(limpo);
  if (!Number.isFinite(numero) || numero < 0) return undefined;
  return Math.round(numero * 100);
}

function formatarMoeda(centavos: number): string {
  return (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function resetForm() {
  produtoId.value = '';
  tipo.value = 'ENTRADA';
  quantidade.value = '';
  valorPago.value = '';
  observacao.value = '';
  erro.value = '';
}

function handleClose() {
  resetForm();
  emit('close');
}

async function handleSubmit() {
  erro.value = '';

  if (!produtoId.value) { erro.value = 'Selecione um produto.'; return; }
  if (!quantidade.value || Number(quantidade.value) < 1) { erro.value = 'Informe uma quantidade válida (mínimo 1).'; return; }

  const custoUnitario = pedeValorPago.value ? paraCentavos(valorPago.value) : undefined;
  if (pedeValorPago.value && valorPago.value.trim() && custoUnitario === undefined) {
    erro.value = 'Valor pago inválido. Use apenas números (ex: 45,90).';
    return;
  }

  mutation.mutate(
    {
      produto_id: Number(produtoId.value),
      data: {
        tipo: tipo.value,
        quantidade: Number(quantidade.value),
        custo_unitario: custoUnitario,
        observacao: observacao.value.trim() || undefined,
      },
    },
    {
      onSuccess: () => handleClose(),
      onError: (err: any) => {
        const detail = err?.response?.data?.detail;
        erro.value = typeof detail === 'string' ? detail : 'Erro ao registrar movimentação.';
      },
    },
  );
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Nova Movimentação de Estoque" size="md" @close="handleClose">
    <div class="space-y-5">
      <div
        v-if="erro"
        class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm"
      >
        {{ erro }}
      </div>

      <!-- Produto -->
      <BaseSelect
        v-model="produtoId"
        label="Produto"
        placeholder="Selecione o produto"
        :options="produtoOptions"
        :required="true"
      />

      <!-- Estoque atual -->
      <div
        v-if="produtoSelecionado"
        class="flex items-center gap-2 px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-600"
      >
        <span>Estoque atual:</span>
        <span class="font-semibold text-zinc-800">{{ produtoSelecionado.estoque.quantidade }} un</span>
      </div>

      <!-- Tipo -->
      <BaseSelect
        v-model="tipo"
        label="Tipo de Movimentação"
        :options="tipoOptions"
        :required="true"
      />

      <!-- Indicador visual do tipo -->
      <div
        class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium"
        :class="tipoBadge.class"
      >
        <component :is="tipoBadge.icon" :size="16" />
        <span v-if="tipo === 'AJUSTE'">Define a quantidade final do estoque</span>
        <span v-else-if="tipo === 'ENTRADA'">Adiciona ao estoque atual</span>
        <span v-else>Retira do estoque atual</span>
      </div>

      <!-- Quantidade -->
      <div>
        <label class="block text-sm font-medium text-zinc-700 mb-1">
          {{ tipo === 'AJUSTE' ? 'Quantidade final desejada' : 'Quantidade' }}
          <span class="text-red-500 ml-0.5">*</span>
        </label>
        <input
          v-model.number="quantidade"
          type="number"
          min="1"
          placeholder="0"
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
        />
      </div>

      <!-- Valor pago (só na entrada: é a compra que muda o custo) -->
      <div v-if="pedeValorPago">
        <label class="block text-sm font-medium text-zinc-700 mb-1">
          Valor pago por unidade
          <span class="text-zinc-400 font-normal">(opcional)</span>
        </label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-zinc-400">R$</span>
          <input
            v-model="valorPago"
            type="text"
            inputmode="decimal"
            placeholder="0,00"
            class="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
          />
        </div>
        <p v-if="novaMediaPrevista !== null" class="mt-1.5 text-xs text-zinc-500">
          Custo médio passa a
          <strong class="text-zinc-700">{{ formatarMoeda(novaMediaPrevista) }}</strong>
          <template v-if="custoConhecido !== null">
            (era {{ formatarMoeda(custoConhecido) }})
          </template>
        </p>
        <p v-else class="mt-1.5 text-xs text-zinc-400">
          Deixe em branco se for devolução — devolver não é comprar, e o custo médio não muda.
        </p>
      </div>

      <!-- Observação -->
      <div>
        <label class="block text-sm font-medium text-zinc-700 mb-1">Observação</label>
        <textarea
          v-model="observacao"
          rows="2"
          placeholder="Motivo da movimentação (opcional)"
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm resize-none focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
        ></textarea>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3 w-full">
        <BaseButton type="button" variant="secondary" @click="handleClose">Cancelar</BaseButton>
        <BaseButton
          type="button"
          variant="primary"
          :is-loading="mutation.isPending.value"
          @click="handleSubmit"
        >
          Registrar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>