# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/campos.py
# DESCRICAO: Vocabulario de construcao das definicoes (motor). Sao os tijolos
#            que os arquivos de `definicoes/` usam para se declarar.
# ---------------------------------------------------------------------------

from typing import Any, Dict, List, Optional

# ===========================================================================
# VOCABULARIO SUPORTADO
# ===========================================================================
# Estas listas sao a fronteira entre o que um segmento PODE declarar e o que o
# sistema sabe desenhar. Elas existem para o guard de contrato
# (test/core/test_registry_segmentos.py) poder falhar quando alguem declara um
# campo que ninguem sabe renderizar -- metadado orfao e a unica forma de um
# segmento novo quebrar uma tela em producao.

# "lista" e um campo REPETIVEL de texto: o valor gravado e uma list[str], nao
# uma string. Nasceu da serigrafia, onde uma mesma OS produz sacolas de varios
# tamanhos e o dono trabalha por REFERENCIA ("20.1", "22", "Bolo") em vez de
# medida -- um campo de texto so nao comporta a lista. Fica no vocabulario do
# motor, e nao num componente da serigrafia, porque a regra do projeto e que
# segmento novo so acrescente declaracao: qualquer segmento futuro que precise
# de "varios valores do mesmo tipo" ja tem onde se apoiar.
TIPOS_DE_CAMPO_SUPORTADOS = ("texto", "numero", "inteiro", "opcao", "booleano", "lista")

# Onde o valor e persistido de fato.
#   dados_adicionais -> chave dentro do JSON (o caso de todo campo novo)
#   coluna           -> coluna real da tabela; exige `coluna` quando o nome do
#                       campo difere do nome da coluna (ex: placa -> numero_serie)
ORIGENS_SUPORTADAS = ("dados_adicionais", "coluna")

# Em qual entidade o valor mora: no objeto de servico ou na propria OS.
ESCOPOS_SUPORTADOS = ("objeto", "os")

# Quanto o campo ocupa na grade de 2 colunas do formulario.
LARGURAS_SUPORTADAS = ("meia", "inteira")


def campo(
    nome: str,
    label: str,
    tipo: str,
    obrigatorio: bool = False,
    opcoes: Optional[List[str]] = None,
    escopo: str = "objeto",
    grupo: Optional[str] = None,
    largura: str = "meia",
    origem: str = "dados_adicionais",
    coluna: Optional[str] = None,
) -> Dict[str, Any]:
    """Descreve um campo dinamico.

    tipo:    ver TIPOS_DE_CAMPO_SUPORTADOS
    escopo:  'objeto' (dados do bem) | 'os' (dados da OS/check-in)
    grupo:   cabecalho da secao em que o campo aparece no formulario
    largura: 'meia' | 'inteira' na grade de 2 colunas
    origem:  'dados_adicionais' (padrao) | 'coluna'
    coluna:  nome da coluna real, quando difere de `nome` e origem='coluna'

    `origem` tem padrao 'dados_adicionais' de proposito: e o padrao SEGURO.
    Errar para o JSON nao corrompe nada nem exige migracao; errar para uma
    coluna gravaria no lugar errado. Campo que E coluna precisa dizer isso em
    voz alta.
    """
    resultado: Dict[str, Any] = {
        "nome": nome,
        "label": label,
        "tipo": tipo,
        "obrigatorio": obrigatorio,
        "escopo": escopo,
        "grupo": grupo,
        "largura": largura,
        "origem": origem,
    }
    if opcoes is not None:
        resultado["opcoes"] = opcoes
    if coluna is not None:
        resultado["coluna"] = coluna
    return resultado


def tipo_de_trabalho(id: str, label: str, campos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Um processo de negocio dentro do mesmo segmento.

    Oficina e informatica tem UM processo so: toda OS e sobre um veiculo, ou
    toda OS e sobre um equipamento. Serigrafia e o primeiro segmento em que a
    OS pode ser de coisas diferentes (camisa ou sacola), cada uma com seus
    campos -- entao o formulario precisa perguntar "o que e este trabalho?"
    antes de saber o que mostrar.

    Segmento que NAO declara `tipos` continua exatamente como sempre foi: e o
    que mantem oficina e informatica intocadas.
    """
    return {"id": id, "label": label, "campos": campos}


def grupo_vistoria(titulo: str, itens: List[str]) -> Dict[str, Any]:
    """Grupo de itens de inspecao. Cada item e avaliado como OK / N_OK / REPARAR."""
    return {
        "titulo": titulo,
        "estados": ["OK", "N_OK", "REPARAR"],
        "itens": itens,
    }
