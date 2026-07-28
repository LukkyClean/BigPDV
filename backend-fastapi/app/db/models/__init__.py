"""
Importa todos os modelos para que Base.metadata seja populado.
Usado pelo Alembic env.py e pelo módulo de migrações.
"""

from app.db.models.usuario import Usuario  # noqa: F401
from app.db.models.funcionario import Funcionario  # noqa: F401
from app.db.models.cliente import Cliente, ClientePF  # noqa: F401
from app.db.models.endereco import Endereco  # noqa: F401
from app.db.models.token import TokenBlocklist  # noqa: F401
from app.db.models.produto import Produto  # noqa: F401
from app.db.models.estoque import Estoque  # noqa: F401
from app.db.models.fornecedor import Fornecedor  # noqa: F401
from app.db.models.servico import Servico  # noqa: F401
from app.db.models.produto_fotos import ProdutoFoto  # noqa: F401
from app.db.models.empresa import Empresa  # noqa: F401
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings  # noqa: F401
from app.db.models.cargo import Cargo  # noqa: F401
from app.db.models.ordem_servico import OrdemServico  # noqa: F401
from app.db.models.objeto_servico import ObjetoServico  # noqa: F401
from app.db.models.ordem_servico_item import OrdemServicoItem  # noqa: F401
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento  # noqa: F401
from app.db.models.ordem_servico_foto import OrdemServicoFoto  # noqa: F401
from app.db.models.forma_pagamento import FormaPagamento  # noqa: F401
from app.db.models.configuracao_clientes import ConfiguracaoClientes  # noqa: F401
from app.db.models.configuracao_produtos import ConfiguracaoProdutos  # noqa: F401
from app.db.models.configuracao_os import ConfiguracaoOS  # noqa: F401
from app.db.models.configuracao_vendas import ConfiguracaoVendas  # noqa: F401
from app.db.models.configuracao_seguranca import ConfiguracaoSeguranca  # noqa: F401
from app.db.models.configuracao_licenca import ConfiguracaoLicenca  # noqa: F401
from app.db.models.comunicado import Comunicado, ComunicadoLeitura  # noqa: F401
from app.db.models.sessao_caixa import SessaoCaixa  # noqa: F401
from app.db.models.venda import Venda  # noqa: F401
from app.db.models.venda_produto import ProdutoVenda  # noqa: F401
from app.db.models.venda_pagamento import PagamentoVenda  # noqa: F401
from app.db.models.log_produto import LogProduto  # noqa: F401
from app.db.models.movimentacao_estoque import MovimentacaoEstoque  # noqa: F401
from app.db.models.orcamento import Orcamento  # noqa: F401
from app.db.models.orcamento_produto import OrcamentoProduto  # noqa: F401
from app.db.models.contador_venda import ContadorVenda  # noqa: F401
