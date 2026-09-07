/**
 * @fileoverview Segunda via do DANFE NFC-e a partir do Centro Fiscal.
 *
 * A reimpressão parte do DOCUMENTO fiscal, não de uma nova consulta à SEFAZ:
 * chave, protocolo, QR Code e tributos já estão gravados desde a emissão. O
 * que falta buscar é a venda, porque o cupom discrimina os itens — e isso o
 * documento não guarda.
 */

import { ref } from 'vue';

import { saleService } from '@/modules/sales/api.service';
import { useNfcePrintFlow } from '@/modules/sales/composables/flows/useNfcePrintFlow';
import { usePaymentMethodsQuery } from '@/modules/sales/composables/queries/usePaymentMethodsQuery';
import { useToast } from '@/shared/composables/useToast';
import { getPaymentDisplayName } from '@/shared/utils/print.utils';

import type { DocumentoFiscalRead } from '../types/fiscal.types';

export function useNfceReimpressao() {
  const toast = useToast();
  const { formasPagamento } = usePaymentMethodsQuery();

  function resolverNomePagamento(formaId: number): string {
    const forma = formasPagamento.value.find((fp) => fp.id === formaId);
    return getPaymentDisplayName(forma?.nome ?? 'Desconhecido');
  }

  const { imprimirDanfeNfce } = useNfcePrintFlow(resolverNomePagamento);

  const isReimprimindo = ref(false);

  /** True quando o documento pode gerar uma segunda via. */
  function podeReimprimir(documento: DocumentoFiscalRead | null | undefined): boolean {
    if (!documento) return false;
    return (
      documento.tipo_documento === 'NFCE'
      && documento.status === 'AUTORIZADA'
      // Sem QR Code não há cupom válido a reimprimir — seria entregar ao
      // cliente um papel que parece fiscal e não é conferível.
      && Boolean(documento.qrcode)
      && Boolean(documento.venda_id ?? documento.origem_id)
    );
  }

  async function reimprimir(documento: DocumentoFiscalRead): Promise<boolean> {
    if (!podeReimprimir(documento)) return false;

    const vendaId = documento.venda_id ?? documento.origem_id;
    if (!vendaId) return false;

    isReimprimindo.value = true;
    try {
      const venda = await saleService.getSale(vendaId);

      // O CPF do consumidor vive na nota da venda, não no documento fiscal.
      // Falhar em buscá-lo não impede a segunda via: o cupom sai declarando
      // consumidor não identificado, que é pior que o ideal mas melhor que
      // não sair.
      let documentoConsumidor: string | null = null;
      try {
        const nota = await saleService.getVendaNotaFiscal(vendaId);
        documentoConsumidor = nota?.documento_consumidor ?? null;
      } catch {
        documentoConsumidor = null;
      }

      return await imprimirDanfeNfce(venda, documento, {
        documentoConsumidor,
        reimpressao: true,
      });
    } catch (erro) {
      console.error('[NFC-e] Falha ao reimprimir o cupom:', erro);
      toast.error(
        'Não foi possível reimprimir',
        'Não conseguimos carregar a venda deste cupom.',
      );
      return false;
    } finally {
      isReimprimindo.value = false;
    }
  }

  return { reimprimir, podeReimprimir, isReimprimindo };
}
