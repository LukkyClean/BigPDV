# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_certificado_vencimento.py
# DESCRIÇÃO: O certificado A1 vence e a SEFAZ não avisa antes -- a primeira
# notícia é uma rejeição. Estes testes fixam a regra em três lugares que
# precisam concordar: o helper que conta os dias, o gate (só VENCIDO barra)
# e o painel (avisa com 30 dias).
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone

import pytest

from app.services.fiscal.helpers import (
    DIAS_AVISO_CERTIFICADO,
    aviso_certificado,
    dias_para_vencer_certificado,
)


def _daqui(dias: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=dias)


# --- helper ---

def test_sem_validade_nao_conta():
    assert dias_para_vencer_certificado(None) is None
    assert aviso_certificado(None) is None


@pytest.mark.parametrize("dias", [0, 1, 15, 30, 31, 365])
def test_conta_dias_inteiros(dias):
    assert dias_para_vencer_certificado(_daqui(dias)) == dias


def test_vencido_e_negativo():
    assert dias_para_vencer_certificado(_daqui(-3)) == -3


def test_validade_sem_fuso_e_tratada_como_utc():
    """O banco grava naive; o helper não pode explodir nem errar por 3 horas."""
    naive = (_daqui(10)).replace(tzinfo=None)
    assert dias_para_vencer_certificado(naive) == 10


# --- aviso do painel ---

def test_longe_do_fim_nao_avisa():
    assert aviso_certificado(_daqui(DIAS_AVISO_CERTIFICADO + 1)) is None


def test_no_limiar_avisa_com_os_dias():
    aviso = aviso_certificado(_daqui(DIAS_AVISO_CERTIFICADO))
    assert aviso is not None
    assert "30 dias" in aviso


def test_um_dia_no_singular():
    assert "1 dia (" in aviso_certificado(_daqui(1))


def test_hoje_e_vencido_tem_frases_proprias():
    assert "HOJE" in aviso_certificado(_daqui(0))
    assert "vencido" in aviso_certificado(_daqui(-1))


# --- gate ---

@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.base import Base

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    sessao = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield sessao
    sessao.close()


def _empresa_completa(db, validade):
    from app.db.models.empresa import Empresa
    from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
    from app.core.enum import EntityType, State
    from app.db.models.endereco import Endereco

    empresa = Empresa(
        id=1, razao_social="Loja", documento="11222333000181", is_cnpj=True,
        regime_tributario="Simples Nacional", indicador_ie="1", inscricao_estadual="123",
    )
    db.add(empresa)
    db.flush()
    db.add(Endereco(
        id_entidade=1, tipo_entidade=EntityType.EMPRESA,
        logradouro="Rua", numero="1", bairro="Centro",
        cidade="Cidade", estado=State("SP"), cep="01310100",
    ))
    db.add(EmpresaFiscalSettings(
        empresa_id=1, serie_nfe=1, ambiente_emissao=2, certificado_validade=validade,
    ))
    db.commit()
    return empresa


def _campos(pendencias):
    return {p.campo for p in pendencias}


def test_gate_nao_barra_certificado_prestes_a_vencer(db):
    from app.services.fiscal.validators import verificar_emitente

    _empresa_completa(db, _daqui(5))
    assert "certificado" not in _campos(verificar_emitente(db, 1))


def test_gate_barra_certificado_vencido_e_diz_a_data(db):
    from app.services.fiscal.validators import verificar_emitente

    _empresa_completa(db, _daqui(-1))
    pendencias = verificar_emitente(db, 1)
    assert "certificado" in _campos(pendencias)
    msg = next(p.mensagem for p in pendencias if p.campo == "certificado")
    assert "vencido" in msg and "Centro Fiscal" in msg


def test_gate_sem_validade_conhecida_nao_barra(db):
    """O certificado vive na plataforma; sem validade aqui, não há o que barrar."""
    from app.services.fiscal.validators import verificar_emitente

    _empresa_completa(db, None)
    assert "certificado" not in _campos(verificar_emitente(db, 1))
