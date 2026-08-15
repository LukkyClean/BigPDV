import { ref } from 'vue';
import { usePrintFlow } from '@/shared/composables/usePrintFlow';
import { useImpressao } from '@/shared/composables/useImpressao';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { useCompanyPrintInfo, getPaymentDisplayName } from '@/shared/utils/print.utils';
import { usePaymentMethodsQuery } from '../queries/usePaymentMethodsQuery';
import { saleToEscPos } from '../../components/print/saleToEscPos';
import { DOTS } from '@/shared/services/escpos';
import { carregarLogoRaster } from '@/shared/services/escposImagem';
import { saleService } from '../../api.service';
import type { SaleRead } from '../../schemas/sale.schema';
import type { PrintFormat } from '@/shared/components/print/print.types';

export type SalePrintType = 'VENDA';

export function useSalePrintFlow() {
  const {
    printType,
    printFormat,
    isPrintSelectModalOpen,
    printDirect,
    handlePrintFormatSelected: handlePrintFormatSelectedBase,
    closePrintSelectModal,
  } = usePrintFlow<SalePrintType>();

  const saleForPrint = ref<SaleRead | null>(null);
  const { formasPagamento } = usePaymentMethodsQuery();

  function resolvePaymentMethodName(formaId: number): string {
    const method = formasPagamento.value.find((fp) => fp.id === formaId);
    return getPaymentDisplayName(method?.nome ?? 'Desconhecido');
  }

  /**
   * Regra única (sem perguntar formato): térmica configurada → cupom ESC/POS
   * direto; sem térmica (ou falha) → recibo A4 abrindo o diálogo do sistema.
   */
  async function decidirEImprimir(sale: SaleRead, type: SalePrintType, afterPrint?: () => void) {
    saleForPrint.value = sale;
    const finalizar = () => {
      saleForPrint.value = null;
      afterPrint?.();
    };
    if (await imprimirEscPosDireto(sale)) {
      finalizar();
      return;
    }
    printDirect(type, 'A4', finalizar);
  }

  async function printSale(saleId: number, type: SalePrintType, afterPrint?: () => void) {
    const sale = await saleService.getSale(saleId);
    await decidirEImprimir(sale, type, afterPrint);
  }

  function printSaleData(sale: SaleRead, type: SalePrintType, afterPrint?: () => void) {
    void decidirEImprimir(sale, type, afterPrint);
  }

  const impressao = useImpressao();
  const impressaoStore = useImpressaoStore();
  const { companyInfo } = useCompanyPrintInfo();

  function vendaTemPagamentoDinheiro(sale: SaleRead): boolean {
    return (sale.pagamentos ?? []).some((pg) =>
      resolvePaymentMethodName(pg.forma_pagamento_id).toLowerCase().includes('dinheiro'),
    );
  }

  /** Manda o cupom térmico direto pra impressora configurada; false = sem impressora/falhou */
  async function imprimirEscPosDireto(sale: SaleRead): Promise<boolean> {
    if (!impressao.podeImprimirDireto.value) return false;
    const bobina = impressaoStore.config.bobina;
    const logoRaster = await carregarLogoRaster(companyInfo.value.logo, DOTS[bobina]);
    const dados = saleToEscPos(sale, {
      bobina,
      empresa: companyInfo.value,
      resolverPagamento: resolvePaymentMethodName,
      logoRaster,
      // Reimpressão manual não deve reabrir a gaveta (só a impressão pós-venda faz isso)
    });
    return impressao.imprimirCupom(dados);
  }

  /**
   * Formato escolhido no modal de reimpressão manual: Cupom Térmico sai direto
   * pela impressora (sem diálogo); A4 continua abrindo o diálogo de impressão
   * do sistema, onde o usuário escolhe a impressora/PDF.
   */
  async function handlePrintFormatSelected(format: PrintFormat) {
    if (format === 'CUPOM' && saleForPrint.value && (await imprimirEscPosDireto(saleForPrint.value))) {
      closePrintSelectModal();
      printFormat.value = '' as PrintFormat;
      return;
    }
    handlePrintFormatSelectedBase(format);
  }

  /**
   * Impressão pós-finalização da venda conforme a configuração local:
   * automático + cupom → ESC/POS silencioso na térmica;
   * automático + A4 → abre o diálogo do Windows direto com o recibo pronto;
   * perguntar → modal de formato; não imprimir → só executa o callback.
   * Falha no ESC/POS cai no modal de formato.
   */
  async function imprimirAposFinalizar(sale: SaleRead, afterPrint?: () => void) {
    const config = impressaoStore.config;

    if (config.auto_imprimir_venda === 'nao') {
      afterPrint?.();
      return;
    }

    // Térmica configurada → cupom direto (abre a gaveta quando for pagamento em dinheiro).
    if (impressao.podeImprimirDireto.value) {
      const logoRaster = await carregarLogoRaster(companyInfo.value.logo, DOTS[config.bobina]);
      const dados = saleToEscPos(sale, {
        bobina: config.bobina,
        empresa: companyInfo.value,
        resolverPagamento: resolvePaymentMethodName,
        abrirGaveta: config.gaveta_ativa && config.abrir_gaveta_na_venda && vendaTemPagamentoDinheiro(sale),
        logoRaster,
      });
      if (await impressao.imprimirCupom(dados)) {
        afterPrint?.();
        return;
      }
    }

    // Sem térmica (ou falha na impressão) → recibo A4 abrindo o diálogo do sistema.
    saleForPrint.value = sale;
    printDirect('VENDA', 'A4', () => {
      saleForPrint.value = null;
      afterPrint?.();
    });
  }

  return {
    imprimirAposFinalizar,
    printType,
    printFormat,
    isPrintSelectModalOpen,
    saleForPrint,
    printSale,
    printSaleData,
    handlePrintFormatSelected,
    closePrintSelectModal,
    resolvePaymentMethodName,
  };
}
