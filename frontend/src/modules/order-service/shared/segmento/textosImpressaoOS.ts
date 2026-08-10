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
  /** Cabeçalho do texto livre relatado pelo cliente, em caixa alta na bobina. */
  defeito: string;
  /** Quem assina pela loja, na bobina (sem acento). */
  assinaturaLoja: string;
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
  /**
   * Cabeçalho do quadro do objeto na A4.
   *
   * Vem inteiro do pacote, e não montado como `'Dados do ' + labelSingular`,
   * porque português tem gênero: essa montagem imprimia "DADOS DO ARTE".
   */
  tituloObjeto: string;
  /** Rótulo do identificador na coluna da A4; `null` = usar o do contrato. */
  identificador: string | null;
  /**
   * Cabeçalho do texto livre relatado pelo cliente.
   *
   * "Defeito" pressupõe conserto. Numa serigrafia ninguém traz camisa
   * quebrada: o cliente encomenda, e o cabeçalho da via precisa dizer isso.
   */
  defeito: string;
  /** Continua a frase "A garantia NÃO COBRE: ...". */
  garantiaExclusoes: string;
  condicoesEntrada: string;
  /**
   * Quem assina pela loja, na linha de assinatura.
   *
   * "Técnico" pressupõe conserto: numa serigrafia quem assina é o responsável
   * pelo pedido, não um técnico. Os dois segmentos em produção mantêm a
   * palavra que sempre imprimiram.
   */
  assinaturaLoja: string;
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
  tituloObjeto: 'Dados do Equipamento',
  // O contrato chama de "Nº de série / IMEI", que não cabe na coluna da via.
  identificador: 'Nº Série',
  defeito: 'Defeito Relatado / Solicitação',
  garantiaExclusoes:
    'mau uso, contato com líquidos, quedas, oxidação, violação de selos de garantia ou intervenção de terceiros.',
  condicoesEntrada:
    'O cliente declara estar ciente que a empresa não se responsabiliza por perda de dados '
    + '(backup é responsabilidade do cliente) nem por chips/cartões de memória deixados no aparelho. '
    + 'Autorizo a análise técnica do objeto acima. Em caso de não aprovação do orçamento, estou ciente '
    + 'que poderá ser cobrada taxa de análise técnica.',
  assinaturaLoja: 'Técnico Responsável',
  cupom: {
    objeto: 'Objeto',
    identificador: 'N/S',
    defeito: 'DEFEITO RELATADO',
    assinaturaLoja: 'Tecnico Responsavel',
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
  tituloObjeto: 'Dados do Veículo',
  identificador: null,
  defeito: 'Defeito Relatado / Solicitação',
  garantiaExclusoes:
    'mau uso, falta de manutenção preventiva, desgaste natural de peças, uso indevido do veículo, '
    + 'adulteração de componentes ou intervenção de terceiros.',
  condicoesEntrada:
    'O cliente declara estar ciente que a empresa não se responsabiliza por objetos pessoais deixados '
    + 'no interior do veículo. Autorizo a execução dos serviços descritos e a movimentação do veículo '
    + 'por funcionários da empresa para testes e diagnóstico. Em caso de não aprovação do orçamento, '
    + 'estou ciente que poderá ser cobrada taxa de diagnóstico.',
  assinaturaLoja: 'Técnico Responsável',
  cupom: {
    objeto: 'Veiculo',
    identificador: null,
    defeito: 'DEFEITO RELATADO',
    assinaturaLoja: 'Tecnico Responsavel',
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

/**
 * Serigrafia. Duas escolhas de vocabulário que valem explicação:
 *
 * 1. O substantivo é **peça**, não "arte". O objeto de serviço é a arte (é ela
 *    que se repete entre pedidos), mas quem entra e sai da loja é a peça — e a
 *    via fala do que o cliente entrega e leva de volta. "Arte devolvida sem
 *    estampa" não diz nada; "Peças devolvidas sem estampa" diz tudo.
 *
 * 2. As condições de entrada carregam a cláusula de peça do cliente, que é o
 *    padrão do ramo: peça nova e sem uso, e a loja não repõe o que estragar no
 *    processo. Numa loja que estampa peça de terceiro, esse parágrafo é a
 *    diferença entre um prejuízo combinado e uma discussão no balcão.
 */
const SERIGRAFIA: TextosImpressaoOS = {
  objeto: 'peça',
  objetoPlural: 'Peças',
  empresa: 'A empresa',
  tituloObjeto: 'Dados da Arte',
  // O contrato chama de "Código da arte", que não cabe na coluna da via.
  identificador: 'Arte',
  defeito: 'Descrição do Pedido',
  garantiaExclusoes:
    'lavagem com água quente, uso de alvejante ou secadora, passar ferro diretamente sobre a estampa, '
    + 'desgaste natural por lavagens sucessivas ou uso indevido da peça.',
  condicoesEntrada:
    'As peças entregues pelo cliente devem ser novas, sem uso e do mesmo modelo. A empresa não se '
    + 'responsabiliza por defeitos de fabricação das peças fornecidas pelo cliente nem repõe peças '
    + 'danificadas durante o processo de estampa. O cliente declara ter conferido e aprovado a arte, '
    + 'as cores e a posição da estampa antes da produção.',
  assinaturaLoja: 'Responsável',
  cupom: {
    objeto: 'Peca',
    identificador: 'Arte',
    defeito: 'DESCRICAO DO PEDIDO',
    assinaturaLoja: 'Responsavel',
    garantiaExclusoes:
      'agua quente, alvejante, secadora, ferro sobre a estampa ou uso indevido da peca.',
    semReparo: 'Pecas devolvidas sem estampa. Sem garantia aplicavel a esta OS.',
    cancelamento:
      'A OS acima foi cancelada nesta data. Pecas devolvidas ao cliente sem estampa ou com producao '
      + 'parcial, isentando a empresa de garantias sobre servicos nao concluidos.',
    condicoesEntrada:
      'Pecas do cliente devem ser novas e sem uso. A empresa nao repoe pecas danificadas no processo '
      + 'de estampa. Cliente declara ter aprovado arte, cores e posicao antes da producao.',
    prazoRetirada:
      'PRAZO DE RETIRADA: Pecas nao retiradas em 90 dias apos aviso de conclusao serao consideradas '
      + 'abandonadas, conforme Art. 1.275 do Codigo Civil Brasileiro.',
  },
};

const PACOTES: Record<string, TextosImpressaoOS> = {
  oficina_mecanica: OFICINA_MECANICA,
  assistencia_tecnica: ASSISTENCIA_TECNICA,
  serigrafia: SERIGRAFIA,
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
