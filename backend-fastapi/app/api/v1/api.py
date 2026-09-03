# ---------------------------------------------------------------------------
# ARQUIVO: api.py
# DESCRIÇÃO: Roteador principal que agrega todos os endpoints da versão V1
#            da API. Este arquivo centraliza os módulos de rotas.
# ---------------------------------------------------------------------------

from fastapi import APIRouter
from app.api.v1.endpoints import reset_bd
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import cliente
from app.api.v1.endpoints import produto
from app.api.v1.endpoints import fornecedor
from app.api.v1.endpoints import servico
from app.api.v1.endpoints import endereco
from app.api.v1.endpoints import funcionario
from app.api.v1.endpoints import empresa
from app.api.v1.endpoints import cargo
from app.api.v1.endpoints import usuario
from app.api.v1.endpoints import ordem_servico
from app.api.v1.endpoints import forma_pagamento
from app.api.v1.endpoints import venda
from app.api.v1.endpoints import orcamento
from app.api.v1.endpoints import dashboard
from app.api.v1.endpoints import relatorios
from app.api.v1.endpoints import movimentacao_estoque
from app.api.v1.endpoints import configuracao
from app.api.v1.endpoints import comunicado
from app.api.v1.endpoints import licenca
from app.api.v1.endpoints import backup
from app.api.v1.endpoints import checklist_mobile
from app.api.v1.endpoints import fiscal

# Cria a instância principal do roteador para a V1
router = APIRouter()

# Endpoint utilitário para resetar o banco de dados (provavelmente para testes)
router.include_router(reset_bd.router, prefix="/reset", tags=["Resetar BD"])

# Inclui o roteador de autenticação sob o prefixo /auth
router.include_router(auth.router, prefix="/auth", tags=["Login"])

# Inclui o roteador de usuários sob o prefixo /usuarios
router.include_router(usuario.router, prefix="/usuarios", tags=["Usuários"])

# Inclui o roteador de empresas sob o prefixo /empresas
router.include_router(empresa.router, prefix="/empresas", tags=["Empresas"])

# Inclui o roteador de funcionários sob o prefixo /funcionarios
router.include_router(funcionario.router, prefix="/funcionarios", tags=["Funcionários"])

# Inclui o roteador de cargos sob o prefixo /cargos
router.include_router(cargo.router, prefix="/cargos", tags=["Cargos"])

# Inclui o roteador de clientes sob o prefixo /clientes
router.include_router(cliente.router, prefix="/clientes", tags=["Clientes"])

# Inclui o roteador de fornecedores sob o prefixo /fornecedores
router.include_router(fornecedor.router, prefix="/fornecedores", tags=["Fornecedores"])

# Inclui o roteador de movimentações de estoque sob o prefixo /produtos
# Contém sub-recursos: registrar movimentação e listar movimentações
# IMPORTANTE: precisa vir ANTES de produto.router. O caminho literal
# /produtos/movimentacoes seria capturado por /produtos/{produto_id} e o
# FastAPI tentaria converter "movimentacoes" em int, devolvendo 422.
router.include_router(movimentacao_estoque.router, prefix="/produtos", tags=["Movimentações de Estoque"])

# Inclui o roteador de produtos sob o prefixo /produtos
router.include_router(produto.router, prefix="/produtos", tags=["Produtos"])

# Inclui o roteador de serviços sob o prefixo /servicos
router.include_router(servico.router, prefix="/servicos", tags=["Serviços"])

# Inclui o roteador de endereços sob o prefixo /enderecos
router.include_router(endereco.router, prefix="/enderecos", tags=["Endereços"])

# Inclui o roteador de ordens de serviço (OS) sob o prefixo /ordens-servico
# Contém também os sub-recursos: itens, fotos e ações de status (finalizar, cancelar, reabrir)
router.include_router(ordem_servico.router, prefix="/ordens-servico", tags=["Ordens de Serviço"])

# Inclui o roteador do catálogo de formas de pagamento sob o prefixo /formas-pagamento
# Entidade global do sistema, usada na finalização de OS
router.include_router(forma_pagamento.router, prefix="/formas-pagamento", tags=["Formas de Pagamento"])

# Inclui o roteador de vendas (PDV) sob o prefixo /vendas
# Contém sub-recursos: itens do carrinho e ações de status (cancelar, finalizar)
router.include_router(venda.router, prefix="/vendas", tags=["Vendas"])

# Inclui o roteador de orcamentos sob o prefixo /orcamentos
router.include_router(orcamento.router, prefix="/orcamentos", tags=["Orcamentos"])

# Inclui o roteador do Dashboard sob o prefixo /dashboard
# Endpoints read-only para metricas, OS vencendo, estoque e vendas recentes
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# Inclui o roteador de Relatorios sob o prefixo /relatorios
# Endpoints read-only de faturamento/analytics, protegidos por permissao
router.include_router(relatorios.router, prefix="/relatorios", tags=["Relatórios"])

# Inclui o roteador de configurações do sistema sob o prefixo /configuracoes
router.include_router(configuracao.router, prefix="/configuracoes", tags=["Configurações"])
router.include_router(comunicado.router, prefix="/comunicados", tags=["Comunicados"])

# Inclui o roteador de licença sob o prefixo /licenca
# Endpoint público (sem autenticação) para verificação de licença no boot
router.include_router(licenca.router, prefix="/licenca", tags=["Licença"])

router.include_router(backup.router, prefix="/backup", tags=["Backup"])
# Inclui o roteador do checklist mobile (formulario web via QR code)
# Endpoints publicos autenticados por token HMAC + gerador de token via JWT
router.include_router(checklist_mobile.router, prefix="/checklist", tags=["Checklist Mobile"])

# Inclui o roteador do Centro Fiscal sob o prefixo /fiscal
# Endpoints de documentos fiscais, resumo e pendências globais
router.include_router(fiscal.router, prefix="/fiscal", tags=["Fiscal"])
