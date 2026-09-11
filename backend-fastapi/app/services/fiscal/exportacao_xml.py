# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/exportacao_xml.py
# DESCRIÇÃO: O pacote de XMLs do período para o contador.
#
# Todo dia 5 o contador pede os XMLs do mês. Sem isto, a loja "emite" e a
# operação quebra no primeiro fechamento: o lojista abriria nota por nota no
# Centro Fiscal e baixaria uma a uma. Aqui sai um ZIP com o XML de cada nota
# autorizada ou cancelada do período, as inutilizações homologadas e uma
# relação em CSV -- que é o que o escritório importa.
#
# O XML não fica no ERP: o livro guarda a URL e a plataforma guarda o arquivo.
# Este módulo baixa um a um na hora. O que não vier entra em `nao_baixados.txt`
# em vez de derrubar o pacote inteiro -- um XML fora do ar não pode segurar os
# outros duzentos.
# ---------------------------------------------------------------------------

import csv
import io
import logging
import zipfile
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.crud import fiscal as crud
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.inutilizacao_fiscal import InutilizacaoFiscal

from .http import get_fiscal_client

logger = logging.getLogger(__name__)

STATUS_EXPORTAVEIS = ("AUTORIZADA", "CANCELADA")


def _janela_utc(data_inicio: date, data_fim: date) -> tuple[datetime, datetime]:
    """[00:00 de `data_inicio`, 23:59:59 de `data_fim`] no fuso LOCAL, em UTC.

    `data_emissao` é gravada em UTC e o contador pede o mês do calendário da
    loja. Comparar data local com timestamp UTC perde as notas das 21h às 24h
    do último dia (e ganha as do primeiro dia do mês seguinte) -- o mesmo
    defeito do relatório de vendas, ver `project_relatorio_fuso_consulta`.
    """
    inicio_local = datetime.combine(data_inicio, time.min).astimezone()
    fim_local = datetime.combine(data_fim, time.max).astimezone()
    return (
        inicio_local.astimezone(timezone.utc).replace(tzinfo=None),
        fim_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _local(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%d/%m/%Y %H:%M")


def _reais(centavos: Optional[int]) -> str:
    return f"{(centavos or 0) / 100:.2f}".replace(".", ",")


def _nome_xml(doc: DocumentoFiscal) -> str:
    chave = (doc.chave_acesso or "").strip()
    if chave:
        return f"{chave}.xml"
    # Sem chave não há nome canônico; número+série identifica dentro da loja.
    return f"{doc.tipo_documento}-{doc.serie}-{doc.numero_documento or doc.id}.xml"


def listar_documentos_do_periodo(
    db: Session, data_inicio: date, data_fim: date, tipo: Optional[str] = None,
) -> list[DocumentoFiscal]:
    ini, fim = _janela_utc(data_inicio, data_fim)
    query = db.query(DocumentoFiscal).filter(
        DocumentoFiscal.status.in_(STATUS_EXPORTAVEIS),
        DocumentoFiscal.data_emissao >= ini,
        DocumentoFiscal.data_emissao <= fim,
    )
    if tipo:
        query = query.filter(DocumentoFiscal.tipo_documento == tipo.upper())
    return query.order_by(
        DocumentoFiscal.tipo_documento, DocumentoFiscal.serie, DocumentoFiscal.numero_documento,
    ).all()


def listar_inutilizacoes_do_periodo(
    db: Session, empresa_id: int, data_inicio: date, data_fim: date,
) -> list[InutilizacaoFiscal]:
    ini, fim = _janela_utc(data_inicio, data_fim)
    return db.query(InutilizacaoFiscal).filter(
        InutilizacaoFiscal.empresa_id == empresa_id,
        InutilizacaoFiscal.status == "HOMOLOGADA",
        InutilizacaoFiscal.data_homologacao >= ini,
        InutilizacaoFiscal.data_homologacao <= fim,
    ).all()


def montar_pacote_xml(
    db: Session,
    empresa_id: int,
    data_inicio: date,
    data_fim: date,
    tipo: Optional[str] = None,
) -> tuple[bytes, dict]:
    """Devolve (zip_em_bytes, resumo). Nunca levanta por XML que não veio."""
    documentos = listar_documentos_do_periodo(db, data_inicio, data_fim, tipo)
    inutilizacoes = listar_inutilizacoes_do_periodo(db, empresa_id, data_inicio, data_fim)

    fiscal_settings = crud.get_fiscal_settings(db, empresa_id)
    ambiente = fiscal_settings.ambiente_emissao if fiscal_settings else 2
    client = get_fiscal_client(ambiente, crud.get_licenca_token(db))

    buffer = io.BytesIO()
    nao_baixados: list[str] = []
    baixados = 0

    relacao = io.StringIO()
    escritor = csv.writer(relacao, delimiter=";", lineterminator="\r\n")
    escritor.writerow([
        "modelo", "serie", "numero", "chave_acesso", "status", "emissao",
        "autorizacao", "protocolo", "valor_total", "origem", "arquivo",
    ])

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as pacote:
        for doc in documentos:
            nome = _nome_xml(doc)
            pasta = "Cancelados" if doc.status == "CANCELADA" else (
                "NFCe" if doc.tipo_documento == "NFCE" else "NFe"
            )
            caminho = f"{pasta}/{nome}"

            xml = client.baixar_xml(doc.url_xml) if doc.url_xml else None
            if xml:
                pacote.writestr(caminho, xml)
                baixados += 1
            else:
                nao_baixados.append(
                    f"{doc.tipo_documento} {doc.serie}/{doc.numero_documento} "
                    f"chave={doc.chave_acesso or '-'} status={doc.status}: "
                    + ("sem URL de XML no registro" if not doc.url_xml else "download falhou")
                )
                caminho = ""

            origem = (
                f"OS {doc.origem_numero_os}" if doc.origem_tipo == "OS"
                else f"Venda {doc.origem_id}"
            )
            escritor.writerow([
                "65" if doc.tipo_documento == "NFCE" else "55",
                doc.serie, doc.numero_documento, doc.chave_acesso or "", doc.status,
                _local(doc.data_emissao), _local(doc.data_autorizacao),
                doc.protocolo_autorizacao or "", _reais(doc.valor_total), origem, caminho,
            ])

        for inut in inutilizacoes:
            nome = f"Inutilizacoes/inut-{inut.serie}-{inut.numero_inicial}-{inut.numero_final}.xml"
            xml = client.baixar_xml(inut.url_xml) if inut.url_xml else None
            if xml:
                pacote.writestr(nome, xml)
                baixados += 1
            else:
                nao_baixados.append(
                    f"INUTILIZACAO serie {inut.serie} {inut.numero_inicial}-{inut.numero_final}: "
                    + ("sem URL de XML no registro" if not inut.url_xml else "download falhou")
                )

        # BOM para o Excel PT-BR abrir com acento certo, mesmo padrão do CSV do front.
        pacote.writestr("relacao.csv", "﻿" + relacao.getvalue())

        if nao_baixados:
            pacote.writestr(
                "nao_baixados.txt",
                "Estes documentos existem no periodo mas o XML nao veio da emissora.\n"
                "Tente de novo mais tarde ou baixe pelo Centro Fiscal.\n\n"
                + "\n".join(nao_baixados) + "\n",
            )

        pacote.writestr(
            "LEIA-ME.txt",
            f"XMLs fiscais de {data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y}\n"
            f"Gerado pelo StartBig em {datetime.now():%d/%m/%Y %H:%M}\n\n"
            f"NFe/          NF-e (modelo 55) autorizadas\n"
            f"NFCe/         NFC-e (modelo 65) autorizadas\n"
            f"Cancelados/   notas canceladas no periodo (XML de autorizacao)\n"
            f"Inutilizacoes/ faixas de numeracao inutilizadas\n"
            f"relacao.csv   uma linha por documento (abre no Excel)\n",
        )

    resumo = {
        "documentos": len(documentos),
        "inutilizacoes": len(inutilizacoes),
        "baixados": baixados,
        "nao_baixados": len(nao_baixados),
    }
    logger.info("[FISCAL] Pacote de XMLs %s..%s: %s", data_inicio, data_fim, resumo)
    return buffer.getvalue(), resumo
