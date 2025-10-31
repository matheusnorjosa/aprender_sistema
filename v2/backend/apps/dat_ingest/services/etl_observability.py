"""
ETL Observability Service

Fornece funções para listar e inspecionar relatórios ETL gerados pelos
management commands (etl_upsert_*, etl_import_*, etc).

Fase 5 - Desligamento gradual de planilhas
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings


def list_latest_reports(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lista os relatórios ETL mais recentes do diretório de saída.

    Args:
        limit: Número máximo de relatórios a retornar (1-100)

    Returns:
        Lista de dicionários com metadados dos arquivos:
        - filename: Nome do arquivo
        - size_bytes: Tamanho em bytes
        - mtime_iso: Data/hora de modificação (ISO 8601)
        - kind: Tipo do arquivo (json, csv, txt, other)
        - path_rel: Caminho relativo ao ETL_OUTPUT_DIR

    Raises:
        ValueError: Se limit estiver fora do intervalo 1-100

    Security:
        - Apenas retorna arquivos dentro de ETL_OUTPUT_DIR
        - Não expõe caminhos absolutos do sistema
        - Ignora arquivos ocultos (começando com .)
    """
    # Validar limite
    if not (1 <= limit <= 100):
        raise ValueError("limit deve estar entre 1 e 100")

    # Obter diretório de saída ETL
    output_dir = Path(settings.ETL_OUTPUT_DIR)

    # Se diretório não existe, retornar lista vazia (não é erro)
    if not output_dir.exists():
        return []

    # Listar todos os arquivos (não recursivo por segurança)
    try:
        files = []
        for entry in output_dir.iterdir():
            # Ignorar diretórios e arquivos ocultos
            if entry.is_dir() or entry.name.startswith('.'):
                continue

            # Obter metadados
            stat = entry.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)

            # Determinar tipo de arquivo pela extensão
            ext = entry.suffix.lower()
            if ext == '.json':
                kind = 'json'
            elif ext == '.csv':
                kind = 'csv'
            elif ext == '.txt' or ext == '.log':
                kind = 'txt'
            else:
                kind = 'other'

            # Caminho relativo seguro (apenas nome do arquivo neste caso)
            path_rel = entry.name

            files.append({
                'filename': entry.name,
                'size_bytes': stat.st_size,
                'mtime_iso': mtime.isoformat(),
                'kind': kind,
                'path_rel': path_rel,
            })

    except PermissionError:
        # Se não tivermos permissão, retornar lista vazia
        return []

    # Ordenar por mtime (mais recente primeiro)
    files.sort(key=lambda x: x['mtime_iso'], reverse=True)

    # Aplicar limite
    return files[:limit]


def get_report_path(filename: str) -> Optional[Path]:
    """
    Retorna o Path absoluto de um relatório se ele existir dentro do ETL_OUTPUT_DIR.

    Args:
        filename: Nome do arquivo (sem path)

    Returns:
        Path absoluto se o arquivo existir, None caso contrário

    Security:
        - Valida que o arquivo está dentro de ETL_OUTPUT_DIR
        - Não permite path traversal (../)
        - Retorna None se caminho for suspeito
    """
    # Validar que filename não contém path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return None

    output_dir = Path(settings.ETL_OUTPUT_DIR)
    file_path = output_dir / filename

    # Validar que arquivo está dentro do diretório permitido
    try:
        file_path.resolve().relative_to(output_dir.resolve())
    except ValueError:
        # Path traversal detected
        return None

    # Verificar se arquivo existe
    if not file_path.exists() or not file_path.is_file():
        return None

    return file_path
