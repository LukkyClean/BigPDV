/**
 * @fileoverview Perfil de apresentação dos comprovantes (OS e Venda).
 *
 * FONTE ÚNICA de como o comprovante se APRESENTA. O que ele CONTÉM não passa
 * por aqui e não é configurável: dados da empresa, dados do cliente com
 * endereço, itens discriminados e resumo exato do pagamento saem sempre, em
 * qualquer empresa e qualquer segmento, porque protegem o cliente.
 * Ver `backend-fastapi/docs/comprovantes-perfil-plano.md` §4.
 *
 * ORIGEM: `configuracoes_os` (banco, por empresa), via `configuracoesStore` — que
 * já carrega a config no boot. Fica na empresa, e não no `localStorage`, porque a
 * mesma OS impressa no balcão e na oficina tem que sair igual; a máquina decide
 * só ONDE imprime.
 *
 * Quando a config não chegou (store ainda carregando, ou falha de rede) cai no
 * PERFIL_PADRAO, que reproduz a saída de sempre. Comprovante não é lugar de
 * esperar: melhor sair no formato antigo que não sair.
 */

import { computed } from 'vue';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import type {
  DensidadeComprovante,
  LarguraBobina,
  TamanhoFolha,
} from '@/shared/components/print/print.types';

export interface PerfilComprovante {
  /** Tamanho do papel quando a via sai em folha. */
  folha: TamanhoFolha;
  /** Densidade do layout: mesma informação, mais ou menos papel. */
  densidade: DensidadeComprovante;
}

/** Padrão que reproduz a saída de hoje — não mudar sem decidir a migração. */
export const PERFIL_PADRAO: PerfilComprovante = {
  folha: 'A4',
  densidade: 'normal',
};

export type DocumentoComprovante = 'os_entrada' | 'os_entrega' | 'venda_recibo';

export function usePerfilComprovante(documento: DocumentoComprovante = 'os_entrega') {
  const impressaoStore = useImpressaoStore();
  const configuracoesStore = useConfiguracoesStore();

  /**
   * Perfil de um documento específico. Existe como função, e não só como
   * computed do `documento` fixo, porque o fluxo de impressão só descobre qual
   * documento está imprimindo na hora do clique — antes disso o mesmo
   * composable serve entrada e entrega.
   */
  function perfilDe(doc: DocumentoComprovante): PerfilComprovante {
    const os = configuracoesStore.configOS;
    if (!os) return { ...PERFIL_PADRAO };

    // A via de entrada e a de entrega têm conteúdos quase disjuntos, e a loja
    // costuma querer a entrada enxuta (protocolo) e a entrega completa.
    if (doc === 'os_entrada') {
      return {
        folha: (os.comprovante_entrada_folha ?? PERFIL_PADRAO.folha) as TamanhoFolha,
        densidade: (os.comprovante_entrada_densidade ?? PERFIL_PADRAO.densidade) as DensidadeComprovante,
      };
    }
    // `venda_recibo` ainda não tem colunas próprias (Fase 6 do plano): segue a
    // entrega, que é o documento com pagamento — melhor que divergir sem motivo.
    return {
      folha: (os.comprovante_entrega_folha ?? PERFIL_PADRAO.folha) as TamanhoFolha,
      densidade: (os.comprovante_entrega_densidade ?? PERFIL_PADRAO.densidade) as DensidadeComprovante,
    };
  }

  /**
   * Opções de papel para `imprimirComPagina`. A folha vem do perfil (empresa);
   * a bobina vem da MÁQUINA, que é quem sabe qual impressora tem.
   */
  function opcoesPaginaDe(doc: DocumentoComprovante) {
    return {
      folha: perfilDe(doc).folha,
      bobina: impressaoStore.config.bobina as LarguraBobina,
    };
  }

  const perfil = computed<PerfilComprovante>(() => perfilDe(documento));

  /** Classe de densidade para o container de impressão. '' quando normal. */
  const classeDensidade = computed(() =>
    perfil.value.densidade === 'compacto' ? 'compacto' : '',
  );

  return { perfil, perfilDe, classeDensidade, opcoesPaginaDe };
}
