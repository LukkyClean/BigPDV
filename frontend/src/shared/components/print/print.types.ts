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
}
