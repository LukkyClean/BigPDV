// ---------------------------------------------------------------------------
// Contrato de definição de campos por segmento (metadados vindos do backend).
// Fonte: GET /ordens-servico/definicao-campos (app/core/segmentos.py).
//
// O frontend renderiza os campos/vistoria a partir deste contrato, permitindo
// que novos segmentos (ex: oficina_moto) funcionem sem alterar o frontend.
// ---------------------------------------------------------------------------

/**
 * Tipo de widget de um campo dinâmico.
 *
 * Espelha TIPOS_DE_CAMPO_SUPORTADOS (app/core/segmentos/campos.py). O
 * renderizador faz `switch` exaustivo sobre esta união: acrescentar um tipo
 * aqui sem desenhá-lo lá **não compila**. É de propósito — é o que impede um
 * segmento novo de declarar campo que ninguém sabe mostrar.
 */
/**
 * `lista` é um campo REPETÍVEL de texto: o valor gravado é `string[]`, não uma
 * string. Todos os outros tipos guardam um valor único.
 */
export type SegmentFieldType = 'texto' | 'numero' | 'inteiro' | 'opcao' | 'booleano' | 'lista';

/** Onde o campo é persistido: no objeto (veículo) ou na OS (check-in). */
export type SegmentFieldScope = 'objeto' | 'os';

/** Quanto o campo ocupa na grade de 2 colunas. */
export type SegmentFieldWidth = 'meia' | 'inteira';

/**
 * Como o valor é persistido.
 *
 * `coluna` = coluna real da tabela (marca, modelo, cor, numero_serie).
 * `dados_adicionais` = chave no JSON — o caso de todo campo de segmento novo.
 *
 * Existe porque o projeto mistura os dois, e um renderizador que não saiba a
 * diferença grava no lugar errado.
 */
export type SegmentFieldOrigin = 'coluna' | 'dados_adicionais';

/** Descrição de um campo dinâmico do segmento. */
export interface SegmentField {
  nome: string;
  label: string;
  tipo: SegmentFieldType;
  obrigatorio: boolean;
  escopo: SegmentFieldScope;
  /** Presente quando `tipo === 'opcao'`. */
  opcoes?: string[];
  /** Cabeçalho da seção em que o campo aparece. `null` = sem seção. */
  grupo?: string | null;
  largura?: SegmentFieldWidth;
  origem?: SegmentFieldOrigin;
  /** Nome da coluna real, quando difere de `nome` (ex: placa → numero_serie). */
  coluna?: string;
}

/** Campo identificador principal do objeto (ex: placa mapeada em numero_serie). */
export interface SegmentIdentifier {
  nome: string;
  label: string;
  /** Regex de validação (ex: placa). `null` quando não há. */
  regex: string | null;
  /**
   * `true` quando o SISTEMA cria o identificador e o formulário não o pergunta.
   *
   * Placa e nº de série existem no mundo — estão escritos no bem, e o atendente
   * só copia. Código de arte não existe até alguém inventar, e campo
   * obrigatório que o usuário não tem como preencher vira lixo ("1", "teste").
   */
  gerado?: boolean;
  /** Prefixo do identificador gerado (ex: "ART" → "ART-0042"). */
  prefixo?: string;
}

/** Grupo da vistoria de inspeção; cada item é avaliado por um dos `estados`. */
export interface SegmentInspectionGroup {
  titulo: string;
  estados: string[];
  itens: string[];
}

/**
 * O que o segmento FAZ (em oposição a quais campos ele tem).
 * Fonte: CAPACIDADES_CONHECIDAS em app/core/segmentos.py.
 *
 * A UI pergunta pela capacidade, não pelo segmento — assim um segmento novo
 * liga a funcionalidade no registry do backend, sem alterar o frontend.
 */
export type SegmentCapability =
  | 'vistoria'
  | 'revisoes'
  | 'aprovacao_itens'
  | 'garantia_itens'
  /**
   * O negócio DIAGNOSTICA antes de executar: recebe algo com problema,
   * investiga e emite laudo. Sem isto, a aba deixa de pedir laudo técnico e
   * serve só para as imagens.
   */
  | 'diagnostico'
  /**
   * A imagem faz parte do PEDIDO, não do laudo.
   *
   * Em oficina e informática a foto é prova do estado do bem: nasce depois, com
   * o aparelho na bancada, e por isso a aba só existe na OS já salva. Em
   * serigrafia a imagem É a arte a ser estampada — sem ela não há o que
   * produzir. Liberar a aba na criação e imprimir as imagens na via de ENTRADA.
   */
  | 'imagem_na_entrada'
  /**
   * O serviço tem garantia contada em PRAZO (dias/meses), escolhida ao
   * finalizar. Faz sentido onde se conserta — o reparo responde por um período.
   *
   * Numa serigrafia a estampa não tem prazo: se dura, mede-se em lavagens.
   * Desligada, o campo some da finalização e o Termo de Garantia só é impresso
   * quando houver prazo de fato.
   */
  | 'garantia_prazo';

/**
 * Um processo de negócio dentro do mesmo segmento.
 *
 * Oficina e informática têm um só (toda OS é sobre um veículo / um
 * equipamento). Serigrafia é o primeiro segmento em que a OS pode ser de
 * coisas diferentes — camisa ou sacola —, cada uma com seus campos.
 *
 * Segmento que não declara `tipos` continua exatamente como sempre foi.
 */
export interface SegmentWorkType {
  id: string;
  label: string;
  campos: SegmentField[];
}

/** Definição completa dos campos de um segmento com regras dedicadas. */
export interface SegmentDefinition {
  segmento: string;
  rotulo_objeto_singular: string;
  rotulo_objeto_plural: string;
  /**
   * Rótulo do texto livre que o cliente relata. Ausente = "Defeito Relatado".
   *
   * O campo nasceu do modelo de CONSERTO ("o que quebrou"). Num segmento de
   * produção não há defeito — o cliente encomenda. O campo continua útil (é o
   * "o que ele pediu", e sai impresso), mas com o nome certo.
   */
  rotulo_defeito?: string;
  placeholder_defeito?: string;
  /**
   * Quem executa o serviço, na tela e nas vias. Ausente = "Técnico".
   *
   * "Técnico" pressupõe conserto. Num segmento de produção quem toca o pedido
   * é o responsável por ele.
   */
  rotulo_responsavel?: string;
  /**
   * Título da seção de desfecho na finalização. Ausente = "Situação do " + rótulo
   * do objeto, que é o que oficina e informática mostram hoje.
   *
   * Vem inteiro, e não montado, porque português tem gênero: a montagem exibia
   * "SITUAÇÃO DO ARTE".
   */
  rotulo_situacao?: string;
  /**
   * Rótulo de cada valor do desfecho, por chave do enum
   * (`REPARADO` | `SEM_REPARO` | `CONDENADO`). Ausente = o rótulo de conserto.
   *
   * O enum NÃO muda: ele carrega a regra de dispensar o pagamento integral
   * (SEM_REPARO/CONDENADO) e alimenta filtro, relatório e histórico. Só as
   * palavras mudam — "Reparado" não descreve nada numa produção.
   */
  rotulos_situacao?: Record<string, string>;
  identificador: SegmentIdentifier;
  /** O que o segmento faz. Vazio = só o fluxo genérico de OS. */
  capacidades: SegmentCapability[];
  veiculo: SegmentField[];
  checkin: SegmentField[];
  acessorios: string[];
  vistoria: SegmentInspectionGroup[];
  /**
   * Ausente/vazio = formulário único (o caso de oficina e informática).
   * Presente = a OS pergunta o tipo antes de mostrar os campos.
   */
  tipos?: SegmentWorkType[];
}

/** Resposta do endpoint de definição de campos. */
export interface SegmentDefinitionResponse {
  segmento: string | null;
  tem_definicao: boolean;
  /**
   * `null` só para segmentos sem definição dedicada (ex: mercado, marcenaria).
   * Oficina e assistência técnica TÊM definição — ambas estão em DEFINICOES
   * (app/core/segmentos.py).
   */
  definicao: SegmentDefinition | null;
}
