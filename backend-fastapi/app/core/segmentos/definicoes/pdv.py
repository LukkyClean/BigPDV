# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/definicoes/pdv.py
# DESCRICAO: Definicao do segmento PDV (venda de produto no balcao). Dado, nao motor.
#
#            Serve adega, mercado, mercearia, papelaria -- qualquer loja que
#            venda produto e nao preste servico. E o primeiro segmento do
#            sistema SEM Ordem de Servico.
# ---------------------------------------------------------------------------

SEGMENTO_PDV = "pdv"


# O unico segmento que declara isto, e a razao de o arquivo existir.
#
# O PADRAO E TER OS: `segmento_usa_ordem_servico()` responde True para qualquer
# segmento que nao diga o contrario -- inclusive para os que nem tem arquivo de
# definicao (marcenaria, eletricista, outros). Foi de proposito: fosse ao
# contrario, ligar esta regra teria APAGADO o modulo de OS de toda loja que nao
# estivesse declarada aqui, e o sintoma na loja seria "sumiu o menu de
# Servicos".
#
# Nao ha `checkin`, `vistoria` nem `identificador`: sem OS, nao ha objeto de
# servico para descrever. O dicionario existe so para carregar a bandeira.
PDV = {
    "segmento": SEGMENTO_PDV,
    "usa_ordem_servico": False,

    # Sem OS, nada abaixo e alcancavel. Ficam declarados vazios porque o guard
    # de contrato (test_registry_segmentos.py) percorre estas chaves em toda
    # definicao, e omiti-las quebraria o teste em vez de descrever o segmento.
    "rotulo_objeto_singular": "Item",
    "rotulo_objeto_plural": "Itens",
    "identificador": None,
    "capacidades": [],
    "veiculo": [],
    "checkin": [],
    "acessorios": [],
    "vistoria": [],
}
