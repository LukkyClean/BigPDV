# ---------------------------------------------------------------------------
# ARQUIVO: test_auditoria_nomes_no_xml.py
# DESCRIÇÃO: Descobre quais nomes de campo a Focus IGNOROU, comparando o que
#            enviamos com o XML que a SEFAZ autorizou.
#
# POR QUE ESTE TESTE, E NÃO O LOG LADO A LADO
# -------------------------------------------
# A ideia anterior era comparar o payload que o ERP envia com o que a
# plataforma repassa. O time da VPS apontou o furo, e ele é decisivo:
#
#   "o log lado a lado prova transporte, não nomes. Se o ERP mandar
#    `ipi_codigo_enquadramento` e o log mostrar `ipi_codigo_enquadramento`
#    chegando na Focus, o diff passa limpo — e o campo continua errado."
#
# Exatamente o que aconteceu em 12/09/2026: o nome certo era
# `ipi_codigo_enquadramento_legal`, o campo viajou intacto a vida toda, e
# ninguém viu até a SEFAZ recusar por schema.
#
# Quem responde "a Focus entendeu?" é o XML AUTORIZADO. Campo enviado que não
# aparece lá foi ignorado em silêncio.
#
# COMO RODAR A AUDITORIA
# ----------------------
# 1. Emita uma nota em HOMOLOGAÇÃO com o máximo de campos preenchidos.
# 2. Baixe o XML autorizado (a Focus devolve em `caminho_xml_nota_fiscal`; o
#    ERP já o lê com `completa=1` em `client.baixar_xml`).
# 3. Salve como `docs/payloads/xml-autorizado-homologacao.xml`.
# 4. Salve o payload correspondente (do log `[FISCAL] payload NFE ref=...`)
#    como `docs/payloads/payload-da-emissao.json`.
# 5. `pytest test/services/fiscal/test_auditoria_nomes_no_xml.py -s`
#
# Sem os arquivos, o teste é pulado — ele não trava a suíte de ninguém.
# ---------------------------------------------------------------------------

import json
import re
from pathlib import Path

import pytest

PASTA = Path(__file__).resolve().parents[3] / "docs" / "payloads"
XML = PASTA / "xml-autorizado-homologacao.xml"
PAYLOAD = PASTA / "payload-da-emissao.json"


# Campo da API (Focus) -> tag no XML da NF-e.
#
# Esta tabela É a documentação que faltava. Cada linha foi conferida contra o
# layout da NF-e 4.0; onde a tag se repete em grupos diferentes (`CST`, `vBC`),
# o grupo vai junto, porque é ele que desfaz a ambiguidade.
CAMPO_PARA_TAG: dict[str, str] = {
    # Identificação do item
    "codigo_produto": "cProd",
    "descricao": "xProd",
    "unidade_comercial": "uCom",
    "quantidade_comercial": "qCom",
    "valor_unitario_comercial": "vUnCom",
    "valor_bruto": "vProd",
    "codigo_barras_comercial": "cEAN",
    "unidade_tributavel": "uTrib",
    "codigo_barras_tributavel": "cEANTrib",
    "ncm": "NCM",
    "cest": "CEST",
    "cfop": "CFOP",
    # Rateio
    "valor_frete": "vFrete",
    "valor_seguro": "vSeg",
    "valor_outras_despesas_acessorias": "vOutro",
    "valor_desconto": "vDesc",
    # ICMS
    "icms_origem": "orig",
    "icms_situacao_tributaria": "CST|CSOSN",
    "icms_modalidade_base_calculo": "modBC",
    "icms_base_calculo": "ICMS/vBC",
    "icms_aliquota": "pICMS",
    "icms_valor": "vICMS",
    "icms_reducao_base_calculo": "pRedBC",
    "icms_codigo_beneficio_fiscal_reducao_base_calculo": "cBenef",
    "icms_aliquota_aplicavel_calculo_credito": "pCredSN",
    "icms_valor_credito_aproveitado": "vCredICMSSN",
    # PIS / COFINS
    "pis_situacao_tributaria": "PIS/CST",
    "pis_base_calculo": "PIS/vBC",
    "pis_aliquota_porcentual": "pPIS",
    "pis_valor": "vPIS",
    "cofins_situacao_tributaria": "COFINS/CST",
    "cofins_base_calculo": "COFINS/vBC",
    "cofins_aliquota_porcentual": "pCOFINS",
    "cofins_valor": "vCOFINS",
    # IPI — fora do payload hoje; a linha fica para quando voltar (indústria).
    "ipi_situacao_tributaria": "IPI/CST",
    "ipi_codigo_enquadramento_legal": "cEnq",
}


def _tags_presentes(xml: str) -> set[str]:
    """Nomes de tag do XML, sem namespace."""
    return {t.split(":")[-1] for t in re.findall(r"<([A-Za-z][\w:]*)", xml)}


@pytest.mark.skipif(
    not (XML.exists() and PAYLOAD.exists()),
    reason=(
        "Auditoria sob demanda: salve o XML autorizado e o payload da emissão "
        "em docs/payloads/. Ver o cabeçalho do arquivo."
    ),
)
def test_nomes_enviados_aparecem_no_xml_autorizado():
    """
    Todo campo de item que enviamos precisa ter deixado rastro no XML.

    Falha nomeando o campo e a tag que deveria existir — que é a informação
    que faltou durante a investigação de 12/09/2026.
    """
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    xml = XML.read_text(encoding="utf-8")
    tags = _tags_presentes(xml)

    enviados: set[str] = set()
    for item in payload.get("payload", payload).get("items", []):
        enviados |= set(item)

    ignorados = []
    sem_mapa = []

    for campo in sorted(enviados):
        alvo = CAMPO_PARA_TAG.get(campo)
        if alvo is None:
            sem_mapa.append(campo)
            continue
        esperadas = {t.split("/")[-1] for t in alvo.split("|")}
        if not (esperadas & tags):
            ignorados.append(f"{campo} -> esperava <{alvo}> no XML")

    print(f"\n[auditoria] {len(enviados)} campos de item enviados")
    print(f"[auditoria] tags no XML: {len(tags)}")
    if sem_mapa:
        print(f"[auditoria] sem mapeamento nesta tabela: {sem_mapa}")

    assert not ignorados, (
        "Campos enviados que NÃO apareceram no XML — a Focus ignorou o nome:\n  "
        + "\n  ".join(ignorados)
    )


def test_tabela_de_mapeamento_cobre_o_payload_atual():
    """
    A tabela acima precisa acompanhar o payload: campo novo sem mapeamento
    entra na auditoria como "não sei conferir", que é pior que não auditar.

    Roda sempre, sem depender do XML.
    """
    from test.services.fiscal.test_contrato_payload_campos import CAMPOS_ITEM

    campos_item = {c.split("[].")[-1] for c in CAMPOS_ITEM}
    # `numero_item` vira atributo `nItem` do <det>, não tag própria.
    campos_item -= {"numero_item"}

    faltando = campos_item - set(CAMPO_PARA_TAG)
    assert not faltando, (
        f"Sem tag mapeada (acrescente em CAMPO_PARA_TAG): {sorted(faltando)}"
    )
