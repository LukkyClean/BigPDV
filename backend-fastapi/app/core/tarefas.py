import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI

from app.db.base import Base
from app.db.migrations import aplicar_migracoes
from app.db.session import SessionLocal, engine
from app.db.models.contador_venda import ContadorVenda
from app.db.models.empresa import Empresa
from app.db.models.forma_pagamento import FormaPagamento
from app.services.limpeza_temporal import cancelar_vendas_ativas_expiradas, limpar_orcamentos_expirados, limpar_temp_data
from app.services.licenca import enviar_heartbeat, renovar_licenca_background, desconectar_terminal
from app.services.backup import (
    create_backup,
    get_last_backup,
    apply_pending_restore,
    limpar_snapshots_antigos,
)
# `cloud` reexporta sync/CloudSyncError; o alias mantem o resto do arquivo igual.
from app.services import cloud as cloud_sync
from app.services.configuracao_backup import get_or_create_configuracao_backup
from app.db.crud import terminal_conectado as terminal_crud

from app.core.discovery import register_service, stop_discovery

logger = logging.getLogger(__name__)

INTERVALO_LIMPEZA_HORAS = 6
INTERVALO_HEARTBEAT_SEGUNDOS = 100  # 5 minutos
INTERVALO_RENOVACAO_SEGUNDOS = 3600  # 1 hora

ATRASO_INICIAL_BACKUP_SEGUNDOS = 180
# Checagem curta: o horario do backup diario e escolhido pelo lojista e pode
# mudar a qualquer momento, entao o loop rele a configuracao a cada minuto.
INTERVALO_CHECAGEM_BACKUP_SEGUNDOS = 60

FREQUENCIA_HORAS = {
    "8horas": 8,
    "12horas": 12,
    "diario": 24,
}

ATRASO_INICIAL_SYNC_SEGUNDOS = 300
INTERVALO_SYNC_SEGUNDOS = 3600


# De hora em hora. Nao precisa ser mais rapido: o dinheiro cai na conta em D+n,
# e uma hora de atraso num deposito de ontem nao muda decisao nenhuma. Mais
# lento perderia a virada do dia numa loja que fica aberta ate tarde.
INTERVALO_BAIXA_AUTOMATICA_SEGUNDOS = 3600


async def _loop_baixa_automatica():
    """Entra o dinheiro das cobrancas que o dono declarou que caem sozinhas.

    RODA ANTES DO PRIMEIRO SLEEP, de proposito: e no boot que ela recupera o
    que passou. Loja fecha na sexta e abre na segunda -- as cobrancas de sabado
    e domingo entram todas no boot de segunda, porque a consulta e por
    "vencimento <= hoje" e nao "vencimento = hoje".

    So alcanca o que nasceu marcado, que e cartao com prazo declarado na forma
    de pagamento. Fiado nunca entra sozinho: cliente nao paga por agendamento.
    """
    from app.services import financeiro_receber as receber_service

    while True:
        try:
            db = SessionLocal()
            try:
                quantidade = receber_service.baixar_automaticas(db)
                if quantidade:
                    logger.info(
                        "Baixa automatica: %d cobranca(s) entraram no caixa.",
                        quantidade,
                    )
            finally:
                db.close()
        except Exception:
            logger.exception("Erro na baixa automatica de recebimentos")

        await asyncio.sleep(INTERVALO_BAIXA_AUTOMATICA_SEGUNDOS)


async def _loop_limpeza_temporal():
    """Loop em segundo plano que executa a limpeza periodicamente."""
    while True:
        try:
            db = SessionLocal()
            try:
                cancelar_vendas_ativas_expiradas(db)
                limpar_orcamentos_expirados(db)
            finally:
                db.close()
        except Exception:
            logger.exception("Erro na limpeza automatica temporal")

        await asyncio.sleep(INTERVALO_LIMPEZA_HORAS * 3600)


def _precisa_backup_por_horario(horario: str, last_backup_created_at: datetime | None) -> bool:
    """
    Decide o backup diario: so dispara depois do horario escolhido e no maximo
    uma vez por dia. `horario` invalido cai em 02:00 em vez de derrubar o loop.
    """
    agora = datetime.now()
    try:
        hora, minuto = map(int, horario.split(":"))
    except (ValueError, AttributeError):
        hora, minuto = 2, 0

    alvo_hoje = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    if agora < alvo_hoje:
        return False

    if last_backup_created_at is None:
        return True

    return last_backup_created_at < alvo_hoje


async def _loop_backup():
    """Loop que mantem o backup local em dia, na frequencia escolhida na tela."""
    await asyncio.sleep(ATRASO_INICIAL_BACKUP_SEGUNDOS)

    while True:
        try:
            db = SessionLocal()
            try:
                # A loja tem uma empresa so, mas o id nem sempre e 1 (banco
                # recriado/restaurado). Fixar 1 faria a linha nascer com FK
                # invalida e o loop errar de minuto em minuto, sem backup.
                empresa_id = db.query(Empresa.id).order_by(Empresa.id).limit(1).scalar()
                if empresa_id is None:
                    # Onboarding ainda nao rodou: nao ha o que salvar.
                    ativo = False
                else:
                    config = get_or_create_configuracao_backup(db, empresa_id)
                    ativo = config.backup_automatico_ativo
                    frequencia = config.frequencia
                    horario = config.horario
                    db.commit()
            finally:
                db.close()

            if not ativo:
                await asyncio.sleep(INTERVALO_CHECAGEM_BACKUP_SEGUNDOS)
                continue

            last_backup = await asyncio.to_thread(get_last_backup)
            last_backup_created_at = datetime.fromisoformat(last_backup.criado_em) if last_backup else None

            if frequencia == "diario":
                need_backup = _precisa_backup_por_horario(horario, last_backup_created_at)
            else:
                intervalo_horas = FREQUENCIA_HORAS.get(frequencia, 8)
                need_backup = (
                    last_backup_created_at is None
                    or datetime.now() - last_backup_created_at >= timedelta(hours=intervalo_horas)
                )

            if need_backup:
                print(f"[BACKUP] Criando backup automático (último backup: {last_backup.criado_em if last_backup else 'nenhum'})")
                backup_info = await asyncio.to_thread(create_backup)
                print(f'[BACKUP] Backup automático criado: {backup_info.arquivo} ({backup_info.tamanho_bytes} Bytes)')
        except Exception as e:
            print(f"[BACKUP] Erro ao criar backup automático: {type(e).__name__}: {e}")
            print(f"[BACKUP] Próxima tentativa em {INTERVALO_CHECAGEM_BACKUP_SEGUNDOS}s")

        await asyncio.sleep(INTERVALO_CHECAGEM_BACKUP_SEGUNDOS)


async def _loop_cloud_sync():
    """Loop em segundo plano que envia o backup local para a nuvem (a cada 1h)."""
    await asyncio.sleep(ATRASO_INICIAL_SYNC_SEGUNDOS)

    while True:
        try:
            db = SessionLocal()

            try:
                print("[SYNC] Iniciando ciclo de sincronização com nuvem...")
                summary = await cloud_sync.sync(db)
                print(f"[SYNC] Status da sincronização: {summary}")
            except Exception as e:
                print(f"[SYNC] Erro durante a sincronização: {type(e).__name__}: {e}")
            finally:
                db.close()
        except cloud_sync.CloudSyncError as e:
            print(f"[SYNC] Ciclo encerrado: {e} (codigo={e.code})")

        await asyncio.sleep(INTERVALO_SYNC_SEGUNDOS)


async def _loop_heartbeat_licenca():
    """Loop em segundo plano que envia heartbeat à API StartBig periodicamente."""
    while True:
        try:
            db = SessionLocal()
            try:
                await enviar_heartbeat(db)
            finally:
                db.close()
        except Exception as e:
            print(f"[licenca] Erro no heartbeat de licenca: {type(e).__name__}: {e}")

        print(f"[licenca] Proximo heartbeat em {INTERVALO_HEARTBEAT_SEGUNDOS}s...")
        await asyncio.sleep(INTERVALO_HEARTBEAT_SEGUNDOS)


async def _loop_renovacao_licenca():
    """Loop em segundo plano que renova o token de licença proativamente."""
    while True:
        try:
            db = SessionLocal()
            try:
                await renovar_licenca_background(db)
            finally:
                db.close()
        except Exception as e:
            print(f"[licenca] Erro na renovação de licença: {type(e).__name__}: {e}")

        await asyncio.sleep(INTERVALO_RENOVACAO_SEGUNDOS)


# Nome da forma de pagamento -> código `tPag` do layout da NF-e.
#
# POR QUE ISTO EXISTE
# -------------------
# As seis formas padrão nasciam com `codigo_sefaz` NULL, nenhuma tela permitia
# preencher, e o gate de emissão recusa a nota enquanto houver forma ativa sem
# código (`pendencias_globais.pagamentos_sem_sefaz`). Resultado: TODA instalação
# ficava impedida de emitir por um campo que não havia como preencher. Achado
# numa loja real em 12/09/2026, na tentativa da primeira NF-e.
#
# O 17 é o PIX. A NT 2023.004 separou 17 (dinâmico) de 20 (estático) — o nosso
# QR é estático, mas a forma "PIX" da loja também recebe PIX dinâmico pelo app
# do banco. Fica 17, que é o de uso geral, e a tela permite trocar.
_CODIGO_SEFAZ_PADRAO = {
    "dinheiro": "01",
    "pix": "17",
    "cartão de crédito": "03",
    "cartao de credito": "03",
    "cartão de débito": "04",
    "cartao de debito": "04",
    "transferência bancária": "18",
    "transferencia bancaria": "18",
    "boleto": "15",
    "fiado": "05",           # 05 = Crédito Loja
    "crediário": "05",
    "crediario": "05",
    "cheque": "02",
}

_FORMAS_PAGAMENTO_PADRAO = [
    "Dinheiro",
    "PIX",
    "Cartão de Crédito",
    "Cartão de Débito",
    "Transferência Bancária",
    "Boleto",
]


def _seed_formas_pagamento():
    """
    Insere as formas de pagamento padrão e completa o código SEFAZ do que faltar.

    SÓ PREENCHE O QUE FALTA. Forma com código já gravado não é tocada: a loja
    pode ter trocado de propósito (o 20 do PIX estático, por exemplo), e
    sobrescrever desfaria a escolha a cada reinício do sistema.
    """
    db = SessionLocal()
    try:
        for nome in _FORMAS_PAGAMENTO_PADRAO:
            existe = db.query(FormaPagamento).filter(FormaPagamento.nome.ilike(nome)).first()
            if not existe:
                db.add(FormaPagamento(
                    nome=nome,
                    ativo=True,
                    codigo_sefaz=_CODIGO_SEFAZ_PADRAO.get(nome.strip().lower()),
                ))
                logger.info("Forma de pagamento criada: %s", nome)

        # Backfill: alcança as instalações que já rodam, onde as formas foram
        # criadas antes de o código existir.
        for forma in db.query(FormaPagamento).filter(
            (FormaPagamento.codigo_sefaz == None) | (FormaPagamento.codigo_sefaz == "")  # noqa: E711
        ).all():
            codigo = _CODIGO_SEFAZ_PADRAO.get((forma.nome or "").strip().lower())
            if codigo:
                forma.codigo_sefaz = codigo
                logger.info("Código SEFAZ %s atribuído a '%s'.", codigo, forma.nome)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Erro ao criar formas de pagamento padrão")
    finally:
        db.close()


def _seed_contador_venda():
    """Inicializa o contador de vendas com o registro único (id=1) se não existir."""
    db = SessionLocal()
    try:
        existe = db.query(ContadorVenda).first()
        if not existe:
            db.add(ContadorVenda(id=1, proximo_numero=1))
            db.commit()
            logger.info("Contador de vendas inicializado.")
    except Exception:
        db.rollback()
        logger.exception("Erro ao inicializar contador de vendas")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador de ciclo de vida do FastAPI.
    Inicia tarefas em segundo plano ao iniciar e cancela ao encerrar.
    """
    # PRIMEIRA COISA DO BOOT, antes de create_all/migracoes: a restauracao troca
    # o ARQUIVO do banco no disco. Se rodasse depois, o create_all abriria o
    # banco antigo e as migracoes seriam aplicadas no arquivo que esta prestes a
    # ser substituido. So faz algo se houver um marcador pendente confirmado.
    try:
        result = apply_pending_restore()
        if result:
            print(f"[RESTORE] Restauração aplicada no boot: "
                  f"ciclo {result['restored_cycle']}. "
                  f"Cópia de segurança em {result.get('old_db')}")
            print(f"[RESTORE] Licença: {result.get('license')}")
    except Exception as e:
        print(f"[RESTORE] Erro ao aplicar restauração pendente: {type(e).__name__}: {e}")

    try:
        await asyncio.to_thread(limpar_snapshots_antigos)
    except Exception as e:
        print(f"[LIMPEZA] Erro ao limpar snapshots antigos: {type(e).__name__}: {e}")

    await asyncio.to_thread(limpar_temp_data)

    # create_all CONTINUA AQUI. A versao do master removeu esta linha porque la
    # o Alembic tem um baseline unico que cria o schema inteiro; nesta branch a
    # cadeia de migracoes pressupoe que o create_all rodou antes (ver
    # db/migrations.py e CLAUDE.md). Remover isto deixaria banco novo sem tabelas.
    Base.metadata.create_all(bind=engine)

    # Limpar terminais conectados da sessão anterior (stale após restart)
    db = SessionLocal()
    try:
        terminal_crud.limpar_todos_terminais(db)
        db.commit()
        logger.info("Terminais conectados da sessão anterior limpos.")
    finally:
        db.close()

    aplicar_migracoes()
    _seed_formas_pagamento()
    _seed_contador_venda()
    print("Iniciando tarefa de baixa automatica de recebimentos...")
    tarefa_baixa_automatica = asyncio.create_task(_loop_baixa_automatica())

    print("Iniciando tarefa de limpeza automatica temporal...")
    tarefa_limpeza = asyncio.create_task(_loop_limpeza_temporal())

    print("Iniciando tarefa de backup automático...")
    tarefa_backup = asyncio.create_task(_loop_backup())

    print("Iniciando tarefa de sincronização com nuvem automático...")
    tarefa_cloud_sync = asyncio.create_task(_loop_cloud_sync())

    print("Iniciando tarefa de heartbeat de licenca...")
    tarefa_heartbeat = asyncio.create_task(_loop_heartbeat_licenca())

    print("Iniciando tarefa de renovação de licença...")
    tarefa_renovacao = asyncio.create_task(_loop_renovacao_licenca())

    host = os.getenv("STARTBIG_HOST", "0.0.0.0")
    port = int(os.getenv("STARTBIG_PORT", "8080"))
    
    print(f"Iniciando mDNS em {host}:{port}")
    
    await asyncio.to_thread(register_service, host, port)

    yield

    print("Encerrando mDNS...")
    await asyncio.to_thread(stop_discovery)
    
    print("Encerrando tarefas em segundo plano...")
    tarefa_baixa_automatica.cancel()
    tarefa_limpeza.cancel()
    tarefa_backup.cancel()
    tarefa_cloud_sync.cancel()
    tarefa_heartbeat.cancel()
    tarefa_renovacao.cancel()
    for tarefa in (tarefa_baixa_automatica, tarefa_limpeza, tarefa_backup,
                   tarefa_cloud_sync, tarefa_heartbeat, tarefa_renovacao):
        try:
            await tarefa
        except asyncio.CancelledError:
            pass

    # Desconectar todos os terminais na API externa antes de encerrar
    print("Desconectando terminais na API externa...")
    db = SessionLocal()
    try:
        terminais = terminal_crud.get_todos_terminais(db)
        for terminal in terminais:
            await desconectar_terminal(db, terminal.hwid)
        terminal_crud.limpar_todos_terminais(db)
        db.commit()
        print(f"Todos os {len(terminais)} terminais desconectados.")
    except Exception:
        print("Erro ao desconectar terminais no shutdown.")
    finally:
        db.close()
