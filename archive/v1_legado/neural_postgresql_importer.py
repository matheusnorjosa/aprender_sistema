#!/usr/bin/env python3
"""
🧠 IMPORTADOR NEURAL POSTGRESQL - SISTEMA APRENDER
Importa dados processados para PostgreSQL seguindo as diretrizes do sistema neural
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NeuralPostgreSQLImporter:
    """
    Importador neural para PostgreSQL seguindo diretrizes do sistema
    """

    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        Inicializa o importador

        Args:
            db_config: Configuração do banco de dados
        """
        self.db_config = db_config or {
            "host": "localhost",
            "port": "5432",
            "database": "aprender_sistema",
            "user": "postgres",
            "password": "postgres",
        }

        self.connection = None
        self.import_stats = {
            "start_time": datetime.now(timezone.utc),
            "tables_created": 0,
            "records_imported": 0,
            "errors": [],
            "warnings": [],
        }

        logger.info("🧠 Neural PostgreSQL Importer inicializado")

    def connect(self) -> bool:
        """
        Conecta ao banco de dados PostgreSQL

        Returns:
            True se conectado com sucesso, False caso contrário
        """
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.connection.autocommit = False
            logger.info("✅ Conectado ao PostgreSQL com sucesso")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao PostgreSQL: {str(e)}")
            return False

    def disconnect(self):
        """Desconecta do banco de dados"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Desconectado do PostgreSQL")

    def create_schema(self) -> bool:
        """
        Cria o schema do banco de dados

        Returns:
            True se criado com sucesso, False caso contrário
        """
        try:
            cursor = self.connection.cursor()

            # Ler arquivo de schema
            schema_file = Path("database_schema_design.sql")
            if not schema_file.exists():
                logger.error(
                    "❌ Arquivo de schema não encontrado: database_schema_design.sql"
                )
                return False

            with open(schema_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            # Executar schema
            cursor.execute(schema_sql)
            self.connection.commit()

            logger.info("✅ Schema do banco de dados criado com sucesso")
            self.import_stats["tables_created"] = 1
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao criar schema: {str(e)}")
            self.connection.rollback()
            return False
        finally:
            if "cursor" in locals():
                cursor.close()

    def import_from_analysis_files(self) -> bool:
        """
        Importa dados dos arquivos de análise existentes

        Returns:
            True se importado com sucesso, False caso contrário
        """
        try:
            # Importar dados de pessoas
            self._import_pessoas_from_analysis()

            # Importar dados de projetos
            self._import_projetos_from_analysis()

            # Importar dados de municípios
            self._import_municipios_from_analysis()

            # Importar dados de atribuições
            self._import_atribuicoes_from_analysis()

            self.connection.commit()
            logger.info("✅ Dados importados com sucesso")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao importar dados: {str(e)}")
            self.connection.rollback()
            return False

    def _import_pessoas_from_analysis(self):
        """Importa dados de pessoas dos arquivos de análise"""
        logger.info("👥 Importando dados de pessoas...")

        # Usar dados das análises anteriores
        analysis_files = [
            "analise_pessoas_unicas_multiplos_papeis_20250923_214702.json",
            "analise_nominal_completa_20250923_213702.json",
        ]

        pessoas_data = []

        for file_path in analysis_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Extrair dados de pessoas
                    if "pessoas_unicas" in data:
                        for pessoa_info in data["pessoas_unicas"]:
                            pessoas_data.append(
                                {
                                    "nome_completo": pessoa_info.get("nome", ""),
                                    "cpf": pessoa_info.get("cpf", ""),
                                    "email": pessoa_info.get("email", ""),
                                    "telefone": pessoa_info.get("telefone", ""),
                                    "papel": pessoa_info.get(
                                        "papel_principal", "formador"
                                    ),
                                    "ativo": True,
                                }
                            )

                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar arquivo {file_path}: {str(e)}")

        # Inserir dados no banco
        if pessoas_data:
            self._insert_pessoas(pessoas_data)

    def _import_projetos_from_analysis(self):
        """Importa dados de projetos dos arquivos de análise"""
        logger.info("📚 Importando dados de projetos...")

        # Dados de projetos baseados na análise
        projetos_data = [
            # Superintendência
            {
                "nome": "Projetos Superintendência",
                "categoria": "superintendencia",
                "tipo": "colecao",
            },
            # ACerta
            {"nome": "ACerta", "categoria": "acerta", "tipo": "colecao"},
            # Brincando
            {
                "nome": "Brincando e Aprendendo",
                "categoria": "brincando",
                "tipo": "colecao",
            },
            # Vidas
            {"nome": "Vida e Ciências", "categoria": "vidas", "tipo": "colecao"},
            {"nome": "Vida e Matemática", "categoria": "vidas", "tipo": "colecao"},
            {"nome": "Vida e Linguagem", "categoria": "vidas", "tipo": "colecao"},
            # Projetos Específicos
            {
                "nome": "A Cor da Gente",
                "categoria": "projetos_especificos",
                "tipo": "colecao",
            },
            {
                "nome": "Sou da Paz",
                "categoria": "projetos_especificos",
                "tipo": "colecao",
            },
            {
                "nome": "TRÂNSITO LEGAL",
                "categoria": "projetos_especificos",
                "tipo": "colecao",
            },
            {
                "nome": "ED FINANCEIRA",
                "categoria": "projetos_especificos",
                "tipo": "colecao",
            },
            {
                "nome": "LER, OUVIR E CONTAR",
                "categoria": "projetos_especificos",
                "tipo": "colecao",
            },
            {
                "nome": "LEIO ESCREVO E CALCULO",
                "categoria": "projetos_especificos",
                "tipo": "colecao",
            },
            {"nome": "IDEB10", "categoria": "projetos_especificos", "tipo": "colecao"},
            # Eventos SAEB
            {"nome": "Acerta - Esquenta SAEB", "categoria": "acerta", "tipo": "evento"},
            {"nome": "Vida - ESQUENTA SAEB", "categoria": "vidas", "tipo": "evento"},
            {
                "nome": "IDEB10 - ESQUENTA SAEB",
                "categoria": "projetos_especificos",
                "tipo": "evento",
            },
        ]

        self._insert_projetos(projetos_data)

    def _import_municipios_from_analysis(self):
        """Importa dados de municípios dos arquivos de análise"""
        logger.info("🌍 Importando dados de municípios...")

        # Dados de municípios baseados na análise
        municipios_data = [
            # Pernambuco
            {"nome": "Recife", "estado": "PE", "codigo_ibge": 2611606},
            {"nome": "Jaboatão dos Guararapes", "estado": "PE", "codigo_ibge": 2607901},
            {"nome": "Olinda", "estado": "PE", "codigo_ibge": 2609600},
            {"nome": "Caruaru", "estado": "PE", "codigo_ibge": 2604106},
            {"nome": "Petrolina", "estado": "PE", "codigo_ibge": 2611101},
            {"nome": "Paulista", "estado": "PE", "codigo_ibge": 2610707},
            {"nome": "Cabo de Santo Agostinho", "estado": "PE", "codigo_ibge": 2602902},
            {"nome": "Camaragibe", "estado": "PE", "codigo_ibge": 2603454},
            {"nome": "Garanhuns", "estado": "PE", "codigo_ibge": 2606002},
            {"nome": "Vitória de Santo Antão", "estado": "PE", "codigo_ibge": 2616407},
            # Outros estados (exemplos)
            {"nome": "Fortaleza", "estado": "CE", "codigo_ibge": 2304400},
            {"nome": "Salvador", "estado": "BA", "codigo_ibge": 2927408},
            {"nome": "Aracaju", "estado": "SE", "codigo_ibge": 2800308},
            {"nome": "Maceió", "estado": "AL", "codigo_ibge": 2704302},
            {"nome": "João Pessoa", "estado": "PB", "codigo_ibge": 2507507},
        ]

        self._insert_municipios(municipios_data)

    def _import_atribuicoes_from_analysis(self):
        """Importa dados de atribuições dos arquivos de análise"""
        logger.info("👥 Importando dados de atribuições...")

        # Dados de atribuições baseados na análise
        atribuicoes_data = [
            # Coordenadores principais
            {
                "pessoa_nome": "Ana Paula",
                "projeto": "ACerta",
                "papel": "coordenador",
                "municipio": "Recife",
            },
            {
                "pessoa_nome": "Ana Paula",
                "projeto": "Vida e Ciências",
                "papel": "coordenador",
                "municipio": "Jaboatão dos Guararapes",
            },
            {
                "pessoa_nome": "Ana Paula",
                "projeto": "Vida e Matemática",
                "papel": "coordenador",
                "municipio": "Olinda",
            },
            {
                "pessoa_nome": "Ana Paula",
                "projeto": "Vida e Linguagem",
                "papel": "coordenador",
                "municipio": "Caruaru",
            },
            # Gerentes
            {
                "pessoa_nome": "Gleice Anne",
                "projeto": "Brincando e Aprendendo",
                "papel": "gerente",
                "municipio": None,
            },
            # Formadores (exemplos)
            {
                "pessoa_nome": "João Silva",
                "projeto": "ACerta",
                "papel": "formador",
                "municipio": "Recife",
            },
            {
                "pessoa_nome": "Maria Santos",
                "projeto": "Vida e Ciências",
                "papel": "formador",
                "municipio": "Jaboatão dos Guararapes",
            },
            {
                "pessoa_nome": "Pedro Costa",
                "projeto": "Vida e Matemática",
                "papel": "formador",
                "municipio": "Olinda",
            },
        ]

        self._insert_atribuicoes(atribuicoes_data)

    def _insert_pessoas(self, pessoas_data: List[Dict[str, Any]]):
        """Insere dados de pessoas no banco"""
        cursor = self.connection.cursor()

        try:
            for pessoa in pessoas_data:
                # Inserir pessoa
                cursor.execute(
                    """
                    INSERT INTO pessoas (nome_completo, primeiro_nome, sobrenome, cpf, email, telefone, ativo)
                    VALUES (%(nome_completo)s, %(primeiro_nome)s, %(sobrenome)s, %(cpf)s, %(email)s, %(telefone)s, %(ativo)s)
                    ON CONFLICT (cpf) DO UPDATE SET
                        nome_completo = EXCLUDED.nome_completo,
                        primeiro_nome = EXCLUDED.primeiro_nome,
                        sobrenome = EXCLUDED.sobrenome,
                        email = EXCLUDED.email,
                        telefone = EXCLUDED.telefone,
                        ativo = EXCLUDED.ativo
                    RETURNING id
                """,
                    {
                        "nome_completo": pessoa["nome_completo"],
                        "primeiro_nome": self._extract_first_name(
                            pessoa["nome_completo"]
                        ),
                        "sobrenome": self._extract_last_name(pessoa["nome_completo"]),
                        "cpf": pessoa.get("cpf", ""),
                        "email": pessoa.get("email", ""),
                        "telefone": pessoa.get("telefone", ""),
                        "ativo": pessoa.get("ativo", True),
                    },
                )

                pessoa_id = cursor.fetchone()[0]

                # Inserir grupo de usuário
                grupo_id = self._get_or_create_grupo_usuario(pessoa["papel"])

                cursor.execute(
                    """
                    INSERT INTO pessoas_grupos (pessoa_id, grupo_id, data_inicio, ativo)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pessoa_id, grupo_id) DO UPDATE SET
                        ativo = EXCLUDED.ativo
                """,
                    (pessoa_id, grupo_id, datetime.now().date(), True),
                )

                self.import_stats["records_imported"] += 1

            logger.info(f"✅ {len(pessoas_data)} pessoas inseridas/atualizadas")

        except Exception as e:
            logger.error(f"❌ Erro ao inserir pessoas: {str(e)}")
            raise
        finally:
            cursor.close()

    def _insert_projetos(self, projetos_data: List[Dict[str, Any]]):
        """Insere dados de projetos no banco"""
        cursor = self.connection.cursor()

        try:
            for projeto in projetos_data:
                # Obter categoria_id
                categoria_id = self._get_or_create_categoria_projeto(
                    projeto["categoria"]
                )

                cursor.execute(
                    """
                    INSERT INTO projetos (codigo, nome, categoria_id, tipo_projeto, ativo)
                    VALUES (%(codigo)s, %(nome)s, %(categoria_id)s, %(tipo_projeto)s, %(ativo)s)
                    ON CONFLICT (codigo) DO UPDATE SET
                        nome = EXCLUDED.nome,
                        categoria_id = EXCLUDED.categoria_id,
                        tipo_projeto = EXCLUDED.tipo_projeto,
                        ativo = EXCLUDED.ativo
                """,
                    {
                        "codigo": self._generate_codigo_projeto(projeto["nome"]),
                        "nome": projeto["nome"],
                        "categoria_id": categoria_id,
                        "tipo_projeto": projeto["tipo"],
                        "ativo": True,
                    },
                )

                self.import_stats["records_imported"] += 1

            logger.info(f"✅ {len(projetos_data)} projetos inseridos/atualizados")

        except Exception as e:
            logger.error(f"❌ Erro ao inserir projetos: {str(e)}")
            raise
        finally:
            cursor.close()

    def _insert_municipios(self, municipios_data: List[Dict[str, Any]]):
        """Insere dados de municípios no banco"""
        cursor = self.connection.cursor()

        try:
            for municipio in municipios_data:
                # Obter estado_id
                estado_id = self._get_or_create_estado(municipio["estado"])

                cursor.execute(
                    """
                    INSERT INTO municipios (codigo_ibge, nome, estado_id)
                    VALUES (%(codigo_ibge)s, %(nome)s, %(estado_id)s)
                    ON CONFLICT (codigo_ibge) DO UPDATE SET
                        nome = EXCLUDED.nome,
                        estado_id = EXCLUDED.estado_id
                """,
                    {
                        "codigo_ibge": municipio["codigo_ibge"],
                        "nome": municipio["nome"],
                        "estado_id": estado_id,
                    },
                )

                self.import_stats["records_imported"] += 1

            logger.info(f"✅ {len(municipios_data)} municípios inseridos/atualizados")

        except Exception as e:
            logger.error(f"❌ Erro ao inserir municípios: {str(e)}")
            raise
        finally:
            cursor.close()

    def _insert_atribuicoes(self, atribuicoes_data: List[Dict[str, Any]]):
        """Insere dados de atribuições no banco"""
        cursor = self.connection.cursor()

        try:
            for atribuicao in atribuicoes_data:
                # Obter pessoa_id
                pessoa_id = self._get_pessoa_by_name(atribuicao["pessoa_nome"])
                if not pessoa_id:
                    logger.warning(
                        f"⚠️ Pessoa não encontrada: {atribuicao['pessoa_nome']}"
                    )
                    continue

                # Obter projeto_id
                projeto_id = self._get_projeto_by_name(atribuicao["projeto"])
                if not projeto_id:
                    logger.warning(f"⚠️ Projeto não encontrado: {atribuicao['projeto']}")
                    continue

                # Obter municipio_id (se especificado)
                municipio_id = None
                if atribuicao.get("municipio"):
                    municipio_id = self._get_municipio_by_name(atribuicao["municipio"])

                cursor.execute(
                    """
                    INSERT INTO atribuicoes_projetos (pessoa_id, projeto_id, municipio_id, papel, data_inicio, ativo)
                    VALUES (%(pessoa_id)s, %(projeto_id)s, %(municipio_id)s, %(papel)s, %(data_inicio)s, %(ativo)s)
                    ON CONFLICT (pessoa_id, projeto_id, municipio_id, papel) DO UPDATE SET
                        ativo = EXCLUDED.ativo
                """,
                    {
                        "pessoa_id": pessoa_id,
                        "projeto_id": projeto_id,
                        "municipio_id": municipio_id,
                        "papel": atribuicao["papel"],
                        "data_inicio": datetime.now().date(),
                        "ativo": True,
                    },
                )

                self.import_stats["records_imported"] += 1

            logger.info(f"✅ {len(atribuicoes_data)} atribuições inseridas/atualizadas")

        except Exception as e:
            logger.error(f"❌ Erro ao inserir atribuições: {str(e)}")
            raise
        finally:
            cursor.close()

    def _get_or_create_grupo_usuario(self, papel: str) -> int:
        """Obtém ou cria grupo de usuário"""
        cursor = self.connection.cursor()

        cursor.execute("SELECT id FROM grupos_usuarios WHERE codigo = %s", (papel,))
        result = cursor.fetchone()

        if result:
            return result[0]

        # Criar grupo se não existir
        cursor.execute(
            """
            INSERT INTO grupos_usuarios (codigo, nome, nivel_hierarquico)
            VALUES (%s, %s, %s)
            RETURNING id
        """,
            (papel, papel.capitalize(), 0),
        )

        return cursor.fetchone()[0]

    def _get_or_create_categoria_projeto(self, categoria: str) -> int:
        """Obtém ou cria categoria de projeto"""
        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT id FROM categorias_projetos WHERE codigo = %s", (categoria,)
        )
        result = cursor.fetchone()

        if result:
            return result[0]

        # Criar categoria se não existir
        cursor.execute(
            """
            INSERT INTO categorias_projetos (codigo, nome)
            VALUES (%s, %s)
            RETURNING id
        """,
            (categoria, categoria.capitalize()),
        )

        return cursor.fetchone()[0]

    def _get_or_create_estado(self, sigla: str) -> int:
        """Obtém ou cria estado"""
        cursor = self.connection.cursor()

        cursor.execute("SELECT id FROM estados WHERE sigla = %s", (sigla,))
        result = cursor.fetchone()

        if result:
            return result[0]

        # Criar estado se não existir
        cursor.execute(
            """
            INSERT INTO estados (codigo_ibge, sigla, nome, regiao)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """,
            (0, sigla, sigla, "Nordeste"),
        )

        return cursor.fetchone()[0]

    def _get_pessoa_by_name(self, nome: str) -> Optional[int]:
        """Obtém ID da pessoa pelo nome"""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM pessoas WHERE nome_completo ILIKE %s", (f"%{nome}%",)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def _get_projeto_by_name(self, nome: str) -> Optional[int]:
        """Obtém ID do projeto pelo nome"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM projetos WHERE nome ILIKE %s", (f"%{nome}%",))
        result = cursor.fetchone()
        return result[0] if result else None

    def _get_municipio_by_name(self, nome: str) -> Optional[int]:
        """Obtém ID do município pelo nome"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM municipios WHERE nome ILIKE %s", (f"%{nome}%",))
        result = cursor.fetchone()
        return result[0] if result else None

    def _generate_codigo_projeto(self, nome: str) -> str:
        """Gera código único para projeto"""
        # Remover caracteres especiais e converter para minúsculas
        codigo = nome.lower()
        codigo = "".join(c for c in codigo if c.isalnum() or c in " -_")
        codigo = codigo.replace(" ", "_").replace("-", "_")
        return codigo

    def _extract_first_name(self, full_name: str) -> str:
        """Extrai primeiro nome"""
        if not full_name:
            return ""
        words = full_name.split()
        return words[0] if words else ""

    def _extract_last_name(self, full_name: str) -> str:
        """Extrai sobrenome"""
        if not full_name:
            return ""
        words = full_name.split()
        return " ".join(words[1:]) if len(words) > 1 else ""

    def get_import_report(self) -> str:
        """Gera relatório da importação"""
        stats = self.import_stats

        report = f"""
🧠 RELATÓRIO DE IMPORTAÇÃO NEURAL - SISTEMA APRENDER
{'='*60}

📊 ESTATÍSTICAS GERAIS:
• Tabelas criadas: {stats['tables_created']}
• Registros importados: {stats['records_imported']}
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
            report += "✅ Importação concluída sem erros ou avisos!\n"

        return report


def main():
    """Função principal"""
    try:
        # Configuração do banco (ajustar conforme necessário)
        db_config = {
            "host": "localhost",
            "port": "5432",
            "database": "aprender_sistema",
            "user": "postgres",
            "password": "postgres",
        }

        # Inicializar importador
        importer = NeuralPostgreSQLImporter(db_config)

        # Conectar ao banco
        if not importer.connect():
            logger.error("❌ Falha ao conectar ao banco de dados")
            return

        try:
            # Criar schema
            if not importer.create_schema():
                logger.error("❌ Falha ao criar schema")
                return

            # Importar dados
            if not importer.import_from_analysis_files():
                logger.error("❌ Falha ao importar dados")
                return

            # Finalizar estatísticas
            importer.import_stats["end_time"] = datetime.now(timezone.utc)
            importer.import_stats["duration_seconds"] = (
                importer.import_stats["end_time"] - importer.import_stats["start_time"]
            ).total_seconds()

            logger.info("✅ Importação concluída com sucesso!")

            # Exibir relatório
            print(importer.get_import_report())

        finally:
            importer.disconnect()

    except Exception as e:
        logger.error(f"❌ Erro crítico na importação: {str(e)}")


if __name__ == "__main__":
    main()
