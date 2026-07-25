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
