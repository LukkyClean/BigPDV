import { computed } from 'vue';
import { useAuthStore } from '@/shared/stores/auth.store';
import { formatCNPJ, formatCPF } from '@/shared/utils/document.utils';
import { getBackendBaseUrl } from '@/api/backendUrl';
import { montarPixBrCode } from '@/shared/utils/pixBrCode';
import type {
  CompanyPrintInfo,
  LarguraBobina,
  PrintFormat,
  TamanhoFolha,
} from '@/shared/components/print/print.types';
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

// --- Meia folha ---

/** 1mm em px CSS (96dpi). É a mesma conversão que o motor de impressão usa. */
const MM_EM_PX = 96 / 25.4;

/**
 * Alvo do encolhimento de emergência: a A4 (297mm, `@page` com margem 0) menos
 * 4mm de folga. A folga não é superstição — mirar nos 297mm exatos ainda dava
 * segunda folha numa via de 42 itens: não sobra nada para o arredondamento do
 * motor de impressão, e os blocos com `page-break-inside: avoid` precisam de
 * espaço inteiro para caber.
 */
const ALTURA_A4_PX = 293 * MM_EM_PX;

/**
 * Corpo de letra da meia folha, como fator.
 *
 * O texto da via é dimensionado por classes ABSOLUTAS do Tailwind — `text-xs`
 * (12px) no corpo, `text-[10px]` nos rótulos, `text-[8px]` nos textos legais.
 * Elas não herdam do `font-size` do container, então "fixar a fonte em 10" não
 * se faz mudando o container: faz-se fixando o FATOR. 10/12 põe o corpo da via
 * em 10px e desce todo o resto na mesma proporção.
 *
 * O que este número resolve: com zoom calculado por via, cada recibo saía com
 * um corpo de letra diferente — 0,94 numa venda de 3 itens, 0,81 numa de 8. A
 * loja imprime dezenas por dia e a variação aparece. Fixo, a via cresce para
 * baixo em vez de encolher, e o tamanho da letra é sempre o mesmo.
 */
const ZOOM_MEIA_FOLHA = 10 / 12;

/**
 * Piso do encolhimento de emergência. Só entra em cena quando a via, já no
 * corpo 10, passaria da folha INTEIRA — o que exige mais de 40 itens. Aí vale
 * apertar mais um pouco para salvar a folha única; abaixo de 0,7 não vale, e a
 * via aceita a segunda folha (nesse volume ela é conteúdo, não desperdício).
 */
const ZOOM_MINIMO = 0.7;

/**
 * Mede a altura real da via, em px, como ela sairá no papel.
 *
 * Precisa expor o container: fora da impressão ele é `hidden` (display:none) e
 * mediria zero. `display:block` inline vence a classe do Tailwind, a largura é
 * fixada na largura útil da página (a A4 inteira, já que `@page` tem margem 0)
 * e `visibility:hidden` + posição fora do viewport garantem que nada pisca na
 * tela. As medidas do documento (padding, corpo de letra, densidade) valem aqui
 * porque moram fora do `@media print` — ver CAMADA 2 do print-a4.css.
 */
function medirAlturaComprovante(container: HTMLElement): number {
  const estilo = container.style;
  // Salva e devolve PROPRIEDADE A PROPRIEDADE, e não via `cssText`: trocar o
  // `cssText` inteiro apagaria as variáveis já postas no elemento — entre elas
  // o `--arte-retrato`, que é justamente o que `ajustarArteParaCaber` está
  // medindo. O laço mediria sempre a mesma altura e nunca convergiria.
  const anterior = {
    display: estilo.display,
    position: estilo.position,
    left: estilo.left,
    top: estilo.top,
    width: estilo.width,
    visibility: estilo.visibility,
  };

  estilo.display = 'block';
  estilo.position = 'absolute';
  estilo.left = '-10000px';
  estilo.top = '0';
  estilo.width = '210mm';
  estilo.visibility = 'hidden';

  const altura = container.getBoundingClientRect().height;

  Object.assign(estilo, anterior);
  return altura;
}

/**
 * Põe a via no corpo de letra da meia folha e mede o resultado.
 *
 * O papel continua A4 e a via ocupa a metade de cima; quando não cabe nela, ela
 * CRESCE para baixo em vez de encolher — a metade é o piso do corte, não um
 * teto. Isso é o que mantém a letra igual em toda via impressa (ver
 * ZOOM_MEIA_FOLHA); a folha única continua garantida porque no corpo 10 cabem
 * mais de 40 itens numa A4.
 *
 * Sem nada disso, "meia folha" só funcionava em recibo de 1 item: medido no
 * comprovante de venda, o compacto custa 146mm com 1 item, 157mm com 3 e 184mm
 * com 8 — contra 148mm de metade de folha. O que sobrava para fora era o
 * rodapé, e o vazio antes dele vinha dos blocos com `page-break-inside: avoid`
 * (o card do cliente sozinho tem 36mm), que pulam inteiros quando não cabem no
 * que resta da página.
 */
function aplicarMeiaFolha(container: HTMLElement): void {
  const altura = medirAlturaComprovante(container);
  if (altura <= 0) return;

  // Encolhimento de emergência só se, no corpo 10, a via passar da folha
  // inteira. Nesse ponto é escolher entre letra menor e uma segunda folha.
  const zoom = Math.max(ZOOM_MINIMO, Math.min(ZOOM_MEIA_FOLHA, ALTURA_A4_PX / altura));

  container.classList.add('meia-folha');
  // Arredonda para baixo: 2 casas dão uma folga de fração de milímetro sem
  // mudança visível, e é essa folga que evita a segunda folha por um fio.
  container.style.setProperty('--meia-zoom', String(Math.floor(zoom * 100) / 100));
}

/**
 * Degraus do teto da foto em retrato na via de entrada (ver `.print-fotos img`
 * em OSPrintTemplate.vue), do maior para o menor. O laço fica com o PRIMEIRO
 * que fechar em uma folha, então a escada serve para os dois lados: numa via
 * folgada a arte sobe e ocupa o que a folha tem livre; numa via cheia ela desce
 * e cede o necessário para não gastar uma segunda folha.
 *
 * O topo é 120mm porque é o que a via de entrada da serigrafia libera na
 * densidade compacta — nela o comprovante inteiro encolhe cerca de 30% e a arte
 * herda a sobra. Um retrato 3:4 a 120mm de altura tem 90mm de largura e ainda
 * cabe nos ~175mm úteis do bloco, então a largura nunca é o limite.
 */
const TETOS_ARTE_MM = [120, 100, 85, 68, 55, 45, 38, 30];

/**
 * Marca as fotos em retrato, imediatamente antes de medir e imprimir.
 *
 * Foto de celular é retrato e precisa de mais altura que uma arte deitada para
 * sair do mesmo tamanho aparente — é a classe `.foto-retrato` que lhe dá o teto
 * maior. A orientação só existe depois do download, então isto tem que rodar
 * tarde; `aguardarImagensDaImpressao` já correu quando chegamos aqui.
 *
 * Ficava num `@load` no template e era uma armadilha: o evento **não redispara
 * para imagem que já está no cache do navegador**. Na segunda impressão da
 * mesma OS o listener podia entrar depois do `complete`, a classe nunca era
 * posta, e a arte saía no teto pequeno — sem erro nenhum no console. Aqui a
 * decisão é tomada por estado (`naturalHeight > naturalWidth`), não por evento,
 * e o estado não tem como se perder.
 */
function classificarOrientacaoDasFotos(container: HTMLElement): void {
  container.querySelectorAll<HTMLImageElement>('.print-fotos img').forEach((img) => {
    img.classList.toggle('foto-retrato', img.naturalHeight > img.naturalWidth);
  });
}

/**
 * Encolhe a arte — e só a arte — até a via caber em uma folha.
 *
 * Foto de celular é retrato e precisa de altura para ser legível para quem
 * produz, mas a via de entrada tem pouca folga: o histórico do template conta
 * que 55mm já deixava o rodapé transbordar sozinho para a segunda folha. Em vez
 * de chutar um teto que sirva para toda OS, a via é medida e a arte cede o
 * necessário — em OS curta ela sai grande, em OS cheia sai menor, e nenhuma das
 * duas gasta folha a mais.
 *
 * Cede a ARTE porque é o único elemento elástico: o resto do comprovante é
 * conteúdo que protege o cliente e não é negociável (ver §4 do plano).
 *
 * Só vale para a folha inteira. Na meia folha o corpo de letra fixo já reduz
 * tudo em 17% e a via cresce dentro da mesma folha, então a arte não precisa
 * ceder nada.
 */
function ajustarArteParaCaber(container: HTMLElement): void {
  if (!container.querySelector('.print-fotos img.foto-retrato')) return;

  for (const teto of TETOS_ARTE_MM) {
    container.style.setProperty('--arte-retrato', `${teto}mm`);
    if (medirAlturaComprovante(container) <= ALTURA_A4_PX) return;
  }
  // Nem no menor teto coube: a via é grande por conteúdo, não por causa da
  // foto. Devolve o tamanho bom da arte — a segunda folha viria de qualquer
  // jeito, e aí não há motivo para imprimir a arte pequena também.
  container.style.removeProperty('--arte-retrato');
}

/** Devolve todos os containers ao estado de folha inteira, arte no tamanho cheio. */
function limparMeiaFolha(): void {
  document.querySelectorAll<HTMLElement>('.print-container').forEach((el) => {
    el.classList.remove('meia-folha');
    el.style.removeProperty('--meia-zoom');
    el.style.removeProperty('--arte-retrato');
  });
}

/**
 * Imprime injetando a regra `@page` do papel escolhido.
 *
 * `format` é a CLASSE do dispositivo (folha ou bobina); `opcoes` refina o papel
 * dentro dela. Os dois eixos são separados porque quem decide cada um é
 * diferente: a máquina sabe se tem térmica (formato), a empresa decide se a via
 * sai em folha inteira ou meia folha (tamanho).
 *
 * `folha: 'A5'` NÃO troca o papel da impressora: ela continua recebendo uma A4
 * — a folha que a loja tem na gaveta — e o comprovante é confinado à metade de
 * cima, com linha de corte. Trocar o `@page` para A5 deixava o resultado na mão
 * do driver (escalar, centralizar ou cortar, varia por modelo) e, pior, punha a
 * página em 148mm de LARGURA: o layout refluía numa coluna estreita e CRESCIA.
 *
 * Os padrões reproduzem o comportamento anterior, então os chamadores que só
 * passam `format` — ficha de vistoria, relatórios — seguem em A4 inalterados.
 */
export function imprimirComPagina(
  format: PrintFormat,
  opcoes: { folha?: TamanhoFolha; bobina?: LarguraBobina } = {},
): void {
  const { folha = 'A4', bobina = '80' } = opcoes;
  // A bobina deixou de ser fixa em 80mm: numa loja de 58mm a via HTML saía com
  // a página larga demais e o conteúdo desalinhado do papel.
  const size = format === 'CUPOM' ? `${bobina}mm auto` : 'A4';

  // Sempre antes de decidir: a impressão anterior pode ter sido de outro
  // documento, com outro papel.
  limparMeiaFolha();
  if (format !== 'CUPOM') {
    // A ficha de vistoria fica de fora: ela é um formulário para preencher à
    // mão, com página própria (`@page ficha-vistoria`), e não um comprovante.
    // Ela pode estar montada junto com a OS — o `v-if` dela só cai no
    // `afterprint`, com fallback de 2 minutos.
    document
      .querySelectorAll<HTMLElement>('.print-container:not(.ficha-a4)')
      .forEach((container) => {
        classificarOrientacaoDasFotos(container);
        if (folha === 'A5') aplicarMeiaFolha(container);
        else ajustarArteParaCaber(container);
      });
  }

  // Limpa sobras de uma impressão anterior ANTES de injetar a nova. A limpeza
  // migrou para cá de propósito: antes havia um `setTimeout(limpar, 1500)` como
  // rede de segurança do `afterprint`, e 1,5s é MENOS do que alguém leva para
  // olhar a pré-visualização e clicar em Imprimir. O timer disparava com o
  // diálogo ABERTO, arrancava a regra e a página voltava para o A4 do
  // print-a4.css — pedir A5 e sair A4 era exatamente esse sintoma.
  //
  // Deixar a regra no DOM até a próxima impressão é inócuo: ela vive dentro de
  // `@media print` e não afeta a tela.
  document.querySelectorAll('style[data-print-page]').forEach((s) => s.remove());

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
  // Sem timer de fallback aqui: ele corria contra o diálogo aberto (ver acima).
  // Se o `afterprint` não disparar, a regra fica no <head> até a próxima
  // impressão, que a remove — e enquanto isso não faz nada, porque é `@media print`.
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
      inscricaoEstadual: empresa?.inscricao_estadual ?? null,
      cidade: endereco?.cidade || '',
      chavePix: empresa?.chave_pix ?? null,
      pixAtivo: Boolean(empresa?.pix_ativo),
    };
  });

  return { companyInfo };
}
