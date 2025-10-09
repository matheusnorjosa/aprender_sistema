#!/usr/bin/env python3
"""
🧠 EXTRATOR DE DADOS NEURAL - SISTEMA APRENDER
Baseado nas diretrizes do sistema neural e melhores práticas

Este extrator implementa:
- Validação de segurança
- Padrões de código Python/Django
- Tratamento robusto de dados
- Logging estruturado
- Tratamento de exceções específicas
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re
import hashlib

# Configuração de logging seguindo padrões do Sistema APRENDER
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("neural_extraction.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class NeuralDataExtractor:
    """
    Extrator de dados seguindo diretrizes do sistema neural
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o extrator neural

        Args:
            config_path: Caminho para arquivo de configuração
        """
        self.config = self._load_config(config_path)
        self.extraction_stats = {
            "start_time": datetime.now(timezone.utc),
            "files_processed": 0,
            "records_extracted": 0,
            "errors": [],
            "warnings": [],
        }

        logger.info("🧠 Neural Data Extractor inicializado")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do extrator

        Args:
            config_path: Caminho para arquivo de configuração

        Returns:
            Dicionário com configurações
        """
        default_config = {
            "google_sheets": {
                "credentials_file": "google_oauth_token.json",
                "sheets": [
                    "Disponibilidade | 2025",
                    "Planilha de Controle - 2025",
                    "Acompanhamento de Agenda | 2025",
                    "Usuários",
                ],
            },
            "data_validation": {
                "cpf_length": 11,
                "email_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "phone_pattern": r"^\+?[\d\s\-\(\)]+$",
                "required_fields": ["nome", "email"],
            },
            "output": {"format": "json", "include_metadata": True, "compress": False},
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"✅ Configuração carregada de {config_path}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar configuração: {e}")
                logger.info("📋 Usando configuração padrão")

        return default_config

    def extract_from_google_sheets(self) -> Dict[str, Any]:
        """
        Extrai dados do Google Sheets seguindo padrões de segurança

        Returns:
            Dicionário com dados extraídos e metadados
        """
        logger.info("🔄 Iniciando extração do Google Sheets")

        try:
            # Verificar credenciais
            credentials_file = self.config["google_sheets"]["credentials_file"]
            if not Path(credentials_file).exists():
                raise FileNotFoundError(
                    f"Arquivo de credenciais não encontrado: {credentials_file}"
                )

            # Importar gspread apenas quando necessário (lazy import)
            import gspread
            from google.oauth2.credentials import Credentials

            # Carregar token OAuth2
            with open(credentials_file, "r") as f:
                token_data = json.load(f)

            # Configurar credenciais OAuth2
            credentials = Credentials(
                token=token_data["token"],
                refresh_token=token_data["refresh_token"],
                token_uri=token_data["token_uri"],
                client_id=token_data["client_id"],
                client_secret=token_data["client_secret"],
                scopes=token_data["scopes"],
            )

            gc = gspread.authorize(credentials)

            extracted_data = {
                "metadata": {
                    "extraction_time": datetime.now(timezone.utc).isoformat(),
                    "extractor_version": "1.0.0",
                    "source": "google_sheets",
                    "sheets_processed": [],
                },
                "data": {},
            }

            # Processar cada planilha
            for sheet_name in self.config["google_sheets"]["sheets"]:
                try:
                    logger.info(f"📊 Processando planilha: {sheet_name}")
                    sheet_data = self._extract_sheet_data(gc, sheet_name)

                    if sheet_data:
                        extracted_data["data"][sheet_name] = sheet_data
                        extracted_data["metadata"]["sheets_processed"].append(
                            {
                                "name": sheet_name,
                                "tabs_count": len(sheet_data.get("tabs", {})),
                                "total_records": sum(
                                    len(tab.get("records", []))
                                    for tab in sheet_data.get("tabs", {}).values()
                                ),
                            }
                        )

                        self.extraction_stats["files_processed"] += 1
                        self.extraction_stats["records_extracted"] += sum(
                            len(tab.get("records", []))
                            for tab in sheet_data.get("tabs", {}).values()
                        )

                except Exception as e:
                    error_msg = f"Erro ao processar planilha {sheet_name}: {str(e)}"
                    logger.error(error_msg)
                    self.extraction_stats["errors"].append(error_msg)

            logger.info("✅ Extração do Google Sheets concluída")
            return extracted_data

        except Exception as e:
            error_msg = f"Erro crítico na extração do Google Sheets: {str(e)}"
            logger.error(error_msg)
            self.extraction_stats["errors"].append(error_msg)
            raise

    def _extract_sheet_data(self, gc, sheet_name: str) -> Dict[str, Any]:
        """
        Extrai dados de uma planilha específica

        Args:
            gc: Cliente gspread autorizado
            sheet_name: Nome da planilha

        Returns:
            Dados da planilha estruturados
        """
        try:
            # Abrir planilha
            spreadsheet = gc.open(sheet_name)
            sheet_info = {
                "name": sheet_name,
                "id": spreadsheet.id,
                "url": spreadsheet.url,
                "tabs": {},
            }

            # Processar cada aba
            for worksheet in spreadsheet.worksheets():
                try:
                    tab_name = worksheet.title
                    logger.info(f"  📋 Processando aba: {tab_name}")

                    # Obter todos os valores
                    all_values = worksheet.get_all_values()

                    if not all_values:
                        logger.warning(f"  ⚠️ Aba {tab_name} está vazia")
                        continue

                    # Processar dados da aba
                    tab_data = self._process_worksheet_data(all_values, tab_name)
                    sheet_info["tabs"][tab_name] = tab_data

                except Exception as e:
                    error_msg = f"Erro ao processar aba {worksheet.title}: {str(e)}"
                    logger.error(error_msg)
                    self.extraction_stats["errors"].append(error_msg)

            return sheet_info

        except Exception as e:
            logger.error(f"Erro ao acessar planilha {sheet_name}: {str(e)}")
            raise

    def _process_worksheet_data(
        self, all_values: List[List[str]], tab_name: str
    ) -> Dict[str, Any]:
        """
        Processa dados de uma aba da planilha

        Args:
            all_values: Todos os valores da aba
            tab_name: Nome da aba

        Returns:
            Dados processados da aba
        """
        if not all_values:
            return {"records": [], "headers": [], "metadata": {}}

        # Primeira linha são os cabeçalhos
        headers = [self._normalize_header(header) for header in all_values[0]]
        data_rows = all_values[1:]

        # Processar registros
        records = []
        for row_idx, row in enumerate(data_rows, start=2):  # Começar da linha 2
            try:
                # Criar registro
                record = {}
                for col_idx, value in enumerate(row):
                    if col_idx < len(headers):
                        header = headers[col_idx]
                        record[header] = self._clean_value(value)

                # Validar registro
                if self._validate_record(record, tab_name):
                    records.append(record)
                else:
                    warning_msg = (
                        f"Registro inválido na linha {row_idx} da aba {tab_name}"
                    )
                    logger.warning(warning_msg)
                    self.extraction_stats["warnings"].append(warning_msg)

            except Exception as e:
                error_msg = (
                    f"Erro ao processar linha {row_idx} da aba {tab_name}: {str(e)}"
                )
                logger.error(error_msg)
                self.extraction_stats["errors"].append(error_msg)

        # Metadados da aba
        metadata = {
            "total_rows": len(all_values),
            "data_rows": len(data_rows),
            "valid_records": len(records),
            "headers_count": len(headers),
            "headers": headers,
            "data_types": self._analyze_data_types(records, headers),
        }

        return {"records": records, "headers": headers, "metadata": metadata}

    def _normalize_header(self, header: str) -> str:
        """
        Normaliza cabeçalho da planilha

        Args:
            header: Cabeçalho original

        Returns:
            Cabeçalho normalizado
        """
        if not header:
            return f"coluna_{hashlib.md5(str(header).encode()).hexdigest()[:8]}"

        # Normalizar texto
        normalized = re.sub(r"[^\w\s]", "", header.strip())
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = normalized.lower()

        # Mapeamentos específicos do Sistema APRENDER
        header_mappings = {
            "nome_completo": "nome",
            "cpf": "cpf",
            "email": "email",
            "telefone": "telefone",
            "projeto": "projeto",
            "municipio": "municipio",
            "papel": "papel",
            "cargo": "cargo",
            "setor": "setor",
        }

        return header_mappings.get(normalized, normalized)

    def _clean_value(self, value: str) -> str:
        """
        Limpa e normaliza valor da célula

        Args:
            value: Valor original

        Returns:
            Valor limpo
        """
        if not value:
            return ""

        # Remover espaços extras
        cleaned = value.strip()

        # Normalizar quebras de linha
        cleaned = re.sub(r"\n+", " ", cleaned)

        # Limpar caracteres de controle
        cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", cleaned)

        return cleaned

    def _validate_record(self, record: Dict[str, str], tab_name: str) -> bool:
        """
        Valida um registro extraído

        Args:
            record: Registro a ser validado
            tab_name: Nome da aba para contexto

        Returns:
            True se válido, False caso contrário
        """
        try:
            # Verificar campos obrigatórios
            required_fields = self.config["data_validation"]["required_fields"]
            for field in required_fields:
                if field not in record or not record[field]:
                    return False

            # Validar CPF se presente
            if "cpf" in record and record["cpf"]:
                if not self._validate_cpf(record["cpf"]):
                    return False

            # Validar email se presente
            if "email" in record and record["email"]:
                if not self._validate_email(record["email"]):
                    return False

            # Validar telefone se presente
            if "telefone" in record and record["telefone"]:
                if not self._validate_phone(record["telefone"]):
                    return False

            return True

        except Exception as e:
            logger.error(f"Erro na validação do registro: {str(e)}")
            return False

    def _validate_cpf(self, cpf: str) -> bool:
        """
        Valida CPF brasileiro

        Args:
            cpf: CPF a ser validado

        Returns:
            True se válido, False caso contrário
        """
        # Remover caracteres não numéricos
        cpf = re.sub(r"\D", "", cpf)

        # Verificar tamanho
        if len(cpf) != self.config["data_validation"]["cpf_length"]:
            return False

        # Verificar se todos os dígitos são iguais
        if cpf == cpf[0] * len(cpf):
            return False

        # Validar dígitos verificadores
        try:
            # Calcular primeiro dígito
            sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
            digit1 = 11 - (sum1 % 11)
            if digit1 >= 10:
                digit1 = 0

            # Calcular segundo dígito
            sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
            digit2 = 11 - (sum2 % 11)
            if digit2 >= 10:
                digit2 = 0

            return int(cpf[9]) == digit1 and int(cpf[10]) == digit2

        except (ValueError, IndexError):
            return False

    def _validate_email(self, email: str) -> bool:
        """
        Valida formato de email

        Args:
            email: Email a ser validado

        Returns:
            True se válido, False caso contrário
        """
        pattern = self.config["data_validation"]["email_pattern"]
        return bool(re.match(pattern, email))

    def _validate_phone(self, phone: str) -> bool:
        """
        Valida formato de telefone

        Args:
            phone: Telefone a ser validado

        Returns:
            True se válido, False caso contrário
        """
        pattern = self.config["data_validation"]["phone_pattern"]
        return bool(re.match(pattern, phone))

    def _analyze_data_types(
        self, records: List[Dict[str, str]], headers: List[str]
    ) -> Dict[str, str]:
        """
        Analisa tipos de dados das colunas

        Args:
            records: Lista de registros
            headers: Lista de cabeçalhos

        Returns:
            Mapeamento de coluna para tipo de dado
        """
        data_types = {}

        for header in headers:
            values = [
                record.get(header, "") for record in records if record.get(header)
            ]

            if not values:
                data_types[header] = "empty"
                continue

            # Analisar tipo baseado nos valores
            if all(self._is_email(v) for v in values if v):
                data_types[header] = "email"
            elif all(self._is_cpf(v) for v in values if v):
                data_types[header] = "cpf"
            elif all(self._is_phone(v) for v in values if v):
                data_types[header] = "phone"
            elif all(self._is_date(v) for v in values if v):
                data_types[header] = "date"
            elif all(self._is_number(v) for v in values if v):
                data_types[header] = "number"
            else:
                data_types[header] = "text"

        return data_types

    def _is_email(self, value: str) -> bool:
        """Verifica se valor é email"""
        return self._validate_email(value)

    def _is_cpf(self, value: str) -> bool:
        """Verifica se valor é CPF"""
        return self._validate_cpf(value)

    def _is_phone(self, value: str) -> bool:
        """Verifica se valor é telefone"""
        return self._validate_phone(value)

    def _is_date(self, value: str) -> bool:
        """Verifica se valor é data"""
        date_patterns = [
            r"\d{2}/\d{2}/\d{4}",
            r"\d{4}-\d{2}-\d{2}",
            r"\d{2}-\d{2}-\d{4}",
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)

    def _is_number(self, value: str) -> bool:
        """Verifica se valor é número"""
        try:
            float(value.replace(",", "."))
            return True
        except ValueError:
            return False

    def save_extraction(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Salva dados extraídos em arquivo

        Args:
            data: Dados extraídos
            output_path: Caminho do arquivo de saída

        Returns:
            True se salvo com sucesso, False caso contrário
        """
        try:
            # Adicionar estatísticas de extração
            data["extraction_stats"] = self.extraction_stats
            data["extraction_stats"]["end_time"] = datetime.now(timezone.utc)
            data["extraction_stats"]["duration_seconds"] = (
                data["extraction_stats"]["end_time"]
                - data["extraction_stats"]["start_time"]
            ).total_seconds()

            # Salvar arquivo
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Dados salvos em: {output_path}")
            logger.info(
                f"📊 Estatísticas: {self.extraction_stats['files_processed']} arquivos, "
                f"{self.extraction_stats['records_extracted']} registros"
            )

            return True

        except Exception as e:
            logger.error(f"Erro ao salvar dados: {str(e)}")
            return False

    def get_extraction_report(self) -> str:
        """
        Gera relatório da extração

        Returns:
            Relatório em formato texto
        """
        stats = self.extraction_stats

        report = f"""
🧠 RELATÓRIO DE EXTRAÇÃO NEURAL - SISTEMA APRENDER
{'='*60}

📊 ESTATÍSTICAS GERAIS:
• Arquivos processados: {stats['files_processed']}
• Registros extraídos: {stats['records_extracted']}
• Erros encontrados: {len(stats['errors'])}
• Avisos gerados: {len(stats['warnings'])}

⏱️ TEMPO DE EXECUÇÃO:
• Início: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}
• Duração: {stats.get('duration_seconds', 0):.2f} segundos

"""

        if stats["errors"]:
            report += "❌ ERROS ENCONTRADOS:\n"
            for i, error in enumerate(stats["errors"], 1):
                report += f"{i}. {error}\n"
            report += "\n"

        if stats["warnings"]:
            report += "⚠️ AVISOS:\n"
            for i, warning in enumerate(stats["warnings"], 1):
                report += f"{i}. {warning}\n"
            report += "\n"

        if not stats["errors"] and not stats["warnings"]:
            report += "✅ Extração concluída sem erros ou avisos!\n"

        return report


def main():
    """
    Função principal do extrator neural
    """
    try:
        # Inicializar extrator
        extractor = NeuralDataExtractor()

        # Executar extração
        logger.info("🚀 Iniciando extração neural de dados")
        extracted_data = extractor.extract_from_google_sheets()

        # Salvar dados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"neural_extraction_{timestamp}.json"

        if extractor.save_extraction(extracted_data, output_file):
            logger.info("✅ Extração concluída com sucesso!")

            # Exibir relatório
            print(extractor.get_extraction_report())
        else:
            logger.error("❌ Falha ao salvar dados extraídos")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erro crítico na extração: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
