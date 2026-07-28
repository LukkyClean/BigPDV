<script setup lang="ts">
/**
 * @fileoverview Ficha de Vistoria imprimível (A4), em branco para preenchimento
 * manual no veículo. Layout de formulário "quadriculado" (moldura contínua,
 * células com borda, checklist em tabela OK/N-OK/Reparar), no estilo das fichas
 * de oficina em papel. Calibrada para ocupar uma folha A4 inteira sem transbordar.
 * Dirigida pelo contrato do segmento (/definicao-campos): lista os acessórios e o
 * checklist corretos sem hardcode.
 *
 * Recebe as PEÇAS (cliente + objeto) em vez de uma OS pronta, para funcionar
 * também ANTES da OS existir (modo criação): imprime com o que já está no form.
 */
import { computed } from 'vue';

import {
  useCompanyPrintInfo,
  getClienteNome,
  getClienteDoc,
  getClientePhone,
  formatPrintDate,
  formatPrintDoc,
  formatPrintPhone,
} from '@/shared/utils/print.utils';


import { useOSFieldDefinition } from '@/modules/order-service/shared/segmento/useOSFieldDefinition.queries';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';
import { corPorTipo, type MarcaDano } from '../types/mapeamentoDanos.types';

interface FichaObjeto {
  marca?: string | null;
  modelo?: string | null;
  numero_serie?: string | null;
  cor?: string | null;
  dados_adicionais?: Record<string, unknown> | null;
}

const props = defineProps<{
  cliente: Record<string, unknown> | null;
  objeto: FichaObjeto | null;
  numeroOs?: string | null;
  dataOs?: string | null;
  tipo: 'ENTRADA' | 'SAIDA';
  /**
   * Quando presente, a ficha sai PREENCHIDA com o que foi marcado na tela
   * (acessórios, checklist, pneus/estepe, danos). É o `dados_adicionais` da OS
   * (mesmo formato que a OSVistoriaTab manipula). Ausente = ficha em branco.
   */
  preenchimento?: Record<string, unknown> | null;
}>();

const { companyInfo } = useCompanyPrintInfo();
const { data } = useOSFieldDefinition();
const { labelIdentificador } = useObjetoLabels();

const definicao = computed(() => data.value?.definicao ?? null);
const acessorios = computed<string[]>(() => definicao.value?.acessorios ?? []);
const grupos = computed(() => definicao.value?.vistoria ?? []);

const titulo = computed(() =>
  props.tipo === 'ENTRADA' ? 'FICHA DE VISTORIA DE ENTRADA' : 'FICHA DE VISTORIA DE SAÍDA',
);
const kmLabel = computed(() => (props.tipo === 'ENTRADA' ? 'KM Entrada' : 'KM Saída'));
const numeroExibicao = computed(() => props.numeroOs || '—');
const dataExibicao = computed(() =>
  props.dataOs ? formatPrintDate(props.dataOs) : formatPrintDate(new Date().toISOString()),
);

const clienteNome = computed(() => (props.cliente ? getClienteNome(props.cliente as any) : ''));

const objetoDados = computed<Record<string, unknown>>(() => props.objeto?.dados_adicionais ?? {});

/** Converte o slug do contrato (ex: chave_de_roda) em rótulo (Chave de roda). */
function rotulo(slug: string): string {
  const s = slug.replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function dado(chave: string): string {
  const v = objetoDados.value[chave];
  return v === null || v === undefined ? '' : String(v);
}

const niveisCombustivel = ['Reserva', '1/4', '1/2', '3/4', 'Cheio'];
const estadosPecas = ['Bom', 'Regular', 'Ruim'];

// ─── Modo preenchido ───────────────────────────────────────────────────────
// Quando `preenchimento` chega, marcamos na ficha o que foi selecionado na tela.
const preench = computed<Record<string, unknown> | null>(() => props.preenchimento ?? null);
const isPreenchida = computed(() => preench.value !== null);

const acessoriosSel = computed<Record<string, boolean>>(
  () => (preench.value?.acessorios as Record<string, boolean>) ?? {},
);
const acessoriosOutros = computed<string>(() => (preench.value?.acessorios_outros as string) ?? '');
const vistoriaSel = computed<Record<string, string>>(
  () => (preench.value?.vistoria as Record<string, string>) ?? {},
);
const danos = computed<MarcaDano[]>(() => (preench.value?.mapeamento_danos as MarcaDano[]) ?? []);

/** Valor de check-in salvo direto no dados_adicionais (ex: pneus_estado, km_entrada). */
function pd(chave: string): string {
  const v = preench.value?.[chave];
  return v === null || v === undefined ? '' : String(v);
}

/** True se o check-in `campo` tem o valor `label` (compara ignorando caixa). */
function checkinMarcado(campo: string, label: string): boolean {
  const v = preench.value?.[campo];
  return typeof v === 'string' && v.toUpperCase() === label.toUpperCase();
}

/** Estado marcado do item do checklist (OK / N_OK / REPARAR). Vazio se não marcado. */
function vistoriaEstado(grupoIdx: number, item: string): string {
  return vistoriaSel.value[`${grupoIdx}_${item}`] ?? '';
}

</script>

<template>
  <Teleport to="body">
    <div class="print-container ficha-a4 hidden print:block bg-white text-black font-sans leading-tight">
      <!-- Moldura contínua do formulário -->
      <div class="border-2 border-slate-800">
        <!-- Cabeçalho: empresa + Nº da O.S. -->
        <div class="flex items-stretch border-b-2 border-slate-800">
          <div class="w-20 flex items-center justify-center border-r border-slate-800 p-1 shrink-0">
            <img
              v-if="companyInfo.logo"
              :src="companyInfo.logo"
              alt="Logo"
              class="max-w-full max-h-13 object-contain"
            />
            <span v-else class="text-[9px] text-slate-400 text-center uppercase tracking-wide">Logo</span>
          </div>
          <div class="flex-1 px-2 py-0.5 border-r border-slate-800">
            <h1 class="text-lg font-black uppercase leading-tight text-slate-900">{{ companyInfo.nome }}</h1>
            <p v-if="companyInfo.razaoSocial" class="text-[9px] uppercase font-semibold text-slate-500">
              {{ companyInfo.razaoSocial }}
            </p>
            <p class="text-[11px] text-slate-700 mt-0.5">{{ companyInfo.endereco }}</p>
            <div class="text-[11px] text-slate-700 mt-0.5 space-y-0.5">
              <p v-if="companyInfo.cnpj">{{ companyInfo.labelDocumento }}: {{ companyInfo.cnpj }}</p>
              <p v-if="companyInfo.contato">Celular: {{ companyInfo.contato }}</p>
            </div>
          </div>
          <div class="w-36 shrink-0 flex flex-col">
            <div class="bg-slate-800 text-white text-center py-1">
              <p class="text-[9px] font-bold uppercase tracking-wider">O.S. Nº</p>
              <p class="text-xl font-mono font-black leading-none">{{ numeroExibicao }}</p>
            </div>
            <div class="flex-1 flex flex-col items-center justify-center py-1">
              <p class="text-[9px] font-bold uppercase text-slate-500">Data</p>
              <p class="text-sm font-bold text-slate-800">{{ dataExibicao }}</p>
            </div>
          </div>
        </div>

        <!-- Título -->
        <div class="text-center py-0.5 bg-slate-100 border-b-2 border-slate-800">
          <h2 class="text-base font-black text-slate-800 uppercase tracking-widest">{{ titulo }}</h2>
        </div>

        <!-- Dados do cliente -->
        <div class="grid grid-cols-[1fr_1fr_1fr] text-xs border-b border-slate-800">
          <div class="px-2 py-0.5 border-r border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Cliente</span>
            {{ clienteNome || '—' }}
          </div>
          <div class="px-2 py-0.5 border-r border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">CPF / CNPJ</span>
            {{ formatPrintDoc(getClienteDoc(cliente as any)) }}
          </div>
          <div class="px-2 py-0.5">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Telefone</span>
            {{ formatPrintPhone(getClientePhone(cliente as any)) }}
          </div>
        </div>

        <!-- Dados do veículo -->
        <div class="grid grid-cols-4 text-xs border-b border-slate-800">
          <div class="px-2 py-0.5 border-r border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Marca</span>
            {{ objeto?.marca || '' }}&nbsp;
          </div>
          <div class="px-2 py-0.5 border-r border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Modelo</span>
            {{ objeto?.modelo || '' }}&nbsp;
          </div>
          <div class="px-2 py-0.5 border-r border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Cor</span>
            {{ objeto?.cor || '' }}&nbsp;
          </div>
          <div class="px-2 py-0.5">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Ano</span>
            {{ dado('ano') }}&nbsp;
          </div>
          <div class="px-2 py-0.5 border-r border-t border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">{{ labelIdentificador }}</span>
            {{ objeto?.numero_serie || '' }}&nbsp;
          </div>
          <div class="px-2 py-0.5 border-r border-t border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Chassi</span>
            {{ dado('chassi') }}&nbsp;
          </div>
          <div class="px-2 py-0.5 border-r border-t border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">{{ kmLabel }}</span>
            {{ isPreenchida ? pd('km_entrada') : '' }}&nbsp;
          </div>
          <div class="px-2 py-0.5 border-t border-slate-800">
            <span class="text-[9px] font-bold uppercase text-slate-500 block">Prisma</span>
            {{ isPreenchida ? pd('prisma') : '' }}&nbsp;
          </div>
        </div>

        <!-- Diagrama + combustível/acessórios -->
        <div class="grid grid-cols-[1fr_1.3fr] border-b-2 border-slate-800">
          <!-- Avarias: ilustração das 5 vistas do veículo (superior, laterais, frente, traseira) -->
          <div class="border-r border-slate-800 p-1 flex flex-col items-center justify-center">
            <p class="text-[8px] font-bold uppercase text-slate-500 text-center leading-none mb-0.5">
              {{ isPreenchida ? 'Avarias registradas' : 'Avarias — marque com X' }}
            </p>
            <!-- Em branco: apenas a ilustração -->
            <img
              v-if="!isPreenchida"
              src="/vistoria-carro.png"
              alt="Vistas do veículo: superior, laterais, frente e traseira"
              class="w-full object-contain"
              style="max-height: 36mm"
            />
            <!-- Preenchida: ilustração + marcadores de dano sobrepostos (coords em %) -->
            <div v-else class="relative w-full" style="max-width: 48mm">
              <img
                src="/vistoria-carro.png"
                alt="Vistas do veículo: superior, laterais, frente e traseira"
                class="block w-full h-auto"
              />
              <svg
                v-if="danos.length"
                class="absolute inset-0 w-full h-full"
                viewBox="0 0 1000 750"
                preserveAspectRatio="none"
              >
                <g v-for="m in danos" :key="m.id">
                  <circle :cx="m.x * 10" :cy="m.y * 7.5" r="13" :fill="corPorTipo(m.tipo)" stroke="white" stroke-width="2.5" />
                  <circle :cx="m.x * 10" :cy="m.y * 7.5" r="4" fill="white" />
                </g>
              </svg>
            </div>
          </div>
          <div>
            <!-- Combustível -->
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 px-2 py-1 border-b border-slate-800 text-xs">
              <span class="font-bold uppercase text-slate-600 text-[10px]">Combustível:</span>
              <span v-for="n in niveisCombustivel" :key="n" class="inline-flex items-center gap-1">
                <span
                  class="inline-block w-3 h-3 rounded-full border border-slate-600"
                  :class="{ 'bg-slate-800': isPreenchida && checkinMarcado('combustivel_nivel', n) }"
                ></span>{{ n }}
              </span>
            </div>
            <!-- Pneus / Estepe -->
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 py-1 border-b border-slate-800 text-xs">
              <span class="inline-flex items-center gap-1.5">
                <span class="font-bold uppercase text-slate-600 text-[10px]">Pneus:</span>
                <span v-for="e in estadosPecas" :key="'pneu-' + e" class="inline-flex items-center gap-1">
                  <span
                    class="inline-block w-3 h-3 rounded-full border border-slate-600"
                    :class="{ 'bg-slate-800': isPreenchida && checkinMarcado('pneus_estado', e) }"
                  ></span>{{ e }}
                </span>
              </span>
              <span class="inline-flex items-center gap-1.5">
                <span class="font-bold uppercase text-slate-600 text-[10px]">Estepe:</span>
                <span v-for="e in estadosPecas" :key="'estepe-' + e" class="inline-flex items-center gap-1">
                  <span
                    class="inline-block w-3 h-3 rounded-full border border-slate-600"
                    :class="{ 'bg-slate-800': isPreenchida && checkinMarcado('estepe_estado', e) }"
                  ></span>{{ e }}
                </span>
              </span>
            </div>
            <!-- Acessórios -->
            <div class="px-2 py-1">
              <p class="text-[10px] font-bold uppercase text-slate-600 mb-1">Acessórios presentes</p>
              <div v-if="acessorios.length" class="grid grid-cols-3 gap-x-3 gap-y-1 text-xs">
                <span v-for="ac in acessorios" :key="ac" class="flex items-center gap-1.5">
                  <span class="inline-flex items-center justify-center w-3 h-3 border border-slate-600 shrink-0 text-[10px] font-black leading-none text-slate-800">
                    <template v-if="isPreenchida && acessoriosSel[ac]">✕</template>
                  </span>
                  <span class="shrink-0">{{ rotulo(ac) }}</span>
                  <span v-if="ac === 'outros'" class="flex-1 self-end border-b border-dotted border-slate-400 text-[10px] leading-tight">
                    {{ isPreenchida ? acessoriosOutros : '' }}&nbsp;
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Checklists de inspeção (uma tabela por grupo) -->
        <table
          v-for="(grupo, gi) in grupos"
          :key="grupo.titulo"
          class="w-full border-collapse text-[12px] border-b border-slate-800"
        >
          <thead>
            <tr class="bg-slate-100">
              <th class="border-r border-b border-slate-800 text-left px-2 py-0.5 font-bold uppercase text-[11px] text-slate-700">
                {{ grupo.titulo }}
              </th>
              <th class="border-r border-b border-slate-800 w-12 py-0.5 font-bold text-[10px] text-slate-700">OK</th>
              <th class="border-r border-b border-slate-800 w-12 py-0.5 font-bold text-[10px] text-slate-700">N/OK</th>
              <th class="border-b border-slate-800 w-14 py-0.5 font-bold text-[10px] text-slate-700">Reparar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in grupo.itens" :key="item">
              <td class="border-r border-b border-slate-300 px-2 py-px leading-tight text-slate-700">{{ rotulo(item) }}</td>
              <td class="border-r border-b border-slate-300 text-center font-black text-slate-800">
                {{ vistoriaEstado(gi, item) === 'OK' ? '✕' : '' }}
              </td>
              <td class="border-r border-b border-slate-300 text-center font-black text-slate-800">
                {{ vistoriaEstado(gi, item) === 'N_OK' ? '✕' : '' }}
              </td>
              <td class="border-b border-slate-300 text-center font-black text-slate-800">
                {{ vistoriaEstado(gi, item) === 'REPARAR' ? '✕' : '' }}
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Assinatura -->
        <div class="grid grid-cols-2 text-xs border-t-2 border-slate-800">
          <div class="px-2 py-1 border-r border-slate-800 font-bold uppercase text-slate-700 flex items-end">
            De acordo com a vistoria
          </div>
          <div class="px-4 pb-1 text-center" :class="isPreenchida ? 'pt-6' : 'pt-8'">
            <div class="border-t border-slate-700 pt-1">
              <span class="text-[10px] uppercase text-slate-500">Assinatura do Cliente</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  </Teleport>
</template>

<style scoped>
/* A margem da ficha é do próprio container (não do @page global, compartilhado
   com as impressões de OS/venda em produção). A margem VERTICAL fica no @page
   (repete em toda página, inclusive o topo da 2ª folha, evitando corte); a
   HORIZONTAL fica no padding do container (independe do diálogo de impressão). */
@media print {
  @page ficha-vistoria {
    size: A4;
    margin: 0;
  }

  .ficha-a4 {
    page: ficha-vistoria;
    box-sizing: border-box;
    padding: 8mm 10mm !important;
  }

  /* Permite quebra entre linhas do checklist, mas nunca dentro de uma linha
     nem do cabeçalho do grupo (que se repete no topo se a tabela virar página). */
  .ficha-a4 table {
    break-inside: auto;
  }
  .ficha-a4 tr,
  .ficha-a4 thead {
    break-inside: avoid;
  }

}
</style>
