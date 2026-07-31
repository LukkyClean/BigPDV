# ---------------------------------------------------------------------------
# ARQUIVO: test_ordem_servico_oficina.py
# DESCRICAO: Testes de integracao do segmento de oficina mecanica na OS.
#            Cobre a validacao de placa (gated por segmento) e um teste
#            GUARDIAO garantindo que o segmento de informatica/assistencia
#            tecnica NAO sofre a validacao de placa (permanece intacto).
# ---------------------------------------------------------------------------

from starlette import status

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


# =========================
# Helpers de setup
# =========================

def _autenticar_e_criar_empresa(client, segmento: str) -> dict:
    """Cria o usuario master, faz login e cria a empresa com o segmento dado.
    Retorna o header Authorization."""
    client.post("/api/v1/usuarios/", json={
        "nome": "Admin Master",
        "email": TEST_USER_EMAIL,
        "senha": TEST_USER_PASSWORD,
    })

    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}

    empresa = {
        "razao_social": "Empresa Teste 000199 LTDA",
        "nome_fantasia": "Teste",
        "is_cnpj": True,
        "documento": "12345678000199",
        "regime_tributario": "Simples Nacional",
        "celular": "11999998888",
        "segmento": segmento,
        "endereco": [{
            "logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
            "cidade": "São Paulo", "estado": "SP", "cep": "01310-100",
        }],
    }
    r = client.post("/api/v1/empresas/", json=empresa, headers=header)
    assert r.status_code == 201, r.text
    return header


def _criar_cliente(client, header: dict) -> int:
    payload = {
        "nome": "João Pedro Silva",
        "cpf": "98765432101",
        "tipo": "PF",
        "celular": "11987654321",
        "endereco": [{
            "logradouro": "Rua das Flores", "numero": "100", "bairro": "Centro",
            "cidade": "Campinas", "estado": "SP", "cep": "13010-000",
        }],
    }
    r = client.post("/api/v1/clientes/cliente_pf", json=payload, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_payload(cliente_id: int, numero_serie: str, dados_adicionais: dict | None = None,
                itens: list | None = None, os_dados_adicionais: dict | None = None,
                objeto_extra: dict | None = None) -> dict:
    objeto = {
        "marca": "Fiat",
        "modelo": "Uno",
        "numero_serie": numero_serie,
        # dados_adicionais do objeto/veículo (placa, chassi, ano)
        "dados_adicionais": dados_adicionais or {},
    }
    if objeto_extra:
        objeto.update(objeto_extra)
    return {
        "cliente_id": cliente_id,
        "prioridade": "NORMAL",
        "defeito_relatado": "Barulho ao frear",
        # dados_adicionais no nível da OS (check-in: km_entrada, combustível, vistoria)
        "dados_adicionais": os_dados_adicionais or {},
        "objeto": objeto,
        "itens": itens if itens is not None else [],
    }


def _item(nome: str, valor_unitario: int, **extra) -> dict:
    base = {
        "tipo": "SERVICO",
        "nome": nome,
        "unidade_medida": "UN",
        "quantidade": 1,
        "valor_unitario": valor_unitario,
    }
    base.update(extra)
    return base


# =========================
# OFICINA MECANICA
# =========================

def test_criar_os_oficina_com_placa_valida(client, db_session):
    """Oficina: placa valida (Mercosul) cria a OS e persiste dados_adicionais."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)

    dados = {"km_entrada": 85000, "combustivel_nivel": "1/2", "pneus_estado": "BOM"}
    r = client.post(
        "/api/v1/ordens-servico/",
        json=_os_payload(cliente_id, "ABC1D23", dados),
        headers=header,
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    body = r.json()
    assert body["objeto"]["numero_serie"] == "ABC1D23"
    assert body["objeto"]["dados_adicionais"]["km_entrada"] == 85000
    assert body["objeto"]["dados_adicionais"]["pneus_estado"] == "BOM"


def test_criar_os_oficina_com_placa_invalida_bloqueia(client, db_session):
    """Oficina: numero_serie que nao e placa valida deve retornar 422."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)

    r = client.post(
        "/api/v1/ordens-servico/",
        json=_os_payload(cliente_id, "SEM-PLACA-123"),
        headers=header,
    )
    assert r.status_code == 422, r.text


def test_acessorios_vistoria_sobrevivem_ao_update(client, db_session):
    """Oficina: o Record de acessórios da vistoria (dados_adicionais.acessorios)
    não pode ser apagado pelo campo legado 'acessorios' (texto) vazio que o form
    envia no update. Regressão do bug de colisão de nome."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)

    payload = _os_payload(
        cliente_id, "ABC1D23",
        os_dados_adicionais={"acessorios": {"acendedor": True}},
    )
    r = client.post("/api/v1/ordens-servico/", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    # Update como o frontend: marca mais um acessório + envia 'acessorios' legado vazio
    upd = {
        "dados_adicionais": {"acessorios": {"acendedor": True, "calota": True}},
        "acessorios": "",
    }
    r2 = client.put(f"/api/v1/ordens-servico/{numero}", json=upd, headers=header)
    assert r2.status_code == 200, r2.text

    g = client.get(f"/api/v1/ordens-servico/{numero}", headers=header)
    assert g.status_code == 200, g.text
    da = g.json().get("dados_adicionais") or {}
    assert da.get("acessorios") == {"acendedor": True, "calota": True}, da


def test_guardiao_informatica_pode_limpar_campo_legado(client, db_session):
    """GUARDIAO: informática continua podendo LIMPAR os campos legados de texto
    (senha_aparelho/acessorios/condicoes_aparelho) enviando string vazia — o
    guard do dict não afeta a informática, cujos campos são sempre texto."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    payload = _os_payload(cliente_id, "SERIAL-9", os_dados_adicionais={"senha_aparelho": "1234"})
    r = client.post("/api/v1/ordens-servico/", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]
    assert (r.json().get("dados_adicionais") or {}).get("senha_aparelho") == "1234"

    r2 = client.put(f"/api/v1/ordens-servico/{numero}", json={"senha_aparelho": ""}, headers=header)
    assert r2.status_code == 200, r2.text

    g = client.get(f"/api/v1/ordens-servico/{numero}", headers=header)
    da = g.json().get("dados_adicionais") or {}
    assert da.get("senha_aparelho") == "", da


def test_definicao_campos_oficina(client, db_session):
    """Contrato de campos: oficina retorna definicao dedicada com rotulo Veiculo."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    r = client.get("/api/v1/ordens-servico/definicao-campos", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["segmento"] == "oficina_mecanica"
    assert body["tem_definicao"] is True
    assert body["definicao"]["rotulo_objeto_singular"] == "Veículo"
    assert len(body["definicao"]["vistoria"]) == 3


# =========================
# GUARDIAO — INFORMATICA INTACTA
# =========================

def test_os_informatica_nao_sofre_validacao_de_placa(client, db_session):
    """GUARDIAO: empresa de informatica cria OS com qualquer numero_serie
    (IMEI/serial), sem a validacao de placa exclusiva da oficina."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    dados = {"imei": "359999000000001", "senha_aparelho": "1234"}
    r = client.post(
        "/api/v1/ordens-servico/",
        json=_os_payload(cliente_id, "SERIAL-XYZ-999", dados),
        headers=header,
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    assert r.json()["objeto"]["numero_serie"] == "SERIAL-XYZ-999"


def test_definicao_campos_segmento_generico_sem_definicao(client, db_session):
    """Segmento generico (mercado) nao tem definicao dedicada."""
    header = _autenticar_e_criar_empresa(client, "mercado")
    r = client.get("/api/v1/ordens-servico/definicao-campos", headers=header)
    assert r.status_code == 200, r.text
    assert r.json()["tem_definicao"] is False


# =========================
# ONDA 2 — aprovacao / garantia por item / historico de KM
# =========================

def test_item_reprovado_nao_entra_no_total(client, db_session):
    """Item REPROVADO nao entra no valor_total; APROVADO conta."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)
    itens = [
        _item("Troca de pastilha", 10000, status_aprovacao="APROVADO"),
        _item("Troca de disco", 5000, status_aprovacao="REPROVADO"),
    ]
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, "ABC1D23", itens=itens), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    body = r.json()
    assert body["valor_bruto"] == 10000, "só o item APROVADO deve contar"
    assert body["valor_total"] == 10000


def test_garantia_por_item_persistida(client, db_session):
    """Garantia (dias e KM) por item é persistida e retornada."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)
    itens = [_item("Troca de correia", 20000, garantia_dias=90, garantia_km=10000)]
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, "ABC1D23", itens=itens), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    item = r.json()["itens"][0]
    assert item["garantia_dias"] == 90
    assert item["garantia_km"] == 10000
    assert item["status_aprovacao"] == "APROVADO"


def test_historico_km_do_veiculo(client, db_session):
    """Histórico de KM lê km_entrada das OS do veículo, da mais antiga p/ recente."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)

    # 1a OS com KM 80000 (check-in é nível da OS)
    r1 = client.post("/api/v1/ordens-servico/",
                     json=_os_payload(cliente_id, "ABC1D23", os_dados_adicionais={"km_entrada": 80000}),
                     headers=header)
    assert r1.status_code == 201, r1.text
    objeto_id = r1.json()["objeto"]["id"]

    r = client.get(f"/api/v1/ordens-servico/objeto/{objeto_id}/historico-km", headers=header)
    assert r.status_code == 200, r.text
    hist = r.json()
    assert len(hist) == 1
    assert hist[0]["km_entrada"] == 80000


def test_atualizar_dados_adicionais_persiste(client, db_session):
    """REGRESSÃO: atualizar dados_adicionais de uma OS que já tem conteúdo deve
    persistir. Bug: mutação in-place + reatribuição da mesma referência não era
    detectada pelo SQLAlchemy (JSON não rastreado in-place)."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)
    r = client.post("/api/v1/ordens-servico/",
                    json=_os_payload(cliente_id, "ABC1D23", os_dados_adicionais={"km_entrada": 80000}),
                    headers=header)
    assert r.status_code == 201, r.text
    numero_os = r.json()["numero_os"]

    up = client.put(f"/api/v1/ordens-servico/{numero_os}",
                    json={"dados_adicionais": {"combustivel_nivel": "CHEIO"}},
                    headers=header)
    assert up.status_code == 200, up.text

    # GET em requisição separada (sessão nova) reflete o que foi de fato persistido
    g = client.get(f"/api/v1/ordens-servico/{numero_os}", headers=header)
    assert g.status_code == 200, g.text
    dados = g.json()["dados_adicionais"]
    assert dados.get("km_entrada") == 80000, "chave original deve ser preservada"
    assert dados.get("combustivel_nivel") == "CHEIO", "chave nova deve persistir"


def test_imei_volta_na_resposta_e_sobrevive_ao_update(client, db_session):
    """REGRESSÃO (informática): o IMEI era GRAVADO mas nunca devolvido.

    `imei` não é coluna — vive em objeto.dados_adicionais desde a refatoração
    Equipamento->ObjetoServico, e o modelo não tinha a property correspondente.
    O Pydantic não achava o atributo no ORM e devolvia null calado: o campo
    reabria em branco ("não salvou") e o save seguinte mandava "" por cima,
    destruindo o dado de verdade.
    """
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    r = client.post(
        "/api/v1/ordens-servico/",
        json=_os_payload(cliente_id, "SERIAL-IMEI-1",
                         objeto_extra={"imei": "352415001234567"}),
        headers=header,
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero_os = r.json()["numero_os"]
    assert r.json()["objeto"]["imei"] == "352415001234567", "criação deve devolver o IMEI"

    # Reabrir a OS (é aqui que o campo aparecia vazio)
    g = client.get(f"/api/v1/ordens-servico/{numero_os}", headers=header)
    assert g.status_code == 200, g.text
    assert g.json()["objeto"]["imei"] == "352415001234567", "GET deve devolver o IMEI gravado"

    # Editar OUTRO campo do objeto sem tocar no IMEI não pode apagá-lo
    up = client.put(f"/api/v1/ordens-servico/{numero_os}/objeto",
                    json={"cor": "Preto"}, headers=header)
    assert up.status_code == 200, up.text

    g2 = client.get(f"/api/v1/ordens-servico/{numero_os}", headers=header)
    assert g2.json()["objeto"]["cor"] == "Preto"
    assert g2.json()["objeto"]["imei"] == "352415001234567", "IMEI deve sobreviver ao update"


def test_imei_vazio_limpa_sem_gravar_string_vazia(client, db_session):
    """Limpar o IMEI de propósito ("") remove a chave em vez de gravar "" —
    string vazia no JSON é lixo que reaparece como valor 'preenchido'."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    r = client.post(
        "/api/v1/ordens-servico/",
        json=_os_payload(cliente_id, "SERIAL-IMEI-2",
                         objeto_extra={"imei": "352415001234567"}),
        headers=header,
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero_os = r.json()["numero_os"]

    up = client.put(f"/api/v1/ordens-servico/{numero_os}/objeto",
                    json={"imei": ""}, headers=header)
    assert up.status_code == 200, up.text

    g = client.get(f"/api/v1/ordens-servico/{numero_os}", headers=header)
    objeto = g.json()["objeto"]
    assert objeto["imei"] is None, "IMEI limpo deve voltar como null"
    assert "imei" not in (objeto["dados_adicionais"] or {}), "chave deve sumir do JSON"


# =========================
# ONDA 3A — lembrete de revisão
# =========================

def test_revisao_pendente_por_data(client, db_session):
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)
    r = client.post("/api/v1/ordens-servico/",
                    json=_os_payload(cliente_id, "ABC1D23", objeto_extra={"proxima_revisao_data": "2020-01-01"}),
                    headers=header)
    assert r.status_code == 201, r.text
    g = client.get("/api/v1/ordens-servico/revisoes-pendentes", headers=header)
    assert g.status_code == 200, g.text
    lst = g.json()
    assert len(lst) == 1
    assert lst[0]["numero_serie"] == "ABC1D23"
    assert lst[0]["motivo"] == "data"


def test_revisao_futura_nao_aparece(client, db_session):
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)
    r = client.post("/api/v1/ordens-servico/",
                    json=_os_payload(cliente_id, "ABC1D23", objeto_extra={"proxima_revisao_data": "2099-01-01"}),
                    headers=header)
    assert r.status_code == 201, r.text
    g = client.get("/api/v1/ordens-servico/revisoes-pendentes", headers=header)
    assert g.status_code == 200, g.text
    assert g.json() == []


def test_revisao_pendente_por_km(client, db_session):
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)
    r = client.post(
        "/api/v1/ordens-servico/",
        json=_os_payload(cliente_id, "ABC1D23",
                         objeto_extra={"proxima_revisao_km": 10000},
                         os_dados_adicionais={"km_entrada": 12000}),
        headers=header,
    )
    assert r.status_code == 201, r.text
    g = client.get("/api/v1/ordens-servico/revisoes-pendentes", headers=header)
    assert g.status_code == 200, g.text
    lst = g.json()
    assert len(lst) == 1
    assert lst[0]["motivo"] == "km"
    assert lst[0]["km_atual"] == 12000


def test_informatica_nao_aparece_em_revisoes(client, db_session):
    """GUARDIAO: equipamento de informática (sem revisão agendada) não aparece."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    r = client.post("/api/v1/ordens-servico/",
                    json=_os_payload(cliente_id, "SERIAL-1"),
                    headers=header)
    assert r.status_code == 201, r.text
    g = client.get("/api/v1/ordens-servico/revisoes-pendentes", headers=header)
    assert g.status_code == 200, g.text
    assert g.json() == []


def test_guardiao_informatica_itens_contam_normalmente(client, db_session):
    """GUARDIAO: sem status enviado, itens default APROVADO contam no total
    (comportamento da informática permanece igual)."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    itens = [_item("Formatação", 8000), _item("Limpeza", 2000)]  # sem status_aprovacao
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, "SERIAL-1", itens=itens), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    body = r.json()
    assert body["valor_bruto"] == 10000, "todos os itens contam (default APROVADO)"
    assert body["itens"][0]["status_aprovacao"] == "APROVADO"


# =========================
# REABERTURA — cliente_pagou (global: OS de qualquer segmento)
# =========================

def _criar_forma_pagamento(client, header) -> int:
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True}, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()["id"]


def _criar_e_finalizar_os(client, header, cliente_id, fp_id, numero_serie, valor):
    """Cria uma OS (informática) com 1 item e finaliza pagando o valor cheio."""
    itens = [_item("Serviço", valor)]
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, numero_serie, itens=itens), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]
    fin = {
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": valor}],
    }
    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert rf.status_code == 200, rf.text
    assert len(rf.json()["pagamentos"]) == 1
    return numero


def test_reabrir_nao_pagou_apaga_pagamento_e_recobra_cheio(client, db_session):
    """Reabertura com cliente_pagou=False: pagamento não era real → apaga os
    pagamentos e zera o crédito; a OS recobra o valor cheio."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    fp_id = _criar_forma_pagamento(client, header)
    numero = _criar_e_finalizar_os(client, header, cliente_id, fp_id, "SERIAL-NP", 14000)

    rr = client.put(f"/api/v1/ordens-servico/{numero}/reabrir", json={"cliente_pagou": False}, headers=header)
    assert rr.status_code == 200, rr.text
    body = rr.json()
    assert body["pagamentos"] == [], body["pagamentos"]
    assert body.get("credito_anterior") in (None, 0), body.get("credito_anterior")
    assert body["valor_total"] == 14000, body["valor_total"]


def test_reabrir_ja_pagou_preserva_credito(client, db_session):
    """Reabertura padrão (cliente_pagou=True): o valor pago vira crédito da OS
    (credito_anterior), abatido do novo total. Comportamento atual preservado."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    fp_id = _criar_forma_pagamento(client, header)
    numero = _criar_e_finalizar_os(client, header, cliente_id, fp_id, "SERIAL-JP", 14000)

    rr = client.put(f"/api/v1/ordens-servico/{numero}/reabrir", json={"cliente_pagou": True}, headers=header)
    assert rr.status_code == 200, rr.text
    assert rr.json().get("credito_anterior") == 14000, rr.json().get("credito_anterior")


# =========================
# JUROS: repassado ao cliente x absorvido pela loja
# =========================

def _finalizar_com_juros(client, header, cliente_id, fp_id, serie, base, juros, responsavel):
    """Cria uma OS de `base` e finaliza com um pagamento que tem juros.

    Espelha o que o frontend monta: quando o cliente paga o juros, ele vem
    embutido no `valor` e some no `acrescimo`; quando a loja absorve, o `valor`
    é só a base e o `acrescimo` fica zerado.
    """
    itens = [_item("Serviço", base)]
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, serie, itens=itens), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    repassa = responsavel == "CLIENTE"
    fin = {
        "situacao_equipamento": "REPARADO",
        "garantia": "90 dias",
        "acrescimo": juros if repassa else 0,
        "pagamentos": [{
            "forma_pagamento_id": fp_id,
            "valor": base + juros if repassa else base,
            "juros_valor": juros,
            "juros_responsavel": responsavel,
            "bandeira_cartao": "VISA",
        }],
    }
    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert rf.status_code == 200, rf.text
    return rf.json()


def test_os_juros_repassado_ao_cliente_sobe_o_total(client, db_session):
    """CLIENTE: o juros entra no acréscimo e o cliente paga a mais."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    fp_id = _criar_forma_pagamento(client, header)

    body = _finalizar_com_juros(client, header, cliente_id, fp_id, "SERIAL-JC", 10000, 500, "CLIENTE")

    assert body["acrescimo"] == 500
    assert body["valor_total"] == 10500, "total sobe com o juros repassado"
    pgto = body["pagamentos"][0]
    assert pgto["valor"] == 10500, "o valor cobrado já inclui o juros"
    assert pgto["juros_valor"] == 500
    assert pgto["juros_responsavel"] == "CLIENTE"


def test_os_juros_absorvido_pela_loja_nao_sobe_o_total(client, db_session):
    """LOJA: o cliente paga o preço combinado; o juros fica registrado como custo
    e NÃO pode inflar o total da OS."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    fp_id = _criar_forma_pagamento(client, header)

    body = _finalizar_com_juros(client, header, cliente_id, fp_id, "SERIAL-JL", 10000, 500, "LOJA")

    assert body["acrescimo"] == 0, "juros absorvido não é acréscimo"
    assert body["valor_total"] == 10000, "o cliente paga o preço combinado"
    pgto = body["pagamentos"][0]
    assert pgto["valor"] == 10000, "o valor cobrado NÃO inclui o juros"
    assert pgto["juros_valor"] == 500, "mas o custo fica registrado"
    assert pgto["juros_responsavel"] == "LOJA"


def test_os_pagamento_sem_juros_assume_cliente(client, db_session):
    """Retrocompatibilidade: payload antigo, sem os campos de juros, continua
    válido e é lido como CLIENTE com juros zero."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    fp_id = _criar_forma_pagamento(client, header)
    numero = _criar_e_finalizar_os(client, header, cliente_id, fp_id, "SERIAL-JZ", 14000)

    r = client.get(f"/api/v1/ordens-servico/{numero}", headers=header)
    assert r.status_code == 200, r.text
    pgto = r.json()["pagamentos"][0]
    assert pgto["juros_valor"] == 0
    assert pgto["juros_responsavel"] == "CLIENTE"


# =========================
# ESTOQUE: peca aplicada na OS sai do estoque
# =========================

def _criar_produto(client, header, codigo: str, quantidade: int, valor: int = 5000) -> int:
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Peça {codigo}", "codigo_produto": codigo, "unidade_medida": "UN",
        "estoque": {"valor_varejo": valor, "quantidade": quantidade},
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()["id"]


def _estoque_atual(db_session, produto_id: int) -> int:
    """Le a quantidade direto do banco: nao existe GET /produtos/{id} na API."""
    from app.db.models.produto import Produto
    db_session.expire_all()
    produto = db_session.query(Produto).filter(Produto.id == produto_id).first()
    return produto.estoque.quantidade


def _item_produto(produto_id: int, nome: str, valor: int, quantidade: int = 1, **extra) -> dict:
    base = {
        "tipo": "PRODUTO", "item_id": produto_id, "nome": nome,
        "unidade_medida": "UN", "quantidade": quantidade, "valor_unitario": valor,
    }
    base.update(extra)
    return base


def _os_com_produto(client, header, cliente_id, serie, produto_id, valor=5000, quantidade=1, **item_extra):
    itens = [_item_produto(produto_id, "Peça aplicada", valor, quantidade, **item_extra)]
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, serie, itens=itens), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()["numero_os"]


def _finalizar(client, header, numero, valor):
    # OS de valor zero (ex.: todos os itens reprovados) finaliza sem pagamento —
    # o schema recusa pagamento com valor 0.
    pagamentos = [{"forma_pagamento_id": _FP_ID["id"], "valor": valor}] if valor > 0 else []
    fin = {
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": pagamentos,
    }
    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert r.status_code == 200, r.text
    return r


_FP_ID = {}


def test_os_finalizada_da_baixa_no_estoque(client, db_session):
    """O bug: peça aplicada na OS saía do estoque no papel mas não no sistema."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    _FP_ID["id"] = _criar_forma_pagamento(client, header)
    produto_id = _criar_produto(client, header, "PECA-1", quantidade=10)

    numero = _os_com_produto(client, header, cliente_id, "SERIAL-E1", produto_id, valor=5000, quantidade=3)
    assert _estoque_atual(db_session, produto_id) == 10, "criar a OS não movimenta estoque"

    _finalizar(client, header, numero, 15000)
    assert _estoque_atual(db_session, produto_id) == 7, "finalizar tira as 3 peças do estoque"


def test_os_item_reprovado_nao_da_baixa(client, db_session):
    """Peça recusada pelo cliente continua na prateleira — não entra no total
    da OS e também não pode sair do estoque."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    _FP_ID["id"] = _criar_forma_pagamento(client, header)
    produto_id = _criar_produto(client, header, "PECA-2", quantidade=10)

    numero = _os_com_produto(
        client, header, cliente_id, "SERIAL-E2", produto_id,
        valor=5000, quantidade=2, status_aprovacao="REPROVADO",
    )
    _finalizar(client, header, numero, 0)
    assert _estoque_atual(db_session, produto_id) == 10


def test_os_reaberta_devolve_a_peca_ao_estoque(client, db_session):
    """Reabrir desfaz a baixa. Sem isso, reabrir e refinalizar tiraria a mesma
    peça duas vezes do estoque."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    _FP_ID["id"] = _criar_forma_pagamento(client, header)
    produto_id = _criar_produto(client, header, "PECA-3", quantidade=10)

    numero = _os_com_produto(client, header, cliente_id, "SERIAL-E3", produto_id, valor=5000, quantidade=2)
    _finalizar(client, header, numero, 10000)
    assert _estoque_atual(db_session, produto_id) == 8

    rr = client.put(f"/api/v1/ordens-servico/{numero}/reabrir", json={"cliente_pagou": True}, headers=header)
    assert rr.status_code == 200, rr.text
    assert _estoque_atual(db_session, produto_id) == 10, "reabrir devolve a peça"

    _finalizar(client, header, numero, 10000)
    assert _estoque_atual(db_session, produto_id) == 8, "refinalizar tira UMA vez, não duas"


def test_os_cancelada_apos_finalizar_devolve_estoque_uma_vez_so(client, db_session):
    """Cancelar uma OS finalizada estorna. Reabrir depois NÃO pode estornar de
    novo — a peça já voltou no cancelamento."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    _FP_ID["id"] = _criar_forma_pagamento(client, header)
    produto_id = _criar_produto(client, header, "PECA-4", quantidade=10)

    numero = _os_com_produto(client, header, cliente_id, "SERIAL-E4", produto_id, valor=5000, quantidade=4)
    _finalizar(client, header, numero, 20000)
    assert _estoque_atual(db_session, produto_id) == 6

    rc = client.put(f"/api/v1/ordens-servico/{numero}/cancelar", json={"motivo": "desistiu"}, headers=header)
    assert rc.status_code == 200, rc.text
    assert _estoque_atual(db_session, produto_id) == 10, "cancelar devolve"

    rr = client.put(f"/api/v1/ordens-servico/{numero}/reabrir", json={"cliente_pagou": False}, headers=header)
    assert rr.status_code == 200, rr.text
    assert _estoque_atual(db_session, produto_id) == 10, "reabrir de CANCELADA não estorna de novo"


def test_os_cancelada_sem_finalizar_nao_mexe_no_estoque(client, db_session):
    """OS que nunca foi finalizada não consumiu estoque; cancelar não pode
    inventar peça que nunca saiu."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    _FP_ID["id"] = _criar_forma_pagamento(client, header)
    produto_id = _criar_produto(client, header, "PECA-5", quantidade=10)

    numero = _os_com_produto(client, header, cliente_id, "SERIAL-E5", produto_id, valor=5000, quantidade=2)
    rc = client.put(f"/api/v1/ordens-servico/{numero}/cancelar", json={"motivo": "desistiu"}, headers=header)
    assert rc.status_code == 200, rc.text
    assert _estoque_atual(db_session, produto_id) == 10


def test_os_estoque_insuficiente_finaliza_e_fica_negativo(client, db_session):
    """Decisão de negócio: a peça já foi instalada, então a OS não pode ficar
    presa. O saldo negativo é o sinal de que falta acertar a contagem."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)
    _FP_ID["id"] = _criar_forma_pagamento(client, header)
    produto_id = _criar_produto(client, header, "PECA-6", quantidade=1)

    numero = _os_com_produto(client, header, cliente_id, "SERIAL-E6", produto_id, valor=5000, quantidade=3)
    _finalizar(client, header, numero, 15000)
    assert _estoque_atual(db_session, produto_id) == -2


# =========================
# FILTRO POR DESFECHO (situacao_equipamento)
# =========================

def _finalizar_com_situacao(client, header, cliente_id, serie, situacao):
    """Cria uma OS sem itens e a finaliza com o desfecho informado.

    SEM_REPARO/CONDENADO não exigem pagamento — o serviço libera a cobrança
    para esses desfechos.
    """
    r = client.post("/api/v1/ordens-servico/", json=_os_payload(cliente_id, serie), headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]
    rf = client.put(
        f"/api/v1/ordens-servico/{numero}/finalizar",
        json={"situacao_equipamento": situacao, "pagamentos": []},
        headers=header,
    )
    assert rf.status_code == 200, rf.text
    assert rf.json()["situacao_equipamento"] == situacao
    assert rf.json()["status"] == "FINALIZADA", "desfecho não é status: a OS segue FINALIZADA"
    return numero


def test_filtro_por_desfecho_separa_condenado_de_sem_reparo(client, db_session):
    """A listagem filtra por `situacao_equipamento` — é o que faz a OS condenada
    ser encontrável, já que o `status` dela é FINALIZADA como o de qualquer outra."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    cond = _finalizar_com_situacao(client, header, cliente_id, "SERIAL-D1", "CONDENADO")
    sem = _finalizar_com_situacao(client, header, cliente_id, "SERIAL-D2", "SEM_REPARO")
    _finalizar_com_situacao(client, header, cliente_id, "SERIAL-D3", "REPARADO")

    r = client.get("/api/v1/ordens-servico/", params={"situacao_equipamento": "CONDENADO"}, headers=header)
    assert r.status_code == 200, r.text
    assert [os["numero_os"] for os in r.json()["items"]] == [cond]

    r = client.get("/api/v1/ordens-servico/", params={"situacao_equipamento": "SEM_REPARO"}, headers=header)
    assert r.status_code == 200, r.text
    assert [os["numero_os"] for os in r.json()["items"]] == [sem]

    # O filtro de status continua enxergando as três: condenar não tira a OS
    # de FINALIZADA, e o faturamento depende disso.
    r = client.get("/api/v1/ordens-servico/", params={"status": "FINALIZADA"}, headers=header)
    assert r.json()["total_items"] == 3, r.json()


def test_filtro_por_desfecho_ignora_os_reaberta(client, db_session):
    """Reabrir não limpa `situacao_equipamento` (é o último desfecho conhecido),
    então o filtro exige FINALIZADA — senão o "Condenado" traria de volta uma OS
    que a tela já mostra como EM_ANDAMENTO."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    numero = _finalizar_com_situacao(client, header, cliente_id, "SERIAL-D4", "CONDENADO")
    rr = client.put(f"/api/v1/ordens-servico/{numero}/reabrir", json={"cliente_pagou": False}, headers=header)
    assert rr.status_code == 200, rr.text
    assert rr.json()["status"] == "EM_ANDAMENTO"

    r = client.get("/api/v1/ordens-servico/", params={"situacao_equipamento": "CONDENADO"}, headers=header)
    assert r.status_code == 200, r.text
    assert r.json()["items"] == [], "OS reaberta não é mais um condenado entregue"
