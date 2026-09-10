# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_emissao_numeracao.py
# DESCRIÇÃO: Testes do cluster de duplicidade (Fase 2).
#
# Cobre as três regras que impedem nota duplicada na SEFAZ:
#   1. A reserva do número é atômica (Rejeição 204)
#   2. O número NUNCA volta para o contador depois do disparo
#   3. Falha de comunicação vira INDETERMINADA, nunca REJEITADA
# ---------------------------------------------------------------------------

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.crud import fiscal as crud
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.services.fiscal.emissao import _aplicar_resultado


@pytest.fixture
def db():
    """Banco em memória isolado, exclusivo deste módulo."""
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
def empresa_com_contador(db):
    """Empresa com o contador de NF-e em 42."""
    empresa = Empresa(
        id=1,
        razao_social="Loja Teste LTDA",
        documento="11222333000181",
        is_cnpj=True,
        regime_tributario="Simples Nacional",
    )
    db.add(empresa)
    db.flush()
    db.add(EmpresaFiscalSettings(
        empresa_id=empresa.id, serie_nfe=1, ultimo_numero_nfe=42, ambiente_emissao=2,
    ))
    db.commit()
    return empresa


# =========================
# 1. Reserva atômica de numeração
# =========================

def test_reserva_devolve_o_proximo_numero_e_grava_no_contador(db, empresa_com_contador):
    numero = crud.reservar_proximo_numero_nfe(db, empresa_com_contador.id)

    assert numero == 43
    assert crud.get_fiscal_settings(db, empresa_com_contador.id).ultimo_numero_nfe == 43


def test_reservas_seguidas_nunca_repetem_numero(db, empresa_com_contador):
    """
    O cenário da Rejeição 204: dois caixas emitindo em sequência.
    Com SELECT-depois-UPDATE ambos pegariam 43.
    """
    numeros = [crud.reservar_proximo_numero_nfe(db, empresa_com_contador.id) for _ in range(5)]

    assert numeros == [43, 44, 45, 46, 47]
    assert len(set(numeros)) == 5


def test_reserva_e_um_unico_update_sem_leitura_previa(db, empresa_com_contador):
    """
    A reserva não pode depender do valor lido antes: mesmo com a instância ORM
    carregada e desatualizada em memória, o contador avança corretamente.
    """
    fs = crud.get_fiscal_settings(db, empresa_com_contador.id)
    assert fs.ultimo_numero_nfe == 42  # instância em memória

    primeiro = crud.reservar_proximo_numero_nfe(db, empresa_com_contador.id)
    segundo = crud.reservar_proximo_numero_nfe(db, empresa_com_contador.id)

    assert (primeiro, segundo) == (43, 44)
    assert fs.ultimo_numero_nfe == 44  # expirada e relida


def test_reserva_em_empresa_sem_configuracao_fiscal_falha(db):
    with pytest.raises(ValueError, match="não encontradas"):
        crud.reservar_proximo_numero_nfe(db, 999)


# =========================
# 1b. Numeração da NFC-e (modelo 65)
# =========================

def test_contador_de_nfce_e_independente_do_de_nfe(db, empresa_com_contador):
    """
    Cada modelo tem sua sequência na SEFAZ. Compartilhar o contador abriria
    buraco nas duas e causaria Rejeição 204 numa delas.
    """
    empresa_id = empresa_com_contador.id

    nfce_1 = crud.reservar_proximo_numero_nfce(db, empresa_id)
    nfe_1 = crud.reservar_proximo_numero_nfe(db, empresa_id)
    nfce_2 = crud.reservar_proximo_numero_nfce(db, empresa_id)

    # A NFC-e começa do zero (contador não inicializado nesta fixture)...
    assert [nfce_1, nfce_2] == [1, 2]
    # ...enquanto a NF-e segue de onde estava, em 42.
    assert nfe_1 == 43

    fs = crud.get_fiscal_settings(db, empresa_id)
    assert fs.ultimo_numero_nfce == 2
    assert fs.ultimo_numero_nfe == 43


def test_reservas_de_nfce_seguidas_nunca_repetem(db, empresa_com_contador):
    """No PDV a corrida é real: vários caixas fechando venda ao mesmo tempo."""
    numeros = [
        crud.reservar_proximo_numero_nfce(db, empresa_com_contador.id)
        for _ in range(5)
    ]

    assert numeros == [1, 2, 3, 4, 5]
    assert len(set(numeros)) == 5


def test_reserva_de_nfce_sem_configuracao_fiscal_falha(db):
    with pytest.raises(ValueError, match="não encontradas"):
        crud.reservar_proximo_numero_nfce(db, 999)


# =========================
# 2. Estado indeterminado vs. rejeição
# =========================

def test_resposta_de_rejeicao_da_sefaz_marca_rejeitada():
    doc = DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", status="PROCESSANDO")

    _aplicar_resultado(doc, {"status": "erro", "mensagem_sefaz": "Rejeicao 999"})

    assert doc.status == "REJEITADA"


def test_resposta_de_autorizacao_preenche_protocolo_e_data():
    doc = DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", status="PROCESSANDO")

    _aplicar_resultado(doc, {
        "status": "autorizado",
        "chave_acesso": "3" * 44,
        "protocolo": "135240001234567",
    })

    assert doc.status == "AUTORIZADA"
    assert doc.data_autorizacao is not None
    assert doc.protocolo_autorizacao == "135240001234567"


def test_indeterminada_bloqueia_nova_emissao_da_mesma_venda(db, empresa_com_contador):
    """
    O ponto do achado C2: enquanto não soubermos se a nota foi autorizada,
    a venda não pode ser reemitida — senão vira nota duplicada.
    """
    db.add(DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=1001,
        status="INDETERMINADA", numero_documento=43, serie=1,
    ))
    db.commit()

    ativo = crud.get_documento_ativo_por_venda(db, 1001)

    assert ativo is not None
    assert ativo.status == "INDETERMINADA"


@pytest.mark.parametrize("status_doc", ["AUTORIZADA", "PROCESSANDO", "INDETERMINADA"])
def test_todos_os_estados_ativos_bloqueiam_reemissao(db, empresa_com_contador, status_doc):
    """Os três estados em que a nota PODE existir na SEFAZ."""
    db.add(DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=2002,
        status=status_doc, numero_documento=50, serie=1,
    ))
    db.commit()

    assert crud.get_documento_ativo_por_venda(db, 2002) is not None


@pytest.mark.parametrize("status_doc", ["PENDENTE", "NAO_TRANSMITIDA"])
def test_documento_nunca_transmitido_nao_tranca_a_venda(db, empresa_com_contador, status_doc):
    """PENDENTE saiu da lista de bloqueio, e isto documenta por quê.

    PENDENTE não significa "prestes a transmitir": a emissão cria o documento já
    como PROCESSANDO. Quem cria PENDENTE é a reemissão, que monta a linha e NÃO
    transmite. Enquanto isso bloqueava, cada clique em "reemitir" trancava a
    venda em "já possui uma emissão em andamento" — para sempre, por uma nota
    que nunca saiu do prédio.

    Bloquear aqui nunca protegeu nada: a proteção contra nota duplicada é
    INDETERMINADA, que continua na lista (teste acima).
    """
    db.add(DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=2003,
        status=status_doc, numero_documento=50, serie=1,
    ))
    db.commit()

    assert crud.get_documento_ativo_por_venda(db, 2003) is None


@pytest.mark.parametrize("status_doc", ["REJEITADA", "DENEGADA", "CANCELADA"])
def test_estados_encerrados_liberam_nova_emissao(db, empresa_com_contador, status_doc):
    db.add(DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=3003,
        status=status_doc, numero_documento=51, serie=1,
    ))
    db.commit()

    assert crud.get_documento_ativo_por_venda(db, 3003) is None


def test_indeterminada_tem_prioridade_sobre_rejeitada_na_listagem(db, empresa_com_contador):
    """
    Na tela de vendas, um documento indeterminado precisa aparecer por cima de
    uma tentativa rejeitada anterior — é ele que exige ação do operador.
    """
    db.add_all([
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=4004,
                        status="REJEITADA", numero_documento=60, serie=1),
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=4004,
                        status="INDETERMINADA", numero_documento=61, serie=1),
    ])
    db.commit()

    relevantes = crud.get_documentos_relevantes_por_vendas(db, [4004])

    assert relevantes[4004].status == "INDETERMINADA"


# =========================
# 3. Persistência da chave de idempotência
# =========================

def test_documento_fiscal_tem_coluna_de_idempotencia(db):
    colunas = {c["name"] for c in inspect(db.get_bind()).get_columns("documento_fiscal")}

    assert "idempotency_key" in colunas


def test_chave_de_idempotencia_e_unica(db, empresa_com_contador):
    from sqlalchemy.exc import IntegrityError

    chave = "11111111-2222-3333-4444-555555555555"
    db.add(DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=1,
                           status="PROCESSANDO", idempotency_key=chave))
    db.commit()

    db.add(DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=2,
                           status="PROCESSANDO", idempotency_key=chave))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_documentos_sem_chave_nao_colidem_entre_si(db, empresa_com_contador):
    """NULL não conflita com NULL: documentos antigos convivem sem chave."""
    db.add_all([
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=1,
                        status="REJEITADA", idempotency_key=None),
        DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", origem_id=2,
                        status="REJEITADA", idempotency_key=None),
    ])
    db.commit()

    assert db.query(DocumentoFiscal).count() == 2
