<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { refDebounced } from '@vueuse/core';
import { useQuery } from '@tanstack/vue-query';
import { Wrench, ShoppingBag, Save, Search, Loader2, Lock } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { useProductsQuery } from '@/modules/products/inventory/composables/useProductsQuery';
import { getServicos } from '@/modules/order-service/servicos/services/servicos.service';
import { SERVICOS_OS_ITEM_QUERY_KEY } from '@/modules/order-service/shared/constants/queryKeys';
import { MEDIDA_SERVICO_OPTIONS, MEDIDA_PRODUTO_OPTIONS } from '../../constants/core.constant';
import type { OsItemCreateSchemaDataType } from '../../schemas/relationship/osItem.schema';
import type { OsItemTypeEnumDataType, OsItemMeasureEnumDataType, OsItemAprovacaoEnumDataType } from '../../schemas/enums/osEnums.schema';
import { useCapacidades } from '@/modules/order-service/shared/segmento/useCapacidades';

interface Props {
  isOpen: boolean;
  item?: OsItemCreateSchemaDataType | null;
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  item: null,
});

const emit = defineEmits<{
  close: [];
  save: [item: OsItemCreateSchemaDataType];
}>();

// --- Estado do formulário ---
const tipo = ref<OsItemTypeEnumDataType>('SERVICO');
const nome = ref('');
const unidade_medida = ref<OsItemMeasureEnumDataType>('UN');
const quantidade = ref(1);
const valorUnitarioNum = ref(0);
const selectedCatalogId = ref<number | null>(null);
// Quanto a loja PAGOU por unidade. Campo interno — não sai em nenhuma via
// impressa. É o que permite lançar só o serviço ("Troca de conector, R$ 150") e
// mesmo assim o relatório saber que a peça custou R$ 40.
const custoUnitarioNum = ref(0);

// Aprovação/garantia por item (fluxo de orçamento): dirigidas por capacidade,
// não por segmento — qualquer negócio de serviço pode querer orçar e garantir.
const { temAprovacaoItens, temGarantiaItens } = useCapacidades();
const statusAprovacao = ref<OsItemAprovacaoEnumDataType>('APROVADO');
const garantiaDias = ref<number | null>(null);
const garantiaKm = ref<number | null>(null);

const STATUS_APROVACAO: { value: OsItemAprovacaoEnumDataType; label: string; selected: string }[] = [
  { value: 'PENDENTE', label: 'Pendente', selected: 'bg-amber-500 text-white shadow-sm' },
  { value: 'APROVADO', label: 'Aprovado', selected: 'bg-emerald-500 text-white shadow-sm' },
  { value: 'REPROVADO', label: 'Reprovado', selected: 'bg-red-500 text-white shadow-sm' },
];

// --- Catálogo ---
const catalogSearch = ref('');
const debouncedCatalogSearch = refDebounced(catalogSearch, 400);

// O limite espelha o dos serviços (logo abaixo): as duas abas da busca do
// catálogo devem devolver o mesmo tanto de sugestões.
const { data: produtosData, isLoading: isLoadingProdutos } = useProductsQuery(
  computed(() => tipo.value === 'PRODUTO' && debouncedCatalogSearch.value
    ? debouncedCatalogSearch.value
    : null
  ),
  20,
);

// A chave pende do prefixo canônico 'servicos': é o que faz o preço editado no
// catálogo aparecer aqui sem F5. Como chave própria ('servicos-os-item'), a
// invalidação das mutations do catálogo nunca alcançava este cache.
const { data: servicosData, isLoading: isLoadingServicos } = useQuery({
  queryKey: [...SERVICOS_OS_ITEM_QUERY_KEY, debouncedCatalogSearch] as const,
  queryFn: () => getServicos({
    search: debouncedCatalogSearch.value || undefined,
    active: true,
    limit: 20,
  }),
  enabled: computed(() => tipo.value === 'SERVICO' && debouncedCatalogSearch.value.length > 0),
  staleTime: 1000 * 60,
});

interface CatalogItem {
  id: number;
  nome: string;
  valor: number;
  unidade_medida: string;
}

const catalogItems = computed<CatalogItem[]>(() => {
  if (tipo.value === 'PRODUTO') {
    return (produtosData.value ?? [])
      .filter(p => p.ativo)
      .map(p => ({
        id: p.id,
        nome: p.nome,
        valor: p.estoque?.valor_varejo ?? 0,
        unidade_medida: p.unidade_medida ?? 'UN',
      }));
  }
  return (servicosData.value?.items ?? []).map(s => ({
    id: s.id,
    nome: s.descricao,
    valor: s.valor,
    unidade_medida: 'UN',
  }));
});

const isLoadingCatalog = computed(() =>
  tipo.value === 'PRODUTO' ? isLoadingProdutos.value : isLoadingServicos.value,
);

const showCatalogResults = computed(() =>
  catalogSearch.value.length > 0 && catalogItems.value.length > 0,
);

function selectCatalogItem(item: CatalogItem): void {
  selectedCatalogId.value = item.id;
  nome.value = item.nome;
  valorUnitarioNum.value = item.valor / 100;
  unidade_medida.value = item.unidade_medida as OsItemMeasureEnumDataType;
  catalogSearch.value = '';
}

// --- Medidas filtradas por tipo ---
const medidaOptions = computed(() =>
  tipo.value === 'SERVICO' ? [...MEDIDA_SERVICO_OPTIONS] : [...MEDIDA_PRODUTO_OPTIONS],
);

// --- Computeds ---
const total = computed(() => Math.round(quantidade.value * valorUnitarioNum.value * 100));
const isValid = computed(() => nome.value.trim().length > 0 && quantidade.value > 0);

// Produto do catálogo tem o custo vindo do livro de estoque, congelado na baixa.
// Pedir o custo de novo aqui abriria espaço para dois números divergentes para a
// mesma peça — e o relatório contaria os dois.
const custoVemDoEstoque = computed(
  () => tipo.value === 'PRODUTO' && selectedCatalogId.value != null,
);

const margemItem = computed(() => {
  const receita = Math.round(quantidade.value * valorUnitarioNum.value * 100);
  const custo = Math.round(quantidade.value * custoUnitarioNum.value * 100);
  if (custo <= 0) return null;
  return { lucro: receita - custo, custo };
});

// --- Watchers ---
watch(tipo, () => {
  catalogSearch.value = '';
  selectedCatalogId.value = null;

  const validValues = medidaOptions.value.map(o => o.value);
  if (!validValues.includes(unidade_medida.value)) {
    unidade_medida.value = 'UN';
  }
});

watch(() => props.isOpen, (open) => {
  if (open) {
    if (props.item) populate(props.item);
    else reset();
  }
});

// --- Ações ---
function reset(): void {
  tipo.value = 'SERVICO';
  nome.value = '';
  unidade_medida.value = 'UN';
  quantidade.value = 1;
  valorUnitarioNum.value = 0;
  custoUnitarioNum.value = 0;
  catalogSearch.value = '';
  selectedCatalogId.value = null;
  statusAprovacao.value = 'APROVADO';
  garantiaDias.value = null;
  garantiaKm.value = null;
}

function populate(item: OsItemCreateSchemaDataType): void {
  tipo.value = item.tipo;
  nome.value = item.nome;
  unidade_medida.value = item.unidade_medida;
  quantidade.value = item.quantidade;
  valorUnitarioNum.value = item.valor_unitario / 100;
  custoUnitarioNum.value = (item.custo_unitario ?? 0) / 100;
  selectedCatalogId.value = item.item_id ?? null;
  statusAprovacao.value = item.status_aprovacao ?? 'APROVADO';
  garantiaDias.value = item.garantia_dias ?? null;
  garantiaKm.value = item.garantia_km ?? null;
}

function handleSave(): void {
  if (!isValid.value) return;
  emit('save', {
    tipo: tipo.value,
    nome: nome.value.trim(),
    unidade_medida: unidade_medida.value,
    quantidade: quantidade.value,
    valor_unitario: Math.round(valorUnitarioNum.value * 100),
    // Só envia custo quando ele é desta linha. Com produto do catálogo, quem
    // manda é o livro de estoque.
    custo_unitario: custoVemDoEstoque.value || custoUnitarioNum.value <= 0
      ? undefined
      : Math.round(custoUnitarioNum.value * 100),
    status_aprovacao: statusAprovacao.value,
    garantia_dias: garantiaDias.value ?? undefined,
    garantia_km: garantiaKm.value ?? undefined,
    ...(selectedCatalogId.value != null && { item_id: selectedCatalogId.value }),
  });
  emit('close');
}

function handleClose(): void {
  emit('close');
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="item ? 'Editar Item' : 'Adicionar Item'"
    size="lg"
    @close="handleClose"
  >
    <form @submit.prevent="handleSave" class="space-y-5">
      <!-- Toggle Tipo -->
      <div class="flex p-1 bg-slate-100 rounded-lg">
        <button
          type="button"
          @click="tipo = 'SERVICO'"
          :class="[
            'flex-1 flex items-center justify-center gap-2 py-2 text-sm font-bold rounded-md transition-all',
            tipo === 'SERVICO' ? 'bg-white text-brand-primary shadow-sm' : 'text-slate-500 hover:text-slate-700',
          ]"
        >
          <Wrench :size="16" />
          Serviço / Mão de Obra
        </button>
        <button
          type="button"
          @click="tipo = 'PRODUTO'"
          :class="[
            'flex-1 flex items-center justify-center gap-2 py-2 text-sm font-bold rounded-md transition-all',
            tipo === 'PRODUTO' ? 'bg-white text-brand-primary shadow-sm' : 'text-slate-500 hover:text-slate-700',
          ]"
        >
          <ShoppingBag :size="16" />
          Produto / Peça
        </button>
      </div>

      <!-- Busca no Catálogo -->
      <div class="space-y-2">
        <label class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          {{ tipo === 'SERVICO' ? 'Buscar Serviço Cadastrado' : 'Buscar Produto Cadastrado' }}
        </label>

        <div class="relative">
          <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            v-model="catalogSearch"
            type="text"
            :placeholder="tipo === 'SERVICO' ? 'Pesquisar serviços cadastrados...' : 'Pesquisar produtos cadastrados...'"
            class="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary placeholder:text-slate-400"
          />
          <Loader2
            v-if="isLoadingCatalog && catalogSearch.length > 0"
            :size="16"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 animate-spin"
          />
        </div>

        <div
          v-if="showCatalogResults"
          class="max-h-36 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100 bg-white shadow-sm"
        >
          <button
            v-for="catalogItem in catalogItems"
            :key="catalogItem.id"
            type="button"
            @click="selectCatalogItem(catalogItem)"
            :class="[
              'w-full flex items-center justify-between px-3 py-2.5 text-left transition-colors',
              selectedCatalogId === catalogItem.id
                ? 'bg-brand-primary-light text-brand-primary'
                : 'hover:bg-slate-50',
            ]"
          >
            <span class="text-sm font-medium text-slate-700 truncate">{{ catalogItem.nome }}</span>
            <span class="text-sm font-bold text-slate-600 shrink-0 ml-3">
              {{ formatCurrency(catalogItem.valor) }}
            </span>
          </button>
        </div>

        <p
          v-else-if="catalogSearch.length > 0 && !isLoadingCatalog && catalogItems.length === 0"
          class="text-xs text-slate-400 italic py-1"
        >
          Nenhum resultado encontrado. Preencha manualmente abaixo.
        </p>
      </div>

      <!-- Separador -->
      <div class="relative flex items-center gap-3">
        <div class="flex-1 border-t border-slate-200"></div>
        <span class="text-xs text-slate-400 font-medium">ou preencha manualmente</span>
        <div class="flex-1 border-t border-slate-200"></div>
      </div>

      <!-- Campos do formulário -->
      <div class="space-y-4">
        <BaseInput
          v-model="nome"
          :label="tipo === 'SERVICO' ? 'Nome do Serviço' : 'Nome do Produto'"
          :placeholder="tipo === 'SERVICO' ? 'Ex: Troca de tela, Formatação...' : 'Ex: Tela LCD, Bateria...'"
          required
        />

        <div class="grid grid-cols-2 gap-4">
          <BaseSelect
            v-model="unidade_medida"
            label="Unidade de Medida"
            :options="medidaOptions"
          />

          <BaseInput
            v-model.number="quantidade"
            :label="tipo === 'SERVICO' ? 'Qtd. / Horas' : 'Quantidade'"
            type="number"
            :min="0"
          />
        </div>

        <BaseMoneyInput
          v-model="valorUnitarioNum"
          :label="tipo === 'SERVICO' ? 'Valor / Hora' : 'Valor Unitário'"
        />

        <!--
          Custo interno. Existe porque o normal é lançar só o serviço, sem
          cadastrar a peça — e aí o gasto com ela não tem por onde entrar no
          relatório. NÃO aparece em nenhuma via do cliente.
        -->
        <div v-if="!custoVemDoEstoque" class="rounded-xl border border-slate-200 bg-slate-50/60 p-3 space-y-2">
          <div class="flex items-center gap-1.5">
            <Lock :size="13" class="text-slate-400" />
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Custo para a loja
            </span>
            <span class="text-[10px] text-slate-400">(opcional)</span>
          </div>
          <BaseMoneyInput v-model="custoUnitarioNum" label="" />
          <p v-if="margemItem" class="text-xs text-slate-500">
            Custo {{ formatCurrency(margemItem.custo) }} · sobra
            <strong :class="margemItem.lucro >= 0 ? 'text-emerald-600' : 'text-red-600'">
              {{ formatCurrency(margemItem.lucro) }}
            </strong>
          </p>
          <p class="text-[11px] text-slate-400 leading-snug">
            Quanto você pagou pela peça. Fica só no relatório —
            <strong class="text-slate-500">o cliente nunca vê este valor</strong>.
          </p>
        </div>

        <p v-else class="flex items-start gap-1.5 text-[11px] text-slate-400 leading-snug">
          <Lock :size="12" class="shrink-0 mt-0.5" />
          <span>
            Custo vem do estoque automaticamente, congelado no dia da baixa — não
            precisa informar aqui.
          </span>
        </p>

        <!-- Aprovação e garantia por item: cada uma é uma capacidade independente
             do segmento. Item REPROVADO não entra no total. -->
        <div
          v-if="temAprovacaoItens || temGarantiaItens"
          class="space-y-3 border-t border-slate-100 pt-4"
        >
          <template v-if="temAprovacaoItens">
            <label class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Aprovação do Item
            </label>
            <div class="flex p-1 bg-slate-100 rounded-lg gap-1">
              <button
                v-for="s in STATUS_APROVACAO"
                :key="s.value"
                type="button"
                class="flex-1 py-2 text-sm font-bold rounded-md transition-all"
                :class="statusAprovacao === s.value ? s.selected : 'text-slate-500 hover:text-slate-700'"
                @click="statusAprovacao = s.value"
              >
                {{ s.label }}
              </button>
            </div>
          </template>

          <div v-if="temGarantiaItens" class="grid grid-cols-2 gap-4">
            <BaseInput
              v-model.number="garantiaDias"
              label="Garantia (dias)"
              type="number"
              :min="0"
              placeholder="Ex: 90"
            />
            <BaseInput
              v-model.number="garantiaKm"
              label="Garantia (KM)"
              type="number"
              :min="0"
              placeholder="Ex: 10000"
            />
          </div>
        </div>

        <div class="bg-slate-50 rounded-xl p-4 border border-slate-200 flex items-center justify-between">
          <span class="text-sm font-bold text-slate-500 uppercase">Total do Item</span>
          <span class="text-xl font-black text-slate-800">{{ formatCurrency(total) }}</span>
        </div>
      </div>
    </form>

    <template #footer>
      <div class="flex justify-end gap-2 w-full">
        <BaseButton variant="secondary" @click="handleClose">
          CANCELAR
        </BaseButton>
        <BaseButton type="submit" variant="primary" :disabled="!isValid" @click="handleSave">
          <Save :size="16" class="mr-2" />
          {{ item ? 'SALVAR ALTERAÇÕES' : 'ADICIONAR ITEM' }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
