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
    openPrintSelect,
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
   * A gaveta abre pelo pulso ESC/POS, que normalmente viaja DENTRO do cupom.
   * Quando o cupom não é impresso (formato A4, ou o caixa escolhe o formato no
   * modal), o pulso precisa ir sozinho — senão trocar o formato do recibo, que
   * é decisão de papel, apagaria em silêncio a abertura da gaveta, que é
   * decisão de dinheiro. Falhar aqui não pode derrubar a venda já finalizada.
   */
  async function abrirGavetaAvulsa(sale: SaleRead) {
    const config = impressaoStore.config;
    const deveAbrir =
      config.gaveta_ativa && config.abrir_gaveta_na_venda && vendaTemPagamentoDinheiro(sale);
    if (!deveAbrir || !impressao.podeImprimirDireto.value) return;
    try {
      await impressao.abrirGaveta();
    } catch (e) {
      console.error('[Impressão] Falha ao abrir a gaveta:', e);
    }
  }

  /**
   * Impressão pós-finalização da venda conforme a configuração local:
   * automático + cupom → ESC/POS silencioso na térmica;
   * automático + A4 → abre o diálogo do Windows direto com o recibo pronto;
   * perguntar → modal de formato; não imprimir → só executa o callback.
   * Falha no ESC/POS cai no A4.
   */
  async function imprimirAposFinalizar(sale: SaleRead, afterPrint?: () => void) {
    const config = impressaoStore.config;

    if (config.auto_imprimir_venda === 'nao') {
      afterPrint?.();
      return;
    }

    const finalizar = () => {
      saleForPrint.value = null;
      afterPrint?.();
    };

    // 'perguntar' → o caixa decide o papel nesta venda. A gaveta vai à parte,
    // porque o pulso não pode depender do formato que ele vai escolher.
    if (config.auto_imprimir_venda === 'perguntar') {
      await abrirGavetaAvulsa(sale);
      saleForPrint.value = sale;
      openPrintSelect('VENDA', finalizar);
      return;
    }

    // Formato Cupom + térmica configurada → cupom direto (com o pulso da gaveta
    // embutido). Com formato A4 este ramo é PULADO: ESC/POS são bytes de
    // comando, e numa impressora comum saem como uma folha de pontinhos.
    if (config.formato_venda === 'cupom' && impressao.podeImprimirDireto.value) {
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
    } else {
      // Nenhum cupom sairá: o pulso da gaveta não tem carona e vai sozinho.
      await abrirGavetaAvulsa(sale);
    }

    // Formato A4, sem térmica, ou falha no ESC/POS → recibo A4 abrindo o diálogo.
    saleForPrint.value = sale;
    printDirect('VENDA', 'A4', finalizar);
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
