# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/campos_produto.py
# DESCRIÇÃO: Quais campos fiscais o cadastro de produto deve mostrar e exigir,
#            conforme o regime da empresa.
# ---------------------------------------------------------------------------
"""
O mapa de campos do cadastro de produto.

POR QUE ISTO NÃO É UM `v-if` NA TELA
------------------------------------
Estava: o formulário decidia entre CST e CSOSN com
`regime_tributario.includes('Simples Nacional')`. Duas coisas quebravam ali —
"Simples Nacional (Excesso de Sublimite)" é CRT 2 e usa **CST**, e sem regime
preenchido a tela mostrava os dois campos e aceitava os dois preenchidos, uma
combinação que não existe em nota nenhuma.

Quem sabe responder é o backend, que já lê o CRT (`obter_crt`) e já decide a
mesma coisa na hora de emitir (`usa_csosn`, `pis_cofins_por_fora`). Perguntar
aqui garante que cadastro e emissão concordem — quando divergem, o cadastro
aprova o que a emissão recusa, que é a pior combinação possível.

A REGRA: campo que não se aplica **não aparece**. Não aparece cinza, não
aparece desabilitado. É o que os formulários de referência do mercado fazem —
uma empresa do Simples não vê a palavra "CST" em lugar nenhum.

O QUE **NÃO** ESTÁ AQUI
-----------------------
Condição que depende do VALOR de outro campo — CEST obrigatório sob ST,
redução de base com CST 20, alíquota de PIS com CST tributável. Isso muda a
cada tecla e continua na tela, que já tem os `computed`. Aqui mora só o que o
cadastro da empresa decide, e que não muda enquanto o produto é preenchido.
"""

from typing import Any, Optional

from app.services.fiscal.helpers import (
    CRT_MEI,
    CRT_REGIME_NORMAL,
    CRT_SIMPLES_EXCESSO,
    CRT_SIMPLES_NACIONAL,
    obter_crt,
    pis_cofins_por_fora,
    usa_csosn,
)

_ROTULO_REGIME = {
    CRT_SIMPLES_NACIONAL: "Simples Nacional",
    CRT_SIMPLES_EXCESSO: "Simples Nacional (excesso de sublimite)",
    CRT_REGIME_NORMAL: "Regime Normal",
    CRT_MEI: "MEI",
}


def _campo(visivel: bool, obrigatorio: bool = False) -> dict[str, bool]:
    # Invisível nunca é obrigatório: exigir campo que a tela não renderiza é
    # como se perde um formulário em silêncio — o submit morre e o usuário vê
    # "cliquei em salvar e não aconteceu nada".
    return {"visivel": visivel, "obrigatorio": obrigatorio and visivel}


def mapa_campos_produto(crt: int) -> dict[str, Any]:
    """
    Mapa de visibilidade e obrigatoriedade dos campos fiscais de produto.

    Args:
        crt: Código de Regime Tributário da empresa (1, 2, 3 ou 4).

    Returns:
        dict com `crt`, `regime` (rótulo para a tela), `usa_csosn` e `campos`.
    """
    simples = usa_csosn(crt)
    tributo_na_guia = pis_cofins_por_fora(crt)

    campos: dict[str, dict[str, bool]] = {
        # --- Sempre, e exigidos pelo gate de emissão (validators.py) ---
        "ncm": _campo(True, True),
        "cfop_padrao": _campo(True, True),
        "origem_mercadoria": _campo(True, True),

        # Unidade tributável NÃO é obrigatória de propósito: o payload já
        # resolve `unidade_tributavel or unidade_medida or "UN"`, e exigir
        # aqui obrigaria a digitar duas vezes a mesma unidade.
        "unidade_tributavel": _campo(True, False),

        # Condicionais por VALOR — quem decide é a tela.
        "cest": _campo(True, False),
        "gtin_tributavel": _campo(True, False),

        # --- ICMS: um campo OU o outro, nunca os dois ---
        "csosn": _campo(simples, True),
        "cst_icms": _campo(not simples, True),

        # No Simples o ICMS não é destacado: alíquota, redução de base e
        # código de benefício não existem na nota, então não existem na tela.
        "aliquota_icms": _campo(not simples, False),
        "reducao_base_icms": _campo(not simples, False),
        "codigo_beneficio_fiscal": _campo(not simples, False),

        # --- PIS/COFINS ---
        # No Simples/MEI vão na guia única e o motor GRAVA 49 sozinho,
        # ignorando o que estiver no cadastro (`tax_engine/resolver.py`). Um
        # campo que não muda nada só serve para o lojista travar sem saber o
        # que responder — foi o que aconteceu numa loja real em 12/09/2026.
        # Some junto com as alíquotas.
        "cst_pis": _campo(not tributo_na_guia, False),
        "cst_cofins": _campo(not tributo_na_guia, False),
        "aliquota_pis": _campo(not tributo_na_guia, False),
        "aliquota_cofins": _campo(not tributo_na_guia, False),

        # --- Reforma Tributária (IBS/CBS) ---
        # Em transição: visível para todo regime, exigido por nenhum.
        "c_class_trib": _campo(True, False),
        "cst_ibs_cbs": _campo(True, False),
        "aliquota_ibs": _campo(True, False),
        "aliquota_cbs": _campo(True, False),
        "c_benef": _campo(True, False),
    }

    return {
        "crt": crt,
        "regime": _ROTULO_REGIME.get(crt, "Regime Normal"),
        "usa_csosn": simples,
        "campos": campos,
    }


def mapa_campos_da_empresa(empresa: Optional[Any]) -> dict[str, Any]:
    """Mesma coisa, partindo da empresa — a única linha que toca no ORM."""
    return mapa_campos_produto(obter_crt(empresa))
