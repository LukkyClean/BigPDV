import os
import sys
import glob
import shutil
import tempfile
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import limite_utc_ha
from app.core.enum import VendaStatus
from app.db.models.venda import Venda
from app.db.models.orcamento import Orcamento

logger = logging.getLogger(__name__)

DIAS_EXPIRACAO_VENDA_ATIVA = 3
DIAS_EXPIRACAO_ORCAMENTO = 7


def cancelar_vendas_ativas_expiradas(db: Session) -> int:
    """
    Deleta vendas ATIVAS (rascunhos) que nao foram atualizadas nos ultimos
    DIAS_EXPIRACAO_VENDA_ATIVA dias. Retorna a quantidade deletada.
    """
    # A coluna comparada e gravada em UTC pelo banco; usar o relogio local
    # aqui adiantaria ou atrasaria a expiracao pelo tamanho do fuso.
    limite = limite_utc_ha(dias=DIAS_EXPIRACAO_VENDA_ATIVA)

    stmt = select(Venda).where(
        Venda.status == VendaStatus.ATIVA,
        Venda.atualizado_em < limite,
    )
    vendas_expiradas = db.scalars(stmt).all()
    quantidade = len(vendas_expiradas)

    for venda in vendas_expiradas:
        db.delete(venda)

    if quantidade > 0:
        db.commit()
        logger.info(
            "Limpeza automatica: %d rascunho(s) de venda deletado(s) (anterior a %s)",
            quantidade,
            limite.isoformat(),
        )
    else:
        logger.debug("Limpeza automatica: nenhuma venda ativa expirada encontrada.")

    return quantidade


def limpar_orcamentos_expirados(db: Session) -> int:
    """
    Remove orcamentos nao convertidos que nao foram atualizados nos ultimos
    DIAS_EXPIRACAO_ORCAMENTO dias. Retorna a quantidade removida.
    """
    limite = limite_utc_ha(dias=DIAS_EXPIRACAO_ORCAMENTO)

    stmt = select(Orcamento).where(
        Orcamento.convertido == False,
        Orcamento.atualizado_em < limite,
    )
    orcamentos_expirados = db.scalars(stmt).all()
    quantidade = len(orcamentos_expirados)

    for orcamento in orcamentos_expirados:
        db.delete(orcamento)

    if quantidade > 0:
        db.commit()
        logger.info(
            "Limpeza automatica: %d orcamento(s) removido(s) (anterior a %s)",
            quantidade,
            limite.isoformat(),
        )
    else:
        logger.debug("Limpeza automatica: nenhum orcamento expirado encontrado.")

    return quantidade

def limpar_temp_data(): 
    temp_dir = tempfile.gettempdir()
    
    q_pattern = os.path.join(temp_dir, "_MEI*")
    pastas_encontradas = glob.glob(q_pattern)
    
    acc_temp_dir = getattr(sys, "_MEIPASS", None)
    
    for pasta in pastas_encontradas:
        if os.path.isdir(pasta) and pasta != acc_temp_dir:
            try:
                shutil.rmtree(pasta)
                logger.info("Limpeza automática: diretório temporário removido: %s", pasta)
            except Exception as e:
                logger.error("Erro ao remover diretório temporário %s: %s", pasta, str(e))