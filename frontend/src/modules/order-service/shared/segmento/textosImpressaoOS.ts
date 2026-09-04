import { computed, toValue, type MaybeRefOrGetter } from 'vue';

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
  /**
   * Função do prazo, e não texto pronto: o número vem de
   * `configuracoes_os.prazo_abandono_dias`, que a loja edita em Configurações →
   * Ordens de Serviço. Estava chumbado em 90 nas três vias, então mudar a
   * configuração não mudava o papel — o cliente lia um prazo e o relatório de
   * abandono usava outro.
   */
  prazoRetirada: (dias: number) => string;
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
  /**
   * Cláusula de prazo de retirada da A4, INTEIRA — mesma razão do
   * `tituloObjeto`: português tem gênero.
   *
   * A frase era fixa no template, no masculino, com só o substantivo
   * interpolado. Em serigrafia isso imprimia "Peças ... não forem retirados ...
   * serão considerados abandonados ... poderão ser destinados" — quatro erros
   * de concordância na cláusula jurídica da via do cliente.
   *
   * @param prazo Prazo já formatado por extenso (ex: "90 (noventa) dias").
   */
  prazoRetiradaEntradaA4: (prazo: string) => string;
  /**
   * A MESMA cláusula, na via de SAÍDA (dentro do Termo de Garantia).
   *
   * São duas de propósito: a redação difere ("vendidos para custeio das
   * despesas" contra "destinados para cobrir as despesas do serviço") e o
   * formato do prazo também ("90 dias" contra "90 (noventa) dias"). Cada uma
   * reproduz exatamente o que sua via já imprimia — juntá-las numa só mudaria
   * o papel de dois segmentos em produção.
   *
   * @param prazo Prazo já formatado (ex: "90 dias").
   */
  prazoRetiradaGarantiaA4: (prazo: string) => string;
  cupom: TextosCupomOS;
  /**
   * Ajuste dos termos por tipo de trabalho, dentro do mesmo segmento.
   *
   * Serigrafia é o único segmento em que uma OS pode ser de coisas diferentes
   * (camisa, sacola plástica, sacola de papel) — e os termos mudam junto: a
   * cláusula de "peças entregues pelo cliente" não existe numa sacola, que a
   * loja produz do zero, e as exclusões de garantia falam de lavagem, que não
   * se aplica a plástico nem a papel.
   *
   * Só sobrescreve o que declarar; o resto do pacote continua valendo. Segmento
   * de formulário único não declara isto e não é afetado.
   */
  porTipoTrabalho?: Record<string, TextosPorTipoTrabalho>;
}

/**
 * Prazo por extenso para a via em papel: "90 (noventa) dias".
 *
 * A via sempre escreveu o número por extenso, do jeito que se escreve prazo em
 * contrato — perder isso ao tornar o prazo configurável seria trocar clareza
 * jurídica por facilidade de código. Valor fora da tabela cai no número puro
 * ("45 dias"), que continua correto, só menos formal.
 */
const POR_EXTENSO: Record<number, string> = {
  15: 'quinze',
  30: 'trinta',
  45: 'quarenta e cinco',
  60: 'sessenta',
  90: 'noventa',
  120: 'cento e vinte',
  180: 'cento e oitenta',
  365: 'trezentos e sessenta e cinco',
};

export function prazoPorExtenso(dias: number): string {
  const extenso = POR_EXTENSO[dias];
  return extenso ? `${dias} (${extenso}) dias` : `${dias} dias`;
}

/** Sobrescritas permitidas por tipo de trabalho. Tudo opcional. */
export interface TextosPorTipoTrabalho {
  objeto?: string;
  objetoPlural?: string;
  garantiaExclusoes?: string;
  condicoesEntrada?: string;
  prazoRetiradaEntradaA4?: (prazo: string) => string;
  prazoRetiradaGarantiaA4?: (prazo: string) => string;
  cupom?: Partial<
    Pick<
      TextosCupomOS,
      | 'objeto'
      | 'garantiaExclusoes'
      | 'condicoesEntrada'
      | 'semReparo'
      | 'cancelamento'
      | 'prazoRetirada'
    >
  >;
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
  // Masculino: "Objetos". Reproduz palavra por palavra o que o template fixo
  // imprimia — este segmento está em produção.
  prazoRetiradaEntradaA4: (prazo) =>
    `Objetos com serviço concluído que não forem retirados no prazo de ${prazo} após notificação `
    + 'serão considerados abandonados e poderão ser destinados para cobrir as despesas do serviço, '
    + 'conforme Art. 1.275 do Código Civil Brasileiro.',
  prazoRetiradaGarantiaA4: (prazo) =>
    `Objetos não retirados no prazo de ${prazo} após notificação de conclusão serão considerados `
    + 'abandonados e poderão ser vendidos para custeio das despesas, conforme Art. 1.275 do Código '
    + 'Civil Brasileiro.',
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
    prazoRetirada: (dias) =>
      `PRAZO DE RETIRADA: Objetos nao retirados em ${dias} dias apos aviso de conclusao serao `
      + 'considerados abandonados, conforme Art. 1.275 do Codigo Civil Brasileiro.',
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
  // Masculino: "Veículos". Verbatim do template fixo — segmento em produção.
  prazoRetiradaEntradaA4: (prazo) =>
    `Veículos com serviço concluído que não forem retirados no prazo de ${prazo} após notificação `
    + 'serão considerados abandonados e poderão ser destinados para cobrir as despesas do serviço, '
    + 'conforme Art. 1.275 do Código Civil Brasileiro.',
  prazoRetiradaGarantiaA4: (prazo) =>
    `Veículos não retirados no prazo de ${prazo} após notificação de conclusão serão considerados `
    + 'abandonados e poderão ser vendidos para custeio das despesas, conforme Art. 1.275 do Código '
    + 'Civil Brasileiro.',
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
    prazoRetirada: (dias) =>
      `PRAZO DE RETIRADA: Veiculos nao retirados em ${dias} dias apos aviso de conclusao serao `
      + 'considerados abandonados, conforme Art. 1.275 do Codigo Civil Brasileiro.',
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
  // FEMININO. É aqui que a frase fixa do template errava: "Peças ... não forem
  // retirados ... considerados abandonados ... destinados".
  prazoRetiradaEntradaA4: (prazo) =>
    `Peças com serviço concluído que não forem retiradas no prazo de ${prazo} após notificação `
    + 'serão consideradas abandonadas e poderão ser destinadas para cobrir as despesas do serviço, '
    + 'conforme Art. 1.275 do Código Civil Brasileiro.',
  prazoRetiradaGarantiaA4: (prazo) =>
    `Peças não retiradas no prazo de ${prazo} após notificação de conclusão serão consideradas `
    + 'abandonadas e poderão ser vendidas para custeio das despesas, conforme Art. 1.275 do Código '
    + 'Civil Brasileiro.',
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
    prazoRetirada: (dias) =>
      `PRAZO DE RETIRADA: Pecas nao retiradas em ${dias} dias apos aviso de conclusao serao `
      + 'consideradas abandonadas, conforme Art. 1.275 do Codigo Civil Brasileiro.',
  },

  // ─── Sacola: a loja PRODUZ, o cliente não entrega peça ─────────────────────
  // O pacote acima é de camisa (peça do cliente, lavagem, ferro). Numa sacola
  // nada disso existe: não há peça entregue para estampar, e ninguém lava uma
  // sacola. Sem esta separação a via saía prometendo e isentando coisas que não
  // têm relação com o trabalho contratado.
  porTipoTrabalho: {
    sacola_plastica: {
      objeto: 'sacola',
      objetoPlural: 'Sacolas',
      prazoRetiradaEntradaA4: (prazo) =>
        `Sacolas com serviço concluído que não forem retiradas no prazo de ${prazo} após `
        + 'notificação serão consideradas abandonadas e poderão ser destinadas para cobrir as '
        + 'despesas do serviço, conforme Art. 1.275 do Código Civil Brasileiro.',
      prazoRetiradaGarantiaA4: (prazo) =>
        `Sacolas não retiradas no prazo de ${prazo} após notificação de conclusão serão `
        + 'consideradas abandonadas e poderão ser vendidas para custeio das despesas, conforme '
        + 'Art. 1.275 do Código Civil Brasileiro.',
      garantiaExclusoes:
        'uso de carga acima da capacidade da sacola, contato com objetos cortantes, exposição '
        + 'prolongada ao sol ou ao calor, e desgaste natural pelo uso.',
      condicoesEntrada:
        'O cliente declara ter conferido e aprovado a arte, as cores, a posição da impressão, as '
        + 'referências e as quantidades antes da produção. Por se tratar de produção sob encomenda, '
        + 'pequenas variações de tonalidade e de medida são inerentes ao processo de impressão.',
      cupom: {
        objeto: 'Sacola',
        garantiaExclusoes:
          'carga acima da capacidade, objetos cortantes, calor ou desgaste natural pelo uso.',
        condicoesEntrada:
          'Cliente declara ter aprovado arte, cores, posicao, referencias e quantidades antes da '
          + 'producao. Pequenas variacoes de tonalidade e medida sao inerentes ao processo.',
        semReparo: 'Producao nao realizada. Sem garantia aplicavel a esta OS.',
        cancelamento:
          'A OS acima foi cancelada nesta data, com producao nao iniciada ou parcial, isentando a '
          + 'empresa de garantias sobre servicos nao concluidos.',
        // Sem esta linha a bobina herdaria a da camisa e diria "Pecas nao
        // retiradas" numa OS de sacola.
        prazoRetirada: (dias) =>
          `PRAZO DE RETIRADA: Sacolas nao retiradas em ${dias} dias apos aviso de conclusao serao `
          + 'consideradas abandonadas, conforme Art. 1.275 do Codigo Civil Brasileiro.',
      },
    },
    sacola_papel: {
      objeto: 'sacola',
      objetoPlural: 'Sacolas',
      prazoRetiradaEntradaA4: (prazo) =>
        `Sacolas com serviço concluído que não forem retiradas no prazo de ${prazo} após `
        + 'notificação serão consideradas abandonadas e poderão ser destinadas para cobrir as '
        + 'despesas do serviço, conforme Art. 1.275 do Código Civil Brasileiro.',
      prazoRetiradaGarantiaA4: (prazo) =>
        `Sacolas não retiradas no prazo de ${prazo} após notificação de conclusão serão `
        + 'consideradas abandonadas e poderão ser vendidas para custeio das despesas, conforme '
        + 'Art. 1.275 do Código Civil Brasileiro.',
      garantiaExclusoes:
        'contato com água ou umidade, uso de carga acima da capacidade da sacola, contato com '
        + 'objetos cortantes e desgaste natural pelo uso.',
      condicoesEntrada:
        'O cliente declara ter conferido e aprovado a arte, as cores, a posição da impressão, as '
        + 'referências e as quantidades antes da produção. Por se tratar de produção sob encomenda, '
        + 'pequenas variações de tonalidade e de medida são inerentes ao processo de impressão.',
      cupom: {
        objeto: 'Sacola',
        garantiaExclusoes:
          'agua ou umidade, carga acima da capacidade, objetos cortantes ou desgaste natural.',
        condicoesEntrada:
          'Cliente declara ter aprovado arte, cores, posicao, referencias e quantidades antes da '
          + 'producao. Pequenas variacoes de tonalidade e medida sao inerentes ao processo.',
        semReparo: 'Producao nao realizada. Sem garantia aplicavel a esta OS.',
        cancelamento:
          'A OS acima foi cancelada nesta data, com producao nao iniciada ou parcial, isentando a '
          + 'empresa de garantias sobre servicos nao concluidos.',
        // Sem esta linha a bobina herdaria a da camisa e diria "Pecas nao
        // retiradas" numa OS de sacola.
        prazoRetirada: (dias) =>
          `PRAZO DE RETIRADA: Sacolas nao retiradas em ${dias} dias apos aviso de conclusao serao `
          + 'consideradas abandonadas, conforme Art. 1.275 do Codigo Civil Brasileiro.',
      },
    },
  },
};

const PACOTES: Record<string, TextosImpressaoOS> = {
  oficina_mecanica: OFICINA_MECANICA,
  assistencia_tecnica: ASSISTENCIA_TECNICA,
  serigrafia: SERIGRAFIA,
};

const PADRAO = ASSISTENCIA_TECNICA;

/**
 * Aplica a sobrescrita do tipo de trabalho sobre o pacote do segmento.
 *
 * Mescla rasa, com `cupom` tratado à parte: um spread simples trocaria o objeto
 * `cupom` inteiro pelo parcial, e a via em bobina perderia identificador,
 * defeito, assinatura e prazo de retirada de uma vez.
 */
function aplicarTipoTrabalho(
  pacote: TextosImpressaoOS,
  tipo: string | null | undefined,
): TextosImpressaoOS {
  const override = tipo ? pacote.porTipoTrabalho?.[tipo] : undefined;
  if (!override) return pacote;

  const { cupom: cupomOverride, ...raiz } = override;
  return {
    ...pacote,
    ...raiz,
    cupom: { ...pacote.cupom, ...(cupomOverride ?? {}) },
  };
}

/**
 * @param tipoTrabalho Tipo de trabalho da OS (`dados_adicionais.tipo_trabalho`).
 *   Omitido = pacote do segmento sem ajuste, que é o comportamento de todo
 *   segmento de formulário único.
 */
export function useTextosImpressaoOS(
  tipoTrabalho?: MaybeRefOrGetter<string | null | undefined>,
) {
  const { segmento } = useSegmento();
  const { labelIdentificador } = useObjetoLabels();

  const textos = computed<TextosImpressaoOS>(() =>
    aplicarTipoTrabalho(
      PACOTES[segmento.value ?? ''] ?? PADRAO,
      toValue(tipoTrabalho),
    ),
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
