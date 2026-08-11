import logging
import os
import shutil

from app.core.config import BASE_DIR, DB_NAME, data_dir, database_path

logger = logging.getLogger(__name__)


def migrar_estrutura_diretorios() -> None:
    """
    Migra pastas da raiz de BASE_DIR para dentro de data_dir.
    Idempotente: só age se a origem existir; pula se o destino já tem conteúdo.
    """
    migracoes = [
        (os.path.join(BASE_DIR, "static"),          os.path.join(data_dir, "static")),
        (os.path.join(BASE_DIR, "backups"),         os.path.join(data_dir, "backup")),
        (os.path.join(BASE_DIR, "restore_backups"), os.path.join(data_dir, "backup", "restore")),
    ]

    for origem, destino in migracoes:
        if not os.path.exists(origem):
            continue  # já migrado ou nunca existiu

        os.makedirs(os.path.dirname(destino), exist_ok=True)

        if not os.path.exists(destino):
            # Caso simples: destino não existe → mover diretamente
            shutil.move(origem, destino)
            logger.info("[MIGRACAO] %s → %s", origem, destino)
        elif not os.listdir(destino):
            # Destino existe mas está vazio (criado em boot anterior) → substituir
            tmp = destino + "_tmp"
            shutil.move(origem, tmp)
            os.rmdir(destino)
            os.rename(tmp, destino)
            logger.info("[MIGRACAO] (substituicao) %s → %s", origem, destino)
        else:
            # Destino já tem conteúdo: origem é resíduo — remover com segurança
            logger.warning(
                "[MIGRACAO] Destino '%s' já existe com conteúdo. "
                "Removendo origem residual '%s'.",
                destino, origem,
            )
            shutil.rmtree(origem, ignore_errors=True)

    # Migra arquivos .old soltos (gerados por restores antigos) para data/old/migrado/
    _old_db = database_path + ".old"
    _old_static = os.path.join(data_dir, "static.old")
    if os.path.exists(_old_db) or os.path.exists(_old_static):
        _migrado = os.path.join(data_dir, "old", "migrado")
        os.makedirs(_migrado, exist_ok=True)
        if os.path.exists(_old_db):
            shutil.move(_old_db, os.path.join(_migrado, DB_NAME))
            logger.info("[MIGRACAO] %s → %s", _old_db, _migrado)
        if os.path.exists(_old_static):
            shutil.move(_old_static, os.path.join(_migrado, "static"))
            logger.info("[MIGRACAO] %s → %s", _old_static, _migrado)
