# app/services/fiscal/helpers.py
from typing import Optional

from app.schemas.verificacao_fiscal import PendenciaFiscal
from app.db.models.cliente import Cliente, ClientePF, ClientePJ


# ---------------------------------------------------------------------------
# CRT — Código de Regime Tributário da NF-e
# ---------------------------------------------------------------------------
# 1 = Simples Nacional
# 2 = Simples Nacional, excesso de sublimite de receita bruta
# 3 = Regime Normal
# 4 = Simples Nacional — MEI
#
# Só CRT 1 e 4 usam CSOSN. O CRT 2 é do Simples mas, para o excedente, tributa
# pelo regime normal: usa CST como qualquer empresa de Lucro Presumido/Real.
# Confundir os dois manda a nota com o grupo de ICMS errado.
CRT_SIMPLES_NACIONAL = 1
CRT_SIMPLES_EXCESSO = 2
CRT_REGIME_NORMAL = 3
CRT_MEI = 4

CRT_PADRAO = CRT_REGIME_NORMAL

# Mapeia os rótulos usados na interface para o CRT correspondente.
# Chaves em minúsculas e sem espaços nas bordas.
_ROTULO_PARA_CRT = {
    "simples nacional": CRT_SIMPLES_NACIONAL,
    "simples nacional (excesso de sublimite)": CRT_SIMPLES_EXCESSO,
    "regime normal": CRT_REGIME_NORMAL,
    "mei": CRT_MEI,
    "microempreendedor individual": CRT_MEI,
}


def crt_do_rotulo(regime: Optional[str]) -> Optional[int]:
    """
    Traduz o texto de `regime_tributario` para CRT.

    Usado apenas na migração de dados antigos e como último recurso quando a
    coluna `crt` ainda está vazia. O caminho normal é ler `empresa.crt`.
    """
    if not regime:
        return None
    return _ROTULO_PARA_CRT.get(regime.strip().lower())


def obter_crt(empresa) -> int:
    """
    CRT efetivo da empresa.

    Prioriza a coluna `crt`; cai no rótulo textual só enquanto houver cadastros
    anteriores à migração. Sem nenhum dos dois, assume Regime Normal — o padrão
    seguro, porque destacar ICMS indevidamente é erro corrigível por carta de
    correção, enquanto usar CSOSN sem ser do Simples é rejeição na origem.
    """
    if empresa is None:
        return CRT_PADRAO

    crt = getattr(empresa, "crt", None)
    if crt in (CRT_SIMPLES_NACIONAL, CRT_SIMPLES_EXCESSO, CRT_REGIME_NORMAL, CRT_MEI):
        return crt

    return crt_do_rotulo(getattr(empresa, "regime_tributario", None)) or CRT_PADRAO


def usa_csosn(crt: int) -> bool:
    """Só CRT 1 (Simples) e 4 (MEI) preenchem CSOSN; os demais usam CST."""
    return crt in (CRT_SIMPLES_NACIONAL, CRT_MEI)


def pis_cofins_por_fora(crt: int) -> bool:
    """
    Se a empresa recolhe PIS/COFINS por fora da nota.

    No Simples Nacional (CRT 1 e 4) os tributos estão embutidos na guia única:
    destacar alíquota na nota gera bitributação aparente. Esses casos saem com
    CST 49 e valores zerados.
    """
    return crt in (CRT_SIMPLES_NACIONAL, CRT_MEI)


def is_simples_nacional(regime: Optional[str]) -> bool:
    """
    DEPRECADO — mantido só para não quebrar chamadas antigas.

    O nome engana: `"simples" in regime` também casa com "Simples Nacional
    (Excesso de Sublimite)", que é CRT 2 e usa CST, não CSOSN. Use
    `obter_crt(empresa)` + `usa_csosn(crt)`.
    """
    return usa_csosn(crt_do_rotulo(regime) or CRT_PADRAO)


def criar_pendencia(categoria: str, campo: str, mensagem: str,
                    referencia_id: int = None, referencia_nome: str = None) -> PendenciaFiscal:
    return PendenciaFiscal(
        categoria=categoria,
        campo=campo,
        mensagem=mensagem,
        referencia_id=referencia_id,
        referencia_nome=referencia_nome,
    )


def get_nome_cliente(cliente: Cliente) -> str:
    if isinstance(cliente, ClientePF):
        return cliente.nome
    elif isinstance(cliente, ClientePJ):
        return cliente.nome_fantasia or cliente.razao_social
    return f"Cliente #{cliente.id}"
