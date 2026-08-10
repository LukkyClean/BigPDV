# ---------------------------------------------------------------------------
# PACOTE: app/core/segmentos
# DESCRICAO: Registry (fonte de verdade) dos campos dinamicos de cada segmento
#            de negocio. Define quais chaves vao dentro de `dados_adicionais`
#            do objeto de servico e da OS, por segmento.
#
#            Este pacote NAO altera nenhuma tabela. Ele apenas descreve, de
#            forma declarativa, os campos que cada segmento usa dentro do JSON
#            `dados_adicionais` ja existente. E consumido por:
#              - services/segmentos.py  -> validacao (gated por segmento)
#              - endpoint de definicao  -> contrato para o frontend renderizar
#
# ORGANIZACAO (motor x dado):
#   capacidades.py     o que um segmento FAZ         -> motor
#   campos.py          tijolos de construcao         -> motor
#   identificador.py   o que vale como chave         -> motor
#   definicoes/        um arquivo por segmento       -> dado
#
#            A REGRA DO PROJETO: segmento novo so acrescenta DADO. Um segmento
#            que exija codigo novo no frontend e sinal de metadado faltando --
#            nao e trabalho de segmento. Foi assim que informatica e oficina
#            chegaram a producao sem uma quebrar a outra, e e o que permite
#            atender a proxima empresa sem risco para as duas que ja rodam.
#
#            Este __init__ reexporta a API publica: quem importa
#            `from app.core.segmentos import X` nao precisa saber em qual
#            arquivo X mora.
# ---------------------------------------------------------------------------

from .campos import campo, grupo_vistoria, tipo_de_trabalho
from .capacidades import (
    CAP_APROVACAO_ITENS,
    CAP_GARANTIA_ITENS,
    CAP_REVISOES,
    CAP_VISTORIA,
    CAPACIDADES_CONHECIDAS,
)
from .definicoes import (
    ASSISTENCIA,
    DEFINICOES,
    OFICINA,
    PLACA_REGEX,
    SEGMENTO_ASSISTENCIA,
    SEGMENTO_OFICINA,
    SEGMENTO_SERIGRAFIA,
    SERIGRAFIA,
    get_definicao_segmento,
    get_identificador_segmento,
    segmento_tem_definicao,
)
from .identificador import (
    IDENTIFICADOR_MIN_CARACTERES,
    IDENTIFICADORES_GENERICOS,
    identificador_pesquisavel,
    normalizar_identificador,
)

__all__ = [
    # capacidades
    "CAP_VISTORIA",
    "CAP_REVISOES",
    "CAP_APROVACAO_ITENS",
    "CAP_GARANTIA_ITENS",
    "CAPACIDADES_CONHECIDAS",
    # construcao
    "campo",
    "grupo_vistoria",
    "tipo_de_trabalho",
    # definicoes
    "DEFINICOES",
    "OFICINA",
    "ASSISTENCIA",
    "SERIGRAFIA",
    "PLACA_REGEX",
    "SEGMENTO_OFICINA",
    "SEGMENTO_ASSISTENCIA",
    "SEGMENTO_SERIGRAFIA",
    "get_definicao_segmento",
    "segmento_tem_definicao",
    "get_identificador_segmento",
    # identificador
    "IDENTIFICADORES_GENERICOS",
    "IDENTIFICADOR_MIN_CARACTERES",
    "normalizar_identificador",
    "identificador_pesquisavel",
]
