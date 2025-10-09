#!/usr/bin/env python3
"""
🧠 PROCESSADOR NEURAL ROBUSTO - SISTEMA APRENDER
===============================================

Processador robusto para extrair e tratar dados do Google Sheets
seguindo as diretrizes do sistema neural.

Author: Claude Code
Date: Setembro 2025
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NeuralRobustProcessor:
    """
    Processador neural robusto para dados do Google Sheets
    """

    def __init__(self, input_file: str = None):
        self.input_file = input_file or self._find_latest_mapping_file()
        self.processed_data = {
            "metadata": {
                "processing_time": datetime.now().isoformat(),
                "processor_version": "2.0.0",
                "source_file": self.input_file,
                "statistics": {},
            },
            "pessoas": {},
            "projetos": {},
            "municipios": {},
            "atribuicoes": {},
            "eventos": {},
            "solicitacoes": {},
            "processing_stats": {
                "start_time": datetime.now().isoformat(),
                "files_processed": 0,
                "records_processed": 0,
                "errors": [],
                "warnings": [],
                "end_time": None,
                "duration_seconds": 0,
            },
        }

    def _find_latest_mapping_file(self) -> str:
        """Encontra o arquivo de mapeamento mais recente"""
        mapping_files = list(Path(".").glob("mapeamento_completo_google_sheets_*.json"))
        if not mapping_files:
            raise FileNotFoundError("Nenhum arquivo de mapeamento encontrado")

        latest_file = max(mapping_files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)

    def process(self) -> Dict[str, Any]:
        """Processa os dados do arquivo de mapeamento"""
        logger.info(f"🔄 Processando dados do arquivo: {self.input_file}")

        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Processar cada planilha
            for sheet_name, sheet_data in raw_data.get("planilhas", {}).items():
                try:
                    logger.info(f"📊 Processando planilha: {sheet_name}")
                    self._process_sheet(sheet_name, sheet_data)
                    self.processed_data["processing_stats"]["files_processed"] += 1

                except Exception as e:
                    error_msg = f"Erro ao processar planilha {sheet_name}: {str(e)}"
                    logger.error(error_msg)
                    self.processed_data["processing_stats"]["errors"].append(error_msg)

            # Calcular estatísticas finais
            self._calculate_final_statistics()

            # Salvar dados processados
            output_file = f"neural_robust_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.processed_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Dados salvos em: {output_file}")

            # Relatório final
            self._print_final_report()

            return self.processed_data

        except Exception as e:
            logger.error(f"❌ Erro no processamento: {str(e)}")
            raise

    def _process_sheet(self, sheet_name: str, sheet_data: Dict[str, Any]):
        """Processa uma planilha específica"""

        # Processar planilha de usuários
        if "usuarios" in sheet_name.lower():
            self._process_usuarios_sheet(sheet_data)

        # Processar planilha de controle
        elif "controle" in sheet_name.lower():
            self._process_controle_sheet(sheet_data)

        # Processar planilha de acompanhamento
        elif "acompanhamento" in sheet_name.lower():
            self._process_acompanhamento_sheet(sheet_data)

        # Processar planilha de disponibilidade
        elif "disponibilidade" in sheet_name.lower():
            self._process_disponibilidade_sheet(sheet_data)

    def _process_usuarios_sheet(self, sheet_data: Dict[str, Any]):
        """Processa planilha de usuários"""
        logger.info("👥 Processando planilha de usuários")

        for aba in sheet_data.get("abas", []):
            aba_name = aba.get("nome", "")
            logger.info(f"  📋 Processando aba: {aba_name}")

            # Determinar status baseado no nome da aba
            status = (
                "ativo"
                if "ativo" in aba_name.lower()
                else (
                    "inativo"
                    if "inativo" in aba_name.lower()
                    else "pendente" if "pendente" in aba_name.lower() else "ativo"
                )
            )

            # Processar dados da aba
            self._process_usuarios_aba(aba, status)

    def _process_usuarios_aba(self, aba_data: Dict[str, Any], status: str):
        """Processa uma aba específica de usuários"""
        headers = aba_data.get("cabecalhos", [])
        amostra_dados = aba_data.get("amostra_dados", [])

        if not headers or len(amostra_dados) < 2:
            logger.warning(f"    ⚠️ Aba sem dados válidos: {aba_data.get('nome', '')}")
            return

        # Mapear índices das colunas
        col_indices = {}
        for i, header in enumerate(headers):
            if header:
                col_indices[header.lower()] = i

        # Processar cada linha de dados (pular cabeçalho)
        for row in amostra_dados[1:]:
            if not row or len(row) < len(headers):
                continue

            try:
                pessoa_data = self._extract_pessoa_data(row, col_indices, status)
                if pessoa_data:
                    self._add_pessoa(pessoa_data)
                    self.processed_data["processing_stats"]["records_processed"] += 1

            except Exception as e:
                error_msg = f"Erro ao processar linha de usuário: {str(e)}"
                logger.warning(f"    ⚠️ {error_msg}")
                self.processed_data["processing_stats"]["warnings"].append(error_msg)

    def _extract_pessoa_data(
        self, row: List[str], col_indices: Dict[str, int], status: str
    ) -> Optional[Dict[str, Any]]:
        """Extrai dados de uma pessoa de uma linha"""

        # Extrair dados básicos
        nome_completo = self._get_cell_value(
            row, col_indices, ["nome completo", "nome"]
        )
        if not nome_completo:
            return None

        cpf = self._get_cell_value(row, col_indices, ["cpf"])
        email = self._get_cell_value(row, col_indices, ["email"])
        telefone = self._get_cell_value(row, col_indices, ["telefone"])
        cargo = self._get_cell_value(row, col_indices, ["cargo"])
        gerencia = self._get_cell_value(
            row, col_indices, ["gerência", "gerencia", "projeto"]
        )

        # Limpar e normalizar dados
        nome_completo = self._normalize_name(nome_completo)
        cpf = self._clean_cpf(cpf)
        email = self._clean_email(email)

        if not nome_completo:
            return None

        # Gerar ID único
        pessoa_id = self._generate_id(f"pessoa_{nome_completo}_{cpf}")

        return {
            "id": pessoa_id,
            "nome_completo": nome_completo,
            "cpf": cpf,
            "email": email,
            "telefone": telefone,
            "cargo": cargo,
            "gerencia": gerencia,
            "status": status,
            "roles": self._extract_roles(cargo),
            "created_at": datetime.now().isoformat(),
        }

    def _get_cell_value(
        self, row: List[str], col_indices: Dict[str, int], possible_keys: List[str]
    ) -> str:
        """Obtém valor de uma célula baseado em possíveis nomes de coluna"""
        for key in possible_keys:
            if key in col_indices:
                idx = col_indices[key]
                if idx < len(row):
                    value = str(row[idx]).strip()
                    if value and value != "None":
                        return value
        return ""

    def _normalize_name(self, name: str) -> str:
        """Normaliza nome"""
        if not name:
            return ""

        # Remover caracteres especiais e normalizar espaços
        import re

        name = re.sub(r"[^\w\s]", "", name)
        name = " ".join(name.split())

        return name.title()

    def _clean_cpf(self, cpf: str) -> str:
        """Limpa e valida CPF"""
        if not cpf:
            return ""

        # Remover caracteres não numéricos
        import re

        cpf_clean = re.sub(r"[^\d]", "", cpf)

        # Validar se tem 11 dígitos
        if len(cpf_clean) == 11:
            return cpf_clean

        return ""

    def _clean_email(self, email: str) -> str:
        """Limpa email"""
        if not email:
            return ""

        email = email.strip().lower()

        # Remover caracteres de controle
        import re

        email = re.sub(r"[\t\n\r]", "", email)

        # Validar formato básico
        if "@" in email and "." in email:
            return email

        return ""

    def _extract_roles(self, cargo: str) -> List[str]:
        """Extrai roles baseado no cargo"""
        if not cargo:
            return []

        roles = []
        cargo_lower = cargo.lower()

        if "formador" in cargo_lower:
            roles.append("Formador")
        if "coordenador" in cargo_lower:
            roles.append("Coordenador")
        if "gerente" in cargo_lower:
            roles.append("Gerente")
        if "superintendente" in cargo_lower:
            roles.append("Superintendente")

        return roles

    def _add_pessoa(self, pessoa_data: Dict[str, Any]):
        """Adiciona pessoa aos dados processados"""
        pessoa_id = pessoa_data["id"]

        # Verificar se já existe
        if pessoa_id in self.processed_data["pessoas"]:
            # Atualizar dados existentes
            existing = self.processed_data["pessoas"][pessoa_id]
            existing.update(pessoa_data)
            existing["updated_at"] = datetime.now().isoformat()
        else:
            # Adicionar nova pessoa
            self.processed_data["pessoas"][pessoa_id] = pessoa_data

    def _process_controle_sheet(self, sheet_data: Dict[str, Any]):
        """Processa planilha de controle"""
        logger.info("🎛️ Processando planilha de controle")
        # Implementar processamento de controle se necessário

    def _process_acompanhamento_sheet(self, sheet_data: Dict[str, Any]):
        """Processa planilha de acompanhamento"""
        logger.info("📊 Processando planilha de acompanhamento")
        # Implementar processamento de acompanhamento se necessário

    def _process_disponibilidade_sheet(self, sheet_data: Dict[str, Any]):
        """Processa planilha de disponibilidade"""
        logger.info("📅 Processando planilha de disponibilidade")
        # Implementar processamento de disponibilidade se necessário

    def _generate_id(self, base_string: str) -> str:
        """Gera ID único baseado em string"""
        import hashlib

        hash_obj = hashlib.md5(base_string.encode())
        return hash_obj.hexdigest()[:12]

    def _calculate_final_statistics(self):
        """Calcula estatísticas finais"""
        stats = self.processed_data["metadata"]["statistics"]
        stats.update(
            {
                "total_pessoas": len(self.processed_data["pessoas"]),
                "total_projetos": len(self.processed_data["projetos"]),
                "total_municipios": len(self.processed_data["municipios"]),
                "total_eventos": len(self.processed_data["eventos"]),
                "total_atribuicoes": len(self.processed_data["atribuicoes"]),
                "total_solicitacoes": len(self.processed_data["solicitacoes"]),
            }
        )

        # Finalizar estatísticas de processamento
        end_time = datetime.now()
        start_time = datetime.fromisoformat(
            self.processed_data["processing_stats"]["start_time"]
        )
        duration = (end_time - start_time).total_seconds()

        self.processed_data["processing_stats"]["end_time"] = end_time.isoformat()
        self.processed_data["processing_stats"]["duration_seconds"] = duration

    def _print_final_report(self):
        """Imprime relatório final"""
        stats = self.processed_data["metadata"]["statistics"]

        print("\n🧠 RELATÓRIO DE PROCESSAMENTO NEURAL ROBUSTO - SISTEMA APRENDER")
        print("=" * 70)
        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"• Pessoas identificadas: {stats['total_pessoas']}")
        print(f"• Projetos identificados: {stats['total_projetos']}")
        print(f"• Municípios identificados: {stats['total_municipios']}")
        print(f"• Eventos identificados: {stats['total_eventos']}")
        print(f"• Atribuições identificadas: {stats['total_atribuicoes']}")

        processing_stats = self.processed_data["processing_stats"]
        print(f"\n⏱️ ESTATÍSTICAS DE PROCESSAMENTO:")
        print(f"• Arquivos processados: {processing_stats['files_processed']}")
        print(f"• Registros processados: {processing_stats['records_processed']}")
        print(f"• Erros encontrados: {len(processing_stats['errors'])}")
        print(f"• Avisos gerados: {len(processing_stats['warnings'])}")
        print(f"• Tempo de processamento: {processing_stats['duration_seconds']:.2f}s")

        if processing_stats["errors"]:
            print(f"\n❌ ERROS ENCONTRADOS:")
            for error in processing_stats["errors"]:
                print(f"  • {error}")

        if processing_stats["warnings"]:
            print(f"\n⚠️ AVISOS GERADOS:")
            for warning in processing_stats["warnings"][
                :5
            ]:  # Mostrar apenas os primeiros 5
                print(f"  • {warning}")
            if len(processing_stats["warnings"]) > 5:
                print(f"  ... e mais {len(processing_stats['warnings']) - 5} avisos")

        print(f"\n✅ Processamento concluído com sucesso!")


def main():
    """Função principal"""
    try:
        processor = NeuralRobustProcessor()
        result = processor.process()

        print(f"\n🎯 Processamento concluído!")
        print(f"📁 Arquivo de saída: neural_robust_processed_*.json")

        return result

    except Exception as e:
        logger.error(f"❌ Erro no processamento: {str(e)}")
        raise


if __name__ == "__main__":
    main()
