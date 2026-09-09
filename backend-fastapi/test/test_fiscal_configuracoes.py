import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings


@pytest.fixture(autouse=True)
def _licenca_com_nfe(monkeypatch):
    """Concede o módulo NFE à licença durante estes testes.

    A NF-e NEGA por padrão quando a licença não responde (ver
    test/core/test_modulo_nfe_nega_por_padrao.py), e no ambiente de teste não
    há licença nenhuma -- sem isto toda rota /fiscal responderia 403.

    A trava tem testes próprios; aqui o objetivo é exercitar o que vem DEPOIS
    dela, então o módulo é concedido de propósito.
    """
    from app.core import modulos as modulos_mod

    monkeypatch.setattr(
        modulos_mod.licenca_service, "modulos_da_licenca", lambda _db: ["NFE"]
    )


@pytest.fixture
def header_with_token(client: TestClient, db_session: Session, create_test_empresa) -> dict:
    login_data = {
        "username": "teste.funcionario@example.com",
        "password": "senhaSegura456",
        "hwid": "test-terminal-hwid"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def setup_fiscal_settings(db_session: Session, header_with_token: dict, client: TestClient):
    from app.db.models.empresa import Empresa
    empresa = db_session.query(Empresa).first()
    if not empresa:
        pytest.fail("Nenhuma empresa encontrada.")
    empresa_id = empresa.id
    
    fs = EmpresaFiscalSettings(
        empresa_id=empresa_id,
        ambiente_emissao=2,
        serie_nfe=1,
        ultimo_numero_nfe=0,
        serie_nfce=1,
        ultimo_numero_nfce=0,
        tipo_certificado="ARQUIVO"
    )
    db_session.add(fs)
    db_session.commit()
    db_session.refresh(fs)
    return fs

def test_get_configuracao_fiscal(client: TestClient, header_with_token: dict, setup_fiscal_settings):
    response = client.get("/api/v1/fiscal/configuracao", headers=header_with_token)
    assert response.status_code == 200
    data = response.json()
    assert data["ambiente"] == 2
    assert data["ambiente_label"] == "Homologação"

def test_put_configuracao_fiscal(client: TestClient, header_with_token: dict, setup_fiscal_settings):
    payload = {
        "ambiente_emissao": 1,
        "serie_nfe": 2,
        "tipo_certificado": "NUVEM"
    }
    response = client.put("/api/v1/fiscal/configuracao", json=payload, headers=header_with_token)
    assert response.status_code == 200
    data = response.json()
    assert data["ambiente"] == 1
    assert data["ambiente_label"] == "Produção"

def test_upload_certificado_focus_invalid_password(client: TestClient, header_with_token: dict, setup_fiscal_settings):
    # Mocking is done inside upload_certificado_focus? Actually the service calls Focus API or validates password
    # In BigPDV, usually if the password is wrong, the external service fails or we mock it.
    # We can try hitting it directly and it should return 400 if we send a dummy file and dummy password,
    # assuming the service validates the certificate or the mock does it.
    # Let's send a simple text file as .pfx
    
    file_content = b"dummy certificate content"
    files = {
        "file": ("cert.pfx", file_content, "application/x-pkcs12")
    }
    data = {
        "senha": "senha_invalida"
    }
    
    # Using pytest-mock to mock the external call if needed. But let's just see what the service does.
    # The prompt says "(you may need to mock the external call to Focus NFe / API Online)".
    
    with pytest.MonkeyPatch.context() as m:
        # Mocking the external focus API call to throw an error for invalid password
        # Since we just want to ensure we get a 400 when invalid password, we can mock `upload_certificado_focus`
        # wait, the service does the logic. Let's mock `focus_api.upload_certificado` or similar.
        pass

    # Actually, the instructions say to test POST upload-focus with invalid password (400)
    # Let's write the request first.
    response = client.post(
        "/api/v1/fiscal/certificado/upload-focus",
        headers=header_with_token,
        data=data,
        files=files
    )
    # We'll see what it actually returns. If we need to mock, we'll patch it.
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# PERSISTÊNCIA — a configuração precisa SOBREVIVER à requisição
#
# Os testes acima olham só o corpo da resposta, e por isso passavam com o
# defeito: `update_fiscal_settings` e `upload_certificado_focus` terminavam em
# `flush`, nunca em `commit`, e o objeto devolvido vinha da sessão ainda aberta
# -- a resposta mostrava os valores novos que o banco nunca recebeu. Como o
# `get_db` só FECHA a sessão, e fechar com transação pendente descarta a
# escrita, o lojista via "salvo com sucesso" e encontrava tudo como antes na
# volta.
#
# Ler de novo, numa requisição NOVA (o TestClient abre outra sessão a cada
# chamada, como em produção), é o que separa "a resposta disse" de "o banco
# gravou".
# ---------------------------------------------------------------------------

def _gerar_pfx(senha: bytes, dias_de_validade: int = 365) -> bytes:
    """Certificado A1 autoassinado, só para exercitar o upload."""
    from datetime import datetime, timedelta, timezone

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "LOJA TESTE LTDA:12345678000199"),
    ])
    agora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=dias_de_validade))
        .sign(chave, hashes.SHA256())
    )

    return pkcs12.serialize_key_and_certificates(
        name=b"teste",
        key=chave,
        cert=certificado,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha),
    )


def test_put_configuracao_fiscal_sobrevive_a_requisicao(
    client: TestClient, header_with_token: dict, setup_fiscal_settings
):
    """O que o PUT grava tem que estar lá no GET seguinte."""
    payload = {"ambiente_emissao": 1, "serie_nfe": 7, "tipo_certificado": "NUVEM"}

    resposta_put = client.put(
        "/api/v1/fiscal/configuracao", json=payload, headers=header_with_token
    )
    assert resposta_put.status_code == 200
    assert resposta_put.json()["serie_nfe"] == 7

    # Requisição nova, sessão nova -- é aqui que o `flush` sem `commit` some.
    resposta_get = client.get("/api/v1/fiscal/configuracao", headers=header_with_token)
    assert resposta_get.status_code == 200
    dados = resposta_get.json()
    assert dados["serie_nfe"] == 7, "a série voltou ao valor antigo: não foi commitada"
    assert dados["ambiente"] == 1, "o ambiente voltou ao valor antigo: não foi commitado"


def test_upload_certificado_focus_sobrevive_a_requisicao(
    client: TestClient, header_with_token: dict, setup_fiscal_settings
):
    """O certificado aceito precisa aparecer como configurado depois."""
    senha = b"senha-do-pfx"
    arquivo = {"file": ("cert.pfx", _gerar_pfx(senha), "application/x-pkcs12")}

    resposta_upload = client.post(
        "/api/v1/fiscal/certificado/upload-focus",
        headers=header_with_token,
        data={"senha": senha.decode()},
        files=arquivo,
    )
    assert resposta_upload.status_code == 200

    resposta_get = client.get("/api/v1/fiscal/configuracao", headers=header_with_token)
    assert resposta_get.status_code == 200
    dados = resposta_get.json()
    assert dados["certificado_configurado"] is True, (
        "o Centro Fiscal continua dizendo 'Não configurado' depois de um upload "
        "bem-sucedido — o certificado não foi commitado"
    )
    assert dados["certificado_status"] == "CONECTADO_NUVEM"
    assert dados["certificado_valido"] is True


# ---------------------------------------------------------------------------
# DIAGNÓSTICO DA PLATAFORMA
#
# Responde "de quem é o problema" sem abrir chamado. Nasceu do episódio em que a
# loja recebeu "CNPJ do emitente não autorizado" e não havia como saber, de
# dentro do sistema, se a recusa vinha do cadastro daqui ou da ficha de lá.
# ---------------------------------------------------------------------------

class _ClienteFake:
    def __init__(self, config):
        self._config = config

    def consultar_config(self):
        return self._config


def _fingir_plataforma(monkeypatch, config):
    from app.services.fiscal import http as http_mod

    monkeypatch.setattr(
        http_mod, "get_fiscal_client", lambda ambiente, token="": _ClienteFake(config)
    )


def test_diagnostico_sem_resposta_da_plataforma_nao_acusa(
    client: TestClient, header_with_token: dict, setup_fiscal_settings, monkeypatch
):
    """Plataforma muda: "não sei" NUNCA pode virar "não configurado"."""
    _fingir_plataforma(monkeypatch, {})

    resposta = client.get("/api/v1/fiscal/plataforma", headers=header_with_token)
    assert resposta.status_code == 200
    dados = resposta.json()

    assert dados["consultou"] is False
    assert dados["configurado"] is None, "silêncio da plataforma virou acusação"
    assert dados["csc_configurado"] is None
    # O lado de cá a gente sabe mesmo sem ela.
    assert dados["cnpj_erp"] is None or dados["cnpj_erp"].isdigit()


def test_diagnostico_mapeia_o_que_a_plataforma_responde(
    client: TestClient, header_with_token: dict, setup_fiscal_settings, monkeypatch
):
    _fingir_plataforma(monkeypatch, {
        "ambiente": 2,
        "ambienteNome": "Homologação",
        "configurado": True,
        "tokenConfigurado": True,
        "cscConfigurado": False,
        "certificadoStatus": "OK",
        "pendencias": ["CSC não cadastrado"],
    })

    dados = client.get("/api/v1/fiscal/plataforma", headers=header_with_token).json()

    assert dados["consultou"] is True
    assert dados["ambiente"] == 2
    assert dados["ambiente_nome"] == "Homologação"
    assert dados["token_configurado"] is True
    assert dados["csc_configurado"] is False
    assert dados["certificado_status"] == "OK"
    assert dados["pendencias"] == ["CSC não cadastrado"]


def test_diagnostico_nao_inventa_divergencia_de_cnpj(
    client: TestClient, header_with_token: dict, setup_fiscal_settings, monkeypatch
):
    """Sem o CNPJ da plataforma, `cnpj_confere` é None — não é False.

    Hoje o `GET /erp/fiscal/config` não devolve o CNPJ da ficha. Enquanto não
    devolver, a tela precisa dizer "a plataforma não informa" em vez de acusar
    uma divergência que ninguém mediu.
    """
    _fingir_plataforma(monkeypatch, {"ambiente": 2, "configurado": True})

    dados = client.get("/api/v1/fiscal/plataforma", headers=header_with_token).json()

    assert dados["cnpj_plataforma"] is None
    assert dados["cnpj_confere"] is None


def test_diagnostico_compara_quando_a_plataforma_manda_o_cnpj(
    client: TestClient, header_with_token: dict, setup_fiscal_settings, monkeypatch
):
    _fingir_plataforma(monkeypatch, {
        "ambiente": 2,
        "configurado": True,
        "cnpj": "11.222.333/0001-81",
    })

    dados = client.get("/api/v1/fiscal/plataforma", headers=header_with_token).json()

    # Comparação sempre em dígitos: máscara dos dois lados não pode virar
    # divergência falsa.
    assert dados["cnpj_plataforma"] == "11222333000181"
    assert dados["cnpj_confere"] == (dados["cnpj_erp"] == "11222333000181")
