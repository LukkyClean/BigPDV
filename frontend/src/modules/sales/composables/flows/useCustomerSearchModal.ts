import { ref } from 'vue'
import { refDebounced } from '@vueuse/core'

import { useCustomersQuery } from '../queries/useCustomersQuery'
import { useCreateSaleMutation } from '../mutates/useCreateSaleMutation'

import { useCustomerModal } from '@/modules/customers/composables/modal/useCustomerModal'
import { useSaleModal } from './useSaleModal'
import { useAuthStore } from '@/shared/stores/auth.store'

type ModalMode = 'create' | 'change' | 'converter'

const customerModalIsOpen = ref(false)
const modalMode = ref<ModalMode>('create')
let changeCallback: ((clienteId: number | null) => void) | null = null

export function useCustomerSearchModal() {
  const searchTerm = ref('')
  const debouncedSearchTerm = refDebounced(searchTerm, 500)

  const { openCreateModalWithCallback } = useCustomerModal()
  const { openSaleEditModal } = useSaleModal()
  const authStore = useAuthStore()

  const {
    data: customers,
    isLoading: isSearchingCustomers,
  } = useCustomersQuery(debouncedSearchTerm)

  const createSaleMutation = useCreateSaleMutation()

  function resetSearch() {
    searchTerm.value = ''
  }

  function openCustomerModal() {
    resetSearch()
    modalMode.value = 'create'
    changeCallback = null
    customerModalIsOpen.value = true
  }

  function openCustomerModalForChange(callback: (clienteId: number | null) => void) {
    resetSearch()
    modalMode.value = 'change'
    changeCallback = callback
    customerModalIsOpen.value = true
  }

  function openCustomerModalForConversion(callback: (clienteId: number | null) => void) {
    resetSearch()
    modalMode.value = 'converter'
    changeCallback = callback
    customerModalIsOpen.value = true
  }

  function closeCustomerModal() {
    resetSearch()
    customerModalIsOpen.value = false
    changeCallback = null
  }

  /** Cria a venda e abre o carrinho. Único lugar que dispara a criação. */
  function abrirVendaNova(clienteId: number | null) {
    createSaleMutation.mutate(
      {
        cliente_id: clienteId,
        funcionario_id: authStore.userData?.funcionario_id as number,
      },
      {
        onSuccess: (createdSale) => {
          closeCustomerModal()
          openSaleEditModal(createdSale.id)
        },
      },
    )
  }

  function selectCustomer(customerId: number | null) {
    if (modalMode.value === 'change' || modalMode.value === 'converter') {
      changeCallback?.(customerId)
      closeCustomerModal()
      return
    }

    abrirVendaNova(customerId)
  }

  /**
   * Abre a venda direto, sem passar pelo modal de cliente. É o começo de venda
   * do Modo Balcão.
   *
   * Numa adega quase toda venda é sem cliente, e escolher "Venda sem cliente"
   * antes de bipar o primeiro item é um passo repetido a cada atendimento, com
   * a fila esperando. Aqui a venda nasce no produto.
   *
   * O caller é quem decide se pode chamar isto (ver `SalesView.vue`): loja que
   * exige cliente identificado continua passando pelo modal, senão a venda
   * nasceria só para ser recusada na finalização por `venda.py`.
   *
   * O cliente ainda pode ser posto depois, pelo `CustomerCard` dentro da venda.
   */
  function iniciarVendaSemCliente() {
    abrirVendaNova(null)
  }

  function openCreateCustomerModal() {
    const currentMode = modalMode.value
    const currentCallback = changeCallback
    closeCustomerModal()

    openCreateModalWithCallback((customer) => {
      if (currentMode === 'change') {
        currentCallback?.(customer.id)
      } else {
        selectCustomer(customer.id)
      }
    })
  }

  return {
    searchTerm,
    customers,

    customerModalIsOpen,
    modalMode,

    isSearchingCustomers,
    isCreatingSale: createSaleMutation.isPending,

    openCustomerModal,
    openCustomerModalForChange,
    openCustomerModalForConversion,
    closeCustomerModal,
    openCreateCustomerModal,
    selectCustomer,
    iniciarVendaSemCliente,
  }
}