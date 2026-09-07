# ---------------------------------------------------------------------------
# ARQUIVO: enum.py
# DESCRIÇÃO: Centraliza todas as classes Enum da aplicação para garantir
#            consistência e reutilização de tipos de dados fixos.
# ---------------------------------------------------------------------------

import enum

class Gender(enum.Enum):
    """Define os gêneros possíveis para usuários ou clientes."""
    MASCULINO = "MASCULINO"
    FEMININO = "FEMININO"
    OUTRO = "OUTRO"

class ClientType(str, enum.Enum):
    """Define os tipos de cliente (Pessoa Física ou Jurídica)."""
    # Herda de `str` para que os valores possam ser usados diretamente como strings (ex: em Pydantic)
    PF = "PF"
    PJ = "PJ"

class State(str, enum.Enum):
    """Define as siglas dos estados brasileiros (UF)."""
    # Lista abrangente das siglas estaduais.
    ACRE = "AC"
    ALAGOAS = "AL"
    AMAPA = "AP"
    AMAZONAS = "AM"
    BAHIA = "BA"
    CEARA = "CE"
    DISTRITO_FEDERAL = "DF"
    ESPIRITO_SANTO = "ES"
    GOIAS = "GO"
    MARANHAO = "MA"
    MATO_GROSSO = "MT"
    MATO_GROSSO_DO_SUL = "MS"
    MINAS_GERAIS = "MG"
    PARA = "PA"
    PARAIBA = "PB"
    PARANA = "PR"
    PERNAMBUCO = "PE"
    PIAUI = "PI"
    RIO_DE_JANEIRO = "RJ"
    RIO_GRANDE_DO_NORTE = "RN"
    RIO_GRANDE_DO_SUL = "RS"
    RONDONIA = "RO"
    RORAIMA = "RR"
    SANTA_CATARINA = "SC"
    SAO_PAULO = "SP"
    SERGIPE = "SE"
    TOCANTINS = "TO"

class EntityType(str, enum.Enum):
    """
    Define os tipos de entidades polimórficas no sistema.
    
    Essencial para o relacionamento polimórfico de Endereços
    (ex: Endereço pode pertencer a um Cliente, Fornecedor, Funcionário ou Empresa).
    """
    CLIENTE = "CLIENTE"
    FORNECEDOR = "FORNECEDOR"
    FUNCIONARIO = "FUNCIONARIO"
    EMPRESA = "EMPRESA"

class BankAccountType(str, enum.Enum):
    POUPANCA = "POUPANCA"
    CORRENTE = "CORRENTE"

class OrdemServicoStatus(str, enum.Enum):
    """Status possíveis de uma Ordem de Serviço."""
    ABERTA = "ABERTA"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    AGUARDANDO_PECAS = "AGUARDANDO_PECAS"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"

class OrdemServicoPrioridade(str, enum.Enum):
    """Prioridades possíveis de uma Ordem de Serviço."""
    BAIXA = "BAIXA"
    NORMAL = "NORMAL"
    ALTA = "ALTA"
    URGENTE = "URGENTE"

class SituacaoEquipamento(str, enum.Enum):
    """Situação final do equipamento ao finalizar a OS."""
    REPARADO = "REPARADO"
    SEM_REPARO = "SEM_REPARO"
    CONDENADO = "CONDENADO"

class OrdemServicoItemTipo(str, enum.Enum):
    PRODUTO = "PRODUTO"
    SERVICO = "SERVICO"

class OrdemServicoItemAprovacao(str, enum.Enum):
    """Status de aprovação de um item da OS (usado no fluxo de orçamento).

    Default APROVADO preserva o comportamento existente (todos os itens contam
    no total). REPROVADO exclui o item do total; PENDENTE aguarda decisão."""
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"

class TipoEquipamento(str, enum.Enum):
    COMPUTADOR = "COMPUTADOR"
    NOTEBOOK = "NOTEBOOK"
    CELULAR = "CELULAR"
    TABLET = "TABLET"
    IMPRESSORA = "IMPRESSORA"
    MONITOR = "MONITOR"
    PRINTER = "PRINTER"
    SCANNER = "SCANNER"
    OUTROS = "OUTROS"

class UnidadeMedida(str, enum.Enum):
    """Define as unidades de medida para produtos e serviços."""
    UNIDADE = "UN"
    KILO = "KG"
    GRAMA = "G"
    LITRO = "L"
    MILILITRO = "ML"
    METRO = "M"
    CENTIMETRO = "CM"
    METRO_QUADRADO = "M2"
    METRO_CUBICO = "M3"
    HORA = "H"
    DIA = "D"
    MES = "MES"
    OUTROS = "OUTROS"

class VendaStatus(str, enum.Enum):
    """Status possiveis de uma Venda no PDV."""
    ATIVA = "ATIVA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"

class TipoProdutoVenda(str, enum.Enum):
    CADASTRADO = "CADASTRADO"
    AVULSO = "AVULSO"

class SessaoCaixaStatus(str, enum.Enum):
    """Status possiveis de uma Sessao de Caixa."""
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"

class TipoTransacaoEstoque(str, enum.Enum):
    """Tipos de transacao para movimentacao de estoque."""
    ENTRADA = "ENTRADA"
    SAIDA_VENDA = "SAIDA_VENDA"
    ESTORNO = "ESTORNO"

class MovimentacaoTipo(str, enum.Enum):
    """Define o tipo de movimentação de estoque."""
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    AJUSTE = "AJUSTE"
    EDICAO_DADOS = "EDICAO_DADOS"

class MovimentacaoOrigem(str, enum.Enum):
    """De onde veio uma movimentação de estoque.

    `movimentacoes_estoque` é o livro-razão ÚNICO do estoque: toda alteração de
    quantidade passa por lá, venha de onde vier. A origem é o que permite
    responder "esta peça saiu por venda ou por OS?" sem depender de texto livre.

    LEGADO: linhas anteriores à criação deste campo. A origem real delas não é
    recuperável — não presuma que eram manuais.
    """
    LEGADO = "LEGADO"
    MANUAL = "MANUAL"
    CADASTRO = "CADASTRO"
    VENDA = "VENDA"
    ORDEM_SERVICO = "ORDEM_SERVICO"


class JurosResponsavel(str, enum.Enum):
    """Define quem arca com os juros de um pagamento parcelado/cartão.

    CLIENTE: juros repassado — o cliente paga a mais e o `valor` do pagamento
             já inclui o acréscimo (comportamento histórico, é o padrão).
    LOJA:    juros absorvido — o cliente paga o preço cheio sem acréscimo e a
             loja recebe menos; `valor` NÃO inclui o juros.
    """
    CLIENTE = "CLIENTE"
    LOJA = "LOJA"


class MovimentacaoFinanceiraTipo(str, enum.Enum):
    """Direção do dinheiro no livro financeiro.

    Existe desde a primeira versão da tabela de propósito: "contas a pagar" é
    justamente o lado SAIDA, e uma tabela que nascesse só pensando em recebimento
    precisaria ser alterada depois — com dado real de loja dentro.
    """
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class MovimentacaoFinanceiraOrigem(str, enum.Enum):
    """De onde veio uma movimentação de dinheiro.

    `movimentacoes_financeiras` é o livro-razão ÚNICO do dinheiro, no mesmo
    espírito de `movimentacoes_estoque` (ver MovimentacaoOrigem). Todo dinheiro
    que entra ou sai passa por lá, venha de onde vier, e a origem é o que permite
    responder "isto foi venda, sangria ou pagamento de fornecedor?" sem depender
    de texto livre.

    ATENÇÃO — cobrança não é movimento. Uma venda a prazo gera a COBRANÇA hoje
    (em `pagamentos_venda`) e NENHUM movimento; o movimento nasce no dia em que o
    dinheiro entra de fato, com origem RECEBIMENTO. É essa separação que faz o
    fechamento de caixa bater numa loja que vende fiado.
    """
    VENDA = "VENDA"
    ORDEM_SERVICO = "ORDEM_SERVICO"
    ABERTURA = "ABERTURA"          # troco inicial posto na gaveta
    SANGRIA = "SANGRIA"            # retirada que não é venda
    SUPRIMENTO = "SUPRIMENTO"      # entrada que não é venda
    # Reservados para o módulo de gestão financeira. Declarados agora para que a
    # tabela não precise ser alterada quando ele chegar.
    RECEBIMENTO = "RECEBIMENTO"    # baixa de conta a receber (fiado, boleto)
    DESPESA = "DESPESA"            # conta a pagar (aluguel, fornecedor)


class TipoIntegracaoPagamento(str, enum.Enum):
    """Como a maquininha de cartão conversa com o PDV — grupo `card` da NF-e/NFC-e.

    A SEFAZ quer saber se a transação foi integrada ao sistema ou digitada à
    mão na maquininha, e o XML separa os dois casos (tpIntegra 1 e 2). Enviar
    o valor errado não derruba a nota, mas descreve mal a operação num
    documento fiscal — e é o tipo de divergência que aparece em fiscalização.

    TEF:            maquininha integrada ao PDV (tpIntegra 1). O sistema manda
                    o valor e recebe a confirmação; não há digitação.
    POS:            maquininha autônoma (tpIntegra 2). O operador digita o
                    valor no aparelho; o PDV só registra que foi cartão.
    NAO_SE_APLICA:  formas que não passam por maquininha — dinheiro, PIX,
                    crediário. É o padrão, e o motivo de o campo ser opcional.
    """
    TEF = "TEF"
    POS = "POS"
    NAO_SE_APLICA = "NAO_SE_APLICA"
