export type PrintFormat = 'A4' | 'CUPOM';

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
