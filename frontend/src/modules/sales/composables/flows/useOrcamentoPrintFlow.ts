import { ref } from 'vue';
import { usePrintFlow } from '@/shared/composables/usePrintFlow';
import { useImpressao } from '@/shared/composables/useImpressao';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { useCompanyPrintInfo } from '@/shared/utils/print.utils';
import { orcamentoService } from '../../orcamento.service';
import { saleToEscPos } from '../../components/print/saleToEscPos';
import { DOTS } from '@/shared/services/escpos';
import { carregarLogoRaster } from '@/shared/services/escposImagem';
import type { OrcamentoRead } from '../../schemas/orcamento.schema';
import type { PrintFormat } from '@/shared/components/print/print.types';

export type OrcamentoPrintType = 'ORCAMENTO';

export function useOrcamentoPrintFlow() {
  const {
    printType,
    printFormat,
    isPrintSelectModalOpen,
    printDirect,
    handlePrintFormatSelected: handlePrintFormatSelectedBase,
    closePrintSelectModal,
  } = usePrintFlow<OrcamentoPrintType>();

  const orcamentoForPrint = ref<OrcamentoRead | null>(null);

  const impressao = useImpressao();
  const impressaoStore = useImpressaoStore();
  const { companyInfo } = useCompanyPrintInfo();

  /** Manda o orçamento térmico direto pra impressora configurada; false = sem impressora/falhou */
  async function imprimirEscPosDireto(orcamento: OrcamentoRead): Promise<boolean> {
    if (!impressao.podeImprimirDireto.value) return false;
    const bobina = impressaoStore.config.bobina;
    const logoRaster = await carregarLogoRaster(companyInfo.value.logo, DOTS[bobina]);
    const dados = saleToEscPos(orcamento, {
      bobina,
      empresa: companyInfo.value,
      tipo: 'ORCAMENTO',
      logoRaster,
      // Orçamento não movimenta caixa: nunca abre a gaveta.
    });
    return impressao.imprimirCupom(dados);
  }

  /**
   * Cupom Térmico sai direto pela impressora (sem diálogo); A4 abre o diálogo do
   * sistema. Sem impressora configurada, cai no diálogo — mesmo comportamento
   * do fluxo de venda.
   */
  async function handlePrintFormatSelected(format: PrintFormat) {
    if (
      format === 'CUPOM' &&
      orcamentoForPrint.value &&
      (await imprimirEscPosDireto(orcamentoForPrint.value))
    ) {
      closePrintSelectModal();
      printFormat.value = '' as PrintFormat;
      return;
    }
    handlePrintFormatSelectedBase(format);
  }

  /**
   * Regra única (sem perguntar formato): térmica configurada → orçamento ESC/POS
   * direto; sem térmica (ou falha) → recibo A4 abrindo o diálogo do sistema.
   */
  async function printOrcamento(orcamentoId: number, afterPrint?: () => void) {
    const orc = await orcamentoService.getOrcamento(orcamentoId);
    orcamentoForPrint.value = orc;
    const finalizar = () => {
      orcamentoForPrint.value = null;
      afterPrint?.();
    };
    if (await imprimirEscPosDireto(orc)) {
      finalizar();
      return;
    }
    printDirect('ORCAMENTO', 'A4', finalizar);
  }

  return {
    printType,
    printFormat,
    isPrintSelectModalOpen: isPrintSelectModalOpen,
    orcamentoForPrint,
    printOrcamento,
    handlePrintFormatSelected,
    closePrintSelectModal,
  };
}
