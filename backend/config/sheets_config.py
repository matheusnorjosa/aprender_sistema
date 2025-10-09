"""
Configurações de IDs de planilhas Google Sheets.

Este arquivo centraliza todos os IDs de planilhas e abas usadas pelo sistema.
Para obter os IDs:
1. Abra a planilha no Google Sheets
2. Copie o ID da URL (entre /d/ e /edit)
3. Para gid da aba, clique na aba e copie o número após #gid=
"""

# =============================================================================
# IDs DAS PLANILHAS PRINCIPAIS
# =============================================================================

# Planilha de Agenda 2025
AGENDA_2025_ID = (
    "1oqDA9tN-wNiFVLS3KYTFzsXKpJpvDECfeKucjwf9GKs"  # ID da planilha principal de agenda
)

# Planilha de Disponibilidade
DISPONIBILIDADE_2025_ID = "1C4_9Gn8gwKjgD1CgssIKaU4bacwv7XuL2QnoSVwomxU"  # ID da planilha de disponibilidade dos formadores

# Planilha de Controle
CONTROLE_2025_ID = "1adUmabEnbaG6Ldf58poLZts-4Bc7zSOm0XbVuhc_dfo"  # ID da planilha de controle administrativo

# Planilha de Usuários Ativos
USUARIOS_ID = "1yPH-uCRc2XyThLU7V4pSoNYozydn1-IRRJRjubFCjXs"  # ID da planilha com cadastro de usuários/formadores


# =============================================================================
# ABAS DAS PLANILHAS (gid)
# =============================================================================

# Abas da Planilha de Agenda
ABAS = {
    "ACerta": "1055368874",
    "Outros": "1647358371",
    "Super": "0",
    "Brincando": "1101094368",
    "Vidas": "1882642294",
}


# Abas da Planilha de Disponibilidade
ABAS_DISPONIBILIDADE = {
    "ANUAL": "696255555",
    "DESLOCAMENTO": "1634387612",
    "Bloqueios": "1728789738",
}


# Abas da Planilha de Usuários
ABAS_USUARIOS = {
    "Ativos": "143336602",
}


# =============================================================================
# CONFIGURAÇÕES DE IMPORTAÇÃO
# =============================================================================

# Ano de referência para importações
ANO_REFERENCIA = 2025

# Timeout para requests (segundos)
SHEETS_TIMEOUT = 30

# Máximo de tentativas em caso de erro
MAX_RETRIES = 3

# Delay entre tentativas (segundos)
RETRY_DELAY = 2


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def csv_url(sheet_id: str, gid: str) -> str:
    """
    Gera URL de exportação CSV para uma aba específica.

    Args:
        sheet_id: ID da planilha Google Sheets
        gid: ID da aba (GID)

    Returns:
        str: URL de exportação no formato CSV
    """
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    )


def get_aba_gid(aba_nome: str) -> str:
    """
    Retorna o GID de uma aba pelo nome.

    Args:
        aba_nome: Nome da aba (case-insensitive)

    Returns:
        str: GID da aba ou string vazia se não encontrada
    """
    aba_nome_normalized = aba_nome.strip().lower()

    for key, value in ABAS.items():
        if key.lower() == aba_nome_normalized:
            return value

    return ""
