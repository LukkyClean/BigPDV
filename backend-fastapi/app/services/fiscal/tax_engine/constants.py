# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/constants.py
# DESCRIÇÃO: Constantes do motor de cálculo tributário.
#            CSTs/CSOSNs suportados, precisão numérica e defaults.
# ---------------------------------------------------------------------------

from decimal import Decimal, ROUND_HALF_UP

# --- Precisão numérica ---
PRECISAO = Decimal("0.01")
ROUND_MODE = ROUND_HALF_UP

# --- CSTs de ICMS suportados (Regime Normal) ---
CST_ICMS_TRIBUTADO = frozenset({"00"})       # Tributada integralmente
CST_ICMS_REDUZIDA = frozenset({"20"})        # Com redução de base de cálculo
CST_ICMS_ISENTO = frozenset({"40", "41"})    # Isenta / Não tributada
CST_ICMS_ST = frozenset({"60"})              # ICMS cobrado anteriormente por ST
CST_ICMS_SUPORTADOS = CST_ICMS_TRIBUTADO | CST_ICMS_REDUZIDA | CST_ICMS_ISENTO | CST_ICMS_ST

# --- CSOSNs suportados (Simples Nacional) ---
CSOSN_COM_CREDITO = frozenset({"101"})       # Tributada com permissão de crédito
CSOSN_SEM_CREDITO = frozenset({"102"})       # Tributada sem permissão de crédito
CSOSN_ST = frozenset({"500"})                # ICMS cobrado anteriormente por ST
CSOSN_SUPORTADOS = CSOSN_COM_CREDITO | CSOSN_SEM_CREDITO | CSOSN_ST

# --- CSTs de PIS/COFINS ---
CST_PIS_COFINS_TRIBUTADO = frozenset({"01", "02"})  # Alíquota normal / diferenciada
CST_PIS_COFINS_ISENTO = frozenset({"04", "05", "06", "07", "08", "09"})

# --- IPI (comércio/serviços — não calculado) ---
CST_IPI_NAO_TRIBUTADO = "53"
IPI_CODIGO_ENQUADRAMENTO = "999"

# --- Defaults de alíquota PIS/COFINS (Lucro Presumido cumulativo) ---
PIS_PADRAO = Decimal("1.65")
COFINS_PADRAO = Decimal("7.60")
