import type { DocumentoFiscalRead } from '../types/fiscal.types';
import { formatDataHora } from '@/shared/utils/date.utils';

export type DiagnosticCategory =
  | 'CONFIGURACAO'
  | 'CLIENTE'
  | 'PRODUTO'
  | 'TRIBUTACAO'
  | 'SEFAZ_INDISPONIVEL'
  | 'DUPLICIDADE'
  | 'GENERICO';

export type ActionType =
  | 'CONFIG_FISCAL'
  | 'EDITAR_VENDA'
  | 'RESOLVER_PRODUTOS'
  | 'REEMITIR'
  | 'RECONSULTAR';

export interface FiscalDiagnostic {
  categoria: DiagnosticCategory;
  cStat?: number | null;
  badge: {
    label: string;
    bg: string;
    text: string;
    border: string;
  };
  titulo: string;
  explicacao: string;
  comoResolver: string;
  acaoPrincipal?: {
    tipo: ActionType;
    label: string;
  };
}

export function analisarDiagnosticoFiscal(documento: DocumentoFiscalRead | null | undefined): FiscalDiagnostic {
  if (!documento) {
    return {
      categoria: 'GENERICO',
      badge: { label: 'Indisponível', bg: 'bg-zinc-100', text: 'text-zinc-700', border: 'border-zinc-200' },
      titulo: 'Documento Não Carregado',
      explicacao: 'Nenhum detalhe disponível para este documento.',
      comoResolver: 'Tente recarregar a tela.',
    };
  }

  const cStat = documento.codigo_status_sefaz;
  const msg = (documento.mensagem_sefaz || '').toLowerCase();
  const motivo = (documento.motivo_rejeicao || '').toLowerCase();
  const textoCompleto = `${msg} ${motivo}`;

  // 1. Configuração Fiscal Interna / Certificado
  if (
    textoCompleto.includes('configuração fiscal') ||
    textoCompleto.includes('certificado') ||
    textoCompleto.includes('emitente') ||
    textoCompleto.includes('empresa não possui')
  ) {
    return {
      categoria: 'CONFIGURACAO',
      cStat,
      badge: { label: 'Configuração Pendente', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
      titulo: 'Configuração Fiscal da Empresa Incompleta',
      explicacao:
        documento.mensagem_sefaz ||
        'A empresa não possui parâmetros fiscais ativos ou certificado digital configurado para este ambiente.',
      comoResolver: 'Acesse as Configurações Fiscais da empresa e cadastre o certificado e séries fiscais.',
      acaoPrincipal: {
        tipo: 'CONFIG_FISCAL',
        label: 'Abrir Configuração Fiscal',
      },
    };
  }

  // 2. Erros de Inscrição Estadual e Cliente (cStat 232, 233, 234, 696, 778)
  if (
    cStat === 696 ||
    cStat === 234 ||
    cStat === 232 ||
    cStat === 233 ||
    cStat === 778 ||
    textoCompleto.includes('inscrição estadual') ||
    textoCompleto.includes('destinatário não vinculada') ||
    textoCompleto.includes('indicador de ie')
  ) {
    return {
      categoria: 'CLIENTE',
      cStat: cStat || 696,
      badge: { label: `cStat ${cStat || 696} · IE Destinatário`, bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
      titulo: 'Inscrição Estadual do Cliente Inconsistente',
      explicacao:
        'A SEFAZ rejeitou porque o cliente está classificado com Inscrição Estadual não vinculada ao CNPJ ou não cadastrada na UF de destino.',
      comoResolver:
        'Abra a edição da venda, marque o cliente como "Consumidor Não Contribuinte / Isento" ou preencha a IE correta e reemita a nota.',
      acaoPrincipal: {
        tipo: 'EDITAR_VENDA',
        label: 'Editar Cliente da Venda',
      },
    };
  }

  // 3. CPF ou CNPJ do Destinatário Inválido (cStat 207, 208, 209)
  if (
    cStat === 207 ||
    cStat === 208 ||
    cStat === 209 ||
    textoCompleto.includes('cpf do destinatário') ||
    textoCompleto.includes('cnpj do destinatário') ||
    textoCompleto.includes('dígito verificador')
  ) {
    return {
      categoria: 'CLIENTE',
      cStat: cStat || 208,
      badge: { label: `cStat ${cStat || 208} · CPF/CNPJ`, bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
      titulo: 'Documento (CPF/CNPJ) do Cliente Inválido',
      explicacao: 'O número do CPF ou CNPJ informado para o destinatário é inválido perante a Receita Federal.',
      comoResolver: 'Edite os dados da venda vinculando o cliente com CPF ou CNPJ válido.',
      acaoPrincipal: {
        tipo: 'EDITAR_VENDA',
        label: 'Corrigir Cliente da Venda',
      },
    };
  }

  // 4. Produto sem NCM ou NCM Inválido (cStat 703, 777)
  if (
    cStat === 703 ||
    cStat === 777 ||
    textoCompleto.includes('ncm') ||
    textoCompleto.includes('nomenclatura comum')
  ) {
    return {
      categoria: 'PRODUTO',
      cStat: cStat || 703,
      badge: { label: `cStat ${cStat || 703} · NCM Inválido`, bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
      titulo: 'Código NCM do Produto Inexistente ou Incorreto',
      explicacao: 'Um ou mais produtos vinculados à nota possuem NCM fora da tabela vigente da Receita Federal ou em branco.',
      comoResolver: 'Acesse o cadastro de produtos ou o painel de pendências fiscais para informar o NCM válido de 8 dígitos.',
      acaoPrincipal: {
        tipo: 'RESOLVER_PRODUTOS',
        label: 'Resolver Pendências de Produtos',
      },
    };
  }

  // 5. Inconsistência de Regra Fiscal e CSOSN (cStat 508, 528)
  if (
    cStat === 508 ||
    cStat === 528 ||
    cStat === 539 ||
    textoCompleto.includes('csosn') ||
    textoCompleto.includes('cfop') ||
    textoCompleto.includes('alíquota')
  ) {
    return {
      categoria: 'TRIBUTACAO',
      cStat: cStat || 508,
      badge: { label: `cStat ${cStat || 508} · Regra Fiscal`, bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
      titulo: 'Incompatibilidade de Tributação (CSOSN / CFOP)',
      explicacao: 'A regra fiscal (CSOSN/CST) não é compatível com o CFOP de operação ou regime tributário da empresa.',
      comoResolver: 'Verifique a configuração fiscal do produto e ajuste o CSOSN (ex: 102 para tributação integral ou 500 para ST).',
      acaoPrincipal: {
        tipo: 'RESOLVER_PRODUTOS',
        label: 'Ajustar Dados do Produto',
      },
    };
  }

  // 6. Duplicidade de Nota (cStat 204)
  if (cStat === 204 || textoCompleto.includes('duplicidade')) {
    return {
      categoria: 'DUPLICIDADE',
      cStat: 204,
      badge: { label: 'cStat 204 · Duplicidade', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
      titulo: 'Número de NF-e Já Utilizado',
      explicacao: 'Esta numeração e série de nota já foram autorizadas anteriormente na base de dados da SEFAZ.',
      comoResolver: 'Consulte o status do documento ou faça a reemissão para gerar a próxima numeração sequencial.',
      acaoPrincipal: {
        tipo: 'RECONSULTAR',
        label: 'Consultar Status na SEFAZ',
      },
    };
  }

  // 7. Instabilidade ou SEFAZ Offline (cStat 108, 109, 502)
  if (
    cStat === 108 ||
    cStat === 109 ||
    cStat === 502 ||
    textoCompleto.includes('paralisado') ||
    textoCompleto.includes('timeout') ||
    textoCompleto.includes('comunicação') ||
    textoCompleto.includes('bad gateway')
  ) {
    return {
      categoria: 'SEFAZ_INDISPONIVEL',
      cStat: cStat || 108,
      badge: { label: 'SEFAZ Temporariamente Instável', bg: 'bg-zinc-100', text: 'text-zinc-700', border: 'border-zinc-200' },
      titulo: 'Servidores da SEFAZ Temporariamente Indisponíveis',
      explicacao: 'Os servidores da Secretaria da Fazenda estão enfrentando oscilações ou lentidão no momento.',
      comoResolver: 'Aguarde alguns minutos e tente reemitir ou consultar o status novamente.',
      acaoPrincipal: {
        tipo: 'RECONSULTAR',
        label: 'Tentar Novamente',
      },
    };
  }

  // 8. Genérico / Outros Códigos SEFAZ
  return {
    categoria: 'GENERICO',
    cStat,
    badge: {
      label: cStat ? `cStat ${cStat}` : 'Rejeição SEFAZ',
      bg: 'bg-rose-50',
      text: 'text-rose-700',
      border: 'border-rose-200',
    },
    titulo: cStat ? `Rejeição SEFAZ (Código ${cStat})` : 'Rejeição na Emissão Fiscal',
    explicacao: documento.mensagem_sefaz || documento.motivo_rejeicao || 'A SEFAZ rejeitou o lote de emissão deste documento.',
    comoResolver: 'Revise os dados da venda, destinatário e tributação dos produtos antes de tentar uma nova emissão.',
    acaoPrincipal: {
      tipo: 'EDITAR_VENDA',
      label: 'Editar Dados da Venda',
    },
  };
}

export function formatarDiagnosticoParaSuporte(documento: DocumentoFiscalRead | null | undefined): string {
  if (!documento) return '';
  const diag = analisarDiagnosticoFiscal(documento);
  const dataFormatada = formatDataHora(documento.data_criacao);

  return [
    '========================================',
    '       DIAGNÓSTICO FISCAL - STARTBIG     ',
    '========================================',
    `Documento ID: ${documento.id}`,
    `Número / Série: Nº ${documento.numero_documento ?? '-'} · Série ${documento.serie ?? '-'}`,
    `Ambiente: ${documento.ambiente_emissao === 1 ? 'Produção' : 'Homologação'}`,
    `Status: ${documento.status}`,
    `Código SEFAZ (cStat): ${documento.codigo_status_sefaz ?? 'N/A'}`,
    `Origem: ${documento.origem_tipo} #${documento.origem_id ?? documento.venda_id ?? '-'}`,
    `Destinatário: ${documento.destinatario_nome ?? 'Consumidor Final'} (${documento.destinatario_documento ?? 'Sem doc'})`,
    `Data do Evento: ${dataFormatada}`,
    '----------------------------------------',
    `Diagnóstico: ${diag.titulo}`,
    `Mensagem SEFAZ: ${documento.mensagem_sefaz || 'Sem mensagem detalhada'}`,
    `Recomendação: ${diag.comoResolver}`,
    '========================================',
  ].join('\n');
}
