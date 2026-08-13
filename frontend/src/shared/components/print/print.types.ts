/** Classe do dispositivo: folha ou bobina. Decidida pela MÁQUINA (que impressora tem). */
export type PrintFormat = 'A4' | 'CUPOM';

/**
 * Quanto papel a via ocupa dentro da classe folha. Decidido pela EMPRESA/segmento.
 *
 * `A4` é a folha inteira. `A5` é MEIA FOLHA — e é meia folha de A4, não papel
 * A5: a impressora continua recebendo uma A4 e o comprovante fica na metade de
 * cima, com linha de corte. O nome ficou 'A5' porque é o valor já gravado em
 * `configuracoes_os` nas lojas, e trocá-lo custaria migração para nada: o
 * lojista sempre viu isso escrito como "meia folha" na tela.
 */
export type TamanhoFolha = 'A4' | 'A5';

/** Largura da bobina dentro da classe cupom. */
export type LarguraBobina = '58' | '80';

/**
 * Densidade do layout: a MESMA informação ocupando mais ou menos papel.
 *
 * Não confundir com "menos conteúdo" — o conteúdo do comprovante é invariante
 * (dados da empresa, do cliente com endereço, itens discriminados e resumo de
 * pagamento saem sempre, por proteção do cliente). O que muda é a forma:
 * `normal` usa cards com moldura e respiro; `compacto` usa linha corrida.
 * Ver `backend-fastapi/docs/comprovantes-perfil-plano.md` §4.
 */
export type DensidadeComprovante = 'normal' | 'compacto';

export interface CompanyPrintInfo {
  nome: string;
  razaoSocial: string;
  cnpj: string;
  documento?: string;
  labelDocumento?: string;
  endereco: string;
  enderecoLinha1: string;
  enderecoLinha2: string;
  contato: string;
  email: string;
  logo: string | null;
  /** Cidade sozinha — o BR Code do PIX exige o campo separado do endereço. */
  cidade?: string;
  /** Chave PIX do recebedor, para montar o QR do comprovante. */
  chavePix?: string | null;
  pixAtivo?: boolean;
}
