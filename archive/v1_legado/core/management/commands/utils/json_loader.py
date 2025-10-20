"""
Utilitários para carregar dados JSON extraídos das planilhas
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings


class JSONDataLoader:
    """Carregador de dados JSON otimizado para migração massiva"""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path(settings.BASE_DIR)
        self.cache = {}

    def load_extracted_data(
        self, filename: str, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Carrega dados de arquivo JSON extraído

        Args:
            filename: Nome do arquivo JSON (ex: 'extracted_usuarios.json')
            use_cache: Se deve usar cache em memória

        Returns:
            Dict com dados carregados
        """
        if use_cache and filename in self.cache:
            return self.cache[filename]

        file_path = self.base_path / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if use_cache:
                self.cache[filename] = data

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao decodificar JSON em {filename}: {e}")

        except Exception as e:
            raise RuntimeError(f"Erro ao carregar {filename}: {e}")

    def get_worksheet_data(self, filename: str, worksheet_name: str) -> Dict[str, Any]:
        """
        Obtém dados de uma aba específica

        Args:
            filename: Arquivo JSON da planilha
            worksheet_name: Nome da aba

        Returns:
            Dict com dados da aba
        """
        data = self.load_extracted_data(filename)
        worksheets = data.get("worksheets", {})

        if worksheet_name not in worksheets:
            available = list(worksheets.keys())
            raise KeyError(
                f"Aba '{worksheet_name}' não encontrada. Disponíveis: {available}"
            )

        return worksheets[worksheet_name]

    def get_worksheet_records(
        self, filename: str, worksheet_name: str, skip_header: bool = True
    ) -> List[List[str]]:
        """
        Obtém registros de uma aba como lista de listas

        Args:
            filename: Arquivo JSON da planilha
            worksheet_name: Nome da aba
            skip_header: Se deve pular o cabeçalho

        Returns:
            Lista de registros
        """
        worksheet_data = self.get_worksheet_data(filename, worksheet_name)

        records = worksheet_data.get("data", [])

        if skip_header and records:
            # Primeira linha geralmente é cabeçalho
            return records[1:] if len(records) > 1 else []

        return records

    def get_headers(self, filename: str, worksheet_name: str) -> List[str]:
        """
        Obtém cabeçalhos de uma aba

        Args:
            filename: Arquivo JSON da planilha
            worksheet_name: Nome da aba

        Returns:
            Lista de headers
        """
        worksheet_data = self.get_worksheet_data(filename, worksheet_name)
        return worksheet_data.get("headers", [])

    def get_records_as_dicts(
        self, filename: str, worksheet_name: str
    ) -> List[Dict[str, str]]:
        """
        Converte registros para dicionários usando headers como chaves

        Args:
            filename: Arquivo JSON da planilha
            worksheet_name: Nome da aba

        Returns:
            Lista de dicionários
        """
        headers = self.get_headers(filename, worksheet_name)
        records = self.get_worksheet_records(filename, worksheet_name)

        result = []
        for record in records:
            # Garantir que o record tenha o mesmo tamanho dos headers
            record_dict = {}
            for i, header in enumerate(headers):
                value = record[i] if i < len(record) else ""
                record_dict[header] = (
                    value.strip() if isinstance(value, str) else str(value)
                )

            result.append(record_dict)

        return result

    def validate_file_exists(self, filename: str) -> bool:
        """Verifica se arquivo existe"""
        return (self.base_path / filename).exists()

    def get_file_stats(self, filename: str) -> Dict[str, Any]:
        """
        Obtém estatísticas do arquivo

        Returns:
            Dict com estatísticas (tamanho, data modificação, etc)
        """
        file_path = self.base_path / filename

        if not file_path.exists():
            return {"exists": False}

        stat = file_path.stat()
        data = self.load_extracted_data(filename)

        total_records = 0
        total_worksheets = 0

        if "worksheets" in data:
            total_worksheets = len(data["worksheets"])
            total_records = sum(
                ws_data.get("total_rows", 0) for ws_data in data["worksheets"].values()
            )

        return {
            "exists": True,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
            "total_worksheets": total_worksheets,
            "total_records": total_records,
            "extraction_date": data.get("data_extracao", "N/A"),
            "unicode_cleaned": data.get("unicode_cleaning", False),
        }

    def clear_cache(self):
        """Limpa cache de dados carregados"""
        self.cache.clear()


# Instância global para uso nos commands
json_loader = JSONDataLoader()
