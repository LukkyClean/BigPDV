# app/services/fiscal/helpers.py
from datetime import datetime, timezone
from typing import Optional

from app.schemas.verificacao_fiscal import PendenciaFiscal
from app.db.models.cliente import Cliente, ClientePF, ClientePJ


# ---------------------------------------------------------------------------
# Validade do certificado A1
# ---------------------------------------------------------------------------
# Um certificado vencido para a loja inteira, e a SEFAZ nao avisa antes: a
# primeira noticia e uma rejeicao. Quem conta os dias e este helper, para o
# gate, o painel de pendencias e o card lerem o MESMO numero.
DIAS_AVISO_CERTIFICADO = 30


def dias_para_vencer_certificado(validade: Optional[datetime]) -> Optional[int]:
    """Dias inteiros ate a validade (negativo = vencido); None se nao ha validade."""
    if validade is None:
        return None
    agora = datetime.now(timezone.utc)
    if validade.tzinfo is None:
        validade = validade.replace(tzinfo=timezone.utc)
    return (validade.date() - agora.date()).days


def aviso_certificado(validade: Optional[datetime]) -> Optional[str]:
    """Frase para a tela quando o certificado esta a 30 dias ou menos do fim."""
    dias = dias_para_vencer_certificado(validade)
    if dias is None or dias > DIAS_AVISO_CERTIFICADO:
        return None
    data = validade.strftime("%d/%m/%Y")
    if dias < 0:
        return f"Certificado digital vencido em {data}. A SEFAZ recusa toda emissao ate um novo ser enviado."
    if dias == 0:
        return f"Certificado digital vence HOJE ({data}). Renove e envie o novo antes de emitir."
    return f"Certificado digital vence em {dias} dia{'s' if dias != 1 else ''} ({data}). Renove e envie o novo em Centro Fiscal > Configuracoes."


# ---------------------------------------------------------------------------
# CRT — Código de Regime Tributário da NF-e
# ---------------------------------------------------------------------------
# 1 = Simples Nacional
# 2 = Simples Nacional, excesso de sublimite de receita bruta
# 3 = Regime Normal
# 4 = Simples Nacional — MEI
#
# Só CRT 1 e 4 usam CSOSN. O CRT 2 é do Simples mas, para o excedente, tributa
# pelo regime normal: usa CST como qualquer empresa de Lucro Presumido/Real.
# Confundir os dois manda a nota com o grupo de ICMS errado.
CRT_SIMPLES_NACIONAL = 1
CRT_SIMPLES_EXCESSO = 2
CRT_REGIME_NORMAL = 3
CRT_MEI = 4

CRT_PADRAO = CRT_REGIME_NORMAL

# Mapeia os rótulos usados na interface para o CRT correspondente.
# Chaves em minúsculas e sem espaços nas bordas.
_ROTULO_PARA_CRT = {
    "simples nacional": CRT_SIMPLES_NACIONAL,
    "simples nacional (excesso de sublimite)": CRT_SIMPLES_EXCESSO,
    "regime normal": CRT_REGIME_NORMAL,
    "mei": CRT_MEI,
    "microempreendedor individual": CRT_MEI,
    # Lucro Presumido e Lucro Real são os dois sabores do Regime Normal. Para o
    # CRT da nota os dois valem 3 — a diferença entre eles só aparece no regime
    # de apuração do PIS/COFINS (ver `regime_apuracao`).
    "lucro presumido": CRT_REGIME_NORMAL,
    "lucro real": CRT_REGIME_NORMAL,
}


# ---------------------------------------------------------------------------
# Regime de apuração do PIS/COFINS
# ---------------------------------------------------------------------------
# É ortogonal ao CRT: quem está no Simples (CRT 1/4) nem chega aqui, porque sai
# com CST 49 zerado. Para o Regime Normal, o que decide a alíquota é o regime de
# apuração, não a UF — PIS e COFINS são tributos federais.
REGIME_CUMULATIVO = "CUMULATIVO"          # Lucro Presumido — 0,65% / 3,00%
REGIME_NAO_CUMULATIVO = "NAO_CUMULATIVO"  # Lucro Real      — 1,65% / 7,60%

_ROTULO_PARA_APURACAO = {
    "lucro real": REGIME_NAO_CUMULATIVO,
    "lucro presumido": REGIME_CUMULATIVO,
}


def regime_apuracao(empresa) -> str:
    """
    Regime de apuração do PIS/COFINS da empresa.

    Default conservador: CUMULATIVO. É o regime da esmagadora maioria das lojas,
    e o rótulo genérico "Regime Normal" (usado por todo cadastro anterior a esta
    versão) não distingue Presumido de Real. Destacar 0,65/3,00 quando o certo
    seria 1,65/7,60 recolhe a menor e se corrige; o contrário cobra do cliente
    um imposto que não era devido.
    """
    rotulo = (getattr(empresa, "regime_tributario", None) or "").strip().lower()
    return _ROTULO_PARA_APURACAO.get(rotulo, REGIME_CUMULATIVO)


def crt_efetivo(regime_tributario, natureza_juridica) -> int:
    """
    CRT a persistir no cadastro, a partir do que o usuário preencheu.

    Ordem: o rótulo de regime manda; se ele não disser nada, a natureza jurídica
    MEI resolve; sem os dois, Regime Normal. Diferente de `obter_crt`, que lê uma
    empresa já salva, esta função roda no momento do save.
    """
    do_rotulo = crt_do_rotulo(regime_tributario)
    if do_rotulo is not None:
        return do_rotulo

    if (natureza_juridica or "").strip().upper() == "MEI":
        return CRT_MEI

    return CRT_PADRAO


def crt_do_rotulo(regime: Optional[str]) -> Optional[int]:
    """
    Traduz o texto de `regime_tributario` para CRT.

    Usado apenas na migração de dados antigos e como último recurso quando a
    coluna `crt` ainda está vazia. O caminho normal é ler `empresa.crt`.
    """
    if not regime:
        return None
    return _ROTULO_PARA_CRT.get(regime.strip().lower())


def obter_crt(empresa) -> int:
    """
    CRT efetivo da empresa.

    Prioriza a coluna `crt`; cai no rótulo textual só enquanto houver cadastros
    anteriores à migração. Sem nenhum dos dois, assume Regime Normal — o padrão
    seguro, porque destacar ICMS indevidamente é erro corrigível por carta de
    correção, enquanto usar CSOSN sem ser do Simples é rejeição na origem.
    """
    if empresa is None:
        return CRT_PADRAO

    crt = getattr(empresa, "crt", None)
    if crt in (CRT_SIMPLES_NACIONAL, CRT_SIMPLES_EXCESSO, CRT_REGIME_NORMAL, CRT_MEI):
        return crt

    return crt_do_rotulo(getattr(empresa, "regime_tributario", None)) or CRT_PADRAO


def usa_csosn(crt: int) -> bool:
    """Só CRT 1 (Simples) e 4 (MEI) preenchem CSOSN; os demais usam CST."""
    return crt in (CRT_SIMPLES_NACIONAL, CRT_MEI)


def pis_cofins_por_fora(crt: int) -> bool:
    """
    Se a empresa recolhe PIS/COFINS por fora da nota.

    No Simples Nacional (CRT 1 e 4) os tributos estão embutidos na guia única:
    destacar alíquota na nota gera bitributação aparente. Esses casos saem com
    CST 49 e valores zerados.
    """
    return crt in (CRT_SIMPLES_NACIONAL, CRT_MEI)


def is_simples_nacional(regime: Optional[str]) -> bool:
    """
    DEPRECADO — mantido só para não quebrar chamadas antigas.

    O nome engana: `"simples" in regime` também casa com "Simples Nacional
    (Excesso de Sublimite)", que é CRT 2 e usa CST, não CSOSN. Use
    `obter_crt(empresa)` + `usa_csosn(crt)`.
    """
    return usa_csosn(crt_do_rotulo(regime) or CRT_PADRAO)


def criar_pendencia(categoria: str, campo: str, mensagem: str,
                    referencia_id: int = None, referencia_nome: str = None) -> PendenciaFiscal:
    return PendenciaFiscal(
        categoria=categoria,
        campo=campo,
        mensagem=mensagem,
        referencia_id=referencia_id,
        referencia_nome=referencia_nome,
    )


def get_nome_cliente(cliente: Cliente) -> str:
    if isinstance(cliente, ClientePF):
        return cliente.nome
    elif isinstance(cliente, ClientePJ):
        return cliente.nome_fantasia or cliente.razao_social
    return f"Cliente #{cliente.id}"


# ---------------------------------------------------------------------------
# CSC — Código de Segurança do Contribuinte (NFC-e)
# ---------------------------------------------------------------------------
# O CSC é o segredo que autentica o QR Code do cupom: é com ele que o
# provedor monta o hash que a SEFAZ confere quando o consumidor lê o código.
# Vazado, permite forjar QR Code em nome da loja — por isso é guardado
# cifrado com Fernet, do mesmo jeito que a senha do certificado A1.

def cifrar_csc_token(token: Optional[str]) -> Optional[str]:
    """Cifra o CSC para gravar. Vazio vira None (limpa o campo)."""
    from app.core.security import encrypt_data

    if not token or not token.strip():
        return None
    return encrypt_data(token.strip())


def decifrar_csc(bruto: Optional[str]) -> Optional[str]:
    """Decifra o valor gravado na coluna `csc_token`.

    Tolera o valor em texto puro: as instalações anteriores a esta versão
    gravaram o CSC sem cifrar, e recusá-las aqui quebraria a emissão de quem
    já tinha o token configurado. O valor legado é devolvido como está e
    passa a ser cifrado no próximo salvamento da configuração fiscal.
    """
    from app.core.security import decrypt_data

    if not bruto:
        return None

    try:
        return decrypt_data(bruto)
    except Exception:
        return bruto


def obter_csc_token(fiscal_settings) -> Optional[str]:
    """CSC em claro a partir do objeto de configuração fiscal."""
    return decifrar_csc(getattr(fiscal_settings, "csc_token", None))


# Caractere da máscara do CSC. Escolhido por não existir em CSC real (que é
# alfanumérico), então serve de sentinela: se ele voltar no PUT, é porque a
# tela devolveu a máscara sem que ninguém digitasse um token novo.
MASCARA_CSC = "•"


def mascarar_csc(token: Optional[str]) -> Optional[str]:
    """Versão do CSC segura para trafegar até a tela.

    O segredo não precisa sair do servidor para o lojista saber que está
    configurado — bastam os últimos caracteres para ele reconhecer QUAL token
    cadastrou. Devolver o CSC inteiro colocava o segredo do QR Code em toda
    resposta da configuração fiscal, em log de proxy e no cache do navegador.
    """
    if not token:
        return None
    visivel = token[-4:] if len(token) > 4 else ""
    return MASCARA_CSC * 8 + visivel


def e_csc_mascarado(valor: Optional[str]) -> bool:
    """True quando a tela devolveu a máscara em vez de um token novo."""
    return bool(valor) and MASCARA_CSC in valor
