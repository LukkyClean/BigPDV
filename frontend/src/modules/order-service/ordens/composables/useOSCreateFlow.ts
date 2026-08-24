import { ref } from 'vue';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import type { CustomerUnionReadSchemaDataType } from '../schemas/relationship/customer/customer.schema';
import type { ObjetoHistorico } from '@/modules/customers/types/clientes.types';
import type { ObjetoBuscaItemDataType } from '../schemas/relationship/objetoBusca.schema';
import { getClientObjetos } from '@/modules/customers/services/customerGet.service';
import { getCustomerByIdForOS } from '../services/relationship/osRelationshipGet.service';

// =============================================
// Shared State (singleton pattern)
// =============================================

const isClienteSearchOpen = ref(false);
const isFormModalOpen = ref(false);
const isObjetoSelectOpen = ref(false);
const isCreditAlertOpen = ref(false);
// Quando a OS é aberta a partir do botão "Reabrir" da tabela, o formulário já
// abre com o modal de opções de reabertura (fluxo correto fica dentro do form).
const autoOpenReopen = ref(false);
const selectedCliente = ref<CustomerUnionReadSchemaDataType | null>(null);
const selectedOS = ref<OrderServiceReadDataType | null>(null);
const objetosHistoricoFlow = ref<ObjetoHistorico[]>([]);
const selectedObjeto = ref<ObjetoHistorico | null>(null);
const autoUsarCredito = ref(false);
// Objeto que veio junto da busca por placa / nº de série. Existir aqui é o que
// faz o fluxo pular a pergunta "objeto já cadastrado?" — mas SEM pular o alerta
// de crédito, que é dinheiro do cliente e precisa ser visto de qualquer jeito.
const objetoPreSelecionado = ref<ObjetoHistorico | null>(null);

// =============================================
// Helper privado — continua o fluxo após a decisão de crédito
// =============================================

async function _continuarFluxoCliente() {
  const cliente = selectedCliente.value;
  if (!cliente) return;

  // Veio da busca pelo identificador: o bem já está escolhido. Perguntar
  // "objeto já cadastrado?" aqui seria repetir o que o atendente acabou de
  // responder ao digitar a placa.
  if (objetoPreSelecionado.value) {
    selectedObjeto.value = objetoPreSelecionado.value;
    objetoPreSelecionado.value = null;
    isFormModalOpen.value = true;
    return;
  }

  try {
    const history = await getClientObjetos(cliente.id);
    if (history.length > 0) {
      objetosHistoricoFlow.value = history;
      isObjetoSelectOpen.value = true;
      return;
    }
  } catch {
    // histórico de objetos é opcional
  }

  isFormModalOpen.value = true;
}

// =============================================
// Composable
// =============================================

export function useOSCreateFlow() {
  function openNovaOS() {
    selectedOS.value = null;
    selectedCliente.value = null;
    selectedObjeto.value = null;
    autoUsarCredito.value = false;
    objetoPreSelecionado.value = null;
    isClienteSearchOpen.value = true;
  }

  function openExistingOS(os: OrderServiceReadDataType, comReopen = false) {
    selectedOS.value = os;
    selectedCliente.value = null;
    selectedObjeto.value = null;
    autoOpenReopen.value = comReopen;
    isFormModalOpen.value = true;
  }

  async function handleClienteSelected(cliente: CustomerUnionReadSchemaDataType) {
    selectedCliente.value = cliente;
    selectedObjeto.value = null;
    isClienteSearchOpen.value = false;

    const saldo = (cliente as { saldo_credito?: number }).saldo_credito ?? 0;
    if (saldo > 0) {
      isCreditAlertOpen.value = true;
      return;
    }

    await _continuarFluxoCliente();
  }

  /**
   * O atendente achou o bem pela placa / nº de série / código da arte.
   *
   * Traz o cliente do servidor porque a linha do objeto só carrega o `id` e o
   * nome — e o formulário (e o alerta de crédito) precisam do cadastro
   * completo, com `saldo_credito`. É a mesma requisição barata que o aviso de
   * duplicidade já fazia.
   *
   * Se a busca do cliente falhar, devolve o atendente à tela de busca em vez de
   * abrir uma OS sem dono.
   */
  async function handleObjetoEncontrado(objeto: ObjetoBuscaItemDataType) {
    let cliente: CustomerUnionReadSchemaDataType;
    try {
      cliente = await getCustomerByIdForOS(objeto.cliente_id);
    } catch {
      isClienteSearchOpen.value = true;
      return;
    }

    // `tipo_equipamento` fica de fora de propósito: o valor guardado no objeto
    // ("Equipamento", "Veículo") não é opção do select de segmento nenhum, e
    // campo que não casa com o enum reprova no Zod em silêncio. O fluxo de
    // "objeto já cadastrado?" também nunca preencheu esse campo.
    objetoPreSelecionado.value = {
      marca: objeto.marca ?? null,
      modelo: objeto.modelo ?? null,
      numero_serie: objeto.numero_serie ?? null,
      cor: objeto.cor ?? null,
      dados_adicionais: objeto.dados_adicionais ?? {},
    } as ObjetoHistorico;

    await handleClienteSelected(cliente);
  }

  async function handleCreditoUsado() {
    autoUsarCredito.value = true;
    isCreditAlertOpen.value = false;
    await _continuarFluxoCliente();
  }

  async function handleCreditoIgnorado() {
    autoUsarCredito.value = false;
    isCreditAlertOpen.value = false;
    await _continuarFluxoCliente();
  }

  function handleObjetoSelectedFlow(objeto: ObjetoHistorico) {
    selectedObjeto.value = objeto;
    isObjetoSelectOpen.value = false;
    isFormModalOpen.value = true;
  }

  function skipObjetoSelectFlow() {
    selectedObjeto.value = null;
    isObjetoSelectOpen.value = false;
    isFormModalOpen.value = true;
  }

  function handleChangeCliente() {
    isFormModalOpen.value = false;
    isClienteSearchOpen.value = true;
  }

  function closeClienteSearch() {
    isClienteSearchOpen.value = false;
  }

  function closeFormModal() {
    isFormModalOpen.value = false;
    selectedOS.value = null;
    selectedCliente.value = null;
    selectedObjeto.value = null;
    objetosHistoricoFlow.value = [];
    autoUsarCredito.value = false;
    autoOpenReopen.value = false;
    objetoPreSelecionado.value = null;
  }

  return {
    isClienteSearchOpen,
    isFormModalOpen,
    isObjetoSelectOpen,
    isCreditAlertOpen,
    selectedCliente,
    selectedOS,
    objetosHistoricoFlow,
    selectedObjeto,
    autoUsarCredito,
    autoOpenReopen,
    openNovaOS,
    openExistingOS,
    handleClienteSelected,
    handleObjetoEncontrado,
    handleCreditoUsado,
    handleCreditoIgnorado,
    handleObjetoSelectedFlow,
    skipObjetoSelectFlow,
    handleChangeCliente,
    closeClienteSearch,
    closeFormModal,
  };
}
