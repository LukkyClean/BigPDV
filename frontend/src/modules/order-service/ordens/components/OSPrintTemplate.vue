<script setup lang="ts">
import { computed } from 'vue';
import {
  User,
  CheckCircle2,
  CreditCard,
  Receipt,
  Banknote,
  Image as ImageIcon,
} from 'lucide-vue-next';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import { formatCurrency } from '@/shared/utils/finance';
import { usePerfilComprovante } from '@/shared/composables/usePerfilComprovante';
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
  pixParaImpressao,
  getImageUrl,
} from '@/shared/utils/print.utils';

import PixQrPrint from '@/shared/components/print/PixQrPrint.vue';
import PrintCompanyHeader from '@/shared/components/print/a4/PrintCompanyHeader.vue';
import PrintSignatures from '@/shared/components/print/a4/PrintSignatures.vue';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';
import { useTextosImpressaoOS, prazoPorExtenso } from '@/modules/order-service/shared/segmento/textosImpressaoOS';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { useTiposDeTrabalho } from '@/modules/order-service/shared/segmento/useTiposDeTrabalho';
import { useAtributosImpressaoOS } from '@/modules/order-service/shared/segmento/useAtributosImpressaoOS';
import { useCapacidades } from '@/modules/order-service/shared/segmento/useCapacidades';
import { formatGarantiaItem } from '@/modules/order-service/shared/utils/formatters';

const props = defineProps<{
  ordemServico: OrderServiceReadDataType | null;
  type: 'ENTRADA' | 'SAIDA' | 'CANCELAMENTO';
}>();

const { companyInfo } = useCompanyPrintInfo();

// Densidade do layout. O documento é passado porque entrada e entrega podem
// querer apresentações diferentes (a Fase 4 do plano declara por documento).
const { classeDensidade } = usePerfilComprovante(
  props.type === 'ENTRADA' ? 'os_entrada' : 'os_entrega',
);
const { labelSingular, objetoIcon, labelDaColuna } = useObjetoLabels();
const { tipoPorId } = useTiposDeTrabalho();
// Gate das imagens na via: capacidade do registry, não nome de segmento.
const { temImagemNaEntrada, temGarantiaPrazo } = useCapacidades();
// Os termos mudam com o tipo de trabalho: a cláusula de "peças entregues pelo
// cliente" é de camisa e não vale para sacola, que a loja produz do zero.
const { textos, identificadorA4 } = useTextosImpressaoOS(
  () => (props.ordemServico?.dados_adicionais as Record<string, unknown> | undefined)
    ?.tipo_trabalho as string | undefined,
);
const { atributos } = useAtributosImpressaoOS();

/**
 * Prazo de abandono vindo de Configurações → Ordens de Serviço. Estava chumbado
 * em "90 (noventa)" aqui: a loja mudava a configuração, o relatório de abandono
 * obedecia e o papel entregue ao cliente continuava prometendo 90.
 */
const configuracoesStore = useConfiguracoesStore();
const prazoAbandonoTexto = computed(() =>
  prazoPorExtenso(configuracoesStore.prazoAbandonoDias),
);

/**
 * A cláusula do Termo de Garantia sempre escreveu o prazo sem o por extenso
 * ("90 dias", não "90 (noventa) dias"). Mantido como estava.
 */
const prazoAbandonoSimples = computed(
  () => `${configuracoesStore.prazoAbandonoDias} dias`,
);

/**
 * Imagens que saem na via de entrada, já com a URL absoluta do backend.
 *
 * Teto de 4: a via de entrada é uma folha só e precisa caber com os termos e as
 * assinaturas. Quem anexou mais continua vendo tudo na galeria da OS.
 */
const MAX_FOTOS_IMPRESSAS = 4;

const fotosImpressas = computed(() =>
  (props.ordemServico?.fotos ?? [])
    .slice(0, MAX_FOTOS_IMPRESSAS)
    .map((foto) => ({ ...foto, src: getImageUrl(foto.url) ?? '' }))
    .filter((foto) => foto.src !== ''),
);

/**
 * Densidade do layout desta via.
 *
 * A via de entrada que LEVA ARTE é **sempre compacta**, por mais que a empresa
 * tenha escolhido Normal. Não é preferência de forma: é a diferença entre a
 * arte sair utilizável ou não. Medido nesta mesma via (foto de celular, folha
 * A4, uma página): no Normal a via fecha em 291mm de 293mm disponíveis e a arte
 * cabe em 34x45mm; no compacto a via cai para 286mm e a arte sobe para 90x120mm
 * — sete vezes a área, na mesma folha única.
 *
 * O compacto não tira informação nenhuma (§4 do plano): encolhe moldura e
 * espaçamento. Numa via cujo motivo de existir é a arte que o cliente aprovou e
 * o estampador vai reproduzir, gastar esses milímetros com respiro é o mesmo
 * que imprimir a via errada.
 *
 * Repare no `fotosImpressas.length`: a condição é a arte ESTAR NA VIA, não o
 * segmento poder ter arte. Numa OS sem foto anexada o bloco nem é renderizado —
 * não há o que espremer, e sobrescrever a escolha da empresa ali seria mudar o
 * comprovante dela sem nada em troca.
 */
const classeImpressao = computed(() =>
  props.type === 'ENTRADA' && temImagemNaEntrada.value && fotosImpressas.value.length
    ? 'compacto'
    : classeDensidade.value,
);

/**
 * Divide a cláusula no prazo para manter o número em negrito, como as vias em
 * produção sempre imprimiram. Determinístico: as duas pontas do corte são
 * strings que nós mesmos montamos. Se o prazo não for encontrado (pacote
 * reescrito sem ele), imprime a frase inteira sem negrito em vez de sumir.
 */
const prazoRetiradaPartes = computed(() => {
  const prazo = prazoAbandonoTexto.value;
  const frase = textos.value.prazoRetiradaEntradaA4(prazo);
  const corte = frase.indexOf(prazo);
  if (corte === -1) return { antes: frase, depois: '' };
  return { antes: frase.slice(0, corte), depois: frase.slice(corte + prazo.length) };
});

/**
 * Atributos do segmento além das linhas fixas (oficina: Ano, Chassi, KM de
 * entrada). Vem do contrato — em informática a lista é vazia.
 */
const atributosObjeto = computed(() =>
  atributos(
    props.ordemServico?.objeto?.dados_adicionais,
    props.ordemServico?.dados_adicionais,
  ),
);

// O "tipo" só aparece quando acrescenta info além do rótulo do segmento (em
// oficina ele é o próprio "Veículo" → redundante sob "Dados do Veículo").
const mostrarTipoObjeto = computed(() =>
  tipoObjetoRelevante(props.ordemServico?.objeto?.tipo_equipamento, labelSingular.value),
);

/**
 * Linha em destaque sob o cabeçalho do quadro.
 *
 * Em segmento com tipos de trabalho, é o TIPO ("Camisa (pintura)", "Sacola de
 * papel") — que é o que quem vai produzir precisa ler primeiro. Antes saía
 * "Equipamento" ali, herdado do shim de compatibilidade: uma palavra que não
 * diz nada numa OS de arte.
 *
 * Nos demais segmentos, continua sendo o `tipo_equipamento` de sempre.
 */
const subtituloObjeto = computed<string | null>(() => {
  const tipo = tipoPorId(props.ordemServico?.dados_adicionais?.tipo_trabalho as string | undefined);
  if (tipo) return tipo.label;
  return mostrarTipoObjeto.value
    ? (props.ordemServico?.objeto?.tipo_equipamento ?? null)
    : null;
});

const situacao = computed(() => props.ordemServico?.situacao_equipamento ?? null);

const isSemReparo = computed(() =>
  situacao.value === 'SEM_REPARO' || situacao.value === 'CONDENADO'
);

// O substantivo vem do pacote do segmento, não de `labelSingular`: a oficina
// precisa ler "VEÍCULO" no lugar de "OBJETO", e informática tem que continuar
// lendo "OBJETO" — que é o que ela sempre imprimiu.
const objetoNoTitulo = computed(() => textos.value.objeto.toUpperCase());

const title = computed(() => {
  if (props.type === 'ENTRADA') return `COMPROVANTE DE ENTRADA DE ${objetoNoTitulo.value}`;
  if (props.type === 'CANCELAMENTO') return 'DECLARAÇÃO DE CANCELAMENTO DE SERVIÇO';
  if (situacao.value === 'SEM_REPARO') return 'DECLARAÇÃO DE ENTREGA SEM REPARO';
  if (situacao.value === 'CONDENADO') return `DECLARAÇÃO DE ${objetoNoTitulo.value} CONDENADO`;
  return 'RECIBO E TERMO DE GARANTIA';
});

// Impressão é preto e branco por contrato (ver nota no topo do template): as três
// situações compartilham o mesmo estilo porque quem distingue é o `label`, escrito
// por extenso. A cor era redundante com ele.
const situacaoConfig = computed(() => {
  const CLS_SITUACAO = 'bg-neutral-100 text-neutral-900 border border-neutral-400';
  const map: Record<string, { label: string; cls: string }> = {
    REPARADO:   { label: 'Reparado',   cls: CLS_SITUACAO },
    SEM_REPARO: { label: 'Sem Reparo', cls: CLS_SITUACAO },
    CONDENADO:  { label: 'Condenado',  cls: CLS_SITUACAO },
  };
  return situacao.value ? map[situacao.value] ?? null : null;
});

const motivoCancelamento = computed(() => {
  const obs = props.ordemServico?.observacoes ?? '';
  const match = obs.match(/\[CANCELAMENTO\]\s*([\s\S]+)/);
  return match ? match[1].trim() : 'Motivo não informado.';
});

// Peça embutida no serviço não é listada para o cliente: ela existe na OS, dá
// baixa no estoque e entra no custo, mas a via impressa mostra só o serviço.
// `!== false` e não `=== true`: item antigo vem sem o campo e tem que continuar
// aparecendo, exatamente como sempre apareceu.
// Item REPROVADO também sai: o cliente recusou, não foi feito, e o backend já o
// tira do valor_total. Listado aqui ele aparecia com preço na via e entrava no
// Subtotal impresso — a conta não fechava contra o total que ele pagou.
// `!== 'REPROVADO'` e não `=== 'APROVADO'`: item sem o campo (informática, e
// qualquer OS anterior a esta coluna) tem que continuar aparecendo.
const itensVisiveis = computed(() =>
  (props.ordemServico?.itens ?? []).filter(
    (item) => item.visivel_cliente !== false && item.status_aprovacao !== 'REPROVADO',
  ),
);

// Somado sobre os visíveis para a via fechar por construção: o cliente consegue
// conferir a conta com as linhas que ele tem na mão.
const subtotal = computed(() =>
  itensVisiveis.value.reduce((acc, item) => acc + item.valor_total, 0),
);

/**
 * Algum item traz garantia própria?
 *
 * Quando traz, o termo geral NÃO pode dizer que cobre as peças: a linha do item
 * diz outra coisa (ex: peça 90 dias / 1.000 km contra serviço de 30 dias) e o
 * documento passaria a se contradizer — num conflito desses quem perde é quem
 * escreveu o papel.
 *
 * Em informática isto nunca é verdadeiro: o segmento não declara garantia por
 * item, então o termo continua exatamente o que sempre foi.
 */
const temGarantiaPorItem = computed(() =>
  itensVisiveis.value.some((item) => formatGarantiaItem(item) !== ''),
);

const adiantamento = computed(() => props.ordemServico?.valor_entrada ?? 0);
// Null em OS anterior a este campo: a via sai só com o valor, como antes.
const formaEntradaNome = computed(
  () => props.ordemServico?.forma_pagamento_entrada?.nome ?? null,
);

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

/** QR do PIX no papel — só quando há pagamento em PIX e a loja tem chave ativa. */
const pix = computed(() =>
  pixParaImpressao({
    empresa: companyInfo.value,
    pagamentos: props.ordemServico?.pagamentos?.map((pgto) => ({
      nome: pgto.forma_pagamento?.nome || '',
      valor: pgto.valor,
    })),
    txid: props.ordemServico?.numero_os ?? undefined,
  }),
);
</script>

<template>
  <Teleport to="body">
  <div
    v-if="ordemServico"
    class="print-container hidden print:block bg-white text-black font-sans leading-tight"
    :class="classeImpressao"
  >
    <PrintCompanyHeader
      :company="companyInfo"
      document-label="Número da O.S."
      :document-number="ordemServico.numero_os || String(ordemServico.id).padStart(6, '0')"
      date-label="Data Entrada"
      :date-value="formatPrintDate(ordemServico.data_criacao)"
      :finalizada-date="ordemServico.data_finalizacao ? formatPrintDate(ordemServico.data_finalizacao) : undefined"
    />

    <div class="text-center py-2 mb-4 border-y-2 border-neutral-200 bg-neutral-50">
      <h2 class="text-lg font-black text-neutral-900 uppercase tracking-widest">{{ title }}</h2>
    </div>

    <div class="grid grid-cols-2 gap-4 mb-4">
      <div class="border border-neutral-300 rounded-lg overflow-hidden">
        <div class="bg-neutral-100 px-3 py-1.5 border-b border-neutral-200 flex items-center gap-2">
          <User :size="14" class="text-neutral-600" />
          <h3 class="text-xs font-bold uppercase text-neutral-800">Dados do Cliente</h3>
        </div>
        <div class="p-3 text-xs space-y-1.5">
          <p><span class="font-bold text-neutral-700">Nome:</span> {{ ordemServico.cliente ? getClienteNome(ordemServico.cliente) : 'Consumidor' }}</p>
          <div class="flex gap-4">
            <p><span class="font-bold text-neutral-700">CPF/CNPJ:</span> {{ formatPrintDoc(getClienteDoc(ordemServico.cliente)) }}</p>
            <p><span class="font-bold text-neutral-700">Telefone:</span> {{ formatPrintPhone(getClientePhone(ordemServico.cliente as any)) }}</p>
          </div>
          <p v-if="getClienteEndereco(ordemServico.cliente)"><span class="font-bold text-neutral-700">Endereço:</span> {{ getClienteEndereco(ordemServico.cliente) }}</p>
          <p v-if="ordemServico.cliente?.id"><span class="font-bold text-neutral-700">Cód. Cliente:</span> #{{ ordemServico.cliente.id }}</p>
        </div>
      </div>

      <div class="border border-neutral-300 rounded-lg overflow-hidden">
        <div class="bg-neutral-100 px-3 py-1.5 border-b border-neutral-200 flex items-center gap-2">
          <component :is="objetoIcon" :size="14" class="text-neutral-600" />
          <h3 class="text-xs font-bold uppercase text-neutral-800">{{ textos.tituloObjeto }}</h3>
        </div>
        <div class="p-3 text-xs space-y-1.5">
          <div v-if="subtituloObjeto || situacaoConfig" class="flex items-center gap-2">
            <p v-if="subtituloObjeto" class="text-sm font-bold text-neutral-900">{{ subtituloObjeto }}</p>
            <span v-if="situacaoConfig" :class="['px-2 py-0.5 rounded-full text-[10px] font-bold', situacaoConfig.cls]">
              {{ situacaoConfig.label }}
            </span>
          </div>
          <!-- Rótulos das colunas vêm do contrato: em serigrafia, "Marca" e
               "Modelo" são "Empresa / Marca da estampa" e "Nome da arte". -->
          <div class="grid grid-cols-2 gap-2">
            <p v-if="ordemServico.objeto.marca">
              <span class="font-bold text-neutral-700">{{ labelDaColuna('marca', 'Marca') }}:</span>
              {{ ordemServico.objeto.marca }}
            </p>
            <p v-if="ordemServico.objeto.modelo">
              <span class="font-bold text-neutral-700">{{ labelDaColuna('modelo', 'Modelo') }}:</span>
              {{ ordemServico.objeto.modelo }}
            </p>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <p><span class="font-bold text-neutral-700">{{ identificadorA4 }}:</span> {{ ordemServico.objeto.numero_serie || '-' }}</p>
            <!-- "Cor: -" ocupava linha sem dizer nada; a arte nem tem cor. -->
            <p v-if="ordemServico.objeto.cor">
              <span class="font-bold text-neutral-700">{{ labelDaColuna('cor', 'Cor') }}:</span>
              {{ ordemServico.objeto.cor }}
            </p>
          </div>
          <!-- Atributos do segmento (oficina: Ano, Chassi, KM de entrada). -->
          <div v-if="atributosObjeto.length" class="grid grid-cols-2 gap-2">
            <p v-for="attr in atributosObjeto" :key="attr.label">
              <span class="font-bold text-neutral-700">{{ attr.label }}:</span> {{ attr.valor }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="mb-4 space-y-2">
      <div class="border border-neutral-300 rounded-lg p-3 bg-neutral-50/50">
        <p class="text-[10px] font-bold text-neutral-600 uppercase mb-1">{{ textos.defeito }}</p>
        <p class="text-xs text-neutral-900 font-medium">{{ ordemServico.defeito_relatado }}</p>
      </div>
      <div v-if="ordemServico.observacoes" class="border border-dashed border-neutral-300 rounded-lg p-3">
        <p class="text-[10px] font-bold text-neutral-600 uppercase mb-1">Observações / Acessórios</p>
        <p class="text-xs text-neutral-800 whitespace-pre-line">{{ ordemServico.observacoes }}</p>
      </div>
    </div>

    <!--
      Imagens na via de ENTRADA — só onde a imagem é o pedido (serigrafia: a
      foto é a arte a estampar, e é dela que quem pinta trabalha). Em oficina e
      informática a foto é prova do estado do bem e não vai para o papel: por
      isso o gate é a capacidade, não o segmento.
    -->
    <div
      v-if="type === 'ENTRADA' && temImagemNaEntrada && fotosImpressas.length"
      class="mb-3 border border-neutral-300 rounded-lg overflow-hidden print-fotos"
      :class="{ varias: fotosImpressas.length > 1 }"
    >
      <div class="bg-neutral-100 px-3 py-1 border-b border-neutral-200 flex items-center gap-2">
        <ImageIcon :size="14" class="text-neutral-800" />
        <h3 class="text-xs font-bold uppercase text-neutral-800">
          {{ fotosImpressas.length === 1 ? 'Arte para Produção' : 'Artes para Produção' }}
        </h3>
      </div>
      <div class="p-2" :class="fotosImpressas.length === 1 ? '' : 'grid grid-cols-2 gap-2'">
        <figure
          v-for="foto in fotosImpressas"
          :key="foto.id"
          class="border border-neutral-200 rounded overflow-hidden bg-white"
        >
          <!--
            Sem `w-full`, sem `object-contain` e sem tamanho aqui: o tamanho
            impresso está no CSS (`.print-fotos img`), em MILÍMETROS, e a classe
            `foto-retrato` é posta por `classificarOrientacaoDasFotos`
            (print.utils.ts) na hora de imprimir — quando as imagens já
            carregaram e `naturalWidth/Height` valem alguma coisa.
          -->
          <img :src="foto.src" :alt="foto.nome_arquivo" />
        </figure>
      </div>
    </div>

    <!-- ── SAÍDA ── -->
    <template v-if="type === 'SAIDA'">
      <div v-if="ordemServico.solucao || ordemServico.diagnostico" class="mb-4 border border-neutral-300 rounded-lg overflow-hidden">
        <div class="bg-neutral-100 px-3 py-1.5 border-b border-neutral-200 flex items-center gap-2">
          <CheckCircle2 :size="14" class="text-neutral-800" />
          <h3 class="text-xs font-bold uppercase text-neutral-800">Laudo Técnico & Solução</h3>
        </div>
        <div class="p-3 text-xs space-y-2">
          <div v-if="ordemServico.diagnostico">
            <span class="font-bold text-neutral-700 uppercase text-[10px]">Diagnóstico:</span>
            <p class="text-neutral-900">{{ ordemServico.diagnostico }}</p>
          </div>
          <div v-if="ordemServico.solucao" class="pt-2 border-t border-neutral-100 mt-2">
            <span class="font-bold text-neutral-900 uppercase text-[10px]">Solução Realizada:</span>
            <p class="text-neutral-900 font-medium">{{ ordemServico.solucao }}</p>
          </div>
        </div>
      </div>

      <div class="mb-4" v-if="itensVisiveis.length">
        <table class="w-full text-xs text-left">
          <thead>
            <tr class="border-b-2 border-neutral-800">
              <th class="py-2 pl-2 text-neutral-700 uppercase font-bold w-[60%]">Descrição do Serviço / Peça</th>
              <th class="py-2 text-center text-neutral-700 uppercase font-bold w-[10%]">Qtd</th>
              <th class="py-2 text-right text-neutral-700 uppercase font-bold w-[15%]">Unit.</th>
              <th class="py-2 pr-2 text-right text-neutral-700 uppercase font-bold w-[15%]">Total</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-200">
            <tr v-for="item in itensVisiveis" :key="item.id">
              <td class="py-2 pl-2 text-neutral-900">
                {{ item.nome }}
                <!-- Garantia da peça: só sai quando o mecânico preencheu. -->
                <span v-if="formatGarantiaItem(item)" class="block text-[9px] text-neutral-600">
                  Garantia: {{ formatGarantiaItem(item) }}
                </span>
              </td>
              <td class="py-2 text-center text-neutral-700">{{ item.quantidade }}</td>
              <td class="py-2 text-right text-neutral-700">{{ formatCurrency(item.valor_unitario) }}</td>
              <td class="py-2 pr-2 text-right font-bold text-neutral-900">{{ formatCurrency(item.valor_total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="grid grid-cols-2 gap-6 mb-4">
        <!-- Detalhes do pagamento -->
        <div>
          <p class="text-[10px] font-bold text-neutral-600 uppercase mb-2 border-b border-neutral-200 pb-1">Detalhes do Pagamento</p>
          <!-- Adiantamento recebido na entrada -->
          <div v-if="adiantamento > 0" class="flex justify-between items-center text-xs bg-neutral-50 p-1.5 rounded border border-neutral-200 mb-1.5">
            <div class="flex items-center gap-2">
              <Banknote :size="12" class="text-neutral-800" />
              <span class="font-semibold text-neutral-900">
                Adiantamento (entrada)<template v-if="formaEntradaNome"> — {{ formaEntradaNome }}</template>
              </span>
            </div>
            <span class="font-bold text-neutral-900">{{ formatCurrency(adiantamento) }}</span>
          </div>
          <!-- Pagamentos no fechamento -->
          <div v-if="ordemServico.pagamentos?.length" class="space-y-1.5">
            <div v-for="pgto in ordemServico.pagamentos" :key="pgto.id" class="flex justify-between items-center text-xs bg-neutral-50 p-1.5 rounded border border-neutral-100">
              <div class="flex items-center gap-2">
                <CreditCard :size="12" class="text-neutral-600" />
                <span class="font-semibold text-neutral-800">
                  {{ getPaymentDisplayName(pgto.forma_pagamento?.nome || 'Pagamento') }}
                  <span v-if="pgto.parcelas > 1" class="text-[10px] text-neutral-600 font-normal">({{ pgto.parcelas }}x)</span>
                </span>
              </div>
              <span class="font-bold text-neutral-900">{{ formatCurrency(pgto.valor) }}</span>
            </div>
          </div>
          <div v-else-if="adiantamento === 0" class="text-xs text-neutral-600 italic py-2">Nenhum pagamento registrado.</div>
        </div>

        <!-- Resumo financeiro -->
        <div class="space-y-1 text-right">
          <!-- O cabeçalho não é enfeite: sem ele esta coluna começava no topo da
               linha do grid e o "Subtotal" alinhava com o TÍTULO da coluna de
               pagamentos, não com o conteúdo dela. -->
          <p class="text-[10px] font-bold text-neutral-600 uppercase mb-2 border-b border-neutral-200 pb-1 text-left">Resumo Financeiro</p>
          <div class="flex justify-between text-xs text-neutral-600">
            <span>Subtotal:</span>
            <span>{{ formatCurrency(subtotal) }}</span>
          </div>
          <div v-if="(ordemServico.desconto ?? 0) > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Desconto:</span>
            <span>- {{ formatCurrency(ordemServico.desconto ?? 0) }}</span>
          </div>
          <div v-if="(ordemServico.taxa_entrega ?? 0) > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Deslocamento:</span>
            <span>+ {{ formatCurrency(ordemServico.taxa_entrega ?? 0) }}</span>
          </div>
          <div v-if="(ordemServico.acrescimo ?? 0) > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Juros:</span>
            <span>+ {{ formatCurrency(ordemServico.acrescimo ?? 0) }}</span>
          </div>
          <div v-if="adiantamento > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Adiantamento:</span>
            <span>- {{ formatCurrency(adiantamentoUtilizado) }}</span>
          </div>
          <div class="border-t border-neutral-800 my-1 pt-1 flex justify-between items-end">
            <span class="text-sm font-bold text-neutral-900 uppercase">Total Pago:</span>
            <span class="text-xl font-black text-neutral-900 leading-none">{{ formatCurrency(totalRecebido) }}</span>
          </div>
          <div v-if="(ordemServico.acrescimo ?? 0) > 0" class="mt-1 border border-neutral-400 bg-neutral-50 rounded p-1.5 space-y-0.5">
            <p class="text-[9px] font-bold text-neutral-900 uppercase">Em caso de devolução</p>
            <div class="flex justify-between text-[9px] text-neutral-700">
              <span>Valor do serviço (dinheiro):</span>
              <span class="font-semibold">{{ formatCurrency(totalPago - (ordemServico.acrescimo ?? 0)) }}</span>
            </div>
            <div class="flex justify-between text-[9px] text-neutral-700">
              <span>Estorno no cartão:</span>
              <span class="font-semibold">{{ formatCurrency(totalPago) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- PIX: fecha o bloco financeiro, antes do termo de garantia -->
      <div v-if="pix" class="mb-6 border border-neutral-300 rounded-lg p-3 inline-block">
        <PixQrPrint :payload="pix.payload" :valor-centavos="pix.valorCentavos" lado="30mm" />
      </div>

      <!--
        Termo de Garantia — só para REPARADO e só onde há PRAZO de garantia.

        O texto abaixo cai em '90 (noventa) dias' quando `garantia` está vazia.
        Isso é correto onde a garantia é obrigatória (oficina, informática:
        sempre preenchida). Num segmento sem prazo — serigrafia, em que a
        estampa se mede em lavagens — o fallback faria a via PROMETER 90 dias de
        garantia que a loja nunca deu.
      -->
      <div v-if="!isSemReparo && temGarantiaPrazo" class="border border-neutral-300 bg-neutral-50 rounded-lg p-3 text-[10px] text-neutral-800 text-justify leading-relaxed mb-6">
        <div class="flex items-center gap-2 mb-1 font-bold text-neutral-900 uppercase">
          <Receipt :size="12" />
          Termo de Garantia
        </div>
        A garantia é válida por <strong>{{ ordemServico.garantia || '90 (noventa) dias' }}</strong> a contar desta data,
        <template v-if="temGarantiaPorItem">cobrindo os serviços prestados e as peças substituídas descritos neste documento, <strong>exceto quando houver garantia específica indicada na linha do item</strong>.</template>
        <template v-else>cobrindo exclusivamente os serviços prestados e peças substituídas descritos neste documento.</template>
        A garantia <strong>NÃO COBRE</strong>: {{ textos.garantiaExclusoes }}
        <br/>
        IMPORTANTE: {{ textos.prazoRetiradaGarantiaA4(prazoAbandonoSimples) }}
      </div>

      <!-- Declaração de entrega sem reparo (SEM_REPARO / CONDENADO) -->
      <div v-else class="border border-neutral-300 bg-neutral-50 rounded-lg p-3 text-[10px] text-neutral-800 text-justify leading-relaxed mb-6">
        <div class="flex items-center gap-2 mb-1 font-bold text-neutral-900 uppercase">
          <Receipt :size="12" />
          Declaração de Entrega
        </div>
        O {{ textos.objeto }} acima identificado está sendo devolvido ao cliente <strong>sem realização de reparo</strong>.
        {{ textos.empresa }} <strong>não oferece garantia</strong> sobre os serviços desta O.S.
        O cliente declara estar ciente da situação do {{ textos.objeto }} e recebe o mesmo conforme descrito neste documento.
      </div>
    </template>

    <!-- ── CANCELAMENTO ── -->
    <template v-else-if="type === 'CANCELAMENTO'">
      <div class="border border-neutral-400 bg-neutral-50 rounded-lg p-4 mb-6">
        <div class="flex items-center gap-2 mb-2 font-bold text-neutral-900 uppercase">
          <span class="p-1 bg-neutral-200 border border-neutral-400 rounded">CANCELAMENTO</span>
          Motivo do Cancelamento
        </div>
        <p class="text-sm text-neutral-900 font-medium">{{ motivoCancelamento }}</p>
      </div>
      <div class="border border-neutral-200 bg-neutral-50 rounded-lg p-3 text-[10px] text-neutral-600 text-justify leading-relaxed mb-6">
        <strong class="text-neutral-800 uppercase">Declaração:</strong>
        Declaro para os devidos fins que a Ordem de Serviço acima identificada foi cancelada na presente data.
        O {{ textos.objeto }} foi devolvido ao cliente no estado em que se encontrava, sem realização de reparos ou com reparos parciais conforme acordado, isentando {{ textos.empresa.toLowerCase() }} de garantias sobre serviços não concluídos.
      </div>
    </template>

    <!-- ── ENTRADA ── -->
    <div v-else class="border border-neutral-200 bg-neutral-50 rounded-lg p-3 text-[10px] text-neutral-600 text-justify leading-relaxed mb-8 space-y-2">
      <p>
        <strong class="text-neutral-800 uppercase">Condições de Entrada:</strong>
        {{ textos.condicoesEntrada }}
      </p>
      <p class="border-t border-neutral-200 pt-2">
        <strong class="text-neutral-800 uppercase">⚠ Prazo de Retirada:</strong>
        {{ prazoRetiradaPartes.antes }}<strong class="text-neutral-800">{{ prazoAbandonoTexto }}</strong>{{ prazoRetiradaPartes.depois }}
      </p>
    </div>

    <PrintSignatures
      :left-label="textos.assinaturaLoja"
      right-label="Assinatura do Cliente"
      :right-name="ordemServico.cliente ? getClienteNome(ordemServico.cliente) : undefined"
    />

    <PrintFooter />
  </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-a4.css';

/* =====================================================================
   ARTE PARA PRODUÇÃO (via de entrada, segmentos com imagem no pedido)

   A imagem NÃO usa `w-full`/`object-contain`. Aquela combinação dava à foto
   uma caixa da largura inteira do bloco e encaixava o retrato no meio dela:
   uma foto de celular saía com ~31mm de largura cercada de branco, pequena
   demais para produzir. Aqui a imagem é limitada pelos dois lados e a caixa
   encolhe até ela — o branco em volta some.

   Alturas em MILÍMETROS: o papel é medido em mm, e é o que decide se a via
   fecha em uma folha. Histórico do teto da arte deitada: 90mm empurrava termos
   e assinaturas para a segunda folha, 55mm ainda deixava o rodapé transbordar
   sozinho, 45mm fecha a via.

   O retrato tem teto maior de propósito. Não é privilégio: a 45mm uma foto 3:4
   ocupa 34x45mm, contra os ~155x45mm da arte deitada — um quarto da área. Os
   68mm igualam as duas em tamanho aparente (51x68mm), e custam altura só na OS
   que tem foto de celular.
   ===================================================================== */
.print-fotos img {
  display: block;
  margin: 0 auto;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 45mm;
}

/* A moldura acompanha a foto em vez de atravessar a via.
   Com a moldura em largura total, um retrato de 25mm ficava no meio de um
   retângulo vazio de 175mm — o branco em volta parecia defeito de impressão, e
   era a maior parte do bloco.

   `fit-content` + `margin-inline: auto` e não `inline-block` + `text-align` do
   pai: assim a centralização mora inteira na própria moldura e não depende de
   classe nenhuma no elemento de cima. Só no caso de arte única — com duas ou
   mais, cada célula da grade já tem metade da largura. */
.print-fotos:not(.varias) figure {
  width: fit-content;
  margin-inline: auto;
}

/* O teto do retrato é o único tamanho ELÁSTICO da via: quando a folha inteira
   não fecha em uma página, `ajustarArteParaCaber` (print.utils.ts) baixa esta
   variável degrau a degrau até caber. A arte é o que dá para ceder — o resto do
   comprovante é conteúdo que protege o cliente. */
.print-fotos img.foto-retrato {
  max-height: var(--arte-retrato, 68mm);
}

/* Duas ou mais artes dividem a linha: cada uma cabe em metade do espaço. */
.print-fotos.varias img {
  max-height: 30mm;
}

.print-fotos.varias img.foto-retrato {
  max-height: 45mm;
}
</style>
