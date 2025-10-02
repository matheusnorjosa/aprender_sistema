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
AGENDA_2025_ID = "1oqDA9tN-wNiFVLS3KYTFzsXKpJpvDECfeKucjwf9GKs"  # ID da planilha principal de agenda

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
    # Eventos por projeto
    # 'ACerta': '123456789',  # Exemplo: ID numérico da aba
    # 'Brincando': '987654321',
    # 'Novo Lendo': '456789123',
    # 'Super': '789123456',  # Aba de controle da superintendência

    # Abas de controle
    # 'Bloqueios': '321654987',
    # 'Deslocamentos': '654987321',
    # 'Configuracoes': '147258369',
}

# Abas da Planilha de Disponibilidade
ABAS_DISPONIBILIDADE = {
    # 'Janeiro': '111111111',
    # 'Fevereiro': '222222222',
    # etc...
}

# Abas da Planilha de Usuários
ABAS_USUARIOS = {
    # 'Ativos': '333333333',
    # 'Inativos': '444444444',
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
