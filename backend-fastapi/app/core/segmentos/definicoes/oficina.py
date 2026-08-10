# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/definicoes/oficina.py
# DESCRICAO: Definicao do segmento OFICINA MECANICA (dado, nao motor).
#            Baseado na ficha de vistoria de entrada usada pela loja.
#
#            EM PRODUCAO. Alterar aqui muda a tela de uma loja que esta
#            faturando -- ver [project_informatica_producao].
# ---------------------------------------------------------------------------

from ..campos import campo, grupo_vistoria
from ..capacidades import (
    CAP_APROVACAO_ITENS,
    CAP_GARANTIA_ITENS,
    CAP_REVISOES,
    CAP_VISTORIA,
)

SEGMENTO_OFICINA = "oficina_mecanica"

# Regex de placa: aceita padrao antigo (ABC-1234 / ABC1234) e Mercosul (ABC1D23).
# A validacao real normaliza (uppercase, sem hifen) antes de aplicar.
PLACA_REGEX = r"^(?:[A-Z]{3}\d{4}|[A-Z]{3}\d[A-Z]\d{2})$"


OFICINA = {
    "segmento": SEGMENTO_OFICINA,
    # Rotulos que o frontend usa para nomear a entidade no lugar de "Objeto".
    "rotulo_objeto_singular": "Veículo",
    "rotulo_objeto_plural": "Veículos",
    # Campo do objeto que serve de identificador principal (mapeia numero_serie).
    "identificador": {"nome": "placa", "label": "Placa", "regex": PLACA_REGEX},

    # O que o segmento faz (ver ../capacidades.py).
    "capacidades": [
        CAP_VISTORIA,
        CAP_REVISOES,
        CAP_APROVACAO_ITENS,
        CAP_GARANTIA_ITENS,
    ],

    # --- Dados do veiculo (escopo=objeto) ---
    "veiculo": [
        campo("placa", "Placa", "texto", obrigatorio=True, escopo="objeto"),
        campo("marca", "Marca", "texto", escopo="objeto"),
        campo("modelo", "Modelo", "texto", escopo="objeto"),
        campo("cor", "Cor", "texto", escopo="objeto"),
        campo("ano", "Ano", "inteiro", escopo="objeto"),
        campo("chassi", "Chassi", "texto", escopo="objeto"),
    ],

    # --- Check-in de entrada (escopo=os) ---
    "checkin": [
        campo("km_entrada", "KM de entrada", "inteiro", escopo="os"),
        campo("prisma", "Prisma", "texto", escopo="os"),
        campo("ct", "CT", "texto", escopo="os"),
        campo("estacao_radio", "Estação do rádio", "texto", escopo="os"),
        campo("combustivel_nivel", "Nível de combustível", "opcao",
              opcoes=["VAZIO", "1/4", "1/2", "3/4", "CHEIO"], escopo="os"),
        campo("combustivel_tipo", "Tipo de combustível", "opcao",
              opcoes=["ALCOOL", "GASOLINA", "DIESEL"], escopo="os"),
        campo("pneus_estado", "Estado dos pneus", "opcao",
              opcoes=["BOM", "REGULAR", "RUIM"], escopo="os"),
        campo("estepe_estado", "Estado do estepe", "opcao",
              opcoes=["BOM", "REGULAR", "RUIM"], escopo="os"),
    ],

    # --- Acessorios presentes (checklist sim/nao) ---
    "acessorios": [
        "acendedor", "calota", "chave_de_roda", "estepe", "extintor",
        "gps", "haste_antena", "macaco", "manual", "radio_cd_dvd",
        "pen_drive", "roda_liga_leve", "triangulo", "outros",
    ],

    # --- Vistoria de inspecao (3 blocos, cada item = OK / N_OK / REPARAR) ---
    "vistoria": [
        grupo_vistoria("Inspeção externa (carro no chão)", [
            "antena_teto", "pintura_manchas_riscos_amassados", "bagageiro",
            "farois", "frisos_laterais", "lanternas", "portas",
            "rodas_calotas", "percepcoes_de_uso",
        ]),
        grupo_vistoria("Inspeção interna", [
            "antena_interna", "bancos_dianteiros_revestimentos_cintos",
            "bancos_traseiros_revestimentos_cintos",
            "comutadores_consumidores_eletricos_comandos", "contem_som",
            "direcao", "sinais_de_criancas", "sinais_odores_cigarro",
            "vidros_eletricos", "uso_de_celular", "percepcoes_de_uso",
        ]),
        grupo_vistoria("Inspeção externa (carro no elevador)", [
            "escapamento", "estribos_laterais", "pneus", "protetor_de_carter",
            "rodas", "sinais_de_impacto", "suspensao_coifas",
            "vazamentos_oleo_agua_fluidos", "percepcoes_de_uso",
        ]),
    ],
}
