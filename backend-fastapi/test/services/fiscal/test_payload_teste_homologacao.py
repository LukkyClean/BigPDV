# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_payload_teste_homologacao.py
# DESCRIÇÃO: A nota de teste de homologação — a única que ninguém cobria.
#
# `montar_payload_teste_nfe` era o único construtor de payload sem teste, e foi
# o único que a SEFAZ recusou duas vezes seguidas:
#
#   1. 422 nomeando logradouro/numero/bairro/municipio do destinatário e
#      modalidade_frete — o grupo enderDest não existia no payload.
#   2. CPF "00000000000" no destinatário — homologação dispensa a EXISTÊNCIA do
#      destinatário, nunca o dígito verificador.
#
# O segundo é o mais constrangedor: o projeto tem `validar_cpf`, que rejeita
# onze zeros desde sempre. O payload de teste simplesmente nunca passou por ele.
# É o que este arquivo conserta — as conferências abaixo são as do próprio
# sistema, viradas contra o payload que ele mesmo monta.
# ---------------------------------------------------------------------------

import pytest

from app.core.enum import State
from app.core.validators import validar_cnpj, validar_cpf
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
from app.services.fiscal.payload_builder import montar_payload_teste_nfe


@pytest.fixture
def payload():
    empresa = Empresa(
        id=1,
        razao_social="LOJA TESTE LTDA",
        nome_fantasia="Loja Teste",
        documento="11222333000181",
        is_cnpj=True,
        regime_tributario="Simples Nacional",
        inscricao_estadual="123456789",
        indicador_ie="1",
    )
    endereco = Endereco(
        logradouro="Rua das Flores",
        numero="100",
        complemento="Sala 2",
        bairro="Centro",
        cidade="Sao Paulo",
        estado=State.SAO_PAULO,
        cep="01001-000",
    )
    fiscal_settings = EmpresaFiscalSettings(
        empresa_id=1, ambiente_emissao=2, serie_nfe=1, ultimo_numero_nfe=0,
    )
    return montar_payload_teste_nfe(empresa, endereco, fiscal_settings)


# ---------------------------------------------------------------------------
# 1. O documento do destinatário
# ---------------------------------------------------------------------------

def test_documento_do_destinatario_passa_no_digito_verificador(payload):
    """A recusa nº 2, travada.

    Não basta "ter 14 dígitos": o que a SEFAZ confere é o módulo 11, e é por
    isso que a conferência aqui é a mesma função que o cadastro usa.
    """
    dest = payload["destinatario"]

    assert "cpf" not in dest, "CPF fictício válido pode ser de uma pessoa real"
    assert validar_cnpj(dest["cnpj"]) == "99999999000191"


def test_cpf_antigo_seria_recusado_pelo_proprio_sistema():
    """A prova de que o defeito era detectável aqui dentro o tempo todo."""
    with pytest.raises(ValueError):
        validar_cpf("00000000000")


def test_destinatario_declara_nao_contribuinte(payload):
    # indIEDest 9. Sem ele a SEFAZ cobra inscrição estadual de um destinatário
    # que não tem nenhuma.
    assert payload["destinatario"]["indicador_ie"] == "9"


def test_nome_do_destinatario_e_a_frase_exigida_em_homologacao(payload):
    assert payload["destinatario"]["nome"] == (
        "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
    )


# ---------------------------------------------------------------------------
# 2. O endereço do destinatário e o frete
# ---------------------------------------------------------------------------

def test_enderdest_vem_completo(payload):
    """A recusa nº 1, travada. Na NF-e o enderDest é obrigatório."""
    endereco = payload["destinatario"]["endereco"]

    for campo in ("logradouro", "numero", "bairro", "cidade", "uf", "cep"):
        assert endereco.get(campo), f"enderDest sem {campo}"


def test_endereco_do_destinatario_e_o_do_emitente(payload):
    """Reuso deliberado: o par município/UF já foi aceito no cadastro.

    A Focus resolve município + UF para código IBGE. Um endereço inventado pode
    cair num município que não existe naquela UF, e aí a nota de teste falha por
    um motivo que nada tem a ver com o que se queria testar.
    """
    assert payload["destinatario"]["endereco"]["cidade"] == payload["emitente"]["endereco"]["cidade"]
    assert payload["destinatario"]["endereco"]["uf"] == payload["emitente"]["endereco"]["uf"]


def test_cep_vai_sem_pontuacao(payload):
    # O cadastro guarda "01001-000"; a SEFAZ quer só dígitos.
    assert payload["destinatario"]["endereco"]["cep"] == "01001000"


def test_modalidade_frete_presente(payload):
    # modFrete 9 = sem transporte. Obrigatório na NF-e 4.0 mesmo sem frete.
    assert payload["modalidade_frete"] == 9
