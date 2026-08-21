import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { toast } from 'vue-sonner'
import { getConfiguracoesClientes, getConfiguracoesProdutos, getConfiguracoesOS, getConfiguracoesVendas, getConfiguracoesSeguranca } from '@/modules/configuracoes/services/configuracoes.service'
import type { ConfiguracaoClientesRead, ConfiguracaoProdutosRead, ConfiguracaoOSRead, ConfiguracaoVendasRead, ConfiguracaoSegurancaRead } from '@/modules/configuracoes/schemas/configuracoes.schema'

export const useConfiguracoesStore = defineStore('configuracoes', () => {
  const configClientes = ref<ConfiguracaoClientesRead | null>(null)
  const configProdutos = ref<ConfiguracaoProdutosRead | null>(null)
  const configOS = ref<ConfiguracaoOSRead | null>(null)
  const configVendas = ref<ConfiguracaoVendasRead | null>(null)
  const configSeguranca = ref<ConfiguracaoSegurancaRead | null>(null)

  async function carregarConfiguracoes() {
    // allSettled: a falha de uma requisição não descarta as demais —
    // cada config que carregar com sucesso é aplicada individualmente
    const [clientes, produtos, os, vendas, seguranca] = await Promise.allSettled([
      getConfiguracoesClientes(),
      getConfiguracoesProdutos(),
      getConfiguracoesOS(),
      getConfiguracoesVendas(),
      getConfiguracoesSeguranca(),
    ])

    if (clientes.status === 'fulfilled') configClientes.value = clientes.value
    if (produtos.status === 'fulfilled') configProdutos.value = produtos.value
    if (os.status === 'fulfilled') configOS.value = os.value
    if (vendas.status === 'fulfilled') configVendas.value = vendas.value
    if (seguranca.status === 'fulfilled') configSeguranca.value = seguranca.value

    const falhas = [clientes, produtos, os, vendas, seguranca].filter((r) => r.status === 'rejected')
    if (falhas.length > 0) {
      console.error('[Configurações] Falha ao carregar:', falhas.map((f) => (f as PromiseRejectedResult).reason))
      toast.warning('Não foi possível carregar todas as configurações', {
        description: 'O sistema pode exibir valores padrão. Verifique a conexão e tente novamente.',
      })
    }
  }

  // ── Clientes: campos obrigatórios ──
  const exigirCpfPf = computed(() => configClientes.value?.exigir_cpf_pf ?? false)
  const exigirCnpjPj = computed(() => configClientes.value?.exigir_cnpj_pj ?? false)
  const exigirCelular = computed(() => configClientes.value?.exigir_celular ?? true)
  const exigirRgPf = computed(() => configClientes.value?.exigir_rg_pf ?? false)
  const exigirIePj = computed(() => configClientes.value?.exigir_ie_pj ?? false)
  const exigirEmail = computed(() => configClientes.value?.exigir_email ?? false)
  const exigirEndereco = computed(() => configClientes.value?.exigir_endereco ?? false)

  // ── Clientes: exibição do formulário ──
  const tipoPessoaPadrao = computed(() => configClientes.value?.tipo_pessoa_padrao ?? 'PF')
  const exibirGenero = computed(() => configClientes.value?.exibir_genero ?? true)
  const exibirDataNascimento = computed(() => configClientes.value?.exibir_data_nascimento ?? true)

  // ── Clientes: comportamento ──
  const bloquearFaturamentoInativo = computed(() => configClientes.value?.bloquear_faturamento_inativo ?? false)
  const oferecerReativacaoRapida = computed(() => configClientes.value?.oferecer_reativacao_rapida ?? false)

  // ── Clientes: controle financeiro ──
  const ativarLimiteCredito = computed(() => configClientes.value?.ativar_limite_credito ?? false)
  const bloquearVendaLimite = computed(() => configClientes.value?.bloquear_venda_limite ?? false)

  // ── Produtos: campos obrigatórios no cadastro ──
  const exigirCodigoBarras = computed(() => configProdutos.value?.exigir_codigo_barras ?? false)
  const exigirCategoria = computed(() => configProdutos.value?.exigir_categoria ?? false)
  const exigirPrecoCusto = computed(() => configProdutos.value?.exigir_preco_custo ?? false)

  // ── Produtos: preços e exibição ──
  const margemLucroPadrao = computed(() => configProdutos.value?.margem_lucro_padrao ?? 0)
  const utilizarPrecoAtacado = computed(() => configProdutos.value?.utilizar_preco_atacado ?? true)

  // ── Produtos: controle de estoque ──
  // O padrão acompanha o do banco (`configuracao_produtos.permitir_venda_estoque_zerado`,
  // default=True). Assumir `false` aqui fazia a tela ser mais restritiva que o
  // servidor enquanto a configuração da empresa ainda não existisse — e recusar
  // uma venda que o backend teria aceitado.
  const permitirVendaEstoqueZerado = computed(() => configProdutos.value?.permitir_venda_estoque_zerado ?? true)
  const quantidadeMinimaPadrao = computed(() => configProdutos.value?.quantidade_minima_padrao ?? 5)
  const unidadeMedidaPadrao = computed(() => configProdutos.value?.unidade_medida_padrao ?? 'UN')

  // ── OS: prazos e padrões ──
  const prazoEntregaPadrao = computed(() => configOS.value?.prazo_entrega_padrao ?? 7)
  const garantiaPadrao = computed(() => configOS.value?.garantia_padrao ?? '90 dias')
  const prazoAbandonoDias = computed(() => configOS.value?.prazo_abandono_dias ?? 90)
  const taxaDiagnosticoPadrao = computed(() => configOS.value?.taxa_diagnostico_padrao ?? 0)

  // ── OS: apresentação dos comprovantes (só a FORMA; conteúdo é invariante) ──
  const comprovanteEntradaFolha = computed(() => configOS.value?.comprovante_entrada_folha ?? 'A4')
  const comprovanteEntradaDensidade = computed(() => configOS.value?.comprovante_entrada_densidade ?? 'normal')
  const comprovanteEntregaFolha = computed(() => configOS.value?.comprovante_entrega_folha ?? 'A4')
  const comprovanteEntregaDensidade = computed(() => configOS.value?.comprovante_entrega_densidade ?? 'normal')

  // ── Vendas: regras ──
  const permitirDesconto = computed(() => configVendas.value?.permitir_desconto ?? true)
  const descontoMaximoPercent = computed(() => configVendas.value?.desconto_maximo_percent ?? 30)
  const exigirClienteIdentificado = computed(() => configVendas.value?.exigir_cliente_identificado ?? false)
  const valorMinimoVenda = computed(() => configVendas.value?.valor_minimo_venda ?? 0)
  const permitirParcelamento = computed(() => configVendas.value?.permitir_parcelamento ?? true)
  const parcelasMaximas = computed(() => configVendas.value?.parcelas_maximas ?? 12)

  // Controle de caixa. Os padrões repetem o comportamento de hoje de propósito:
  // enquanto a loja não ligar nada, tudo se comporta como antes de existirem.
  const controlarCaixa = computed(() => configVendas.value?.controlar_caixa ?? false)
  const exigirCaixaAberto = computed(() => configVendas.value?.exigir_caixa_aberto ?? false)
  const fechamentoCego = computed(() => configVendas.value?.fechamento_cego ?? false)
  // Mora na config de VENDAS, e não junto dos PINs de Segurança: é regra do
  // caixa e o dono a quis no bloco do caixa. O segredo conferido continua
  // sendo o `pin_gerente` de Segurança — a chave é que mudou de casa.
  const requerPinAbrirCaixa = computed(() => configVendas.value?.requer_pin_abrir_caixa ?? false)
  // A fila do caixa e separada de `controlarCaixa`: controlar a gaveta e uma
  // pergunta, ter gente diferente montando e recebendo e outra. Loja de um PC
  // so responde nao a segunda.
  const usarFilaDoCaixa = computed(() => configVendas.value?.usar_fila_do_caixa ?? false)

  // ── Segurança: PINs ──
  const requerPinDescontoVenda = computed(() => configSeguranca.value?.requer_pin_desconto_venda ?? false)
  const requerPinAlterarPreco = computed(() => configSeguranca.value?.requer_pin_alterar_preco_venda ?? false)
  const requerPinSangria = computed(() => configSeguranca.value?.requer_pin_sangria ?? false)
  const requerPinCancelarVenda = computed(() => configSeguranca.value?.requer_pin_cancelar_venda ?? false)
  const requerPinReabrirVenda = computed(() => configSeguranca.value?.requer_pin_reabrir_venda ?? false)
  const requerPinCancelarOS = computed(() => configSeguranca.value?.requer_pin_cancelar_os ?? false)
  const requerPinReabrirOS = computed(() => configSeguranca.value?.requer_pin_reabrir_os ?? false)
  const secoesProtegidas = computed<string[]>(() => configSeguranca.value?.secoes_protegidas ?? [])
  const temPinConfigurado = computed(() => configSeguranca.value?.tem_pin_configurado ?? false)

  return {
    configClientes,
    configProdutos,
    configOS,
    configVendas,
    configSeguranca,
    carregarConfiguracoes,

    exigirCpfPf,
    exigirCnpjPj,
    exigirCelular,
    exigirRgPf,
    exigirIePj,
    exigirEmail,
    exigirEndereco,

    tipoPessoaPadrao,
    exibirGenero,
    exibirDataNascimento,

    bloquearFaturamentoInativo,
    oferecerReativacaoRapida,

    ativarLimiteCredito,
    bloquearVendaLimite,

    exigirCodigoBarras,
    exigirCategoria,
    exigirPrecoCusto,

    margemLucroPadrao,
    utilizarPrecoAtacado,

    permitirVendaEstoqueZerado,
    quantidadeMinimaPadrao,
    unidadeMedidaPadrao,

    prazoEntregaPadrao,
    garantiaPadrao,
    prazoAbandonoDias,
    taxaDiagnosticoPadrao,

    comprovanteEntradaFolha,
    comprovanteEntradaDensidade,
    comprovanteEntregaFolha,
    comprovanteEntregaDensidade,

    permitirDesconto,
    descontoMaximoPercent,
    exigirClienteIdentificado,
    valorMinimoVenda,
    permitirParcelamento,
    parcelasMaximas,
    controlarCaixa,
    exigirCaixaAberto,
    fechamentoCego,
    requerPinAbrirCaixa,
    usarFilaDoCaixa,

    requerPinDescontoVenda,
    requerPinAlterarPreco,
    requerPinSangria,
    requerPinCancelarVenda,
    requerPinReabrirVenda,
    requerPinCancelarOS,
    requerPinReabrirOS,
    secoesProtegidas,
    temPinConfigurado,
  }
})
