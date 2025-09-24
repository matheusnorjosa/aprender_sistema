#!/usr/bin/env python3
"""
🧠 PROCESSADOR DE DADOS NEURAL - SISTEMA APRENDER
Baseado nas diretrizes do sistema neural e dados extraídos

Este processador implementa:
- Validação de segurança
- Padrões de código Python/Django
- Tratamento robusto de dados
- Logging estruturado
- Tratamento de exceções específicas
- Análise com Pandas
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neural_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NeuralDataProcessor:
    """
    Processador de dados seguindo diretrizes do sistema neural
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o processador neural
        
        Args:
            config_path: Caminho para arquivo de configuração
        """
        self.config = self._load_config(config_path)
        self.processing_stats = {
            'start_time': datetime.now(timezone.utc),
            'files_processed': 0,
            'records_processed': 0,
            'errors': [],
            'warnings': []
        }
        
        logger.info("🧠 Neural Data Processor inicializado")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do processador
        
        Args:
            config_path: Caminho para arquivo de configuração
            
        Returns:
            Dicionário com configurações
        """
        default_config = {
            'data_validation': {
                'cpf_length': 11,
                'email_pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'phone_pattern': r'^\+?[\d\s\-\(\)]+$',
                'required_fields': ['nome', 'email']
            },
            'organizational_structure': {
                'categorias': {
                    'superintendencia': {
                        'nome': 'Superintendência',
                        'cor': '#1f77b4',
                        'projetos': []
                    },
                    'acerta': {
                        'nome': 'ACerta',
                        'cor': '#ff7f0e',
                        'projetos': []
                    },
                    'brincando': {
                        'nome': 'Brincando',
                        'cor': '#2ca02c',
                        'projetos': []
                    },
                    'vidas': {
                        'nome': 'Vidas',
                        'cor': '#d62728',
                        'projetos': ['Vida e Ciências', 'Vida e Matemática', 'Vida e Linguagem']
                    },
                    'projetos_especificos': {
                        'nome': 'Projetos Específicos',
                        'cor': '#9467bd',
                        'projetos': []
                    }
                },
                'setores': {
                    'superintendencia': {'nome': 'Superintendência', 'sigla': 'SUP'},
                    'acerta': {'nome': 'ACerta', 'sigla': 'ACE'},
                    'brincando': {'nome': 'Brincando', 'sigla': 'BRI'},
                    'vidas': {'nome': 'Vidas', 'sigla': 'VID'},
                    'controle': {'nome': 'Controle', 'sigla': 'CON'},
                    'dat': {'nome': 'DAT', 'sigla': 'DAT'}
                },
                'grupos_usuarios': {
                    'formador': {'nome': 'Formador', 'nivel': 0},
                    'coordenador': {'nome': 'Coordenador', 'nivel': 1},
                    'gerente': {'nome': 'Gerente', 'nivel': 2},
                    'superintendencia': {'nome': 'Superintendência', 'nivel': 3},
                    'controle': {'nome': 'Controle', 'nivel': 1},
                    'dat': {'nome': 'DAT', 'nivel': 1}
                }
            },
            'output': {
                'format': 'json',
                'include_metadata': True,
                'compress': False
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"✅ Configuração carregada de {config_path}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar configuração: {e}")
                logger.info("📋 Usando configuração padrão")
        
        return default_config
    
    def process_google_sheets_data(self, input_file: str) -> Dict[str, Any]:
        """
        Processa dados extraídos do Google Sheets
        
        Args:
            input_file: Caminho para arquivo de dados extraídos
            
        Returns:
            Dados processados e estruturados
        """
        logger.info(f"🔄 Processando dados do arquivo: {input_file}")
        
        try:
            # Carregar dados extraídos
            with open(input_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            processed_data = {
                'metadata': {
                    'processing_time': datetime.now(timezone.utc).isoformat(),
                    'processor_version': '1.0.0',
                    'source_file': input_file,
                    'source_metadata': raw_data.get('metadata', {})
                },
                'pessoas': {},
                'projetos': {},
                'municipios': {},
                'atribuicoes': {},
                'eventos': {},
                'solicitacoes': {}
            }
            
            # Processar cada planilha
            for sheet_name, sheet_data in raw_data.get('planilhas', {}).items():
                try:
                    logger.info(f"📊 Processando planilha: {sheet_name}")
                    self._process_sheet(sheet_name, sheet_data, processed_data)
                    self.processing_stats['files_processed'] += 1
                    
                except Exception as e:
                    error_msg = f"Erro ao processar planilha {sheet_name}: {str(e)}"
                    logger.error(error_msg)
                    self.processing_stats['errors'].append(error_msg)
            
            # Pós-processamento e validação
            self._post_process_data(processed_data)
            
            logger.info("✅ Processamento concluído")
            return processed_data
            
        except Exception as e:
            error_msg = f"Erro crítico no processamento: {str(e)}"
            logger.error(error_msg)
            self.processing_stats['errors'].append(error_msg)
            raise
    
    def _process_sheet(self, sheet_name: str, sheet_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        """
        Processa uma planilha específica
        
        Args:
            sheet_name: Nome da planilha
            sheet_data: Dados da planilha
            processed_data: Dados processados (modificado in-place)
        """
        for tab_data in sheet_data.get('abas', []):
            tab_name = tab_data.get('nome', '')
            try:
                logger.info(f"  📋 Processando aba: {tab_name}")
                
                # Processar baseado no tipo de aba
                if 'usuarios' in sheet_name.lower() or 'usuários' in sheet_name.lower():
                    self._process_usuarios_tab(tab_name, tab_data, processed_data)
                elif 'controle' in sheet_name.lower():
                    self._process_controle_tab(tab_name, tab_data, processed_data)
                elif 'acompanhamento' in sheet_name.lower() or 'agenda' in sheet_name.lower():
                    self._process_agenda_tab(tab_name, tab_data, processed_data)
                elif 'disponibilidade' in sheet_name.lower():
                    self._process_disponibilidade_tab(tab_name, tab_data, processed_data)
                
                self.processing_stats['records_processed'] += len(tab_data.get('records', []))
                
            except Exception as e:
                error_msg = f"Erro ao processar aba {tab_name}: {str(e)}"
                logger.error(error_msg)
                self.processing_stats['errors'].append(error_msg)
    
    def _process_usuarios_tab(self, tab_name: str, tab_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        """
        Processa aba de usuários
        
        Args:
            tab_name: Nome da aba
            tab_data: Dados da aba
            processed_data: Dados processados (modificado in-place)
        """
        for record in tab_data.get('records', []):
            try:
                # Extrair dados da pessoa
                pessoa_data = self._extract_pessoa_data(record)
                if not pessoa_data:
                    continue
                
                # Gerar ID único
                pessoa_id = self._generate_pessoa_id(pessoa_data)
                
                # Adicionar à estrutura de pessoas
                if pessoa_id not in processed_data['pessoas']:
                    processed_data['pessoas'][pessoa_id] = pessoa_data
                else:
                    # Mesclar dados se já existir
                    processed_data['pessoas'][pessoa_id] = self._merge_pessoa_data(
                        processed_data['pessoas'][pessoa_id], 
                        pessoa_data
                    )
                
            except Exception as e:
                error_msg = f"Erro ao processar registro de usuário: {str(e)}"
                logger.error(error_msg)
                self.processing_stats['errors'].append(error_msg)
    
    def _process_controle_tab(self, tab_name: str, tab_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        """
        Processa aba de controle
        
        Args:
            tab_name: Nome da aba
            tab_data: Dados da aba
            processed_data: Dados processados (modificado in-place)
        """
        # Processar diferentes tipos de abas de controle
        if 'coord' in tab_name.lower():
            self._process_coordenadores_tab(tab_name, tab_data, processed_data)
        elif 'config' in tab_name.lower():
            self._process_config_tab(tab_name, tab_data, processed_data)
        elif 'formações' in tab_name.lower():
            self._process_formacoes_tab(tab_name, tab_data, processed_data)
    
    def _process_agenda_tab(self, tab_name: str, tab_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        """
        Processa aba de agenda
        
        Args:
            tab_name: Nome da aba
            tab_data: Dados da aba
            processed_data: Dados processados (modificado in-place)
        """
        # Identificar categoria do projeto baseado no nome da aba
        categoria = self._identify_project_category(tab_name)
        
        for record in tab_data.get('records', []):
            try:
                # Extrair dados do evento
                evento_data = self._extract_evento_data(record, categoria)
                if not evento_data:
                    continue
                
                # Adicionar à estrutura de eventos
                evento_id = self._generate_evento_id(evento_data)
                processed_data['eventos'][evento_id] = evento_data
                
                # Extrair atribuições
                atribuicoes = self._extract_atribuicoes_from_evento(record, categoria)
                for atribuicao in atribuicoes:
                    atribuicao_id = self._generate_atribuicao_id(atribuicao)
                    processed_data['atribuicoes'][atribuicao_id] = atribuicao
                
            except Exception as e:
                error_msg = f"Erro ao processar registro de agenda: {str(e)}"
                logger.error(error_msg)
                self.processing_stats['errors'].append(error_msg)
    
    def _process_disponibilidade_tab(self, tab_name: str, tab_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        """
        Processa aba de disponibilidade
        
        Args:
            tab_name: Nome da aba
            tab_data: Dados da aba
            processed_data: Dados processados (modificado in-place)
        """
        # Processar diferentes tipos de abas de disponibilidade
        if 'eventos' in tab_name.lower():
            self._process_eventos_disponibilidade_tab(tab_name, tab_data, processed_data)
        elif 'bloqueios' in tab_name.lower():
            self._process_bloqueios_tab(tab_name, tab_data, processed_data)
        elif 'configurações' in tab_name.lower():
            self._process_configuracoes_tab(tab_name, tab_data, processed_data)
    
    def _extract_pessoa_data(self, record: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Extrai dados de uma pessoa do registro
        
        Args:
            record: Registro da planilha
            
        Returns:
            Dados da pessoa ou None se inválido
        """
        try:
            # Mapear campos
            nome_completo = record.get('nome_completo') or record.get('nome') or ''
            cpf = record.get('cpf', '')
            email = record.get('email', '')
            telefone = record.get('telefone', '')
            cargo = record.get('cargo', '')
            gerencia = record.get('gerência') or record.get('gerencia', '')
            
            # Validar dados obrigatórios
            if not nome_completo:
                return None
            
            # Limpar e normalizar dados
            nome_completo = self._clean_name(nome_completo)
            cpf = self._clean_cpf(cpf)
            email = self._clean_email(email)
            telefone = self._clean_phone(telefone)
            
            # Determinar papel baseado no cargo
            papel = self._determine_papel(cargo, gerencia)
            
            # Determinar setor baseado na gerência
            setor = self._determine_setor(gerencia)
            
            return {
                'nome_completo': nome_completo,
                'primeiro_nome': self._extract_first_name(nome_completo),
                'sobrenome': self._extract_last_name(nome_completo),
                'cpf': cpf,
                'email': email,
                'telefone': telefone,
                'cargo': cargo,
                'papel': papel,
                'setor': setor,
                'gerencia': gerencia,
                'ativo': True
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da pessoa: {str(e)}")
            return None
    
    def _extract_evento_data(self, record: Dict[str, str], categoria: str) -> Optional[Dict[str, Any]]:
        """
        Extrai dados de um evento do registro
        
        Args:
            record: Registro da planilha
            categoria: Categoria do projeto
            
        Returns:
            Dados do evento ou None se inválido
        """
        try:
            # Mapear campos
            municipio = record.get('município') or record.get('municipio', '')
            projeto = record.get('projeto', '')
            tipo = record.get('tipo', '')
            data = record.get('data', '')
            hora_inicio = record.get('hora_início') or record.get('hora inicio', '')
            hora_fim = record.get('hora_fim') or record.get('hora fim', '')
            coordenador = record.get('coordenador', '')
            
            # Validar dados obrigatórios
            if not municipio or not projeto:
                return None
            
            return {
                'municipio': municipio,
                'projeto': projeto,
                'categoria': categoria,
                'tipo': tipo,
                'data': data,
                'hora_inicio': hora_inicio,
                'hora_fim': hora_fim,
                'coordenador': coordenador,
                'formadores': self._extract_formadores_from_record(record)
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do evento: {str(e)}")
            return None
    
    def _extract_atribuicoes_from_evento(self, record: Dict[str, str], categoria: str) -> List[Dict[str, Any]]:
        """
        Extrai atribuições de um evento
        
        Args:
            record: Registro da planilha
            categoria: Categoria do projeto
            
        Returns:
            Lista de atribuições
        """
        atribuicoes = []
        
        try:
            municipio = record.get('município') or record.get('municipio', '')
            projeto = record.get('projeto', '')
            coordenador = record.get('coordenador', '')
            
            # Atribuição do coordenador
            if coordenador:
                atribuicoes.append({
                    'pessoa_nome': coordenador,
                    'projeto': projeto,
                    'categoria': categoria,
                    'municipio': municipio,
                    'papel': 'coordenador'
                })
            
            # Atribuições dos formadores
            formadores = self._extract_formadores_from_record(record)
            for formador in formadores:
                if formador:
                    atribuicoes.append({
                        'pessoa_nome': formador,
                        'projeto': projeto,
                        'categoria': categoria,
                        'municipio': municipio,
                        'papel': 'formador'
                    })
            
        except Exception as e:
            logger.error(f"Erro ao extrair atribuições: {str(e)}")
        
        return atribuicoes
    
    def _extract_formadores_from_record(self, record: Dict[str, str]) -> List[str]:
        """
        Extrai formadores de um registro
        
        Args:
            record: Registro da planilha
            
        Returns:
            Lista de formadores
        """
        formadores = []
        
        # Buscar campos de formadores
        for key, value in record.items():
            if 'formador' in key.lower() and value:
                formadores.append(value.strip())
        
        return [f for f in formadores if f]
    
    def _identify_project_category(self, tab_name: str) -> str:
        """
        Identifica categoria do projeto baseado no nome da aba
        
        Args:
            tab_name: Nome da aba
            
        Returns:
            Categoria do projeto
        """
        tab_lower = tab_name.lower()
        
        if 'super' in tab_lower:
            return 'superintendencia'
        elif 'acerta' in tab_lower:
            return 'acerta'
        elif 'brincando' in tab_lower:
            return 'brincando'
        elif 'vidas' in tab_lower:
            return 'vidas'
        else:
            return 'projetos_especificos'
    
    def _determine_papel(self, cargo: str, gerencia: str) -> str:
        """
        Determina papel da pessoa baseado no cargo e gerência
        
        Args:
            cargo: Cargo da pessoa
            gerencia: Gerência da pessoa
            
        Returns:
            Papel da pessoa
        """
        cargo_lower = cargo.lower()
        gerencia_lower = gerencia.lower()
        
        if 'coordenador' in cargo_lower:
            return 'coordenador'
        elif 'formador' in cargo_lower:
            return 'formador'
        elif 'gerente' in cargo_lower:
            return 'gerente'
        elif 'superintendência' in gerencia_lower or 'superintendencia' in gerencia_lower:
            return 'superintendencia'
        elif 'controle' in gerencia_lower:
            return 'controle'
        elif 'dat' in gerencia_lower:
            return 'dat'
        else:
            return 'formador'  # Default
    
    def _determine_setor(self, gerencia: str) -> str:
        """
        Determina setor baseado na gerência
        
        Args:
            gerencia: Gerência da pessoa
            
        Returns:
            Setor da pessoa
        """
        gerencia_lower = gerencia.lower()
        
        if 'superintendência' in gerencia_lower or 'superintendencia' in gerencia_lower:
            return 'superintendencia'
        elif 'acerta' in gerencia_lower:
            return 'acerta'
        elif 'brincando' in gerencia_lower:
            return 'brincando'
        elif 'vidas' in gerencia_lower:
            return 'vidas'
        elif 'controle' in gerencia_lower:
            return 'controle'
        elif 'dat' in gerencia_lower:
            return 'dat'
        else:
            return 'superintendencia'  # Default
    
    def _clean_name(self, name: str) -> str:
        """
        Limpa e normaliza nome
        
        Args:
            name: Nome original
            
        Returns:
            Nome limpo
        """
        if not name:
            return ""
        
        # Remover espaços extras e normalizar
        cleaned = re.sub(r'\s+', ' ', name.strip())
        
        # Capitalizar palavras
        words = cleaned.split()
        capitalized_words = [word.capitalize() for word in words]
        
        return ' '.join(capitalized_words)
    
    def _clean_cpf(self, cpf: str) -> str:
        """
        Limpa e normaliza CPF
        
        Args:
            cpf: CPF original
            
        Returns:
            CPF limpo
        """
        if not cpf:
            return ""
        
        # Remover caracteres não numéricos
        cleaned = re.sub(r'\D', '', cpf)
        
        # Verificar se tem 11 dígitos
        if len(cleaned) == 11:
            return cleaned
        
        return ""
    
    def _clean_email(self, email: str) -> str:
        """
        Limpa e normaliza email
        
        Args:
            email: Email original
            
        Returns:
            Email limpo
        """
        if not email:
            return ""
        
        # Remover espaços e converter para minúsculas
        cleaned = email.strip().lower()
        
        # Validar formato básico
        if '@' in cleaned and '.' in cleaned:
            return cleaned
        
        return ""
    
    def _clean_phone(self, phone: str) -> str:
        """
        Limpa e normaliza telefone
        
        Args:
            phone: Telefone original
            
        Returns:
            Telefone limpo
        """
        if not phone:
            return ""
        
        # Remover caracteres não numéricos exceto +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        return cleaned
    
    def _extract_first_name(self, full_name: str) -> str:
        """
        Extrai primeiro nome
        
        Args:
            full_name: Nome completo
            
        Returns:
            Primeiro nome
        """
        if not full_name:
            return ""
        
        words = full_name.split()
        return words[0] if words else ""
    
    def _extract_last_name(self, full_name: str) -> str:
        """
        Extrai sobrenome
        
        Args:
            full_name: Nome completo
            
        Returns:
            Sobrenome
        """
        if not full_name:
            return ""
        
        words = full_name.split()
        return ' '.join(words[1:]) if len(words) > 1 else ""
    
    def _generate_pessoa_id(self, pessoa_data: Dict[str, Any]) -> str:
        """
        Gera ID único para pessoa
        
        Args:
            pessoa_data: Dados da pessoa
            
        Returns:
            ID único
        """
        # Usar CPF se disponível, senão usar nome
        if pessoa_data.get('cpf'):
            return f"pessoa_{pessoa_data['cpf']}"
        else:
            nome_hash = hashlib.md5(pessoa_data['nome_completo'].encode()).hexdigest()[:8]
            return f"pessoa_{nome_hash}"
    
    def _generate_evento_id(self, evento_data: Dict[str, Any]) -> str:
        """
        Gera ID único para evento
        
        Args:
            evento_data: Dados do evento
            
        Returns:
            ID único
        """
        # Usar combinação de dados para gerar ID único
        key_data = f"{evento_data.get('municipio', '')}_{evento_data.get('projeto', '')}_{evento_data.get('data', '')}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"evento_{key_hash}"
    
    def _generate_atribuicao_id(self, atribuicao_data: Dict[str, Any]) -> str:
        """
        Gera ID único para atribuição
        
        Args:
            atribuicao_data: Dados da atribuição
            
        Returns:
            ID único
        """
        # Usar combinação de dados para gerar ID único
        key_data = f"{atribuicao_data.get('pessoa_nome', '')}_{atribuicao_data.get('projeto', '')}_{atribuicao_data.get('papel', '')}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"atribuicao_{key_hash}"
    
    def _merge_pessoa_data(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mescla dados de pessoa existentes com novos dados
        
        Args:
            existing_data: Dados existentes
            new_data: Novos dados
            
        Returns:
            Dados mesclados
        """
        merged = existing_data.copy()
        
        # Mesclar campos, priorizando dados não vazios
        for key, value in new_data.items():
            if value and (not merged.get(key) or merged[key] == ""):
                merged[key] = value
        
        return merged
    
    def _post_process_data(self, processed_data: Dict[str, Any]) -> None:
        """
        Pós-processamento dos dados
        
        Args:
            processed_data: Dados processados (modificado in-place)
        """
        try:
            # Estatísticas finais
            processed_data['metadata']['statistics'] = {
                'total_pessoas': len(processed_data['pessoas']),
                'total_projetos': len(processed_data['projetos']),
                'total_municipios': len(processed_data['municipios']),
                'total_atribuicoes': len(processed_data['atribuicoes']),
                'total_eventos': len(processed_data['eventos']),
                'total_solicitacoes': len(processed_data['solicitacoes'])
            }
            
            # Identificar projetos únicos
            projetos_unicos = set()
            for evento in processed_data['eventos'].values():
                if evento.get('projeto'):
                    projetos_unicos.add(evento['projeto'])
            
            processed_data['projetos'] = {
                f"projeto_{i}": {
                    'nome': projeto,
                    'categoria': self._identify_project_category(projeto)
                }
                for i, projeto in enumerate(projetos_unicos, 1)
            }
            
            # Identificar municípios únicos
            municipios_unicos = set()
            for evento in processed_data['eventos'].values():
                if evento.get('municipio'):
                    municipios_unicos.add(evento['municipio'])
            
            processed_data['municipios'] = {
                f"municipio_{i}": {
                    'nome': municipio
                }
                for i, municipio in enumerate(municipios_unicos, 1)
            }
            
            logger.info("✅ Pós-processamento concluído")
            
        except Exception as e:
            error_msg = f"Erro no pós-processamento: {str(e)}"
            logger.error(error_msg)
            self.processing_stats['errors'].append(error_msg)
    
    def save_processed_data(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Salva dados processados em arquivo
        
        Args:
            data: Dados processados
            output_path: Caminho do arquivo de saída
            
        Returns:
            True se salvo com sucesso, False caso contrário
        """
        try:
            # Adicionar estatísticas de processamento
            data['processing_stats'] = self.processing_stats
            data['processing_stats']['end_time'] = datetime.now(timezone.utc)
            data['processing_stats']['duration_seconds'] = (
                data['processing_stats']['end_time'] - 
                data['processing_stats']['start_time']
            ).total_seconds()
            
            # Salvar arquivo
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"✅ Dados processados salvos em: {output_path}")
            logger.info(f"📊 Estatísticas: {self.processing_stats['files_processed']} arquivos, "
                       f"{self.processing_stats['records_processed']} registros")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar dados processados: {str(e)}")
            return False
    
    def get_processing_report(self) -> str:
        """
        Gera relatório do processamento
        
        Returns:
            Relatório em formato texto
        """
        stats = self.processing_stats
        
        report = f"""
🧠 RELATÓRIO DE PROCESSAMENTO NEURAL - SISTEMA APRENDER
{'='*60}

📊 ESTATÍSTICAS GERAIS:
• Arquivos processados: {stats['files_processed']}
• Registros processados: {stats['records_processed']}
• Erros encontrados: {len(stats['errors'])}
• Avisos gerados: {len(stats['warnings'])}

⏱️ TEMPO DE EXECUÇÃO:
• Início: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}
• Duração: {stats.get('duration_seconds', 0):.2f} segundos

"""
        
        if stats['errors']:
            report += "❌ ERROS ENCONTRADOS:\n"
            for i, error in enumerate(stats['errors'], 1):
                report += f"{i}. {error}\n"
            report += "\n"
        
        if stats['warnings']:
            report += "⚠️ AVISOS:\n"
            for i, warning in enumerate(stats['warnings'], 1):
                report += f"{i}. {warning}\n"
            report += "\n"
        
        if not stats['errors'] and not stats['warnings']:
            report += "✅ Processamento concluído sem erros ou avisos!\n"
        
        return report

def main():
    """
    Função principal do processador neural
    """
    try:
        # Encontrar arquivo de dados mais recente
        data_files = list(Path('.').glob('mapeamento_completo_google_sheets_*.json'))
        if not data_files:
            logger.error("❌ Nenhum arquivo de dados encontrado")
            sys.exit(1)
        
        # Usar o arquivo mais recente
        latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"📁 Usando arquivo de dados: {latest_file}")
        
        # Inicializar processador
        processor = NeuralDataProcessor()
        
        # Executar processamento
        logger.info("🚀 Iniciando processamento neural de dados")
        processed_data = processor.process_google_sheets_data(str(latest_file))
        
        # Salvar dados processados
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"neural_processed_data_{timestamp}.json"
        
        if processor.save_processed_data(processed_data, output_file):
            logger.info("✅ Processamento concluído com sucesso!")
            
            # Exibir relatório
            print(processor.get_processing_report())
        else:
            logger.error("❌ Falha ao salvar dados processados")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Erro crítico no processamento: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
