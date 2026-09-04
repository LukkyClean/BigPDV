# ---------------------------------------------------------------------------
# ARQUIVO: app/services/produto/produto.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Lógica para criação, atualização e controle de estado de produtos.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from typing import Sequence

from app.schemas.produto import ProdutoCreate, ProdutoSimpleRead, ProdutoUpdate
from app.db.models.produto import Produto as ProdutoModel
from app.db.models.estoque import Estoque as EstoqueModel
from app.db.crud import produto as produto_crud
from app.services import movimentacao_estoque as mov_service
from app.core.enum import MovimentacaoTipo, MovimentacaoOrigem

# Importando as exceções do arquivo centralizado do módulo
from ._errors import conflict_codigo_produto_exce, not_found_exce

# ===========================================================================
# LÓGICA DE CRIAÇÃO (CREATE)
# ===========================================================================

def create_produto(db: Session, produto_to_add: ProdutoCreate, usuario_token: dict) -> ProdutoModel:
    """
    Orquestra a criação de um novo produto.
    
    1. Verifica unicidade do código.
    2. Separa dados de Produto e Estoque.
    3. Cria instâncias ORM e vincula.
    4. Persiste.
    """
    # Verifica duplicidade
    produto_in_db = produto_crud.get_produto_by_code(db, produto_to_add.codigo_produto)
    
    if produto_in_db and produto_in_db.ativo:
        raise conflict_codigo_produto_exce
    
    # Prepara dados (separa estoque do produto principal)
    produto_data = produto_to_add.model_dump(exclude={"estoque"})
    produto_to_db = ProdutoModel(**produto_data)

    estoque_data = produto_to_add.estoque.model_dump()
    quantidade_inicial = estoque_data.get("quantidade", 0) or 0

    # Nasce zerado: a quantidade inicial entra pelo livro, logo abaixo. Se ela
    # já viesse gravada aqui, a ENTRADA somaria em cima e o produto começaria
    # com o dobro do estoque.
    estoque_data["quantidade"] = 0
    # A média ponderada começa no custo informado no cadastro — é a única compra
    # conhecida deste produto até aqui.
    estoque_data["custo_medio"] = estoque_data.get("valor_entrada")
    estoque_for_produto = EstoqueModel(**estoque_data)

    # Vincula estoque ao produto (Relacionamento 1:1)
    produto_to_db.estoque = estoque_for_produto

    produto_in_db = produto_crud.create_produto(db, produto_to_add=produto_to_db)

    # Estoque inicial entra como qualquer outra compra: pelo registro central,
    # com o custo informado, para o livro nascer contando a verdade (0 → N).
    mov_service.registrar_movimentacao(
        db,
        produto=produto_in_db,
        tipo=MovimentacaoTipo.ENTRADA,
        quantidade=quantidade_inicial,
        origem=MovimentacaoOrigem.CADASTRO,
        usuario_id=int(usuario_token["sub"]) if usuario_token.get("sub") else None,
        usuario_nome=usuario_token.get("nome", "Sistema"),
        observacao="Estoque inicial",
        custo_unitario=estoque_data.get("valor_entrada"),
    )

    return produto_in_db

# ===========================================================================
# LÓGICA DE LEITURA (READ)
# ===========================================================================

def get_produto_by_search(
    db: Session,
    produto_search: str | None,
    limite: int | None = None,
) -> Sequence[ProdutoModel]:
    """Intermediário para busca de produtos via CRUD."""
    return produto_crud.get_produto_by_search(db, search=produto_search, limite=limite)

def get_produto_simple_by_search(
    db: Session,
    search: str | None,
    limite: int | None = None,
) -> Sequence[ProdutoSimpleRead]:
    """Intermediário para busca rápida de produtos."""
    return produto_crud.get_produto_simple_by_search(db, search=search, limite=limite)

def get_produto_by_id(db: Session, produto_id: int) -> ProdutoModel:
    product_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not product_in_db:
        raise not_found_exce
    return product_in_db

# ===========================================================================
# LÓGICA DE ATUALIZAÇÃO (UPDATE)
# ===========================================================================

_CAMPO_LEGIVEL: dict[str, str] = {
    "nome": "Nome",
    "codigo_produto": "Código SKU",
    "codigo_barras": "Código de Barras",
    "unidade_medida": "Unidade de Medida",
    "categoria": "Categoria",
    "marca": "Marca",
    "fornecedor_id": "Fornecedor",
    "localizacao_estoque": "Localização",
    "observacao": "Descrição",
    "valor_varejo": "Preço Varejo",
    "valor_entrada": "Preço Custo",
    "valor_atacado": "Preço Atacado",
    "quantidade": "Quantidade",
    "quantidade_minima": "Qtd. Mínima",
    "quantidade_ideal": "Qtd. Ideal",
}

def _build_observacao_edicao(campos: list[str]) -> str:
    nomes = [_CAMPO_LEGIVEL.get(c, c) for c in campos]
    if len(nomes) == 1:
        return f"{nomes[0]} alterado"
    return f"Campos alterados: {', '.join(nomes)}"

def _registrar_edicao(db: Session, produto, usuario_token: dict, observacao: str) -> None:
    """Função utilitária que também é consumida por imagem.py"""
    mov_service.registrar_movimentacao(
        db,
        produto=produto,
        tipo=MovimentacaoTipo.EDICAO_DADOS,
        quantidade=0,
        origem=MovimentacaoOrigem.CADASTRO,
        usuario_id=int(usuario_token["sub"]) if usuario_token.get("sub") else None,
        usuario_nome=usuario_token.get("nome", "Sistema"),
        observacao=observacao,
    )

def update_produto_by_id(db: Session, produto_id: int, produto_to_update: ProdutoUpdate, usuario_token: dict) -> ProdutoModel:
    """
    Atualiza produto e dados de estoque aninhados.
    """
    produto_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)

    if not produto_in_db:
        raise not_found_exce

    data_to_update = produto_to_update.model_dump(exclude_unset=True)
    campos_alterados: list[str] = []
    # Quantidade não é um campo editável como os outros: ela precisa passar pelo
    # livro de estoque. Fica de fora do setattr e é aplicada depois, como AJUSTE.
    nova_quantidade: int | None = None

    # Tratamento para atualização de Estoque (Tabela Filha)
    if "estoque" in data_to_update:
        storage_data_to_update = produto_to_update.estoque.model_dump(exclude_unset=True)

        if "quantidade" in storage_data_to_update:
            nova_quantidade = storage_data_to_update.pop("quantidade")

        for key, value in storage_data_to_update.items():
            if getattr(produto_in_db.estoque, key, None) != value:
                campos_alterados.append(key)
            setattr(produto_in_db.estoque, key, value)

        del data_to_update["estoque"]

    # Atualiza atributos do Produto (Tabela Pai)
    for key, value in data_to_update.items():
        if getattr(produto_in_db, key, None) != value:
            campos_alterados.append(key)
        setattr(produto_in_db, key, value)

    produto_result = produto_crud.update_produto(db, produto_in_db)

    if campos_alterados:
        _registrar_edicao(db, produto_result, usuario_token, _build_observacao_edicao(campos_alterados))

    # Mudança de quantidade pela tela de cadastro é uma CONTAGEM, e vai para o
    # livro como AJUSTE. Antes ela era gravada direto no estoque e o histórico
    # só registrava "Quantidade alterado", com anterior e posterior iguais: as
    # unidades sumiam sem deixar rastro de quantas eram nem de quando foi.
    if nova_quantidade is not None and nova_quantidade != (produto_result.estoque.quantidade or 0):
        mov_service.registrar_movimentacao(
            db,
            produto=produto_result,
            tipo=MovimentacaoTipo.AJUSTE,
            quantidade=nova_quantidade,
            origem=MovimentacaoOrigem.CADASTRO,
            usuario_id=int(usuario_token["sub"]) if usuario_token.get("sub") else None,
            usuario_nome=usuario_token.get("nome", "Sistema"),
            observacao="Quantidade corrigida no cadastro",
        )

    return produto_result

# ===========================================================================
# LÓGICA DE STATUS (TOGGLE)
# ===========================================================================

def toggle_active_disable_produto_by_id(db: Session, produto_id: int, new_produto_code: str | None, usuario_token: dict) -> ProdutoModel:
    """
    Alterna status Ativo/Inativo.
    Se estiver reativando, verifica conflito de código e permite atualização.
    """
    produto_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    
    if not produto_in_db:
        raise not_found_exce
    
    # Lógica de Reativação (Inativo -> Ativo)
    if not produto_in_db.ativo:
        
        # Define qual código validar (o novo sugerido ou o atual existente)
        codigo_to_verify = new_produto_code if new_produto_code else produto_in_db.codigo_produto
        
        # Busca conflitos
        produto_with_same_code_in_db = produto_crud.get_produto_by_code(db, produto_code=codigo_to_verify)

        # Se existe conflito e não é o mesmo produto
        if produto_with_same_code_in_db and produto_with_same_code_in_db.id != produto_in_db.id:
            conflict_codigo_produto_exce.detail["mensagem"] = f"Código '{codigo_to_verify}' já cadastrado. Envie um novo código."
            raise conflict_codigo_produto_exce
        
        # Se forneceu código novo e passou na validação, atualiza
        if new_produto_code:
            produto_in_db.codigo_produto = new_produto_code
                
    # Inverte o status
    produto_in_db.ativo = not produto_in_db.ativo

    produto_result = produto_crud.update_produto(db, produto_to_update=produto_in_db)

    observacao = "Produto reativado" if produto_result.ativo else "Produto desabilitado"
    _registrar_edicao(db, produto_result, usuario_token, observacao)

    return produto_result