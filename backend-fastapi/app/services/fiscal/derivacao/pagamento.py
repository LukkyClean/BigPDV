# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/pagamento.py
# DESCRIÇÃO: Deduz o código SEFAZ de uma forma de pagamento pelo nome.
# ---------------------------------------------------------------------------
"""
Código SEFAZ (`tPag`) por palavra-chave no nome.

O PROBLEMA QUE ISTO RESOLVE
---------------------------
As seis formas padrão já nascem com código, semeadas no startup. Mas uma forma
criada pelo lojista — "Vale Refeição", "Cartão da Loja", "Fiado" — nasce sem
código, vira pendência que impede a emissão, e **não havia como resolvê-la
pela interface**: o campo não existe em tela nenhuma, embora a API aceite.

Aqui a dedução acontece no momento em que a forma é criada, então o caso comum
se resolve sozinho e o lojista nunca vê a pendência.

A ORDEM DAS REGRAS IMPORTA
--------------------------
"Cartão de Crédito" contém "cartão" e "crédito". Débito e crédito são
verificados ANTES do genérico "cartão", senão toda forma com cartão no nome
cairia no mesmo código.
"""
import re
import unicodedata
from typing import Optional

from .types import CampoSugerido, Confianca, Fonte

# tPag da NF-e/NFC-e. Só os que aparecem no varejo.
TPAG_DINHEIRO = "01"
TPAG_CHEQUE = "02"
TPAG_CARTAO_CREDITO = "03"
TPAG_CARTAO_DEBITO = "04"
TPAG_CREDITO_LOJA = "05"
TPAG_VALE_ALIMENTACAO = "10"
TPAG_VALE_REFEICAO = "11"
TPAG_VALE_PRESENTE = "12"
TPAG_VALE_COMBUSTIVEL = "13"
TPAG_BOLETO = "15"
TPAG_PIX = "17"
TPAG_OUTROS = "99"

# Integração da maquininha — só existe em cartão (tPag 03 e 04).
INTEGRACAO_POS = "POS"
INTEGRACAO_NAO_SE_APLICA = "NAO_SE_APLICA"

CODIGOS_DE_CARTAO = frozenset({TPAG_CARTAO_CREDITO, TPAG_CARTAO_DEBITO})

# (padrão, código). Avaliado em ordem — do mais específico ao mais genérico.
_REGRAS: list[tuple[str, str]] = [
    (r"dinheiro|especie|a vista|avista", TPAG_DINHEIRO),
    (r"cheque", TPAG_CHEQUE),
    (r"pix", TPAG_PIX),
    (r"boleto|bancaria", TPAG_BOLETO),
    # Débito e crédito ANTES de "cartão", senão o genérico engole os dois.
    (r"debito", TPAG_CARTAO_DEBITO),
    (r"credito", TPAG_CARTAO_CREDITO),
    (r"alimentacao", TPAG_VALE_ALIMENTACAO),
    (r"refeicao", TPAG_VALE_REFEICAO),
    (r"combustivel", TPAG_VALE_COMBUSTIVEL),
    (r"vale.?presente|gift", TPAG_VALE_PRESENTE),
    # "Crediário", "Fiado", "Conta da Loja" — venda a prazo da própria loja.
    (r"crediario|fiado|caderneta|conta da loja", TPAG_CREDITO_LOJA),
    # Genérico por último: um "Cartão da Loja" sem débito/crédito no nome.
    (r"cartao", TPAG_CARTAO_CREDITO),
]


def _normalizar(nome: str) -> str:
    """Minúsculas, sem acento — para 'Refeição' casar com 'refeicao'."""
    sem_acento = unicodedata.normalize("NFKD", nome or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def codigo_sefaz_por_nome(nome: str) -> Optional[str]:
    """Código SEFAZ deduzido do nome, ou None quando nada casa."""
    normalizado = _normalizar(nome)
    if not normalizado:
        return None

    for padrao, codigo in _REGRAS:
        if re.search(padrao, normalizado):
            return codigo
    return None


def tipo_integracao_por_codigo(codigo: Optional[str]) -> str:
    """
    POS para cartão, NAO_SE_APLICA para o resto.

    POS (maquininha autônoma, digitada à mão) é o arranjo da maioria das lojas
    pequenas — e afirmar uma integração TEF que não existe descreveria mal a
    operação num documento fiscal. Quem tem TEF troca no cadastro.
    """
    return INTEGRACAO_POS if codigo in CODIGOS_DE_CARTAO else INTEGRACAO_NAO_SE_APLICA


def derivar_forma_pagamento(nome: str) -> list[CampoSugerido]:
    """
    Sugestões para uma forma de pagamento nova.

    Sem correspondência, sugere 99 (Outros) com confiança AMBIGUA: 99 emite
    sem ser recusado, mas descreve mal a operação, então a tela deve pedir
    confirmação em vez de aplicar sozinha.
    """
    codigo = codigo_sefaz_por_nome(nome)
    integracao = tipo_integracao_por_codigo(codigo)

    if codigo is None:
        return [
            CampoSugerido(
                campo="codigo_sefaz",
                valor=TPAG_OUTROS,
                fonte=Fonte.DERIVADO,
                confianca=Confianca.AMBIGUA,
                fundamentacao=(
                    f"Nao reconhecemos '{nome}' entre as formas conhecidas. O 99 "
                    f"(Outros) e aceito pela SEFAZ, mas descreve mal a operacao — "
                    f"confira se ha um codigo mais especifico."
                ),
                alternativas=[
                    (TPAG_VALE_ALIMENTACAO, "Vale-alimentacao"),
                    (TPAG_VALE_REFEICAO, "Vale-refeicao"),
                    (TPAG_CREDITO_LOJA, "Credito da loja (crediario, fiado)"),
                    (TPAG_OUTROS, "Outros"),
                ],
                exige_confirmacao=True,
            ),
            CampoSugerido(
                campo="tipo_integracao",
                valor=INTEGRACAO_NAO_SE_APLICA,
                fonte=Fonte.DERIVADO,
                confianca=Confianca.PROVAVEL,
                fundamentacao="Sem maquininha envolvida ate que o codigo seja de cartao.",
            ),
        ]

    sugestoes = [
        CampoSugerido(
            campo="codigo_sefaz",
            valor=codigo,
            fonte=Fonte.DERIVADO,
            confianca=Confianca.PROVAVEL,
            fundamentacao=f"Codigo SEFAZ {codigo}, deduzido do nome '{nome}'.",
        ),
        CampoSugerido(
            campo="tipo_integracao",
            valor=integracao,
            fonte=Fonte.DERIVADO,
            confianca=Confianca.PROVAVEL,
            fundamentacao=(
                "Maquininha autonoma (POS) — o arranjo da maioria das lojas. "
                "Quem tem TEF integrado troca no cadastro."
                if integracao == INTEGRACAO_POS
                else "Nao passa por maquininha."
            ),
        ),
    ]
    return sugestoes
