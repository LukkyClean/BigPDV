# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_gate_e_payload.py
# DESCRIÇÃO: Testes da Fase 5 — gate e payload.
#
# Achados cobertos:
#   A6  CEST obrigatório sob ICMS-ST
#   A7  GTIN GS1 e sanitização de NCM
#   C5  trava interestadual por operação, não por endereço do cliente
#   C6  enderDest omitido quando incompleto
#   C8  modelo, idDest e modFrete no payload
#   C13 gate recusa CST/CSOSN fora da cobertura do motor
# ---------------------------------------------------------------------------

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enum import State
from app.db.base import Base
from app.db.models.aliquota_uf import AliquotaUF
from app.db.models.cliente import ClientePF
from app.db.models.endereco import Endereco
from app.db.models.produto import Produto
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.venda import Venda
from app.db.models.venda_nota_fiscal import VendaNotaFiscal
from app.db.models.venda_produto import ProdutoVenda
from app.services.fiscal.payload_builder import (
    SEM_GTIN,
    _codigo_barras_para_sefaz,
    _gtin_valido,
    _montar_destinatario,
    _sanitizar_ncm,
)
from app.services.fiscal.tax_engine.exceptions import OperacaoInterestadualError
from app.services.fiscal.tax_engine.resolver import resolver_aliquotas_venda
from app.services.fiscal.validators import _exige_cest, verificar_produto_fiscal


# =========================
# 1. GTIN (achado A7)
# =========================

@pytest.mark.parametrize("codigo", [
    "7891234567895",    # EAN-13
    "78912342",         # EAN-8
    "012345678905",     # UPC-A (12)
    "17891234567892",   # GTIN-14
])
def test_gtin_valido_e_aceito(codigo):
    assert _gtin_valido(codigo) is True
    assert _codigo_barras_para_sefaz(codigo) == codigo


@pytest.mark.parametrize("codigo, motivo", [
    ("7891234567890", "dígito verificador errado"),
    ("12345", "5 dígitos — código interno de loja"),
    ("123456789012345", "15 dígitos"),
    ("789123456789A", "contém letra"),
    ("", "vazio"),
    (None, "ausente"),
    ("   ", "só espaços"),
])
def test_codigo_que_nao_e_gtin_vira_sem_gtin(codigo, motivo):
    assert _gtin_valido(codigo) is False, motivo
    assert _codigo_barras_para_sefaz(codigo) == SEM_GTIN


def test_gtin_com_espacos_nas_bordas_e_aceito():
    assert _codigo_barras_para_sefaz("  7891234567895  ") == "7891234567895"


# =========================
# 2. NCM (achado A7)
# =========================

@pytest.mark.parametrize("entrada, esperado", [
    ("84713012", "84713012"),
    ("8471.30.12", "84713012"),
    ("8471 30 12", "84713012"),
    ("8471-30-12", "84713012"),
    (None, None),
    ("", None),
    ("....", None),
])
def test_ncm_e_sanitizado(entrada, esperado):
    assert _sanitizar_ncm(entrada) == esperado


# =========================
# 3. CEST obrigatório em ST (achado A6)
# =========================

class _Fiscal:
    def __init__(self, cst_icms=None, csosn=None, cest=None):
        self.cst_icms, self.csosn, self.cest = cst_icms, csosn, cest


@pytest.mark.parametrize("cst", ["10", "30", "60", "70", "90"])
def test_cst_de_st_exige_cest(cst):
    assert _exige_cest(_Fiscal(cst_icms=cst), simples_nacional=False) is True


@pytest.mark.parametrize("csosn", ["201", "202", "203", "500", "900"])
def test_csosn_de_st_exige_cest(csosn):
    assert _exige_cest(_Fiscal(csosn=csosn), simples_nacional=True) is True


@pytest.mark.parametrize("cst", ["00", "20", "40", "41"])
def test_cst_sem_st_nao_exige_cest(cst):
    assert _exige_cest(_Fiscal(cst_icms=cst), simples_nacional=False) is False


@pytest.mark.parametrize("csosn", ["101", "102", "103", "300", "400"])
def test_csosn_sem_st_nao_exige_cest(csosn):
    assert _exige_cest(_Fiscal(csosn=csosn), simples_nacional=True) is False


def test_sem_codigo_nao_exige_cest():
    assert _exige_cest(_Fiscal(), simples_nacional=False) is False


# =========================
# 4. Gate: cobertura e CEST (achados A6 e C13)
# =========================

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
    sessao.add(AliquotaUF(uf="SP", aliquota_icms_interna=1800,
                          aliquota_pis_padrao=165, aliquota_cofins_padrao=760))
    sessao.commit()
    yield sessao
    sessao.close()


def _produto_com_fiscal(db, **campos_fiscais):
    produto = Produto(id=1, nome="Teclado", codigo_produto="P1", unidade_medida="UN")
    db.add(produto)
    db.flush()
    base = dict(
        produto_id=1, ncm="84716052", cfop_padrao="5102", origem_mercadoria=0,
        unidade_tributavel="UN", cst_pis="01", cst_cofins="01",
    )
    base.update(campos_fiscais)
    db.add(ProdutoFiscal(**base))
    db.commit()
    return produto


def _campos(pendencias):
    return {p.campo for p in pendencias}


def test_produto_em_st_sem_cest_gera_pendencia(db):
    produto = _produto_com_fiscal(db, csosn="500", cest=None)
    pendencias = []

    verificar_produto_fiscal(db, produto, pendencias, simples_nacional=True)

    assert "cest" in _campos(pendencias)
    assert any("obrigatório" in p.mensagem for p in pendencias if p.campo == "cest")


def test_produto_em_st_com_cest_passa(db):
    produto = _produto_com_fiscal(db, csosn="500", cest="2100100")
    pendencias = []

    verificar_produto_fiscal(db, produto, pendencias, simples_nacional=True)

    assert "cest" not in _campos(pendencias)


def test_produto_sem_st_nao_exige_cest_no_gate(db):
    produto = _produto_com_fiscal(db, csosn="102", cest=None)
    pendencias = []

    verificar_produto_fiscal(db, produto, pendencias, simples_nacional=True)

    assert "cest" not in _campos(pendencias)


def test_csosn_fora_da_cobertura_e_barrado_no_cadastro(db):
    """
    Achado C13: antes o gate aprovava e o usuário recebia um 422 genérico ao
    clicar em Emitir. Agora a pendência aparece com o nome do produto.
    """
    produto = _produto_com_fiscal(db, csosn="900")
    pendencias = []

    verificar_produto_fiscal(db, produto, pendencias, simples_nacional=True)

    assert "csosn" in _campos(pendencias)
    mensagem = next(p.mensagem for p in pendencias if p.campo == "csosn")
    assert "900" in mensagem and "101" in mensagem  # cita o inválido e os aceitos


def test_cst_fora_da_cobertura_e_barrado_no_cadastro(db):
    produto = _produto_com_fiscal(db, cst_icms="70", cest="2100100")
    pendencias = []

    verificar_produto_fiscal(db, produto, pendencias, simples_nacional=False)

    assert "cst_icms" in _campos(pendencias)


def test_csosn_suportado_passa_no_gate(db):
    produto = _produto_com_fiscal(db, csosn="102")
    pendencias = []

    verificar_produto_fiscal(db, produto, pendencias, simples_nacional=True)

    assert _campos(pendencias) == set()


# =========================
# 5. Endereço do destinatário (achado C6)
# =========================

def _cliente_com_endereco(**campos):
    base = dict(
        logradouro="Rua das Flores", numero="100", bairro="Centro",
        cidade="Sao Paulo", estado=State.SAO_PAULO, cep="01001000",
    )
    base.update(campos)
    cliente = ClientePF(id=1, nome="Maria Souza", cpf="52998224725")
    cliente.endereco = [Endereco(**base)]
    return cliente


def test_endereco_completo_vai_no_payload():
    dest = _montar_destinatario(_cliente_com_endereco())

    assert dest["endereco"]["cep"] == "01001000"
    assert dest["endereco"]["uf"] == "SP"


@pytest.mark.parametrize("campo_vazio", ["logradouro", "numero", "bairro", "cidade", "cep"])
def test_endereco_incompleto_e_omitido_por_inteiro(campo_vazio):
    """
    Enviar o grupo com campo vazio é rejeição. Omitir é aceito para NF-e a
    consumidor final — melhor omitir do que mandar quebrado.
    """
    dest = _montar_destinatario(_cliente_com_endereco(**{campo_vazio: None}))

    assert "endereco" not in dest
    assert dest["cpf"] == "52998224725"   # o resto do destinatário continua


def test_cliente_sem_endereco_nao_quebra():
    cliente = ClientePF(id=1, nome="Maria Souza", cpf="52998224725")
    cliente.endereco = []

    dest = _montar_destinatario(cliente)

    assert "endereco" not in dest


# =========================
# 6. Trava interestadual por operação (achado C5)
# =========================

def _venda(uf_cliente=State.SAO_PAULO, indicador_presenca=None):
    produto = Produto(id=1, nome="Teclado", codigo_produto="P1", unidade_medida="UN")
    produto.fiscal = ProdutoFiscal(
        produto_id=1, ncm="84716052", cfop_padrao="5102", origem_mercadoria=0,
        cst_icms="00", csosn="102", aliquota_icms=1800,
    )
    item = ProdutoVenda(id=1, produto_id=1, quantidade=1,
                        valor_unitario=10000, subtotal=10000, desconto=0)
    item.produto = produto

    cliente = ClientePF(id=1, nome="Maria", cpf="52998224725")
    cliente.endereco = [Endereco(
        logradouro="Rua X", numero="1", bairro="Centro",
        cidade="Cidade", estado=uf_cliente, cep="01001000",
    )]

    venda = Venda(id=1, numero_venda=1001, subtotal=10000, total=10000,
                  entrega=0, acrescimo=0)
    venda.itens = [item]
    venda.cliente = cliente
    venda.nota_fiscal = (
        VendaNotaFiscal(venda_id=1, indicador_presenca=indicador_presenca)
        if indicador_presenca is not None else None
    )
    return venda


def test_venda_de_balcao_para_cliente_de_outra_uf_e_permitida(db):
    """
    Achado C5: a mercadoria sai pelo balcão e não cruza fronteira. Travar por
    endereço cadastrado impedia faturar para turista sem irregularidade alguma.
    """
    venda = _venda(uf_cliente=State.MINAS_GERAIS, indicador_presenca=1)

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert len(itens) == 1


def test_venda_sem_dados_fiscais_assume_presencial(db):
    """O PDV é o uso dominante; sem indicação, é balcão."""
    venda = _venda(uf_cliente=State.MINAS_GERAIS, indicador_presenca=None)

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert len(itens) == 1


@pytest.mark.parametrize("indpres", [2, 3, 4, 9])
def test_operacao_nao_presencial_interestadual_continua_travada(db, indpres):
    """Aí a mercadoria circula de fato e DIFAL/FCP seriam devidos."""
    venda = _venda(uf_cliente=State.MINAS_GERAIS, indicador_presenca=indpres)

    with pytest.raises(OperacaoInterestadualError) as exc:
        resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert exc.value.campo == "uf_destinatario"


def test_operacao_nao_presencial_na_mesma_uf_e_permitida(db):
    venda = _venda(uf_cliente=State.SAO_PAULO, indicador_presenca=2)

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert len(itens) == 1


# =========================
# 7. Payload: modelo, idDest e modFrete (achado C8)
# =========================

def test_payload_declara_modelo_local_e_frete():
    from test.services.fiscal.test_payload_builder import (
        _item_venda, _montar, _pagamento, _produto, _venda,
    )

    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    payload = _montar(_venda(itens, [_pagamento(10000)]))

    assert payload["modelo"] == 55          # NF-e
    assert payload["local_destino"] == 1    # operação interna
    assert payload["modalidade_frete"] == 9  # sem transporte


def test_modalidade_frete_muda_quando_ha_entrega():
    from test.services.fiscal.test_payload_builder import (
        _item_venda, _montar, _pagamento, _produto, _venda,
    )

    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(11500)], entrega=1500)

    assert _montar(venda)["modalidade_frete"] == 0  # por conta do emitente


# =========================
# 8. Janela de cancelamento (achado B6)
# =========================

def test_cancelamento_dentro_de_24h_e_permitido():
    from datetime import datetime, timedelta, timezone
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _assert_dentro_da_janela_de_cancelamento

    doc = DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", status="AUTORIZADA",
        data_autorizacao=datetime.now(timezone.utc) - timedelta(hours=23),
    )

    _assert_dentro_da_janela_de_cancelamento(doc)  # não levanta


def test_cancelamento_apos_24h_e_recusado_com_orientacao():
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _assert_dentro_da_janela_de_cancelamento

    doc = DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", status="AUTORIZADA",
        data_autorizacao=datetime.now(timezone.utc) - timedelta(hours=30),
    )

    with pytest.raises(HTTPException) as exc:
        _assert_dentro_da_janela_de_cancelamento(doc)

    assert exc.value.detail["codigo"] == "PRAZO_CANCELAMENTO_EXPIRADO"
    assert "devolução" in exc.value.detail["mensagem"]


def test_data_de_autorizacao_sem_fuso_e_tratada_como_utc():
    """SQLite devolve datetime ingênuo; assumir local erraria por 3 horas."""
    from datetime import datetime, timedelta, timezone
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _assert_dentro_da_janela_de_cancelamento

    ingenuo = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
    doc = DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", status="AUTORIZADA",
        data_autorizacao=ingenuo,
    )

    _assert_dentro_da_janela_de_cancelamento(doc)  # não levanta


# =========================
# 9. Sanitização de log (achado A9)
# =========================

@pytest.mark.parametrize("chave", [
    "password", "senha", "token", "secret", "certificado_senha",
    "csc_token", "authorization", "cpf", "cnpj",
])
def test_campos_sensiveis_nao_vao_para_o_log(chave):
    from app.services.fiscal.http.client_startbig import _ofuscar

    assert _ofuscar({chave: "valor-secreto"})[chave] == "***"


def test_campos_normais_permanecem_legiveis_no_log():
    from app.services.fiscal.http.client_startbig import _ofuscar

    assert _ofuscar({"numero": 43, "status": "autorizado"}) == {
        "numero": 43, "status": "autorizado",
    }


def test_ofuscacao_alcanca_estruturas_aninhadas():
    from app.services.fiscal.http.client_startbig import _ofuscar

    resultado = _ofuscar({"emitente": {"cnpj": "11222333000181", "razao_social": "Loja"}})

    assert resultado["emitente"]["cnpj"] == "***"
    assert resultado["emitente"]["razao_social"] == "Loja"


def test_ofuscacao_nao_entra_em_recursao_infinita():
    from app.services.fiscal.http.client_startbig import _ofuscar

    profundo = atual = {}
    for _ in range(20):
        atual["nivel"] = {}
        atual = atual["nivel"]

    _ofuscar(profundo)  # não estoura a pilha
