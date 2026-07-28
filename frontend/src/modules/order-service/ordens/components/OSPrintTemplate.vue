<script setup lang="ts">
import { computed } from 'vue';
import {
  Smartphone,
  User,
  CheckCircle2,
  CreditCard,
  Receipt,
  Banknote,
} from 'lucide-vue-next';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import { formatCurrency } from '@/shared/utils/finance';
import {
  useCompanyPrintInfo,
  getClienteNome,
  getClienteDoc,
  getClientePhone,
  getClienteEndereco,
  getPaymentDisplayName,
  formatPrintDate,
  formatPrintPhone,
  formatPrintDoc,
  tipoObjetoRelevante,
} from '@/shared/utils/print.utils';

import PrintCompanyHeader from '@/shared/components/print/a4/PrintCompanyHeader.vue';
import PrintSignatures from '@/shared/components/print/a4/PrintSignatures.vue';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';

const props = defineProps<{
  ordemServico: OrderServiceReadDataType | null;
  type: 'ENTRADA' | 'SAIDA' | 'CANCELAMENTO';
}>();

const { companyInfo } = useCompanyPrintInfo();
const { labelSingular } = useObjetoLabels();

// O "tipo" só aparece quando acrescenta info além do rótulo do segmento (em
// oficina ele é o próprio "Veículo" → redundante sob "Dados do Veículo").
const mostrarTipoObjeto = computed(() =>
  tipoObjetoRelevante(props.ordemServico?.objeto?.tipo_equipamento, labelSingular.value),
);

const situacao = computed(() => props.ordemServico?.situacao_equipamento ?? null);

const isSemReparo = computed(() =>
  situacao.value === 'SEM_REPARO' || situacao.value === 'CONDENADO'
);

const title = computed(() => {
  if (props.type === 'ENTRADA') return 'COMPROVANTE DE ENTRADA DE OBJETO';
  if (props.type === 'CANCELAMENTO') return 'DECLARAÇÃO DE CANCELAMENTO DE SERVIÇO';
  if (situacao.value === 'SEM_REPARO') return 'DECLARAÇÃO DE ENTREGA SEM REPARO';
  if (situacao.value === 'CONDENADO') return 'DECLARAÇÃO DE OBJETO CONDENADO';
  return 'RECIBO E TERMO DE GARANTIA';
});

const situacaoConfig = computed(() => {
  const map: Record<string, { label: string; cls: string }> = {
    REPARADO:   { label: 'Reparado',   cls: 'bg-emerald-100 text-emerald-700 border border-emerald-300' },
    SEM_REPARO: { label: 'Sem Reparo', cls: 'bg-amber-100 text-amber-700 border border-amber-300' },
    CONDENADO:  { label: 'Condenado',  cls: 'bg-red-100 text-red-700 border border-red-300' },
  };
  return situacao.value ? map[situacao.value] ?? null : null;
});

const motivoCancelamento = computed(() => {
  const obs = props.ordemServico?.observacoes ?? '';
  const match = obs.match(/\[CANCELAMENTO\]\s*([\s\S]+)/);
  return match ? match[1].trim() : 'Motivo não informado.';
});

const subtotal = computed(() => {
  if (!props.ordemServico) return 0;
  return props.ordemServico.itens.reduce((acc, item) => acc + item.valor_total, 0);
});

const adiantamento = computed(() => props.ordemServico?.valor_entrada ?? 0);

const adiantamentoUtilizado = computed(() => {
  const entrada = adiantamento.value;
  const total = props.ordemServico?.valor_total ?? 0;
  return Math.min(entrada, total);
});

const totalPago = computed(() => {
  if (!props.ordemServico?.pagamentos) return 0;
  return props.ordemServico.pagamentos.reduce((acc, pg) => acc + pg.valor, 0);
});

const totalRecebido = computed(() => adiantamentoUtilizado.value + totalPago.value);
</script>

<template>
  <Teleport to="body">
  <div v-if="ordemServico" class="print-container hidden print:block bg-white text-black font-sans leading-tight">
    <PrintCompanyHeader
      :company="companyInfo"
      document-label="Número da O.S."
      :document-number="ordemServico.numero_os || String(ordemServico.id).padStart(6, '0')"
      date-label="Data Entrada"
      :date-value="formatPrintDate(ordemServico.data_criacao)"
      :finalizada-date="ordemServico.data_finalizacao ? formatPrintDate(ordemServico.data_finalizacao) : undefined"
    />

    <div class="text-center py-2 mb-4 border-y-2 border-slate-200 bg-slate-50">
      <h2 class="text-lg font-black text-slate-800 uppercase tracking-widest">{{ title }}</h2>
    </div>

    <div class="grid grid-cols-2 gap-4 mb-4">
      <div class="border border-slate-300 rounded-lg overflow-hidden">
        <div class="bg-slate-100 px-3 py-1.5 border-b border-slate-200 flex items-center gap-2">
          <User :size="14" class="text-slate-500" />
          <h3 class="text-xs font-bold uppercase text-slate-700">Dados do Cliente</h3>
        </div>
        <div class="p-3 text-xs space-y-1.5">
          <p><span class="font-bold text-slate-600">Nome:</span> {{ ordemServico.cliente ? getClienteNome(ordemServico.cliente) : 'Consumidor' }}</p>
          <div class="flex gap-4">
            <p><span class="font-bold text-slate-600">CPF/CNPJ:</span> {{ formatPrintDoc(getClienteDoc(ordemServico.cliente)) }}</p>
            <p><span class="font-bold text-slate-600">Telefone:</span> {{ formatPrintPhone(getClientePhone(ordemServico.cliente as any)) }}</p>
          </div>
          <p v-if="getClienteEndereco(ordemServico.cliente)"><span class="font-bold text-slate-600">Endereço:</span> {{ getClienteEndereco(ordemServico.cliente) }}</p>
          <p v-if="ordemServico.cliente?.id"><span class="font-bold text-slate-600">Cód. Cliente:</span> #{{ ordemServico.cliente.id }}</p>
        </div>
      </div>

      <div class="border border-slate-300 rounded-lg overflow-hidden">
        <div class="bg-slate-100 px-3 py-1.5 border-b border-slate-200 flex items-center gap-2">
          <Smartphone :size="14" class="text-slate-500" />
          <h3 class="text-xs font-bold uppercase text-slate-700">Dados do {{ labelSingular }}</h3>
        </div>
        <div class="p-3 text-xs space-y-1.5">
          <div v-if="mostrarTipoObjeto || situacaoConfig" class="flex items-center gap-2">
            <p v-if="mostrarTipoObjeto" class="text-sm font-bold text-slate-900">{{ ordemServico.objeto.tipo_equipamento }}</p>
            <span v-if="situacaoConfig" :class="['px-2 py-0.5 rounded-full text-[10px] font-bold', situacaoConfig.cls]">
              {{ situacaoConfig.label }}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <p><span class="font-bold text-slate-600">Marca:</span> {{ ordemServico.objeto.marca || '-' }}</p>
            <p><span class="font-bold text-slate-600">Modelo:</span> {{ ordemServico.objeto.modelo || '-' }}</p>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <p><span class="font-bold text-slate-600">Nº Série:</span> {{ ordemServico.objeto.numero_serie || '-' }}</p>
            <p><span class="font-bold text-slate-600">Cor:</span> {{ ordemServico.objeto.cor || '-' }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="mb-4 space-y-2">
      <div class="border border-slate-300 rounded-lg p-3 bg-slate-50/50">
        <p class="text-[10px] font-bold text-slate-500 uppercase mb-1">Defeito Relatado / Solicitação</p>
        <p class="text-xs text-slate-900 font-medium">{{ ordemServico.defeito_relatado }}</p>
      </div>
      <div v-if="ordemServico.observacoes" class="border border-dashed border-slate-300 rounded-lg p-3">
        <p class="text-[10px] font-bold text-slate-500 uppercase mb-1">Observações / Acessórios</p>
        <p class="text-xs text-slate-700 whitespace-pre-line">{{ ordemServico.observacoes }}</p>
      </div>
    </div>

    <!-- ── SAÍDA ── -->
    <template v-if="type === 'SAIDA'">
      <div v-if="ordemServico.solucao || ordemServico.diagnostico" class="mb-4 border border-slate-300 rounded-lg overflow-hidden">
        <div class="bg-slate-100 px-3 py-1.5 border-b border-slate-200 flex items-center gap-2">
          <CheckCircle2 :size="14" class="text-emerald-600" />
          <h3 class="text-xs font-bold uppercase text-slate-700">Laudo Técnico & Solução</h3>
        </div>
        <div class="p-3 text-xs space-y-2">
          <div v-if="ordemServico.diagnostico">
            <span class="font-bold text-slate-600 uppercase text-[10px]">Diagnóstico:</span>
            <p class="text-slate-800">{{ ordemServico.diagnostico }}</p>
          </div>
          <div v-if="ordemServico.solucao" class="pt-2 border-t border-slate-100 mt-2">
            <span class="font-bold text-emerald-600 uppercase text-[10px]">Solução Realizada:</span>
            <p class="text-slate-900 font-medium">{{ ordemServico.solucao }}</p>
          </div>
        </div>
      </div>

      <div class="mb-4" v-if="ordemServico.itens?.length">
        <table class="w-full text-xs text-left">
          <thead>
            <tr class="border-b-2 border-slate-800">
              <th class="py-2 pl-2 text-slate-600 uppercase font-bold w-[60%]">Descrição do Serviço / Peça</th>
              <th class="py-2 text-center text-slate-600 uppercase font-bold w-[10%]">Qtd</th>
              <th class="py-2 text-right text-slate-600 uppercase font-bold w-[15%]">Unit.</th>
              <th class="py-2 pr-2 text-right text-slate-600 uppercase font-bold w-[15%]">Total</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200">
            <tr v-for="item in ordemServico.itens" :key="item.id">
              <td class="py-2 pl-2 text-slate-800">{{ item.nome }}</td>
              <td class="py-2 text-center text-slate-600">{{ item.quantidade }}</td>
              <td class="py-2 text-right text-slate-600">{{ formatCurrency(item.valor_unitario) }}</td>
              <td class="py-2 pr-2 text-right font-bold text-slate-800">{{ formatCurrency(item.valor_total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="grid grid-cols-2 gap-6 mb-4">
        <!-- Detalhes do pagamento -->
        <div>
          <p class="text-[10px] font-bold text-slate-500 uppercase mb-2 border-b border-slate-200 pb-1">Detalhes do Pagamento</p>
          <!-- Adiantamento recebido na entrada -->
          <div v-if="adiantamento > 0" class="flex justify-between items-center text-xs bg-emerald-50 p-1.5 rounded border border-emerald-100 mb-1.5">
            <div class="flex items-center gap-2">
              <Banknote :size="12" class="text-emerald-600" />
              <span class="font-semibold text-emerald-700">Adiantamento (entrada)</span>
            </div>
            <span class="font-bold text-emerald-700">{{ formatCurrency(adiantamento) }}</span>
          </div>
          <!-- Pagamentos no fechamento -->
          <div v-if="ordemServico.pagamentos?.length" class="space-y-1.5">
            <div v-for="pgto in ordemServico.pagamentos" :key="pgto.id" class="flex justify-between items-center text-xs bg-slate-50 p-1.5 rounded border border-slate-100">
              <div class="flex items-center gap-2">
                <CreditCard :size="12" class="text-slate-400" />
                <span class="font-semibold text-slate-700">
                  {{ getPaymentDisplayName(pgto.forma_pagamento?.nome || 'Pagamento') }}
                  <span v-if="pgto.parcelas > 1" class="text-[10px] text-slate-500 font-normal">({{ pgto.parcelas }}x)</span>
                </span>
              </div>
              <span class="font-bold text-slate-800">{{ formatCurrency(pgto.valor) }}</span>
            </div>
          </div>
          <div v-else-if="adiantamento === 0" class="text-xs text-slate-400 italic py-2">Nenhum pagamento registrado.</div>
        </div>

        <!-- Resumo financeiro -->
        <div class="space-y-1 text-right">
          <!-- O cabeçalho não é enfeite: sem ele esta coluna começava no topo da
               linha do grid e o "Subtotal" alinhava com o TÍTULO da coluna de
               pagamentos, não com o conteúdo dela. -->
          <p class="text-[10px] font-bold text-slate-500 uppercase mb-2 border-b border-slate-200 pb-1 text-left">Resumo Financeiro</p>
          <div class="flex justify-between text-xs text-slate-500">
            <span>Subtotal:</span>
            <span>{{ formatCurrency(subtotal) }}</span>
          </div>
          <div v-if="(ordemServico.desconto ?? 0) > 0" class="flex justify-between text-xs text-red-600">
            <span>Desconto:</span>
            <span>- {{ formatCurrency(ordemServico.desconto ?? 0) }}</span>
          </div>
          <div v-if="(ordemServico.taxa_entrega ?? 0) > 0" class="flex justify-between text-xs text-slate-500">
            <span>Deslocamento:</span>
            <span>+ {{ formatCurrency(ordemServico.taxa_entrega ?? 0) }}</span>
          </div>
          <div v-if="(ordemServico.acrescimo ?? 0) > 0" class="flex justify-between text-xs text-amber-600">
            <span>Juros:</span>
            <span>+ {{ formatCurrency(ordemServico.acrescimo ?? 0) }}</span>
          </div>
          <div v-if="adiantamento > 0" class="flex justify-between text-xs text-emerald-600">
            <span>Adiantamento:</span>
            <span>- {{ formatCurrency(adiantamentoUtilizado) }}</span>
          </div>
          <div class="border-t border-slate-800 my-1 pt-1 flex justify-between items-end">
            <span class="text-sm font-bold text-slate-900 uppercase">Total Pago:</span>
            <span class="text-xl font-black text-slate-900 leading-none">{{ formatCurrency(totalRecebido) }}</span>
          </div>
          <div v-if="(ordemServico.acrescimo ?? 0) > 0" class="mt-1 border border-amber-300 bg-amber-50 rounded p-1.5 space-y-0.5">
            <p class="text-[9px] font-bold text-amber-700 uppercase">Em caso de devolução</p>
            <div class="flex justify-between text-[9px] text-slate-600">
              <span>Valor do serviço (dinheiro):</span>
              <span class="font-semibold">{{ formatCurrency(totalPago - (ordemServico.acrescimo ?? 0)) }}</span>
            </div>
            <div class="flex justify-between text-[9px] text-slate-600">
              <span>Estorno no cartão:</span>
              <span class="font-semibold">{{ formatCurrency(totalPago) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Termo de Garantia (só para REPARADO) -->
      <div v-if="!isSemReparo" class="border border-brand-primary/20 bg-brand-primary-light/50 rounded-lg p-3 text-[10px] text-slate-700 text-justify leading-relaxed mb-6">
        <div class="flex items-center gap-2 mb-1 font-bold text-brand-primary uppercase">
          <Receipt :size="12" />
          Termo de Garantia
        </div>
        A garantia é válida por <strong>{{ ordemServico.garantia || '90 (noventa) dias' }}</strong> a contar desta data, cobrindo exclusivamente os serviços prestados e peças substituídas descritos neste documento.
        A garantia <strong>NÃO COBRE</strong>: mau uso, contato com líquidos, quedas, oxidação, violação de selos de garantia ou intervenção de terceiros.
        <br/>
        IMPORTANTE: Objetos não retirados no prazo de 90 dias após notificação de conclusão serão considerados abandonados e poderão ser vendidos para custeio das despesas, conforme Art. 1.275 do Código Civil Brasileiro.
      </div>

      <!-- Declaração de entrega sem reparo (SEM_REPARO / CONDENADO) -->
      <div v-else class="border border-amber-200 bg-amber-50/50 rounded-lg p-3 text-[10px] text-slate-700 text-justify leading-relaxed mb-6">
        <div class="flex items-center gap-2 mb-1 font-bold text-amber-700 uppercase">
          <Receipt :size="12" />
          Declaração de Entrega
        </div>
        O objeto acima identificado está sendo devolvido ao cliente <strong>sem realização de reparo</strong>.
        A assistência técnica <strong>não oferece garantia</strong> sobre os serviços desta O.S.
        O cliente declara estar ciente da situação do objeto e recebe o mesmo conforme descrito neste documento.
      </div>
    </template>

    <!-- ── CANCELAMENTO ── -->
    <template v-else-if="type === 'CANCELAMENTO'">
      <div class="border border-red-200 bg-red-50/50 rounded-lg p-4 mb-6">
        <div class="flex items-center gap-2 mb-2 font-bold text-red-700 uppercase">
          <span class="p-1 bg-red-100 rounded">CANCELAMENTO</span>
          Motivo do Cancelamento
        </div>
        <p class="text-sm text-slate-900 font-medium">{{ motivoCancelamento }}</p>
      </div>
      <div class="border border-slate-200 bg-slate-50 rounded-lg p-3 text-[10px] text-slate-500 text-justify leading-relaxed mb-6">
        <strong class="text-slate-700 uppercase">Declaração:</strong>
        Declaro para os devidos fins que a Ordem de Serviço acima identificada foi cancelada na presente data.
        O objeto foi devolvido ao cliente no estado em que se encontrava, sem realização de reparos ou com reparos parciais conforme acordado, isentando a assistência técnica de garantias sobre serviços não concluídos.
      </div>
    </template>

    <!-- ── ENTRADA ── -->
    <div v-else class="border border-slate-200 bg-slate-50 rounded-lg p-3 text-[10px] text-slate-500 text-justify leading-relaxed mb-8 space-y-2">
      <p>
        <strong class="text-slate-700 uppercase">Condições de Entrada:</strong>
        O cliente declara estar ciente que a empresa não se responsabiliza por perda de dados (backup é responsabilidade do cliente) nem por chips/cartões de memória deixados no aparelho.
        Autorizo a análise técnica do objeto acima. Em caso de não aprovação do orçamento, estou ciente que poderá ser cobrada taxa de análise técnica.
      </p>
      <p class="border-t border-slate-200 pt-2">
        <strong class="text-slate-700 uppercase">⚠ Prazo de Retirada:</strong>
        Objetos com serviço concluído que não forem retirados no prazo de <strong class="text-slate-700">90 (noventa) dias</strong> após notificação serão considerados abandonados e poderão ser destinados para cobrir as despesas do serviço, conforme Art. 1.275 do Código Civil Brasileiro.
      </p>
    </div>

    <PrintSignatures
      left-label="Técnico Responsável"
      right-label="Assinatura do Cliente"
      :right-name="ordemServico.cliente ? getClienteNome(ordemServico.cliente) : undefined"
    />

    <PrintFooter />
  </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-a4.css';
</style>
