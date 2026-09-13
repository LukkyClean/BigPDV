# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/arquivos.py
# DESCRIÇÃO: Guarda o XML e o DANFE das notas autorizadas no computador da loja.
# ---------------------------------------------------------------------------
"""
Os documentos fiscais passam a ser da LOJA.

O QUE HAVIA ANTES
-----------------
O ERP guardava só `url_pdf` e `url_xml` — endereços na emissora. Os botões da
tela abriam o link, e o ZIP para o contador baixava tudo na hora da exportação
(por isso ele tem um `nao_baixados.txt`). Nada ficava no disco.

Quem é obrigado a guardar o XML por cinco anos é o **emitente**, não a
emissora. Sem arquivo local, a loja dependia de a plataforma e a Focus estarem
no ar, do link não expirar e de continuarmos clientes da mesma emissora. Três
dependências para um documento que é dela.

QUANDO O ARQUIVO É ESCRITO
--------------------------
No instante da autorização — o XML já é baixado ali para extrair o `vTotTrib`
(Lei 12.741), e era descartado em seguida. Aqui é literalmente parar de jogar
fora.

ONDE
----
`{data_dir}/fiscal/{ano}/{mes}/{chave}.xml`, ao lado do banco, com o nome sendo
a **chave de acesso de 44 dígitos** — que é como todo contador espera receber.

NÃO fica em `static/`: aquela pasta é servida por HTTP sem autenticação para a
LAN inteira (é de onde saem foto de produto e logo). Documento fiscal não.

FALHAR AQUI NUNCA DERRUBA UMA EMISSÃO. A nota já está autorizada na SEFAZ
quando este código roda; um disco cheio não pode transformar isso em erro para
o operador. Falha vira log, e o arquivo se recupera depois pelo mesmo caminho
que o ZIP do contador já usa.
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

from app.core.config import data_dir

logger = logging.getLogger(__name__)

PASTA_FISCAL = os.path.join(data_dir, "fiscal")

# O DANFE mora numa SUBPASTA própria, e o motivo é o backup.
#
# Os dois sobem para a nuvem, mas com pesos diferentes: o XML é obrigação legal
# de cinco anos e vai sempre; o DANFE cede lugar quando a pasta dele passa do
# teto (`backup/_constants.py`), porque o ZIP é lido inteiro em memória e o
# envio tem 600s de timeout. Estando numa subpasta, podá-lo é uma linha.
#
# Local ele fica sempre — reimprimir sem internet é o que o balcão precisa.
PASTA_DANFE = os.path.join(PASTA_FISCAL, "danfe")

_RE_CHAVE = re.compile(r"^\d{44}$")


def _nome_seguro(chave: Optional[str], fallback: str) -> str:
    """
    Nome do arquivo: a chave de acesso quando existe, senão o fallback.

    A chave é validada porque ela vira caminho em disco — e porque um valor
    estranho vindo da emissora não pode escrever fora da pasta.
    """
    if chave and _RE_CHAVE.match(chave.strip()):
        return chave.strip()
    return re.sub(r"[^A-Za-z0-9_.-]", "_", fallback)[:80]


def caminho_do_documento(
    chave: Optional[str], fallback: str, extensao: str, quando: Optional[datetime] = None
) -> str:
    """Caminho absoluto onde este documento deve morar."""
    momento = quando or datetime.now()
    raiz = PASTA_DANFE if extensao == "pdf" else PASTA_FISCAL
    pasta = os.path.join(raiz, f"{momento.year:04d}", f"{momento.month:02d}")
    return os.path.join(pasta, f"{_nome_seguro(chave, fallback)}.{extensao}")


def guardar_xml(
    conteudo: str,
    chave: Optional[str],
    fallback: str,
    quando: Optional[datetime] = None,
) -> Optional[str]:
    """
    Grava o XML autorizado e devolve o caminho — ou None se não deu.

    Não sobrescreve: XML autorizado é imutável, e reescrever seria a única
    forma de corromper um documento que já está na SEFAZ.
    """
    if not conteudo:
        return None

    caminho = caminho_do_documento(chave, fallback, "xml", quando)
    try:
        if os.path.exists(caminho):
            return caminho

        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)

        logger.info("[FISCAL] XML guardado em %s", caminho)
        return caminho
    except Exception as exc:
        # A nota JÁ está autorizada. Disco cheio não vira erro para o operador.
        logger.error("[FISCAL] Não foi possível guardar o XML em %s: %s", caminho, exc)
        return None


def guardar_pdf(
    conteudo: Optional[bytes],
    chave: Optional[str],
    fallback: str,
    quando: Optional[datetime] = None,
) -> Optional[str]:
    """
    Grava o DANFE e devolve o caminho — ou None se não deu.

    Confere o cabeçalho `%PDF`: a emissora pode responder 200 com uma página
    de erro em HTML, e guardar isso como se fosse o DANFE é pior que não
    guardar — o lojista só descobriria ao abrir, meses depois.
    """
    if not conteudo or not conteudo[:4] == b"%PDF":
        if conteudo:
            logger.warning("[FISCAL] Resposta do DANFE não é um PDF; descartada.")
        return None

    caminho = caminho_do_documento(chave, fallback, "pdf", quando)
    try:
        if os.path.exists(caminho):
            return caminho

        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "wb") as arquivo:
            arquivo.write(conteudo)

        logger.info("[FISCAL] DANFE guardado em %s", caminho)
        return caminho
    except Exception as exc:
        logger.error("[FISCAL] Não foi possível guardar o DANFE em %s: %s", caminho, exc)
        return None


def ler_pdf(caminho: Optional[str]) -> Optional[bytes]:
    """Lê um DANFE guardado. None quando não existe."""
    if not caminho:
        return None
    try:
        with open(caminho, "rb") as arquivo:
            return arquivo.read()
    except OSError:
        return None


def ler_xml(caminho: Optional[str]) -> Optional[str]:
    """Lê um XML guardado. None quando não existe — quem chama cai na emissora."""
    if not caminho:
        return None
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return arquivo.read()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Recuperação: as notas que já existiam antes disto
# ---------------------------------------------------------------------------

def sincronizar_pendentes(db, client, limite: int = 200) -> dict:
    """
    Busca na emissora o XML das notas autorizadas que ainda não têm arquivo.

    É o caminho de quem já emitia antes de 13/09/2026: a coluna
    `caminho_xml_local` nasce vazia e só o documento novo passa pelo
    arquivamento automático.

    Tem `limite` porque uma loja com anos de emissão faria centenas de
    downloads numa requisição só — e a emissora entrega um XML por vez. Rodar
    de novo continua de onde parou.

    Nunca levanta por causa de um documento: o que falhar entra na contagem e
    o resto segue.
    """
    from app.db.models.documento_fiscal import DocumentoFiscal

    pendentes = (
        db.query(DocumentoFiscal)
        .filter(
            DocumentoFiscal.status == "AUTORIZADA",
            DocumentoFiscal.url_xml.isnot(None),
            (DocumentoFiscal.caminho_xml_local.is_(None))
            | (DocumentoFiscal.caminho_xml_local == ""),
        )
        .order_by(DocumentoFiscal.id.desc())
        .limit(limite)
        .all()
    )

    guardados = 0
    falharam = 0

    for doc in pendentes:
        try:
            xml = client.baixar_xml(doc.url_xml)
        except Exception as exc:
            logger.warning("[FISCAL] Documento %s: falha ao baixar XML: %s", doc.id, exc)
            falharam += 1
            continue

        caminho = guardar_xml(
            xml,
            chave=doc.chave_acesso,
            fallback=f"doc-{doc.id}",
            quando=doc.data_autorizacao,
        )
        if caminho:
            doc.caminho_xml_local = caminho
            guardados += 1
        else:
            falharam += 1

        # O DANFE vai junto, e sem entrar na contagem: ele é conveniência,
        # não obrigação. Falhar aqui não torna a sincronização malsucedida.
        if doc.url_pdf and not doc.caminho_pdf_local:
            try:
                caminho_pdf = guardar_pdf(
                    client.baixar_pdf(doc.url_pdf),
                    chave=doc.chave_acesso,
                    fallback=f"doc-{doc.id}",
                    quando=doc.data_autorizacao,
                )
                if caminho_pdf:
                    doc.caminho_pdf_local = caminho_pdf
            except Exception as exc:
                logger.warning("[FISCAL] Documento %s: DANFE não veio: %s", doc.id, exc)

    return {
        "pendentes_encontrados": len(pendentes),
        "guardados": guardados,
        "falharam": falharam,
        # Quem chama decide se roda de novo — a tela mostra isso ao usuário.
        "restam": max(0, len(pendentes) - guardados) if len(pendentes) == limite else 0,
    }


def obter_xml(db, client, doc) -> Optional[str]:
    """
    O XML deste documento, venha de onde vier.

    Disco primeiro (funciona sem internet); emissora como plano B, guardando o
    que baixar para a próxima vez sair do disco.
    """
    conteudo = ler_xml(getattr(doc, "caminho_xml_local", None))
    if conteudo:
        return conteudo

    if not getattr(doc, "url_xml", None):
        return None

    try:
        conteudo = client.baixar_xml(doc.url_xml)
    except Exception as exc:
        logger.warning("[FISCAL] Documento %s: XML indisponível: %s", doc.id, exc)
        return None

    if conteudo:
        caminho = guardar_xml(
            conteudo, chave=doc.chave_acesso,
            fallback=f"doc-{doc.id}", quando=doc.data_autorizacao,
        )
        if caminho:
            doc.caminho_xml_local = caminho

    return conteudo
