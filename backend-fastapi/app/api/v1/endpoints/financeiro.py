# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/financeiro.py
# DESCRIÇÃO: Endpoints do módulo de gestão financeira (Onda 1 — despesas).
# ---------------------------------------------------------------------------
"""
DUAS TRAVAS, EM EIXOS DIFERENTES, e as duas em toda rota:

  `requer_modulo(FINANCEIRO)` — a LOJA contratou? Responde 403 com
  MODULO_NAO_CONTRATADO. Esconder o item do menu é cortesia: o backend escuta
  numa porta da máquina, e quem chamar a rota direto não passa pelo menu.

  `check_permission(...)`     — ESTE funcionário pode? Duas permissões, porque
  consultar e lançar são coisas diferentes: Contas a Pagar expõe aluguel e
  salário, e quem só precisa consultar não deveria poder dar baixa.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.depends import _handle_db_transaction, check_permission
from app.core.modulos import requer_modulo
from app.db.session import get_db
from app.schemas.conta_bancaria import (
    ContaBancariaCreate,
    ContaBancariaRead,
    ContaBancariaUpdate,
)
from app.schemas.conta_pagar import (
    ContaPagarBaixa,
    ContaPagarCreate,
    ContaPagarEstorno,
    ContaPagarListagem,
    ContaPagarRead,
    ContaPagarUpdate,
    HistoricoFinanceiroRead,
)
from app.schemas.conta_receber import (
    ContaReceberBaixa,
    ContaReceberCreate,
    ContaReceberEstorno,
    ContaReceberListagem,
    ContaReceberRead,
    ContaReceberUpdate,
)
from app.schemas.financeiro import (
    Conciliacao,
    ConciliacaoBaixaLote,
    ConciliacaoResultado,
    Extrato,
    FluxoCaixa,
    Projecao,
    Serie,
    ResumoFinanceiro,
)
from app.schemas.plano_conta import PlanoContaCreate, PlanoContaRead, PlanoContaUpdate
from app.services import financeiro as financeiro_service
from app.services import licenca as licenca_service

router = APIRouter(dependencies=[Depends(requer_modulo("FINANCEIRO"))])

# Master e cargos com "all" já furam a checagem; os demais precisam destas.
PERMISSAO_VER = ["view_financeiro", "manage_financeiro"]
PERMISSAO_GERIR = ["manage_financeiro"]


# ===========================================================================
# PLANO DE CONTAS
# ===========================================================================

@router.get(
    "/plano-contas",
    response_model=List[PlanoContaRead],
    summary="Categorias de despesa e receita",
)
def listar_plano_contas(
    apenas_ativos: bool = Query(False, description="Só as disponíveis para novos lançamentos"),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """Semeia as categorias padrão no primeiro acesso da empresa.

    Semear na listagem, e não na criação da empresa, é o que alcança as lojas
    que já existem — nenhuma delas passou por um setup que soubesse deste módulo.
    """
    return _handle_db_transaction(
        db, financeiro_service.listar_planos_conta,
        usuario_token["empresa_id"], apenas_ativos,
    )


@router.post(
    "/plano-contas",
    response_model=PlanoContaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma categoria",
)
def criar_plano_conta(
    dados: PlanoContaCreate,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.criar_plano_conta, usuario_token["empresa_id"], dados
    )


@router.patch(
    "/plano-contas/{plano_id}",
    response_model=PlanoContaRead,
    summary="Renomeia ou desativa uma categoria",
)
def atualizar_plano_conta(
    dados: PlanoContaUpdate,
    plano_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Não existe exclusão, só desativação.

    A categoria pode estar amarrada a contas antigas, e apagá-la deixaria o
    histórico sem classificação — o relatório do ano passado passaria a mostrar
    despesa "sem categoria" que sempre teve uma.
    """
    return _handle_db_transaction(
        db, financeiro_service.atualizar_plano_conta,
        usuario_token["empresa_id"], plano_id, dados,
    )


# ===========================================================================
# CONTAS BANCÁRIAS
# ===========================================================================

@router.get(
    "/contas-bancarias",
    response_model=List[ContaBancariaRead],
    summary="Onde o dinheiro da loja fica",
)
def listar_contas_bancarias(
    apenas_ativas: bool = Query(False),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.listar_contas_bancarias,
        usuario_token["empresa_id"], apenas_ativas,
    )


@router.post(
    "/contas-bancarias",
    response_model=ContaBancariaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma conta",
)
def criar_conta_bancaria(
    dados: ContaBancariaCreate,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.criar_conta_bancaria, usuario_token["empresa_id"], dados
    )


@router.patch(
    "/contas-bancarias/{conta_id}",
    response_model=ContaBancariaRead,
    summary="Altera uma conta",
)
def atualizar_conta_bancaria(
    dados: ContaBancariaUpdate,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.atualizar_conta_bancaria,
        usuario_token["empresa_id"], conta_id, dados,
    )


# ===========================================================================
# CONTAS A PAGAR
# ===========================================================================

@router.get(
    "/contas-pagar",
    response_model=ContaPagarListagem,
    summary="Lista as contas com os totais do filtro",
)
def listar_contas_pagar(
    status_filtro: Optional[str] = Query(
        None, alias="status", description="PENDENTE, PAGA ou CANCELADA"
    ),
    inicio: Optional[date] = Query(None, description="Vencimento a partir de"),
    fim: Optional[date] = Query(None, description="Vencimento até"),
    plano_conta_id: Optional[int] = Query(None),
    # Os dois recortes do painel de atenção. `vencidas` IGNORA o período: dívida
    # vencida é de mês anterior quase sempre, e filtrar pelo mês visto esconderia
    # justamente a conta do alerta.
    vencidas: bool = Query(False, description="Só pendentes com vencimento passado"),
    sem_categoria: bool = Query(False, description="Só as sem categoria no plano de contas"),
    fornecedor_id: Optional[int] = Query(None),
    busca: Optional[str] = Query(None, description="Trecho da descrição"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """Os totais vêm do servidor, calculados sobre o filtro INTEIRO.

    Somar no frontend daria o total da página, não o do período — e a diferença
    só apareceria quando a loja tivesse contas o bastante para paginar, que é
    tarde demais para descobrir.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.listar_contas_pagar(
            db_, usuario_token["empresa_id"], status=status_filtro, inicio=inicio,
            fim=fim, plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id,
            vencidas=vencidas, sem_categoria=sem_categoria,
            busca=busca, limit=limit, offset=offset,
        ),
    )


@router.post(
    "/contas-pagar",
    response_model=ContaPagarRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma conta a pagar",
)
def criar_conta_pagar(
    dados: ContaPagarCreate,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.criar_conta_pagar,
        usuario_token["empresa_id"], dados, usuario_token,
    )


@router.get(
    "/contas-pagar/{conta_id}",
    response_model=ContaPagarRead,
    summary="Detalhe de uma conta",
)
def get_conta_pagar(
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.get_conta_pagar, usuario_token["empresa_id"], conta_id
    )


@router.patch(
    "/contas-pagar/{conta_id}",
    response_model=ContaPagarRead,
    summary="Altera uma conta ainda não paga",
)
def atualizar_conta_pagar(
    dados: ContaPagarUpdate,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Alterar valor ou vencimento deixa rastro em `historico_financeiro`.

    Prorrogar boleto é legítimo; o que não pode é acontecer sem ninguém saber
    quem prorrogou. Conta já paga não se edita — estorne primeiro.
    """
    return _handle_db_transaction(
        db, financeiro_service.atualizar_conta_pagar,
        usuario_token["empresa_id"], conta_id, dados, usuario_token,
    )


@router.delete(
    "/contas-pagar/{conta_id}",
    response_model=ContaPagarRead,
    summary="Cancela a conta (não exclui)",
)
def cancelar_conta_pagar(
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """DELETE que cancela em vez de apagar.

    "Sumiu uma conta de R$ 3.000" é exatamente a pergunta que este módulo existe
    para responder — e não responderia se a linha tivesse sido excluída.
    """
    return _handle_db_transaction(
        db, financeiro_service.cancelar_conta_pagar,
        usuario_token["empresa_id"], conta_id, usuario_token,
    )


@router.post(
    "/contas-pagar/{conta_id}/pagar",
    response_model=ContaPagarRead,
    summary="Dá baixa e lança no livro do dinheiro",
)
def pagar_conta(
    dados: ContaPagarBaixa,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """A baixa e o lançamento acontecem na MESMA transação.

    Conta marcada como paga sem lançamento faria o resultado do mês mentir;
    lançamento sem a conta deixaria despesa órfã no livro.
    """
    return _handle_db_transaction(
        db, financeiro_service.pagar_conta,
        usuario_token["empresa_id"], conta_id, dados, usuario_token,
    )


@router.post(
    "/contas-pagar/{conta_id}/estornar",
    response_model=ContaPagarRead,
    summary="Desfaz a baixa sem apagar o lançamento",
)
def estornar_pagamento(
    dados: ContaPagarEstorno,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Gera o movimento contrário com a data de HOJE, nunca a original.

    `sessao_caixa` persiste o saldo esperado e o contado; um lançamento
    retroativo faria a quebra de caixa gravada discordar da recalculada.
    """
    return _handle_db_transaction(
        db, financeiro_service.estornar_pagamento,
        usuario_token["empresa_id"], conta_id, dados, usuario_token,
    )


@router.get(
    "/contas-pagar/{conta_id}/historico",
    response_model=List[HistoricoFinanceiroRead],
    summary="Quem mexeu nesta conta, quando e o quê",
)
def historico_da_conta(
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.listar_historico_da_conta,
        usuario_token["empresa_id"], conta_id,
    )


# ===========================================================================
# CONTAS A RECEBER
#
# A maioria destas contas NASCE SOZINHA, no fecho da venda ou da OS, quando o
# pagamento tem vencimento futuro. As rotas de cadastro existem para o que não
# passou pelo sistema — o cliente que já devia antes do módulo existir.
# ===========================================================================

@router.get(
    "/contas-receber",
    response_model=ContaReceberListagem,
    summary="Lista o que ainda não entrou, com os totais do filtro",
)
def listar_contas_receber(
    status_filtro: Optional[str] = Query(
        None, alias="status", description="PENDENTE, RECEBIDA ou CANCELADA"
    ),
    inicio: Optional[date] = Query(None, description="Vencimento a partir de"),
    fim: Optional[date] = Query(None, description="Vencimento até"),
    cliente_id: Optional[int] = Query(None),
    busca: Optional[str] = Query(None, description="Trecho da descrição"),
    # Recorte do painel de atenção, e IGNORA o período pela mesma razão do a
    # pagar: fiado atrasado é de mês anterior quase por definição.
    vencidas: bool = Query(False, description="Só pendentes com vencimento passado"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.listar_contas_receber(
            db_, usuario_token["empresa_id"], status=status_filtro, inicio=inicio,
            fim=fim, cliente_id=cliente_id, busca=busca, vencidas=vencidas,
            limit=limit, offset=offset,
        ),
    )


@router.post(
    "/contas-receber",
    response_model=ContaReceberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Lança uma cobrança à mão",
)
def criar_conta_receber(
    dados: ContaReceberCreate,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.criar_conta_receber,
        usuario_token["empresa_id"], dados, usuario_token,
    )


@router.get(
    "/contas-receber/{conta_id}",
    response_model=ContaReceberRead,
    summary="Detalhe de uma cobrança",
)
def get_conta_receber(
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.get_conta_receber, usuario_token["empresa_id"], conta_id
    )


@router.patch(
    "/contas-receber/{conta_id}",
    response_model=ContaReceberRead,
    summary="Altera uma cobrança ainda não recebida",
)
def atualizar_conta_receber(
    dados: ContaReceberUpdate,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Renegociar prazo com o cliente é legítimo — e deixa rastro."""
    return _handle_db_transaction(
        db, financeiro_service.atualizar_conta_receber,
        usuario_token["empresa_id"], conta_id, dados, usuario_token,
    )


@router.delete(
    "/contas-receber/{conta_id}",
    response_model=ContaReceberRead,
    summary="Cancela a cobrança (não exclui)",
)
def cancelar_conta_receber(
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Dívida perdoada continua sendo história, e o histórico responde por ela."""
    return _handle_db_transaction(
        db, financeiro_service.cancelar_conta_receber,
        usuario_token["empresa_id"], conta_id, usuario_token,
    )


@router.post(
    "/contas-receber/{conta_id}/receber",
    response_model=ContaReceberRead,
    summary="Dá baixa e lança a entrada no livro",
)
def receber_conta(
    dados: ContaReceberBaixa,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """O momento que o fecho da venda deixou marcado: "o movimento nasce no dia
    em que o cliente pagar". Origem RECEBIMENTO."""
    return _handle_db_transaction(
        db, financeiro_service.receber_conta,
        usuario_token["empresa_id"], conta_id, dados, usuario_token,
    )


@router.post(
    "/contas-receber/{conta_id}/estornar",
    response_model=ContaReceberRead,
    summary="Desfaz o recebimento sem apagar o lançamento",
)
def estornar_recebimento(
    dados: ContaReceberEstorno,
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.estornar_recebimento,
        usuario_token["empresa_id"], conta_id, dados, usuario_token,
    )


@router.get(
    "/contas-receber/{conta_id}/historico",
    response_model=List[HistoricoFinanceiroRead],
    summary="Quem mexeu nesta cobrança, quando e o quê",
)
def historico_da_cobranca(
    conta_id: int = Path(..., gt=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db, financeiro_service.listar_historico_do_recebimento,
        usuario_token["empresa_id"], conta_id,
    )


# ===========================================================================
# RESUMO
# ===========================================================================

@router.get(
    "/resumo",
    response_model=ResumoFinanceiro,
    summary="Entrou, saiu, sobrou no período",
)
def get_resumo(
    inicio: date = Query(..., description="Primeiro dia do período (data local da loja)"),
    fim: date = Query(..., description="Último dia do período (data local da loja)"),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """Regime de CAIXA, não competência — por isso "Resultado", nunca "DRE".

    O faturamento sai da mesma fonte do dashboard e dos relatórios; recalcular
    aqui abriria a porta para dois números diferentes para o mesmo mês.
    """
    # O alerta "o dinheiro acaba dia X" é o Fluxo de Caixa respondendo, e o
    # Fluxo é FINANCEIRO_PRO. A Visão Geral é do plano base, então a projeção só
    # entra para quem contratou -- senão o painel de alertas entregaria de graça
    # a resposta que o módulo pago existe para dar.
    #
    # Mesma regra do `requer_modulo`: lista vazia (a plataforma ainda não
    # cadastrou módulo nenhum) LIBERA. Bloquear aqui recusaria o alerta para
    # 100% das lojas em campo, inclusive as que pagam.
    modulos = licenca_service.modulos_da_licenca(db)
    com_projecao = not modulos or "FINANCEIRO_PRO" in modulos

    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.get_resumo(
            db_, usuario_token["empresa_id"], inicio, fim, com_projecao=com_projecao
        ),
    )


# ===========================================================================
# FLUXO DE CAIXA
# ===========================================================================

@router.get(
    "/fluxo-caixa",
    response_model=FluxoCaixa,
    summary="Projeção dos próximos dias",
    # TERCEIRA trava, além das duas do topo do arquivo: esta rota é do plano
    # PRO. O router inteiro já exige FINANCEIRO; aqui exige-se também o
    # FINANCEIRO_PRO, do mesmo jeito que o item do menu declara.
    dependencies=[Depends(requer_modulo("FINANCEIRO_PRO"))],
)
def get_fluxo_caixa(
    dias: int = Query(
        30, ge=1, le=365,
        description=(
            "Tamanho da janela a partir de hoje (a tela oferece 30, 60, 90, 180 e 360). "
            "Teto de um ano: além disso não há documento lançado para projetar"
        ),
    ),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """O que está agendado para acontecer, não o que aconteceu.

    Parte do saldo DECLARADO pelo dono (ver `ContaBancaria.saldo_informado`);
    enquanto ninguém declarar, responde `saldo_declarado=false` e a tela pede o
    número em vez de desenhar uma linha que parte de zero fingindo ser saldo.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.get_fluxo_caixa(
            db_, usuario_token["empresa_id"], dias
        ),
    )


# ===========================================================================
# CONCILIAÇÃO
# ===========================================================================

@router.get(
    "/conciliacao",
    response_model=Conciliacao,
    summary="O que a loja espera receber, agrupado por dia",
    dependencies=[Depends(requer_modulo("FINANCEIRO_PRO"))],
)
def get_conciliacao(
    inicio: date = Query(..., description="Primeiro vencimento do período (data local)"),
    fim: date = Query(..., description="Último vencimento do período (data local)"),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """Agrupado por DIA porque é assim que o dinheiro chega: a operadora não
    deposita venda a venda, deposita o lote do dia."""
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.get_conciliacao(
            db_, usuario_token["empresa_id"], inicio, fim
        ),
    )


@router.post(
    "/conciliacao/baixar-lote",
    response_model=ConciliacaoResultado,
    summary="Confere o depósito do dia e baixa o lote inteiro",
    # GERIR, não VER: isto dá baixa em dinheiro. Quem só consulta o financeiro
    # não conferencia depósito.
    dependencies=[Depends(requer_modulo("FINANCEIRO_PRO"))],
)
def baixar_lote(
    dados: ConciliacaoBaixaLote,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Rateia o depósito entre as cobranças do dia, proporcional ao previsto.

    Cada uma é baixada pelo mesmo caminho da baixa manual — mesmo movimento no
    livro, mesma trilha, mesmo estorno.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.baixar_lote(
            db_, usuario_token["empresa_id"], dados, usuario_token
        ),
    )


# ===========================================================================
# EXTRATO
# ===========================================================================

@router.get(
    "/extrato",
    response_model=Extrato,
    summary="O livro do dinheiro, linha a linha",
)
def listar_extrato(
    inicio: Optional[date] = Query(None, description="Primeiro dia (data local da loja)"),
    fim: Optional[date] = Query(None, description="Último dia (data local da loja)"),
    tipo: Optional[str] = Query(None, description="ENTRADA ou SAIDA"),
    origem: Optional[str] = Query(
        None, description="VENDA, ORDEM_SERVICO, ABERTURA, SANGRIA, SUPRIMENTO, RECEBIMENTO, DESPESA"
    ),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """O que JÁ aconteceu — o oposto do Fluxo de Caixa.

    FINANCEIRO e não FINANCEIRO_PRO: conferir o próprio dinheiro não é recurso
    avançado. É a tela que responde "de onde veio e para onde foi", e toda loja
    precisa dela para fechar o mês com o contador.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.listar_extrato(
            db_, usuario_token["empresa_id"],
            inicio=inicio, fim=fim, tipo=tipo, origem=origem,
            limit=limit, offset=offset,
        ),
    )


@router.post(
    "/alertas/{codigo}/adiar",
    summary="Cala um alerta do painel por alguns dias",
)
def adiar_alerta(
    codigo: str = Path(..., description="Código do alerta (ver AlertaFinanceiro)"),
    dias: int = Query(
        7, ge=1, le=90,
        description="Por quantos dias calar. Teto de 90: silêncio longo demais vira problema escondido",
    ),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_GERIR)),
    db: Session = Depends(get_db),
):
    """Adia, nunca dispensa para sempre.

    É o snooze do portlet de lembretes do NetSuite, com uma diferença
    deliberada: lá dá para dispensar de vez; aqui não. Alerta financeiro que
    some para sempre vira problema escondido — o prazo devolve o aviso, e se o
    problema tiver sido resolvido no meio tempo ele nem reaparece.

    Exige `manage_financeiro`: calar o aviso da loja inteira não é ação de quem
    só consulta.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.adiar_alerta(
            db_, usuario_token["empresa_id"], codigo, dias, usuario_token
        ),
    )


# ===========================================================================
# ANÁLISE — série mensal
# ===========================================================================

@router.get(
    "/serie",
    response_model=Serie,
    summary="Receita por origem, despesa e caixa, mês a mês",
    # A tela de Análise inteira é PRO: base guarda e controla o dinheiro; pro
    # avisa e aconselha.
    dependencies=[Depends(requer_modulo("FINANCEIRO_PRO"))],
)
def get_serie(
    meses: int = Query(
        12, ge=1, le=36,
        description="Quantos meses FECHADOS trazer, do mais antigo para o mais novo",
    ),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """Só meses fechados: o mês corrente não entra em série nenhuma.

    `meses_disponiveis` é o que abre e fecha os portões da tela — cada métrica
    declara quantos meses de histórico exige, e abaixo disso a tela diz o que
    falta em vez de desenhar uma reta entre dois pontos.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.get_serie(db_, usuario_token["empresa_id"], meses),
    )


@router.get(
    "/projecao",
    response_model=Projecao,
    summary="Onde o ritmo atual leva a loja em 12 meses",
    dependencies=[Depends(requer_modulo("FINANCEIRO_PRO"))],
)
def get_projecao(
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO_VER)),
    db: Session = Depends(get_db),
):
    """Repete a média dos últimos meses; NÃO extrapola inclinação.

    Com seis pontos, uma reta de regressão erra feio — e a tela passaria a
    prometer uma data que o dado não sustenta. Responde `disponivel=false`
    enquanto faltar histórico, com quantos meses faltam.
    """
    return _handle_db_transaction(
        db,
        lambda db_: financeiro_service.get_projecao(db_, usuario_token["empresa_id"]),
    )
