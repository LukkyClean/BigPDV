/**
 * @fileoverview Motor ESC/POS
 * @description Constrói sequências de bytes ESC/POS para impressoras térmicas
 * (cupom, corte de papel, gaveta de dinheiro), com suporte a bobina 58/80mm.
 */

export type Bobina = '58' | '80'

export const COLUNAS: Record<Bobina, number> = { '58': 32, '80': 48 }

/** Largura útil de impressão em pontos (dots) por bobina — limite do raster. */
export const DOTS: Record<Bobina, number> = { '58': 384, '80': 576 }

/**
 * Imagem monocromática pronta para o comando raster (GS v 0).
 * `data` é 1 bit por pixel, MSB primeiro, cada linha alinhada a byte;
 * bit 1 = ponto preto (impresso).
 */
export interface RasterImage {
  width: number
  height: number
  data: Uint8Array
}

const ESC = 0x1b
const GS = 0x1d

/**
 * Mapeamento Unicode → CP860 (português) dos caracteres acentuados relevantes.
 * Isolado em constante: se algum clone de impressora usar tabela divergente,
 * basta esvaziar este mapa para cair no strip de acentos.
 */
const CP860: Record<string, number> = {
  á: 0xa0, à: 0x85, â: 0x83, ã: 0x84, ç: 0x87,
  é: 0x82, ê: 0x88, í: 0xa1, ó: 0xa2, ô: 0x93, õ: 0x94,
  ú: 0xa3, ü: 0x81,
  Á: 0x86, À: 0x91, Â: 0x8f, Ã: 0x8e, Ç: 0x80,
  É: 0x90, Ê: 0x89, Í: 0x8b, Ó: 0x9f, Ô: 0x8c, Õ: 0x99,
  Ú: 0x96, Ü: 0x9a,
  º: 0xa7, ª: 0xa6, '°': 0xf8,
}

const COMBINANTES = /[̀-ͯ]/g

function removerAcentos(texto: string): string {
  return texto.normalize('NFD').replace(COMBINANTES, '')
}

/** Codifica texto para bytes CP860; caracteres desconhecidos perdem o acento ou viram '?' */
export function codificarTexto(texto: string): number[] {
  const bytes: number[] = []
  for (const char of texto) {
    if (char in CP860) {
      bytes.push(CP860[char])
      continue
    }
    const code = char.codePointAt(0) ?? 0x3f
    if (code <= 0x7f) {
      bytes.push(code)
      continue
    }
    const semAcento = removerAcentos(char)
    const codeSemAcento = semAcento.codePointAt(0) ?? 0x3f
    bytes.push(codeSemAcento <= 0x7f ? codeSemAcento : 0x3f) // 0x3f = '?'
  }
  return bytes
}

export class EscPosBuilder {
  private bytes: number[] = []
  readonly colunas: number
  readonly larguraDots: number

  constructor(bobina: Bobina) {
    this.colunas = COLUNAS[bobina]
    this.larguraDots = DOTS[bobina]
    this.init()
  }

  private init(): this {
    this.bytes.push(ESC, 0x40) // ESC @ — reset
    this.bytes.push(ESC, 0x74, 0x03) // ESC t 3 — codepage CP860 (português)
    return this
  }

  alinhar(a: 'esq' | 'centro' | 'dir'): this {
    this.bytes.push(ESC, 0x61, a === 'esq' ? 0 : a === 'centro' ? 1 : 2)
    return this
  }

  negrito(on: boolean): this {
    this.bytes.push(ESC, 0x45, on ? 1 : 0)
    return this
  }

  tamanhoDuplo(on: boolean): this {
    this.bytes.push(GS, 0x21, on ? 0x11 : 0x00)
    return this
  }

  /**
   * Imprime uma imagem raster monocromática (GS v 0). A centralização respeita
   * o `alinhar()` corrente. A largura da imagem deve caber em `larguraDots`
   * (garantido por quem gera o bitmap) — acima disso a impressora corta/embaralha.
   */
  raster(img: RasterImage): this {
    const larguraBytes = Math.ceil(img.width / 8)
    this.bytes.push(
      GS, 0x76, 0x30, 0x00, // GS v 0, modo normal
      larguraBytes & 0xff, (larguraBytes >> 8) & 0xff, // xL xH — largura em bytes
      img.height & 0xff, (img.height >> 8) & 0xff, // yL yH — altura em pontos
    )
    for (const byte of img.data) this.bytes.push(byte)
    return this
  }

  /** Imprime o texto e quebra a linha; textos maiores que a bobina quebram em várias linhas */
  linha(texto = ''): this {
    if (!texto) {
      this.bytes.push(0x0a)
      return this
    }
    for (let i = 0; i < texto.length; i += this.colunas) {
      this.bytes.push(...codificarTexto(texto.slice(i, i + this.colunas)), 0x0a)
    }
    return this
  }

  separador(): this {
    return this.linha('-'.repeat(this.colunas))
  }

  /** Texto à esquerda + texto à direita na mesma linha, preenchendo com espaços */
  parLados(esq: string, dir: string): this {
    const espaco = this.colunas - esq.length - dir.length
    if (espaco >= 1) {
      return this.linha(esq + ' '.repeat(espaco) + dir)
    }
    // Não cabe na mesma linha: esquerda em cima, direita alinhada embaixo
    this.linha(esq)
    return this.linha(' '.repeat(Math.max(0, this.colunas - dir.length)) + dir)
  }

  pular(n = 1): this {
    for (let i = 0; i < n; i++) this.bytes.push(0x0a)
    return this
  }

  /** Avança o papel e aciona o corte (ignorado por impressoras sem guilhotina) */
  cortar(): this {
    this.pular(4)
    this.bytes.push(GS, 0x56, 0x42, 0x03) // GS V 66 3 — corte parcial com feed
    return this
  }

  /** Pulso para abrir gaveta de dinheiro conectada à impressora */
  pulsoGaveta(): this {
    this.bytes.push(ESC, 0x70, 0x00, 0x19, 0xfa) // ESC p 0 25 250
    return this
  }

  build(): Uint8Array {
    return new Uint8Array(this.bytes)
  }
}

export function gerarCupomTeste(bobina: Bobina, opts?: { gaveta?: boolean }): Uint8Array {
  const b = new EscPosBuilder(bobina)
  b.alinhar('centro')
    .tamanhoDuplo(true)
    .linha('StartBig')
    .tamanhoDuplo(false)
    .linha('Cupom de teste de impressão')
    .pular()
    .alinhar('esq')
    .separador()
    .parLados('Bobina:', `${bobina}mm (${COLUNAS[bobina]} colunas)`)
    .parLados('Data:', new Date().toLocaleString('pt-BR'))
    .separador()
    .linha('Acentuação: ÁÉÍÓÚ áéíóú ãõ ç')
    .negrito(true)
    .linha('Texto em negrito')
    .negrito(false)
    .parLados('1x Produto exemplo', 'R$ 10,00')
    .negrito(true)
    .parLados('TOTAL', 'R$ 10,00')
    .negrito(false)
    .separador()
    .alinhar('centro')
    .linha('Se você leu até aqui,')
    .linha('a impressora está pronta!')
  if (opts?.gaveta) b.pulsoGaveta()
  b.cortar()
  return b.build()
}

export function gerarPulsoGaveta(): Uint8Array {
  return new Uint8Array([ESC, 0x40, ESC, 0x70, 0x00, 0x19, 0xfa])
}
