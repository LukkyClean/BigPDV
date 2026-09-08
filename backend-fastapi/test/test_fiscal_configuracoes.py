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
