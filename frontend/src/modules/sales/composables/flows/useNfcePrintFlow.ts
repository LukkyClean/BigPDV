/**
 * @fileoverview Impressão do DANFE NFC-e na térmica.
 *
 * Separado do `useSalePrintFlow` de propósito: aquele decide entre A4 e cupom,
 * pergunta ao operador e respeita `auto_imprimir_venda`. O cupom fiscal não
 * tem essas escolhas — ele é entregue ao consumidor por obrigação legal, na
 * bobina, sempre. Misturar os dois faria a configuração de comprovante
 * gerencial decidir, sem querer, se um documento fiscal é impresso.
 */

import { useImpressao } from '@/shared/composables/useImpressao';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { useToast } from '@/shared/composables/useToast';
import { useCompanyPrintInfo } from '@/shared/utils/print.utils';
import { carregarLogoRaster } from '@/shared/services/escposImagem';
import { DOTS } from '@/shared/services/escpos';
import { nfceToEscPos } from '../../components/print/nfceToEscPos';

import type { SaleRead } from '../../schemas/sale.schema';
import type { DocumentoFiscalRead } from '@/modules/fiscal/types/fiscal.types';

interface OpcoesImpressaoNfce {
  /** CPF/CNPJ digitado no caixa, quando não veio do cadastro do cliente. */
  documentoConsumidor?: string | null;
  /** Segunda via — imprime o aviso de reimpressão. */
  reimpressao?: boolean;
}

export function useNfcePrintFlow(resolverPagamento?: (id: number) => string) {
  const impressao = useImpressao();
  const impressaoStore = useImpressaoStore();
  const { companyInfo } = useCompanyPrintInfo();
  const toast = useToast();

  /**
   * Imprime o cupom fiscal. Devolve false quando não há térmica configurada
   * ou a impressão falhou.
   *
   * NUNCA levanta: quando isto roda a NFC-e já está autorizada na SEFAZ. Uma
   * falha de impressora não pode desfazer a venda nem virar erro na tela do
   * caixa — o documento é válido, e a segunda via resolve o papel.
   */
  async function imprimirDanfeNfce(
    sale: SaleRead,
    documento: DocumentoFiscalRead,
    opcoes: OpcoesImpressaoNfce = {},
  ): Promise<boolean> {
    if (documento.status !== 'AUTORIZADA') return false;

    if (!impressao.podeImprimirDireto.value) {
      // Aviso, não erro: a nota existe e vale. O que falta é o papel.
      toast.info(
        'Cupom não impresso',
        'Nenhuma impressora térmica configurada. A NFC-e foi autorizada e pode '
        + 'ser reimpressa pelo Centro Fiscal.',
      );
      return false;
    }

    try {
      const bobina = impressaoStore.config.bobina;
      const logoRaster = await carregarLogoRaster(companyInfo.value.logo, DOTS[bobina]);

      const dados = nfceToEscPos(sale, documento, {
        bobina,
        empresa: companyInfo.value,
        resolverPagamento,
        logoRaster,
        documentoConsumidor: opcoes.documentoConsumidor,
        reimpressao: opcoes.reimpressao,
      });

      return await impressao.imprimirCupom(dados);
    } catch (erro) {
      console.error('[NFC-e] Falha ao imprimir o cupom fiscal:', erro);
      toast.warning(
        'Cupom não impresso',
        'A NFC-e foi autorizada, mas o cupom não saiu. Reimprima pelo Centro Fiscal.',
      );
      return false;
    }
  }

  return { imprimirDanfeNfce };
}
