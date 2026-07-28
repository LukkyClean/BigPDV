/**
 * @fileoverview Conversão do logo da empresa em bitmap monocromático (1-bit)
 * para o comando raster do ESC/POS. Roda no browser (fetch/img + canvas).
 *
 * Impressora térmica só imprime preto e branco: a imagem é reduzida à largura
 * da bobina, achatada para tons de cinza e passada por um limiar (threshold).
 *
 * IMPORTANTE (CORS): exibir a logo (`<img>`) não exige CORS, mas LER os pixels
 * dela (canvas.getImageData, necessário para o raster) exige. Como o app roda
 * numa origem (tauri.localhost) e o backend em outra (127.0.0.1:porta), TODO
 * acesso em modo CORS ao `/static` falha no webview do Tauri (fetch, axios-blob e
 * `<img crossOrigin>` deram erro de rede) — a logo aparecia no A4 (`<img>` puro,
 * sem CORS) mas sumia na térmica. A saída é o backend entregar a logo em base64
 * pelo endpoint `/empresas/logo-base64`, que trafega pelo canal /api já
 * autenticado (sem depender de CORS no /static); o data URL resultante é
 * same-origin e o canvas nunca é contaminado. `fetch`/`img` ficam como fallback
 * (navegador em dev) e, se tudo falhar, a impressão segue sem logo (log no console).
 */

import { api } from '@/api/axios'
import type { RasterImage } from './escpos'

// Cache por (url + largura): decodificar e binarizar a cada impressão é caro.
// Só sucessos são cacheados — falha de rede não deve virar "sem logo" permanente.
const cache = new Map<string, RasterImage>()

interface Opcoes {
  /** Luminância (0–255) abaixo da qual o pixel vira preto. Padrão 160. */
  limiar?: number
  /** Teto de altura em pontos, evita logo gigante consumir bobina. Padrão 240. */
  alturaMaxDots?: number
}

interface FonteImagem {
  source: CanvasImageSource
  width: number
  height: number
  cleanup?: () => void
}

function msgErro(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

/** Carrega via elemento <img>. Com crossOrigin='anonymous' o canvas não é
 *  contaminado SE o servidor responder CORS — sem CORS, o load falha (onerror). */
function carregarViaImg(url: string, comCors: boolean): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const el = new Image()
    if (comCors) el.crossOrigin = 'anonymous'
    el.onload = () => resolve(el)
    el.onerror = () => reject(new Error(comCors ? 'load falhou (CORS/rede)' : 'load falhou'))
    el.src = url
  })
}

/**
 * Decodifica a imagem tentando, em ordem, os caminhos mais robustos. Acumula o
 * motivo de cada falha para o diagnóstico — se tudo falhar, lança um Error com
 * todos os motivos concatenados.
 */
async function carregarImagem(url: string): Promise<FonteImagem> {
  const problemas: string[] = []

  // 1) Endpoint /empresas/logo-base64 — CAMINHO PRINCIPAL no app instalado.
  //    No webview do Tauri, TODA requisição em modo CORS contra o /static falha
  //    (fetch, <img crossOrigin> e até axios com blob deram erro de rede), mas o
  //    canal /api já autenticado funciona. Então o backend entrega a logo em
  //    base64 por aqui; o data URL é same-origin, o canvas nunca é contaminado e
  //    getImageData funciona. (O parâmetro `url` vira só chave de cache/fallback.)
  try {
    const resp = await api.get<{ data_url: string }>('/empresas/logo-base64')
    const blob = await (await fetch(resp.data.data_url)).blob()
    const bmp = await createImageBitmap(blob)
    return { source: bmp, width: bmp.width, height: bmp.height, cleanup: () => bmp.close() }
  } catch (e) {
    problemas.push(`api-base64: ${msgErro(e)}`)
  }

  // 2) fetch + createImageBitmap — fallback (navegador em dev, mesma origem).
  try {
    const resp = await fetch(url)
    if (resp.ok) {
      const bmp = await createImageBitmap(await resp.blob())
      return { source: bmp, width: bmp.width, height: bmp.height, cleanup: () => bmp.close() }
    }
    problemas.push(`fetch HTTP ${resp.status}`)
  } catch (e) {
    problemas.push(`fetch: ${msgErro(e)}`)
  }

  // 3) <img crossOrigin> — último recurso; mesmo mecanismo do recibo A4 (que
  //    funciona), mas pedindo CORS para poder ler os pixels depois.
  try {
    const img = await carregarViaImg(url, true)
    return { source: img, width: img.naturalWidth, height: img.naturalHeight }
  } catch (e) {
    problemas.push(`img(cors): ${msgErro(e)}`)
  }

  throw new Error(problemas.join(' | '))
}

/**
 * Carrega o logo e devolve o bitmap pronto para `EscPosBuilder.raster()`.
 * Retorna `null` se não houver URL ou se algo falhar — a impressão segue sem
 * logo, nunca quebra (o motivo da falha vai para o console).
 */
export async function carregarLogoRaster(
  url: string | null | undefined,
  larguraMaxDots: number,
  opts: Opcoes = {},
): Promise<RasterImage | null> {
  if (!url) return null

  const chave = `${url}@${larguraMaxDots}`
  const emCache = cache.get(chave)
  if (emCache) return emCache

  const limiar = opts.limiar ?? 160
  const alturaMax = opts.alturaMaxDots ?? 240

  try {
    const fonte = await carregarImagem(url)

    // Escala mantendo proporção: cabe na largura da bobina e num teto de altura.
    let escala = Math.min(1, larguraMaxDots / fonte.width)
    if (fonte.height * escala > alturaMax) escala = alturaMax / fonte.height
    const w = Math.max(1, Math.round(fonte.width * escala))
    const h = Math.max(1, Math.round(fonte.height * escala))

    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas 2d indisponível')

    // Fundo branco: transparência (PNG/webp) deve virar papel (branco), não preto.
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(fonte.source, 0, 0, w, h)
    fonte.cleanup?.()

    // getImageData lança SecurityError se o canvas foi contaminado (imagem
    // cross-origin sem CORS) — esse é o sintoma clássico do problema aqui.
    const px = ctx.getImageData(0, 0, w, h).data
    const larguraBytes = Math.ceil(w / 8)
    const data = new Uint8Array(larguraBytes * h)

    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4
        const a = px[i + 3]
        // Alfa 0 = transparente = branco. Senão, luminância perceptual.
        const lum = a === 0 ? 255 : 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
        if (lum < limiar) data[y * larguraBytes + (x >> 3)] |= 0x80 >> (x & 7)
      }
    }

    const raster: RasterImage = { width: w, height: h, data }
    cache.set(chave, raster)
    return raster
  } catch (erro) {
    // Não quebra a impressão: segue sem logo, apenas registra no console.
    console.warn('[Impressão] Não foi possível carregar a logo do cupom:', url, erro)
    return null
  }
}
