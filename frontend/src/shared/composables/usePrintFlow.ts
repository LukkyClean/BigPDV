import { ref } from 'vue';
import { imprimirComPagina, aguardarImagensDaImpressao } from '@/shared/utils/print.utils';
import { usePerfilComprovante } from '@/shared/composables/usePerfilComprovante';
import type { DocumentoComprovante } from '@/shared/composables/usePerfilComprovante';
import type { PrintFormat } from '@/shared/components/print/print.types';

/**
 * `documentoDe` traduz o tipo de impressão deste módulo para o documento do
 * perfil de comprovante. Fica como parâmetro porque só quem chama sabe a
 * correspondência: em OS, ENTRADA e SAIDA são documentos diferentes e podem
 * querer papéis diferentes; em vendas há um só.
 */
export function usePrintFlow<T extends string>(
  documentoDe?: (tipo: T) => DocumentoComprovante,
) {
  // Tamanho do papel (folha do perfil, bobina da máquina). A densidade não passa
  // por aqui: ela é uma classe no container, aplicada pelo próprio template.
  const { opcoesPaginaDe } = usePerfilComprovante();
  const printType = ref<T>('' as T);
  const printFormat = ref<PrintFormat>('A4');
  const isPrintSelectModalOpen = ref(false);
  const pendingPrintAction = ref<(() => void) | null>(null);

  function openPrintSelect(type: T, afterPrint?: () => void) {
    printType.value = type as typeof printType.value;
    pendingPrintAction.value = afterPrint ?? null;
    isPrintSelectModalOpen.value = true;
  }

  function handlePrintFormatSelected(format: PrintFormat) {
    printFormat.value = format;
    isPrintSelectModalOpen.value = false;

    setTimeout(async () => {
      // Sem esta espera, uma via com imagem (a arte da OS na serigrafia) podia
      // sair com quadro em branco: os 100ms acima cobrem a renderização do DOM,
      // não o download da imagem. Resolve na hora quando não há imagem pendente,
      // então nenhuma via existente fica mais lenta.
      await aguardarImagensDaImpressao();

      const documento = documentoDe?.(printType.value as T) ?? 'os_entrega';
      imprimirComPagina(format, opcoesPaginaDe(documento));
      printFormat.value = '' as PrintFormat;
      pendingPrintAction.value?.();
      pendingPrintAction.value = null;
    }, 100);
  }

  function closePrintSelectModal() {
    isPrintSelectModalOpen.value = false;
    pendingPrintAction.value?.();
    pendingPrintAction.value = null;
  }

  /** Imprime direto num formato definido, sem abrir o modal de escolha */
  function printDirect(type: T, format: PrintFormat, afterPrint?: () => void) {
    printType.value = type as typeof printType.value;
    pendingPrintAction.value = afterPrint ?? null;
    handlePrintFormatSelected(format);
  }

  return {
    printType,
    printFormat,
    isPrintSelectModalOpen,
    openPrintSelect,
    printDirect,
    handlePrintFormatSelected,
    closePrintSelectModal,
  };
}
