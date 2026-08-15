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
from app.core.segmentos.capacidades import CAP_GARANTIA_PRAZO, CAP_IMAGEM_NA_ENTRADA
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
    """Todo segmento COM OS descreve o objeto que entra na loja.

    Quem nao tem OS e dispensado do identificador, e nao por conveniencia: sem
    Ordem de Servico nao existe objeto de servico para identificar. Exigir um
    obrigaria o PDV a inventar "numero de serie" para uma garrafa de cerveja.
    """
    for segmento, definicao in DEFINICOES.items():
        assert definicao.get("rotulo_objeto_singular"), segmento
        assert definicao.get("rotulo_objeto_plural"), segmento

        if not definicao.get("usa_ordem_servico", True):
            assert not definicao.get("checkin"), f"{segmento}: sem OS, nao ha check-in"
            assert not definicao.get("vistoria"), f"{segmento}: sem OS, nao ha vistoria"
            continue

        identificador = definicao.get("identificador")
        assert identificador, segmento
        assert set(identificador) >= {"nome", "label", "regex"}, segmento


def test_ordem_de_servico_e_o_padrao_para_quem_nao_declara():
    """A trava mais importante desta regra.

    Se o padrao virasse "so tem OS quem declarar", ligar isto apagaria o modulo
    de Ordem de Servico de toda loja cujo segmento nao tem arquivo de definicao
    -- marcenaria, eletricista, outros, e qualquer empresa cadastrada sem
    segmento. O sintoma na loja seria "sumiu o menu de Servicos".
    """
    from app.core.segmentos import segmento_usa_ordem_servico

    # Os tres que ja rodam em producao.
    assert segmento_usa_ordem_servico("assistencia_tecnica") is True
    assert segmento_usa_ordem_servico("oficina_mecanica") is True
    assert segmento_usa_ordem_servico("serigrafia") is True

    # Segmentos sem arquivo de definicao continuam com OS.
    assert segmento_usa_ordem_servico("marcenaria") is True
    assert segmento_usa_ordem_servico("eletricista") is True
    assert segmento_usa_ordem_servico("outros") is True
    assert segmento_usa_ordem_servico("segmento_que_nao_existe") is True

    # Instalacao antiga, sem segmento gravado.
    assert segmento_usa_ordem_servico(None) is True

    # O unico que nao tem.
    assert segmento_usa_ordem_servico("pdv") is False


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


def test_identificador_gerado_nao_e_pedido_ao_usuario():
    """A regra que nasceu do erro do "Codigo da arte".

    Se o SISTEMA gera o identificador, o formulario nao pode pedi-lo: campo
    obrigatorio que o usuario nao tem como preencher vira lixo ("1", "teste"),
    e lixo como chave faz dois bens distintos colapsarem num cadastro so.

    Placa e numero de serie NAO sao gerados justamente porque existem no mundo
    -- estao escritos no bem, e o atendente so copia.
    """
    for segmento, definicao in DEFINICOES.items():
        identificador = definicao.get("identificador") or {}
        if not identificador.get("gerado"):
            continue

        assert identificador.get("prefixo"), f"{segmento}: identificador gerado sem prefixo"

        declarados = {c["nome"] for c in _campos_da_definicao(definicao)}
        assert identificador["nome"] not in declarados, (
            f"{segmento}: '{identificador['nome']}' e gerado pelo sistema, mas esta "
            f"declarado como campo do formulario -- o usuario seria obrigado a "
            f"inventar um valor que ele nao tem como saber"
        )


def test_segmento_com_tipos_nao_usa_veiculo_nem_checkin():
    """As duas formas de declarar campo se excluem: misturar faria a tela
    dinamica ignorar `veiculo`/`checkin` sem ninguem perceber."""
    for segmento, definicao in DEFINICOES.items():
        if not definicao.get("tipos"):
            continue
        assert not definicao.get("veiculo"), segmento
        assert not definicao.get("checkin"), segmento


# ===========================================================================
# Campo `lista` (repetivel)
# ===========================================================================

def test_sacola_pede_referencias_e_nao_medida_unica():
    """
    O dono da serigrafia trabalha por REFERENCIA ("20.1", "22", "Bolo"), nao por
    medida em centimetros, e uma mesma producao sai com varios tamanhos -- o
    campo precisa ser repetivel.

    Trava as duas pontas: que os dois tipos de sacola declaram `referencias` do
    tipo `lista`, e que a `medidas` de valor unico saiu de cena (era ela que
    obrigava a escrever tudo numa linha so).
    """
    tipos_de_sacola = [
        tipo
        for tipo in DEFINICOES["serigrafia"].get("tipos", [])
        if tipo["id"].startswith("sacola_")
    ]
    assert tipos_de_sacola, "serigrafia deveria declarar tipos de sacola"

    for tipo in tipos_de_sacola:
        por_nome = {campo["nome"]: campo for campo in tipo["campos"]}

        assert "referencias" in por_nome, f"{tipo['id']}: sem campo de referencias"
        assert por_nome["referencias"]["tipo"] == "lista", (
            f"{tipo['id']}: referencia precisa ser repetivel"
        )
        assert "medidas" not in por_nome, (
            f"{tipo['id']}: 'medidas' foi substituido por 'referencias'"
        )


def test_ids_dos_tipos_da_serigrafia_sao_contrato_com_o_frontend():
    """
    Estes ids nao sao detalhe interno: o pacote de textos das vias impressas
    (frontend/src/modules/order-service/shared/segmento/textosImpressaoOS.ts)
    indexa `porTipoTrabalho` por eles para trocar os termos entre camisa e
    sacola -- a clausula de "pecas entregues pelo cliente" vale para camisa e
    nao para sacola, que a loja produz do zero.

    Renomear um id aqui nao quebraria build nenhum: a sobrescrita simplesmente
    deixaria de casar, e a via da sacola voltaria a sair com o texto de camisa,
    em silencio, no papel entregue ao cliente. Este teste e o aviso.
    """
    ids = {tipo["id"] for tipo in DEFINICOES["serigrafia"].get("tipos", [])}

    assert {"camisa", "sacola_plastica", "sacola_papel"} <= ids, (
        f"ids esperados pelo pacote de textos das vias nao encontrados: {ids}"
    )


def test_imagem_na_entrada_e_exclusiva_da_serigrafia_por_enquanto():
    """
    A capacidade libera a aba de imagens durante a CRIACAO da OS e imprime as
    imagens na via de entrada.

    Em serigrafia a imagem e a arte a estampar: sem ela nao ha o que produzir, e
    quem pinta trabalha a partir do papel. Em oficina e informatica a foto e
    prova do estado do bem -- nasce depois, com o aparelho na bancada, e nao vai
    para a via do cliente.

    Ligar isto em oficina ou informatica passaria a imprimir foto de aparelho na
    via de entrada dos dois clientes em producao. Se um dia for intencional,
    este teste e o lugar de dizer isso em voz alta.
    """
    assert CAP_IMAGEM_NA_ENTRADA in DEFINICOES["serigrafia"]["capacidades"]
    assert CAP_IMAGEM_NA_ENTRADA not in DEFINICOES["oficina_mecanica"]["capacidades"]
    assert CAP_IMAGEM_NA_ENTRADA not in DEFINICOES["assistencia_tecnica"]["capacidades"]


def test_garantia_por_prazo_segue_ligada_em_quem_conserta():
    """
    A garantia em dias e obrigatoria em oficina e informatica desde sempre --
    desligar aqui deixaria de exigir o prazo e faria a via de saida das duas
    lojas em producao sair sem o Termo de Garantia.

    Serigrafia nao declara: estampa nao tem prazo (se dura, mede-se em lavagens)
    e o fallback da via prometeria "90 (noventa) dias" que a loja nunca deu.
    """
    assert CAP_GARANTIA_PRAZO in DEFINICOES["oficina_mecanica"]["capacidades"]
    assert CAP_GARANTIA_PRAZO in DEFINICOES["assistencia_tecnica"]["capacidades"]
    assert CAP_GARANTIA_PRAZO not in DEFINICOES["serigrafia"]["capacidades"]


def test_rotulos_de_situacao_nao_inventam_valor_de_enum():
    """
    O desfecho e o MESMO enum em todo segmento: ele carrega a regra de dispensar
    o pagamento integral (SEM_REPARO/CONDENADO) e alimenta filtro, relatorio e
    historico. So os ROTULOS mudam.

    Uma chave fora do enum viraria botao que nunca casa com o valor salvo --
    silenciosamente, porque o frontend cai no rotulo padrao.
    """
    validas = {"REPARADO", "SEM_REPARO", "CONDENADO"}

    for segmento, definicao in DEFINICOES.items():
        rotulos = definicao.get("rotulos_situacao")
        if not rotulos:
            continue  # segmento sem rotulo proprio usa o de conserto
        assert set(rotulos) <= validas, f"{segmento}: chave fora do enum -> {set(rotulos) - validas}"
        assert all(str(v).strip() for v in rotulos.values()), f"{segmento}: rotulo vazio"


def test_objeto_feminino_declara_o_titulo_da_situacao_inteiro():
    """
    A tela montava 'Situacao do ' + rotulo do objeto, o que exibia
    "SITUACAO DO ARTE". Objeto de genero feminino precisa declarar o titulo
    inteiro -- e a mesma razao pela qual `tituloObjeto` existe no pacote de
    textos das vias.
    """
    serigrafia = DEFINICOES["serigrafia"]
    assert serigrafia.get("rotulo_situacao") == "Situação da Arte"
