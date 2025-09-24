#!/usr/bin/env python3
"""
🧠 IMPORTADOR NEURAL ROBUSTO PARA POSTGRESQL - SISTEMA APRENDER
==============================================================

Importa dados processados pelo sistema neural para o banco PostgreSQL
seguindo as melhores práticas de banco de dados.

Author: Claude Code
Date: Setembro 2025
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
import django
django.setup()

from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from core.models import (
    Usuario, Setor, Municipio, Projeto, TipoEvento,
    Solicitacao, Aprovacao, DisponibilidadeFormadores
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

User = get_user_model()


class NeuralPostgreSQLImporter:
    """
    Importador neural robusto para PostgreSQL
    """
    
    def __init__(self, data_file: str = None):
        self.data_file = data_file or self._find_latest_processed_file()
        self.import_stats = {
            'start_time': datetime.now(),
            'pessoas_created': 0,
            'pessoas_updated': 0,
            'setores_created': 0,
            'errors': [],
            'warnings': []
        }
        
    def _find_latest_processed_file(self) -> str:
        """Encontra o arquivo de dados processados mais recente"""
        import glob
        files = glob.glob('neural_robust_processed_*.json')
        if not files:
            raise FileNotFoundError("Nenhum arquivo de dados processados encontrado")
        
        latest_file = max(files, key=lambda f: os.path.getmtime(f))
        return latest_file
    
    def import_data(self) -> Dict[str, Any]:
        """Importa todos os dados processados"""
        logger.info(f"🔄 Importando dados do arquivo: {self.data_file}")
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Importar dados em ordem de dependência
            self._import_setores(data)
            self._import_pessoas(data)
            self._import_projetos(data)
            self._import_municipios(data)
            self._import_tipos_evento(data)
            
            # Calcular estatísticas finais
            self._calculate_final_stats()
            
            # Relatório final
            self._print_import_report()
            
            return self.import_stats
            
        except Exception as e:
            logger.error(f"❌ Erro na importação: {str(e)}")
            raise
    
    def _import_setores(self, data: Dict[str, Any]):
        """Importa setores/gerências"""
        logger.info("🏢 Importando setores...")
        
        setores_unicos = set()
        
        # Coletar setores únicos das pessoas
        for pessoa_data in data.get('pessoas', {}).values():
            gerencia = pessoa_data.get('gerencia', '').strip()
            if gerencia:
                setores_unicos.add(gerencia)
        
        # Criar setores
        for setor_nome in setores_unicos:
            try:
                with transaction.atomic():
                    setor, created = Setor.objects.get_or_create(
                        nome=setor_nome,
                        defaults={
                            'sigla': setor_nome[:10].upper(),
                            'ativo': True,
                            'vinculado_superintendencia': 'superintendência' in setor_nome.lower()
                        }
                    )
                    
                    if created:
                        self.import_stats['setores_created'] += 1
                        logger.info(f"  ✅ Setor criado: {setor_nome}")
                    else:
                        logger.info(f"  ℹ️ Setor já existe: {setor_nome}")
                        
            except Exception as e:
                error_msg = f"Erro ao criar setor {setor_nome}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                self.import_stats['errors'].append(error_msg)
    
    def _import_pessoas(self, data: Dict[str, Any]):
        """Importa pessoas/usuários"""
        logger.info("👥 Importando pessoas...")
        
        for pessoa_id, pessoa_data in data.get('pessoas', {}).items():
            try:
                with transaction.atomic():
                    # Buscar setor
                    setor = None
                    if pessoa_data.get('gerencia'):
                        try:
                            setor = Setor.objects.get(nome=pessoa_data['gerencia'])
                        except Setor.DoesNotExist:
                            logger.warning(f"  ⚠️ Setor não encontrado: {pessoa_data['gerencia']}")
                    
                    # Criar ou atualizar usuário
                    cpf = pessoa_data.get('cpf')
                    if cpf:
                        try:
                            usuario = Usuario.objects.get(cpf=cpf)
                            # Atualizar usuário existente
                            usuario.username = cpf or pessoa_data.get('email', '')
                            usuario.first_name = self._extract_first_name(pessoa_data['nome_completo'])
                            usuario.last_name = self._extract_last_name(pessoa_data['nome_completo'])
                            usuario.email = pessoa_data.get('email', '')
                            usuario.setor = setor
                            usuario.is_active = pessoa_data.get('status') == 'ativo'
                            usuario.save()
                            created = False
                        except Usuario.DoesNotExist:
                            # Criar novo usuário
                            usuario = Usuario.objects.create(
                                username=cpf or pessoa_data.get('email', ''),
                                first_name=self._extract_first_name(pessoa_data['nome_completo']),
                                last_name=self._extract_last_name(pessoa_data['nome_completo']),
                                email=pessoa_data.get('email', ''),
                                cpf=cpf,
                                setor=setor,
                                is_active=pessoa_data.get('status') == 'ativo',
                                is_staff=False,
                                is_superuser=False,
                            )
                            created = True
                    else:
                        # Se não tem CPF, usar email como username
                        email = pessoa_data.get('email', '')
                        if email:
                            try:
                                usuario = Usuario.objects.get(email=email)
                                # Atualizar usuário existente
                                usuario.first_name = self._extract_first_name(pessoa_data['nome_completo'])
                                usuario.last_name = self._extract_last_name(pessoa_data['nome_completo'])
                                usuario.setor = setor
                                usuario.is_active = pessoa_data.get('status') == 'ativo'
                                usuario.save()
                                created = False
                            except Usuario.DoesNotExist:
                                # Criar novo usuário
                                usuario = Usuario.objects.create(
                                    username=email,
                                    first_name=self._extract_first_name(pessoa_data['nome_completo']),
                                    last_name=self._extract_last_name(pessoa_data['nome_completo']),
                                    email=email,
                                    setor=setor,
                                    is_active=pessoa_data.get('status') == 'ativo',
                                    is_staff=False,
                                    is_superuser=False,
                                )
                                created = True
                        else:
                            logger.warning(f"  ⚠️ Pessoa sem CPF nem email: {pessoa_data['nome_completo']}")
                            continue
                    
                    if created:
                        self.import_stats['pessoas_created'] += 1
                        logger.info(f"  ✅ Pessoa criada: {pessoa_data['nome_completo']}")
                    else:
                        self.import_stats['pessoas_updated'] += 1
                        logger.info(f"  🔄 Pessoa atualizada: {pessoa_data['nome_completo']}")
                        
            except IntegrityError as e:
                error_msg = f"Erro de integridade ao importar pessoa {pessoa_data.get('nome_completo')}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                self.import_stats['errors'].append(error_msg)
            except Exception as e:
                error_msg = f"Erro inesperado ao importar pessoa {pessoa_data.get('nome_completo')}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                self.import_stats['errors'].append(error_msg)
    
    def _import_projetos(self, data: Dict[str, Any]):
        """Importa projetos"""
        logger.info("📋 Importando projetos...")
        
        # Projetos padrão baseados nas gerências
        projetos_padrao = [
            {'nome': 'ACerta', 'descricao': 'Projeto ACerta'},
            {'nome': 'Brincando', 'descricao': 'Projeto Brincando'},
            {'nome': 'Vidas', 'descricao': 'Projeto Vidas'},
            {'nome': 'Superintendência', 'descricao': 'Projeto Superintendência'},
            {'nome': 'Outros', 'descricao': 'Outros projetos'},
        ]
        
        for projeto_data in projetos_padrao:
            try:
                with transaction.atomic():
                    projeto, created = Projeto.objects.get_or_create(
                        nome=projeto_data['nome'],
                        defaults={
                            'descricao': projeto_data['descricao'],
                            'ativo': True
                        }
                    )
                    
                    if created:
                        logger.info(f"  ✅ Projeto criado: {projeto_data['nome']}")
                    else:
                        logger.info(f"  ℹ️ Projeto já existe: {projeto_data['nome']}")
                        
            except Exception as e:
                error_msg = f"Erro ao criar projeto {projeto_data['nome']}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                self.import_stats['errors'].append(error_msg)
    
    def _import_municipios(self, data: Dict[str, Any]):
        """Importa municípios"""
        logger.info("🏘️ Importando municípios...")
        
        # Municípios padrão do Ceará
        municipios_padrao = [
            {'nome': 'Fortaleza', 'uf': 'CE', 'codigo_ibge': '2304400'},
            {'nome': 'Caucaia', 'uf': 'CE', 'codigo_ibge': '2303709'},
            {'nome': 'Maracanaú', 'uf': 'CE', 'codigo_ibge': '2307700'},
            {'nome': 'Sobral', 'uf': 'CE', 'codigo_ibge': '2312908'},
            {'nome': 'Juazeiro do Norte', 'uf': 'CE', 'codigo_ibge': '2307650'},
        ]
        
        for municipio_data in municipios_padrao:
            try:
                with transaction.atomic():
                    municipio, created = Municipio.objects.get_or_create(
                        nome=municipio_data['nome'],
                        defaults={
                            'uf': municipio_data['uf'],
                            'ativo': True
                        }
                    )
                    
                    if created:
                        logger.info(f"  ✅ Município criado: {municipio_data['nome']}")
                    else:
                        logger.info(f"  ℹ️ Município já existe: {municipio_data['nome']}")
                        
            except Exception as e:
                error_msg = f"Erro ao criar município {municipio_data['nome']}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                self.import_stats['errors'].append(error_msg)
    
    def _import_tipos_evento(self, data: Dict[str, Any]):
        """Importa tipos de evento"""
        logger.info("📅 Importando tipos de evento...")
        
        # Tipos de evento padrão
        tipos_evento_padrao = [
            {'nome': 'Formação Presencial', 'descricao': 'Formação presencial'},
            {'nome': 'Formação Online', 'descricao': 'Formação online'},
            {'nome': 'Reunião', 'descricao': 'Reunião de equipe'},
            {'nome': 'Capacitação', 'descricao': 'Capacitação técnica'},
            {'nome': 'Workshop', 'descricao': 'Workshop'},
        ]
        
        for tipo_data in tipos_evento_padrao:
            try:
                with transaction.atomic():
                    tipo_evento, created = TipoEvento.objects.get_or_create(
                        nome=tipo_data['nome'],
                        defaults={
                            'online': 'online' in tipo_data['nome'].lower(),
                            'ativo': True
                        }
                    )
                    
                    if created:
                        logger.info(f"  ✅ Tipo de evento criado: {tipo_data['nome']}")
                    else:
                        logger.info(f"  ℹ️ Tipo de evento já existe: {tipo_data['nome']}")
                        
            except Exception as e:
                error_msg = f"Erro ao criar tipo de evento {tipo_data['nome']}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                self.import_stats['errors'].append(error_msg)
    
    def _extract_first_name(self, full_name: str) -> str:
        """Extrai primeiro nome"""
        if not full_name:
            return ''
        return full_name.split()[0] if full_name.split() else ''
    
    def _extract_last_name(self, full_name: str) -> str:
        """Extrai sobrenome"""
        if not full_name:
            return ''
        parts = full_name.split()
        return ' '.join(parts[1:]) if len(parts) > 1 else ''
    
    def _calculate_final_stats(self):
        """Calcula estatísticas finais"""
        end_time = datetime.now()
        duration = (end_time - self.import_stats['start_time']).total_seconds()
        self.import_stats['end_time'] = end_time
        self.import_stats['duration_seconds'] = duration
    
    def _print_import_report(self):
        """Imprime relatório de importação"""
        print("\n🧠 RELATÓRIO DE IMPORTAÇÃO NEURAL - SISTEMA APRENDER")
        print("=" * 60)
        
        print(f"\n📊 ESTATÍSTICAS DE IMPORTAÇÃO:")
        print(f"• Pessoas criadas: {self.import_stats['pessoas_created']}")
        print(f"• Pessoas atualizadas: {self.import_stats['pessoas_updated']}")
        print(f"• Setores criados: {self.import_stats['setores_created']}")
        
        print(f"\n⏱️ ESTATÍSTICAS DE TEMPO:")
        print(f"• Tempo de importação: {self.import_stats['duration_seconds']:.2f}s")
        
        if self.import_stats['errors']:
            print(f"\n❌ ERROS ENCONTRADOS:")
            for error in self.import_stats['errors']:
                print(f"  • {error}")
        
        if self.import_stats['warnings']:
            print(f"\n⚠️ AVISOS GERADOS:")
            for warning in self.import_stats['warnings']:
                print(f"  • {warning}")
        
        print(f"\n✅ Importação concluída com sucesso!")


def main():
    """Função principal"""
    try:
        importer = NeuralPostgreSQLImporter()
        result = importer.import_data()
        
        print(f"\n🎯 Importação concluída!")
        print(f"📊 Total de pessoas importadas: {result['pessoas_created'] + result['pessoas_updated']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na importação: {str(e)}")
        raise


if __name__ == "__main__":
    main()
