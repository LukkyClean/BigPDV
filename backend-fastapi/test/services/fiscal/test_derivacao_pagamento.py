# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_derivacao_pagamento.py
# DESCRIÇÃO: Dedução do código SEFAZ (tPag) pelo nome da forma de pagamento.
#
# O defeito que originou isto: uma forma criada pela loja nascia sem código,
# virava pendência que IMPEDE a emissão, e não tinha como ser resolvida pela
# interface — o campo não existe em tela nenhuma, embora a API o aceite.
# ---------------------------------------------------------------------------

import pytest

from app.services.fiscal.derivacao.pagamento import (
    Confianca,
    codigo_sefaz_por_nome,
    derivar_forma_pagamento,
    tipo_integracao_por_codigo,
)


@pytest.mark.parametrize("nome, esperado", [
    # As seis padrao, que ja eram semeadas no startup.
    ("Dinheiro", "01"),
    ("PIX", "17"),
    ("Cartão de Crédito", "03"),
    ("Cartão de Débito", "04"),
    ("Boleto", "15"),
    ("Transferência Bancária", "15"),
    # As que a loja cria e antes ficavam sem codigo.
    ("Vale Refeição", "11"),
    ("Vale Alimentação", "10"),
    ("Vale Combustível", "13"),
    ("Vale Presente", "12"),
    ("Crediário", "05"),
    ("Fiado", "05"),
    ("Caderneta", "05"),
    ("Cheque", "02"),
])
def test_deduz_o_codigo_pelo_nome(nome, esperado):
    assert codigo_sefaz_por_nome(nome) == esperado


@pytest.mark.parametrize("nome", [
    "cartao de credito",   # sem acento
    "CARTÃO DE CRÉDITO",   # caixa alta
    "  Cartão de Crédito ",  # espacos nas bordas
])
def test_acento_e_caixa_nao_atrapalham(nome):
    assert codigo_sefaz_por_nome(nome) == "03"


def test_debito_e_credito_vencem_o_generico_cartao():
    """
    "Cartão de Crédito" contem "cartao" E "credito". Se o generico fosse
    avaliado antes, toda forma com cartao no nome cairia no mesmo codigo.
    """
    assert codigo_sefaz_por_nome("Cartão de Débito") == "04"
    assert codigo_sefaz_por_nome("Cartão de Crédito") == "03"
    # O generico so pega o que nao disse qual e.
    assert codigo_sefaz_por_nome("Cartão da Loja") == "03"


@pytest.mark.parametrize("nome", ["", "   ", None, "Xyz Abc"])
def test_nome_irreconhecivel_nao_inventa_codigo(nome):
    assert codigo_sefaz_por_nome(nome) is None


@pytest.mark.parametrize("codigo, esperado", [
    ("03", "POS"),
    ("04", "POS"),
    ("01", "NAO_SE_APLICA"),
    ("17", "NAO_SE_APLICA"),
    (None, "NAO_SE_APLICA"),
])
def test_integracao_so_existe_em_cartao(codigo, esperado):
    assert tipo_integracao_por_codigo(codigo) == esperado


def test_forma_desconhecida_pede_confirmacao():
    """
    99 (Outros) e aceito pela SEFAZ, mas descreve mal a operacao. Aplicar
    sozinho esconderia do lojista uma escolha que e dele.
    """
    sugestoes = {s.campo: s for s in derivar_forma_pagamento("Bitcoin")}

    assert sugestoes["codigo_sefaz"].valor == "99"
    assert sugestoes["codigo_sefaz"].confianca == Confianca.AMBIGUA
    assert sugestoes["codigo_sefaz"].exige_confirmacao is True
    assert sugestoes["codigo_sefaz"].alternativas


def test_forma_reconhecida_nao_pede_confirmacao():
    sugestoes = {s.campo: s for s in derivar_forma_pagamento("PIX")}

    assert sugestoes["codigo_sefaz"].valor == "17"
    assert sugestoes["codigo_sefaz"].exige_confirmacao is False
    assert sugestoes["tipo_integracao"].valor == "NAO_SE_APLICA"


def test_cartao_novo_ja_nasce_com_a_maquininha_declarada():
    sugestoes = {s.campo: s for s in derivar_forma_pagamento("Cartão de Débito Elo")}

    assert sugestoes["codigo_sefaz"].valor == "04"
    assert sugestoes["tipo_integracao"].valor == "POS"
