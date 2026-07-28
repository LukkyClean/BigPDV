from app.db.base import Base
from app.db.session import engine

# Importa todos os modelos para registrá-los na Base
from app.db.models.usuario import Usuario
from app.db.models.funcionario import Funcionario
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.endereco import Endereco
from app.db.models.token import TokenBlocklist
from app.db.models.produto import Produto
from app.db.models.estoque import Estoque
from app.db.models.fornecedor import Fornecedor
from app.db.models.servico import Servico
from app.db.models.produto_fotos import ProdutoFoto
from app.db.models.empresa import Empresa
from app.db.models.cargo import Cargo
from app.db.models.ordem_servico import OrdemServico
from app.db.models.objeto_servico import ObjetoServico
from app.db.models.ordem_servico_item import OrdemServicoItem
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento
from app.db.models.ordem_servico_foto import OrdemServicoFoto
from app.db.models.forma_pagamento import FormaPagamento
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.configuracao_clientes import ConfiguracaoClientes
from app.db.models.configuracao_produtos import ConfiguracaoProdutos
from app.db.models.configuracao_os import ConfiguracaoOS
from app.db.models.comunicado import Comunicado, ComunicadoLeitura
from app.db.models.sessao_caixa import SessaoCaixa
from app.db.models.venda import Venda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.log_produto import LogProduto
from app.db.models.movimentacao_estoque import MovimentacaoEstoque
from app.db.models.orcamento import Orcamento
from app.db.models.orcamento_produto import OrcamentoProduto

if __name__ == "__main__":
    print("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("Banco de dados criado com sucesso!")
