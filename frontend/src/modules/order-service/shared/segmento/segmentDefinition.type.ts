// ---------------------------------------------------------------------------
// Contrato de definição de campos por segmento (metadados vindos do backend).
// Fonte: GET /ordens-servico/definicao-campos (app/core/segmentos.py).
//
// O frontend renderiza os campos/vistoria a partir deste contrato, permitindo
// que novos segmentos (ex: oficina_moto) funcionem sem alterar o frontend.
// ---------------------------------------------------------------------------

/** Tipo de widget de um campo dinâmico. */
export type SegmentFieldType = 'texto' | 'numero' | 'inteiro' | 'opcao' | 'booleano';

/** Onde o campo é persistido: no objeto (veículo) ou na OS (check-in). */
export type SegmentFieldScope = 'objeto' | 'os';

/** Descrição de um campo dinâmico do segmento. */
export interface SegmentField {
  nome: string;
  label: string;
  tipo: SegmentFieldType;
  obrigatorio: boolean;
  escopo: SegmentFieldScope;
  /** Presente quando `tipo === 'opcao'`. */
  opcoes?: string[];
}

/** Campo identificador principal do objeto (ex: placa mapeada em numero_serie). */
export interface SegmentIdentifier {
  nome: string;
  label: string;
  /** Regex de validação (ex: placa). `null` quando não há. */
  regex: string | null;
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
  | 'garantia_itens';

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
