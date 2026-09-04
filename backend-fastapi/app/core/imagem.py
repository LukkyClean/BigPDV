# ---------------------------------------------------------------------------
# ARQUIVO: core/imagem.py
# MODULO: Utilitario Centralizado de Imagens
# DESCRICAO: Validacao, processamento e armazenamento padronizado de imagens.
#            Substitui as funcoes save_image_locally/delete_image_locally
#            duplicadas nos services de produto, usuario, empresa e OS.
# ---------------------------------------------------------------------------

import os
import sys
import uuid
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.config import data_dir

# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

TIPOS_MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}
TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB

# Configuracoes por contexto de upload
CONTEXTO_IMAGEM = {
    "produto": {
        "max_dimensao": (1200, 1200),
        "qualidade": 85,
        "diretorio_base": "static/uploads/produtos",
    },
    "empresa_logo": {
        "max_dimensao": (400, 400),
        "qualidade": 90,
        "diretorio_base": "static/uploads/empresa",
    },
    "usuario_perfil": {
        "max_dimensao": (300, 300),
        "qualidade": 85,
        "diretorio_base": "static/uploads/usuarios",
    },
    "os_foto": {
        "max_dimensao": (1920, 1920),
        "qualidade": 80,
        "diretorio_base": "static/uploads/ordens-servico",
    },
}


# ---------------------------------------------------------------------------
# VALIDACAO
# ---------------------------------------------------------------------------

def validar_imagem(arquivo: UploadFile) -> bytes:
    """
    Valida o arquivo de imagem enviado pelo cliente.

    Verifica tipo MIME, extensao, tamanho e integridade da imagem.
    Retorna os bytes lidos para evitar re-leitura do stream.

    Raises:
        HTTPException 400: Se a validacao falhar.
    """
    # 1. Tipo MIME
    if arquivo.content_type not in TIPOS_MIME_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de arquivo nao permitido. Envie JPEG, PNG ou WebP.",
        )

    # 2. Extensao
    extensao = os.path.splitext(arquivo.filename or "")[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extensao de arquivo nao permitida. Use .jpg, .png ou .webp.",
        )

    # 3. Tamanho
    conteudo = arquivo.file.read()
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo excede o tamanho maximo de 5MB.",
        )

    # 4. Integridade — verificar se e uma imagem valida
    try:
        img = Image.open(BytesIO(conteudo))
        img.verify()
    except (UnidentifiedImageError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo corrompido ou nao e uma imagem valida.",
        )

    return conteudo


# ---------------------------------------------------------------------------
# PROCESSAMENTO
# ---------------------------------------------------------------------------

def processar_imagem(conteudo: bytes, contexto: str) -> bytes:
    """
    Processa a imagem: corrige orientacao EXIF, redimensiona e converte para WebP.

    Args:
        conteudo: Bytes brutos da imagem ja validada.
        contexto: Chave do CONTEXTO_IMAGEM (ex: "produto", "empresa_logo").

    Returns:
        Bytes da imagem processada em formato WebP.

    Raises:
        HTTPException 500: Se o processamento falhar.
    """
    config = CONTEXTO_IMAGEM[contexto]

    try:
        img = Image.open(BytesIO(conteudo))

        # Corrige rotacao baseada em metadados EXIF (fotos de celular)
        img = ImageOps.exif_transpose(img)

        # Converter modo de cor para compatibilidade com WebP
        if img.mode in ("RGBA", "LA", "PA") and contexto == "empresa_logo":
            img = img.convert("RGBA")  # Preserva transparencia para logos
        elif img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Redimensiona mantendo proporcao (so reduz, nunca amplia)
        img.thumbnail(config["max_dimensao"], Image.LANCZOS)

        # Salva em buffer como WebP
        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=config["qualidade"])
        return buffer.getvalue()

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar a imagem. Tente novamente.",
        )


# ---------------------------------------------------------------------------
# SALVAMENTO
# ---------------------------------------------------------------------------

def salvar_imagem(arquivo: UploadFile, entidade_id: int, contexto: str) -> str:
    """
    Pipeline completo: valida, processa e salva a imagem no disco.

    Args:
        arquivo: UploadFile recebido pelo endpoint.
        entidade_id: ID da entidade (produto_id, usuario_id, etc.).
        contexto: Chave do CONTEXTO_IMAGEM.

    Returns:
        Caminho relativo da imagem salva (usado como URL no banco).
    """
    config = CONTEXTO_IMAGEM[contexto]

    try:
        # 1. Validar
        conteudo = validar_imagem(arquivo)

        # 2. Processar
        conteudo_processado = processar_imagem(conteudo, contexto)

        # 3. Gerar nome unico com extensao .webp
        nome_arquivo = f"{uuid.uuid4()}.webp"

        # 4. Criar diretorio
        diretorio = os.path.join(data_dir, config["diretorio_base"], str(entidade_id))
        os.makedirs(diretorio, exist_ok=True)

        # 5. Escrever no disco
        caminho_arquivo = os.path.join(diretorio, nome_arquivo)
        print(f"Salvando imagem em: {caminho_arquivo}")  # Log para debug
        with open(caminho_arquivo, "wb") as f:
            f.write(conteudo_processado)

        # 6. Retornar URL relativa
        return f"{config['diretorio_base']}/{entidade_id}/{nome_arquivo}"

    finally:
        arquivo.file.close()


# ---------------------------------------------------------------------------
# DELECAO
# ---------------------------------------------------------------------------

def deletar_imagem(caminho_arquivo: str) -> bool:
    """
    Remove o arquivo de imagem do disco e limpa diretorio vazio.

    Args:
        caminho_arquivo: Caminho relativo do arquivo (armazenado no banco).

    Returns:
        True se o arquivo foi removido, False se nao existia.
    """
    caminho_abs = os.path.join(data_dir, caminho_arquivo)

    if not os.path.exists(caminho_abs):
        return False

    try:
        os.remove(caminho_abs)
    except OSError:
        return False

    # Tenta remover diretorio vazio (entidade sem mais imagens)
    diretorio = os.path.dirname(caminho_abs)
    try:
        os.rmdir(diretorio)
    except OSError:
        pass  # Diretorio nao esta vazio — manter

    return True
