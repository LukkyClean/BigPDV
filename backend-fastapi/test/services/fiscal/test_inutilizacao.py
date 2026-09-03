# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_inutilizacao.py
# DESCRIÇÃO: Testes da detecção de buracos na numeração e da inutilização.
#
# Contexto: desde que o contador parou de ser revertido em caso de falha
# (achado C3), buraco na sequência é resultado esperado. A regra que importa
# é nunca inutilizar um número que pode estar em uso na SEFAZ.
# ---------------------------------------------------------------------------

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.inutilizacao_fiscal import InutilizacaoFiscal
from app.services.fiscal.inutilizacao import (
    _agrupar_em_faixas,
    listar_gaps_numeracao,
    solicitar_inutilizacao,
)

EMPRESA_ID = 1


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sessao = Session()
    yield sessao
    sessao.close()


@pytest.fixture
def empresa(db):
    db.add(Empresa(
        id=EMPRESA_ID, razao_social="Loja Teste LTDA",
        documento="11222333000181", is_cnpj=True,
        regime_tributario="Simples Nacional",
    ))
    db.flush()
    db.add(EmpresaFiscalSettings(
        empresa_id=EMPRESA_ID, serie_nfe=1, ultimo_numero_nfe=10, ambiente_emissao=2,
    ))
    db.commit()


def doc(numero, status_doc, serie=1):
    return DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=numero,
        numero_documento=numero, serie=serie, status=status_doc,
    )


# =========================
# 1. Agrupamento em faixas
# =========================

@pytest.mark.parametrize("numeros, esperado", [
    ([], []),
    ([5], [(5, 5)]),
    ([3, 4, 5], [(3, 5)]),
    ([3, 4, 5, 9, 11, 12], [(3, 5), (9, 9), (11, 12)]),
    ([12, 3, 4, 11, 5, 9], [(3, 5), (9, 9), (11, 12)]),   # fora de ordem
    ([7, 7, 8], [(7, 8)]),                                 # duplicados
])
def test_agrupa_numeros_consecutivos_em_faixas(numeros, esperado):
    assert _agrupar_em_faixas(numeros) == esperado


# =========================
# 2. Detecção de buracos
# =========================

def test_sem_documentos_toda_a_sequencia_e_buraco(db, empresa):
    gaps = listar_gaps_numeracao(db, EMPRESA_ID)

    assert gaps == [{"serie": 1, "numero_inicial": 1, "numero_final": 10, "quantidade": 10}]


def test_numeros_autorizados_nao_sao_buraco(db, empresa):
    db.add_all([doc(n, "AUTORIZADA") for n in range(1, 11)])
    db.commit()

    assert listar_gaps_numeracao(db, EMPRESA_ID) == []


def test_numero_rejeitado_vira_buraco(db, empresa):
    """O caso que a Fase 2 criou: número queimado por falha de transmissão."""
    db.add_all([doc(n, "AUTORIZADA") for n in (1, 2, 4, 5, 6, 7, 8, 9, 10)])
    db.add(doc(3, "REJEITADA"))
    db.commit()

    gaps = listar_gaps_numeracao(db, EMPRESA_ID)

    assert gaps == [{"serie": 1, "numero_inicial": 3, "numero_final": 3, "quantidade": 1}]


@pytest.mark.parametrize("status_vivo", [
    "AUTORIZADA", "CANCELADA", "PROCESSANDO", "PENDENTE", "INDETERMINADA",
])
def test_estados_que_podem_ter_consumido_o_numero_nao_viram_buraco(db, empresa, status_vivo):
    """
    INDETERMINADA entra aqui de propósito: inutilizar um número cuja nota pode
    estar autorizada seria declarar à SEFAZ uma inverdade.
    """
    db.add_all([doc(n, "AUTORIZADA") for n in range(1, 11) if n != 5])
    db.add(doc(5, status_vivo))
    db.commit()

    assert listar_gaps_numeracao(db, EMPRESA_ID) == []


def test_buracos_separados_viram_faixas_separadas(db, empresa):
    db.add_all([doc(n, "AUTORIZADA") for n in (1, 5, 6, 10)])
    db.commit()

    gaps = listar_gaps_numeracao(db, EMPRESA_ID)

    assert [(g["numero_inicial"], g["numero_final"]) for g in gaps] == [(2, 4), (7, 9)]


def test_faixa_ja_inutilizada_sai_da_lista(db, empresa):
    db.add_all([doc(n, "AUTORIZADA") for n in range(1, 11) if n != 4])
    db.add(InutilizacaoFiscal(
        empresa_id=EMPRESA_ID, serie=1, ano=2026,
        numero_inicial=4, numero_final=4,
        justificativa="Numero queimado por falha de transmissao",
        status="HOMOLOGADA",
    ))
    db.commit()

    assert listar_gaps_numeracao(db, EMPRESA_ID) == []


def test_contador_zerado_nao_tem_buraco(db):
    db.add(Empresa(id=2, razao_social="Nova LTDA", documento="11222333000181", is_cnpj=True))
    db.flush()
    db.add(EmpresaFiscalSettings(empresa_id=2, serie_nfe=1, ultimo_numero_nfe=0))
    db.commit()

    assert listar_gaps_numeracao(db, 2) == []


# =========================
# 3. Guardas do pedido
# =========================

def test_justificativa_curta_e_recusada(db, empresa):
    with pytest.raises(HTTPException) as exc:
        solicitar_inutilizacao(db, EMPRESA_ID, 1, 3, 3, "curta")

    assert exc.value.status_code == 422
    assert "15 caracteres" in str(exc.value.detail)


def test_faixa_invertida_e_recusada(db, empresa):
    with pytest.raises(HTTPException) as exc:
        solicitar_inutilizacao(db, EMPRESA_ID, 1, 9, 3, "Faixa invertida para teste")

    assert exc.value.status_code == 422


def test_nao_inutiliza_numero_acima_do_contador(db, empresa):
    """Só número já reservado pode ser inutilizado."""
    with pytest.raises(HTTPException) as exc:
        solicitar_inutilizacao(db, EMPRESA_ID, 1, 50, 60, "Numeros nunca reservados")

    assert exc.value.status_code == 422
    assert "contador" in str(exc.value.detail)


@pytest.mark.parametrize("status_vivo", ["AUTORIZADA", "PROCESSANDO", "INDETERMINADA"])
def test_nao_inutiliza_faixa_com_numero_em_uso(db, empresa, status_vivo):
    """A trava central: inutilizar nota viva é declaração falsa à SEFAZ."""
    db.add(doc(5, status_vivo))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        solicitar_inutilizacao(db, EMPRESA_ID, 1, 3, 7, "Tentativa sobre numero em uso")

    assert exc.value.status_code == 409
    assert exc.value.detail["codigo"] == "NUMERO_EM_USO"


def test_faixa_apenas_com_rejeitadas_e_aceita(db, empresa, monkeypatch):
    from app.services.fiscal import inutilizacao as mod

    class ClientFake:
        def inutilizar_numeracao(self, ref, payload, idempotency_key=None):
            return {
                "status": "homologado",
                "protocolo": "135240009999999",
                "codigo_sefaz": 102,
                "mensagem_sefaz": "Inutilizacao homologada",
                "url_xml": None,
            }

    monkeypatch.setattr(
        "app.services.fiscal.http.get_fiscal_client", lambda *a, **k: ClientFake()
    )

    db.add_all([doc(n, "REJEITADA") for n in (3, 4, 5)])
    db.commit()

    registro = solicitar_inutilizacao(
        db, EMPRESA_ID, 1, 3, 5, "Numeros queimados por falha de rede",
    )

    assert registro.status == "HOMOLOGADA"
    assert registro.protocolo == "135240009999999"
    assert registro.idempotency_key is not None
    assert registro.data_homologacao is not None


def test_falha_de_comunicacao_deixa_indeterminada(db, empresa, monkeypatch):
    """
    Mesma regra da emissão: sem resposta não é recusa. Precisa ficar
    INDETERMINADA para a faixa não voltar à lista e ser pedida duas vezes.
    """
    class ClientQueFalha:
        def inutilizar_numeracao(self, ref, payload, idempotency_key=None):
            raise ConnectionError("timeout")

    monkeypatch.setattr(
        "app.services.fiscal.http.get_fiscal_client", lambda *a, **k: ClientQueFalha()
    )

    db.add_all([doc(n, "REJEITADA") for n in (3, 4)])
    db.commit()

    registro = solicitar_inutilizacao(
        db, EMPRESA_ID, 1, 3, 4, "Numeros queimados por falha de rede",
    )

    assert registro.status == "INDETERMINADA"
    assert "não foi possível confirmar" in registro.mensagem_sefaz.lower()


def test_faixa_indeterminada_nao_reaparece_como_gap(db, empresa, monkeypatch):
    class ClientQueFalha:
        def inutilizar_numeracao(self, ref, payload, idempotency_key=None):
            raise ConnectionError("timeout")

    monkeypatch.setattr(
        "app.services.fiscal.http.get_fiscal_client", lambda *a, **k: ClientQueFalha()
    )

    db.add_all([doc(n, "AUTORIZADA") for n in range(1, 11) if n not in (3, 4)])
    db.commit()

    solicitar_inutilizacao(db, EMPRESA_ID, 1, 3, 4, "Numeros queimados por falha de rede")
    db.commit()

    assert listar_gaps_numeracao(db, EMPRESA_ID) == []
