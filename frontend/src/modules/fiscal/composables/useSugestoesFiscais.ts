import { ref } from 'vue';

import { fiscalService } from '../services/fiscal.service';
import type { CampoSugerido } from '../types/fiscal.types';

/**
 * Sugestões fiscais para o cadastro de produto.
 *
 * A regra de aplicação, e ela é o ponto todo deste composable:
 * **só preenche o que está vazio.** Nunca sobrescreve o que o usuário digitou.
 *
 * O padrão já é consagrado no backend — `core/tarefas.py` semeia os códigos
 * SEFAZ das formas de pagamento com o comentário *"Só PREENCHE o que falta: a
 * loja pode ter trocado o padrão de propósito, e sobrescrever desfaria a
 * escolha."* A mesma lógica vale, com mais força ainda, para campo tributário:
 * quando o contador escolhe um CSOSN diferente do default, ele tem um motivo.
 *
 * `exige_confirmacao` marca as sugestões em que errar produz nota ACEITA E
 * ERRADA (a natureza de devolução, que desliga os tributos aproximados). Essas
 * nunca entram sozinhas.
 */
export function useSugestoesFiscais() {
  const sugestoes = ref<CampoSugerido[]>([]);
  /** Campos preenchidos por sugestão nesta sessão — a UI marca visualmente. */
  const camposSugeridos = ref<Set<string>>(new Set());
  const carregando = ref(false);

  async function carregar(): Promise<CampoSugerido[]> {
    carregando.value = true;
    try {
      const { sugestoes: recebidas } = await fiscalService.sugerirCamposProduto();
      sugestoes.value = recebidas ?? [];
      return sugestoes.value;
    } catch {
      // Sugestão é conveniência: sem ela o formulário continua funcionando
      // exatamente como antes. Não vale um toast de erro.
      sugestoes.value = [];
      return [];
    } finally {
      carregando.value = false;
    }
  }

  /**
   * Aplica as sugestões nos campos vazios.
   *
   * @param lerCampo  devolve o valor atual do campo no formulário
   * @param gravarCampo  grava o valor sugerido
   * @returns quantos campos foram preenchidos
   */
  function aplicarNosVazios(
    lerCampo: (campo: string) => unknown,
    gravarCampo: (campo: string, valor: string) => void,
  ): number {
    let aplicados = 0;

    for (const sugestao of sugestoes.value) {
      if (sugestao.valor === null || sugestao.exige_confirmacao) continue;

      const atual = lerCampo(sugestao.campo);
      const vazio = atual === null || atual === undefined || atual === '';
      if (!vazio) continue;

      gravarCampo(sugestao.campo, sugestao.valor);
      camposSugeridos.value.add(sugestao.campo);
      aplicados += 1;
    }

    return aplicados;
  }

  /** O "por quê?" de um campo — a fundamentação que a tela exibe. */
  function explicacao(campo: string): string | null {
    return sugestoes.value.find((s) => s.campo === campo)?.fundamentacao ?? null;
  }

  /** True enquanto o valor do campo veio de sugestão e não foi editado. */
  function veioDeSugestao(campo: string): boolean {
    return camposSugeridos.value.has(campo);
  }

  /**
   * Marca que o usuário assumiu o campo.
   *
   * A partir daqui ele deixa de ser "derivado" e passa a ser decisão de quem
   * cadastrou — é essa distinção que impede a próxima rodada de derivação de
   * apagar a escolha do contador.
   */
  function marcarComoDoUsuario(campo: string): void {
    camposSugeridos.value.delete(campo);
  }

  return {
    sugestoes,
    carregando,
    carregar,
    aplicarNosVazios,
    explicacao,
    veioDeSugestao,
    marcarComoDoUsuario,
  };
}
