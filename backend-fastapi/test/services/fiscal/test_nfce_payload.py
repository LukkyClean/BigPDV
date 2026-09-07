# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_nfce_payload.py
# DESCRIÇÃO: Payload e guardas da NFC-e (modelo 65).
#
# Reusa os helpers de test_payload_builder — a NFC-e nasce do MESMO tronco da
# NF-e, e o que estes testes fixam é justamente onde ela precisa divergir:
# modelo, destinatário opcional, CSC e o expurgo de nós nulos.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.db.models.cliente import ClientePF, ClientePJ
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.venda_nota_fiscal import VendaNotaFiscal
from app.services.fiscal.emissao import (
    _assert_consumidor_identificado,
    _assert_csc_configurado,
    _assert_dentro_da_janela_de_cancelamento,
    _documento_do_consumidor,
)
from app.services.fiscal.helpers import cifrar_csc_token, obter_csc_token
from app.services.fiscal.payload_builder import (
    _montar_destinatario_nfce,
    expurgar_nulos,
    montar_payload_nfce,
)

from test.services.fiscal.test_payload_builder import (
    _calcular,
    _empresa,
    _endereco_empresa,
    _item_venda,
    _pagamento,
    _produto,
    _venda,
)


def _fiscal_settings_nfce(**kwargs):
    base = dict(
        empresa_id=1,
        serie_nfce=2,
        ultimo_numero_nfce=41,
        csc_id="000001",
        csc_token=cifrar_csc_token("CSC-DE-TESTE"),
        limite_consumidor_anonimo=1000000,  # R$ 10.000,00
    )
    base.update(kwargs)
    return EmpresaFiscalSettings(**base)


def _montar_nfce(venda, nota_fiscal=None, fiscal_settings=None, numero=None):
    return montar_payload_nfce(
        empresa=_empresa("Lucro Presumido"),
        endereco_empresa=_endereco_empresa(),
        fiscal_settings=fiscal_settings or _fiscal_settings_nfce(),
        venda=venda,
        nota_fiscal=nota_fiscal,
        resultado_calculo=_calcular(venda),
        numero=numero,
    )


def _venda_simples(total=10000, cliente=None):
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=total)]
    return _venda(itens, [_pagamento(total)], cliente=cliente)


# =========================
# 1. Expurgo de nós nulos
# =========================

def test_expurgo_remove_nulos_e_vazios():
    sujo = {
        "a": None,
        "b": "",
        "c": "   ",
        "d": {},
        "e": [],
        "f": {"g": None},
        "h": "valor",
    }

    assert expurgar_nulos(sujo) == {"h": "valor"}


def test_expurgo_preserva_zero_e_false():
    """
    O ponto mais delicado do expurgo: zero é valor, não ausência.

    `valor_desconto: 0.0` sumindo faz a nota deixar de fechar, e
    `consumidor_final: 0` sumindo muda a natureza da operação.
    """
    payload = {"valor_desconto": 0.0, "consumidor_final": 0, "flag": False}

    assert expurgar_nulos(payload) == payload


def test_expurgo_limpa_aninhado_sem_destruir_o_resto():
    entrada = {
        "totais": {"valor_total": 100.0, "valor_frete": None},
        "items": [{"nome": "X", "cest": None}, {"nome": None}],
    }

    assert expurgar_nulos(entrada) == {
        "totais": {"valor_total": 100.0},
        "items": [{"nome": "X"}],
    }


def test_payload_nfce_nao_tem_nenhuma_chave_nula():
    payload = _montar_nfce(_venda_simples())

    def sem_nulos(valor):
        if isinstance(valor, dict):
            assert None not in valor.values()
            for v in valor.values():
                sem_nulos(v)
        elif isinstance(valor, list):
            for v in valor:
                sem_nulos(v)

    sem_nulos(payload)


# =========================
# 2. Identidade do modelo 65
# =========================

def test_payload_declara_modelo_65_e_operacao_presencial():
    payload = _montar_nfce(_venda_simples())

    assert payload["modelo"] == 65
    assert payload["presenca_comprador"] == 1
    assert payload["consumidor_final"] == 1
    assert payload["local_destino"] == 1
    assert payload["modalidade_frete"] == 9  # o cliente leva a mercadoria


def test_serie_e_numero_saem_do_contador_de_nfce():
    """A numeração do modelo 65 é independente da do 55."""
    payload = _montar_nfce(_venda_simples(), numero=77)

    assert payload["numero"] == 77
    assert payload["serie"] == 2


def test_numero_omitido_e_previsao_do_contador_de_nfce():
    payload = _montar_nfce(_venda_simples())

    assert payload["numero"] == 42  # ultimo_numero_nfce (41) + 1


# =========================
# 3. Destinatário opcional
# =========================

def test_venda_sem_cpf_omite_o_destinatario():
    """
    Na NF-e mandamos {"nome": "CONSUMIDOR FINAL"}. Na NFC-e o grupo inteiro sai
    do payload — enviá-lo só com nome genérico e sem documento é rejeitado.
    """
    payload = _montar_nfce(_venda_simples())

    assert "destinatario" not in payload


def test_cpf_digitado_no_caixa_vira_destinatario():
    nota = VendaNotaFiscal(venda_id=1, documento_consumidor="52998224725")
    payload = _montar_nfce(_venda_simples(), nota_fiscal=nota)

    assert payload["destinatario"] == {"cpf": "52998224725", "indicador_ie": "9"}


def test_cpf_com_pontuacao_e_normalizado():
    nota = VendaNotaFiscal(venda_id=1, documento_consumidor="529.982.247-25")

    assert _montar_destinatario_nfce(None, nota.documento_consumidor) == {
        "cpf": "52998224725", "indicador_ie": "9",
    }


def test_cnpj_de_14_digitos_vira_cnpj():
    assert _montar_destinatario_nfce(None, "11222333000181") == {
        "cnpj": "11222333000181", "indicador_ie": "9",
    }


@pytest.mark.parametrize("documento", ["", None, "123", "5299822472", "abc"])
def test_documento_invalido_cai_em_consumidor_nao_identificado(documento):
    assert _montar_destinatario_nfce(None, documento) is None


def test_cliente_cadastrado_vence_o_cpf_do_caixa():
    """O cadastro foi conferido uma vez; o digitado no balcão, não."""
    cliente = ClientePF(id=1, nome="Maria", cpf="52998224725")

    dest = _montar_destinatario_nfce(cliente, "11122233396")

    assert dest == {"cpf": "52998224725", "indicador_ie": "9"}


def test_destinatario_pj_traz_indicador_de_contribuinte():
    cliente = ClientePJ(
        id=1, razao_social="Loja X", cnpj="11222333000181", ie="110042490114",
    )

    assert _montar_destinatario_nfce(cliente, None) == {
        "cnpj": "11222333000181", "indicador_ie": "1",
    }


def test_destinatario_nfce_nao_leva_endereco():
    """No varejo presencial não há endereço do comprador a informar."""
    cliente = ClientePF(id=1, nome="Maria", cpf="52998224725")

    assert "endereco" not in _montar_destinatario_nfce(cliente, None)


# =========================
# 4. CSC
# =========================

def test_csc_vai_no_payload_em_claro():
    """O provedor precisa do token para montar o hash do QR Code."""
    payload = _montar_nfce(_venda_simples())

    assert payload["csc_id"] == "000001"
    assert payload["csc_token"] == "CSC-DE-TESTE"


def test_csc_e_guardado_cifrado():
    fs = _fiscal_settings_nfce()

    assert fs.csc_token != "CSC-DE-TESTE"          # não está em texto puro
    assert obter_csc_token(fs) == "CSC-DE-TESTE"   # mas volta ao ser lido


def test_csc_legado_em_texto_puro_continua_funcionando():
    """Instalações anteriores gravaram sem cifrar; recusá-las quebraria a loja."""
    fs = _fiscal_settings_nfce(csc_token="TEXTO-PURO-LEGADO")

    assert obter_csc_token(fs) == "TEXTO-PURO-LEGADO"


@pytest.mark.parametrize("fs_kwargs", [
    {"csc_id": None},
    {"csc_token": None},
    {"csc_id": None, "csc_token": None},
])
def test_emissao_sem_csc_e_recusada(fs_kwargs):
    with pytest.raises(HTTPException) as erro:
        _assert_csc_configurado(_fiscal_settings_nfce(**fs_kwargs))

    assert erro.value.status_code == 422
    assert erro.value.detail["codigo"] == "CSC_NAO_CONFIGURADO"


# =========================
# 5. Regra 3 — teto do consumidor anônimo
# =========================

def test_venda_abaixo_do_teto_dispensa_documento():
    venda = _venda_simples(total=999999)  # R$ 9.999,99

    _assert_consumidor_identificado(venda, _fiscal_settings_nfce())


def test_venda_no_teto_exige_documento():
    """O limite é inclusivo: 'a partir de' R$ 10.000,00."""
    venda = _venda_simples(total=1000000)

    with pytest.raises(HTTPException) as erro:
        _assert_consumidor_identificado(venda, _fiscal_settings_nfce())

    assert erro.value.status_code == 422
    assert erro.value.detail["codigo"] == "CONSUMIDOR_NAO_IDENTIFICADO"
    assert "R$ 10.000,00" in erro.value.detail["mensagem"]


def test_venda_acima_do_teto_com_cpf_do_caixa_passa():
    venda = _venda_simples(total=1500000)
    venda.nota_fiscal = VendaNotaFiscal(
        venda_id=1, documento_consumidor="52998224725",
    )

    _assert_consumidor_identificado(venda, _fiscal_settings_nfce())


def test_venda_acima_do_teto_com_cliente_cadastrado_passa():
    cliente = ClientePF(id=1, nome="Maria", cpf="52998224725")
    venda = _venda_simples(total=1500000, cliente=cliente)

    _assert_consumidor_identificado(venda, _fiscal_settings_nfce())


def test_teto_zerado_desliga_a_regra():
    """Quem configura 0 está dizendo 'não quero esse bloqueio'."""
    venda = _venda_simples(total=50000000)

    _assert_consumidor_identificado(
        venda, _fiscal_settings_nfce(limite_consumidor_anonimo=0),
    )


def test_teto_e_configuravel_por_empresa():
    venda = _venda_simples(total=60000)  # R$ 600,00

    with pytest.raises(HTTPException):
        _assert_consumidor_identificado(
            venda, _fiscal_settings_nfce(limite_consumidor_anonimo=50000),
        )


def test_documento_do_consumidor_normaliza_e_respeita_precedencia():
    cliente = ClientePF(id=1, nome="Maria", cpf="529.982.247-25")
    venda = _venda_simples(cliente=cliente)
    venda.nota_fiscal = VendaNotaFiscal(
        venda_id=1, documento_consumidor="11122233396",
    )

    assert _documento_do_consumidor(venda) == "52998224725"


# =========================
# 6. Fechamento em centavos continua valendo (Regra 1)
# =========================

def test_pagamentos_precisam_fechar_com_o_total():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(9000)])  # R$ 10,00 a menos

    with pytest.raises(ValueError, match="não fecham"):
        _montar_nfce(venda)


def test_troco_em_dinheiro_fecha_a_equacao():
    """
    Σ pagamentos − troco = total. Na NFC-e o troco é a regra, não a exceção.
    """
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(15000)])  # paga R$ 150, troco R$ 50

    payload = _montar_nfce(venda)

    assert payload["valor_troco"] == 50.0
    soma = sum(p["valor_pagamento"] for p in payload["formas_pagamento"])
    assert round(soma - payload["valor_troco"], 2) == payload["totais"]["valor_total"]


# =========================
# 7. Janela de cancelamento por modelo
# =========================

def _doc(tipo, minutos_atras):
    return DocumentoFiscal(
        id=1,
        tipo_documento=tipo,
        origem_tipo="VENDA",
        status="AUTORIZADA",
        data_autorizacao=datetime.now(timezone.utc) - timedelta(minutes=minutos_atras),
    )


def test_nfce_pode_ser_cancelada_dentro_de_30_minutos():
    _assert_dentro_da_janela_de_cancelamento(_doc("NFCE", minutos_atras=25))


def test_nfce_nao_pode_ser_cancelada_depois_de_30_minutos():
    with pytest.raises(HTTPException) as erro:
        _assert_dentro_da_janela_de_cancelamento(_doc("NFCE", minutos_atras=31))

    detalhe = erro.value.detail
    assert detalhe["codigo"] == "PRAZO_CANCELAMENTO_EXPIRADO"
    assert "30 minutos" in detalhe["mensagem"]
    assert "NFC-e" in detalhe["mensagem"]


def test_nfe_mantem_as_24_horas():
    """A janela é do modelo: encurtar a NF-e junto seria uma regressão."""
    _assert_dentro_da_janela_de_cancelamento(_doc("NFE", minutos_atras=23 * 60))

    with pytest.raises(HTTPException) as erro:
        _assert_dentro_da_janela_de_cancelamento(_doc("NFE", minutos_atras=25 * 60))

    assert "24 horas" in erro.value.detail["mensagem"]


def test_documento_sem_autorizacao_nao_e_barrado():
    doc = DocumentoFiscal(id=1, tipo_documento="NFCE", origem_tipo="VENDA",
                          status="PENDENTE", data_autorizacao=None)

    _assert_dentro_da_janela_de_cancelamento(doc)
