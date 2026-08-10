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
export type SegmentFieldType = 'texto' | 'numero' | 'inteiro' | 'opcao' | 'booleano';

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
   * Cliente vê o mockup pelo QR e libera a produção. NÃO se confunde com
   * `aprovacao_itens`: aquela é sobre PREÇO (aprovar linha do orçamento), esta
   * é sobre a ARTE (a estampa está certa? pode gravar a tela?).
   */
  | 'aprovacao_arte';

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
