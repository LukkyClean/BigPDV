import { ref } from 'vue';
import { useToast } from '@/shared/composables/useToast';
import { saleService } from '@/modules/sales/api.service';
import { verificarFiscalOS, emitirFiscalOS } from '@/modules/order-service/ordens/services/orderServiceFiscal.service';
import { fiscalService } from '@/modules/fiscal/services/fiscal.service';
import { getErrorMessage } from '@/shared/utils/error.utils';
import {
  ehEmissaoIncerta,
  resolverEmissaoIncerta,
  MENSAGEM_EMISSAO_INCERTA,
} from '@/modules/fiscal/composables/useEmissaoIncerta';
import type { PendenciaFiscal } from '@/shared/types/fiscal.types';
import type { DocumentoFiscalRead } from '@/modules/fiscal/types/fiscal.types';
import type { VendaNotaFiscalUpdate } from '@/modules/sales/schemas/sale.schema';
import type { ApiError } from '@/shared/types/axios.types';
import type { AxiosError } from 'axios';

export function useEmitirFiscal() {
  const pendencias = ref<PendenciaFiscal[]>([]);
  const pendenciasModalOpen = ref(false);
  const isVerificando = ref(false);

  const toast = useToast();

  function handleErroEmissao(err: unknown) {
    const axiosErr = err as AxiosError<any>;
    if (axiosErr?.response?.status === 501) {
      const detail = axiosErr.response.data?.detail;
      toast.info(
        'Integração não disponível',
        detail?.mensagem ?? 'A integração com a SEFAZ ainda não está disponível.',
      );
      return;
    }
    // A mensagem do backend é o que diz o que fazer. Trocá-la por um "erro ao
    // emitir" genérico deixava o operador sem saída — e a venda já foi paga.
    toast.error(
      'A nota fiscal não foi emitida',
      getErrorMessage(err as AxiosError<ApiError>),
    );
  }

  /**
   * Trata o caso em que a emissão ficou INDETERMINADA (timeout / rede).
   *
   * Nunca oferece "tentar de novo": consulta o que de fato aconteceu. Se a nota
   * existe, informa; se não existe, aí sim é seguro emitir outra vez.
   */
  async function handleEmissaoIncerta(vendaId: number): Promise<DocumentoFiscalRead | null> {
    const documento = await resolverEmissaoIncerta(vendaId);

    if (documento?.status === 'AUTORIZADA') {
      toast.success(
        'A nota já estava autorizada',
        'A resposta da SEFAZ demorou, mas a emissão deu certo. Não emita de novo.',
      );
      return documento;
    }

    if (documento) {
      toast.warning(
        `Nota ${documento.status.toLowerCase()}`,
        documento.mensagem_sefaz ?? 'Consulte o Centro Fiscal.',
      );
      return null;
    }

    toast.warning(MENSAGEM_EMISSAO_INCERTA.titulo, MENSAGEM_EMISSAO_INCERTA.descricao);
    return null;
  }

  /**
   * @deprecated SEM CHAMADORES desde 05/09/2026.
   *
   * Vai em `POST /vendas/{id}/emitir-fiscal`, que hoje é um stub: responde 422
   * (pendências) ou 501 (não implementado) e NUNCA emite. Os dois botões que a
   * usavam — SaleTable e SaleModal/NotaFiscalSection — passaram a levar o
   * usuário ao Centro Fiscal, onde a emissão de NF-e realmente acontece, com
   * preview e confirmação.
   *
   * Mantida porque o endpoint existe, está gated e testado: se a integração
   * direta for implementada, este é o ponto de religação. Se a decisão for
   * abandoná-la, remova esta função junto com `saleService.emitirFiscal`.
   */
  async function emitirVenda(vendaId: number) {
    isVerificando.value = true;
    try {
      const resultado = await saleService.verificarFiscal(vendaId);
      if (!resultado.completo) {
        pendencias.value = resultado.pendencias;
        pendenciasModalOpen.value = true;
        return;
      }
      try {
        await saleService.emitirFiscal(vendaId);
        toast.success('Nota fiscal emitida com sucesso!');
      } catch (err) {
        handleErroEmissao(err);
      }
    } catch (err) {
      toast.error(
        'Não conseguimos conferir os dados desta venda',
        getErrorMessage(err as AxiosError<ApiError>),
      );
    } finally {
      isVerificando.value = false;
    }
  }

  /**
   * Emite a NFC-e de uma venda do PDV, gravando antes o CPF/CNPJ digitado no
   * caixa.
   *
   * Devolve o DOCUMENTO FISCAL completo quando autorizado — é ele que carrega
   * QR Code, chave e tributos, que é o que o cupom precisa imprimir. Devolve
   * null em qualquer outro caso (pendência, rejeição, falha de rede): aí não
   * há cupom a imprimir, e o operador resolve pelo Centro Fiscal.
   */
  async function emitirNFCeVenda(
    vendaId: number,
    documentoConsumidor?: string | null,
    indicadorPresenca?: number,
  ): Promise<DocumentoFiscalRead | null> {
    isVerificando.value = true;
    try {
      // Grava o que o caixa escolheu ANTES de emitir. Sem isto o
      // payload_builder assumia 1 (presencial) para toda NFC-e, o que fazia
      // uma entrega a domicílio sair com indPres errado — e, pior, passar
      // batido pela trava interestadual, que trata indPres 1 como venda de
      // balcão e por definição interna.
      const dadosFiscais: VendaNotaFiscalUpdate = {};
      if (documentoConsumidor !== undefined) {
        dadosFiscais.documento_consumidor = documentoConsumidor;
      }
      if (indicadorPresenca !== undefined) {
        dadosFiscais.indicador_presenca = indicadorPresenca;
      }
      if (Object.keys(dadosFiscais).length > 0) {
        await saleService.upsertVendaNotaFiscal(vendaId, dadosFiscais);
      }

      const resultado = await saleService.verificarFiscal(vendaId);
      if (!resultado.completo) {
        pendencias.value = resultado.pendencias;
        pendenciasModalOpen.value = true;
        return null;
      }

      try {
        const emissao = await fiscalService.emitirNfce({ venda_id: vendaId });
        if (emissao.status === 'AUTORIZADA') {
          toast.success('NFC-e autorizada!');
          // O resumo da emissão não traz QR Code, chave nem tributos — e é
          // isso que o cupom precisa imprimir. Buscar o documento completo é
          // o que permite imprimir sem uma segunda ida à SEFAZ.
          try {
            return await fiscalService.obterDocumento(emissao.documento_id);
          } catch {
            // A nota está autorizada; só o cupom fica para a reimpressão.
            return null;
          }
        } else {
          // REJEITADA e INDETERMINADA precisam de tratamento humano, e a
          // mensagem da SEFAZ é o que diz o que fazer — engolir isso num
          // "erro ao emitir" genérico deixaria o operador sem saída.
          toast.warning(
            `NFC-e ${emissao.status.toLowerCase()}`,
            emissao.mensagem ?? 'Consulte o Centro Fiscal.',
          );
        }
        // Não autorizada: não há cupom fiscal a imprimir.
        return null;
      } catch (err) {
        // Timeout numa emissão não é falha — a nota pode existir.
        if (ehEmissaoIncerta(err)) return await handleEmissaoIncerta(vendaId);
        handleErroEmissao(err);
        return null;
      }
    } catch (err) {
      toast.error(
        'Não conseguimos conferir os dados desta venda',
        getErrorMessage(err as AxiosError<ApiError>),
      );
      return null;
    } finally {
      isVerificando.value = false;
    }
  }

  async function emitirOS(osNumero: string, tipoDocumento: string = 'ambos') {
    isVerificando.value = true;
    try {
      const resultado = await verificarFiscalOS(osNumero, tipoDocumento);
      if (!resultado.completo) {
        pendencias.value = resultado.pendencias;
        pendenciasModalOpen.value = true;
        return;
      }
      try {
        await emitirFiscalOS(osNumero, tipoDocumento);
        toast.success('Nota fiscal emitida com sucesso!');
      } catch (err) {
        handleErroEmissao(err);
      }
    } catch (err) {
      toast.error(
        'Não conseguimos conferir os dados desta OS',
        getErrorMessage(err as AxiosError<ApiError>),
      );
    } finally {
      isVerificando.value = false;
    }
  }

  return {
    pendencias,
    pendenciasModalOpen,
    isVerificando,
    emitirVenda,
    emitirNFCeVenda,
    emitirOS,
  };
}
