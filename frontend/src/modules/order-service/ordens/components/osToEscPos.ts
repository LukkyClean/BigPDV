/**
 * @fileoverview Gerador ESC/POS do cupom de Ordem de Serviço
 * @description Espelha o conteúdo do OSPrintCupom.vue (entrada/saída) em
 * comandos ESC/POS para impressão térmica direta (silenciosa).
 */

import { EscPosBuilder } from '@/shared/services/escpos'
import { formatCurrency } from '@/shared/utils/finance'
import {
  getClienteNome,
  getClienteDoc,
  getClientePhone,
  getClienteEndereco,
  getPaymentDisplayName,
  formatPrintDate,
  formatPrintDoc,
  tipoObjetoRelevante,
  pixParaImpressao,
} from '@/shared/utils/print.utils'
import type { Bobina, RasterImage } from '@/shared/services/escpos'
import type { CompanyPrintInfo } from '@/shared/components/print/print.types'
import type { TextosCupomOS } from '@/modules/order-service/shared/segmento/textosImpressaoOS'
import type { AtributoImpresso } from '@/modules/order-service/shared/segmento/useAtributosImpressaoOS'
import { formatGarantiaItem } from '@/modules/order-service/shared/utils/formatters'
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema'

/**
 * Termos usados quando o chamador não passa `textos`. São os da assistência
 * técnica, palavra por palavra — quem não informar o segmento continua
 * imprimindo o que sempre imprimiu.
 */
const TEXTOS_PADRAO: TextosCupomOS = {
  objeto: 'Objeto',
  identificador: 'N/S',
  defeito: 'DEFEITO RELATADO',
  assinaturaLoja: 'Tecnico Responsavel',
  garantiaExclusoes: 'mau uso, liquidos, quedas ou intervencao de terceiros.',
  semReparo: 'Objeto devolvido sem reparo. Sem garantia aplicavel a esta OS.',
  cancelamento:
    'A OS acima foi cancelada nesta data. Objeto devolvido ao cliente sem reparos ou com reparos '
    + 'parciais, isentando a assistencia de garantias sobre servicos nao concluidos.',
  condicoesEntrada:
    'O cliente declara estar ciente que a empresa nao se responsabiliza por perda de dados nem por '
    + 'chips/cartoes deixados no aparelho. Autorizo a analise tecnica do objeto.',
  prazoRetirada: (dias) =>
    `PRAZO DE RETIRADA: Objetos nao retirados em ${dias} dias apos aviso de conclusao serao `
    + 'considerados abandonados, conforme Art. 1.275 do Codigo Civil Brasileiro.',
}

/** Espelha o default de `configuracoes_os.prazo_abandono_dias` no backend. */
const PRAZO_ABANDONO_PADRAO = 90

export interface OsEscPosOptions {
  bobina: Bobina
  empresa: CompanyPrintInfo
  /** Logo já convertido em bitmap 1-bit; omitido = cupom sem logo. */
  logoRaster?: RasterImage | null
  /** Rótulo do objeto por segmento (ex.: "Veículo", "Equipamento"). Padrão: "Objeto". */
  rotuloObjeto?: string
  /** Rótulo do identificador (ex.: "Placa"). Padrão: "N/S". */
  rotuloIdentificador?: string
  /** Termos jurídicos do segmento. Padrão: os da assistência técnica. */
  textos?: TextosCupomOS
  /** `configuracoes_os.prazo_abandono_dias` da loja. Padrão: 90. */
  prazoAbandonoDias?: number
  /** Atributos extras do objeto (oficina: Ano, Chassi, KM). Padrão: nenhum. */
  atributos?: AtributoImpresso[]
}

/**
 * Motivo do cancelamento — não é coluna: fica embutido em `observacoes` com o
 * prefixo [CANCELAMENTO]. Mesma extração do OSPrintCupom.vue, para as duas vias
 * dizerem a mesma coisa.
 */
function extrairMotivoCancelamento(observacoes: string | null | undefined): string {
  const match = (observacoes ?? '').match(/\[CANCELAMENTO\]\s*([\s\S]+)/)
  return match ? match[1].trim() : 'Motivo nao informado.'
}

export function osToEscPos(
  os: OrderServiceReadDataType,
  tipo: 'ENTRADA' | 'SAIDA' | 'CANCELAMENTO',
  opts: OsEscPosOptions,
): Uint8Array {
  const b = new EscPosBuilder(opts.bobina)
  const { empresa } = opts
  const t = opts.textos ?? TEXTOS_PADRAO

  const situacao = os.situacao_equipamento ?? null
  const isSemReparo = situacao === 'SEM_REPARO' || situacao === 'CONDENADO'

  const titulo =
    tipo === 'ENTRADA'
      ? 'COMPROVANTE DE ENTRADA'
      : tipo === 'CANCELAMENTO'
        ? 'CANCELAMENTO DE OS'
        : situacao === 'SEM_REPARO'
          ? 'ENTREGA SEM REPARO'
          : situacao === 'CONDENADO'
            ? `${t.objeto.toUpperCase()} CONDENADO`
            : 'RECIBO E GARANTIA'

  const dataStr = tipo === 'SAIDA' ? ((os.data_finalizacao as string) || os.data_criacao) : os.data_criacao

  // Cabeçalho da empresa
  b.alinhar('centro')
  if (opts.logoRaster) b.raster(opts.logoRaster).pular()
  b.tamanhoDuplo(true)
    .linha(empresa.nome.toUpperCase())
    .tamanhoDuplo(false)
  if (empresa.cnpj) b.linha(empresa.cnpj)
  if (empresa.enderecoLinha1) b.linha(empresa.enderecoLinha1)
  if (empresa.enderecoLinha2) b.linha(empresa.enderecoLinha2)
  if (empresa.contato) b.linha(`TEL: ${empresa.contato}`)

  b.separador().negrito(true).linha(titulo).negrito(false).separador()

  // Identificação
  b.alinhar('esq')
    .negrito(true)
    .linha(`OS: ${os.numero_os}`)
    .negrito(false)
    .linha(`Data: ${formatPrintDate(dataStr)}`)
    .separador()

  // Cliente
  b.negrito(true).linha('CLIENTE').negrito(false)
  b.linha(getClienteNome(os.cliente))
  const doc = getClienteDoc(os.cliente)
  if (doc) b.linha(`Doc: ${formatPrintDoc(doc)}`)
  const tel = getClientePhone(os.cliente)
  if (tel) b.linha(`Tel: ${tel}`)
  const endCli = getClienteEndereco(os.cliente)
  if (endCli) b.linha(endCli)
  b.separador()

  // Objeto — título por segmento (Veículo/Equipamento/...), cai em "OBJETO"
  b.negrito(true).linha((opts.rotuloObjeto || 'Objeto').toUpperCase()).negrito(false)
  // Em MAIÚSCULA para bater com a via em papel: lá o mesmo texto sai com a
  // classe `uppercase`, então imprimia "(REPARADO)" enquanto a térmica saía
  // "(Reparado)" — mesmo documento, duas grafias.
  const sufixoSituacao =
    tipo === 'SAIDA' && situacao
      ? ` (${(situacao === 'REPARADO' ? 'Reparado' : situacao === 'SEM_REPARO' ? 'Sem Reparo' : 'Condenado').toUpperCase()})`
      : ''
  // O "tipo" só sai quando acrescenta info (informática: "COMPUTADOR"). Em oficina
  // ele é o próprio rótulo ("Veículo") e repetir sob o cabeçalho "VEÍCULO" é redundante.
  if (tipoObjetoRelevante(os.objeto.tipo_equipamento, opts.rotuloObjeto)) {
    b.linha(`${os.objeto.tipo_equipamento}${sufixoSituacao}`)
  } else if (sufixoSituacao) {
    b.linha(sufixoSituacao.trim())
  }
  if (os.objeto.marca) b.linha(`Marca: ${os.objeto.marca}`)
  if (os.objeto.modelo) b.linha(`Modelo: ${os.objeto.modelo}`)
  if (os.objeto.numero_serie) {
    b.linha(`${opts.rotuloIdentificador || t.identificador || 'N/S'}: ${os.objeto.numero_serie}`)
  }
  if (os.objeto.cor) b.linha(`Cor: ${os.objeto.cor}`)
  // Atributos do segmento (oficina: Ano, Chassi, KM de entrada) — a via térmica
  // tem que dizer o mesmo que o papel.
  for (const attr of opts.atributos ?? []) b.linha(`${attr.label}: ${attr.valor}`)
  b.separador()

  // Defeito relatado
  b.negrito(true).linha(t.defeito).negrito(false).linha(os.defeito_relatado)

  // Observações
  if (os.observacoes) {
    b.separador().negrito(true).linha('OBSERVACOES').negrito(false).linha(os.observacoes)
  }

  if (tipo === 'SAIDA') {
    // Laudo técnico
    if (os.diagnostico || os.solucao) {
      b.separador().negrito(true).linha('LAUDO TECNICO').negrito(false)
      if (os.diagnostico) b.linha(`Diag: ${os.diagnostico}`)
      if (os.solucao) b.linha(`Solucao: ${os.solucao}`)
    }

    // Itens/serviços — peça embutida no serviço não é listada para o cliente.
    // `!== false` e não `=== true`: item antigo vem sem o campo e tem que
    // continuar aparecendo, exatamente como sempre apareceu.
    // Item REPROVADO fora, pelo mesmo motivo da via em papel: não foi feito e o
    // backend já o tira do total, então listá-lo quebrava a soma do cupom.
    const itensVisiveis = (os.itens ?? []).filter(
      (item) => item.visivel_cliente !== false && item.status_aprovacao !== 'REPROVADO',
    )
    if (itensVisiveis.length) {
      b.separador().negrito(true).linha('ITENS/SERVICOS').negrito(false)
      for (const item of itensVisiveis) {
        b.linha(item.nome)
        // Garantia da peça: só sai quando o mecânico preencheu.
        const garantiaItem = formatGarantiaItem(item)
        if (garantiaItem) b.linha(`Garantia: ${garantiaItem}`)
        b.parLados(`${item.quantidade}x ${formatCurrency(item.valor_unitario)}`, formatCurrency(item.valor_total))
      }
    }

    const subTotal = itensVisiveis.reduce((acc, item) => acc + item.valor_total, 0)
    const adiantamento = os.valor_entrada ?? 0
    const adiantamentoUtilizado = Math.min(adiantamento, os.valor_total ?? 0)
    const paymentTotal = os.pagamentos?.reduce((acc, pay) => acc + pay.valor, 0) ?? 0
    const totalRecebido = adiantamentoUtilizado + paymentTotal

    // Adiantamento
    if (adiantamento > 0) {
      b.separador().negrito(true).linha('ADIANTAMENTO (ENTRADA)').negrito(false)
      b.parLados('Recebido na entrada:', formatCurrency(adiantamento))
      // Ausente em OS anterior a este campo: a via sai como saía antes.
      const formaEntrada = os.forma_pagamento_entrada?.nome
      if (formaEntrada) b.parLados('Forma:', formaEntrada)
    }

    // Pagamentos no fechamento
    if (os.pagamentos?.length) {
      b.separador().negrito(true).linha('PAGAMENTOS').negrito(false)
      for (const pgto of os.pagamentos) {
        const nome = getPaymentDisplayName(pgto.forma_pagamento?.nome || 'Pagamento')
        const parcelas = pgto.parcelas > 1 ? ` (${pgto.parcelas}x)` : ''
        b.parLados(`${nome}${parcelas}`, formatCurrency(pgto.valor))
      }
    }

    // Totais
    b.separador()
    b.parLados('Subtotal:', formatCurrency(subTotal))
    if ((os.desconto ?? 0) > 0) b.parLados('Desconto:', `-${formatCurrency(os.desconto ?? 0)}`)
    if ((os.taxa_entrega ?? 0) > 0) b.parLados('Deslocamento:', `+${formatCurrency(os.taxa_entrega ?? 0)}`)
    if ((os.acrescimo ?? 0) > 0) b.parLados('Juros:', `+${formatCurrency(os.acrescimo ?? 0)}`)
    if (adiantamento > 0) b.parLados('Adiantamento:', `-${formatCurrency(adiantamentoUtilizado)}`)
    b.negrito(true).parLados('TOTAL PAGO:', formatCurrency(totalRecebido)).negrito(false)

    // Devolução (quando há juros): faltava aqui e existia só na via em papel,
    // então a mesma OS saía com a quebra do estorno num comprovante e sem ela
    // no outro. Espelha o bloco do OSPrintCupom.vue.
    if ((os.acrescimo ?? 0) > 0) {
      b.separador().negrito(true).linha('DEVOLUCAO').negrito(false)
      b.parLados('Servico (dinheiro):', formatCurrency(paymentTotal - (os.acrescimo ?? 0)))
      b.parLados('Estorno cartao:', formatCurrency(paymentTotal))
    }

    // PIX: QR pago pelo papel, com o valor só da parte paga em PIX. O número da
    // OS vai como txid — é o que amarra a cobrança ao documento no extrato.
    const pix = pixParaImpressao({
      empresa,
      pagamentos: os.pagamentos?.map((p) => ({
        nome: p.forma_pagamento?.nome || '',
        valor: p.valor,
      })),
      txid: os.numero_os ?? undefined,
    })
    if (pix) {
      b.separador()
        .alinhar('centro')
        .negrito(true)
        .linha('PAGUE COM PIX')
        .negrito(false)
        .linha(`Valor: ${formatCurrency(pix.valorCentavos)}`)
        .pular()
        .qrCode(pix.payload)
        .pular()
        .linha('Aponte a camera do celular')
        .alinhar('esq')
    }

    // Garantia / sem reparo
    if (!isSemReparo && os.garantia) {
      // Com garantia por item, o termo geral cede a vez: dizer que cobre as
      // peças contradiria a linha do item, que declara outro prazo.
      const ressalva = itensVisiveis.some((item) => formatGarantiaItem(item) !== '')
        ? ', exceto onde houver garantia indicada na linha do item'
        : ''
      b.separador().negrito(true).linha(`GARANTIA: ${os.garantia}`).negrito(false)
      b.linha(`Cobre servicos prestados e pecas substituidas neste documento${ressalva}. Nao cobre ${t.garantiaExclusoes}`)
    } else if (isSemReparo) {
      b.separador().linha(t.semReparo)
    }
  } else if (tipo === 'CANCELAMENTO') {
    // CANCELAMENTO: motivo + termo (espelha o OSPrintCupom.vue)
    b.separador()
      .negrito(true)
      .linha('MOTIVO DO CANCELAMENTO')
      .negrito(false)
      .linha(extrairMotivoCancelamento(os.observacoes))
    b.separador()
    b.linha(t.cancelamento)
  } else {
    // ENTRADA: termos
    b.separador()
    b.linha(t.condicoesEntrada)
    b.separador()
    b.linha(t.prazoRetirada(opts.prazoAbandonoDias ?? PRAZO_ABANDONO_PADRAO))
  }

  // Assinaturas — as duas, como na via em papel (lá elas são blocos empilhados,
  // não colunas, então cabem na bobina). Antes só existia a do cliente, e sem
  // o nome embaixo da linha.
  const linhaAssinatura = '_'.repeat(Math.min(28, b.colunas - 4))
  b.pular(2)
    .alinhar('centro')
    .linha(linhaAssinatura)
    .negrito(true)
    .linha(t.assinaturaLoja)
    .negrito(false)
    .pular(2)
    .linha(linhaAssinatura)
    .negrito(true)
    .linha('Assinatura do Cliente')
    .negrito(false)
  if (os.cliente) b.linha(getClienteNome(os.cliente))

  // Rodapé
  b.separador()
    .linha(new Date().toLocaleString('pt-BR'))
    .negrito(true)
    .linha('SISTEMA STARTBIG')
    .negrito(false)

  b.cortar()
  return b.build()
}
