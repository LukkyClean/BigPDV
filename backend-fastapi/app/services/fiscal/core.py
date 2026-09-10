# app/services/verificacao_fiscal/service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.verificacao_fiscal import ResultadoVerificacaoFiscal
from app.db.crud import fiscal as crud

from . import validators
from .helpers import obter_crt, usa_csosn, criar_pendencia as _p

def verificar_completude_venda(
    db: Session, venda_id: int, empresa_id: int, tipo_documento: str = "nfe",
) -> ResultadoVerificacaoFiscal:
    """Pendencias que impedem a emissao desta venda.

    `tipo_documento` existe por causa do ENDERECO do destinatario, que e o unico
    requisito que muda entre os dois modelos: obrigatorio na NF-e (55), omitido
    na NFC-e (65). Exigi-lo dos dois reprovaria o cupom de balcao de todo
    consumidor que so informou o CPF -- que e o caso normal do PDV.

    O padrao e "nfe" porque a NF-e e o caminho que reprova mais; quem emite
    cupom passa "nfce" explicitamente.
    """
    venda = crud.get_venda_completa(db, venda_id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")

    empresa = crud.get_empresa(db, empresa_id)
    simples = usa_csosn(obter_crt(empresa))

    pendencias = []
    pendencias.extend(validators.verificar_emitente(db, empresa_id))
    
    if not venda.cliente_id or not venda.cliente:
        pendencias.append(_p("destinatario", "cliente", "Venda não possui destinatário."))
    else:
        pendencias.extend(validators.verificar_documento_cliente(venda.cliente))
        if tipo_documento == "nfe":
            pendencias.extend(validators.verificar_endereco_destinatario(venda.cliente))

    pendencias.extend(validators.verificar_itens_venda(db, venda, simples))
    pendencias.extend(validators.verificar_pagamentos(venda.pagamentos))

    return ResultadoVerificacaoFiscal(completo=len(pendencias) == 0, pendencias=pendencias)

def verificar_completude_os(db: Session, numero_os: str, empresa_id: int, tipo_documento: str = "ambos") -> ResultadoVerificacaoFiscal:
    os_obj = crud.get_os_completa(db, numero_os)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada.")

    empresa = crud.get_empresa(db, empresa_id)
    simples = usa_csosn(obter_crt(empresa))

    nota = os_obj.nota_fiscal
    emitir_nfe = nota.emitir_nfe if nota and nota.emitir_nfe is not None else True
    emitir_nfse = nota.emitir_nfse if nota and nota.emitir_nfse is not None else True

    pendencias = []
    pendencias.extend(validators.verificar_emitente(db, empresa_id))

    cliente = getattr(os_obj.objeto, "cliente", None) if os_obj.objeto else None
    if not cliente:
        pendencias.append(_p("destinatario", "cliente", "OS sem cliente no objeto."))
    else:
        pendencias.extend(validators.verificar_documento_cliente(cliente))
        if tipo_documento in ("nfe", "ambos") and emitir_nfe:
            pendencias.extend(validators.verificar_endereco_destinatario(cliente))

    if tipo_documento in ("nfe", "ambos") and emitir_nfe:
        pendencias.extend(validators.verificar_itens_os_nfe(db, os_obj, simples))
    if tipo_documento in ("nfse", "ambos") and emitir_nfse:
        pendencias.extend(validators.verificar_itens_os_nfse(db, os_obj))

    pendencias.extend(validators.verificar_pagamentos(os_obj.pagamentos))

    return ResultadoVerificacaoFiscal(completo=len(pendencias) == 0, pendencias=pendencias)