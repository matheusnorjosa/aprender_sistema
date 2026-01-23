"""
DAT Ingest App — AS v2

Responsável pela ingestão (ETL) de dados das planilhas Excel para PostgreSQL:
- Comandos Django: etl_usuarios, etl_agenda, etl_disponibilidade, etl_controle
- API REST: POST /api/ingest/agenda/, /disponibilidade/, /controle/
- Serializers DRF para validação de CSV uploads
"""

from __future__ import annotations

default_app_config = "dat_ingest.apps.DatIngestConfig"
