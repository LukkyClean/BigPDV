import { computed } from 'vue';
import { useAuthStore } from '@/shared/stores/auth.store';
import { formatCNPJ, formatCPF } from '@/shared/utils/document.utils';
import { getBackendBaseUrl } from '@/api/backendUrl';
import { montarPixBrCode } from '@/shared/utils/pixBrCode';
import type { CompanyPrintInfo, PrintFormat } from '@/shared/components/print/print.types';
import { parseTimestampBackend } from './date.utils';

// --- Cliente helpers (union type PF/PJ) ---

export function getClienteNome(cliente?: { tipo: string; nome?: string; nome_fantasia?: string; razao_social?: string } | null): string {
  if (!cliente) return '-';
  if (cliente.tipo === 'PF') return cliente.nome || '-';
  return cliente.nome_fantasia || cliente.razao_social || '-';
}

export function getClienteDoc(cliente?: { cpf?: string; cnpj?: string } | null): string {
  if (!cliente) return '';
  return (cliente as { cpf?: string }).cpf || (cliente as { cnpj?: string }).cnpj || '';
}

export function getClientePhone(cliente?: { celular?: string | null; telefone?: string | null } | null): string {
  if (!cliente) return '';
  return (cliente as { celular?: string | null }).celular || (cliente as { telefone?: string | null }).telefone || '';
}

interface EnderecoCliente {
  logradouro?: string | null;
  numero?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  estado?: string | null;
  cep?: string | null;
  complemento?: string | null;
}

/** "00000000" -> "00000-000"; deixa como está se não tiver 8 dígitos. */
function formatCep(cep?: string | null): string {
  const so = (cep ?? '').replace(/\D/g, '');
  return so.length === 8 ? `${so.slice(0, 5)}-${so.slice(5)}` : (cep ?? '');
}

/**
 * Endereço do cliente em uma linha, para os recibos:
 * "Rua X, 123 (Fundos) - Bairro, Cidade - UF, CEP 00000-000".
 * Retorna '' se o cliente não tiver endereço cadastrado.
 */
export function getClienteEndereco(cliente?: { endereco?: EnderecoCliente | null } | null): string {
  const e = cliente?.endereco;
  if (!e || !e.logradouro) return '';

  const rua = [e.logradouro, e.numero].filter(Boolean).join(', ');
  const compl = e.complemento ? ` (${e.complemento})` : '';
  const cidadeUf = e.cidade && e.estado ? `${e.cidade} - ${e.estado}` : e.cidade || e.estado || '';
  const local = [e.bairro, cidadeUf].filter(Boolean).join(', ');
  const cep = e.cep ? `, CEP ${formatCep(e.cep)}` : '';

  return [rua + compl, local].filter(Boolean).join(' - ') + cep;
}

/**
 * True quando o "tipo" do objeto acrescenta informação além do rótulo do
 * segmento. Em oficina o tipo é deduzido como o próprio rótulo ("Veículo"),
 * então repeti-lo no recibo é redundante → false. Em informática o tipo é
 * específico ("COMPUTADOR" vs rótulo "Equipamento") → true, vale mostrar.
 */
export function tipoObjetoRelevante(tipo?: string | null, rotuloSegmento?: string | null): boolean {
  const t = (tipo ?? '').trim();
  if (!t) return false;
  return t.toLowerCase() !== (rotuloSegmento ?? '').trim().toLowerCase();
}

// --- Payment helpers ---

export function getPaymentDisplayName(nome: string): string {
  if (!nome) return '';
  const cleanName = nome.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
  const map: Record<string, string> = {
    'PIX': 'Pix',
    'DINHEIRO': 'Dinheiro',
    'CARTAO_CREDITO': 'Cartão de Crédito',
    'CARTAO DE CREDITO': 'Cartão de Crédito',
    'CARTAO_DEBITO': 'Cartão de Débito',
    'CARTAO DE DEBITO': 'Cartão de Débito',
    'BOLETO': 'Boleto',
    'TRANSFERENCIA': 'Transferência',
    'TRANSFERENCIA BANCARIA': 'Transferência Bancária',
    'TRANSFERENCIA_BANCARIA': 'Transferência Bancária',
  };

  const mapped = map[cleanName] || map[nome.toUpperCase()];
  if (mapped) return mapped;

  return nome
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function inferPaymentType(nome: string): string {
  const lower = nome.toLowerCase();
  if (lower.includes('pix')) return 'PIX';
  if (lower.includes('crédito') || lower.includes('credito')) return 'CARTAO_CREDITO';
  if (lower.includes('débito') || lower.includes('debito')) return 'CARTAO_DEBITO';
  if (lower.includes('boleto')) return 'BOLETO';
  if (lower.includes('transferência') || lower.includes('transferencia')) return 'TRANSFERENCIA';
  if (lower.includes('dinheiro')) return 'DINHEIRO';
  return 'OUTROS';
}

export function inferPermiteParcelamento(tipo: string): boolean {
  return tipo === 'CARTAO_CREDITO';
}

// --- PIX no comprovante ---

/** O que o comprovante precisa saber de um pagamento para decidir sobre o PIX. */
export interface PagamentoImpresso {
  /** Nome da forma já resolvido — na venda vem de um resolver, na OS vem embutido. */
  nome: string;
  /** Valor em centavos. */
  valor: number;
}

/**
 * Decide se o comprovante leva QR do PIX, e por qual valor.
 *
 * O valor é a soma **só dos pagamentos em PIX**, não o total do documento: numa
 * venda paga metade em dinheiro e metade em PIX, o QR cobra a metade certa.
 *
 * Devolve `null` quando não há o que imprimir — sem chave, com o PIX desligado,
 * ou sem nenhum pagamento em PIX no documento.
 */
export function pixParaImpressao(params: {
  empresa: CompanyPrintInfo;
  pagamentos?: PagamentoImpresso[] | null;
  /** Identificador da cobrança (número da OS, por exemplo). */
  txid?: string;
}): { payload: string; valorCentavos: number } | null {
  const { empresa } = params;
  if (!empresa.pixAtivo || !empresa.chavePix) return null;

  const valorCentavos = (params.pagamentos ?? [])
    .filter((p) => inferPaymentType(p.nome) === 'PIX')
    .reduce((soma, p) => soma + p.valor, 0);
  if (valorCentavos <= 0) return null;

  const payload = montarPixBrCode({
    chave: empresa.chavePix,
    valorCentavos,
    nome: empresa.nome,
    cidade: empresa.cidade,
    txid: params.txid,
  });

  return payload ? { payload, valorCentavos } : null;
}

// --- Formatters ---

/** Timestamp de evento do backend (UTC) → data e hora locais na via impressa. */
export function formatPrintDate(dateStr?: string | Date | null): string {
  if (!dateStr) return '__/__/____';
  return parseTimestampBackend(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatPrintPhone(phone?: string): string {
  if (!phone) return '';
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 11) {
    return digits.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  }
  if (digits.length === 10) {
    return digits.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
  }
  return phone;
}

export function formatPrintDoc(doc?: string): string {
  if (!doc) return '';
  const digits = doc.replace(/\D/g, '');
  if (digits.length > 11) {
    return digits.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
  }
  return digits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

// --- Image URL ---

export function getImageUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  const cleanPath = path.replace(/^static\//, '');
  return `${getBackendBaseUrl()}/static/${cleanPath}`;
}

// --- Impressão: tamanho de página ---

/**
 * Dispara window.print() forçando o tamanho de página do formato atual.
 *
 * print-a4.css e print-cupom.css são globais e ambos declaram `@page { size }`
 * (A4 vs 80mm). Como os dois convivem na cascata, o `size: A4` vencia e o cupom
 * saía impresso numa folha A4. Aqui injetamos a regra do formato atual por
 * último no <head> — última fonte da mesma origem vence a cascata — e a
 * removemos assim que a impressão termina.
 */
/**
 * Espera as imagens do `.print-container` terminarem de carregar.
 *
 * `window.print()` fotografa a página como ela está: imagem que ainda não
 * chegou sai como quadro em branco no papel. Até então isso não aparecia porque
 * a única imagem das vias era a logo, que já vem do cache do cabeçalho do
 * sistema — a arte da OS é buscada do backend na hora da impressão.
 *
 * O teto de tempo é obrigatório: uma URL quebrada não pode deixar o usuário
 * preso olhando para uma tela que nunca abre o diálogo de impressão. Estourando
 * o teto, imprime como estiver — melhor uma via sem a foto do que via nenhuma.
 */
export async function aguardarImagensDaImpressao(timeoutMs = 4000): Promise<void> {
  const imagens = Array.from(
    document.querySelectorAll<HTMLImageElement>('.print-container img'),
  );

  const pendentes = imagens.filter((img) => !img.complete || img.naturalWidth === 0);
  if (pendentes.length === 0) return;

  const carregadas = Promise.all(
    pendentes.map(
      (img) =>
        new Promise<void>((resolve) => {
          // `error` também resolve: imagem quebrada não deve segurar a via.
          img.addEventListener('load', () => resolve(), { once: true });
          img.addEventListener('error', () => resolve(), { once: true });
        }),
    ),
  ).then(() => undefined);

  const teto = new Promise<void>((resolve) => setTimeout(resolve, timeoutMs));

  await Promise.race([carregadas, teto]);
}

export function imprimirComPagina(format: PrintFormat): void {
  const size = format === 'CUPOM' ? '80mm auto' : 'A4';
  const style = document.createElement('style');
  style.setAttribute('data-print-page', '');
  style.textContent = `@media print{@page{size:${size};margin:0}}`;
  document.head.appendChild(style);

  const limpar = () => {
    style.remove();
    window.removeEventListener('afterprint', limpar);
  };
  window.addEventListener('afterprint', limpar);
  window.print();
  // Fallback: em alguns motores o evento afterprint não dispara de forma
  // confiável — garante que a regra injetada não fique presa no <head>.
  setTimeout(limpar, 1500);
}

// --- Company info composable ---

export function useCompanyPrintInfo() {
  const authStore = useAuthStore();

  const companyInfo = computed<CompanyPrintInfo>(() => {
    const empresa = authStore.userData?.empresa;
    const endereco = authStore.enderecoData;

    const enderecoParts: string[] = [];
    if (endereco?.logradouro) {
      enderecoParts.push(endereco.logradouro);
      if (endereco.numero) enderecoParts.push(endereco.numero);
    }
    if (endereco?.bairro) enderecoParts.push(endereco.bairro);
    if (endereco?.cidade && endereco?.estado) {
      enderecoParts.push(`${endereco.cidade} - ${endereco.estado}`);
    }

    const shortParts: string[] = [];
    if (endereco?.logradouro) shortParts.push(endereco.logradouro);
    if (endereco?.numero) shortParts.push(endereco.numero);
    if (endereco?.bairro) shortParts.push(endereco.bairro);

    const cityState = endereco?.cidade && endereco?.estado
      ? `${endereco.cidade} - ${endereco.estado}`
      : '';

    const docRaw = empresa?.documento || '';
    const digits = docRaw.replace(/\D/g, '');
    let formattedDoc = '';
    let labelDoc = 'CNPJ';
    if (digits.length === 11) {
      formattedDoc = formatCPF(digits);
      labelDoc = 'CPF';
    } else if (digits.length === 14) {
      formattedDoc = formatCNPJ(digits);
      labelDoc = 'CNPJ';
    } else if (docRaw) {
      formattedDoc = docRaw;
    }

    return {
      nome: empresa?.nome_fantasia || empresa?.razao_social || 'Empresa',
      razaoSocial: empresa?.razao_social || '',
      cnpj: formattedDoc,
      documento: formattedDoc,
      labelDocumento: labelDoc,
      endereco: enderecoParts.join(', ') || 'Endereço não cadastrado',
      enderecoLinha1: shortParts.join(', ') || 'Endereço não informado',
      enderecoLinha2: cityState,
      contato: formatPrintPhone(empresa?.telefone || empresa?.celular || ''),
      email: empresa?.email || '',
      logo: getImageUrl(empresa?.url_logo),
      cidade: endereco?.cidade || '',
      chavePix: empresa?.chave_pix ?? null,
      pixAtivo: Boolean(empresa?.pix_ativo),
    };
  });

  return { companyInfo };
}
