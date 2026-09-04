"""
Testes do setup inicial quanto ao tipo de pessoa da empresa.

O sistema pode ser instalado por um autônomo (CPF) ou por uma empresa (CNPJ).
O setup gravava o CPF apenas no Funcionário e deixava `empresas.documento` e
`empresas.razao_social` nulos — o cadastro nascia sem documento, os cupons
saíam sem a linha "CPF:" e a tela de Empresa não deixava salvar nada.

Estes testes travam os dois caminhos: o de PF (o que foi corrigido) e o de PJ
(que precisa continuar exatamente como estava).
"""

import pytest
from sqlalchemy.orm import Session

from app.schemas.auth import SetupCreate
from app.services.setup import setup_sistema
from app.db.models.empresa import Empresa
from app.db.models.funcionario import Funcionario


CPF_RESPONSAVEL = "12345678909"
CNPJ_EMPRESA = "12345678000199"


@pytest.fixture(autouse=True)
def pular_registro_de_licenca(monkeypatch):
    """
    Neutraliza o registro de licença (passo 1.5 do setup), que fala com a API
    externa. Fingir que já existe licença para o HWID faz o setup pular o bloco
    inteiro sem alterar nada do que está sendo testado aqui.
    """
    import app.core.hwid as hwid_module
    import app.db.crud.configuracao_licenca as licenca_crud

    monkeypatch.setattr(hwid_module, "obter_hwid", lambda: "hwid-de-teste")
    monkeypatch.setattr(
        licenca_crud, "get_licenca_by_hwid", lambda db, hwid: object()
    )


def montar_setup_pf() -> SetupCreate:
    return SetupCreate(
        nome_loja="Serigrafia do Alan",
        tipo_pessoa="PF",
        nome_responsavel="Alan Alves",
        cpf=CPF_RESPONSAVEL,
        nome_usuario="Alan",
        email="alan@example.com",
        senha="senhaSegura456",
    )


def montar_setup_pj() -> SetupCreate:
    return SetupCreate(
        nome_loja="Tech Teste",
        tipo_pessoa="PJ",
        nome_responsavel="Alan Alves",
        razao_social="Tech Teste LTDA",
        cnpj=CNPJ_EMPRESA,
        inscricao_estadual="ISENTO",
        nome_usuario="Alan",
        email="alan@example.com",
        senha="senhaSegura456",
    )


def test_setup_pf_grava_cpf_e_nome_na_empresa(db_session: Session):
    """Em PF, o CPF e o nome do responsável SÃO o documento e a razão social."""
    setup_sistema(db_session, montar_setup_pf())
    db_session.commit()

    empresa = db_session.query(Empresa).one()

    assert empresa.is_cnpj is False
    assert empresa.documento == CPF_RESPONSAVEL
    assert empresa.razao_social == "Alan Alves"
    # O nome da loja continua sendo o nome fantasia, não o nome da pessoa.
    assert empresa.nome_fantasia == "Serigrafia do Alan"


def test_setup_pf_mantem_cpf_no_funcionario(db_session: Session):
    """Gravar o CPF na empresa não pode tirá-lo do cadastro do funcionário."""
    setup_sistema(db_session, montar_setup_pf())
    db_session.commit()

    funcionario = db_session.query(Funcionario).one()

    assert funcionario.cpf == CPF_RESPONSAVEL
    assert funcionario.nome == "Alan Alves"


def test_setup_pf_nao_preenche_campos_fiscais_de_pj(db_session: Session):
    """PF não tem IE, IM nem regime tributário."""
    setup_sistema(db_session, montar_setup_pf())
    db_session.commit()

    empresa = db_session.query(Empresa).one()

    assert empresa.inscricao_estadual is None
    assert empresa.inscricao_municipal is None
    assert empresa.regime_tributario is None


def test_setup_pj_permanece_inalterado(db_session: Session):
    """Regressão: o caminho de PJ (o que está em produção) não pode mudar."""
    setup_sistema(db_session, montar_setup_pj())
    db_session.commit()

    empresa = db_session.query(Empresa).one()

    assert empresa.is_cnpj is True
    assert empresa.documento == CNPJ_EMPRESA
    assert empresa.razao_social == "Tech Teste LTDA"
    assert empresa.nome_fantasia == "Tech Teste"
    assert empresa.inscricao_estadual == "ISENTO"

    # Em PJ o CPF do responsável não é coletado, então o funcionário fica sem.
    funcionario = db_session.query(Funcionario).one()
    assert funcionario.cpf is None
