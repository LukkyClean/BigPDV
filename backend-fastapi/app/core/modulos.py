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


# Módulos que NÃO seguem a regra "sem resposta, libera".
#
# A regra geral (ver `modulo_dependency`) existe para proteger acesso que o
# cliente JÁ TINHA: token velho sem a claim, rede fora, ou a plataforma que
# ainda não cadastrou módulo nenhum. Nesses casos negar tiraria do ar um
# recurso que estava funcionando, sem mensagem de erro nenhuma.
#
# NFE não tem esse risco: é recurso NOVO, ninguém em campo tem acesso a ele
# hoje, então não há nada a proteger. E o custo de errar é assimétrico —
# liberar por engano deixaria qualquer loja emitir documento fiscal em nome
# dela na SEFAZ. Aqui, "não sei" significa NÃO.
#
# Para conceder: a plataforma inclui "NFE" na lista de módulos da licença,
# por plano ou por cliente.
MODULOS_NEGADOS_SEM_RESPOSTA = frozenset({"NFE"})


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

        # Vazio ou None = "não sei", e não saber LIBERA.
        #
        # None é token sem a claim, ou sem como conferir a assinatura: a estreia
        # desta trava tiraria o sistema de quem paga, por até uma semana,
        # enquanto os tokens antigos não expiram.
        #
        # Lista vazia entra aqui pelo mesmo motivo, e este é o caso comum hoje:
        # a plataforma emite a claim mas ainda não cadastrou módulo nenhum, então
        # TODA licença em campo chega com `[]`. Bloquear nesse caso recusaria a
        # rota para 100% dos clientes -- inclusive os que pagaram -- por falta de
        # configuração do lado de lá, não por decisão comercial.
        #
        # A trava morde quando a lista vem PREENCHIDA e o identificador não está
        # nela: aí a plataforma falou, e falou que esta loja não tem.
        # ... com a exceção de MODULOS_NEGADOS_SEM_RESPOSTA, para quem "não
        # sei" significa NÃO. Ver o comentário da constante no topo.
        if not modulos:
            if identificador in MODULOS_NEGADOS_SEM_RESPOSTA:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "codigo": "MODULO_NAO_CONTRATADO",
                        "mensagem": (
                            f"Este recurso faz parte do módulo {identificador}, "
                            "que não está liberado para esta licença."
                        ),
                        "modulo": identificador,
                    },
                )
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
