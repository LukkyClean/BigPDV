<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import OSFormModalShell from './form/OSFormModalShell.vue';
import OSFormAuxModals from './form/OSFormAuxModals.vue';
import OSVistoriaFichaPrint from './OSVistoriaFichaPrint.vue';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import type { CustomerUnionReadSchemaDataType } from '../schemas/relationship/customer/customer.schema';
import type { ObjetoHistorico } from '@/modules/customers/types/clientes.types';
import { getUniqueOS } from '../services/orderServiceGet.service';
import { uploadFotoOS } from '../services/relationship/osPhotoMutate.service';
import { useOSFormProvider, useOSFormPendingState } from '../context/useForm.context';
import { useCreateItemOSMutation } from '../composables/request/useOrderServiceCreate.mutate';
import { useReopenOrderServiceMutation } from '../composables/request/useOrderServiceUpdate.mutate';
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';
import { useToast } from '@/shared/composables/useToast';
import { imprimirComPagina } from '@/shared/utils/print.utils';
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';
import { useOrderServiceDeleteItem } from '../composables/request/useOrderServiceDelete.mutate';
import { useOSStatusLocks } from '../composables/modal/useOSStatusLocks';
import { useOSFinancialSummary } from '../composables/modal/useOSFinancialSummary';
import { useOSFormAdapter } from '../composables/modal/useOSFormAdapter';
import { useOSPendingPhotos } from '../composables/modal/useOSPendingPhotos';
import { useOSObjetoHistory } from '../composables/modal/useOSObjetoHistory';
import { useOSReopenState } from '../composables/modal/useOSReopenState';
import { useOSItemsManager } from '../composables/modal/useOSItemsManager';
import { useOSModalLifecycle } from '../composables/modal/useOSModalLifecycle';
import { useOSSelectOptions } from '../composables/modal/useOSSelectOptions';
import { useOSPrintFlow } from '../composables/modal/useOSPrintFlow';
import { useOSClientHistory } from '../composables/modal/useOSClientHistory';
import { useOSFormViewProvider } from '../context/useOSFormView.context';
import { getCustomerByIdForOS } from '../services/relationship/osRelationshipGet.service';
interface Props {
  isOpen: boolean;
  ordemServico?: OrderServiceReadDataType | null;
  selectedCliente?: CustomerUnionReadSchemaDataType | null;
  initialObjeto?: ObjetoHistorico | null;
  autoUsarCredito?: boolean;
  /** Abre o modal de opções de reabertura assim que o form carrega (vem da tabela). */
  autoOpenReopen?: boolean;
}
const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  changeCliente: [];
}>();
let closeItemModalProxy: (() => void) | null = null;
function closeItemModal() {
  closeItemModalProxy?.();
}
let resetObjetoSelectStateProxy: (() => void) | null = null;
const localOSData = ref<OrderServiceReadDataType | null>(null);
const currentOSData = computed(() => localOSData.value ?? props.ordemServico ?? null);
const osNumber = computed(() => currentOSData.value?.numero_os ?? null);
const isCreateMode = computed(() => !props.ordemServico);

// Crédito capturado ao reabrir — limita o crédito anterior ao valor que foi cobrado
// (não ao dinheiro entregue, que pode incluir troco)
const creditoAoReabrir = ref<number | null>(null);

function capturarCreditoAnterior() {
  const os = currentOSData.value;
  if (!os || !os.pagamentos?.length) { creditoAoReabrir.value = null; return; }
  const totalPago = os.pagamentos.reduce((s, p) => s + p.valor, 0);
  creditoAoReabrir.value = Math.min(totalPago, os.valor_total);
}

const {
  printType,
  printFormat,
  isFinalizarModalOpen,
  isPrintSelectModalOpen,
  printEntrada,
  printSaida,
  printEntradaAndClose,
  handleFinalizarOS,
  closeFinalizarModal,
  onFinalized,
  handlePrintFormatSelected,
  closePrintSelectModal,
} = useOSPrintFlow({
  onClose: handleClose,
  getOS: () => currentOSData.value,
});

const form = useOSFormProvider({
  osNumber,
  isCreateMode,
  onCreateSuccess: (os: OrderServiceReadDataType) => {
    localOSData.value = os;
    printEntradaAndClose();
  },
  onUpdateSuccess: async () => {
    await uploadPendingPhotos();
    handleClose();
  },
  // Recarrega DEPOIS que o PATCH do item respondeu — é aqui que o status de
  // aprovação e a garantia recém-salvos chegam à tela e ao resumo financeiro.
  onItemSuccess: () => {
    closeItemModal();
    refreshCurrentOSData();
  },
  onFinalizarSuccess: () => { isFinalizarModalOpen.value = false; },
});

const isPending = useOSFormPendingState(form);
const isEditMode = computed(() => !isCreateMode.value);
const isFinalizada = computed(() => currentOSData.value?.status === 'FINALIZADA');
const isCancelada = computed(() => currentOSData.value?.status === 'CANCELADA');
const { funcionariosOptions, statusOptions, prioridadeOptions } = useOSSelectOptions({
  currentStatus: computed(() => currentOSData.value?.status),
});
const reopenMutation = useReopenOrderServiceMutation();
const gerenteReopen = useGerenteAprovacao();
const toast = useToast();

async function executarReopenOS(numeroOS: string, clientePagou: boolean, codigoGerente?: string): Promise<void> {
  try {
    await reopenMutation.mutateAsync({ osNumber: numeroOS, codigoGerente, clientePagou });
    await refreshCurrentOSData();
    capturarCreditoAnterior();
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (detail === 'REQUER_APROVACAO_GERENTE') {
      const pin = await gerenteReopen.pedirPin();
      if (pin) await executarReopenOS(numeroOS, clientePagou, pin);
    } else if (detail === 'PIN_GERENTE_INVALIDO') {
      toast.error('PIN do gerente inválido');
      const pin = await gerenteReopen.pedirPin();
      if (pin) await executarReopenOS(numeroOS, clientePagou, pin);
    }
  }
}

const {
  isReopenOptionsOpen,
  reopenMode,
  handleReopenClick,
  handleReopenCancel,
  handleReopenTextOnly,
  handleReopenFull,
  resetReopenState,
} = useOSReopenState({
  osNumber,
  onReopenRequest: (numeroOS, clientePagou) => void executarReopenOS(numeroOS, clientePagou),
  onFullReopen: () => {},
});
const { isStructureLocked, isDiagnosticoLocked, isItemsLocked } = useOSStatusLocks({ isFinalizada, isCancelada, reopenMode });
const addItemMutation = useCreateItemOSMutation();
const deleteItemMutation = useOrderServiceDeleteItem();

async function refreshCurrentOSData() {
  if (!osNumber.value) return;
  const os = await getUniqueOS(osNumber.value);
  localOSData.value = os;
}
const {
  isItemModalOpen,
  editingItem,
  displayItems,
  openAddItemModal,
  openEditItemModal,
  closeItemModal: closeItemModalFromManager,
  handleSaveItem,
  handleRemoveItem,
} = useOSItemsManager({
  isCreateMode,
  osNumber,
  createItems: computed(() => form.criar.itens.value.map(entry => entry.value)),
  currentOSData,
  form,
  addItemMutation,
  deleteItemMutation,
  refreshCurrentOSData,
  setCurrentOSData: (os) => {
    localOSData.value = os;
  },
});
closeItemModalProxy = closeItemModalFromManager;
const {
  displaySubtotal,
  displayValorEntrega,
  displayValorDesconto,
  displayValorTotal,
  displayValorEntrada,
  displayValorAcrescimo,
  handleValorEntradaUpdate,
  handleValorEntregaUpdate,
} = useOSFinancialSummary({
  isCreateMode,
  createItems: computed(() => form.criar.itens.value.map(item => item.value)),
  currentOSData,
  createDesconto: form.criar.desconto,
  createValorEntrada: form.criar.valor_entrada,
  updateValorEntrada: form.atualizarGeral.valor_entrada,
  updateTaxaEntrega: form.atualizarGeral.taxa_entrega,
});
const {
  pendingPhotos,
  handleAddPhoto,
  handleRemovePending,
  clearPendingPhotos,
  uploadPendingPhotos,
} = useOSPendingPhotos({
  osNumber,
  uploadPhoto: uploadFotoOS,
});

function handlePhotoChange() {
  refreshCurrentOSData();
}
function handleLocalSubmit() {
  if (isCreateMode.value) {
    // `currentCliente` e nao `props.selectedCliente`: quando o atendente troca de
    // dono pelo aviso de identificador duplicado, a OS tem que nascer no nome de
    // quem está na tela. Sem troca, `currentCliente` já cai no selectedCliente.
    const clienteId = (currentCliente.value as { id?: number } | null)?.id;
    if (clienteId) form.criar.cliente_id.value = clienteId;
    form.criar.onSubmit();
  } else if (reopenMode.value === 'TEXT_ONLY') {
    form.atualizarGeral.onSubmitTextOnly();
  } else {
    // Salva também o OBJETO (cor, chassi, ano...). Sem isto, só a OS era
    // persistida e as edições do objeto se perdiam ao reabrir — o objeto tem
    // endpoint próprio e nunca era submetido no salvar comum.
    form.atualizarObjeto.onSubmit();
    form.atualizarGeral.onSubmit();
  }
}
function handleClose() {
  form.criar.resetForm();
  form.atualizarGeral.resetForm();
  form.atualizarObjeto.resetForm();
  form.item.resetForm();
  clearPendingPhotos();
  resetReopenState();
  localOSData.value = null;
  updatedClienteRef.value = null;
  creditoAoReabrir.value = null;
  emit('close');
}

useOSModalLifecycle({
  isOpen: computed(() => props.isOpen),
  ordemServico: computed(() => props.ordemServico),
  selectedCliente: computed(() => props.selectedCliente),
  currentOSData,
  localOSData,
  isCreateMode,
  reopenMode,
  form,
  resetReopenState,
  refreshEditData: refreshCurrentOSData,
  onOpen: () => {
    resetObjetoSelectStateProxy?.();
    // Captura crédito se a OS já foi reaberta anteriormente (vem da tabela)
    const os = currentOSData.value;
    if (os && os.pagamentos?.length > 0 && os.status !== 'FINALIZADA' && os.status !== 'CANCELADA') {
      capturarCreditoAnterior();
    }
    if (props.initialObjeto && isCreateMode.value) {
      const objeto = props.initialObjeto;
      nextTick(() => {
        form.criar.objeto_tipo_equipamento.value = objeto.objeto;
        form.criar.objeto_marca.value = objeto.marca ?? '';
        form.criar.objeto_modelo.value = objeto.modelo ?? '';
        form.criar.objeto_numero_serie.value = objeto.numero_serie ?? '';
        form.criar.objeto_cor.value = objeto.cor ?? '';
        form.criar.objeto_dados_adicionais.value = { ...(objeto.dados_adicionais ?? {}) };
      });
    }
    if (props.autoUsarCredito && isCreateMode.value) {
      nextTick(() => handleUsarCredito());
    }
    // Reabertura vinda da tabela: abre o modal de opções (fluxo correto do form).
    if (props.autoOpenReopen && (isFinalizada.value || isCancelada.value)) {
      nextTick(() => handleReopenClick());
    }
  },
});
const {
  objetosHistorico,
  selectedHistorico,
  isObjetoSelectModalOpen,
  handleObjetoSelected,
  applyObjetoHistorico,
  resetObjetoSelectState,
} = useOSObjetoHistory({
  selectedCliente: computed(() => props.selectedCliente as { id?: number } | null),
  ordemServicoCliente: computed(() => currentOSData.value?.cliente as { id?: number } | null),
  isCreateMode,
  isFormOpen: computed(() => props.isOpen),
  temOSCarregada: computed(() => currentOSData.value != null),
  createObjetoTipo: form.criar.objeto_tipo_equipamento,
  createObjetoMarca: form.criar.objeto_marca,
  createObjetoModelo: form.criar.objeto_modelo,
  createObjetoNumeroSerie: form.criar.objeto_numero_serie,
  createObjetoCor: form.criar.objeto_cor,
  createObjetoDadosAdicionais: form.criar.objeto_dados_adicionais,
});
resetObjetoSelectStateProxy = resetObjetoSelectState;
const {
  objetoFormData,
  objetoDados,
  osDados,
  controlsStatus,
  controlsFuncionarioId,
  controlsPrioridade,
  controlsDataPrevisao,
  handleStatusUpdate,
  handleFuncionarioIdUpdate,
  handlePrioridadeUpdate,
  handleDataPrevisaoUpdate,
  currentDiagnostico,
  handleDiagnosticoUpdate,
} = useOSFormAdapter({
  form,
  isCreateMode,
});
const updatedClienteRef = ref<CustomerUnionReadSchemaDataType | null>(null);
const currentCliente = computed(
  () => updatedClienteRef.value ?? props.selectedCliente ?? currentOSData.value?.cliente ?? null,
);

// ─── Ficha de vistoria imprimível (em branco, pra preencher no carro) ──────────
// Funciona ANTES de criar a OS (usa os dados atuais do form) e também depois.
const fichaTipo = ref<'ENTRADA' | 'SAIDA' | null>(null);
const fichaData = ref<{
  cliente: Record<string, unknown> | null;
  objeto: Record<string, unknown> | null;
  numeroOs: string | null;
  dataOs: string | null;
} | null>(null);
// Quando != null, a ficha sai PREENCHIDA com os dados marcados na tela (vistoria).
const fichaPreenchimento = ref<Record<string, unknown> | null>(null);

/**
 * Pré-carrega uma imagem e resolve quando ela estiver pronta (ou no timeout,
 * pra nunca travar a impressão). Necessário porque window.print() dispara logo
 * após o nextTick, que NÃO espera imagens — sem isso, a ilustração do veículo
 * (PNG grande) pode sair em branco na primeira impressão.
 */
function aguardarImagem(src: string, timeoutMs = 2000): Promise<void> {
  return new Promise((resolve) => {
    const img = new Image();
    const done = () => resolve();
    img.onload = done;
    img.onerror = done;
    img.src = src;
    if (img.complete) done();
    setTimeout(done, timeoutMs);
  });
}

async function imprimirFicha(
  tipo: 'ENTRADA' | 'SAIDA',
  preenchimento: Record<string, unknown> | null = null,
) {
  const os = currentOSData.value;
  // Usa os valores VIVOS do formulário (não o os.objeto persistido): assim a Cor
  // e os demais campos saem preenchidos mesmo antes de salvar e refletem edições.
  const objeto = {
    marca: objetoFormData.value.marca,
    modelo: objetoFormData.value.modelo,
    numero_serie: objetoFormData.value.numero_serie,
    cor: objetoFormData.value.cor,
    dados_adicionais: objetoDados.value,
  };
  fichaData.value = {
    cliente: (currentCliente.value as Record<string, unknown> | null) ?? null,
    objeto: objeto as Record<string, unknown>,
    numeroOs: os?.numero_os ?? null,
    dataOs: os?.data_criacao ?? null,
  };
  fichaPreenchimento.value = preenchimento;
  fichaTipo.value = tipo;
  // Evita que o comprovante (OSPrintTemplate, condicionado a printFormat==='A4')
  // saia junto ao imprimir a ficha.
  printFormat.value = '' as typeof printFormat.value;
  await nextTick();
  // Espera a ilustração do veículo carregar antes de abrir o diálogo de impressão.
  await aguardarImagem('/vistoria-carro.png');

  // A ficha só sai do DOM DEPOIS que a impressão termina (evento afterprint).
  // Um timeout curto (600ms) removia a ficha antes de o "Salvar como PDF"
  // concluir: no WebView o window.print() não bloqueia, então o motor recapturava
  // o DOM já vazio e o arquivo saía em branco (embora o preview aparecesse cheio).
  // O fallback longo cobre motores onde o afterprint não dispara.
  let fallbackTimer: ReturnType<typeof setTimeout>;
  const limparFicha = () => {
    fichaTipo.value = null;
    fichaData.value = null;
    fichaPreenchimento.value = null;
    window.removeEventListener('afterprint', limparFicha);
    clearTimeout(fallbackTimer);
  };
  window.addEventListener('afterprint', limparFicha);
  fallbackTimer = setTimeout(limparFicha, 120000);
  // Ficha de vistoria é sempre A4 (força o @page correto — ver imprimirComPagina).
  imprimirComPagina('A4');
}

/** Imprime a ficha de vistoria de ENTRADA já preenchida com o que está na tela. */
function imprimirVistoriaPreenchida() {
  imprimirFicha('ENTRADA', osDados.value ?? {});
}

const saldoCreditoCliente = computed(() => {
  const c = currentCliente.value as { saldo_credito?: number } | null;
  return c?.saldo_credito ?? 0;
});

function handleUsarCredito() {
  if (!isCreateMode.value || saldoCreditoCliente.value <= 0) return;
  form.criar.valor_entrada.value = saldoCreditoCliente.value;
  form.criar.usar_credito_cliente.value = true;
}

function handleUpdateCliente(cliente: CustomerUnionReadSchemaDataType) {
  updatedClienteRef.value = cliente;
}

/**
 * O atendente viu que a placa/série já é de outro cliente e optou por abrir a OS
 * no nome dele.
 *
 * Busca pelo id no servidor. A versão anterior procurava numa lista em cache que
 * só continha os 20 cadastros mais recentes — e cliente que volta com o mesmo
 * carro raramente é um dos 20 últimos, então o clique não fazia NADA, sem erro
 * nem aviso. Se a busca falhar agora, o atendente fica sabendo.
 */
async function handleAbrirComCliente(clienteId: number) {
  try {
    const cliente = await getCustomerByIdForOS(clienteId);
    handleUpdateCliente(cliente);
  } catch {
    toast.error('Não foi possível carregar o cliente. Selecione-o pela busca.');
  }
}

function handleChangeCliente() {
  emit('changeCliente');
}

function setObjetoFormData(value: typeof objetoFormData.value) {
  objetoFormData.value = value;
}

function setObjetoDados(value: Record<string, unknown>) {
  objetoDados.value = value;
}

function setOsDados(value: Record<string, unknown>) {
  osDados.value = value;
}

const {
  isHistoricoModalOpen,
  openHistoricoModal,
  closeHistoricoModal,
  reutilizarObjeto,
} = useOSClientHistory({ setObjetoFormData });

function setSelectedHistorico(value: string) {
  selectedHistorico.value = value;
}

function closeObjetoModal() {
  isObjetoSelectModalOpen.value = false;
}

const formErrors = computed<Record<string, string | undefined>>(() => {
  if (isCreateMode.value) {
    if (form.criar.submitCount.value === 0) return {};
    return { ...form.criar.errors.value };
  }
  return {
    ...form.atualizarGeral.errors.value,
    ...form.atualizarObjeto.errors.value,
  };
});

useOSFormViewProvider({
  isOpen: computed(() => props.isOpen),
  currentOSData,
  currentCliente,
  osNumber,
  isCreateMode,
  isEditMode,
  isPending,
  isFinalizada,
  isCancelada,
  reopenMode,
  isStructureLocked,
  isDiagnosticoLocked,
  isItemsLocked,
  creditoAoReabrir,
  controlsStatus,
  controlsFuncionarioId,
  controlsPrioridade,
  controlsDataPrevisao,
  statusOptions,
  prioridadeOptions,
  funcionariosOptions,
  displayItems,
  displaySubtotal,
  displayValorEntrega,
  displayValorDesconto,
  displayValorTotal,
  displayValorEntrada,
  displayValorAcrescimo,
  formErrors,
  objetoFormData,
  objetoDados,
  osDados,
  objetosHistorico,
  selectedHistorico,
  currentDiagnostico,
  pendingPhotos,
  isReopenOptionsOpen,
  printType,
  printFormat,
  isPrintSelectModalOpen,
  isFinalizarModalOpen,
  isItemModalOpen,
  editingItem,
  isObjetoSelectModalOpen,
  handleClose,
  handleLocalSubmit,
  handleFinalizarOS,
  printEntrada,
  printSaida,
  imprimirFicha,
  imprimirVistoriaPreenchida,
  handleReopenClick,
  handleChangeCliente,
  handleUpdateCliente,
  handleAbrirComCliente,
  handleStatusUpdate,
  handleFuncionarioIdUpdate,
  handlePrioridadeUpdate,
  handleDataPrevisaoUpdate,
  handleValorEntradaUpdate,
  handleValorEntregaUpdate,
  handleUsarCredito,
  saldoCreditoCliente,
  setObjetoFormData,
  setObjetoDados,
  setOsDados,
  setSelectedHistorico,
  applyObjetoHistorico,
  handleDiagnosticoUpdate,
  handleAddPhoto,
  handleRemovePending,
  handlePhotoChange,
  openAddItemModal,
  openEditItemModal,
  handleRemoveItem,
  handleReopenCancel,
  handleReopenTextOnly,
  handleReopenFull,
  closeFinalizarModal,
  onFinalized,
  refreshCurrentOSData,
  handlePrintFormatSelected,
  closePrintSelectModal,
  closeItemModal,
  handleSaveItem,
  closeObjetoModal,
  handleObjetoSelected,
  isHistoricoModalOpen,
  openHistoricoModal,
  closeHistoricoModal,
  reutilizarObjeto,
});
</script>

<template>
  <OSFormModalShell />
  <OSFormAuxModals />
  <OSVistoriaFichaPrint
    v-if="fichaTipo && fichaData"
    :cliente="fichaData.cliente"
    :objeto="fichaData.objeto"
    :numero-os="fichaData.numeroOs"
    :data-os="fichaData.dataOs"
    :tipo="fichaTipo"
    :preenchimento="fichaPreenchimento"
  />
  <GerenteAprovacaoModal
    :is-open="gerenteReopen.isOpen.value"
    :is-loading="gerenteReopen.isLoading.value"
    @confirmar="gerenteReopen.confirmar"
    @cancelar="gerenteReopen.cancelar"
  />
</template>
