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
} from '@/shared/utils/print.utils'
import type { Bobina, RasterImage } from '@/shared/services/escpos'
import type { CompanyPrintInfo } from '@/shared/components/print/print.types'
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema'

export interface OsEscPosOptions {
  bobina: Bobina
  empresa: CompanyPrintInfo
  /** Logo já convertido em bitmap 1-bit; omitido = cupom sem logo. */
  logoRaster?: RasterImage | null
  /** Rótulo do objeto por segmento (ex.: "Veículo", "Equipamento"). Padrão: "Objeto". */
  rotuloObjeto?: string
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
            ? 'OBJETO CONDENADO'
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
  if (os.objeto.numero_serie) b.linha(`N/S: ${os.objeto.numero_serie}`)
  if (os.objeto.cor) b.linha(`Cor: ${os.objeto.cor}`)
  b.separador()

  // Defeito relatado
  b.negrito(true).linha('DEFEITO RELATADO').negrito(false).linha(os.defeito_relatado)

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

    // Itens/serviços
    if (os.itens?.length) {
      b.separador().negrito(true).linha('ITENS/SERVICOS').negrito(false)
      for (const item of os.itens) {
        b.linha(item.nome)
        b.parLados(`${item.quantidade}x ${formatCurrency(item.valor_unitario)}`, formatCurrency(item.valor_total))
      }
    }

    const subTotal = os.itens?.reduce((acc, item) => acc + item.valor_total, 0) ?? 0
    const adiantamento = os.valor_entrada ?? 0
    const adiantamentoUtilizado = Math.min(adiantamento, os.valor_total ?? 0)
    const paymentTotal = os.pagamentos?.reduce((acc, pay) => acc + pay.valor, 0) ?? 0
    const totalRecebido = adiantamentoUtilizado + paymentTotal

    // Adiantamento
    if (adiantamento > 0) {
      b.separador().negrito(true).linha('ADIANTAMENTO (ENTRADA)').negrito(false)
      b.parLados('Recebido na entrada:', formatCurrency(adiantamento))
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

    // Garantia / sem reparo
    if (!isSemReparo && os.garantia) {
      b.separador().negrito(true).linha(`GARANTIA: ${os.garantia}`).negrito(false)
      b.linha('Cobre servicos prestados e pecas substituidas neste documento. Nao cobre mau uso, liquidos, quedas ou intervencao de terceiros.')
    } else if (isSemReparo) {
      b.separador().linha('Objeto devolvido sem reparo. Sem garantia aplicavel a esta OS.')
    }
  } else if (tipo === 'CANCELAMENTO') {
    // CANCELAMENTO: motivo + termo (espelha o OSPrintCupom.vue)
    b.separador()
      .negrito(true)
      .linha('MOTIVO DO CANCELAMENTO')
      .negrito(false)
      .linha(extrairMotivoCancelamento(os.observacoes))
    b.separador()
    b.linha('A OS acima foi cancelada nesta data. Objeto devolvido ao cliente sem reparos ou com reparos parciais, isentando a assistencia de garantias sobre servicos nao concluidos.')
  } else {
    // ENTRADA: termos
    b.separador()
    b.linha('O cliente declara estar ciente que a empresa nao se responsabiliza por perda de dados nem por chips/cartoes deixados no aparelho. Autorizo a analise tecnica do objeto.')
    b.separador()
    b.linha('PRAZO DE RETIRADA: Objetos nao retirados em 90 dias apos aviso de conclusao serao considerados abandonados, conforme Art. 1.275 do Codigo Civil Brasileiro.')
  }

  // Assinaturas — as duas, como na via em papel (lá elas são blocos empilhados,
  // não colunas, então cabem na bobina). Antes só existia a do cliente, e sem
  // o nome embaixo da linha.
  const linhaAssinatura = '_'.repeat(Math.min(28, b.colunas - 4))
  b.pular(2)
    .alinhar('centro')
    .linha(linhaAssinatura)
    .negrito(true)
    .linha('Tecnico Responsavel')
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
