# ---------------------------------------------------------------------------
# ARQUIVO: test_contrato_payload_campos.py
# DESCRIÇÃO: A lista EXATA de campos que o ERP envia para a plataforma.
#
# POR QUE ESTE TESTE EXISTE
# -------------------------
# A plataforma valida o payload com um `z.object` SEM `.passthrough()`, e o Zod
# descarta silenciosamente todo campo não declarado no schema dela. O campo
# some, a nota vai incompleta para a SEFAZ, e a rejeição volta parecendo culpa
# do ERP. Está documentado em `docs/contrato-api-fiscal-plataforma.md` §1.1
# desde 09/09/2026.
#
# Em 12/09/2026 isso custou a primeira emissão de uma loja real: o
# `ipi_codigo_enquadramento` não chegou ao XML e a SEFAZ recusou por schema
# ("Element IPINT is not expected. Expected is one of ( ... cEnq )").
#
# O QUE ESTE TESTE PROTEGE
# ------------------------
# Não impede a plataforma de descartar campo — isso é do lado de lá. O que ele
# garante é que a lista do nosso lado seja EXPLÍCITA e versionada: mexer no
# payload sem atualizar o contrato quebra o teste, e o time da plataforma tem
# contra o que conferir o schema dele.
#
# Quando um campo novo entrar, acrescente aqui E em
# `docs/contrato-api-fiscal-plataforma.md`.
# ---------------------------------------------------------------------------

# Só a fixture e o helper — `import *` traria junto os 17 testes do outro
# arquivo, que passariam a rodar duas vezes.
from test.services.fiscal.test_payload_builder import (  # noqa: F401
    _montar,
    venda_simples,
)


def _caminhos(obj, prefixo: str = "") -> set[str]:
    """Todo campo folha do payload, em notação de caminho."""
    encontrados: set[str] = set()
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            caminho = f"{prefixo}.{chave}" if prefixo else chave
            if isinstance(valor, (dict, list)):
                encontrados |= _caminhos(valor, caminho)
            else:
                encontrados.add(caminho)
    elif isinstance(obj, list) and obj:
        encontrados |= _caminhos(obj[0], f"{prefixo}[]")
    return encontrados


# A nota "raiz" — o que descreve a operação.
CAMPOS_RAIZ = {
    "modelo",
    "natureza_operacao",
    "tipo_documento",
    "local_destino",
    "modalidade_frete",
    "finalidade_emissao",
    "consumidor_final",
    "presenca_comprador",
    "numero",
    "serie",
    "valor_troco",
}

CAMPOS_EMITENTE = {
    "emitente.cnpj",
    "emitente.razao_social",
    "emitente.nome_fantasia",
    "emitente.inscricao_estadual",
    "emitente.inscricao_municipal",
    "emitente.codigo_regime_tributario",
    "emitente.regime_tributario",
    "emitente.endereco.logradouro",
    "emitente.endereco.numero",
    "emitente.endereco.complemento",
    "emitente.endereco.bairro",
    "emitente.endereco.cidade",
    "emitente.endereco.uf",
    "emitente.endereco.cep",
}

# Identificação e tributação do item. É onde mora a maioria dos campos que a
# SEFAZ exige — e onde a poda do Zod dói mais.
CAMPOS_ITEM = {
    "items[].numero_item",
    "items[].codigo_produto",
    "items[].descricao",
    "items[].quantidade_comercial",
    "items[].valor_unitario_comercial",
    "items[].valor_bruto",
    "items[].unidade_comercial",
    "items[].codigo_barras_comercial",
    "items[].ncm",
    "items[].cfop",
    "items[].icms_origem",
    "items[].unidade_tributavel",
    "items[].codigo_barras_tributavel",
    "items[].icms_situacao_tributaria",
    "items[].valor_frete",
    "items[].valor_seguro",
    "items[].valor_outras_despesas_acessorias",
    "items[].valor_desconto",
    "items[].icms_modalidade_base_calculo",
    "items[].icms_base_calculo",
    "items[].icms_aliquota",
    "items[].icms_valor",
    "items[].pis_situacao_tributaria",
    "items[].pis_base_calculo",
    "items[].pis_aliquota_porcentual",
    "items[].pis_valor",
    "items[].cofins_situacao_tributaria",
    "items[].cofins_base_calculo",
    "items[].cofins_aliquota_porcentual",
    "items[].cofins_valor",
}

CAMPOS_PAGAMENTO = {
    "formas_pagamento[].forma_pagamento",
    "formas_pagamento[].valor_pagamento",
}

CAMPOS_TOTAIS = {
    "totais.valor_produtos",
    "totais.valor_frete",
    "totais.valor_seguro",
    "totais.valor_outras_despesas",
    "totais.valor_desconto",
    "totais.icms_base_calculo",
    "totais.icms_valor_total",
    "totais.valor_total",
}

CONTRATO = (
    CAMPOS_RAIZ | CAMPOS_EMITENTE | CAMPOS_ITEM | CAMPOS_PAGAMENTO | CAMPOS_TOTAIS
)


def test_payload_envia_exatamente_os_campos_do_contrato(venda_simples):
    """
    Mexeu no payload? Atualize esta lista E o
    `docs/contrato-api-fiscal-plataforma.md` — é ele que o time da plataforma lê
    para saber o que declarar no Zod.

    O destinatário fica fora da comparação: o conjunto varia com o tipo de
    cliente (PF, PJ, consumidor no balcão) e tem teste próprio.
    """
    enviados = {c for c in _caminhos(_montar(venda_simples)) if not c.startswith("destinatario")}

    faltando = CONTRATO - enviados
    sobrando = enviados - CONTRATO

    assert not faltando, f"contrato promete e o payload não envia: {sorted(faltando)}"
    assert not sobrando, (
        f"payload envia campo fora do contrato: {sorted(sobrando)}. "
        "A plataforma descarta o que não está no Zod dela — acrescente no contrato."
    )


def test_campos_que_a_sefaz_recusa_sem_estao_presentes(venda_simples):
    """
    O subconjunto sem o qual a nota NÃO é autorizada, conforme
    `contrato-api-fiscal-plataforma.md` §1.1. Um por um, porque cada um deles
    já foi descartado pelo Zod da plataforma em algum momento.
    """
    enviados = _caminhos(_montar(venda_simples))

    obrigatorios = [
        "emitente.inscricao_estadual",
        "emitente.codigo_regime_tributario",
        "items[].icms_situacao_tributaria",
        "items[].icms_origem",
        "items[].pis_situacao_tributaria",
        "items[].cofins_situacao_tributaria",
        "items[].unidade_comercial",
        "items[].ncm",
        "items[].cfop",
        "formas_pagamento[].forma_pagamento",
        "presenca_comprador",
        "finalidade_emissao",
        "consumidor_final",
        "numero",
        "serie",
    ]

    for campo in obrigatorios:
        assert campo in enviados, f"{campo} saiu do payload — a SEFAZ recusa sem ele"


def test_grupo_de_ipi_continua_fora(venda_simples):
    """
    Rejeição de schema da primeira emissão real (12/09/2026): o grupo IPI exige
    `cEnq` antes do `IPINT`, e o `ipi_codigo_enquadramento` não sobrevivia ao
    caminho. O grupo é opcional e não calculamos IPI — volta quando houver
    cliente indústria, calculado de verdade.
    """
    enviados = _caminhos(_montar(venda_simples))
    assert not [c for c in enviados if "ipi" in c.lower()]
