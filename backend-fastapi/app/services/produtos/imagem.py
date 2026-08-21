from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models.produto_fotos import ProdutoFoto as ProdutoFotoModel
from app.db.crud import produto as produto_crud
from app.core.imagem import salvar_imagem, deletar_imagem

from ._errors import not_found_exce, internal_error_exce
from .produto import _registrar_edicao

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

def replace_produto_principal_image(db: Session, produto_id: int, image_file: UploadFile) -> ProdutoFotoModel:
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