# ---------------------------------------------------------------------------
# ARQUIVO: test_busca.py
# DESCRIÇÃO: Testes do motor de busca textual compartilhado (core/busca.py).
#            São testes de unidade: não tocam o banco.
# ---------------------------------------------------------------------------

import pytest

from app.core.busca import (
    SIMILARIDADE_MINIMA,
    compactar,
    extrair_termos,
    normalizar,
    por_similaridade,
)


# =========================
# 1. Normalização
# =========================

@pytest.mark.parametrize("entrada, esperado", [
    ("Tinta Azul", "tinta azul"),
    ("AÇÚCAR", "acucar"),
    ("Café Gourmet Moído", "cafe gourmet moido"),
    ("Tinta Azul-Metálica", "tinta azul metalica"),
    ("  espaços   demais  ", "espacos demais"),
    ("123.456.789-00", "123 456 789 00"),
    ("", ""),
    (None, ""),
])
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("123.456.789-00", "12345678900"),
    ("BUSCA-ESPECIFICA", "buscaespecifica"),
    ("7891234 567890", "7891234567890"),
    (None, ""),
])
def test_compactar(entrada, esperado):
    assert compactar(entrada) == esperado


def test_normalizar_aceita_valor_nao_textual():
    """O SQLite entrega números crus quando a coluna é numérica."""
    assert normalizar(312) == "312"


# =========================
# 2. Extração de palavras
# =========================

def test_extrair_termos_quebra_e_normaliza():
    assert extrair_termos("Tinta Azul-Metálica") == ["tinta", "azul", "metalica"]


def test_extrair_termos_descarta_repetidas():
    assert extrair_termos("tinta tinta azul") == ["tinta", "azul"]


def test_extrair_termos_respeita_o_teto():
    termo = " ".join(f"palavra{i}" for i in range(20))
    assert len(extrair_termos(termo, maximo=8)) == 8


@pytest.mark.parametrize("entrada", ["", "   ", "!!!", None])
def test_extrair_termos_vazio(entrada):
    """Termo sem letra nem número não vira filtro — a lista volta inteira."""
    assert extrair_termos(entrada) == []


# =========================
# 3. Tolerância a erro de digitação
# =========================

class _Registro:
    def __init__(self, nome: str):
        self.nome = nome

    def __repr__(self) -> str:
        return f"_Registro({self.nome!r})"


def _nomes(registro: _Registro):
    return (registro.nome,)


def test_similaridade_acha_apesar_do_erro_de_digitacao():
    catalogo = [_Registro("Tinta Azul"), _Registro("Parafuso 3mm")]

    encontrados = por_similaridade("tnta", catalogo, _nomes)

    assert [r.nome for r in encontrados] == ["Tinta Azul"]


def test_similaridade_ignora_o_que_nao_se_parece():
    catalogo = [_Registro("Anel de Vedação"), _Registro("Cabo HDMI")]

    assert por_similaridade("tinta", catalogo, _nomes) == []


def test_similaridade_ordena_do_mais_parecido_ao_menos():
    catalogo = [_Registro("Tinta Guache"), _Registro("Tinta")]

    encontrados = por_similaridade("tinta", catalogo, _nomes)

    assert encontrados[0].nome == "Tinta"


def test_similaridade_sem_termo_nao_devolve_nada():
    """Sem termo não há o que resgatar — devolver o catálogo seria pior."""
    assert por_similaridade("", [_Registro("Tinta")], _nomes) == []


def test_similaridade_respeita_o_limite():
    catalogo = [_Registro(f"Tinta {i}") for i in range(10)]

    assert len(por_similaridade("tinta", catalogo, _nomes, limite=3)) == 3


def test_limiar_de_similaridade_documentado():
    """
    Se este valor mudar, a busca passa a aceitar (ou recusar) parecenças que
    hoje ela não aceita. É uma decisão de produto, não um detalhe interno.
    """
    assert SIMILARIDADE_MINIMA == pytest.approx(0.72)
