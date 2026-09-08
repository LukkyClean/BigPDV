# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_derivacao.py
# DESCRIÇÃO: Tabela de decisão da derivação fiscal.
#
# Regras confirmadas com a contabilidade em 05/09/2026. Escopo: Ceará,
# operação interna — o primeiro dígito do CFOP é sempre 5.
# ---------------------------------------------------------------------------

import pytest

from app.services.fiscal.derivacao import (
    Confianca,
    ContextoDerivacao,
    DerivacaoAmbiguaError,
    TipoAtividade,
    derivar_cfop,
    derivar_consumidor_final,
    derivar_cst_pis_cofins,
    derivar_local_destino,
    derivar_natureza_operacao,
    derivar_origem_mercadoria,
    derivar_produto,
    derivar_situacao_icms,
)

CRT_SIMPLES = 1
CRT_MEI = 4
CRT_EXCESSO = 2
CRT_NORMAL = 3


def _ctx(**kwargs) -> ContextoDerivacao:
    base = dict(uf_emitente="CE", crt=CRT_SIMPLES, tipo_atividade=TipoAtividade.COMERCIO)
    base.update(kwargs)
    return ContextoDerivacao(**base)


# =========================
# 1. CFOP — a tabela de decisão
# =========================

@pytest.mark.parametrize("atividade, situacao, finalidade, esperado", [
    # Revenda pura: o caso dominante do PDV.
    (TipoAtividade.COMERCIO, "102", 1, "5102"),
    (TipoAtividade.SERVICO, "102", 1, "5102"),
    # Producao propria — industria, panificacao, marcenaria, beneficiamento.
    (TipoAtividade.INDUSTRIA, "102", 1, "5101"),
    (TipoAtividade.MISTO, "00", 1, "5101"),
    # Mercadoria com ICMS ja retido por ST.
    (TipoAtividade.COMERCIO, "500", 1, "5405"),
    (TipoAtividade.COMERCIO, "60", 1, "5405"),
    # ST vence producao propria: o que manda e a tributacao do item.
    (TipoAtividade.INDUSTRIA, "60", 1, "5405"),
    # Devolucao de compra, em operacao de SAIDA (o grupo 1.xxx e entrada).
    (TipoAtividade.COMERCIO, "102", 4, "5202"),
    # Devolucao vence ST e producao propria.
    (TipoAtividade.INDUSTRIA, "60", 4, "5202"),
])
def test_tabela_de_decisao_do_cfop(atividade, situacao, finalidade, esperado):
    ctx = _ctx(tipo_atividade=atividade, finalidade_emissao=finalidade)

    assert derivar_cfop(ctx, situacao_tributaria=situacao).valor == esperado


def test_servico_em_documento_de_mercadoria():
    assert derivar_cfop(_ctx(), tipo_item="SERVICO").valor == "5933"


def test_nfce_e_sempre_interna():
    """Modelo 65 nao existe fora da operacao interna."""
    ctx = _ctx(modelo_documento=65, uf_destinatario="SP")

    assert derivar_cfop(ctx, situacao_tributaria="102").valor.startswith("5")


def test_venda_presencial_e_interna_mesmo_com_cliente_de_fora():
    """
    A mercadoria sai pelo balcao e nao cruza fronteira. Travar por endereco
    impediria faturar para qualquer cliente de outro estado.
    """
    ctx = _ctx(indicador_presenca=1, uf_destinatario="SP")

    assert derivar_cfop(ctx, situacao_tributaria="102").valor == "5102"


def test_entrega_interestadual_nao_presencial_vira_grupo_6():
    ctx = _ctx(indicador_presenca=4, uf_destinatario="SP")

    assert derivar_cfop(ctx, situacao_tributaria="102").valor == "6102"


def test_saida_interestadual_de_substituido_se_recusa_a_chutar():
    """
    Nao existe equivalente interestadual limpo do 5.405 — confirmado com a
    contabilidade. A operacao vira 6.102 ou 6.403/6.404 conforme o protocolo
    entre as UFs, e quem decide isso e o contador.
    """
    ctx = _ctx(indicador_presenca=4, uf_destinatario="SP")

    with pytest.raises(DerivacaoAmbiguaError, match="6.403"):
        derivar_cfop(ctx, situacao_tributaria="60")


def test_producao_propria_oferece_a_revenda_como_alternativa():
    """
    Uma padaria vende pao proprio (5101) e refrigerante revendido (5102) na
    mesma nota. O CNAE decide o default; o produto sobrescreve.
    """
    sugestao = derivar_cfop(_ctx(tipo_atividade=TipoAtividade.INDUSTRIA))

    assert sugestao.confianca == Confianca.PROVAVEL
    assert ("5102", "Revenda de mercadoria de terceiros") in sugestao.alternativas


# =========================
# 2. Natureza da operação
# =========================

@pytest.mark.parametrize("cfop, trecho", [
    ("5102", "adquirida de terceiros"),
    ("5101", "producao do estabelecimento"),
    ("5405", "sujeita a ST"),
    ("5933", "servico"),
])
def test_natureza_vem_da_descricao_oficial(cfop, trecho):
    assert trecho in derivar_natureza_operacao(cfop).valor


def test_devolucao_avisa_que_desliga_os_tributos_aproximados():
    """
    A integradora dispensa o calculo do vTotTrib quando a natureza contem
    DEVOLUCAO. O cupom sai sem a linha de tributos aproximados — infracao a
    Lei 12.741/2012. Nao pode passar em silencio.
    """
    sugestao = derivar_natureza_operacao("5202")

    assert sugestao.exige_confirmacao is True
    assert "12.741" in sugestao.fundamentacao


def test_venda_normal_nao_exige_confirmacao():
    assert derivar_natureza_operacao("5102").exige_confirmacao is False


# =========================
# 3. Situação tributária por regime
# =========================

@pytest.mark.parametrize("crt, campo, valor", [
    (CRT_SIMPLES, "csosn", "102"),
    (CRT_MEI, "csosn", "102"),
    (CRT_NORMAL, "cst_icms", "00"),
    # CRT 2 tributa o excedente pelo regime normal: usa CST, nao CSOSN.
    (CRT_EXCESSO, "cst_icms", "00"),
])
def test_situacao_icms_por_regime(crt, campo, valor):
    sugestao = derivar_situacao_icms(_ctx(crt=crt))

    assert sugestao.campo == campo
    assert sugestao.valor == valor


def test_csosn_101_nunca_e_derivado():
    """
    Depende da faixa de receita do mes. Derivar faz a loja transferir credito
    indevido e responder por ele.
    """
    sugestao = derivar_situacao_icms(_ctx(crt=CRT_SIMPLES))

    assert sugestao.valor != "101"
    # Fica como alternativa explicita, com o motivo.
    assert any(alt[0] == "101" for alt in sugestao.alternativas)


def test_st_nunca_e_derivada_por_inferencia():
    """
    Se o item nao esta em ST na UF, a nota sai com ICMS zerado e e ACEITA.
    O imposto simplesmente nao foi recolhido.
    """
    for crt in (CRT_SIMPLES, CRT_NORMAL):
        sugestao = derivar_situacao_icms(_ctx(crt=crt))
        assert sugestao.valor not in ("60", "500")


@pytest.mark.parametrize("crt, esperado, confianca", [
    (CRT_SIMPLES, "49", Confianca.CERTA),
    (CRT_MEI, "49", Confianca.CERTA),
    (CRT_NORMAL, "01", Confianca.PROVAVEL),
])
def test_cst_pis_cofins_por_regime(crt, esperado, confianca):
    sugestoes = derivar_cst_pis_cofins(_ctx(crt=crt))

    assert [s.campo for s in sugestoes] == ["cst_pis", "cst_cofins"]
    assert all(s.valor == esperado for s in sugestoes)
    assert all(s.confianca == confianca for s in sugestoes)


def test_origem_padrao_e_nacional():
    sugestao = derivar_origem_mercadoria()

    assert sugestao.valor == "0"
    # 3 e 5 dependem da FCI da industria — nem como alternativa automatica.
    assert all(alt[0] not in ("3", "5") for alt in sugestao.alternativas)


# =========================
# 4. Indicadores da operação
# =========================

def test_pj_com_ie_e_tratada_como_revenda():
    sugestao = derivar_consumidor_final(_ctx(destinatario_pj_com_ie=True))

    assert sugestao.valor == "0"


def test_demais_destinatarios_sao_consumidor_final():
    assert derivar_consumidor_final(_ctx()).valor == "1"


def test_pj_com_ie_pode_estar_comprando_para_consumo():
    """A inferencia tem excecao legitima, e ela precisa estar a mao."""
    sugestao = derivar_consumidor_final(_ctx(destinatario_pj_com_ie=True))

    assert sugestao.confianca == Confianca.PROVAVEL
    assert any(alt[0] == "1" for alt in sugestao.alternativas)


def test_local_destino_acompanha_o_cfop():
    """
    idDest e o 1o digito do CFOP tem que sair da MESMA decisao: divergir
    (idDest 1 com CFOP 6.102) e rejeicao na origem.
    """
    interna = _ctx(indicador_presenca=1, uf_destinatario="SP")
    fora = _ctx(indicador_presenca=4, uf_destinatario="SP")

    assert derivar_local_destino(interna).valor == "1"
    assert derivar_cfop(interna, situacao_tributaria="102").valor.startswith("5")

    assert derivar_local_destino(fora).valor == "2"
    assert derivar_cfop(fora, situacao_tributaria="102").valor.startswith("6")


# =========================
# 5. Derivação completa do produto
# =========================

def test_produto_de_varejo_no_simples_nasce_utilizavel():
    sugestoes = {s.campo: s.valor for s in derivar_produto(_ctx(crt=CRT_SIMPLES))}

    assert sugestoes["csosn"] == "102"
    assert sugestoes["cfop_padrao"] == "5102"
    assert sugestoes["origem_mercadoria"] == "0"
    assert sugestoes["cst_pis"] == "49"
    assert sugestoes["natureza_operacao"] == "Venda de mercadoria adquirida de terceiros"


def test_produto_no_regime_normal_usa_cst():
    sugestoes = {s.campo: s.valor for s in derivar_produto(_ctx(crt=CRT_NORMAL))}

    assert sugestoes["cst_icms"] == "00"
    assert sugestoes["cst_pis"] == "01"
    assert "csosn" not in sugestoes


def test_cfop_e_situacao_saem_coerentes():
    """
    Sugerir CSOSN 500 com CFOP 5102 seria oferecer uma combinacao que a SEFAZ
    recusa. O CFOP tem que ser derivado A PARTIR da situacao sugerida.
    """
    sugestoes = {s.campo: s.valor for s in derivar_produto(_ctx(crt=CRT_SIMPLES))}

    assert sugestoes["csosn"] == "102"
    assert sugestoes["cfop_padrao"] == "5102"  # e nao 5405


def test_sem_cfop_derivavel_as_demais_sugestoes_sobrevivem():
    """Recusar o CFOP nao pode zerar o resto do formulario."""
    ctx = _ctx(crt=CRT_NORMAL, indicador_presenca=4, uf_destinatario="SP")

    # Forca o caminho ambiguo: item substituido em saida interestadual.
    with pytest.raises(DerivacaoAmbiguaError):
        derivar_cfop(ctx, situacao_tributaria="60")

    campos = {s.campo for s in derivar_produto(ctx)}
    assert "origem_mercadoria" in campos
    assert "cst_pis" in campos


def test_toda_sugestao_explica_o_porque():
    """
    Sugestao sem fundamentacao, em campo tributario, e pior que campo vazio:
    o contador nao tem como discordar com base.
    """
    for sugestao in derivar_produto(_ctx()):
        assert sugestao.fundamentacao.strip()


# =========================
# 6. Ponte com o banco
# =========================

@pytest.mark.parametrize("bruto, esperado", [
    ("INDUSTRIA", TipoAtividade.INDUSTRIA),
    ("  misto  ", TipoAtividade.MISTO),
    ("comercio", TipoAtividade.COMERCIO),
    ("", None),
    (None, None),
    ("VALOR_QUE_NAO_EXISTE", None),
])
def test_tipo_atividade_e_lido_do_cadastro_sem_quebrar(bruto, esperado):
    """
    `empresas.tipo_atividade` e texto livre no banco. Um valor inesperado nao
    pode derrubar o cadastro de produto — cai em None e o CFOP assume revenda.
    """
    from app.db.models.empresa import Empresa
    from app.services.fiscal.derivacao.resolver_db import _tipo_atividade

    assert _tipo_atividade(Empresa(id=1, tipo_atividade=bruto)) == esperado
