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


def _campos_da_definicao(definicao):
    """Todos os campos de uma definicao, venham de onde vierem.

    Segmento sem tipos de trabalho declara em `veiculo`/`checkin`; segmento com
    tipos (serigrafia) declara dentro de cada tipo. O guard tem que enxergar os
    dois, senao o caminho novo passaria sem conferencia -- que e justamente o
    caminho que ninguem testou ainda.
    """
    for chave in ("veiculo", "checkin"):
        for campo in definicao.get(chave, []):
            yield campo
    for tipo in definicao.get("tipos", []):
        for campo in tipo.get("campos", []):
            yield campo


def _todos_os_campos():
    """(segmento, campo) de todos os campos declarados por todos os segmentos."""
    for segmento, definicao in DEFINICOES.items():
        for campo in _campos_da_definicao(definicao):
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


def test_nomes_de_campo_nao_se_repetem_no_mesmo_formulario():
    """Campos do mesmo formulario caem no mesmo espaco de nomes; nome repetido
    faria um sobrescrever o outro em silencio.

    Em segmento com tipos de trabalho a conferencia e POR TIPO -- dois tipos
    podem ter "cor_impressao" cada um, porque nunca aparecem juntos na tela.
    """
    for segmento, definicao in DEFINICOES.items():
        formularios = {
            "veiculo+checkin": [
                campo["nome"]
                for chave in ("veiculo", "checkin")
                for campo in definicao.get(chave, [])
            ],
        }
        for tipo in definicao.get("tipos", []):
            formularios[f"tipo:{tipo['id']}"] = [c["nome"] for c in tipo.get("campos", [])]

        for qual, nomes in formularios.items():
            assert len(nomes) == len(set(nomes)), f"{segmento}/{qual}: {nomes}"


def test_tipos_de_trabalho_sao_bem_formados():
    """Tipo sem id/label vira opcao vazia no seletor; id repetido faz um tipo
    ficar inalcancavel."""
    for segmento, definicao in DEFINICOES.items():
        tipos = definicao.get("tipos", [])
        if not tipos:
            continue
        ids = []
        for tipo in tipos:
            assert tipo.get("id"), f"{segmento}: tipo sem id"
            assert tipo.get("label"), f"{segmento}: tipo {tipo.get('id')} sem label"
            assert tipo.get("campos"), f"{segmento}: tipo {tipo['id']} sem campos"
            ids.append(tipo["id"])
        assert len(ids) == len(set(ids)), f"{segmento}: ids repetidos {ids}"


def test_segmento_com_tipos_nao_usa_veiculo_nem_checkin():
    """As duas formas de declarar campo se excluem: misturar faria a tela
    dinamica ignorar `veiculo`/`checkin` sem ninguem perceber."""
    for segmento, definicao in DEFINICOES.items():
        if not definicao.get("tipos"):
            continue
        assert not definicao.get("veiculo"), segmento
        assert not definicao.get("checkin"), segmento
