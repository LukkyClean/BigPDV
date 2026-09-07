# ---------------------------------------------------------------------------
# ARQUIVO: app/services/plano.py
# DESCRIÇÃO: Ponto ÚNICO do backend que decide se um recurso do plano está
#            contratado. Quando a API de billing existir, só este arquivo muda.
# ---------------------------------------------------------------------------
"""
Direito de uso por recurso contratado.

QUAL É A BARREIRA DE VERDADE
----------------------------
Não é esta. Quem recusa emissão de cliente sem plano é a API remota
(`api.startbig.com.br`), que recebe o JWT da licença como Bearer em
`emissao.py` e roda fora da máquina do cliente — a única camada que um
lojista não consegue adulterar.

Esta camada local é DEFESA EM PROFUNDIDADE e, principalmente, UX: serve para
não mostrar telas que não vão funcionar e para falhar cedo, com uma mensagem
clara, em vez de falhar fundo dentro do fluxo de emissão.

Isso tem uma consequência de projeto que vale registrar: como a barreira real
é remota, a flag local NÃO precisa ser à prova de adulteração. Se alguém
ligar `modulo_fiscal_ativo` direto no banco, consegue ver a tela e continua
sem emitir nota. Endurecer isso localmente não compraria segurança nenhuma e
custaria uma ligação de suporte a cada cliente novo — por isso a ativação é
deliberadamente simples.
"""
import logging
from typing import Any, Dict, Optional

from jose import JOSEError, JWTError, jwt
from sqlalchemy.orm import Session

from app.db.crud import fiscal as fiscal_crud
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings

logger = logging.getLogger(__name__)


# Recursos conhecidos. O nome bate com o `Recurso` do frontend
# (shared/config/planos.ts), de propósito: é o mesmo vocabulário nas duas pontas.
RECURSO_NFE = "nfe"


def _recursos_do_token(db: Session) -> Optional[Dict[str, Any]]:
    """
    Lê o claim `recursos` do JWT da licença, se ele existir.

    O token é assinado em RS256 pelo servidor de licenças, então este claim é a
    fonte NÃO FORJÁVEL — é para cá que a decisão migra quando o billing passar
    a emiti-lo. Enquanto o servidor não mandar `recursos`, devolve None e o
    chamador cai na flag local.

    Decodifica SEM verificar assinatura de propósito: a validação criptográfica
    da licença já acontece em `services/licenca.py`, no ciclo de heartbeat e
    grace period, e é ela que derruba um token adulterado. Repetir a verificação
    aqui exigiria descriptografar a chave pública a cada request para uma
    decisão que, sozinha, não é a barreira de receita (ver docstring do módulo).
    """
    try:
        token = fiscal_crud.get_licenca_token(db)
    except Exception:
        return None

    if not token:
        return None

    try:
        claims = jwt.get_unverified_claims(token)
    except (JWTError, JOSEError):
        return None

    recursos = claims.get("recursos")
    return recursos if isinstance(recursos, dict) else None


def plano_tem_recurso(db: Session, recurso: str, empresa_id: Optional[int] = None) -> bool:
    """
    Único ponto do backend que decide se um recurso do plano está contratado.

    Ordem de resolução:
      1. Claim `recursos` no JWT da licença — quando existir, manda.
      2. Flag local `empresa_fiscal_settings.modulo_fiscal_ativo`.
      3. False.

    Args:
        db: Sessão SQLAlchemy.
        recurso: Nome do recurso (ex.: "nfe").
        empresa_id: Empresa a consultar na etapa 2. Sem ela, só o token decide.

    Returns:
        True se o recurso está contratado.
    """
    recursos = _recursos_do_token(db)
    if recursos is not None and recurso in recursos:
        return bool(recursos[recurso])

    if recurso != RECURSO_NFE or empresa_id is None:
        return False

    settings = (
        db.query(EmpresaFiscalSettings)
        .filter(EmpresaFiscalSettings.empresa_id == empresa_id)
        .first()
    )
    return bool(settings and settings.modulo_fiscal_ativo)


def ativar_recurso_local(db: Session, empresa_id: int, recurso: str = RECURSO_NFE) -> bool:
    """
    Liga a flag local de um recurso, criando a configuração fiscal se preciso.

    Existe para o onboarding: sem isto, um cliente que acabou de contratar o
    módulo não teria caminho nenhum pela aplicação — a configuração fiscal
    também depende do direito, e nada mais escreveria a flag.

    Vira desnecessário no dia em que o servidor de licenças passar a mandar o
    claim `recursos`: aí a etapa 1 de `plano_tem_recurso` responde sozinha.
    """
    if recurso != RECURSO_NFE:
        raise ValueError(f"Recurso desconhecido: {recurso!r}")

    settings = (
        db.query(EmpresaFiscalSettings)
        .filter(EmpresaFiscalSettings.empresa_id == empresa_id)
        .first()
    )
    if settings is None:
        settings = EmpresaFiscalSettings(empresa_id=empresa_id)
        db.add(settings)

    settings.modulo_fiscal_ativo = True
    db.flush()
    logger.info("[plano] Módulo fiscal ativado para a empresa %s.", empresa_id)
    return True
