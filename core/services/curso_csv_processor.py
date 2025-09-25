import csv
import io
from typing import List, Dict, Any
from django.db import transaction
from django.utils import timezone
from core.models import CursoPlataforma, ImportacaoCursosCSV, Projeto

class CursoCSVProcessor:
    """Processador para importação de cursos da plataforma a partir de CSV"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def process_csv_content(self, csv_content: str, ano_filter: int = None) -> Dict[str, Any]:
        """
        Processa o conteúdo do CSV e importa os cursos

        Args:
            csv_content: Conteúdo do arquivo CSV como string
            ano_filter: Filtro por ano (opcional)

        Returns:
            Dict com estatísticas da importação
        """
        self.errors = []
        self.warnings = []

        try:
            # Limpar encoding malformado (caracteres separados por espaços)
            cleaned_content = self._clean_malformed_unicode(csv_content)

            csv_file = io.StringIO(cleaned_content)
            reader = csv.DictReader(csv_file, delimiter=';')

            # Mapear colunas (flexível para diferentes formatos)
            fieldnames = reader.fieldnames

            if fieldnames is None:
                raise ValueError("Arquivo CSV vazio ou mal formatado. Verifique se o arquivo contém dados válidos.")

            column_mapping = self._map_columns(fieldnames)

            if not column_mapping:
                raise ValueError("Não foi possível identificar as colunas necessárias no CSV")

            importacao = ImportacaoCursosCSV.objects.create(
                arquivo_nome="importacao_cursos.csv",
                status='PROCESSANDO'
            )

            cursos_criados = 0
            cursos_atualizados = 0

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        curso_data = self._extract_curso_data(row, column_mapping, ano_filter)
                        if not curso_data:
                            continue

                        curso, created = CursoPlataforma.objects.update_or_create(
                            id_curso=curso_data['id_curso'],
                            defaults=curso_data
                        )

                        if created:
                            cursos_criados += 1
                        else:
                            cursos_atualizados += 1

                        # Tentar vincular com projeto existente
                        self._try_link_projeto(curso)

                    except Exception as e:
                        self.errors.append(f"Erro na linha {row_num}: {str(e)}")

                importacao.cursos_importados = cursos_criados
                importacao.cursos_atualizados = cursos_atualizados
                importacao.status = 'CONCLUIDA' if len(self.errors) == 0 else 'ERRO'
                importacao.data_fim = timezone.now()
                importacao.log_processamento = f"Processado {cursos_criados + cursos_atualizados} cursos"
                if self.errors:
                    importacao.log_erros = "\n".join(self.errors)
                importacao.save()

            return {
                'importacao_id': importacao.id,
                'cursos_criados': cursos_criados,
                'cursos_atualizados': cursos_atualizados,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            self.errors.append(f"Erro geral no processamento: {str(e)}")
            return {
                'cursos_criados': 0,
                'cursos_atualizados': 0,
                'errors': self.errors,
                'warnings': self.warnings
            }

    def _detect_and_clean_encoding(self, content: str) -> str:
        """
        Detecta e limpa problemas de encoding, incluindo UTF-16 e espaçamento malformado
        """
        import re

        # Primeiro, verificar se há caracteres nulos (indicativo de UTF-16 mal decodificado)
        if '\x00' in content:
            # Remover caracteres nulos (típico de UTF-16 lido como latin1)
            content = content.replace('\x00', '')

        # Aplicar limpeza de espaçamento malformado
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            if not line.strip():
                continue

            # Verificar se a linha tem o padrão de espaços entre caracteres
            # Exemplo: '" I D "' -> '"ID"'
            if '" ' in line and ' "' in line:
                def clean_quoted_content(match):
                    content_inner = match.group(1)  # Conteúdo entre aspas
                    # Remove espaços únicos entre caracteres não-espaço
                    # Preserva espaços duplos/triplos como separadores de palavras
                    cleaned = ''
                    i = 0
                    while i < len(content_inner):
                        char = content_inner[i]
                        if char == ' ':
                            # Contar espaços consecutivos
                            space_count = 0
                            j = i
                            while j < len(content_inner) and content_inner[j] == ' ':
                                space_count += 1
                                j += 1

                            # Se há múltiplos espaços, isso indica separador de palavra
                            if space_count > 1:
                                cleaned += ' '  # Um espaço para separar palavras
                            # Se há apenas um espaço, é separador de caractere (remover)

                            i = j
                        else:
                            cleaned += char
                            i += 1

                    return f'"{cleaned}"'

                # Aplicar limpeza a todo conteúdo entre aspas
                cleaned_line = re.sub(r'"([^"]*)"', clean_quoted_content, line)
            else:
                cleaned_line = line

            cleaned_lines.append(cleaned_line)

        return '\n'.join(cleaned_lines)

    def _clean_malformed_unicode(self, content: str) -> str:
        """Método legado - mantido para compatibilidade"""
        return self._detect_and_clean_encoding(content)

    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """Mapeia as colunas do CSV para os campos esperados"""
        mapping = {}

        # Baseado na estrutura real do CSV: ID, Categoria, Nome breve, Nome completo, Inscritos
        for field in fieldnames:
            field_clean = field.strip()
            field_lower = field_clean.lower()

            if field_clean == 'ID':
                mapping['id'] = field
            elif field_clean == 'Categoria':
                mapping['categoria'] = field
            elif 'nome' in field_lower and ('breve' in field_lower or 'completo' in field_lower):
                # Preferir "Nome breve" se disponível
                if 'breve' in field_lower:
                    mapping['nome'] = field
                elif 'nome' not in mapping:  # Use completo se breve não estiver disponível
                    mapping['nome'] = field

        # Verificar se temos pelo menos ID e Nome
        if 'id' in mapping and 'nome' in mapping:
            return mapping

        return {}

    def _extract_curso_data(self, row: Dict[str, str], column_mapping: Dict[str, str], ano_filter: int = None) -> Dict[str, Any]:
        """Extrai os dados do curso de uma linha do CSV"""
        try:
            id_plataforma = row[column_mapping['id']].strip()
            nome_original = row[column_mapping['nome']].strip()

            if not id_plataforma or not nome_original:
                return None

            data = {
                'id_curso': id_plataforma,
                'nome_breve': nome_original,
                'nome_limpo': self._limpar_nome_curso(nome_original),
            }

            if 'categoria' in column_mapping:
                categoria = row[column_mapping['categoria']].strip()
                if categoria:
                    data['categoria'] = categoria

                    # Extrair ano da categoria se possível (formato "2025 Nome do Projeto")
                    categoria_parts = categoria.split()
                    if categoria_parts and categoria_parts[0].isdigit():
                        ano_from_categoria = int(categoria_parts[0])

                        # Aplicar filtro de ano se especificado
                        if ano_filter and ano_from_categoria != ano_filter:
                            return None

                        data['ano'] = ano_from_categoria

            return data

        except Exception as e:
            raise ValueError(f"Erro ao processar dados: {str(e)}")

    def _limpar_nome_curso(self, nome: str) -> str:
        """
        Aplica a lógica do script 'Limpar projetos' da planilha
        Remove prefixos comuns e limpa o nome do curso
        """
        nome = nome.strip()

        # Remover prefixos comuns (baseado no padrão da planilha)
        prefixes_to_remove = [
            'ACERTA LP - ',
            'ACERTA EF - ',
            'ACERTA EM - ',
            'SUPER - ',
            'VIDAS - ',
            'BRINCANDO - ',
        ]

        for prefix in prefixes_to_remove:
            if nome.startswith(prefix):
                nome = nome[len(prefix):]
                break

        # Limpar caracteres especiais e normalizar
        nome = nome.replace('  ', ' ')  # Remover espaços duplos
        nome = nome.strip()

        return nome

    def _try_link_projeto(self, curso: CursoPlataforma):
        """Tenta vincular automaticamente o curso com um projeto existente usando matching inteligente"""
        try:
            from core.models import ProjetoCursoLink, Projeto

            projeto_match = self._find_projeto_match(curso)

            if projeto_match:
                link, created = ProjetoCursoLink.objects.get_or_create(
                    curso_plataforma=curso,
                    defaults={'projeto': projeto_match}
                )
                if created:
                    self.warnings.append(
                        f"Vinculado automaticamente: '{curso.nome_limpo}' → {projeto_match.nome} ({projeto_match.categoria})"
                    )
            else:
                self.warnings.append(
                    f"Não foi possível vincular automaticamente o curso '{curso.nome_limpo}'"
                )

        except Exception as e:
            self.warnings.append(f"Erro ao tentar vincular curso '{curso.nome_limpo}': {str(e)}")

    def _find_projeto_match(self, curso: CursoPlataforma):
        """Encontra o melhor projeto para um curso usando padrões de matching"""
        from core.models import Projeto

        nome_original = curso.nome_breve.upper()
        nome_limpo = curso.nome_limpo.upper()
        categoria = curso.categoria.upper() if curso.categoria else ''

        # Padrões de matching para diferentes tipos de projeto
        padroes = [
            # ACERTA
            {'keywords': ['ACERTA'], 'projeto_nome': 'ACerta'},

            # Novo Lendo (categoria ou nome)
            {'keywords': ['NOVO LENDO'], 'projeto_nome': 'Super'},

            # Vidas
            {'keywords': ['VIDA', 'LINGUAGEM', 'MATEMATICA'], 'projeto_nome': 'Vidas'},

            # Brincando e Aprendendo
            {'keywords': ['BRINCANDO', 'APRENDENDO'], 'projeto_nome': 'Brincando e Aprendendo'},

            # Projeto AMMA
            {'keywords': ['AMMA'], 'projeto_nome': 'Outros'},

            # A Cor da Gente
            {'keywords': ['COR DA GENTE'], 'projeto_nome': 'Outros'},

            # TEMA
            {'keywords': ['TEMA'], 'projeto_nome': 'Outros'},

            # Avançando Juntos
            {'keywords': ['AVANCANDO', 'JUNTOS'], 'projeto_nome': 'Avançando Juntos'},
        ]

        # Testar cada padrão
        for padrao in padroes:
            keywords = padrao['keywords']
            projeto_nome = padrao['projeto_nome']

            # Verificar se alguma keyword está presente
            match_found = False
            for keyword in keywords:
                if keyword in nome_original or keyword in nome_limpo or keyword in categoria:
                    match_found = True
                    break

            if match_found:
                try:
                    projeto = Projeto.objects.get(nome=projeto_nome)
                    return projeto
                except Projeto.DoesNotExist:
                    continue

        # Se não encontrou match específico, tentar busca por similaridade
        return self._fuzzy_match_projeto(nome_limpo)

    def _fuzzy_match_projeto(self, nome_curso):
        """Busca por similaridade quando não há match direto"""
        from core.models import Projeto

        # Palavras-chave para cada projeto
        projeto_keywords = {
            'Super': ['SUPER', 'NOVO', 'LENDO'],
            'ACerta': ['ACERTA', 'LP', 'MATEMATICA'],
            'Vidas': ['VIDA', 'LINGUAGEM', 'CIENCIAS'],
            'Brincando e Aprendendo': ['BRINCANDO', 'INFANTIL', 'PRE'],
            'Outros': ['TEMA', 'AMMA', 'COR', 'FINANCEIRA'],
        }

        for projeto_nome, keywords in projeto_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in nome_curso:
                    score += 1

            # Se tem pelo menos 1 match, considerar
            if score > 0:
                try:
                    return Projeto.objects.get(nome=projeto_nome)
                except Projeto.DoesNotExist:
                    continue

        return None