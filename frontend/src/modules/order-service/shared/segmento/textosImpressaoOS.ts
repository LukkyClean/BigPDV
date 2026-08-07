import { computed } from 'vue';

import { useSegmento } from '@/shared/composables/useSegmento';
import { useObjetoLabels } from './useObjetoLabels';

/**
 * Termos e rótulos das vias impressas da OS, por segmento.
 *
 * Não é só troca de palavra: uma oficina não fala em backup nem em chips
 * deixados no aparelho, e uma assistência técnica não fala em objetos pessoais
 * deixados no interior do veículo. Cada segmento carrega o seu pacote inteiro,
 * em vez de tentar costurar uma frase única que sirva para os dois.
 *
 * O pacote PADRÃO é o da assistência técnica, e isso é deliberado: informática
 * está em produção. Todo segmento sem pacote próprio continua imprimindo
 * exatamente o que imprimia antes — não existe fallback "genérico" capaz de
 * mudar o papel de quem já roda. Segmento novo que precise de termo próprio
 * ganha seu pacote aqui.
 */

/**
 * Via em bobina (cupom HTML + ESC/POS): texto corrido, condensado e SEM acento,
 * seguindo o que essas duas vias já faziam — o gerador ESC/POS remove acento na
 * codificação, e o cupom HTML é escrito assim para dizer a mesma coisa.
 */
export interface TextosCupomOS {
  /** Substantivo do objeto nas frases, sem acento ("Veiculo", "Objeto"). */
  objeto: string;
  /** Rótulo do identificador na largura da bobina; `null` = usar o do contrato. */
  identificador: string | null;
  /** Continua a frase "Nao cobre ...". */
  garantiaExclusoes: string;
  semReparo: string;
  cancelamento: string;
  condicoesEntrada: string;
  prazoRetirada: string;
}

export interface TextosImpressaoOS {
  /** Substantivo do objeto dentro das frases da A4 ("veículo", "objeto"). */
  objeto: string;
  /** Plural, em início de frase ("Veículos", "Objetos"). */
  objetoPlural: string;
  /** Como a empresa se nomeia nos termos ("A empresa", "A assistência técnica"). */
  empresa: string;
  /** Rótulo do identificador na coluna da A4; `null` = usar o do contrato. */
  identificador: string | null;
  /** Continua a frase "A garantia NÃO COBRE: ...". */
  garantiaExclusoes: string;
  condicoesEntrada: string;
  cupom: TextosCupomOS;
}

/**
 * Assistência técnica — texto reproduzido palavra por palavra do que as vias
 * imprimiam antes deste arquivo existir. Mexer aqui muda o papel de um cliente
 * em produção.
 */
const ASSISTENCIA_TECNICA: TextosImpressaoOS = {
  objeto: 'objeto',
  objetoPlural: 'Objetos',
  empresa: 'A assistência técnica',
  // O contrato chama de "Nº de série / IMEI", que não cabe na coluna da via.
  identificador: 'Nº Série',
  garantiaExclusoes:
    'mau uso, contato com líquidos, quedas, oxidação, violação de selos de garantia ou intervenção de terceiros.',
  condicoesEntrada:
    'O cliente declara estar ciente que a empresa não se responsabiliza por perda de dados '
    + '(backup é responsabilidade do cliente) nem por chips/cartões de memória deixados no aparelho. '
    + 'Autorizo a análise técnica do objeto acima. Em caso de não aprovação do orçamento, estou ciente '
    + 'que poderá ser cobrada taxa de análise técnica.',
  cupom: {
    objeto: 'Objeto',
    identificador: 'N/S',
    garantiaExclusoes: 'mau uso, liquidos, quedas ou intervencao de terceiros.',
    semReparo: 'Objeto devolvido sem reparo. Sem garantia aplicavel a esta OS.',
    cancelamento:
      'A OS acima foi cancelada nesta data. Objeto devolvido ao cliente sem reparos ou com reparos '
      + 'parciais, isentando a assistencia de garantias sobre servicos nao concluidos.',
    condicoesEntrada:
      'O cliente declara estar ciente que a empresa nao se responsabiliza por perda de dados nem por '
      + 'chips/cartoes deixados no aparelho. Autorizo a analise tecnica do objeto.',
    prazoRetirada:
      'PRAZO DE RETIRADA: Objetos nao retirados em 90 dias apos aviso de conclusao serao considerados '
      + 'abandonados, conforme Art. 1.275 do Codigo Civil Brasileiro.',
  },
};

/**
 * Oficina mecânica. O identificador fica `null` de propósito: o contrato já
 * devolve "Placa", que cabe na via — não há o que encurtar.
 */
const OFICINA_MECANICA: TextosImpressaoOS = {
  objeto: 'veículo',
  objetoPlural: 'Veículos',
  empresa: 'A empresa',
  identificador: null,
  garantiaExclusoes:
    'mau uso, falta de manutenção preventiva, desgaste natural de peças, uso indevido do veículo, '
    + 'adulteração de componentes ou intervenção de terceiros.',
  condicoesEntrada:
    'O cliente declara estar ciente que a empresa não se responsabiliza por objetos pessoais deixados '
    + 'no interior do veículo. Autorizo a execução dos serviços descritos e a movimentação do veículo '
    + 'por funcionários da empresa para testes e diagnóstico. Em caso de não aprovação do orçamento, '
    + 'estou ciente que poderá ser cobrada taxa de diagnóstico.',
  cupom: {
    objeto: 'Veiculo',
    identificador: null,
    garantiaExclusoes: 'mau uso, falta de manutencao, desgaste natural ou intervencao de terceiros.',
    semReparo: 'Veiculo devolvido sem reparo. Sem garantia aplicavel a esta OS.',
    cancelamento:
      'A OS acima foi cancelada nesta data. Veiculo devolvido ao cliente sem reparos ou com reparos '
      + 'parciais, isentando a empresa de garantias sobre servicos nao concluidos.',
    condicoesEntrada:
      'O cliente declara estar ciente que a empresa nao se responsabiliza por objetos pessoais deixados '
      + 'no interior do veiculo. Autorizo a execucao dos servicos e a movimentacao do veiculo para testes.',
    prazoRetirada:
      'PRAZO DE RETIRADA: Veiculos nao retirados em 90 dias apos aviso de conclusao serao considerados '
      + 'abandonados, conforme Art. 1.275 do Codigo Civil Brasileiro.',
  },
};

const PACOTES: Record<string, TextosImpressaoOS> = {
  oficina_mecanica: OFICINA_MECANICA,
  assistencia_tecnica: ASSISTENCIA_TECNICA,
};

const PADRAO = ASSISTENCIA_TECNICA;

export function useTextosImpressaoOS() {
  const { segmento } = useSegmento();
  const { labelIdentificador } = useObjetoLabels();

  const textos = computed<TextosImpressaoOS>(
    () => PACOTES[segmento.value ?? ''] ?? PADRAO,
  );

  /** Rótulo do identificador na A4: o encurtado do pacote, senão o do contrato. */
  const identificadorA4 = computed(
    () => textos.value.identificador ?? labelIdentificador.value,
  );

  const identificadorCupom = computed(
    () => textos.value.cupom.identificador ?? labelIdentificador.value,
  );

  return { textos, identificadorA4, identificadorCupom };
}
