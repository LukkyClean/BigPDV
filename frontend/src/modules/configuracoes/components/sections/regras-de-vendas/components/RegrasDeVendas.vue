<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store'

const configStore = useConfiguracoesStore()
const {
  permitirDesconto,
  descontoMaximoPercent,
  exigirClienteIdentificado,
  valorMinimoVenda,
  permitirParcelamento,
  parcelasMaximas,
  permitirVendaEstoqueZerado,
  controlarCaixa,
  exigirCaixaAberto,
  fechamentoCego,
} = storeToRefs(configStore)

function valoresDoStore() {
  return {
    vendas: {
      permitir_desconto: permitirDesconto.value,
      desconto_maximo_percent: descontoMaximoPercent.value,
      exigir_cliente_identificado: exigirClienteIdentificado.value,
      valor_minimo_venda_reais: (valorMinimoVenda.value / 100) as number,
      permitir_parcelamento: permitirParcelamento.value,
      parcelas_maximas: parcelasMaximas.value,
      controlar_caixa: controlarCaixa.value,
      exigir_caixa_aberto: exigirCaixaAberto.value,
      fechamento_cego: fechamentoCego.value,
    },
    estoque: {
      permitir_venda_estoque_zerado: permitirVendaEstoqueZerado.value,
    },
  }
}

const form = reactive(valoresDoStore())

function resetar() {
  Object.assign(form.vendas, valoresDoStore().vendas)
  Object.assign(form.estoque, valoresDoStore().estoque)
}

watch(() => configStore.configVendas, () => {
  Object.assign(form.vendas, valoresDoStore().vendas)
})

watch(() => configStore.configProdutos, () => {
  Object.assign(form.estoque, valoresDoStore().estoque)
})

const isDirty = computed(
  () => JSON.stringify({ vendas: { ...form.vendas }, estoque: { ...form.estoque } }) !== JSON.stringify(valoresDoStore()),
)

defineExpose({
  isDirty,
  resetar,
  get form() {
    return {
      vendas: {
        permitir_desconto: form.vendas.permitir_desconto,
        desconto_maximo_percent: form.vendas.desconto_maximo_percent,
        exigir_cliente_identificado: form.vendas.exigir_cliente_identificado,
        valor_minimo_venda: Math.round(form.vendas.valor_minimo_venda_reais * 100),
        permitir_parcelamento: form.vendas.permitir_parcelamento,
        parcelas_maximas: form.vendas.parcelas_maximas,
        controlar_caixa: form.vendas.controlar_caixa,
        exigir_caixa_aberto: form.vendas.exigir_caixa_aberto,
        fechamento_cego: form.vendas.fechamento_cego,
      },
      estoque: {
        permitir_venda_estoque_zerado: form.estoque.permitir_venda_estoque_zerado,
      },
    }
  },
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Regras de Vendas</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Defina as regras e limitações para o processo de vendas</p>
    </div>

    <!-- Descontos -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Descontos</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Permitir desconto em vendas</p>
          <p class="text-xs text-zinc-500 mt-0.5">Habilita o campo de desconto no carrinho</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.vendas.permitir_desconto ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.vendas.permitir_desconto = !form.vendas.permitir_desconto"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.vendas.permitir_desconto ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Desconto máximo permitido (%) — 0 = bloqueia todo desconto</label>
        <input
          v-model.number="form.vendas.desconto_maximo_percent"
          type="number"
          min="0"
          max="100"
          :disabled="!form.vendas.permitir_desconto"
          class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 disabled:opacity-40 disabled:cursor-not-allowed"
        />
      </div>
    </div>

    <!-- Controle de Caixa -->
    <!-- Chaves por EMPRESA, e não por segmento: quem tem balcão e recebe
         dinheiro na mão pode querer o controle, seja adega, mercado ou oficina.
         Todas nascem desligadas — a segurança é o padrão, não esconder a opção. -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Controle de Caixa</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Usar controle de caixa</p>
          <p class="text-xs text-zinc-500 mt-0.5">Abertura com troco, sangria, suprimento e fechamento conferido</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.vendas.controlar_caixa ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.vendas.controlar_caixa = !form.vendas.controlar_caixa"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.vendas.controlar_caixa ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Exigir caixa aberto para vender</p>
          <p class="text-xs text-zinc-500 mt-0.5">Sem um turno aberto, a venda não é finalizada</p>
        </div>
        <button
          type="button"
          :disabled="!form.vendas.controlar_caixa"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 shrink-0', !form.vendas.controlar_caixa ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer', form.vendas.exigir_caixa_aberto ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.vendas.controlar_caixa && (form.vendas.exigir_caixa_aberto = !form.vendas.exigir_caixa_aberto)"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.vendas.exigir_caixa_aberto ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Fechamento às cegas</p>
          <p class="text-xs text-zinc-500 mt-0.5">O operador conta a gaveta sem ver o valor esperado</p>
        </div>
        <button
          type="button"
          :disabled="!form.vendas.controlar_caixa"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 shrink-0', !form.vendas.controlar_caixa ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer', form.vendas.fechamento_cego ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.vendas.controlar_caixa && (form.vendas.fechamento_cego = !form.vendas.fechamento_cego)"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.vendas.fechamento_cego ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <p class="text-xs text-zinc-500 mt-3">
        A exigência de PIN para sangria fica em
        <strong class="text-zinc-700">Segurança</strong>, junto das outras
        aprovações de gerente.
      </p>
    </div>

    <!-- Estoque e Clientes -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Estoque e Clientes</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Permitir venda sem estoque</p>
          <p class="text-xs text-zinc-500 mt-0.5">Vende mesmo quando o produto está zerado</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.estoque.permitir_venda_estoque_zerado ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.estoque.permitir_venda_estoque_zerado = !form.estoque.permitir_venda_estoque_zerado"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.estoque.permitir_venda_estoque_zerado ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Exigir cliente identificado</p>
          <p class="text-xs text-zinc-500 mt-0.5">Toda venda deve ter um cliente vinculado</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.vendas.exigir_cliente_identificado ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.vendas.exigir_cliente_identificado = !form.vendas.exigir_cliente_identificado"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.vendas.exigir_cliente_identificado ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Valor mínimo de venda — 0 = sem mínimo</label>
        <input
          v-model.number="form.vendas.valor_minimo_venda_reais"
          type="number"
          min="0"
          step="0.01"
          placeholder="0,00"
          class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
        />
      </div>
    </div>

    <!-- Pagamentos -->
    <div class="flex flex-col">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Pagamentos</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Permitir parcelamento</p>
          <p class="text-xs text-zinc-500 mt-0.5">Habilita pagamentos parcelados nas vendas</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.vendas.permitir_parcelamento ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.vendas.permitir_parcelamento = !form.vendas.permitir_parcelamento"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.vendas.permitir_parcelamento ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div class="py-3 border-b border-zinc-100">
        <label class="text-xs font-medium text-zinc-600">Máximo de parcelas (1–48)</label>
        <input
          v-model.number="form.vendas.parcelas_maximas"
          type="number"
          min="1"
          max="48"
          :disabled="!form.vendas.permitir_parcelamento"
          class="mt-1.5 w-full border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 disabled:opacity-40 disabled:cursor-not-allowed"
        />
      </div>
    </div>
  </div>
</template>
