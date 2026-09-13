import { ref, computed } from 'vue';

import { fiscalService } from '../services/fiscal.service';
import type { ValidacaoFiscalProduto } from '../types/fiscal.types';

/**
 * A conferência fiscal do produto, antes de salvar.
 *
 * POR QUE NÃO É UM ZOD NA TELA
 * ----------------------------
 * A regra já existe no `validators.py` e é mais esperta que "campo
 * obrigatório": CEST só é exigido sob substituição tributária, redução de base
 * só com CST 20, e há códigos que o motor ainda não calcula. Reescrever isso
 * aqui criaria um segundo lugar para desatualizar — e quando os dois
 * discordam, o cadastro aprova o que a emissão recusa.
 *
 * O QUE ESTE COMPOSABLE NÃO FAZ: BLOQUEAR O SALVAR
 * ------------------------------------------------
 * As pendências são AVISO. Um produto pode ser cadastrado incompleto de
 * propósito — o lojista está esperando o contador responder, ou nem emite nota
 * ainda. Transformar isso em erro de formulário travaria o cadastro de quem
 * não tem nada a ver com NF-e.
 *
 * Quem recusa é o gate, na hora de emitir. Aqui a gente só adianta a notícia.
 */
export function useValidacaoFiscalProduto() {
  const resultado = ref<ValidacaoFiscalProduto | null>(null);
  const conferindo = ref(false);

  /**
   * Confere o rascunho. Nunca levanta: falha de rede não pode virar erro no
   * cadastro de produto, que existe há muito mais tempo que o módulo fiscal.
   */
  async function conferir(dados: Record<string, unknown>, nomeProduto?: string) {
    // Sem NCM não há o que conferir — é o primeiro campo e todo o resto
    // depende dele. Pedir ao servidor a cada tecla do nome seria ruído.
    if (!dados.ncm) {
      resultado.value = null;
      return;
    }

    conferindo.value = true;
    try {
      resultado.value = await fiscalService.validarProdutoFiscal(dados, nomeProduto);
    } catch {
      // Inclui o 422 do formato (NCM com menos de 8 dígitos), que o Zod da
      // tela já mostra no campo — repetir seria dizer duas vezes a mesma coisa.
      resultado.value = null;
    } finally {
      conferindo.value = false;
    }
  }

  /** A mensagem de um campo, para aparecer embaixo dele. */
  function pendenciaDoCampo(campo: string): string | null {
    return resultado.value?.pendencias.find((p) => p.campo === campo)?.mensagem ?? null;
  }

  /** De onde veio o valor: 'produto', 'ncm' ou 'padrao'. */
  function procedencia(campo: string): string | null {
    return resultado.value?.procedencia?.[campo] ?? null;
  }

  const podeEmitir = computed(() => resultado.value?.pode_emitir ?? null);

  /**
   * Pendências que NÃO têm campo visível para marcar.
   *
   * Existem porque o campo pode estar escondido pelo regime, ou recolhido na
   * seção de exceção. Erro preso a um campo que a tela não renderiza é o bug
   * do complemento da empresa: o usuário vê "não aconteceu nada". Estas vão
   * para o resumo, onde ele lê.
   */
  function pendenciasSemCampo(camposVisiveis: string[]): { campo: string; mensagem: string }[] {
    return (resultado.value?.pendencias ?? []).filter(
      (p) => !camposVisiveis.includes(p.campo),
    );
  }

  return {
    resultado,
    conferindo,
    podeEmitir,
    conferir,
    pendenciaDoCampo,
    procedencia,
    pendenciasSemCampo,
  };
}
