# ---------------------------------------------------------------------------
# ARQUIVO: app/core/security.py
# DESCRIÇÃO: Utilitários de criptografia (Passlib/Bcrypt) e Tokenização (JWT).
# ---------------------------------------------------------------------------

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import bcrypt
from fastapi import HTTPException, status
from jose import jwt, JWTError

from cryptography.fernet import Fernet

from app.core.config import settings

# =========================
# Configuração Fernet - Certificados
# =========================

_fernet_instance = Fernet(settings.FERNET_KEY)

def encrypt_data(plain_text: str) -> str:
    return _fernet_instance.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_data(encrypted_text: str) -> str:
    return _fernet_instance.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')

# =========================
# Hash de Senha
# =========================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Valida a senha informada contra o hash do banco."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def hash_password(password: str) -> str:
    """Gera o hash da senha (bcrypt com salt automático)."""
    hashed = bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt(rounds=12)
    )
    return hashed.decode('utf-8')

# =========================
# Tokens JWT
# =========================

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Gera o JWT. Aceita dados complexos (Bool, Int, Dict) no payload.
    """
    to_encode = data.copy()
    
    # Adiciona metadados do token
    to_encode.update({
        "jti": str(uuid.uuid4()), # ID único do token (para revogação)
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    })

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token_data(token: str) -> Dict[str, Any]:
    """
    Decodifica e valida o JWT. Retorna os dados originais (preservando tipos).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        if payload.get("sub") is None:
            raise credentials_exception
            
        return payload
    except JWTError:
        raise credentials_exception