# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_emitente_cnpj_e_mei.py
# DESCRIÇÃO: As duas regras da fase 1 do plano fiscal.
#
#   1. Emitente cadastrado com CPF não emite NF-e.
#   2. MEI chega a CRT 4 pelo seletor de regime.
#
# Ambas nasceram do mesmo episódio: a loja recebeu "CNPJ do emitente não
# autorizado" e o rastro não apontava para o cadastro. Ver
# docs/fiscal-onboarding-plano.md.
# ---------------------------------------------------------------------------

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.empresa import Empresa
from app.services.fiscal.helpers import CRT_MEI, CRT_SIMPLES_NACIONAL, crt_efetivo
from app.services.fiscal.payload_builder import _so_digitos
from app.services.fiscal.validators import verificar_emitente


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()


def _empresa(db, **kwargs) -> Empresa:
    dados = dict(
        razao_social="LOJA TESTE",
        # CNPJ com dígito verificador válido — `verificar_emitente` confere.
        documento="11222333000181",
        is_cnpj=True,
        regime_tributario="Simples Nacional",
        indicador_ie="9",
    )
    dados.update(kwargs)
    empresa = Empresa(**dados)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


def _campos_com_pendencia(db, empresa_id: int) -> set[str]:
    return {p.campo for p in verificar_emitente(db, empresa_id)}


# ---------------------------------------------------------------------------
# 1. Emitente com CPF
# ---------------------------------------------------------------------------

def test_emitente_com_cpf_nao_emite(db):
    """CPF no lugar do CNPJ tem que parar AQUI, com o cadastro à mão.

    Antes não havia trava: o payload manda `empresa.documento` no campo `cnpj`,
    então um CPF de 11 dígitos saía como se fosse CNPJ e a recusa vinha da
    plataforma ou da SEFAZ — longe, e sem apontar para o cadastro.
    """
    empresa = _empresa(db, documento="06466556395", is_cnpj=False)

    pendencias = verificar_emitente(db, empresa.id)
    documento = [p for p in pendencias if p.campo == "documento"]

    assert documento, "empresa com CPF passou no gate do emitente"
    assert "CPF" in documento[0].mensagem
    assert "Dados da Empresa" in documento[0].mensagem, (
        "a mensagem precisa dizer ONDE corrigir — foi a falta disso que "
        "transformou um campo errado numa investigação"
    )


def test_emitente_com_cnpj_valido_nao_gera_pendencia_de_documento(db):
    empresa = _empresa(db)
    assert "documento" not in _campos_com_pendencia(db, empresa.id)


def test_emitente_sem_documento_continua_reprovando(db):
    empresa = _empresa(db, documento=None, is_cnpj=True)
    assert "documento" in _campos_com_pendencia(db, empresa.id)


# ---------------------------------------------------------------------------
# 2. MEI e o CRT 4
# ---------------------------------------------------------------------------

def test_mei_chega_a_crt_4_pelo_regime():
    """O rótulo do seletor precisa levar a CRT 4.

    `crt_efetivo` dá prioridade ao regime sobre a natureza jurídica. Como o
    seletor não oferecia MEI, um microempreendedor só podia escolher "Simples
    Nacional" e saía com CRT 1 mesmo com a natureza jurídica marcada como MEI —
    nota aceita e errada, que é o pior desfecho.
    """
    assert crt_efetivo("MEI", None) == CRT_MEI


def test_regime_preenchido_ainda_manda_sobre_a_natureza_juridica():
    """A precedência não mudou — só passou a existir como escolher MEI."""
    assert crt_efetivo("Simples Nacional", "MEI") == CRT_SIMPLES_NACIONAL


def test_natureza_juridica_mei_continua_resolvendo_sem_regime():
    assert crt_efetivo(None, "MEI") == CRT_MEI


# ---------------------------------------------------------------------------
# 3. Normalização na saída
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("11.222.333/0001-81", "11222333000181"),
        ("064.665.563-95", "06466556395"),
        ("63502-105", "63502105"),
        ("11222333000181", "11222333000181"),
        ("", None),
        (None, None),
    ],
)
def test_so_digitos(entrada, esperado):
    """Documento e CEP viajam sem pontuação — máscara é recusa lá na frente."""
    assert _so_digitos(entrada) == esperado
