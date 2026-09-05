/**
 * @fileoverview Regras PURAS sobre itens de OS — sem Vue, sem estado.
 *
 * Moram fora do composable para poderem ser executadas isoladamente. O módulo
 * de OS é compartilhado pelos três segmentos em produção (informática, oficina
 * mecânica e serigrafia), e mudança em código compartilhado precisa de prova
 * MEDIDA, não deduzida — ver `scripts/` e a verificação do caso de 2,5 kg da
 * serigrafia.
 */
import type {
  OsItemCreateSchemaDataType,
  OsItemReadSchemaDataType,
} from '../../ordens/schemas/relationship/osItem.schema';

/**
 * O vínculo com o catálogo tem dois nomes conforme a origem do item: `item_id`
 * enquanto a OS está sendo criada (payload de escrita) e `produto_id`/`servico_id`
 * depois de salva (resposta de leitura). É o mesmo dado — o backend converte um
 * no outro. Sem esta ponte, editar um item de OS salva perderia o vínculo na tela.
 */
export function vinculoCatalogo(
  item: OsItemCreateSchemaDataType | OsItemReadSchemaDataType,
): number | undefined {
  const i = item as Partial<OsItemCreateSchemaDataType & OsItemReadSchemaDataType>;
  return i.item_id ?? i.produto_id ?? i.servico_id ?? undefined;
}

type QualquerItem = OsItemCreateSchemaDataType | OsItemReadSchemaDataType;

/**
 * Duas linhas são A MESMA COISA, e por isso podem virar uma com o dobro da
 * quantidade?
 *
 * O defeito que isto conserta: lançar a mesma tinta duas vezes criava duas
 * linhas iguais na OS em vez de somar a quantidade.
 *
 * A REGRA É ESTREITA DE PROPÓSITO. Mesclar é destrutivo — junta dois registros
 * e não tem volta —, então só acontece quando TUDO que distingue uma linha da
 * outra é igual. Cada comparação abaixo evita um estrago concreto:
 *
 *   valor_unitario   duas linhas do mesmo produto com preços diferentes são
 *                    legítimas (uma com desconto combinado). Somar apagaria o
 *                    preço de uma delas.
 *   custo_unitario   lotes de compra diferentes têm custos diferentes, e o CMV
 *                    do mês sai do custo de cada linha.
 *   status_aprovacao um item APROVADO e outro PENDENTE não se juntam: mesclar
 *                    aprovaria em silêncio o que o cliente ainda não aprovou.
 *   garantia         90 dias e 30 dias não viram uma coisa só.
 *   visivel_cliente  peça embutida vale ZERO e não sai na via; juntá-la com uma
 *                    cobrada mudaria o total impresso.
 *
 * SEM VÍNCULO DE CATÁLOGO cai no nome (item digitado à mão, que é como a
 * oficina lança quase tudo). Comparação sem acento não entra aqui: "Tinta" e
 * "tinta" são a mesma peça, mas "Tinta preta" e "Tinta Preta 500ml" não são, e
 * qualquer folga na comparação junta coisa diferente.
 */
export function mesmaLinha(a: QualquerItem, b: QualquerItem): boolean {
  const A = a as Partial<OsItemCreateSchemaDataType & OsItemReadSchemaDataType>;
  const B = b as Partial<OsItemCreateSchemaDataType & OsItemReadSchemaDataType>;

  if (A.tipo !== B.tipo) return false;
  if (A.unidade_medida !== B.unidade_medida) return false;
  if ((A.valor_unitario ?? 0) !== (B.valor_unitario ?? 0)) return false;
  if ((A.custo_unitario ?? 0) !== (B.custo_unitario ?? 0)) return false;
  if ((A.status_aprovacao ?? 'APROVADO') !== (B.status_aprovacao ?? 'APROVADO')) return false;
  if ((A.garantia_dias ?? null) !== (B.garantia_dias ?? null)) return false;
  if ((A.garantia_km ?? null) !== (B.garantia_km ?? null)) return false;
  if ((A.visivel_cliente ?? true) !== (B.visivel_cliente ?? true)) return false;

  const vinculoA = vinculoCatalogo(a);
  const vinculoB = vinculoCatalogo(b);
  if (vinculoA != null || vinculoB != null) return vinculoA === vinculoB;

  return (A.nome ?? '').trim().toLowerCase() === (B.nome ?? '').trim().toLowerCase();
}

/**
 * Soma as quantidades sem herdar lixo de ponto flutuante.
 *
 * A serigrafia vende por quilo quebrado (2,5 kg), então isto é `Float` de
 * verdade: sem o arredondamento, 0,1 + 0,2 vira 0,30000000000000004 e a tela
 * mostra isso. Três casas é a mesma precisão que a lista já usa para exibir.
 */
export function somarQuantidade(a: number, b: number): number {
  return Math.round(((a || 0) + (b || 0)) * 1000) / 1000;
}
