import { ref } from 'vue';
import { useToast } from '@/shared/composables/useToast';
import { saleService } from '@/modules/sales/api.service';
import { verificarFiscalOS, emitirFiscalOS } from '@/modules/order-service/ordens/services/orderServiceFiscal.service';
import type { PendenciaFiscal } from '@/shared/types/fiscal.types';
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
    toast.error('Erro ao emitir nota fiscal.');
  }

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
      toast.error('Erro ao verificar dados fiscais.');
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
      toast.error('Erro ao verificar dados fiscais.');
    } finally {
      isVerificando.value = false;
    }
  }

  return { pendencias, pendenciasModalOpen, isVerificando, emitirVenda, emitirOS };
}
