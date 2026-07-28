import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.base import Base
from app.db.migrations import aplicar_migracoes
from app.db.session import SessionLocal, engine
from app.db.models.contador_venda import ContadorVenda
from app.db.models.forma_pagamento import FormaPagamento
from app.services.limpeza_temporal import cancelar_vendas_ativas_expiradas, limpar_orcamentos_expirados, limpar_temp_data
from app.services.licenca import enviar_heartbeat, renovar_licenca_background, desconectar_terminal
from app.db.crud import terminal_conectado as terminal_crud

from app.core.discovery import register_service, stop_discovery

logger = logging.getLogger(__name__)

INTERVALO_LIMPEZA_HORAS = 6
INTERVALO_HEARTBEAT_SEGUNDOS = 100  # 5 minutos
INTERVALO_RENOVACAO_SEGUNDOS = 3600  # 1 hora


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


_FORMAS_PAGAMENTO_PADRAO = [
    "Dinheiro",
    "PIX",
    "Cartão de Crédito",
    "Cartão de Débito",
    "Transferência Bancária",
    "Boleto",
]


def _seed_formas_pagamento():
    """Insere formas de pagamento padrão caso a tabela esteja vazia ou faltem registros."""
    db = SessionLocal()
    try:
        for nome in _FORMAS_PAGAMENTO_PADRAO:
            existe = db.query(FormaPagamento).filter(FormaPagamento.nome.ilike(nome)).first()
            if not existe:
                db.add(FormaPagamento(nome=nome, ativo=True))
                logger.info("Forma de pagamento criada: %s", nome)
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
    await asyncio.to_thread(limpar_temp_data)

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
    print("Iniciando tarefa de limpeza automatica temporal...")
    tarefa_limpeza = asyncio.create_task(_loop_limpeza_temporal())

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
    tarefa_limpeza.cancel()
    tarefa_heartbeat.cancel()
    tarefa_renovacao.cancel()
    for tarefa in (tarefa_limpeza, tarefa_heartbeat, tarefa_renovacao):
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
