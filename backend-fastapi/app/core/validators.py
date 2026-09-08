# ---------------------------------------------------------------------------
# ARQUIVO: app/core/validators.py
# DESCRIÇÃO: Funções de validação de documentos brasileiros (CPF e CNPJ).
#
# Usadas como `field_validator` nos schemas Pydantic para garantir que
# somente documentos com dígito verificador válido sejam aceitos pelo sistema.
#
# Com o módulo fiscal, documentos inválidos causam rejeição imediata pela
# Receita Federal — essa validação é a Camada 1 (formato) do design fiscal.
# ---------------------------------------------------------------------------

import re
from typing import Optional


def _apenas_digitos(valor: str) -> str:
    """Remove qualquer caractere não-numérico."""
    return re.sub(r"\D", "", valor)


def validar_cpf(valor: Optional[str]) -> Optional[str]:
    """
    Valida CPF com cálculo de dígito verificador.

    - Aceita None e string vazia (campo opcional) — retorna sem erro.
    - Remove formatação (pontos, hífens) antes de validar.
    - Rejeita sequências uniformes (ex: "11111111111").
    - Levanta ValueError se o dígito verificador for inválido.

    Returns:
        str com apenas os dígitos numéricos, ou None se a entrada for vazia.
    """
    if valor is None or valor == "":
        return valor

    digitos = _apenas_digitos(valor)

    if len(digitos) != 11:
        raise ValueError(f"CPF deve ter 11 dígitos numéricos (recebido: {len(digitos)})")

    # Rejeita sequências uniformes (ex: 000.000.000-00, 111.111.111-11)
    if len(set(digitos)) == 1:
        raise ValueError("CPF inválido: sequência de dígitos iguais não é permitida")

    # --- Cálculo do 1º dígito verificador ---
    soma = sum(int(d) * peso for d, peso in zip(digitos[:9], range(10, 1, -1)))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(digitos[9]) != digito1:
        raise ValueError("CPF inválido: dígito verificador incorreto")

    # --- Cálculo do 2º dígito verificador ---
    soma = sum(int(d) * peso for d, peso in zip(digitos[:10], range(11, 1, -1)))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    if int(digitos[10]) != digito2:
        raise ValueError("CPF inválido: dígito verificador incorreto")

    return digitos


def validar_cnpj(valor: Optional[str]) -> Optional[str]:
    """
    Valida CNPJ com cálculo de dígito verificador.

    - Aceita None e string vazia (campo opcional) — retorna sem erro.
    - Remove formatação (pontos, barras, hífens) antes de validar.
    - Rejeita sequências uniformes (ex: "00000000000000").
    - Levanta ValueError se o dígito verificador for inválido.

    Returns:
        str com apenas os dígitos numéricos, ou None se a entrada for vazia.
    """
    if valor is None or valor == "":
        return valor

    digitos = _apenas_digitos(valor)

    if len(digitos) != 14:
        raise ValueError(f"CNPJ deve ter 14 dígitos numéricos (recebido: {len(digitos)})")

    # Rejeita sequências uniformes (ex: 00.000.000/0000-00)
    if len(set(digitos)) == 1:
        raise ValueError("CNPJ inválido: sequência de dígitos iguais não é permitida")

    # --- Cálculo do 1º dígito verificador ---
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(d) * p for d, p in zip(digitos[:12], pesos1))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(digitos[12]) != digito1:
        raise ValueError("CNPJ inválido: dígito verificador incorreto")

    # --- Cálculo do 2º dígito verificador ---
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(d) * p for d, p in zip(digitos[:13], pesos2))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    if int(digitos[13]) != digito2:
        raise ValueError("CNPJ inválido: dígito verificador incorreto")

    return digitos
