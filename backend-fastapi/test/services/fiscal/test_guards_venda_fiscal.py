# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_guards_venda_fiscal.py
# DESCRIÇÃO: Testes do bloqueio de alteração em venda com nota fiscal viva
#            (achados A3, C10, C11) e da reconciliação de boot (A8).
#
# O risco coberto aqui é fraude fiscal por descuido: cancelar a venda no PDV
# — estornando caixa e estoque — enquanto a nota segue válida na SEFAZ.
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
from app.db.models.venda import Venda
from app.services.venda import (
    _STATUS_FISCAIS_BLOQUEANTES,
    _assert_sem_documento_fiscal_ativo,
    _documento_fiscal_bloqueante,
)

NUMERO_VENDA = 1001


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


def venda(numero=NUMERO_VENDA, venda_id=1):
    """Venda mínima — o guard só lê numero_venda e id."""
    return Venda(id=venda_id, numero_venda=numero, subtotal=10000, total=10000)


def documento(status_doc, origem_id=NUMERO_VENDA, numero=43):
    return DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=origem_id,
        numero_documento=numero, serie=1, status=status_doc,
    )


# =========================
# 1. Estados que bloqueiam
# =========================

@pytest.mark.parametrize("status_doc", list(_STATUS_FISCAIS_BLOQUEANTES))
def test_documento_vivo_bloqueia_alteracao(db, status_doc):
    db.add(documento(status_doc))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")

    assert exc.value.status_code == 409
    assert exc.value.detail["documento_id"] is not None


@pytest.mark.parametrize("status_doc", ["REJEITADA", "DENEGADA", "CANCELADA"])
def test_documento_encerrado_nao_bloqueia(db, status_doc):
    db.add(documento(status_doc))
    db.commit()

    _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")  # não levanta


def test_venda_sem_documento_nao_bloqueia(db):
    _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")


def test_venda_nao_finalizada_nao_tem_como_ter_documento(db):
    """Venda ainda ATIVA não tem numero_venda; o guard não pode explodir."""
    rascunho = Venda(id=None, numero_venda=None, subtotal=0, total=0)

    assert _documento_fiscal_bloqueante(db, rascunho) is None


def test_documento_de_outra_venda_nao_bloqueia(db):
    db.add(documento("AUTORIZADA", origem_id=9999))
    db.commit()

    _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")


# =========================
# 2. Mensagem por estado
# =========================

def test_autorizada_orienta_cancelar_na_sefaz(db):
    db.add(documento("AUTORIZADA", numero=43))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")

    detalhe = exc.value.detail
    assert detalhe["codigo"] == "NF_AUTORIZADA"
    assert "43" in detalhe["mensagem"]
    assert "SEFAZ" in detalhe["mensagem"]


def test_indeterminada_orienta_consultar_antes(db):
    db.add(documento("INDETERMINADA"))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        _assert_sem_documento_fiscal_ativo(db, venda(), "reabrir a venda")

    detalhe = exc.value.detail
    assert detalhe["codigo"] == "NF_INDETERMINADA"
    assert "consulte" in detalhe["mensagem"].lower()


def test_processando_orienta_aguardar(db):
    db.add(documento("PROCESSANDO"))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        _assert_sem_documento_fiscal_ativo(db, venda(), "editar itens")

    assert exc.value.detail["codigo"] == "NF_EM_PROCESSAMENTO"


def test_mensagem_cita_a_acao_bloqueada(db):
    db.add(documento("AUTORIZADA"))
    db.commit()

    for acao in ("cancelar a venda", "remover itens", "alterar os dados fiscais"):
        with pytest.raises(HTTPException) as exc:
            _assert_sem_documento_fiscal_ativo(db, venda(), acao)
        assert acao in exc.value.detail["mensagem"]


# =========================
# 3. Cobertura dos pontos de mutação
# =========================

def test_todos_os_mutadores_de_venda_chamam_o_guard():
    """
    Trava de regressão: qualquer função que altere venda finalizada precisa
    passar pelo guard. Esquecer uma reabre o buraco do achado A3.
    """
    import inspect
    from app.services import venda as mod

    fontes = {
        nome: inspect.getsource(getattr(mod, nome))
        for nome in (
            "update_sale", "add_item_to_sale", "update_item_in_sale",
            "remove_item_from_sale", "delete_draft_sale", "cancel_sale",
            "reopen_sale", "corrigir_dados_venda_fiscal",
        )
    }

    sem_guard = [
        nome for nome, src in fontes.items()
        if "_assert_sem_documento_fiscal_ativo" not in src
    ]

    assert sem_guard == [], f"Sem guard fiscal: {sem_guard}"


# =========================
# 4. Reconciliação de boot (A8)
# =========================

def test_lista_apenas_documentos_sem_resposta_definitiva(db):
    from app.services.fiscal.reconciliacao import listar_documentos_pendentes

    db.add_all([
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=1,
                        status="PROCESSANDO", ref_api="venda-1"),
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=2,
                        status="INDETERMINADA", ref_api="venda-2"),
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=3,
                        status="AUTORIZADA", ref_api="venda-3"),
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=4,
                        status="REJEITADA", ref_api="venda-4"),
    ])
    db.commit()

    pendentes = listar_documentos_pendentes(db)

    assert {d.origem_id for d in pendentes} == {1, 2}


def test_documento_sem_ref_api_nao_entra_na_fila(db):
    """Sem referência não há o que consultar."""
    from app.services.fiscal.reconciliacao import listar_documentos_pendentes

    db.add(DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=1,
                           status="PROCESSANDO", ref_api=None))
    db.commit()

    assert listar_documentos_pendentes(db) == []


def test_reconciliacao_sem_pendencias_nao_faz_nada(db):
    from app.services.fiscal.reconciliacao import reconciliar_pendentes

    assert reconciliar_pendentes(db) == {
        "verificados": 0, "resolvidos": 0, "ainda_pendentes": 0,
    }


def _semear_pendente(db, status_final, monkeypatch):
    """Documento INDETERMINADA que a consulta resolve para `status_final`."""
    from app.services.fiscal import reconciliacao as mod

    db.add(Empresa(id=1, razao_social="Loja LTDA", documento="11222333000181", is_cnpj=True))
    db.flush()
    db.add(EmpresaFiscalSettings(empresa_id=1, serie_nfe=1, ultimo_numero_nfe=43, ambiente_emissao=2))
    db.add(DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=NUMERO_VENDA,
                           status="INDETERMINADA", ref_api="venda-1001",
                           numero_documento=43, serie=1))
    db.commit()

    def consulta_fake(db_, documento_id, empresa_id):
        doc = db_.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
        doc.status = status_final
        return doc

    monkeypatch.setattr("app.services.fiscal.emissao.consultar_documento", consulta_fake)
    return mod


def test_reconciliar_para_autorizada_mantem_a_venda_bloqueada(db, monkeypatch):
    """
    Descobrir que a nota FOI autorizada não libera a venda — ela é válida na
    SEFAZ. O ganho é o operador passar a ver o motivo certo do bloqueio.
    """
    mod = _semear_pendente(db, "AUTORIZADA", monkeypatch)

    resumo = mod.reconciliar_pendentes(db)

    assert resumo == {"verificados": 1, "resolvidos": 1, "ainda_pendentes": 0}

    with pytest.raises(HTTPException) as exc:
        _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")
    assert exc.value.detail["codigo"] == "NF_AUTORIZADA"


def test_reconciliar_para_rejeitada_destrava_a_venda(db, monkeypatch):
    """Aqui sim: a SEFAZ nunca autorizou, então a venda volta a ser editável."""
    mod = _semear_pendente(db, "REJEITADA", monkeypatch)

    resumo = mod.reconciliar_pendentes(db)

    assert resumo == {"verificados": 1, "resolvidos": 1, "ainda_pendentes": 0}
    _assert_sem_documento_fiscal_ativo(db, venda(), "cancelar a venda")  # não levanta


def test_falha_na_consulta_nao_derruba_a_reconciliacao(db, monkeypatch):
    from app.services.fiscal import reconciliacao as mod

    db.add(Empresa(id=1, razao_social="Loja LTDA", documento="11222333000181", is_cnpj=True))
    db.flush()
    db.add(EmpresaFiscalSettings(empresa_id=1, serie_nfe=1, ultimo_numero_nfe=43, ambiente_emissao=2))
    db.add(DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=NUMERO_VENDA,
                           status="INDETERMINADA", ref_api="venda-1001"))
    db.commit()

    def consulta_que_falha(db_, documento_id, empresa_id):
        raise ConnectionError("SEFAZ fora do ar")

    monkeypatch.setattr("app.services.fiscal.emissao.consultar_documento", consulta_que_falha)

    resumo = mod.reconciliar_pendentes(db)

    assert resumo == {"verificados": 1, "resolvidos": 0, "ainda_pendentes": 1}
