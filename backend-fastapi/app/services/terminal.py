# ---------------------------------------------------------------------------
# ARQUIVO: services/terminal.py
# DESCRIÇÃO: Regras do cadastro durável de terminais (nome e papel por máquina).
# ---------------------------------------------------------------------------

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.depends import is_visao_gerencial
from app.helpers.exceptions import BadRequestException, NotFoundException
from app.db.crud import terminal as terminal_crud
from app.db.models.terminal import Terminal
from app.schemas.terminal import TerminalEsteRead, TerminalRead, TerminalUpdate


# Papel ausente e papel 'PDV' são a mesma coisa. Escrito uma vez, aqui, para que
# a resposta não dependa de quem perguntou.
def e_retaguarda(terminal: Optional[Terminal]) -> bool:
    """Só o papel RETAGUARDA explícito dispensa a máquina de ser caixa.

    NULL e 'PDV' cobram turno. A assimetria é deliberada: errar para "cobra
    turno demais" custa um clique de configuração; errar para "não cobra" custa
    o controle da gaveta — e falha em silêncio, porque nada quebra na hora, o
    dinheiro só não bate no fim do dia.
    """
    return bool(terminal and terminal.papel == "RETAGUARDA")


def garantir_terminal(db: Session, empresa_id: int, hwid: str) -> Optional[Terminal]:
    """Registra a máquina no primeiro login, e não faz mais nada depois.

    Chamada no login, junto de `conectar_terminal`. A diferença entre as duas é
    o tempo de vida: aquela marca presença (e some no logout), esta cria o
    cadastro que sobrevive.

    NÃO SOBRESCREVE nome nem papel de terminal já conhecido. O login acontece
    todo dia; se ele reescrevesse o cadastro, a configuração do dono duraria até
    o próximo café.

    Falhar aqui não pode derrubar o login: quem chega para trabalhar às 8h da
    manhã não pode ficar de fora porque o cadastro de uma máquina não gravou.
    """
    hwid_limpo = (hwid or "").strip()
    if not hwid_limpo or not empresa_id:
        return None

    existente = terminal_crud.get_por_hwid(db, hwid_limpo)
    if existente:
        return existente

    return terminal_crud.criar(
        db, Terminal(empresa_id=empresa_id, hwid=hwid_limpo)
    )


def listar(db: Session, usuario_token: Dict[str, Any]) -> List[TerminalRead]:
    """As máquinas da loja.

    VISÃO GERENCIAL APENAS. Saber quais terminais existem e quem é retaguarda é
    informação de dono — a mesma régua do histórico de caixas, pela mesma razão.
    """
    if not is_visao_gerencial(usuario_token):
        raise BadRequestException(
            detail="Apenas o responsável pela loja pode ver os terminais"
        )
    return [
        TerminalRead.model_validate(t)
        for t in terminal_crud.listar(db, usuario_token["empresa_id"])
    ]


def garantir_e_listar(
    db: Session, usuario_token: Dict[str, Any], hwid: Optional[str]
) -> List[TerminalRead]:
    """A lista, com a máquina de quem está pedindo garantida dentro dela.

    O dono abre a tela de Terminais a partir de algum computador — e o mínimo
    que ela precisa mostrar é aquele. Sem isto, a primeira visita podia mostrar
    uma lista vazia justamente para quem estava lá para configurar.
    """
    if (hwid or "").strip():
        garantir_terminal(db, usuario_token["empresa_id"], hwid)
    return listar(db, usuario_token)


def get_este_terminal(
    db: Session, usuario_token: Dict[str, Any], hwid: Optional[str]
) -> Optional[TerminalEsteRead]:
    """Quem é ESTA máquina — pergunta que qualquer operador pode fazer.

    Sem visão gerencial de propósito: a tela de vendas precisa saber se está num
    caixa ou na retaguarda para decidir se convida a abrir turno, e quem está no
    balcão não é gerente. A resposta não expõe as outras máquinas da loja.
    """
    hwid_limpo = (hwid or "").strip()
    if not hwid_limpo:
        return None

    terminal = terminal_crud.get_por_hwid(db, hwid_limpo)

    # SÓ LÊ, nunca cria. O HWID chega por header, e header é texto que o cliente
    # escolhe — se esta consulta cadastrasse, qualquer valor inventado viraria
    # uma linha e a lista do dono encheria de máquinas que não existem. Quem
    # cadastra é o login (com o HWID autenticado) e a tela de Terminais (ação
    # deliberada de quem administra a loja).
    #
    # Máquina desconhecida devolve `None`, e a tela trata isso como "sou um
    # caixa" — o lado seguro.
    if not terminal or terminal.empresa_id != usuario_token["empresa_id"]:
        return None

    return TerminalEsteRead(
        **TerminalRead.model_validate(terminal).model_dump(),
        e_retaguarda=e_retaguarda(terminal),
    )


def atualizar(
    db: Session,
    usuario_token: Dict[str, Any],
    terminal_id: int,
    dados: TerminalUpdate,
) -> TerminalRead:
    """Batiza a máquina e define o papel dela."""
    if not is_visao_gerencial(usuario_token):
        raise BadRequestException(
            detail="Apenas o responsável pela loja pode configurar terminais"
        )

    terminal = terminal_crud.get_por_id(db, terminal_id, usuario_token["empresa_id"])
    if not terminal:
        raise NotFoundException(detail="Terminal não encontrado")

    # `exclude_unset` para que não mandar o campo signifique "não mexer", e
    # mandar `null` signifique "limpar". Sem isso, salvar só o nome apagaria o
    # papel junto — e apagar papel devolve a máquina para a regra de caixa sem
    # ninguém ter pedido.
    mudancas = dados.model_dump(exclude_unset=True)
    if "nome" in mudancas:
        terminal.nome = mudancas["nome"]
    if "papel" in mudancas:
        terminal.papel = mudancas["papel"]

    db.flush()
    db.refresh(terminal)
    return TerminalRead.model_validate(terminal)
