"""
Fixtures compartilhadas para testes dat_ingest.

Configura diretórios temporários para evitar escrita em /app/ durante CI.
"""

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def etl_tmpdir(settings, tmp_path):
    """
    Redireciona ETL_OUTPUT_DIR e BASE_DIR para diretórios temporários.

    Evita:
    - Escrita em /app/out_etl/ (CI read-only)
    - Criação de /app/.agents/ (permissões)

    Aplicado automaticamente a todos os testes de dat_ingest.
    """
    # Diretório para relatórios ETL
    tmp_out = tmp_path / "out_etl"
    tmp_out.mkdir()
    settings.ETL_OUTPUT_DIR = str(tmp_out)

    # Diretório para .agents/outbox (usado por backfill commands)
    tmp_base = tmp_path / "base"
    tmp_base.mkdir()
    agents_outbox = tmp_base / ".agents" / "outbox"
    agents_outbox.mkdir(parents=True)
    # BASE_DIR deve ser Path, não str, para compatibilidade com Path() / ".agents"
    settings.BASE_DIR = tmp_base

    yield
