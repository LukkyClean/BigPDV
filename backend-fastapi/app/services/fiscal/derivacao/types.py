# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/derivacao/types.py
# DESCRIÇÃO: Contrato da camada de derivação — DTOs puros, sem ORM.
# ---------------------------------------------------------------------------
"""
Tipos da derivação fiscal.

A regra central deste módulo: **nunca devolver valor cru**. Toda sugestão vem
com procedência, confiança e fundamentação, porque quem consome precisa saber
a diferença entre "o sistema deduziu" e "o contador decidiu" — e porque uma
sugestão sem explicação, num campo tributário, é pior que campo vazio.
"""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TipoAtividade(str, Enum):
    """Espelha `empresas.tipo_atividade`, que já existe no cadastro."""

    COMERCIO = "COMERCIO"
    INDUSTRIA = "INDUSTRIA"
    SERVICO = "SERVICO"
    MISTO = "MISTO"


class Fonte(str, Enum):
    """De onde a sugestão saiu."""

    DERIVADO = "derivado"          # regra pura sobre dados já no banco
    DEFAULT_REGIME = "default_regime"  # padrão do CRT / regime de apuração
    DEFAULT_UF = "default_uf"      # tabela aliquota_uf
    BASE_NCM = "base_ncm"          # tabela externa por NCM (Fase 6)
    BASE_CEST = "base_cest"        # Convênio 142/2018 (Fase 6)


class Confianca(str, Enum):
    """
    Quanto o sistema aposta na sugestão.

    `AMBIGUA` não é "provavelmente errado": é "há mais de uma resposta válida
    e só o usuário sabe qual". Nesse caso `alternativas` vem preenchida e a UI
    deve exigir escolha em vez de preencher.
    """

    CERTA = "certa"
    PROVAVEL = "provavel"
    AMBIGUA = "ambigua"


class CampoSugerido(BaseModel):
    """Uma sugestão para um campo fiscal."""

    campo: str = Field(..., description="Nome do campo, como no ProdutoFiscal")
    valor: Optional[str] = Field(None, description="Valor sugerido, sempre como texto")
    fonte: Fonte
    confianca: Confianca
    fundamentacao: str = Field(
        ...,
        description=(
            "Por que este valor. Vai para a tela, no 'por quê?' ao lado do "
            "campo — é o que permite ao contador discordar com base."
        ),
    )
    alternativas: list[tuple[str, str]] = Field(
        default_factory=list,
        description="(valor, descrição) quando a confiança é AMBIGUA",
    )
    exige_confirmacao: bool = Field(
        False,
        description=(
            "Bloqueia auto-aplicação. Ligado onde errar produz nota ACEITA E "
            "ERRADA — pior desfecho possível, porque só aparece na fiscalização."
        ),
    )


class ContextoDerivacao(BaseModel):
    """
    Tudo que as regras precisam saber, já extraído do banco.

    Existe para manter as regras puras: `resolver_db` monta isto a partir do
    ORM, e daqui para baixo ninguém mais toca em Session.
    """

    uf_emitente: str
    crt: int
    tipo_atividade: Optional[TipoAtividade] = None
    # Reservado para quando a operação interestadual sair do bloqueio.
    uf_destinatario: Optional[str] = None
    indicador_presenca: Optional[int] = None
    modelo_documento: Literal[55, 65] = 55
    finalidade_emissao: int = 1
    destinatario_pj_com_ie: bool = False
