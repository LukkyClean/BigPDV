import { inject, provide } from 'vue';
import type { ComputedRef, InjectionKey, Ref } from 'vue';

import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import type { ObjetoHistorico } from '@/modules/customers/types/clientes.types';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import type { CustomerUnionReadSchemaDataType } from '../schemas/relationship/customer/customer.schema';
import type {
  OsItemCreateSchemaDataType,
  OsItemReadSchemaDataType,
} from '../schemas/relationship/osItem.schema';
import type {
  OsPriorityEnumDataType,
  OsStatusEnumDataType,
} from '../schemas/enums/osEnums.schema';
import type { PendingPhoto } from '../components/form/OSFotoGallery.vue';
import type { ObjetoFormData } from '../composables/modal/useOSFormAdapter';
import type { OSReopenMode } from '../composables/modal/useOSStatusLocks';
import type { PrintFormat } from '../composables/modal/useOSPrintFlow';

type OsItem = OsItemCreateSchemaDataType | OsItemReadSchemaDataType;

export interface OSFormViewContext {
  isOpen: ComputedRef<boolean>;
  currentOSData: ComputedRef<OrderServiceReadDataType | null>;
  currentCliente: ComputedRef<CustomerUnionReadSchemaDataType | null>;
  osNumber: ComputedRef<string | null>;
  isCreateMode: ComputedRef<boolean>;
  isEditMode: ComputedRef<boolean>;
  isPending: ComputedRef<boolean>;
  isFinalizada: ComputedRef<boolean>;
  isCancelada: ComputedRef<boolean>;
  reopenMode: Ref<OSReopenMode>;
  isStructureLocked: ComputedRef<boolean>;
  isDiagnosticoLocked: ComputedRef<boolean>;
  isItemsLocked: ComputedRef<boolean>;
  creditoAoReabrir: Ref<number | null>;
  controlsStatus: ComputedRef<OsStatusEnumDataType>;
  controlsFuncionarioId: ComputedRef<string>;
  controlsPrioridade: ComputedRef<OsPriorityEnumDataType>;
  controlsDataPrevisao: ComputedRef<string>;
  statusOptions: ComputedRef<SelectOption[]>;
  prioridadeOptions: ComputedRef<SelectOption[]>;
  funcionariosOptions: ComputedRef<SelectOption[]>;
  displayItems: ComputedRef<OsItem[]>;
  displaySubtotal: ComputedRef<number>;
  displayValorEntrega: ComputedRef<number>;
  displayValorDesconto: ComputedRef<number>;
  displayValorTotal: ComputedRef<number>;
  displayValorEntrada: ComputedRef<number>;
  displayValorAcrescimo: ComputedRef<number>;
  formErrors: ComputedRef<Record<string, string | undefined>>;
  objetoFormData: ComputedRef<ObjetoFormData>;
  objetoDados: ComputedRef<Record<string, unknown>>;
  osDados: ComputedRef<Record<string, unknown>>;
  objetosHistorico: Ref<ObjetoHistorico[]>;
  selectedHistorico: Ref<string>;
  currentDiagnostico: ComputedRef<string>;
  pendingPhotos: Ref<PendingPhoto[]>;
  isReopenOptionsOpen: Ref<boolean>;
  printType: Ref<'ENTRADA' | 'SAIDA'>;
  printFormat: Ref<PrintFormat>;
  isPrintSelectModalOpen: Ref<boolean>;
  isFinalizarModalOpen: Ref<boolean>;
  isItemModalOpen: Ref<boolean>;
  editingItem: Ref<OsItemCreateSchemaDataType | null>;
  isObjetoSelectModalOpen: Ref<boolean>;
  handleClose: () => void;
  handleLocalSubmit: () => void;
  handleFinalizarOS: () => void;
  printEntrada: () => void;
  printSaida: () => void;
  imprimirFicha: (tipo: 'ENTRADA' | 'SAIDA', preenchimento?: Record<string, unknown> | null) => void;
  imprimirVistoriaPreenchida: () => void;
  handleReopenClick: () => void;
  handleChangeCliente: () => void;
  handleUpdateCliente: (cliente: CustomerUnionReadSchemaDataType) => void;
  /** Troca o dono da OS em criação para um cliente já cadastrado, pelo ID. */
  handleAbrirComCliente: (clienteId: number) => void;
  handleStatusUpdate: (value: OsStatusEnumDataType) => void;
  handleFuncionarioIdUpdate: (value: string) => void;
  handlePrioridadeUpdate: (value: OsPriorityEnumDataType) => void;
  handleDataPrevisaoUpdate: (value: string) => void;
  handleValorEntradaUpdate: (value: number) => void;
  handleValorEntregaUpdate: (value: number) => void;
  handleUsarCredito: () => void;
  saldoCreditoCliente: ComputedRef<number>;
  setObjetoFormData: (value: ObjetoFormData) => void;
  setObjetoDados: (value: Record<string, unknown>) => void;
  setOsDados: (value: Record<string, unknown>) => void;
  setSelectedHistorico: (value: string) => void;
  applyObjetoHistorico: () => void;
  handleDiagnosticoUpdate: (value: string) => void;
  handleAddPhoto: (file: File) => void;
  handleRemovePending: (index: number) => void;
  handlePhotoChange: () => void;
  openAddItemModal: () => void;
  openEditItemModal: (index: number) => void;
  handleRemoveItem: (index: number) => void;
  handleReopenCancel: () => void;
  handleReopenTextOnly: () => void;
  handleReopenFull: (clientePagou?: boolean) => void;
  closeFinalizarModal: () => void;
  onFinalized: (payload: { shouldPrint: boolean }) => void;
  refreshCurrentOSData: () => Promise<void>;
  handlePrintFormatSelected: (format: PrintFormat) => void;
  closePrintSelectModal: () => void;
  closeItemModal: () => void;
  handleSaveItem: (item: OsItemCreateSchemaDataType) => void;
  closeObjetoModal: () => void;
  handleObjetoSelected: (objeto: ObjetoHistorico) => void;
  isHistoricoModalOpen: Ref<boolean>;
  openHistoricoModal: () => void;
  closeHistoricoModal: () => void;
  reutilizarObjeto: (os: OrderServiceReadDataType) => void;
}

export const OS_FORM_VIEW_CONTEXT_KEY: InjectionKey<OSFormViewContext> = Symbol('os-form-view-context');

export function useOSFormViewProvider(context: OSFormViewContext): OSFormViewContext {
  provide(OS_FORM_VIEW_CONTEXT_KEY, context);
  return context;
}

export function useOSFormView(): OSFormViewContext {
  const context = inject(OS_FORM_VIEW_CONTEXT_KEY);

  if (!context) {
    throw new Error(
      '[useOSFormView] Contexto não encontrado. ' +
        'Certifique-se de que useOSFormViewProvider foi chamado em um componente ancestral.',
    );
  }

  return context;
}