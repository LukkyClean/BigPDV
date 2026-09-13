import os
import re

from app.core.config import BASE_DIR, database_path

# Os caminhos ficam sob BASE_DIR (e nao sob data_dir) de proposito: `static` e
# escrito por core/imagem.py como BASE_DIR/static/uploads/... e servido pelo
# mount de main.py. Mover a pasta sem mover quem escreve nela faria todo upload
# novo (foto de produto, logo, foto de OS) cair fora do que e servido, e o
# faxineiro de diretorios apagaria a origem no boot seguinte.
LOCAL_BACKUP = os.path.join(BASE_DIR, "backups")
RESTORE_BACKUPS = os.path.join(BASE_DIR, "restore_backups")
STATIC_DIR = os.path.join(BASE_DIR, "static")
OLD_DIR = os.path.join(BASE_DIR, "old")
DATA_DIR = os.path.dirname(database_path)

# Os XMLs autorizados, gravados por `services/fiscal/arquivos.py`.
#
# Ficam sob `data/` (ao lado do banco) e NÃO sob `static/`, porque `static` é
# servida por HTTP sem autenticação para a LAN inteira — é de onde saem foto de
# produto e logo. Documento fiscal não vai para lá.
#
# Como consequência dessa escolha, eles precisavam ser incluídos aqui à mão: o
# backup levava só o arquivo do banco e a árvore de `static`. Guardar o XML por
# cinco anos é obrigação do emitente, e obrigação fora do backup é o tipo de
# coisa que só se descobre quando já era.
FISCAL_DIR = os.path.join(DATA_DIR, "fiscal")
FISCAL_DIR_NO_ZIP = "fiscal"

# O DANFE SOBE — mas cede lugar quando o pacote fica grande demais.
#
# A primeira versão o deixava sempre de fora, com o argumento de que é
# "derivado do XML e pode ser regerado". O argumento é fraco: este sistema NÃO
# tem gerador de DANFE, então quem perder o PDF depende de ferramenta de
# terceiro para ver a nota. Numa loja pequena (30 notas/mês, ~2 MB de PDF por
# ano) excluí-lo era perder conveniência sem ganhar nada.
#
# O que é real, e vale a trava:
#   - o ZIP inteiro é lido em MEMÓRIA antes de subir (cloud/upload.py)
#   - o timeout de escrita é 600s: a 1 Mbps de upload dá ~75 MB
#   - backup COMPLETO reenvia tudo a cada 7 dias, não uma vez
#
# Daí a regra: o XML (obrigação legal de cinco anos) sobe sempre; o DANFE
# (conveniência) é pulado quando sua pasta passa deste teto, com aviso no log.
# A loja perde a comodidade, nunca o documento.
FISCAL_DANFE_SUBPASTA = "danfe"
FISCAL_DANFE_TETO_BYTES = 100 * 1024 * 1024  # 100 MB

FULL_TO_SAVE = 4
MIN_DAYS_TO_COMPLETE_SAVE = 7

BACKUP_PREFIX = "backup_"
PRE_RESTORE_PREFIX = "pre_restore_"
BACKUP_SUFFIX = "(_full|_incr)?"
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"

BACKUP_FILENAME_REGEX = re.compile(
    rf"^{BACKUP_PREFIX}(\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}}){BACKUP_SUFFIX}\.zip$"
)
PRE_RESTORE_FILENAME_REGEX = re.compile(
    rf"^{PRE_RESTORE_PREFIX}(\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}})_(\d{{4}}-\d{{2}}-\d{{2}})\.zip$"
)

MANIFEST_FILENAME = "manifest.json"
STATIC_DIR_NO_ZIP = "static"

MARKER_RESTORE_FILENAME = "restore_pendente.json"
MARKER_RESTORE_PATH = os.path.join(BASE_DIR, MARKER_RESTORE_FILENAME)

OLD_SUFFIX = ".old"
INTEGRITY_CHECK_OK = "ok"


class BackupError(Exception):
    pass
