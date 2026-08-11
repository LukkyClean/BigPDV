import httpx

API_BASE = "https://api.startbig.com.br"
API_BACKUP_STATUS_URL = f"{API_BASE}/erp/backup/status"
API_BACKUP_URL_UPLOAD = f"{API_BASE}/erp/backup/url-upload"
API_BACKUP_CONFIRMAR = f"{API_BASE}/erp/backup/confirmar"
API_BACKUP_DOWNLOAD = f"{API_BASE}/erp/backup/url-download"

API_TIMEOUT = httpx.Timeout(connect=10.0, read=15.0, write=15.0, pool=5.0)
# read/write generosos: o PUT sobe zips que podem ter centenas de MB.
PUT_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=600.0, pool=5.0)
GET_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=15.0, pool=5.0)
