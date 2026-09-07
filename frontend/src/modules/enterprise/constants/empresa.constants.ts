/**
 * @fileoverview Constantes do módulo Enterprise
 * @description Labels, opções de select, ícones e configurações padrão
 */

import {
  Building2,
  MapPin,
  Landmark,
  Settings,
  Shield,
  Phone,
  type LucideIcon,
} from 'lucide-vue-next';

// =============================================
// Tipos auxiliares para constantes
// =============================================

export interface SelectOption<T = string> {
  value: T;
  label: string;
}

export interface SelectOptionWithVariant<T = number> extends SelectOption<T> {
  variant?: 'info' | 'success' | 'warning' | 'danger';
}

// =============================================
// Labels das seções do formulário
// =============================================

export const SECTION_LABELS = {
  identificacao: 'Identificação',
  endereco: 'Endereço Principal',
  dadosFiscais: 'Dados Fiscais',
  configuracoes: 'Configurações de Emissão',
  certificado: 'Certificado Digital',
  contato: 'Canais de Contato',
} as const;

export const SECTION_ICONS: Record<keyof typeof SECTION_LABELS, LucideIcon> = {
  identificacao: Building2,
  endereco: MapPin,
  dadosFiscais: Landmark,
  configuracoes: Settings,
  certificado: Shield,
  contato: Phone,
} as const;

// =============================================
// Opções de ambiente de emissão
// =============================================

export const AMBIENTE_EMISSAO_OPTIONS: SelectOptionWithVariant[] = [
  { value: 2, label: 'Homologação (Testes)', variant: 'info' },
  { value: 1, label: 'Produção', variant: 'danger' },
] as const;

// =============================================
// Opções de regime tributário
// =============================================

/**
 * O rótulo escolhido aqui vira o CRT da nota (helpers.crt_efetivo, no backend),
 * e é ele que decide se a emissão sai com CST ou com CSOSN.
 *
 * MEI existe porque o backend já mapeava "mei" para CRT 4 e a opção nunca foi
 * oferecida: quem se cadastrava como MEI caía em Regime Normal e emitia com CST
 * no lugar de CSOSN. Lucro Presumido e Lucro Real são ambos CRT 3 — a diferença
 * entre eles é o regime de apuração do PIS/COFINS (0,65/3,00 vs 1,65/7,60).
 *
 * "Regime Normal" continua na lista para não invalidar cadastros antigos; quem
 * o mantiver é tratado como cumulativo (o default conservador).
 */
export const REGIME_TRIBUTARIO_OPTIONS: SelectOption[] = [
  { value: 'Simples Nacional', label: '1 - Simples Nacional' },
  { value: 'Simples Nacional (Excesso de Sublimite)', label: '2 - Simples Nacional (Excesso de Sublimite)' },
  { value: 'MEI', label: '4 - MEI (Microempreendedor Individual)' },
  { value: 'Lucro Presumido', label: '3 - Regime Normal (Lucro Presumido)' },
  { value: 'Lucro Real', label: '3 - Regime Normal (Lucro Real)' },
  { value: 'Regime Normal', label: '3 - Regime Normal (não especificado)' },
] as const;

// =============================================
// Opções de regime de tributação ISS
// =============================================

export const REGIME_TRIBUTACAO_ISS_OPTIONS: SelectOption<number>[] = [
  { value: 1, label: 'Microempresa Municipal' },
  { value: 2, label: 'Estimativa' },
  { value: 3, label: 'Sociedade de Profissionais' },
  { value: 4, label: 'Cooperativa' },
  { value: 5, label: 'MEI' },
  { value: 6, label: 'ME/EPP (Simples Nacional)' },
] as const;

// =============================================
// Opções de tipo de certificado
// =============================================

export const TIPO_CERTIFICADO_OPTIONS: SelectOption<string>[] = [
  { value: 'ARQUIVO', label: 'Arquivo (A1)' },
  { value: 'WINDOWS', label: 'Instalado no Windows (A1 ou A3)' },
] as const;

// =============================================
// Opções de Indicador de IE (para NF-e)
// =============================================

export const INDICADOR_IE_OPTIONS: SelectOption[] = [
  { value: '1', label: '1 - Contribuinte ICMS' },
  { value: '2', label: '2 - Contribuinte Isento de IE' },
  { value: '9', label: '9 - Não Contribuinte' },
] as const;

// =============================================
// Opções de Natureza Jurídica
// =============================================

export const NATUREZA_JURIDICA_OPTIONS: SelectOption[] = [
  { value: 'MEI', label: 'MEI - Microempreendedor Individual' },
  { value: 'ME', label: 'ME - Microempresa' },
  { value: 'EPP', label: 'EPP - Empresa de Pequeno Porte' },
  { value: 'EI', label: 'EI - Empresário Individual' },
  { value: 'LTDA', label: 'LTDA - Sociedade Limitada' },
  { value: 'SLU', label: 'SLU - Sociedade Limitada Unipessoal' },
  { value: 'SA', label: 'S.A. - Sociedade Anônima' },
  { value: 'EIRELI', label: 'EIRELI - Empresa Individual de Responsabilidade Limitada' },
] as const;

// =============================================
// Opções de Tipo de Atividade
// =============================================

export const TIPO_ATIVIDADE_OPTIONS: SelectOption[] = [
  { value: 'COMERCIO', label: 'Comércio' },
  { value: 'INDUSTRIA', label: 'Indústria' },
  { value: 'SERVICO', label: 'Prestação de Serviços' },
  { value: 'MISTO', label: 'Misto (Comércio + Serviços)' },
] as const;

// =============================================
// Estados brasileiros (UF)
// =============================================

export const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
] as const;

export type UF = typeof UF_OPTIONS[number];

// =============================================
// Valores padrão
// =============================================

export const DEFAULT_FISCAL_SETTINGS = {
  ambiente_emissao: 2,
  serie_nfe: 1,
  ultimo_numero_nfe: 0,
  serie_nfce: 1,
  ultimo_numero_nfce: 0,
  tipo_certificado: 'ARQUIVO' as const,
  rps_serie: '1',
  rps_ultimo_numero: 0,
} as const;

export const DEFAULT_ENDERECO = {
  logradouro: '',
  numero: '',
  bairro: '',
  cidade: '',
  estado: '',
  cep: '',
  complemento: '',
  codigo_ibge: '',
} as const;

// =============================================
// Labels para exibição
// =============================================

export const FIELD_LABELS = {
  razao_social: 'Razão Social',
  nome_fantasia: 'Nome Fantasia',
  documento: 'CNPJ',
  cnae_principal: 'CNAE Principal',
  inscricao_estadual: 'Inscrição Estadual (IE)',
  inscricao_municipal: 'Inscrição Municipal (IM)',
  regime_tributario: 'Regime Tributário',
  email_comercial: 'E-mail Corporativo',
  telefone: 'Telefone Fixo',
  celular: 'Celular / WhatsApp',
  cep: 'CEP',
  logradouro: 'Logradouro',
  numero: 'Número',
  bairro: 'Bairro',
  cidade: 'Cidade',
  estado: 'Estado',
  complemento: 'Complemento',
  codigo_ibge: 'Código IBGE',
} as const;

// =============================================
// Mensagens de validação e feedback
// =============================================

export const MESSAGES = {
  success: {
    save: 'Dados atualizados com sucesso!',
    uploadCert: 'Certificado enviado com sucesso!',
    uploadLogo: 'Logo atualizada com sucesso!',
    addressFound: 'Endereço encontrado!',
    cnpjAutofill: 'Dados da empresa preenchidos automaticamente!',
  },
  error: {
    save: 'Erro ao salvar dados.',
    uploadCert: 'Erro ao enviar certificado.',
    uploadLogo: 'Erro ao enviar imagem.',
    loadData: 'Erro ao carregar dados.',
    loadCerts: 'Erro ao listar certificados.',
    connection: 'Erro na conexão.',
  },
  warning: {
    cepNotFound: 'CEP não encontrado.',
    invalidFile: 'Arquivo inválido.',
    noCertsFound: 'Nenhum certificado encontrado.',
    fillPrefeitura: 'Preencha os dados da prefeitura.',
    configureCert: 'Configure o certificado primeiro.',
  },
  info: {
    productionLocked: 'Configure Certificado e CSC primeiro',
  },
} as const;

// =============================================
// Configurações de upload
// =============================================

export const UPLOAD_CONFIG = {
  logo: {
    accept: 'image/png, image/jpeg, image/jpg',
    maxSize: 5 * 1024 * 1024, // 5MB
    recommendedSize: '200x200px',
  },
  certificado: {
    accept: '.pfx,.p12',
    extensions: ['.pfx', '.p12'],
  },
} as const;

// =============================================
// Query keys para TanStack Query
// =============================================

export const QUERY_KEYS = {
  empresa: 'empresa',
  windowsCertificates: 'windowsCertificates',
} as const;

export const STALE_TIME = 1000 * 60 * 5; // 5 minutos
