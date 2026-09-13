# ---------------------------------------------------------------------------
# ARQUIVO: app/services/pendencias_globais.py
# DESCRIÇÃO: Pendências fiscais globais para o painel do Centro Fiscal.
#            Diferente de verificacao_fiscal.py que verifica uma venda/OS
#            específica, aqui verificamos o cadastro geral da empresa.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session

from app.db.models.produto import Produto
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.servico import Servico
from app.db.models.servico_fiscal import ServicoFiscal
from app.db.models.forma_pagamento import FormaPagamento
from app.schemas.documento_fiscal import PendenciaGlobalItem, PendenciasGlobais
from app.services.verificacao_fiscal import _verificar_emitente
from app.services.fiscal.helpers import aviso_certificado, dias_para_vencer_certificado
from app.db.crud import fiscal as fiscal_crud


def obter_pendencias_globais(db: Session, empresa_id: int) -> PendenciasGlobais:
    # 1. Emitente — reutiliza lógica existente
    pendencias_emitente = _verificar_emitente(db, empresa_id)
    emitente_completo = len(pendencias_emitente) == 0
    emitente_msgs = [p.mensagem for p in pendencias_emitente]

    # 1b. Certificado vencendo -- aviso com antecedencia, nao pendencia
    fs = fiscal_crud.get_fiscal_settings(db, empresa_id)
    validade = fs.certificado_validade if fs else None

    # 2. Produtos ativos sem NCM
    produtos_sem_ncm_rows = (
        db.query(Produto.id, Produto.nome)
        .outerjoin(ProdutoFiscal, ProdutoFiscal.produto_id == Produto.id)
        .filter(
            Produto.ativo == True,  # noqa: E712
            (ProdutoFiscal.id == None) | (ProdutoFiscal.ncm == None) | (ProdutoFiscal.ncm == ""),  # noqa: E711
        )
        .all()
    )
    produtos_sem_ncm = [
        PendenciaGlobalItem(id=r[0], nome=r[1] or "Sem nome", campo_faltante="NCM")
        for r in produtos_sem_ncm_rows
    ]

    # 3. Serviços ativos sem código LC 116
    servicos_sem_lc116_rows = (
        db.query(Servico.id, Servico.descricao)
        .outerjoin(ServicoFiscal, ServicoFiscal.servico_id == Servico.id)
        .filter(
            Servico.ativo == True,  # noqa: E712
            (ServicoFiscal.id == None)  # noqa: E711
            | (ServicoFiscal.codigo_servico_lc116 == None)  # noqa: E711
            | (ServicoFiscal.codigo_servico_lc116 == ""),
        )
        .all()
    )
    servicos_sem_lc116 = [
        PendenciaGlobalItem(id=r[0], nome=r[1] or "Sem descrição", campo_faltante="Código Serviço LC 116")
        for r in servicos_sem_lc116_rows
    ]

    # 4. Formas de pagamento ativas sem código SEFAZ
    pagamentos_sem_sefaz_rows = (
        db.query(FormaPagamento.id, FormaPagamento.nome)
        .filter(
            FormaPagamento.ativo == True,  # noqa: E712
            (FormaPagamento.codigo_sefaz == None) | (FormaPagamento.codigo_sefaz == ""),  # noqa: E711
        )
        .all()
    )
    pagamentos_sem_sefaz = [
        PendenciaGlobalItem(id=r[0], nome=r[1] or "Sem nome", campo_faltante="Código SEFAZ")
        for r in pagamentos_sem_sefaz_rows
    ]

    return PendenciasGlobais(
        emitente_completo=emitente_completo,
        emitente_pendencias=emitente_msgs,
        emitente_avisos=_avisos_do_emitente(db, empresa_id),
        certificado_aviso=aviso_certificado(validade),
        certificado_dias_restantes=dias_para_vencer_certificado(validade),
        produtos_sem_ncm=produtos_sem_ncm,
        servicos_sem_lc116=servicos_sem_lc116,
        pagamentos_sem_sefaz=pagamentos_sem_sefaz,
    )


def _avisos_do_emitente(db, empresa_id: int) -> list[str]:
    """
    O que está errado no cadastro mas NÃO impede emitir.

    Separado das pendências de propósito: pendência recusa a nota, aviso só
    conta. Confundir os dois é como se trava uma loja que estava emitindo bem.

    Hoje há um: Inscrição Estadual preenchida junto de "9 - Não Contribuinte".
    Apareceu numa loja real em 12/09/2026 (MEI com IE ativa). O indicador do
    emitente não vai no XML — quem tem indicador na nota é o destinatário —,
    então o dado está errado sem quebrar nada.
    """
    from app.db.crud import fiscal as crud

    empresa = crud.get_empresa(db, empresa_id)
    if empresa is None:
        return []

    avisos: list[str] = []
    if getattr(empresa, "indicador_ie", None) == "9" and getattr(empresa, "inscricao_estadual", None):
        avisos.append(
            f"Indicador de IE está como '9 - Não Contribuinte', mas a empresa tem "
            f"Inscrição Estadual ({empresa.inscricao_estadual}). Quem tem IE e vende "
            f"mercadoria é '1 - Contribuinte ICMS'. Não impede a emissão."
        )
    return avisos
