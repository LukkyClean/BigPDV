# ---------------------------------------------------------------------------
# ARQUIVO: app/core/segmentos/campos.py
# DESCRICAO: Vocabulario de construcao das definicoes (motor). Sao os tijolos
#            que os arquivos de `definicoes/` usam para se declarar.
# ---------------------------------------------------------------------------

from typing import Any, Dict, List, Optional


def campo(
    nome: str,
    label: str,
    tipo: str,
    obrigatorio: bool = False,
    opcoes: Optional[List[str]] = None,
    escopo: str = "objeto",
) -> Dict[str, Any]:
    """Descreve um campo dinamico.

    tipo: 'texto' | 'numero' | 'inteiro' | 'opcao' | 'booleano'
    escopo: 'objeto' (dados do veiculo) | 'os' (dados da OS/check-in)
    """
    resultado: Dict[str, Any] = {
        "nome": nome,
        "label": label,
        "tipo": tipo,
        "obrigatorio": obrigatorio,
        "escopo": escopo,
    }
    if opcoes is not None:
        resultado["opcoes"] = opcoes
    return resultado


def grupo_vistoria(titulo: str, itens: List[str]) -> Dict[str, Any]:
    """Grupo de itens de inspecao. Cada item e avaliado como OK / N_OK / REPARAR."""
    return {
        "titulo": titulo,
        "estados": ["OK", "N_OK", "REPARAR"],
        "itens": itens,
    }
