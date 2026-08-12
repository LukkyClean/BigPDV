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

# A imagem faz parte do PEDIDO, e nao do laudo.
#
# Em oficina e informatica a foto e prova do estado do bem: nasce depois, com o
# aparelho ja na bancada, e por isso a aba de imagens so aparece na OS ja salva.
# Em serigrafia a imagem E a arte a ser estampada -- sem ela nao ha o que
# produzir. Ela precisa entrar no primeiro cadastro, junto com o pedido, e sair
# na via de entrada para quem vai pintar poder trabalhar a partir do papel.
#
# Ligar esta capacidade faz duas coisas: libera a aba de imagens durante a
# criacao da OS e imprime as imagens na via de ENTRADA. Segmento que nao a
# declara continua exatamente como sempre foi.
CAP_IMAGEM_NA_ENTRADA = "imagem_na_entrada"

# O servico tem garantia contada em PRAZO (dias/meses), escolhida ao finalizar.
#
# Faz sentido onde se conserta: o reparo responde por um periodo. Numa
# serigrafia a estampa nao tem prazo -- se dura, mede-se em LAVAGENS, e ninguem
# conta dia de camisa. Pedir "90 dias" ali obriga o atendente a responder uma
# pergunta que nao existe, e ainda faz a via prometer uma garantia que a loja
# nao deu.
#
# Desligada, o campo some da finalizacao e o Termo de Garantia so e impresso
# quando houver prazo de fato. As exclusoes de garantia (o "NAO COBRE") seguem
# no pacote de textos, que e outro assunto.
CAP_GARANTIA_PRAZO = "garantia_prazo"

CAPACIDADES_CONHECIDAS = [
    CAP_VISTORIA,
    CAP_REVISOES,
    CAP_APROVACAO_ITENS,
    CAP_GARANTIA_ITENS,
    CAP_DIAGNOSTICO,
    CAP_IMAGEM_NA_ENTRADA,
    CAP_GARANTIA_PRAZO,
]
