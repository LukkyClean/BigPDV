# ---------------------------------------------------------------------------
# ARQUIVO: test/core/test_registry_segmentos.py
# DESCRICAO: Guard do contrato de segmentos.
#
#            A REGRA que este teste protege: segmento novo so acrescenta
#            DECLARACAO. Isso so e seguro enquanto tudo que um segmento declara
#            for algo que o sistema sabe desenhar e gravar. Metadado orfao --
#            declarado e nao suportado -- e a unica forma de um segmento novo
#            quebrar uma tela que ja esta em producao.
#
#            Estes testes nao tocam banco: leem o registry, que e declaracao
#            pura, e falham no CI antes de chegar perto de uma loja.
# ---------------------------------------------------------------------------

import pytest

from app.core.segmentos import CAPACIDADES_CONHECIDAS, DEFINICOES
from app.core.segmentos.campos import (
    ESCOPOS_SUPORTADOS,
    LARGURAS_SUPORTADAS,
    ORIGENS_SUPORTADAS,
    TIPOS_DE_CAMPO_SUPORTADOS,
)
from app.db.models.objeto_servico import ObjetoServico

# Colunas reais da tabela, para conferir quem declara origem="coluna".
COLUNAS_OBJETO = set(ObjetoServico.__table__.columns.keys())


def _todos_os_campos():
    """(segmento, campo) de todos os campos declarados por todos os segmentos."""
    for segmento, definicao in DEFINICOES.items():
        for chave in ("veiculo", "checkin"):
            for campo in definicao.get(chave, []):
                yield segmento, campo


def _ids(par):
    segmento, campo = par
    return f"{segmento}:{campo['nome']}"


CAMPOS = list(_todos_os_campos())


def test_registry_tem_pelo_menos_os_segmentos_conhecidos():
    """Se algum segmento sumir do mapa, a tela dele para de receber contrato."""
    assert "oficina_mecanica" in DEFINICOES
    assert "assistencia_tecnica" in DEFINICOES


def test_chave_do_mapa_bate_com_o_segmento_declarado():
    """DEFINICOES e montado a partir da chave "segmento" de cada definicao;
    divergencia aqui significaria segmento inalcancavel."""
    for chave, definicao in DEFINICOES.items():
        assert definicao["segmento"] == chave


def test_toda_definicao_tem_rotulos_e_identificador():
    for segmento, definicao in DEFINICOES.items():
        assert definicao.get("rotulo_objeto_singular"), segmento
        assert definicao.get("rotulo_objeto_plural"), segmento
        identificador = definicao.get("identificador")
        assert identificador, segmento
        assert set(identificador) >= {"nome", "label", "regex"}, segmento


def test_capacidades_declaradas_sao_conhecidas():
    """Capacidade inventada nao liga nada no frontend -- falha silenciosa."""
    for segmento, definicao in DEFINICOES.items():
        for capacidade in definicao.get("capacidades", []):
            assert capacidade in CAPACIDADES_CONHECIDAS, f"{segmento}: {capacidade}"


@pytest.mark.parametrize("par", CAMPOS, ids=_ids)
def test_campo_usa_vocabulario_suportado(par):
    """O coracao do guard: tipo/escopo/largura/origem tem que ser desenhaveis."""
    segmento, campo = par
    assert campo["tipo"] in TIPOS_DE_CAMPO_SUPORTADOS, f"{segmento}:{campo['nome']}"
    assert campo["escopo"] in ESCOPOS_SUPORTADOS, f"{segmento}:{campo['nome']}"
    assert campo["largura"] in LARGURAS_SUPORTADAS, f"{segmento}:{campo['nome']}"
    assert campo["origem"] in ORIGENS_SUPORTADAS, f"{segmento}:{campo['nome']}"


@pytest.mark.parametrize("par", CAMPOS, ids=_ids)
def test_campo_de_opcao_declara_opcoes(par):
    """Select sem opcoes vira campo morto na tela."""
    segmento, campo = par
    if campo["tipo"] == "opcao":
        assert campo.get("opcoes"), f"{segmento}:{campo['nome']}"


@pytest.mark.parametrize("par", CAMPOS, ids=_ids)
def test_campo_de_coluna_aponta_para_coluna_que_existe(par):
    """O guard mais importante.

    `origem="coluna"` faz o valor ir para uma coluna real; se o nome estiver
    errado, grava-se no lugar errado (ou em lugar nenhum). O campo pode usar
    `coluna` quando o nome dele difere do nome da coluna -- e o caso de
    `placa`, que e a coluna `numero_serie`.
    """
    segmento, campo = par
    if campo["origem"] != "coluna":
        return
    if campo["escopo"] != "objeto":
        return
    alvo = campo.get("coluna", campo["nome"])
    assert alvo in COLUNAS_OBJETO, (
        f"{segmento}:{campo['nome']} declara origem=coluna apontando para "
        f"'{alvo}', que nao existe em objetos_servico"
    )


def test_nomes_de_campo_nao_se_repetem_dentro_do_segmento():
    """veiculo e checkin caem no mesmo espaco de nomes no formulario; nome
    repetido faria um campo sobrescrever o outro em silencio."""
    for segmento, definicao in DEFINICOES.items():
        nomes = [
            campo["nome"]
            for chave in ("veiculo", "checkin")
            for campo in definicao.get(chave, [])
        ]
        assert len(nomes) == len(set(nomes)), f"{segmento}: {nomes}"
