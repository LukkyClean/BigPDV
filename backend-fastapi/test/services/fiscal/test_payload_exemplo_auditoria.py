# ---------------------------------------------------------------------------
# ARQUIVO: test_payload_exemplo_auditoria.py
# DESCRIÇÃO: Gera os JSONs de exemplo que o time da plataforma passa pelo
#            tradutor para auditar quais campos sobrevivem.
#
# POR QUE ISTO EXISTE
# -------------------
# O `traduzirPayloadParaFocus` da VPS é função PURA: recebe o objeto do ERP e
# devolve o que vai para a Focus, sem banco, rede ou token. Então a auditoria
# "que campo é descartado?" não precisa de emissão nenhuma — precisa do JSON
# de entrada. Eles rodam o tradutor, devolvem a saída, e o diff responde a
# pergunta de forma exata em vez de interpretada.
#
# O exemplo é MÁXIMO de propósito: cobre os condicionais (CEST, redução de
# base, cBenef, crédito do CSOSN 101, cartão com tipo_integracao) e o
# destinatário PF com endereço completo, que é o que a NF-e exige. Um exemplo
# mínimo auditaria só o caminho feliz e deixaria justamente os campos raros —
# os que ninguém percebe faltando — de fora.
#
# Os arquivos ficam em `docs/payloads/` e são versionados: mexer no payload
# sem regerar quebra este teste, e o time da plataforma fica com um exemplo
# que não corresponde mais à realidade.
#
# PARA REGERAR:  REGERAR_PAYLOAD=1 pytest test/services/fiscal/test_payload_exemplo_auditoria.py
# ---------------------------------------------------------------------------

import json
import os
from pathlib import Path

from app.core.enum import State
from app.db.models.cliente import ClientePF
from app.db.models.endereco import Endereco
from app.db.models.produto_fiscal import ProdutoFiscal

from test.services.fiscal.test_payload_builder import (  # noqa: F401
    _empresa,
    _endereco_empresa,
    _fiscal_settings,
    _item_venda,
    _montar,
    _pagamento,
    _produto,
    _venda,
)

PASTA = Path(__file__).resolve().parents[3] / "docs" / "payloads"


def _cliente_pf_com_endereco() -> ClientePF:
    """
    Destinatário completo — a NF-e exige endereço (a NFC-e não).

    É o grupo que corre risco real de poda: o tradutor da plataforma achata
    `destinatario{}` por tabela de nomes.
    """
    cliente = ClientePF(
        id=7,
        nome="Maria Souza",
        cpf="52998224725",
    )
    # `endereco` (singular) é o nome da relação no model — é uma LISTA.
    cliente.endereco = [
        Endereco(
            logradouro="Avenida Brasil",
            numero="2500",
            complemento="Apto 51",
            bairro="Jardim America",
            cidade="Campinas",
            estado=State.SAO_PAULO,
            cep="13010000",
        )
    ]
    return cliente


def _produto_com_st(id_produto: int) -> object:
    """Produto sob substituição tributária — traz o CEST junto."""
    produto = _produto(id_produto, nome="Pneu Aro 15", codigo_barras="7891234000019")
    produto.fiscal = ProdutoFiscal(
        produto_id=id_produto,
        ncm="40111000",
        cest="0100100",
        cfop_padrao="5405",
        origem_mercadoria=0,
        unidade_tributavel="UN",
        cst_icms="60",
        csosn="500",
        cst_pis="01",
        cst_cofins="01",
    )
    return produto


def _produto_com_reducao(id_produto: int) -> object:
    """CST 20 — puxa redução de base e código de benefício fiscal."""
    produto = _produto(id_produto, nome="Cesta Basica", codigo_barras="7891234000026")
    produto.fiscal = ProdutoFiscal(
        produto_id=id_produto,
        ncm="19053100",
        cfop_padrao="5102",
        origem_mercadoria=0,
        unidade_tributavel="CX",
        cst_icms="20",
        csosn="101",
        aliquota_icms=1800,
        reducao_base_icms=4112,
        codigo_beneficio_fiscal="SP000001",
        cst_pis="01",
        cst_cofins="01",
    )
    return produto


def _gravar(nome: str, payload: dict) -> dict:
    """Grava (ou confere) o exemplo versionado."""
    PASTA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA / nome
    texto = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)

    if os.environ.get("REGERAR_PAYLOAD") or not caminho.exists():
        caminho.write_text(texto + "\n", encoding="utf-8")

    return json.loads(caminho.read_text(encoding="utf-8"))


def test_exemplo_nfe_regime_normal_esta_atualizado():
    """
    Cenário rico: item comum, item com ST (CEST) e item com CST 20 (redução +
    cBenef), pago no cartão de crédito (tipo_integracao), com destinatário PF
    completo.
    """
    itens = [
        _item_venda(1, _produto(1), quantidade=2, valor_unitario=10000),
        _item_venda(2, _produto_com_st(2), quantidade=1, valor_unitario=45000),
        _item_venda(3, _produto_com_reducao(3), quantidade=3, valor_unitario=8000, desconto=1500),
    ]
    venda = _venda(
        itens,
        [_pagamento(89000, codigo_sefaz="03", nome="Cartão de Crédito")],
        entrega=1500,
        cliente=_cliente_pf_com_endereco(),
    )

    payload = _montar(venda)
    gravado = _gravar("nfe-regime-normal.json", payload)

    assert json.loads(json.dumps(payload, default=str)) == gravado, (
        "O payload mudou e o exemplo versionado não. Rode com REGERAR_PAYLOAD=1 "
        "e avise o time da plataforma — é o arquivo que eles auditam."
    )


def test_exemplo_nfe_simples_nacional_esta_atualizado():
    """
    O caso das lojas em produção: Simples/MEI, CSOSN em vez de CST, PIS/COFINS
    na guia única (CST 49, zerados), pagamento em dinheiro.
    """
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=100)]
    venda = _venda(itens, [_pagamento(100)], cliente=_cliente_pf_com_endereco())

    payload = _montar(venda, simples=True)
    gravado = _gravar("nfe-simples-nacional.json", payload)

    assert json.loads(json.dumps(payload, default=str)) == gravado, (
        "O payload mudou e o exemplo versionado não. Rode com REGERAR_PAYLOAD=1."
    )
