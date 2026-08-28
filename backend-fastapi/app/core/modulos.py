# ---------------------------------------------------------------------------
# ARQUIVO: core/modulos.py
# MÓDULO: CORE/GERAL
# DESCRIÇÃO: Trava de acesso por módulo contratado, lida do JWT da licença.
# ---------------------------------------------------------------------------
"""
Cada licença enxerga um conjunto de módulos, e a lista viaja dentro do JWT
assinado que a plataforma emite. Este arquivo é o lado do ERP dessa trava.

POR QUE TAMBÉM AQUI, SE O MENU JÁ ESCONDE: esconder item de menu é cortesia,
não controle. O backend do ERP escuta numa porta da máquina, e quem quiser
chamar a rota direto não passa pelo menu. Módulo de verdade se trava onde o
dado mora.

Sobre esconder do usuário: as rotas que dependem de módulo respondem 403 com
`MODULO_NAO_CONTRATADO`, e não 404. O dono da loja precisa entender que o
recurso existe e não está contratado -- sumir com ele vira chamado de suporte
com "o sistema quebrou".
"""

from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import licenca as licenca_service


def requer_modulo(identificador: str) -> Callable:
    """
    Factory de dependência que exige um módulo contratado na licença.

    Uso:
        @router.get("/contas", dependencies=[Depends(requer_modulo("FINANCEIRO"))])

    Args:
        identificador: chave técnica do módulo, igual à que a plataforma emite
            no JWT (ex.: "NFE", "FINANCEIRO"). É IMUTÁVEL do lado de lá --
            renomear invalidaria todo token em campo por até 7 dias.

    Returns:
        Callable: dependência que levanta 403 quando o módulo não está liberado.
    """

    def modulo_dependency(db: Session = Depends(get_db)) -> None:
        modulos = licenca_service.modulos_da_licenca(db)

        # None = token sem a claim, ou sem como conferir a assinatura. Não é
        # "nenhum módulo", é "não sei" -- e não saber libera, senão a estreia
        # desta trava tiraria o sistema de quem paga, por até uma semana,
        # enquanto os tokens antigos não expiram.
        if modulos is None:
            return

        if identificador in modulos:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "MODULO_NAO_CONTRATADO",
                "mensagem": (
                    f"Este recurso faz parte do módulo {identificador}, "
                    "que não está incluído no seu plano. Fale com o suporte para contratá-lo."
                ),
                "modulo": identificador,
            },
        )

    return modulo_dependency
