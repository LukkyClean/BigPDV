# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/definicoes/serigrafia.py
# DESCRICAO: Definicao do segmento SERIGRAFIA (dado, nao motor).
#
# O NEGOCIO, em duas metades que NAO sao o mesmo modelo:
#
#   Camisa -- "contract printing": o cliente traz a peca e a loja vende so a
#   pintura. Nao ha estoque de peca, nem grade de tamanho, nem fornecedor.
#
#   Sacola -- a loja FABRICA e vende por peso.
#
# O QUE ESTE ARQUIVO NAO FAZ, DE PROPOSITO:
#
#   Preco. A loja cobra "valor de 1 unidade x quantidade", e o sistema ja faz
#   isso. Camisa entra como SERVICO no catalogo ("Pintura camisa 1 cor" R$4,50 /
#   "2 cores" R$5,00) e sacola como PRODUTO por tipo de papel. O dono edita os
#   valores nas telas que ja existem -- sem tela nova e sem gerar instalador
#   para trocar um numero. Um motor de faixas de preco chegou a ser desenhado e
#   foi cortado: esta loja nao usa faixa.
#
#   Molde/posicao NAO muda preco. Frente e costas com uma cor em cada custa o
#   mesmo que so frente (4,50) -- so o numero de CORES conta. Por isso o molde
#   e descricao de producao, e nao entra em conta nenhuma.
# ---------------------------------------------------------------------------

from typing import Any, Dict, List

from ..campos import campo, tipo_de_trabalho
from ..capacidades import CAP_IMAGEM_NA_ENTRADA

SEGMENTO_SERIGRAFIA = "serigrafia"

GRUPO_ARTE = "Dados da Arte"
GRUPO_ESTAMPA = "Estampa"
GRUPO_SACOLA = "Dados da Sacola"


def _campos_da_arte() -> List[Dict[str, Any]]:
    """A arte e o que se repete quando o cliente volta.

    Ela ocupa o lugar do objeto de servico -- o mesmo mecanismo que liga veiculo
    ao dono e equipamento ao cliente.

    REPARE NO QUE **NAO** ESTA AQUI: o codigo da arte.

    A primeira versao pedia "Codigo da arte" como campo obrigatorio, copiando o
    formato da placa e do numero de serie. Estava errado, e o dono do produto
    achou o erro com uma pergunta de uma linha: "e se e um cliente novo, como vou
    saber esse codigo?".

    Placa e numero de serie EXISTEM NO MUNDO -- estao escritos no bem. Codigo de
    arte nao existe ate alguem inventar. Campo obrigatorio que o usuario nao tem
    como preencher nao vira dado, vira lixo: "1", "arte", "teste" -- exatamente o
    "S/N" que ja colapsou dois notebooks num cadastro so (ver
    identificador_pesquisavel no motor).

    Os sistemas do ramo (Printavo, shopVOX, DecoNetwork, YoPrint) tambem nao tem
    codigo de arte: a arte e um ARQUIVO anexado ao pedido, achada pelo cliente e
    reaproveitada clonando o pedido anterior.

    Entao o codigo passou a ser GERADO (ver `identificador` desta definicao) e
    saiu da frente do atendente. Ele continua existindo -- e util impresso, para
    etiquetar a tela guardada na prateleira --, mas como SAIDA, nunca entrada.

    Sobra um campo obrigatorio: o nome da arte, que o atendente sabe.
    """
    return [
        campo("nome_arte", "Nome da arte", "texto", obrigatorio=True,
              escopo="objeto", grupo=GRUPO_ARTE, origem="coluna", coluna="modelo",
              largura="inteira"),
        # A arte pertence a uma empresa/marca, que nem sempre e quem paga: um
        # revendedor pode encomendar para tres clientes finais diferentes. Em
        # branco, o servico preenche com o nome do cliente da OS -- o caso comum
        # e a estampa ser da propria pessoa que esta pedindo.
        campo("empresa_arte", "Empresa / Marca da estampa", "texto",
              escopo="objeto", grupo=GRUPO_ARTE, origem="coluna", coluna="marca",
              largura="inteira"),
    ]


_CAMISA = tipo_de_trabalho("camisa", "Camisa (pintura)", [
    *_campos_da_arte(),

    # Quantas cores -- e o unico fator de preco, e ele entra pela escolha do
    # servico no catalogo. Aqui o numero e informacao de producao.
    campo("cores_quantidade", "Quantidade de cores", "inteiro",
          escopo="os", grupo=GRUPO_ESTAMPA),
    # Texto livre de proposito: cor de serigrafia nao cabe em lista ("verde
    # bandeira", "azul royal", Pantone). Enum aqui viraria campo que o
    # atendente contorna escrevendo no lugar errado.
    campo("cores_descricao", "Cores usadas", "texto",
          escopo="os", grupo=GRUPO_ESTAMPA, largura="inteira"),
    campo("molde", "Molde da pintura", "opcao",
          opcoes=["Frente", "Costas", "Frente e Costas", "Manga"],
          escopo="os", grupo=GRUPO_ESTAMPA),
    # Peca do cliente e o padrao neste negocio; o campo existe para o caso de a
    # loja fornecer, e para a via impressa poder dizer de quem e a peca.
    campo("peca_do_cliente", "Peça trazida pelo cliente", "booleano",
          escopo="os", grupo=GRUPO_ESTAMPA),
])


_SACOLA_PLASTICA = tipo_de_trabalho("sacola_plastica", "Sacola plástica", [
    *_campos_da_arte(),

    # Familias tiradas da tabela de referencias do proprio dono. "Vazada"
    # generica virou "Branca vazada" e "Plena vazada" (sao duas numeracoes
    # distintas na folha dele) e "Padrao" -- a familia com mais referencias --
    # nao existia na lista. "Mileiro" e "Vazada" seguem no fim por serem valores
    # que uma OS ja aberta pode ter gravado.
    campo("tipo_sacola", "Tipo de sacola", "opcao",
          opcoes=["Padrão", "Camiseta", "Alça fita", "Branca vazada",
                  "Plena vazada", "Mileiro", "Vazada"],
          escopo="os", grupo=GRUPO_SACOLA),
    # Referencia no lugar de medida: o dono nao pensa em "30x40x10 cm", pensa em
    # "referencia 20.1". E REPETIVEL porque uma mesma producao sai com varios
    # tamanhos. Texto (e nao numero) porque a numeracao dele tem "20.1",
    # "24 reduzida", "Bolo" e "P/M/G" convivendo.
    campo("referencias", "Referências", "lista",
          escopo="os", grupo=GRUPO_SACOLA, largura="inteira"),
    campo("cor_sacola", "Cor da sacola", "texto", escopo="os", grupo=GRUPO_SACOLA),
    campo("cor_impressao", "Cor da impressão", "texto", escopo="os", grupo=GRUPO_SACOLA),
])


_SACOLA_PAPEL = tipo_de_trabalho("sacola_papel", "Sacola de papel", [
    *_campos_da_arte(),

    # O papel muda o preco do quilo -- por isso cada papel e um PRODUTO no
    # catalogo, e este campo e a instrucao de producao correspondente.
    campo("tipo_papel", "Tipo de papel", "opcao",
          opcoes=["Kraft", "Duplex", "Offset"],
          escopo="os", grupo=GRUPO_SACOLA),
    campo("referencias", "Referências", "lista",
          escopo="os", grupo=GRUPO_SACOLA, largura="inteira"),
    campo("tipo_pintura", "Tipo da pintura", "opcao",
          opcoes=["Pintura frente", "Pintura total", "Pintura comum"],
          escopo="os", grupo=GRUPO_SACOLA),
    campo("cor_pintura", "Cor da pintura", "texto", escopo="os", grupo=GRUPO_SACOLA),
    campo("tipo_alca", "Tipo da alça", "opcao",
          opcoes=["Gorgorão", "Cordão"],
          escopo="os", grupo=GRUPO_SACOLA),
    campo("cor_alca", "Cor da alça", "texto", escopo="os", grupo=GRUPO_SACOLA),
])


SERIGRAFIA = {
    "segmento": SEGMENTO_SERIGRAFIA,
    "rotulo_objeto_singular": "Arte",
    "rotulo_objeto_plural": "Artes",

    # O campo `defeito_relatado` nasceu do modelo de CONSERTO: o cliente chega
    # com algo quebrado e conta o que houve. Aqui nao ha defeito -- o cliente
    # encomenda uma producao. O campo continua util (e o "o que ele pediu", em
    # texto livre, que sai impresso na via), mas com o nome certo.
    #
    # Segmento que nao declara isto continua com "Defeito Relatado", palavra por
    # palavra -- e o que mantem oficina e informatica intocadas.
    "rotulo_defeito": "Descrição do pedido",
    # Quem toca o pedido nao e "tecnico" -- nao ha o que consertar. E quem
    # responde pelo servico que esta sendo aberto.
    "rotulo_responsavel": "Responsável",
    "placeholder_defeito": "Ex: 100 camisas brancas, logo no peito, 2 cores",

    # O desfecho da OS e o MESMO enum de sempre (REPARADO/SEM_REPARO/CONDENADO)
    # -- so os rotulos mudam. O enum carrega uma regra que nao e de conserto:
    # SEM_REPARO e CONDENADO dispensam o pagamento integral
    # (services/ordem_servico.py), e e o unico jeito de fechar uma OS sem cobrar
    # tudo. Numa serigrafia isso acontece quando o cliente desiste ou reprova a
    # arte depois de adiantar.
    #
    # Trocar o enum exigiria migracao e mexeria em filtro, relatorio e badge de
    # historico dos dois segmentos em producao. Trocar o rotulo nao mexe em nada.
    #
    # "Situacao da Arte", inteiro: a tela montava 'Situacao do ' + rotulo, o que
    # imprimia "SITUACAO DO ARTE".
    "rotulo_situacao": "Situação da Arte",
    "rotulos_situacao": {
        "REPARADO": "Produzido",
        "SEM_REPARO": "Não produzido",
        "CONDENADO": "Perda na produção",
    },
    # `gerado` diz ao servico que o sistema cria este identificador -- o usuario
    # nao digita e o formulario nao pergunta. O codigo nasce do numero da OS
    # ("ART-0042"), entao e unico sem contador novo e sem corrida entre
    # terminais: ele herda a unicidade do numero da OS, que ja existe.
    #
    # Vale impresso: a tela (matriz) fica guardada numa prateleira e precisa de
    # etiqueta. "ART-0042" no quadro da tela e como se acha ela seis meses
    # depois. E o unico ponto em que eu discordo dos sistemas do ramo, que nao
    # tem codigo nenhum -- eles nao lidam com a prateleira fisica.
    "identificador": {
        "nome": "codigo_arte",
        "label": "Código da arte",
        "regex": None,
        "gerado": True,
        "prefixo": "ART",
    },

    # Nenhuma. Vistoria e revisoes nao se aplicam, e garantia de estampa seria
    # medida em lavagens, nao em dias/KM.
    #
    # A aprovacao de arte pelo celular chegou a ser construida e foi REMOVIDA
    # (10/08/2026): o QR aponta para o IP da LAN da loja, entao so abriria para
    # quem estivesse no Wi-Fi dela -- e aprovacao de arte e remota por natureza.
    # Com o cliente no balcao, mostrar a tela e ouvir "pode fazer" e mais
    # simples do que pedir para ele escanear. Refazer, se a loja um dia tiver
    # endereco publico, esta no historico do git.
    # A UNICA capacidade daqui: a imagem e a arte a ser estampada, entao entra
    # ja no primeiro cadastro e sai impressa na via de entrada -- e dela que
    # quem pinta trabalha. Nos outros segmentos a foto e prova do estado do bem
    # e nasce depois, com o aparelho na bancada.
    "capacidades": [CAP_IMAGEM_NA_ENTRADA],

    # Vazios porque este segmento declara por tipo de trabalho. O guard
    # (test/core/test_registry_segmentos.py) proibe usar os dois caminhos.
    "veiculo": [],
    "checkin": [],
    "acessorios": [],
    "vistoria": [],

    "tipos": [_CAMISA, _SACOLA_PLASTICA, _SACOLA_PAPEL],
}
