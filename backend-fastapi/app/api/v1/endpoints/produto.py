# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/produto.py
# MÓDULO: Interface de API (Controller)
# DESCRIÇÃO: Define rotas para manipulação de Produtos e Imagens.
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from typing import Sequence, Optional

from app.schemas.produto import ProdutoCreate, ProdutoRead, ProdutoSimpleRead, ProdutoUpdate
from app.schemas.produto_fotos import ProdutoFotoRead
from app.schemas.produto_fiscal import ProdutoFiscalRead, ProdutoFiscalUpdate
from app.core.depends import check_permission, requer_modulo_fiscal, _handle_db_transaction
from app.db.session import get_db
from app.services import produto as produto_service
from app.services import produto_fiscal as produto_fiscal_service

router = APIRouter()

# ===========================================================================
# ROTAS DE CRIAÇÃO (POST)
# ===========================================================================

@router.post(
    "/",
    response_model=ProdutoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Novo Produto",
    description="Cria um produto e seu estoque inicial. Valida duplicidade de código."
)
def create_new_produto(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    *,
    produto_to_add: ProdutoCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint para cadastro de produtos.

    Args:
        produto_to_add (ProdutoCreate): Payload com dados do produto e estoque.
        db (Session): Sessão de banco de dados.

    Returns:
        ProdutoRead: O produto criado com IDs gerados.
    """
    return _handle_db_transaction(
        db,
        produto_service.create_produto,
        produto_to_add,
        user_token
    )

# ===========================================================================
# ROTAS DE LEITURA (GET)
# ===========================================================================

@router.get(
    "/",
    response_model=Sequence[ProdutoRead],
    status_code=status.HTTP_200_OK,
    summary="Listar ou Buscar Produtos",
    description="Retorna produtos ativos. Permite filtro por nome, código, código de barras, marca ou categoria."
)
def get_produto_by_search(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    *,
    buscar: Optional[str] = Query(
        None,
        description="Termo de busca (nome, código, código de barras, marca ou categoria). Se vazio, retorna todos."
    ),
    limite: Optional[int] = Query(
        None,
        ge=1,
        le=200,
        description="Teto de resultados. Sem valor, devolve tudo — a tela de Produtos depende disso para listar o catálogo."
    ),
    db: Session = Depends(get_db)
):
    """
    Endpoint de busca polivalente.

    Args:
        buscar (Optional[str]): Termo de busca; palavras em qualquer ordem.
        limite (Optional[int]): Teto de resultados para quem usa auto-complete.
        db (Session): Sessão de banco de dados.
    """
    # CORREÇÃO: Passando a referência da função (sem parênteses)
    return _handle_db_transaction(
       db,
       produto_service.get_produto_by_search,
       buscar,
       limite
   )

@router.get(
    "/search",
    response_model=Sequence[ProdutoSimpleRead],
    status_code=status.HTTP_200_OK,
    summary="Busca Rápida de Produtos",
    description="Retorna ID, nome e código de produtos ativos para auto-complete."
)
def get_produto_simple_by_search(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    *,
    search: Optional[str] = Query(
        None,
        description="Termo de busca (nome, código, código de barras, marca ou categoria). Vazio não retorna nada."
    ),
    limite: int = Query(
        30,
        ge=1,
        le=200,
        description="Teto de resultados do auto-complete."
    ),
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db,
        produto_service.get_produto_simple_by_search,
        search,
        limite
    )

@router.get(
    "/{produto_id}",
    response_model=ProdutoRead,
    status_code=status.HTTP_200_OK,
    summary="Obter Produto por ID",
    description="Retorna os dados cadastrais e de estoque de um produto específico."
)
def get_produto_by_id(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    produto_id: int = Path(..., description="ID do produto", ge=1),
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db,
        produto_service.get_produto_by_id,
        produto_id
    )

# ===========================================================================
# ROTAS DE ATUALIZAÇÃO (PUT)
# ===========================================================================

@router.put(
    "/{produto_id}",
    response_model=ProdutoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Produto Completo",
    description="Atualiza dados cadastrais e/ou estoque de um produto pelo ID."
)
def update_produto_by_id(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    produto_id: int = Path(..., description="ID do produto a ser editado", ge=1),
    *,
    produto_to_update: ProdutoUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza um produto existente.

    Args:
        produto_id (int): ID do produto na URL.
        produto_to_update (ProdutoUpdate): Payload com dados a atualizar.
    """
    return _handle_db_transaction(
        db,
        produto_service.update_produto_by_id,
        produto_id,
        produto_to_update,
        user_token,
    )

@router.put(
    "/toggle_ativo/{produto_id}",
    response_model=ProdutoRead,
    status_code=status.HTTP_200_OK,
    summary="Ativar/Desativar Produto",
    description="Alterna o status lógico (Soft Delete). Permite redefinir código na reativação."
)
def toggle_status_produto(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    produto_id: int = Path(..., description="ID do produto alvo", ge=1),
    *,
    novo_codigo_produto: str | None = Query(
        None,
        description="Novo código obrigatório caso o atual esteja em conflito na reativação."
    ),
    db: Session = Depends(get_db)
):
    """
    Realiza o Soft Delete ou Reativação de um produto.
    """
    return _handle_db_transaction(
        db,
        produto_service.toggle_active_disable_produto_by_id,
        produto_id,
        novo_codigo_produto,
        user_token,
    )

# ===========================================================================
# ROTAS DE IMAGEM (UPLOAD/DELETE)
# ===========================================================================

@router.put(
    "/{produto_id}/fotos/principal",
    response_model=ProdutoFotoRead,
    status_code=status.HTTP_200_OK,
    summary="Substituir Foto Principal do Produto",
    description="Substitui a foto principal do produto. Remove a anterior do disco e do banco."
)
def replace_produto_principal_image(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    produto_id: int = Path(..., description="ID do produto alvo", ge=1),
    *,
    image_file: UploadFile = File(..., description="Novo arquivo de imagem"),
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db,
        produto_service.replace_produto_principal_image,
        produto_id,
        image_file
    )

@router.post(
    "/{produto_id}/fotos",
    response_model=ProdutoFotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de Foto do Produto"
)
def upload_produto_image(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    produto_id: int = Path(
        ...,
        description="ID do produto alvo."
    ),
    *,
    image_file: UploadFile = File(
        ...,
        description="Arquivo de imagem (JPEG, PNG)."
    ),
    principal: bool = Form(
        False,
        description="Define se é a foto de capa."
    ),
    db: Session = Depends(get_db)
):
    """
    Recebe um arquivo de imagem e o associa ao produto.
    """
    return _handle_db_transaction(
        db,
        produto_service.create_produto_image,
        produto_id,
        image_file,
        principal,
        user_token,
    )

# ===========================================================================
# ROTAS FISCAIS (GET/PUT) — Requer módulo fiscal ativo
# ===========================================================================

@router.get(
    "/{produto_id}/fiscal",
    response_model=ProdutoFiscalRead,
    status_code=status.HTTP_200_OK,
    summary="Obter Dados Fiscais do Produto",
    description=(
        "Retorna os dados fiscais (NCM, CFOP, CST etc.) de um produto. "
        "Requer módulo fiscal ativo para a empresa. "
        "Retorna 404 se os dados fiscais ainda não foram preenchidos."
    ),
)
def get_dados_fiscais_produto(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    _fiscal: dict = Depends(requer_modulo_fiscal),
    produto_id: int = Path(..., description="ID do produto", ge=1),
    *,
    db: Session = Depends(get_db),
):
    dados = produto_fiscal_service.get_dados_fiscais(
        db, produto_id, user_token["empresa_id"]
    )
    if dados is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dados fiscais ainda não preenchidos para este produto.",
        )
    return dados


@router.put(
    "/{produto_id}/fiscal",
    response_model=ProdutoFiscalRead,
    status_code=status.HTTP_200_OK,
    summary="Salvar Dados Fiscais do Produto",
    description=(
        "Cria ou atualiza os dados fiscais de um produto (NCM, CFOP, CST etc.). "
        "Requer módulo fiscal ativo para a empresa."
    ),
)
def upsert_dados_fiscais_produto(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    _fiscal: dict = Depends(requer_modulo_fiscal),
    produto_id: int = Path(..., description="ID do produto", ge=1),
    *,
    dados: ProdutoFiscalUpdate,
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db,
        produto_fiscal_service.upsert_dados_fiscais,
        produto_id,
        user_token["empresa_id"],
        dados,
    )


@router.delete(
    "/fotos/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover Foto"
)
def delete_produto_image(
    user_token: dict = Depends(check_permission(required_permission="produto")),
    image_id: int = Path(
        ...,
        description="ID da imagem a ser removida."
    ),
    *,
    db: Session = Depends(get_db)
):
    """
    Remove o registro da foto e apaga o arquivo físico.
    """
    _handle_db_transaction(
        db,
        produto_service.delete_produto_image,
        image_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)