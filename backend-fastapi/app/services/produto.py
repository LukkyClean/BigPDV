# ---------------------------------------------------------------------------
# ARQUIVO: services/produto.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Lógica para criação, atualização e controle de estado de produtos.
# ---------------------------------------------------------------------------

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from typing import Sequence

from app.schemas.produto import ProdutoCreate, ProdutoSimpleRead, ProdutoUpdate
from app.db.models.produto import Produto as ProdutoModel
from app.db.models.produto_fotos import ProdutoFoto as ProdutoFotoModel
from app.db.models.estoque import Estoque as EstoqueModel
from app.db.crud import produto as produto_crud
from app.db.crud import produto_fiscal as produto_fiscal_crud
from app.db.crud import funcionario as funcionario_crud
from app.services import movimentacao_estoque as mov_service

from app.core.enum import MovimentacaoTipo, MovimentacaoOrigem
from app.core.imagem import salvar_imagem, deletar_imagem

# Exceções reutilizáveis
conflict_codigo_produto_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={
        "campo": "codigo_produto",
        "mensagem": "Código de produto já cadastrado no sistema"
    }
)

not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Produto não encontrado no sistema"
)

internal_error_exce = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Erro em cumprir a requisição. Tente novamente mais tarde."
)

_bad_request_exce = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Estoque insuficiente para a quantidade solicitada"
)

# ===========================================================================
# LÓGICA DE CRIAÇÃO (CREATE)
# ===========================================================================

def create_produto(db: Session, produto_to_add: ProdutoCreate, usuario_token: dict) -> ProdutoModel:
    """
    Orquestra a criação de um novo produto.

    1. Verifica unicidade do código.
    2. Separa dados de Produto, Estoque e Fiscal.
    3. Cria instâncias ORM e vincula.
    4. Persiste.
    5. Grava os dados fiscais, quando vierem, na MESMA transação.

    O passo 5 existe para o produto poder ser cadastrado e ter nota emitida
    sem passar pela edição: antes, o bloco fiscal só era aceito no update, e
    o lojista precisava salvar, reabrir e preencher de novo.
    """
    # Verifica duplicidade
    produto_in_db = produto_crud.get_produto_by_code(db, produto_to_add.codigo_produto)
    
    if produto_in_db and produto_in_db.ativo:
        raise conflict_codigo_produto_exce
    
    # Prepara dados (separa estoque e fiscal do produto principal)
    produto_data = produto_to_add.model_dump(exclude={"estoque", "fiscal"})
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

    # Dados fiscais, quando vierem. `flush` e não `commit`: quem fecha a
    # transação é o `_handle_db_transaction` do endpoint, então um NCM inválido
    # derruba o produto junto — que é o ponto de gravar os dois de uma vez.
    dados_fiscais = getattr(produto_to_add, "fiscal", None)
    if dados_fiscais is not None:
        produto_fiscal_crud.upsert(db, produto_in_db.id, dados_fiscais)

    return produto_in_db

def create_produto_image(db: Session, produto_id: int, image_file: UploadFile, primary_image: bool, usuario_token: dict) -> ProdutoFotoModel:

    produto_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)

    if not produto_in_db:
        raise not_found_exce

    image_url = salvar_imagem(arquivo=image_file, entidade_id=produto_id, contexto="produto")

    produto_image_to_db = ProdutoFotoModel(
        produto_id=produto_id,
        url=image_url,
        nome_arquivo=image_file.filename,
        principal=primary_image,
    )

    result = produto_crud.create_produto_image(db, produto_image_to_db)

    _registrar_edicao(db, produto_in_db, usuario_token, "Foto do produto atualizada")

    return result

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


def _registrar_edicao(db, produto, usuario_token: dict, observacao: str) -> None:
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

# ===========================================================================
# LÓGICA DE DELEÇÃO (DELETE)
# ===========================================================================

def replace_produto_principal_image(db: Session, produto_id: int, image_file: UploadFile) -> ProdutoFotoModel:
    """
    Substitui a foto principal de um produto.

    1. Busca a foto principal atual (se existir).
    2. Salva a nova imagem no disco.
    3. Cria novo registro ProdutoFoto como principal.
    4. Remove a foto anterior (arquivo + registro).
    """
    produto_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not produto_in_db:
        raise not_found_exce

    foto_anterior = produto_crud.get_produto_principal_image(db, produto_id=produto_id)

    image_url = salvar_imagem(arquivo=image_file, entidade_id=produto_id, contexto="produto")

    nova_foto = ProdutoFotoModel(
        produto_id=produto_id,
        url=image_url,
        nome_arquivo=image_file.filename,
        principal=True,
    )
    nova_foto = produto_crud.create_produto_image(db, nova_foto)

    if foto_anterior:
        deletar_imagem(caminho_arquivo=foto_anterior.url)
        produto_crud.delete_produto_image(db, image_to_delete=foto_anterior)

    return nova_foto

def delete_produto_image(db: Session, image_id: int):
    
    image_in_db = produto_crud.get_produto_image_by_id(db, image_id=image_id)

    if not image_in_db:
        raise not_found_exce
    
    file_path = image_in_db.url
    
    if not deletar_imagem(caminho_arquivo=file_path):
        raise internal_error_exce
    
    return produto_crud.delete_produto_image(db, image_to_delete=image_in_db)

def _usuario_do_funcionario(db: Session, funcionario_id: int | None) -> tuple[int | None, str]:
    """Resolve o usuário responsável a partir do funcionário da venda.

    A movimentação de estoque registra USUÁRIO (quem operou o sistema); a venda
    guarda FUNCIONÁRIO. São entidades diferentes ligadas por FK.
    """
    if not funcionario_id:
        return None, "Sistema"
    funcionario = funcionario_crud.get_funcionario_by_id(db, funcionario_id=funcionario_id)
    if not funcionario:
        return None, "Sistema"
    return funcionario.usuario_id, funcionario.nome or "Sistema"


def decrease_product_in_stock(db: Session, produto_id: int, quantidade: int, venda_id: int, funcionario_id: int):
    """Baixa de estoque por venda.

    NÃO permite estoque negativo: diferente da OS, aqui a peça ainda está na
    prateleira e dá para simplesmente não vender.
    """
    product_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not product_in_db:
        raise not_found_exce

    if quantidade > (product_in_db.estoque.quantidade or 0):
        raise _bad_request_exce

    usuario_id, usuario_nome = _usuario_do_funcionario(db, funcionario_id)
    mov_service.registrar_movimentacao(
        db,
        produto=product_in_db,
        tipo=MovimentacaoTipo.SAIDA,
        quantidade=quantidade,
        origem=MovimentacaoOrigem.VENDA,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        venda_id=venda_id,
        observacao="Baixa por venda",
    )

    return produto_crud.update_produto(db, product_in_db)

def restore_product_to_stock(db: Session, produto_id: int, quantidade: int, venda_id: int, funcionario_id: int):
    """Estorno de estoque por cancelamento de venda."""
    product_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not product_in_db:
        raise not_found_exce

    usuario_id, usuario_nome = _usuario_do_funcionario(db, funcionario_id)
    mov_service.registrar_movimentacao(
        db,
        produto=product_in_db,
        tipo=MovimentacaoTipo.ENTRADA,
        quantidade=quantidade,
        origem=MovimentacaoOrigem.VENDA,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        venda_id=venda_id,
        observacao="Estorno por cancelamento de venda",
    )

    return produto_crud.update_produto(db, product_in_db)

def get_produto_by_id(db: Session, produto_id: int) -> ProdutoModel:
    product_in_db = produto_crud.get_produto_by_id(db, produto_id=produto_id)
    if not product_in_db:
        raise not_found_exce
    return product_in_db