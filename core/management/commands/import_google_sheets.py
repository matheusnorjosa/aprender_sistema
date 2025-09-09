"""
Comando para importação automática de Google Sheets
==================================================

Comando Django para importar dados diretamente do Google Sheets
usando o serviço gspread integrado.

Autor: Claude Code  
Data: Janeiro 2025
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model

from core.models import (
    Formador, Municipio, Projeto, TipoEvento, 
    LogAuditoria, Setor
)
from core.services.google_sheets_service import google_sheets_service

User = get_user_model()


class Command(BaseCommand):
    help = "Importa dados diretamente do Google Sheets"

    def add_arguments(self, parser):
        parser.add_argument(
            '--spreadsheet-key',
            type=str,
            required=True,
            help='ID da planilha Google (extraído da URL)'
        )
        
        parser.add_argument(
            '--worksheet-name',
            type=str,
            help='Nome da aba específica (opcional)'
        )
        
        parser.add_argument(
            '--data-type',
            type=str,
            choices=['formadores', 'municipios', 'projetos', 'tipos_evento', 'all'],
            default='all',
            help='Tipo de dados para importar'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Execução de teste sem salvar no banco'
        )
        
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpar dados existentes antes da importação'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            default='system',
            help='Username para auditoria'
        )

    def handle(self, *args, **options):
        spreadsheet_key = options['spreadsheet_key']
        worksheet_name = options.get('worksheet_name')
        data_type = options['data_type']
        dry_run = options['dry_run']
        clear = options['clear']
        username = options['user']

        # Usuário para auditoria
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
            self.stdout.write(
                self.style.WARNING(f'Usuário "{username}" não encontrado')
            )

        self.stdout.write("=== IMPORTACAO GOOGLE SHEETS ===")
        self.stdout.write(f"Planilha: {spreadsheet_key}")
        self.stdout.write(f"Aba: {worksheet_name or 'Primeira aba'}")
        self.stdout.write(f"Tipo: {data_type}")
        self.stdout.write(f'Modo: {"DRY-RUN" if dry_run else "EXECUCAO REAL"}')

        try:
            # Obter informações da planilha
            spreadsheet_info = google_sheets_service.get_spreadsheet_info(
                spreadsheet_key
            )
            
            self.stdout.write(
                f"Planilha encontrada: {spreadsheet_info['title']}"
            )
            
            # Determinar worksheets para processar
            worksheets_to_process = []
            
            if worksheet_name:
                # Aba específica
                worksheets_to_process = [(worksheet_name, data_type)]
            else:
                # Auto-detectar baseado em nomes das abas
                for ws in spreadsheet_info['worksheets']:
                    ws_name = ws['title'].lower()
                    
                    if 'formador' in ws_name:
                        worksheets_to_process.append((ws['title'], 'formadores'))
                    elif 'municipio' in ws_name or 'cidade' in ws_name:
                        worksheets_to_process.append((ws['title'], 'municipios'))
                    elif 'projeto' in ws_name:
                        worksheets_to_process.append((ws['title'], 'projetos'))
                    elif 'tipo' in ws_name and 'evento' in ws_name:
                        worksheets_to_process.append((ws['title'], 'tipos_evento'))
                    elif data_type == 'all':
                        # Se não conseguir detectar, usar o tipo especificado
                        worksheets_to_process.append((ws['title'], data_type))

            if not worksheets_to_process:
                raise CommandError("Nenhuma aba encontrada para processar")

            # Processar cada worksheet
            total_results = {
                'total': 0,
                'criados': 0,
                'atualizados': 0,
                'erros': 0
            }

            for ws_name, ws_type in worksheets_to_process:
                self.stdout.write(f"\n--- Processando: {ws_name} ({ws_type}) ---")
                
                # Obter dados da aba
                data = google_sheets_service.get_worksheet_data(
                    spreadsheet_key, ws_name
                )
                
                if not data:
                    self.stdout.write("Nenhum dado encontrado nesta aba")
                    continue
                
                # Processar baseado no tipo
                if ws_type == 'formadores':
                    result = self.process_formadores(data, dry_run, clear, user)
                elif ws_type == 'municipios':
                    result = self.process_municipios(data, dry_run, clear, user)
                elif ws_type == 'projetos':
                    result = self.process_projetos(data, dry_run, clear, user)
                elif ws_type == 'tipos_evento':
                    result = self.process_tipos_evento(data, dry_run, clear, user)
                else:
                    self.stdout.write(f"Tipo {ws_type} não implementado")
                    continue
                
                # Somar resultados
                for key in total_results:
                    total_results[key] += result.get(key, 0)
                
                self.display_result(result)

            # Resultado final
            self.stdout.write("\n=== RESULTADO TOTAL ===")
            self.display_result(total_results)
            
            # Log de auditoria
            if not dry_run and user:
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="IMPORT_GOOGLE_SHEETS",
                    detalhes=f"Importação Google Sheets - {spreadsheet_info['title']} - "
                            f"Criados: {total_results['criados']} - "
                            f"Erros: {total_results['erros']}"
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante importação: {e}"))
            raise CommandError(f"Falha na importação: {e}")

    def process_formadores(self, data, dry_run, clear, user):
        """Processa dados de formadores"""
        result = {'total': len(data), 'criados': 0, 'atualizados': 0, 'erros': 0}
        
        if clear and not dry_run:
            count = Formador.objects.count()
            Formador.objects.all().delete()
            self.stdout.write(f"Removidos {count} formadores existentes")
        
        for row in data:
            try:
                nome = row.get('nome', '').strip()
                email = row.get('email', '').strip()
                area_atuacao = row.get('area_atuacao', '').strip()
                
                if not nome:
                    result['erros'] += 1
                    continue
                
                if not dry_run:
                    # Criar ou buscar usuário
                    user_obj, created = User.objects.get_or_create(
                        email=email,
                        defaults={'username': email, 'first_name': nome}
                    )
                    
                    # Criar ou atualizar formador
                    formador, created = Formador.objects.get_or_create(
                        usuario=user_obj,
                        defaults={'ativo': True}
                    )
                    
                    if created:
                        result['criados'] += 1
                        self.stdout.write(f"  [+] Formador: {nome}")
                    else:
                        result['atualizados'] += 1
                        self.stdout.write(f"  [~] Atualizado: {nome}")
                else:
                    result['criados'] += 1
                    self.stdout.write(f"  [+] [DRY] Formador: {nome}")
                    
            except Exception as e:
                result['erros'] += 1
                self.stdout.write(self.style.ERROR(f"  [X] Erro: {e}"))
        
        return result

    def process_municipios(self, data, dry_run, clear, user):
        """Processa dados de municípios"""
        result = {'total': len(data), 'criados': 0, 'atualizados': 0, 'erros': 0}
        
        if clear and not dry_run:
            count = Municipio.objects.count()
            Municipio.objects.all().delete()
            self.stdout.write(f"Removidos {count} municípios existentes")
        
        for row in data:
            try:
                nome = row.get('nome', '').strip()
                uf = row.get('uf', '').strip()[:2].upper()
                ativo = str(row.get('ativo', 'True')).lower() in ['true', '1', 'sim', 'ativo']
                
                if not nome:
                    result['erros'] += 1
                    continue
                
                if not dry_run:
                    municipio, created = Municipio.objects.get_or_create(
                        nome=nome,
                        uf=uf,
                        defaults={'ativo': ativo}
                    )
                    
                    if created:
                        result['criados'] += 1
                        self.stdout.write(f"  [+] Município: {nome} ({uf})")
                    else:
                        if municipio.ativo != ativo:
                            municipio.ativo = ativo
                            municipio.save()
                            result['atualizados'] += 1
                            self.stdout.write(f"  [~] Atualizado: {nome} ({uf})")
                        else:
                            self.stdout.write(f"  [=] Já existe: {nome} ({uf})")
                else:
                    result['criados'] += 1
                    self.stdout.write(f"  [+] [DRY] Município: {nome} ({uf})")
                    
            except Exception as e:
                result['erros'] += 1
                self.stdout.write(self.style.ERROR(f"  [X] Erro: {e}"))
        
        return result

    def process_projetos(self, data, dry_run, clear, user):
        """Processa dados de projetos"""
        result = {'total': len(data), 'criados': 0, 'atualizados': 0, 'erros': 0}
        
        if clear and not dry_run:
            count = Projeto.objects.count()
            Projeto.objects.all().delete()
            self.stdout.write(f"Removidos {count} projetos existentes")
        
        for row in data:
            try:
                nome = row.get('nome', '').strip()
                descricao = row.get('descricao', '').strip()
                ativo = str(row.get('ativo', 'True')).lower() in ['true', '1', 'sim', 'ativo']
                
                if not nome:
                    result['erros'] += 1
                    continue
                
                if not dry_run:
                    projeto, created = Projeto.objects.get_or_create(
                        nome=nome,
                        defaults={'descricao': descricao, 'ativo': ativo}
                    )
                    
                    if created:
                        result['criados'] += 1
                        self.stdout.write(f"  [+] Projeto: {nome}")
                    else:
                        updated = False
                        if projeto.descricao != descricao:
                            projeto.descricao = descricao
                            updated = True
                        if projeto.ativo != ativo:
                            projeto.ativo = ativo
                            updated = True
                        
                        if updated:
                            projeto.save()
                            result['atualizados'] += 1
                            self.stdout.write(f"  [~] Atualizado: {nome}")
                        else:
                            self.stdout.write(f"  [=] Já existe: {nome}")
                else:
                    result['criados'] += 1
                    self.stdout.write(f"  [+] [DRY] Projeto: {nome}")
                    
            except Exception as e:
                result['erros'] += 1
                self.stdout.write(self.style.ERROR(f"  [X] Erro: {e}"))
        
        return result

    def process_tipos_evento(self, data, dry_run, clear, user):
        """Processa dados de tipos de evento"""
        result = {'total': len(data), 'criados': 0, 'atualizados': 0, 'erros': 0}
        
        if clear and not dry_run:
            count = TipoEvento.objects.count()
            TipoEvento.objects.all().delete()
            self.stdout.write(f"Removidos {count} tipos de evento existentes")
        
        for row in data:
            try:
                nome = row.get('nome', '').strip()
                online = str(row.get('online', 'False')).lower() in ['true', '1', 'sim', 'online']
                duracao_padrao = row.get('duracao_padrao', 2)
                
                if not nome:
                    result['erros'] += 1
                    continue
                
                try:
                    duracao_padrao = int(duracao_padrao)
                except (ValueError, TypeError):
                    duracao_padrao = 2
                
                if not dry_run:
                    tipo_evento, created = TipoEvento.objects.get_or_create(
                        nome=nome,
                        defaults={
                            'online': online,
                            'duracao_padrao': duracao_padrao
                        }
                    )
                    
                    if created:
                        result['criados'] += 1
                        self.stdout.write(f"  [+] Tipo Evento: {nome}")
                    else:
                        updated = False
                        if tipo_evento.online != online:
                            tipo_evento.online = online
                            updated = True
                        if tipo_evento.duracao_padrao != duracao_padrao:
                            tipo_evento.duracao_padrao = duracao_padrao
                            updated = True
                        
                        if updated:
                            tipo_evento.save()
                            result['atualizados'] += 1
                            self.stdout.write(f"  [~] Atualizado: {nome}")
                        else:
                            self.stdout.write(f"  [=] Já existe: {nome}")
                else:
                    result['criados'] += 1
                    self.stdout.write(f"  [+] [DRY] Tipo Evento: {nome}")
                    
            except Exception as e:
                result['erros'] += 1
                self.stdout.write(self.style.ERROR(f"  [X] Erro: {e}"))
        
        return result

    def display_result(self, result):
        """Exibe resultado da importação"""
        self.stdout.write(f'Total: {result["total"]}')
        self.stdout.write(self.style.SUCCESS(f'Criados: {result["criados"]}'))
        self.stdout.write(f'Atualizados: {result["atualizados"]}')
        
        if result["erros"] > 0:
            self.stdout.write(self.style.ERROR(f'Erros: {result["erros"]}'))
        
        sucesso = result["criados"] + result["atualizados"]
        if sucesso > 0 and result["erros"] == 0:
            self.stdout.write(self.style.SUCCESS("✅ Importação bem-sucedida!"))
        elif sucesso > 0:
            self.stdout.write(self.style.WARNING("⚠️ Importação com alguns erros"))
        else:
            self.stdout.write(self.style.ERROR("❌ Nenhum registro importado"))