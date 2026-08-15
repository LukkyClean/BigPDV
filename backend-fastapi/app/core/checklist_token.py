# ---------------------------------------------------------------------------
# ARQUIVO: app/core/checklist_token.py
# DESCRICAO: Gera e valida tokens HMAC para acesso publico ao checklist
#            mobile. O token e auto-contido (nao precisa de tabela): codifica
#            o numero da OS + timestamp de expiracao, assinados com SECRET_KEY.
# ---------------------------------------------------------------------------

import base64
import hashlib
import hmac
import time

from app.core.config import settings


def _sign(payload: str) -> str:
    """Gera HMAC-SHA256 do payload usando SECRET_KEY."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def gerar_token_checklist(numero_os: str, ttl_minutos: int = 480) -> str:
    """Gera token URL-safe para acesso ao checklist de uma OS.

    Formato: {base64(numero_os:expiry_ts)}.{hmac_signature}
    TTL padrao: 480 min (8h — jornada de trabalho).
    """
    expiry = int(time.time()) + (ttl_minutos * 60)
    payload = f"{numero_os}:{expiry}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    signature = _sign(payload)
    return f"{encoded}.{signature}"


def validar_token_checklist(token: str, numero_os: str) -> bool:
    """Valida token HMAC e verifica expiracao e numero da OS."""
    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return False

        encoded, signature = parts
        payload = base64.urlsafe_b64decode(encoded).decode()

        # Verifica assinatura (constant-time comparison)
        if not hmac.compare_digest(signature, _sign(payload)):
            return False

        # Extrai numero_os e expiry do payload
        token_os, expiry_str = payload.rsplit(":", 1)
        expiry = int(expiry_str)

        # Verifica se o token pertence a esta OS
        if token_os != numero_os:
            return False

        # Verifica expiracao
        if time.time() > expiry:
            return False

        return True
    except Exception:
        return False
