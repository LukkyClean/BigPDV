export interface OsNotaFiscalUpdate {
  natureza_operacao?: string | null;
  /** 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno */
  finalidade_emissao?: number | null;
  consumidor_final?: boolean | null;
  /** 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domiciliar, 9=Outros */
  indicador_presenca?: number | null;
  emitir_nfe?: boolean | null;
  emitir_nfse?: boolean | null;
}

export interface OsNotaFiscalRead extends OsNotaFiscalUpdate {
  id: number;
  os_id: number;

  // Resultado NFe/NFCe (peças)
  status_nfe?: string | null;
  chave_acesso_nfe?: string | null;
  numero_nfe?: number | null;
  serie_nfe?: number | null;
  protocolo_nfe?: string | null;
  data_autorizacao_nfe?: string | null;
  url_danfe?: string | null;
  mensagem_nfe?: string | null;
  qrcode_nfe?: string | null;

  // Resultado NFSe (mão de obra)
  status_nfse?: string | null;
  numero_nfse?: string | null;
  codigo_verificacao_nfse?: string | null;
  data_emissao_nfse?: string | null;
  url_nfse?: string | null;
  mensagem_nfse?: string | null;

  data_atualizacao: string;
}
