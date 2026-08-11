# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/capacidades.py
# DESCRICAO: O que um segmento FAZ (motor). Ver o __init__.py do pacote.
# ---------------------------------------------------------------------------

# ===========================================================================
# CAPACIDADES
# ===========================================================================
# O que um segmento FAZ, em oposicao a quais campos ele tem. Existe porque o
# frontend precisava perguntar "quem e o cliente?" (if segmento == oficina) para
# decidir se mostrava a aprovacao de itens, a vistoria, etc. Isso obrigava a
# editar o frontend a cada segmento novo.
#
# Com capacidades, o frontend pergunta "o que este segmento faz?" e liga a UI
# pelo contrato. Ligar uma capacidade para um segmento novo passa a ser uma
# linha no arquivo de definicao do segmento, sem tocar em Vue.
#
# NAO sao exclusivas de nenhum segmento: aprovacao de orcamento e garantia
# servem qualquer negocio de servico. Hoje so a oficina as usa porque foi para
# ela que foram construidas -- nao porque sejam "de oficina".

CAP_VISTORIA = "vistoria"                # checklist de inspecao (DVI) na entrada
CAP_REVISOES = "revisoes"                # lembrete de manutencao por data/KM
CAP_APROVACAO_ITENS = "aprovacao_itens"  # cliente aprova/reprova item do orcamento
CAP_GARANTIA_ITENS = "garantia_itens"    # garantia (dias/KM) por item

# O negocio DIAGNOSTICA antes de executar: recebe algo com problema, investiga e
# emite laudo. E o caso de oficina e informatica.
#
# Serigrafia nao diagnostica nada -- o cliente chega dizendo o que quer, e a
# loja produz. Sem esta capacidade, a aba deixa de pedir laudo tecnico e passa a
# servir so para as imagens (que em serigrafia sao a ARTE -- por isso a aba
# continua existindo).
CAP_DIAGNOSTICO = "diagnostico"

CAPACIDADES_CONHECIDAS = [
    CAP_VISTORIA,
    CAP_REVISOES,
    CAP_APROVACAO_ITENS,
    CAP_GARANTIA_ITENS,
    CAP_DIAGNOSTICO,
]
