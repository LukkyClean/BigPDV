# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_nfce_pdv.py
# DESCRIÇÃO: Fase 2 — o que o fechamento do PDV acrescenta à NFC-e.
#
# Cobre três coisas que só existem por causa do caixa:
#   1. O CPF avulso, digitado sem cadastro, e sua validação.
#   2. A classificação da maquininha (TEF x POS) no grupo `card`.
#   3. O mascaramento do CSC — o segredo não pode voltar inteiro para a tela.
# ---------------------------------------------------------------------------

import pytest
from pydantic import ValidationError

from app.db.models.forma_pagamento import FormaPagamento
from app.schemas.venda_nota_fiscal import VendaNotaFiscalUpdate
from app.services.fiscal.helpers import (
    cifrar_csc_token,
    e_csc_mascarado,
    mascarar_csc,
    obter_csc_token,
)
from app.services.fiscal.payload_builder import _montar_pagamentos

from test.services.fiscal.test_payload_builder import (
    _item_venda,
    _produto,
    _venda,
)


# =========================
# 1. CPF avulso no fechamento
# =========================

@pytest.mark.parametrize("entrada, esperado", [
    ("52998224725", "52998224725"),        # CPF limpo
    ("529.982.247-25", "52998224725"),     # com máscara da tela
    ("  52998224725  ", "52998224725"),    # com espaço colado
    ("11222333000181", "11222333000181"),  # CNPJ (compra por empresa)
    ("11.222.333/0001-81", "11222333000181"),
])
def test_documento_do_consumidor_e_normalizado(entrada, esperado):
    nota = VendaNotaFiscalUpdate(documento_consumidor=entrada)

    assert nota.documento_consumidor == esperado


@pytest.mark.parametrize("vazio", ["", "   ", None])
def test_documento_em_branco_e_o_caso_normal(vazio):
    """
    A maioria das vendas de balcão não tem CPF. Vazio precisa passar como
    None, e não estourar validação — senão o caixa trava na venda comum.
    """
    assert VendaNotaFiscalUpdate(documento_consumidor=vazio).documento_consumidor is None


@pytest.mark.parametrize("invalido", [
    "11111111111",       # CPF de dígito repetido
    "12345678901",       # dígito verificador errado
    "12345678000199",    # CNPJ com DV errado
])
def test_documento_invalido_e_recusado_no_fechamento(invalido):
    """
    Recusar aqui é barato. Recusar na SEFAZ custa o número da NFC-e, que já
    foi consumido, e obriga a inutilizá-lo por causa de um erro de digitação.
    """
    with pytest.raises(ValidationError):
        VendaNotaFiscalUpdate(documento_consumidor=invalido)


@pytest.mark.parametrize("tamanho_errado", ["123", "5299822472", "529982247251"])
def test_documento_com_tamanho_errado_diz_o_que_se_espera(tamanho_errado):
    with pytest.raises(ValidationError, match="11 dígitos"):
        VendaNotaFiscalUpdate(documento_consumidor=tamanho_errado)


# =========================
# 2. Maquininha: TEF x POS
# =========================

def _pagamento_cartao(valor, codigo_sefaz="03", tipo_integracao=None):
    from app.db.models.venda_pagamento import PagamentoVenda

    return PagamentoVenda(
        valor=valor,
        forma_pagamento=FormaPagamento(
            id=1, nome="Cartão de Crédito",
            codigo_sefaz=codigo_sefaz, tipo_integracao=tipo_integracao,
        ),
    )


def _venda_com(pagamento, total=10000):
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=total)]
    return _venda(itens, [pagamento])


@pytest.mark.parametrize("integracao, tp_integra", [("TEF", 1), ("POS", 2)])
def test_cartao_declara_o_tipo_de_integracao(integracao, tp_integra):
    venda = _venda_com(_pagamento_cartao(10000, tipo_integracao=integracao))

    pagamentos = _montar_pagamentos(venda)

    assert pagamentos[0]["tipo_integracao"] == tp_integra


def test_cartao_sem_classificacao_assume_pos():
    """
    POS é o padrão seguro: afirmar integração TEF que não existe descreveria
    mal a operação num documento fiscal.
    """
    venda = _venda_com(_pagamento_cartao(10000, tipo_integracao=None))

    assert _montar_pagamentos(venda)[0]["tipo_integracao"] == 2


def test_cartao_de_debito_tambem_declara():
    venda = _venda_com(_pagamento_cartao(10000, codigo_sefaz="04"))

    assert _montar_pagamentos(venda)[0]["tipo_integracao"] == 2


@pytest.mark.parametrize("codigo", ["01", "17", "15", "99"])
def test_pagamento_sem_maquininha_nao_leva_o_grupo(codigo):
    """Dinheiro, PIX e boleto não passam por maquininha — o grupo é ruído."""
    venda = _venda_com(_pagamento_cartao(10000, codigo_sefaz=codigo))

    assert "tipo_integracao" not in _montar_pagamentos(venda)[0]


def test_nao_se_aplica_marcado_em_cartao_omite_o_grupo():
    venda = _venda_com(_pagamento_cartao(10000, tipo_integracao="NAO_SE_APLICA"))

    assert "tipo_integracao" not in _montar_pagamentos(venda)[0]


# =========================
# 3. Mascaramento do CSC
# =========================

def test_csc_sai_mascarado_para_a_tela():
    mascarado = mascarar_csc("CSC-SECRETO-AB12")

    assert "CSC-SECRETO" not in mascarado
    assert mascarado.endswith("AB12")  # o bastante para reconhecer qual é


def test_csc_curto_nao_revela_nada():
    """Token curto não pode ter 'os 4 últimos' revelando o token inteiro."""
    assert mascarar_csc("abc") == "•" * 8


def test_csc_ausente_continua_ausente():
    assert mascarar_csc(None) is None
    assert mascarar_csc("") is None


def test_mascara_e_reconhecida_no_retorno():
    """
    A tela devolve o que recebeu. Gravar a máscara destruiria o CSC sem
    ninguém perceber — o erro só apareceria na primeira venda, com o cupom
    sem QR Code válido.
    """
    assert e_csc_mascarado(mascarar_csc("CSC-SECRETO-AB12")) is True


def test_token_real_nao_e_confundido_com_mascara():
    assert e_csc_mascarado("CSCREAL123") is False
    assert e_csc_mascarado(None) is False


def test_ciclo_completo_cifra_mascara_e_recupera():
    guardado = cifrar_csc_token("CSC-SECRETO-AB12")

    assert guardado != "CSC-SECRETO-AB12"                  # cifrado no banco
    assert obter_csc_token(_FS(guardado)) == "CSC-SECRETO-AB12"  # uso interno
    assert "SECRETO" not in mascarar_csc(obter_csc_token(_FS(guardado)))


class _FS:
    """Stub mínimo de EmpresaFiscalSettings — só o campo que importa aqui."""

    def __init__(self, csc_token):
        self.csc_token = csc_token


# =========================
# 4. Ciclo real do CSC pela configuração fiscal
# =========================

def test_salvar_a_mascara_nao_destroi_o_csc(monkeypatch):
    """
    O caminho que mais quebra em silêncio: a tela recebe o CSC mascarado e
    devolve o objeto inteiro ao salvar qualquer outro campo. Se a máscara
    fosse gravada, o CSC sumiria — e o erro só apareceria na próxima venda,
    com o cupom saindo sem QR Code válido.
    """
    from app.schemas.empresa import FiscalSettingsUpdate
    from app.services import empresa as empresa_service

    guardado = cifrar_csc_token("CSC-ORIGINAL-9999")
    settings = _FiscalSettingsFake(csc_token=guardado, serie_nfce=1)

    monkeypatch.setattr(
        empresa_service, "get_or_create_fiscal_settings",
        lambda db, empresa_id: settings,
    )

    # A tela devolve a máscara junto de uma alteração legítima de série.
    empresa_service.update_fiscal_settings(
        _DbFake(), 1,
        FiscalSettingsUpdate(csc_token=mascarar_csc("CSC-ORIGINAL-9999"), serie_nfce=7),
    )

    assert obter_csc_token(settings) == "CSC-ORIGINAL-9999"  # intacto
    assert settings.serie_nfce == 7                          # o resto gravou


def test_token_novo_substitui_e_fica_cifrado(monkeypatch):
    from app.schemas.empresa import FiscalSettingsUpdate
    from app.services import empresa as empresa_service

    settings = _FiscalSettingsFake(csc_token=cifrar_csc_token("ANTIGO"), serie_nfce=1)
    monkeypatch.setattr(
        empresa_service, "get_or_create_fiscal_settings",
        lambda db, empresa_id: settings,
    )

    empresa_service.update_fiscal_settings(
        _DbFake(), 1, FiscalSettingsUpdate(csc_token="CSC-NOVO-1234"),
    )

    assert settings.csc_token != "CSC-NOVO-1234"        # não ficou em texto puro
    assert obter_csc_token(settings) == "CSC-NOVO-1234"  # e é recuperável


class _FiscalSettingsFake:
    """Stub de EmpresaFiscalSettings — aceita qualquer atributo, como o ORM."""

    def __init__(self, **campos):
        for chave, valor in campos.items():
            setattr(self, chave, valor)


class _DbFake:
    def flush(self):
        pass

    def refresh(self, _obj):
        pass


def test_csc_cifrado_cabe_no_schema_de_leitura():
    """
    Regressão: o CSC cifrado tem ~120 caracteres para um token de 16, mas a
    coluna e o schema nasceram com limite 100 — pensados para o segredo em
    texto puro. Ler a configuração salva estourava a validação.
    """
    from app.schemas.empresa import FiscalSettingsRead

    cifrado = cifrar_csc_token("CSC-SECRETO-AB12")
    assert len(cifrado) > 100  # é isso que quebrava

    lido = FiscalSettingsRead(id=1, empresa_id=1, csc_token=cifrado).model_dump()

    assert lido["csc_token"] == "••••••••AB12"


def test_resposta_de_empresa_nao_carrega_o_csc():
    """
    O formulário de empresa também traz `fiscal_settings`. Mascarar só no
    Centro Fiscal deixaria o segredo saindo por esta outra porta.
    """
    from app.schemas.empresa import FiscalSettingsRead

    lido = FiscalSettingsRead(
        id=1, empresa_id=1, csc_token=cifrar_csc_token("CSC-SECRETO-AB12"),
    ).model_dump()

    assert "SECRETO" not in str(lido)
    assert not str(lido["csc_token"]).startswith("gAAAA")  # nem o blob cifrado
