# app/services/verificacao_fiscal/helpers.py
from typing import Optional
from app.schemas.verificacao_fiscal import PendenciaFiscal
from app.db.models.cliente import Cliente, ClientePF, ClientePJ

def criar_pendencia(categoria: str, campo: str, mensagem: str,
                    referencia_id: int = None, referencia_nome: str = None) -> PendenciaFiscal:
    return PendenciaFiscal(
        categoria=categoria,
        campo=campo,
        mensagem=mensagem,
        referencia_id=referencia_id,
        referencia_nome=referencia_nome,
    )

def is_simples_nacional(regime: Optional[str]) -> bool:
    if not regime:
        return False
    return "simples" in regime.lower()

def get_nome_cliente(cliente: Cliente) -> str:
    if isinstance(cliente, ClientePF):
        return cliente.nome
    elif isinstance(cliente, ClientePJ):
        return cliente.nome_fantasia or cliente.razao_social
    return f"Cliente #{cliente.id}"