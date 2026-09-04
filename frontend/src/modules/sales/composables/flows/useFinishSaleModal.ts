import { ref, computed, type Ref } from "vue";

import { PaymentSaleCreate } from "../../schemas/paymentSale.schema";

const finishModalIsOpen = ref(false);

/**
 * O sub-modal de detalhes do pagamento ("Dinheiro", "Cartao", ...).
 *
 * Mora aqui, e nao dentro do FinishSaleModal, porque a hierarquia do Escape
 * precisa enxerga-lo: era um `ref` local, o atalho global nao sabia da sua
 * existencia e o Esc pulava direto para o nivel de cima -- fechando a
 * Finalizar Venda inteira, com `resetPayments()` junto. Achado em 20/08/2026.
 */
const showPaymentDetails = ref(false);
const payments = ref<PaymentSaleCreate[]>([]);

export function useFinishSaleModal(saleTotal?: Ref<number>) {
    const totalPago = computed(() =>
        payments.value.reduce((sum, p) => sum + p.valor, 0)
    );

    // Acréscimo = só o juros REPASSADO ao cliente. O absorvido pela loja não é
    // cobrado, então não pode inflar o total da venda — ele é custo, não receita.
    const acrescimo = computed(() =>
        payments.value
            .filter((p) => p.juros_responsavel !== 'LOJA')
            .reduce((sum, p) => sum + (p.juros_valor ?? 0), 0)
    );

    // Quanto a loja deixa de receber por ter absorvido juros.
    const jurosLoja = computed(() =>
        payments.value
            .filter((p) => p.juros_responsavel === 'LOJA')
            .reduce((sum, p) => sum + (p.juros_valor ?? 0), 0)
    );

    // Total a pagar já considerando o acréscimo de juros do checkout.
    const totalComAcrescimo = computed(() => (saleTotal?.value ?? 0) + acrescimo.value);

    const troco = computed(() =>
        Math.max(0, totalPago.value - totalComAcrescimo.value)
    );

    const restante = computed(() =>
        Math.max(0, totalComAcrescimo.value - totalPago.value)
    );

    const canFinish = computed(() =>
        payments.value.length > 0 && totalPago.value >= totalComAcrescimo.value
    );

    function addPayment(payment: PaymentSaleCreate) {
        payments.value.push(payment);
    }

    function removePayment(index: number) {
        payments.value.splice(index, 1);
    }

    function resetPayments() {
        payments.value = [];
    }

    function openFinishModal() {
        finishModalIsOpen.value = true;
    }

    function closeFinishModal() {
        resetPayments();
        showPaymentDetails.value = false;
        finishModalIsOpen.value = false;
    }

    return {
        finishModalIsOpen,
        showPaymentDetails,
        openFinishModal,
        closeFinishModal,
        payments,
        addPayment,
        removePayment,
        resetPayments,
        totalPago,
        acrescimo,
        jurosLoja,
        troco,
        restante,
        canFinish,
    }
}
