"""
Constantes para comandos ETL e validações.

Centraliza thresholds, limites e scores para facilitar ajuste fino
e testes parametrizados.

Issue #54: Extrair magic numbers para constantes.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false


from __future__ import annotations

from decimal import Decimal

# ================================================================
# MATCHING DE NOMES (Jaccard similarity)
# ================================================================
# Threshold mínimo para considerar match válido por similaridade Jaccard
NAME_MATCH_JACCARD_MIN = Decimal("0.60")

# Score para subset tokens (todos tokens de um estão no outro)
NAME_MATCH_SCORE_SUBSET = Decimal("0.90")

# Score para first + last name match
NAME_MATCH_SCORE_FIRST_LAST = Decimal("0.85")

# ================================================================
# LIMITES DE RELATÓRIOS
# ================================================================
# Número de usuários não cadastrados a exibir no top ranking
TOP_UNKNOWN_USERS_LIMIT = 20

# ================================================================
# BUFFER DE DESLOCAMENTO (minutos)
# ================================================================
# Buffer padrão entre municípios distintos
# Nota: Esta constante está definida em config/settings.py como TRAVEL_BUFFER_MINUTES
# e pode ser sobrescrita via env var. Mantida aqui para referência.
# TRAVEL_BUFFER_MINUTES = 120

# ================================================================
# CAPACIDADE DIÁRIA (horas)
# ================================================================
# Limite de horas por formador/dia
# Nota: Esta constante está definida em config/settings.py como AVAILABILITY_DAILY_LIMIT_HOURS
# e pode ser sobrescrita via env var. Mantida aqui para referência.
# DAILY_CAPACITY_HOURS = 8

# ================================================================
# THRESHOLDS DE AUDITORIA
# ================================================================
# Mínimo de ocorrências para relatório detalhado
AUDIT_MIN_FREQUENCY = 5

# Mínimo de setores para considerar multi-setor
AUDIT_MULTI_SECTOR_THRESHOLD = 2
