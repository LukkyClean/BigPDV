# ---------------------------------------------------------------------------
# ARQUIVO: core/busca.py
# MÓDULO: Infraestrutura (Busca Textual)
# DESCRIÇÃO: Motor de busca compartilhado por produtos, serviços, clientes,
#            ordens de serviço e vendas.
# ---------------------------------------------------------------------------
#
# O sistema é usado no balcão, com o cliente esperando. Quem digita raramente
# lembra o nome cadastrado por inteiro e na ordem certa: lembra "azul" de
# "Tinta azul", digita "troca tela" para "Troca de tela" e escreve "acucar"
# sem cedilha. As camadas abaixo cobrem esses casos, da mais barata para a
# mais cara:
#
#   1. CONTÉM   → "azul" acha "Tinta azul" (e não só o que começa com "azul")
#   2. PALAVRAS → "azul tinta" acha "Tinta azul" (ordem não importa; todas as
#                 palavras precisam aparecer, cada uma em qualquer campo)
#   3. ACENTOS  → "acucar" acha "Açúcar"; a ordenação por relevância põe o
#                 match exato de código na frente
#   4. ERRO DE  → "tnta" acha "Tinta", mas SOMENTE quando a busca normal não
#      DIGITAÇÃO  devolveu nada — assim nunca polui um resultado bom
#
# O SQLite não sabe comparar texto ignorando acentos, então as funções
# `normalizar` e `compactar` são registradas na conexão como funções SQL
# (ver db/session.py) e aplicadas dos dois lados da comparação.
# ---------------------------------------------------------------------------

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Callable, Iterable, Sequence, TypeVar

from sqlalchemy import and_, case, func, or_
from sqlalchemy.sql.elements import ColumnElement

# Nomes das funções registradas no SQLite. Usados no SQL via `func.<nome>()`.
FUNCAO_SQL_NORMALIZAR = "normalizar_busca"
FUNCAO_SQL_COMPACTAR = "compactar_busca"

# Teto de palavras consideradas. Evita que um "termo" absurdo (um texto colado
# por engano no campo) vire uma query com dezenas de condições AND.
MAXIMO_TERMOS = 8

# A partir de quanto duas palavras são "a mesma com erro de digitação".
# 0.72 aceita "tnta"→"tinta" e "azuu"→"azul", e recusa "azul"→"anel".
SIMILARIDADE_MINIMA = 0.72

_NAO_ALFANUMERICO = re.compile(r"[^0-9a-z]+")

T = TypeVar("T")


# ===========================================================================
# NORMALIZAÇÃO
# ===========================================================================

@lru_cache(maxsize=16384)
def normalizar(texto: str | None) -> str:
    """
    Reduz o texto à forma comparável: minúsculo, sem acentos, com os
    separadores virando um único espaço.

        "Tinta Azul-Metálica"  →  "tinta azul metalica"

    O espaço é preservado (em vez de removido) porque a ordenação por
    relevância precisa saber onde uma palavra começa.

    Cacheado: o SQLite chama esta função uma vez por linha e por campo em
    cada busca, e os valores das colunas se repetem entre as consultas.
    """
    if not texto:
        return ""

    decomposto = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return _NAO_ALFANUMERICO.sub(" ", sem_acento.casefold()).strip()


@lru_cache(maxsize=16384)
def compactar(texto: str | None) -> str:
    """
    Como `normalizar`, mas sem espaço nenhum — a forma certa para comparar
    documentos e códigos, que cada um digita de um jeito.

        "123.456.789-00"  →  "12345678900"
        "BUSCA-ESPECIFICA" →  "buscaespecifica"
    """
    return normalizar(texto).replace(" ", "")


def extrair_termos(termo: str | None, maximo: int = MAXIMO_TERMOS) -> list[str]:
    """
    Quebra o que foi digitado nas palavras que serão exigidas na busca.
    Duplicatas são descartadas ("tinta tinta" não vira duas condições).
    """
    normalizado = normalizar(termo)
    if not normalizado:
        return []

    vistos: set[str] = set()
    termos: list[str] = []
    for parte in normalizado.split():
        if parte in vistos:
            continue
        vistos.add(parte)
        termos.append(parte)
        if len(termos) >= maximo:
            break
    return termos


# ===========================================================================
# FILTRO (CAMADAS 1, 2 E 3)
# ===========================================================================

def filtro_busca(
    termo: str | None,
    campos: Sequence[ColumnElement[Any]],
) -> ColumnElement[bool] | None:
    """
    Monta a condição WHERE da busca.

    Cada palavra digitada precisa aparecer em ALGUM dos campos (OR entre
    campos), e TODAS as palavras precisam aparecer (AND entre palavras) —
    é isso que faz "azul tinta" achar "Tinta azul metálica" sem que
    "azul" sozinho traga a loja inteira.

    Como cortesia extra, o termo todo colado também é testado, para que um
    CPF ou código digitado com pontuação ("123.456.789-00") case com o valor
    gravado sem ela.

    Retorna None quando não há nada a filtrar — o chamador decide o que
    fazer (normalmente, não aplicar filtro algum).
    """
    termos = extrair_termos(termo)
    if not termos or not campos:
        return None

    condicoes = [
        or_(*[_contem(campo, palavra) for campo in campos])
        for palavra in termos
    ]
    filtro: ColumnElement[bool] = and_(*condicoes)

    if len(termos) > 1:
        colado = "".join(termos)
        filtro = or_(filtro, *[_contem_compacto(campo, colado) for campo in campos])

    return filtro


def ordenacao_relevancia(
    termo: str | None,
    campo_principal: ColumnElement[Any],
    campos_exatos: Sequence[ColumnElement[Any]] = (),
) -> ColumnElement[Any] | None:
    """
    Produz a coluna de ordenação (menor = mais relevante).

    A escala existe por causa do balcão: quem bipa um leitor de código de
    barras ou digita o SKU inteiro tem que receber AQUELE item em primeiro
    lugar, nunca um parecido. Só depois vêm os matches por nome.

        0 → código/documento bateu exatamente
        1 → o nome é exatamente o que foi digitado
        2 → o nome começa com o que foi digitado
        3 → alguma palavra do nome começa com o que foi digitado
        4 → apareceu no meio de alguma palavra
    """
    termos = extrair_termos(termo)
    if not termos:
        return None

    alvo = " ".join(termos)
    colado = "".join(termos)
    principal = func.normalizar_busca(campo_principal)

    ramos: list[tuple[ColumnElement[bool], int]] = [
        (func.compactar_busca(campo) == colado, 0) for campo in campos_exatos
    ]
    ramos.append((principal == alvo, 1))
    ramos.append((principal.like(f"{alvo}%"), 2))
    ramos.append((principal.like(f"% {alvo}%"), 3))

    return case(*ramos, else_=4)


def _contem(campo: ColumnElement[Any], valor: str) -> ColumnElement[bool]:
    """`campo` contém `valor`, ignorando caixa, acentos e pontuação."""
    return func.normalizar_busca(campo).like(f"%{valor}%")


def _contem_compacto(campo: ColumnElement[Any], valor: str) -> ColumnElement[bool]:
    """Idem, mas comparando as duas pontas sem espaço algum."""
    return func.compactar_busca(campo).like(f"%{valor}%")


# ===========================================================================
# TOLERÂNCIA A ERRO DE DIGITAÇÃO (CAMADA 4)
# ===========================================================================

def por_similaridade(
    termo: str | None,
    registros: Iterable[T],
    textos: Callable[[T], Iterable[str | None]],
    minimo: float = SIMILARIDADE_MINIMA,
    limite: int = 20,
) -> list[T]:
    """
    Último recurso: reordena `registros` por parecença com o termo digitado.

    Só deve ser chamado quando a busca normal devolveu ZERO resultados.
    Rodar isso sempre seria caro (percorre os candidatos em Python) e, pior,
    encheria de quase-acertos uma lista que já estava correta.

    `textos` extrai de cada registro os campos que valem a comparação
    (nome, código, ...).
    """
    alvo = normalizar(termo)
    if not alvo:
        return []

    pontuados: list[tuple[float, float, int, T]] = []
    for posicao, registro in enumerate(registros):
        melhor = 0.0
        inteiro = 0.0
        for texto in textos(registro):
            parcial, completo = _proximidade(alvo, normalizar(texto), minimo)
            melhor = max(melhor, parcial)
            inteiro = max(inteiro, completo)
        if melhor >= minimo:
            # A posição entra na chave só para desempatar de forma estável.
            pontuados.append((melhor, inteiro, posicao, registro))

    # Nota da palavra primeiro; a do texto inteiro desempata, para que buscar
    # "tinta" traga "Tinta" antes de "Tinta Guache" — ambos casam a palavra
    # com nota máxima, mas um deles é exatamente o que se pediu.
    pontuados.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [registro for _, _, _, registro in pontuados[:limite]]


def _proximidade(alvo: str, base: str, minimo: float) -> tuple[float, float]:
    """
    Quão parecidos são dois textos, de 0 a 1.

    Devolve duas notas: a melhor entre o texto inteiro e cada palavra dele, e
    a do texto inteiro sozinho. A primeira é o que decide se o registro entra
    no resultado — sem olhar palavra a palavra, "tnta" perderia para "Tinta
    azul metálica" só por ser mais curto que o nome completo. A segunda serve
    de desempate.
    """
    if not base:
        return 0.0, 0.0

    inteiro = _razao(alvo, base, minimo)
    melhor = inteiro
    for palavra in base.split():
        if melhor >= 1.0:
            break
        melhor = max(melhor, _razao(alvo, palavra, minimo))
    return melhor, inteiro


def _razao(alvo: str, base: str, minimo: float) -> float:
    """
    Nota de 0 a 1, descartando cedo o que nem poderia atingir `minimo`.

    O resgate compara o termo com milhares de palavras, e o cálculo exato é
    caro. `real_quick_ratio` e `quick_ratio` são limites SUPERIORES baratos:
    se já ficam abaixo do mínimo, a nota real também ficaria, e não há por que
    calculá-la. Medido num catálogo de 5 mil produtos, o resgate caiu de
    ~210ms para ~85ms.
    """
    comparador = SequenceMatcher(None, alvo, base)
    if comparador.real_quick_ratio() < minimo or comparador.quick_ratio() < minimo:
        return 0.0
    return comparador.ratio()
