import { ref } from 'vue';
import { usePrintFlow } from '@/shared/composables/usePrintFlow';
import { useImpressao } from '@/shared/composables/useImpressao';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { useCompanyPrintInfo } from '@/shared/utils/print.utils';
import { osToEscPos } from '../../components/osToEscPos';
import { DOTS } from '@/shared/services/escpos';
import { carregarLogoRaster } from '@/shared/services/escposImagem';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';
import type { PrintFormat } from '@/shared/components/print/print.types';

export type { PrintFormat } from '@/shared/components/print/print.types';

interface UseOSPrintFlowParams {
  onClose: () => void;
  /** Getter da OS atual, usado na impressão térmica direta (ESC/POS) */
  getOS?: () => OrderServiceReadDataType | null;
}

export function useOSPrintFlow({ onClose, getOS }: UseOSPrintFlowParams) {
  const {
    printType,
    printFormat,
    isPrintSelectModalOpen,
    printDirect,
    handlePrintFormatSelected: handlePrintFormatSelectedBase,
    closePrintSelectModal,
  } = usePrintFlow<'ENTRADA' | 'SAIDA'>();

  const isFinalizarModalOpen = ref(false);

  const impressao = useImpressao();
  const impressaoStore = useImpressaoStore();
  const { companyInfo } = useCompanyPrintInfo();
  const { labelSingular } = useObjetoLabels();

  /** Manda o cupom térmico direto pra impressora configurada; false = sem impressora/falhou */
  async function imprimirEscPosDireto(tipo: 'ENTRADA' | 'SAIDA'): Promise<boolean> {
    if (!impressao.podeImprimirDireto.value) return false;
    const os = getOS?.();
    if (!os) return false;
    const bobina = impressaoStore.config.bobina;
    const logoRaster = await carregarLogoRaster(companyInfo.value.logo, DOTS[bobina]);
    const dados = osToEscPos(os, tipo, {
      bobina,
      empresa: companyInfo.value,
      logoRaster,
      rotuloObjeto: labelSingular.value,
    });
    return impressao.imprimirCupom(dados);
  }

  /**
   * Formato escolhido no modal de reimpressão manual: Cupom Térmico sai direto
   * pela impressora (sem diálogo); A4 continua abrindo o diálogo de impressão
   * do sistema, onde o usuário escolhe a impressora/PDF.
   */
  async function handlePrintFormatSelected(format: PrintFormat) {
    if (format === 'CUPOM' && (await imprimirEscPosDireto(printType.value))) {
      closePrintSelectModal();
      printFormat.value = '' as PrintFormat;
      return;
    }
    handlePrintFormatSelectedBase(format);
  }

  /**
   * Regra única de impressão (sem perguntar formato):
   * - Impressora térmica configurada → cupom ESC/POS direto (silencioso).
   * - Sem térmica (ou falha) → recibo A4 abrindo o diálogo do sistema.
   * `imprimirEscPosDireto` já devolve false quando não há térmica configurada.
   */
  async function imprimir(tipo: 'ENTRADA' | 'SAIDA', afterPrint?: () => void) {
    if (await imprimirEscPosDireto(tipo)) {
      afterPrint?.();
      return;
    }
    printDirect(tipo, 'A4', afterPrint);
  }

  function printEntrada() {
    imprimir('ENTRADA');
  }

  function printSaida() {
    imprimir('SAIDA');
  }

  /** Impressão automática pós-criação/finalização: segue a regra única e fecha. */
  async function imprimirAutomaticoEFechar(tipo: 'ENTRADA' | 'SAIDA') {
    await imprimir(tipo, () => onClose());
  }

  async function printEntradaAndClose() {
    // 'nao' vale só para a impressão automática pós-criação;
    // a reimpressão manual (printEntrada) continua disponível
    if (impressaoStore.config.auto_imprimir_os === 'nao') {
      onClose();
      return;
    }
    await imprimirAutomaticoEFechar('ENTRADA');
  }

  function handleFinalizarOS() {
    isFinalizarModalOpen.value = true;
  }

  function closeFinalizarModal() {
    isFinalizarModalOpen.value = false;
  }

  async function onFinalized(payload: { shouldPrint: boolean }) {
    isFinalizarModalOpen.value = false;

    if (!payload.shouldPrint) {
      onClose();
      return;
    }
    await imprimirAutomaticoEFechar('SAIDA');
  }

  return {
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
  };
}
