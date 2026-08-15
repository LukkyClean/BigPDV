/**
 * @fileoverview Decisor global de impressão térmica
 * @description Decide entre impressão ESC/POS direta (silenciosa) e o fluxo
 * tradicional de modal + window.print(). Os geradores de conteúdo ficam em
 * cada módulo (saleToEscPos, osToEscPos); aqui só roteamos e tratamos erro.
 */

import { computed } from 'vue'
import { useImpressaoStore } from '@/shared/stores/impressao.store'
import { useToast } from '@/shared/composables/useToast'
import {
  impressaoDisponivel,
  imprimirRaw,
  imprimirRede,
} from '@/shared/services/impressao.service'
import { gerarCupomTeste, gerarPulsoGaveta } from '@/shared/services/escpos'
import type { ConfigImpressao } from '@/shared/stores/impressao.store'

export function useImpressao() {
  const store = useImpressaoStore()
  const toast = useToast()

  const podeImprimirDireto = computed(
    () => impressaoDisponivel() && store.impressoraConfigurada,
  )

  async function enviar(dados: Uint8Array, config: ConfigImpressao = store.config): Promise<void> {
    if (config.tipo_conexao === 'rede') {
      if (!config.ip_impressora) throw new Error('IP da impressora não configurado')
      await imprimirRede(config.ip_impressora, config.porta_impressora, dados)
      return
    }
    if (!config.impressora_termica) throw new Error('Impressora não configurada')
    await imprimirRaw(config.impressora_termica, dados)
  }

  /** Envia bytes prontos de cupom; retorna true se imprimiu, false para fallback */
  async function imprimirCupom(dados: Uint8Array): Promise<boolean> {
    try {
      await enviar(dados)
      // Feedback discreto: o envio térmico é silencioso (sem diálogo), então
      // sem isto o usuário não sabe se saiu — vale para o automático e o manual.
      toast.success('Cupom enviado à impressora')
      return true
    } catch (error) {
      console.error('[Impressão] Falha ao imprimir cupom:', error)
      toast.error('Falha ao imprimir o cupom', 'Verifique a impressora. Abrindo a via A4...')
      return false
    }
  }

  /** Cupom de teste usando uma config arbitrária (ex.: o form da tela, antes de salvar) */
  async function imprimirTeste(config: ConfigImpressao): Promise<void> {
    await enviar(gerarCupomTeste(config.bobina), config)
  }

  async function abrirGaveta(config: ConfigImpressao = store.config): Promise<void> {
    await enviar(gerarPulsoGaveta(), config)
  }

  return { podeImprimirDireto, imprimirCupom, imprimirTeste, abrirGaveta }
}
