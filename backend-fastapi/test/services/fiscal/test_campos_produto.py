# ---------------------------------------------------------------------------
# ARQUIVO: test_campos_produto.py
# DESCRIÇÃO: O cadastro de produto mostra os campos do regime da empresa.
#
# A tela decidia entre CST e CSOSN com `regime.includes('Simples Nacional')`,
# o que errava o CRT 2 (Simples com excesso de sublimite, que usa CST) e, sem
# regime preenchido, mostrava os dois campos ao mesmo tempo.
# Ver `docs/cadastro-produto-plano.md`, §2.B7 e D6b.
# ---------------------------------------------------------------------------

from app.services.fiscal.campos_produto import mapa_campos_produto
from app.services.fiscal.helpers import (
    CRT_MEI,
    CRT_REGIME_NORMAL,
    CRT_SIMPLES_EXCESSO,
    CRT_SIMPLES_NACIONAL,
)


def _visivel(mapa, campo: str) -> bool:
    return mapa["campos"][campo]["visivel"]


def _obrigatorio(mapa, campo: str) -> bool:
    return mapa["campos"][campo]["obrigatorio"]


# =========================
# Um campo OU o outro
# =========================

def test_simples_nacional_ve_csosn_e_nunca_cst():
    mapa = mapa_campos_produto(CRT_SIMPLES_NACIONAL)

    assert _visivel(mapa, "csosn") and _obrigatorio(mapa, "csosn")
    assert not _visivel(mapa, "cst_icms")
    assert not _obrigatorio(mapa, "cst_icms")


def test_regime_normal_ve_cst_e_nunca_csosn():
    mapa = mapa_campos_produto(CRT_REGIME_NORMAL)

    assert _visivel(mapa, "cst_icms") and _obrigatorio(mapa, "cst_icms")
    assert not _visivel(mapa, "csosn")


def test_mei_segue_o_simples():
    """CRT 4 preenche CSOSN, igual ao CRT 1 (`usa_csosn`)."""
    assert mapa_campos_produto(CRT_MEI)["usa_csosn"] is True
    assert _visivel(mapa_campos_produto(CRT_MEI), "csosn")


def test_simples_com_excesso_de_sublimite_usa_cst():
    """
    O CRT 2 é a armadilha que derrubava o `includes('Simples Nacional')`: o
    rótulo diz "Simples Nacional (Excesso de Sublimite)" mas o documento sai
    com CST, não com CSOSN.
    """
    mapa = mapa_campos_produto(CRT_SIMPLES_EXCESSO)

    assert mapa["usa_csosn"] is False
    assert _visivel(mapa, "cst_icms")
    assert not _visivel(mapa, "csosn")


def test_cst_e_csosn_nunca_aparecem_juntos():
    """A combinação não existe em nota nenhuma — em nenhum dos quatro CRTs."""
    for crt in (CRT_SIMPLES_NACIONAL, CRT_SIMPLES_EXCESSO, CRT_REGIME_NORMAL, CRT_MEI):
        mapa = mapa_campos_produto(crt)
        assert _visivel(mapa, "cst_icms") != _visivel(mapa, "csosn"), f"CRT {crt}"


# =========================
# O que some junto com o ICMS
# =========================

def test_simples_nao_mostra_aliquota_nem_reducao_de_icms():
    """No Simples o ICMS não é destacado: não há alíquota que informar."""
    mapa = mapa_campos_produto(CRT_SIMPLES_NACIONAL)

    assert not _visivel(mapa, "aliquota_icms")
    assert not _visivel(mapa, "reducao_base_icms")
    assert not _visivel(mapa, "codigo_beneficio_fiscal")


def test_simples_nao_mostra_nada_de_pis_cofins():
    """
    PIS/COFINS do Simples/MEI vão na guia única, e o motor grava CST 49
    sozinho — ignorando o cadastro. Campo que não muda nada só serve para o
    lojista travar sem saber o que responder.
    """
    mapa = mapa_campos_produto(CRT_SIMPLES_NACIONAL)

    assert not _visivel(mapa, "cst_pis")
    assert not _visivel(mapa, "cst_cofins")
    assert not _visivel(mapa, "aliquota_pis")
    assert not _visivel(mapa, "aliquota_cofins")


def test_regime_normal_mostra_as_aliquotas():
    mapa = mapa_campos_produto(CRT_REGIME_NORMAL)

    assert _visivel(mapa, "aliquota_icms")
    assert _visivel(mapa, "aliquota_pis")
    assert _visivel(mapa, "aliquota_cofins")


# =========================
# Obrigatoriedade
# =========================

def test_obrigatorios_sao_os_mesmos_que_o_gate_de_emissao_cobra():
    """
    NCM, CFOP e origem são o que o `validators.verificar_produto_fiscal` exige
    de todo produto. Exigir mais no cadastro trava quem poderia emitir.
    """
    for crt in (CRT_SIMPLES_NACIONAL, CRT_REGIME_NORMAL):
        mapa = mapa_campos_produto(crt)
        obrigatorios = {c for c, v in mapa["campos"].items() if v["obrigatorio"]}
        situacao = "csosn" if mapa["usa_csosn"] else "cst_icms"
        assert obrigatorios == {"ncm", "cfop_padrao", "origem_mercadoria", situacao}


def test_unidade_tributavel_nao_e_obrigatoria():
    """
    O payload resolve `unidade_tributavel or unidade_medida or "UN"`; exigir
    aqui obrigaria a digitar duas vezes a mesma unidade. O `validators.py`
    tirou esse campo da lista pelo mesmo motivo.
    """
    assert not _obrigatorio(mapa_campos_produto(CRT_SIMPLES_NACIONAL), "unidade_tributavel")


def test_campo_invisivel_nunca_e_obrigatorio():
    """
    Campo exigido e não renderizado mata o submit em silêncio — é o bug do
    complemento da empresa, que está em produção até hoje.
    """
    for crt in (CRT_SIMPLES_NACIONAL, CRT_SIMPLES_EXCESSO, CRT_REGIME_NORMAL, CRT_MEI):
        for campo, regra in mapa_campos_produto(crt)["campos"].items():
            if regra["obrigatorio"]:
                assert regra["visivel"], f"CRT {crt}: {campo} exigido e invisível"


# =========================
# Sem regime cadastrado
# =========================

def test_sem_crt_valido_cai_no_regime_normal():
    """
    `obter_crt` já decide assim: destacar ICMS indevidamente se corrige por
    carta de correção, usar CSOSN sem ser do Simples é rejeição na origem.
    """
    mapa = mapa_campos_produto(99)

    assert mapa["regime"] == "Regime Normal"
    assert _visivel(mapa, "cst_icms")
    assert not _visivel(mapa, "csosn")
