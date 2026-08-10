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
from ..capacidades import CAP_APROVACAO_ARTE

SEGMENTO_SERIGRAFIA = "serigrafia"

GRUPO_ARTE = "Dados da Arte"
GRUPO_ESTAMPA = "Estampa"
GRUPO_SACOLA = "Dados da Sacola"


def _campos_da_arte() -> List[Dict[str, Any]]:
    """A arte e o que se repete quando o cliente volta.

    Ela ocupa o lugar do objeto de servico -- o mesmo mecanismo que liga veiculo
    ao dono e equipamento ao cliente. Cliente volta em outubro pedindo mais 200
    com a mesma arte, e o historico, a busca e o "ja fiz isso pra ela" saem de
    graca do motor que ja existe.

    Os tres campos sao COLUNAS de objetos_servico (NOT NULL), por isso
    `origem="coluna"`. `codigo_arte` grava em `numero_serie`, do mesmo jeito que
    a placa da oficina -- o nome do campo nao e o nome da coluna, e e o contrato
    que carrega essa diferenca.

    Repetido nos tres tipos de trabalho porque a arte existe em todos; a funcao
    evita triplicar a declaracao a mao.
    """
    return [
        campo("codigo_arte", "Código da arte", "texto", obrigatorio=True,
              escopo="objeto", grupo=GRUPO_ARTE, origem="coluna", coluna="numero_serie"),
        campo("nome_arte", "Nome da arte", "texto", obrigatorio=True,
              escopo="objeto", grupo=GRUPO_ARTE, origem="coluna", coluna="modelo"),
        # A arte pertence a uma empresa/marca, que nem sempre e quem paga: um
        # revendedor pode encomendar para tres clientes finais diferentes.
        campo("empresa_arte", "Empresa / Marca da estampa", "texto", obrigatorio=True,
              escopo="objeto", grupo=GRUPO_ARTE, origem="coluna", coluna="marca"),
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

    campo("tipo_sacola", "Tipo de sacola", "opcao",
          opcoes=["Alça fita", "Vasada", "Camiseta", "Mileiro"],
          escopo="os", grupo=GRUPO_SACOLA),
    campo("medidas", "Medidas (L × A × fole)", "texto",
          escopo="os", grupo=GRUPO_SACOLA),
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
    campo("medidas", "Medidas (L × A × fole)", "texto",
          escopo="os", grupo=GRUPO_SACOLA),
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
    "identificador": {"nome": "codigo_arte", "label": "Código da arte", "regex": None},

    # Vistoria e revisoes nao se aplicam; garantia de estampa seria medida em
    # lavagens, e nao em dias/KM. Fica a aprovacao de ARTE: o cliente ve o
    # mockup no celular e libera a producao -- e o unico ponto do processo em
    # que estampar errado ainda custa barato.
    "capacidades": [CAP_APROVACAO_ARTE],

    # Vazios porque este segmento declara por tipo de trabalho. O guard
    # (test/core/test_registry_segmentos.py) proibe usar os dois caminhos.
    "veiculo": [],
    "checkin": [],
    "acessorios": [],
    "vistoria": [],

    "tipos": [_CAMISA, _SACOLA_PLASTICA, _SACOLA_PAPEL],
}
