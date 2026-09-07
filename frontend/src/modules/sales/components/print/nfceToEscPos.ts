/**
 * @fileoverview Gerador ESC/POS do DANFE NFC-e (modelo 65)
 *
 * O DANFE NFC-e NÃO é o comprovante de venda com um QR Code no rodapé: é um
 * documento fiscal com layout definido pela SEFAZ, e o que sai nele é o que a
 * lei manda sair. Por isso vive num arquivo separado do `saleToEscPos.ts` —
 * aquele é o comprovante gerencial da loja e pode mudar por gosto; este muda
 * por legislação.
 *
 * O que é obrigatório, e por quê:
 *   - Identificação do emitente (razão social, CNPJ, IE, endereço).
 *   - Discriminação dos itens: código, descrição, quantidade, unidade,
 *     valor unitário e total.
 *   - Tributos aproximados (Lei 12.741/2012 — a Lei da Transparência).
 *   - Chave de acesso de 44 dígitos, legível para digitação manual.
 *   - QR Code e o endereço de consulta da SEFAZ.
 *   - Identificação do consumidor, ou a declaração de que não foi informado.
 */

import { EscPosBuilder } from '@/shared/services/escpos'
import { formatCurrency } from '@/shared/utils/finance'
import { formatCPF, formatCNPJ } from '@/shared/utils/document.utils'
import type { Bobina, RasterImage } from '@/shared/services/escpos'
import type { CompanyPrintInfo } from '@/shared/components/print/print.types'
import { documentoDoCliente } from '../../schemas/customers.schema'
import type { SaleRead } from '../../schemas/sale.schema'
import type { DocumentoFiscalRead } from '@/modules/fiscal/types/fiscal.types'

export interface NfceEscPosOptions {
  bobina: Bobina
  empresa: CompanyPrintInfo
  /** Resolve o nome da forma de pagamento pelo id. */
  resolverPagamento?: (id: number) => string
  abrirGaveta?: boolean
  logoRaster?: RasterImage | null
  /** Segunda via: acrescenta o aviso exigido para reimpressão. */
  reimpressao?: boolean
  /**
   * CPF/CNPJ do consumidor, só dígitos.
   *
   * Vem por fora porque o `SaleRead` não carrega a nota fiscal da venda — quem
   * tem esse dado é quem acabou de emitir (o fechamento do PDV) ou quem
   * reimprime (a central fiscal, a partir da nota).
   */
  documentoConsumidor?: string | null
}

/** Formata a chave de 44 dígitos em blocos de 4, como no manual da SEFAZ. */
export function formatarChaveAcesso(chave: string | null | undefined): string {
  const digitos = (chave ?? '').replace(/\D/g, '')
  if (!digitos) return ''
  return digitos.match(/.{1,4}/g)?.join(' ') ?? digitos
}

/**
 * Quebra a chave em linhas SEM partir um bloco de 4 ao meio.
 *
 * A chave formatada tem 54 caracteres (44 dígitos + 10 espaços) e não cabe em
 * nenhuma bobina: 48 colunas na de 80mm, 32 na de 58mm. Deixar o `linha()`
 * quebrar sozinho produzia coisas como "...3410 987" / "6 5432" — e a chave
 * existe justamente para ser DIGITADA no site da SEFAZ quando o QR Code não
 * lê. Um bloco partido no meio é um erro de digitação esperando acontecer.
 */
export function quebrarChaveEmLinhas(
  chave: string | null | undefined,
  colunas: number,
): string[] {
  const digitos = (chave ?? '').replace(/\D/g, '')
  if (!digitos) return []

  const blocos = digitos.match(/.{1,4}/g) ?? []
  // Cada bloco ocupa 4 caracteres + 1 espaço de separação; a última da linha
  // não precisa do espaço, daí o +1 na conta.
  const porLinha = Math.max(1, Math.floor((colunas + 1) / 5))

  const linhas: string[] = []
  for (let i = 0; i < blocos.length; i += porLinha) {
    linhas.push(blocos.slice(i, i + porLinha).join(' '))
  }
  return linhas
}

/**
 * Mascara o documento do consumidor no cupom.
 *
 * O cupom é papel que fica no balcão, cai no chão e vai para o lixo da loja.
 * Imprimir o CPF inteiro ali entrega o número de quem comprou a quem pegar o
 * papel — e o cupom não precisa dele por extenso: serve para o consumidor
 * reconhecer que a nota é dele.
 */
export function mascararDocumentoConsumidor(documento: string | null | undefined): string {
  const digitos = (documento ?? '').replace(/\D/g, '')

  if (digitos.length === 11) {
    const formatado = formatCPF(digitos)          // 123.456.789-00
    return `CPF ${formatado.slice(0, 4)}***.***-${digitos.slice(-2)}`
  }
  if (digitos.length === 14) {
    const formatado = formatCNPJ(digitos)         // 12.345.678/0001-90
    return `CNPJ ${formatado.slice(0, 3)}***.***/${digitos.slice(8, 12)}-${digitos.slice(-2)}`
  }
  return ''
}

/** Trunca a descrição para caber ao lado dos números, sem estourar a coluna. */
function encurtar(texto: string, limite: number): string {
  const limpo = (texto ?? '').trim()
  return limpo.length <= limite ? limpo : `${limpo.slice(0, limite - 1)}.`
}

export function nfceToEscPos(
  sale: SaleRead,
  documento: DocumentoFiscalRead,
  opts: NfceEscPosOptions,
): Uint8Array {
  const b = new EscPosBuilder(opts.bobina)
  const { empresa } = opts
  const largo = b.colunas >= 48

  // ── Emitente ────────────────────────────────────────────────────────────
  b.alinhar('centro')
  if (opts.logoRaster) b.raster(opts.logoRaster).pular()

  b.negrito(true).linha(encurtar(empresa.razaoSocial || empresa.nome, b.colunas)).negrito(false)
  if (empresa.cnpj) {
    // Na 58mm o CNPJ e a IE juntos não cabem, e o `linha()` quebraria no meio
    // da IE. Duas linhas são melhores que uma IE partida ao meio.
    const cnpj = `CNPJ: ${empresa.cnpj}`
    const ie = empresa.inscricaoEstadual ? `IE: ${empresa.inscricaoEstadual}` : ''
    if (ie && cnpj.length + ie.length + 2 <= b.colunas) {
      b.linha(`${cnpj}  ${ie}`)
    } else {
      b.linha(cnpj)
      if (ie) b.linha(ie)
    }
  }
  if (empresa.enderecoLinha1) b.linha(encurtar(empresa.enderecoLinha1, b.colunas))
  if (empresa.enderecoLinha2) b.linha(encurtar(empresa.enderecoLinha2, b.colunas))

  // ── Título legal ────────────────────────────────────────────────────────
  b.separador()
    .negrito(true)
    .linha('DANFE NFC-e')
    .negrito(false)
  if (largo) {
    b.linha('Documento Auxiliar da Nota Fiscal')
      .linha('de Consumidor Eletronica')
  } else {
    // 'Documento Auxiliar da Nota Fiscal' tem 33 caracteres e estoura as 32
    // colunas da 58mm, quebrando num 'l' sozinho na linha seguinte.
    b.linha('Doc. Auxiliar da NFC-e')
  }
  b.separador()

  // ── Itens ───────────────────────────────────────────────────────────────
  // Cabeçalho só na 80mm: na 58mm ele não cabe sem comer a descrição, e o
  // manual da SEFAZ permite a versão reduzida.
  b.alinhar('esq')
  if (largo) {
    b.linha('# COD  DESCRICAO        QTD UN  VL UN   TOTAL')
  }

  let quantidadeItens = 0
  for (const [indice, item] of (sale.produtos ?? []).entries()) {
    quantidadeItens += 1
    const numero = String(indice + 1).padStart(3, '0')
    // O SKU é o código que o lojista reconhece na etiqueta; o id interno não
    // significa nada para quem confere o cupom no balcão.
    const codigo = encurtar(item.sku || String(item.produto_id ?? ''), 6)

    b.linha(`${numero} ${codigo} ${encurtar(item.nome, b.colunas - 11)}`)
    b.parLados(
      `    ${item.quantidade} x ${formatCurrency(item.valor_unitario)}`,
      formatCurrency(item.total),
    )
    if (item.desconto > 0) {
      b.parLados('    Desconto', `-${formatCurrency(item.desconto)}`)
    }
  }

  // ── Totais ──────────────────────────────────────────────────────────────
  b.separador()
    .parLados('QTD. TOTAL DE ITENS', String(quantidadeItens))
  if (sale.descontos > 0) b.parLados('Descontos', `-${formatCurrency(sale.descontos)}`)
  b.negrito(true)
    .parLados('VALOR TOTAL R$', formatCurrency(sale.total))
    .negrito(false)

  // ── Pagamentos ──────────────────────────────────────────────────────────
  for (const pagamento of sale.pagamentos ?? []) {
    const nome = opts.resolverPagamento?.(pagamento.forma_pagamento_id) ?? 'Pagamento'
    b.parLados(`FORMA PGTO (${encurtar(nome, 14)})`, formatCurrency(pagamento.valor))
  }
  if (sale.troco > 0) b.parLados('TROCO', formatCurrency(sale.troco))

  // ── Tributos (Lei 12.741/2012) ──────────────────────────────────────────
  // Sai só quando temos o número. Imprimir "R$ 0,00" quando o valor não veio
  // seria informar ao consumidor que ele não pagou tributo — pior que omitir.
  if (documento.valor_tributos !== null && documento.valor_tributos !== undefined) {
    b.separador()
      .linha('Tributos Totais Incidentes')
      .parLados('(Lei 12.741/2012 - IBPT)', formatCurrency(documento.valor_tributos))
  }

  // ── Identificação do documento ──────────────────────────────────────────
  b.separador().alinhar('centro')

  if (documento.ambiente_emissao === 2) {
    // 'EMITIDA EM AMBIENTE DE HOMOLOGACAO' tem 34 caracteres e, na 58mm,
    // quebrava dentro da própria palavra HOMOLOGACAO — justamente o aviso que
    // aparta um cupom de treino de um documento fiscal de verdade.
    b.negrito(true)
    if (largo) {
      b.linha('EMITIDA EM AMBIENTE DE HOMOLOGACAO')
    } else {
      b.linha('HOMOLOGACAO')
    }
    b.linha('SEM VALOR FISCAL').negrito(false)
  } else {
    b.linha('EMISSAO NORMAL')
  }

  const emissao = documento.data_autorizacao ?? documento.data_emissao
  b.linha(
    `Numero: ${String(documento.numero_documento ?? '').padStart(9, '0')}`
    + `  Serie: ${String(documento.serie ?? '').padStart(3, '0')}`,
  )
  if (emissao) b.linha(new Date(emissao).toLocaleString('pt-BR'))
  if (documento.protocolo_autorizacao) {
    b.linha(`Protocolo: ${documento.protocolo_autorizacao}`)
  }

  // ── Chave de acesso ─────────────────────────────────────────────────────
  // Em blocos de 4 porque é assim que o consumidor a digita no site da SEFAZ
  // quando o QR Code não lê — e num cupom térmico desbotado isso acontece.
  if (documento.chave_acesso) {
    b.pular()
      .negrito(true)
      .linha('CHAVE DE ACESSO')
      .negrito(false)
    for (const parte of quebrarChaveEmLinhas(documento.chave_acesso, b.colunas)) {
      b.linha(parte)
    }
  }

  // ── Consumidor ──────────────────────────────────────────────────────────
  b.pular()
  // Mesma precedência do backend (`_documento_do_consumidor`): o cadastro do
  // cliente vence o digitado no caixa, porque foi conferido.
  const consumidor = mascararDocumentoConsumidor(
    documentoDoCliente(sale.cliente) || opts.documentoConsumidor,
  )
  b.linha(consumidor ? `CONSUMIDOR: ${consumidor}` : 'CONSUMIDOR NAO IDENTIFICADO')

  // ── QR Code ─────────────────────────────────────────────────────────────
  // Pelo comando nativo da impressora: é o caminho que não depende de
  // rasterizar imagem, e um QR ilegível invalida o cupom na prática.
  if (documento.qrcode) {
    b.pular().qrCode(documento.qrcode, { correcao: 'M' }).pular()
  }
  if (documento.url_consulta) {
    // A URL NÃO pode ser truncada: truncada ela não abre, e é o caminho de
    // quem digita a chave à mão. O `linha()` quebra em várias linhas sozinho.
    b.linha(largo ? 'Consulte pela Chave de Acesso em:' : 'Consulte a chave em:')
      .linha(documento.url_consulta)
  }

  if (opts.reimpressao) {
    b.pular().negrito(true).linha('*** SEGUNDA VIA ***').negrito(false)
  }

  if (opts.abrirGaveta) b.pulsoGaveta()
  b.cortar()
  return b.build()
}
