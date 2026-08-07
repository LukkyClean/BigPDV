/**
 * @fileoverview Montador do BR Code do PIX — offline, sem banco e sem internet.
 *
 * O QR do PIX é o padrão aberto EMV MPM: uma sequência de campos `IDTAMVALOR`
 * fechada por um CRC16. Dado a chave, o valor e o nome/cidade do recebedor, a
 * string se monta aqui mesmo, no navegador — nenhuma credencial, nenhum PSP.
 *
 * A consequência a ter em mente: este QR **cobra, mas não confirma**. O sistema
 * não fica sabendo que o cliente pagou; a conferência segue no app do banco.
 *
 * O risco real desta função não é o algoritmo, que é fechado, e sim a entrada
 * suja. Uma chave digitada como `(11) 99999-8888` gera um QR sintaticamente
 * perfeito e economicamente morto: nenhum banco resolve a chave, e o erro só
 * aparece com o cliente na frente do balcão. Por isso `normalizarChavePix`
 * existe e roda antes de qualquer coisa.
 *
 * Determinístico de ponta a ponta, então dá para provar em vez de confiar:
 * `scripts/check-pix.mjs` barra o build.
 */

// ─── Limites do padrão ────────────────────────────────────────────────────────

/** Teto da chave no BR Code — o e-mail é a mais longa das cinco formas. */
export const CHAVE_TAMANHO_MAXIMO = 77
/** Campo 59 (nome do recebedor). */
export const NOME_TAMANHO_MAXIMO = 25
/** Campo 60 (cidade do recebedor). */
export const CIDADE_TAMANHO_MAXIMO = 15
/** Campo 62-05 (txid). */
export const TXID_TAMANHO_MAXIMO = 25
/** Campo 54 (valor) — `9999999999.99` já ocupa os 13. */
export const VALOR_TAMANHO_MAXIMO = 13

const GUI_PIX = 'br.gov.bcb.pix'
/** Sem txid, a convenção do QR estático é três asteriscos. */
const TXID_VAZIO = '***'
const NOME_QUANDO_VAZIO = 'NAO INFORMADO'
const CIDADE_QUANDO_VAZIA = 'BRASIL'

// ─── Normalização da chave ────────────────────────────────────────────────────

export type TipoChavePix = 'CPF' | 'CNPJ' | 'TELEFONE' | 'EMAIL' | 'ALEATORIA' | 'INDEFINIDA'

export interface ChavePixNormalizada {
  /** A chave no formato que vai literalmente para dentro do QR. */
  chave: string
  tipo: TipoChavePix
  /** `false` quando não deu para reconhecer nenhuma das cinco formas. */
  reconhecida: boolean
}

const RE_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const soDigitos = (texto: string) => texto.replace(/\D/g, '')

/**
 * CPF e celular com DDD têm os mesmos 11 dígitos, então o formato sozinho não
 * decide. O dígito verificador decide: se fecha, é CPF; se não fecha, sobra o
 * telefone.
 */
function cpfValido(digitos: string): boolean {
  if (digitos.length !== 11 || /^(\d)\1{10}$/.test(digitos)) return false
  for (const [ate, posicao] of [[9, 10], [10, 11]] as const) {
    let soma = 0
    for (let i = 0; i < ate; i++) soma += Number(digitos[i]) * (posicao - i)
    const resto = (soma * 10) % 11
    if ((resto === 10 ? 0 : resto) !== Number(digitos[ate])) return false
  }
  return true
}

function cnpjValido(digitos: string): boolean {
  if (digitos.length !== 14 || /^(\d)\1{13}$/.test(digitos)) return false
  for (const ate of [12, 13]) {
    let soma = 0
    let peso = ate - 7
    for (let i = 0; i < ate; i++) {
      soma += Number(digitos[i]) * peso
      peso = peso === 2 ? 9 : peso - 1
    }
    const resto = soma % 11
    if ((resto < 2 ? 0 : 11 - resto) !== Number(digitos[ate])) return false
  }
  return true
}

/** DDD de 11 a 99; celular tem 9 na frente do número. */
function telefoneBrasileiro(digitos: string): boolean {
  if (digitos.length !== 10 && digitos.length !== 11) return false
  const ddd = Number(digitos.slice(0, 2))
  if (ddd < 11 || ddd > 99) return false
  return digitos.length === 10 || digitos[2] === '9'
}

/**
 * Descobre qual das cinco formas o dono digitou e devolve a chave no formato
 * que o banco espera — é este texto, e não o que está na tela, que entra no QR.
 *
 * Não reconhecer não é motivo para bloquear: o backend aceita a chave como
 * texto de propósito. Quem não for reconhecida passa adiante como veio, com
 * `reconhecida: false` para a tela poder avisar.
 */
export function normalizarChavePix(bruta: string | null | undefined): ChavePixNormalizada {
  const texto = (bruta ?? '').trim()
  if (!texto) return { chave: '', tipo: 'INDEFINIDA', reconhecida: false }

  if (RE_EMAIL.test(texto)) {
    return { chave: texto.toLowerCase(), tipo: 'EMAIL', reconhecida: true }
  }
  if (RE_UUID.test(texto)) {
    return { chave: texto.toLowerCase(), tipo: 'ALEATORIA', reconhecida: true }
  }

  const digitos = soDigitos(texto)

  // O `+` é declaração de intenção: quem escreve `+55…` está dizendo telefone.
  if (texto.startsWith('+') && telefoneBrasileiro(digitos.replace(/^55/, ''))) {
    return { chave: `+55${digitos.replace(/^55/, '')}`, tipo: 'TELEFONE', reconhecida: true }
  }

  // Só dígitos (com ou sem máscara). Fora disso é texto solto, não é chave.
  if (digitos.length === texto.replace(/[.\-/()\s+]/g, '').length) {
    if (digitos.length === 14 && cnpjValido(digitos)) {
      return { chave: digitos, tipo: 'CNPJ', reconhecida: true }
    }
    if (digitos.length === 11 && cpfValido(digitos)) {
      return { chave: digitos, tipo: 'CPF', reconhecida: true }
    }
    if (telefoneBrasileiro(digitos)) {
      return { chave: `+55${digitos}`, tipo: 'TELEFONE', reconhecida: true }
    }
    if (digitos.length === 13 && digitos.startsWith('55') && telefoneBrasileiro(digitos.slice(2))) {
      return { chave: `+${digitos}`, tipo: 'TELEFONE', reconhecida: true }
    }
  }

  return { chave: texto, tipo: 'INDEFINIDA', reconhecida: false }
}

export const ROTULO_TIPO_CHAVE: Record<TipoChavePix, string> = {
  CPF: 'CPF',
  CNPJ: 'CNPJ',
  TELEFONE: 'Telefone',
  EMAIL: 'E-mail',
  ALEATORIA: 'Chave aleatória',
  INDEFINIDA: 'Formato não reconhecido',
}

// ─── Texto que cabe no QR ─────────────────────────────────────────────────────

/**
 * Nome e cidade vão no QR sem acento, e não por preciosismo: o comprimento de
 * cada campo é declarado em BYTES, e `ã` ocupa dois. Dobrar o alfabeto para
 * ASCII mantém a contagem honesta — e evita o campo que alguns bancos recusam.
 */
export function paraAsciiImprimivel(texto: string, limite: number): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\x20-\x7e]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, limite)
    .trim()
}

/** txid do QR estático aceita só letra e número. */
function limparTxid(bruto: string | null | undefined): string {
  const limpo = (bruto ?? '').replace(/[^A-Za-z0-9]/g, '').slice(0, TXID_TAMANHO_MAXIMO)
  return limpo || TXID_VAZIO
}

// ─── Montagem ─────────────────────────────────────────────────────────────────

/** Um campo EMV: identificador, tamanho em duas casas, conteúdo. */
function campo(id: string, valor: string): string {
  return `${id}${String(valor.length).padStart(2, '0')}${valor}`
}

/**
 * CRC16/CCITT-FALSE (polinômio 0x1021, inicial 0xFFFF), calculado sobre o
 * payload inteiro **incluindo** o `6304` do próprio campo do CRC.
 */
export function crc16(payload: string): string {
  let crc = 0xffff
  for (let i = 0; i < payload.length; i++) {
    crc ^= payload.charCodeAt(i) << 8
    for (let bit = 0; bit < 8; bit++) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff
    }
  }
  return crc.toString(16).toUpperCase().padStart(4, '0')
}

export interface ParametrosBrCode {
  /** Chave crua, como está cadastrada. A normalização acontece aqui dentro. */
  chave: string
  /** Valor em CENTAVOS. Zero ou ausente gera QR sem valor — o cliente digita. */
  valorCentavos?: number
  /** Nome do recebedor (campo 59). */
  nome?: string
  /** Cidade do recebedor (campo 60). */
  cidade?: string
  /** Identificador da cobrança (campo 62-05). Sem ele, vai `***`. */
  txid?: string
}

/**
 * Monta o BR Code — a mesma string que vira QR e que serve de "copia e cola".
 *
 * Devolve `''` quando não há chave: sem chave não existe QR, e é melhor a tela
 * não desenhar nada do que desenhar um quadrado que ninguém consegue pagar.
 */
export function montarPixBrCode(params: ParametrosBrCode): string {
  const { chave } = normalizarChavePix(params.chave)
  if (!chave || chave.length > CHAVE_TAMANHO_MAXIMO) return ''

  const centavos = Math.round(params.valorCentavos ?? 0)
  const valorPedido = centavos > 0 ? (centavos / 100).toFixed(2) : ''
  // Um valor que estoure os 13 caracteres geraria um QR inválido. Melhor cobrar
  // sem valor — o cliente digita — do que entregar um quadrado que não abre.
  // A decisão precisa vir antes do campo 01: um QR sem valor é reutilizável.
  const valor = valorPedido.length <= VALOR_TAMANHO_MAXIMO ? valorPedido : ''

  const nome = paraAsciiImprimivel(params.nome ?? '', NOME_TAMANHO_MAXIMO) || NOME_QUANDO_VAZIO
  const cidade = paraAsciiImprimivel(params.cidade ?? '', CIDADE_TAMANHO_MAXIMO) || CIDADE_QUANDO_VAZIA

  let payload =
    campo('00', '01') +
    // 11 = reutilizável, 12 = uso único. Com o valor da venda embutido, é único.
    campo('01', valor ? '12' : '11') +
    campo('26', campo('00', GUI_PIX) + campo('01', chave)) +
    campo('52', '0000') +
    campo('53', '986')

  if (valor) payload += campo('54', valor)

  payload +=
    campo('58', 'BR') +
    campo('59', nome) +
    campo('60', cidade) +
    campo('62', campo('05', limparTxid(params.txid)))

  return `${payload}6304${crc16(`${payload}6304`)}`
}
