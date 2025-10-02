"""
Comando DEPRECATED: Importação automática de Google Sheets
=========================================================

⚠️  DEPRECATED: Este comando foi substituído pelos comandos canônicos em ingestao/
Use: python manage.py ingestao.import_usuarios --from=sheets
Use: python manage.py ingestao.import_eventos_abas --from=sheets
Use: python manage.py ingestao.import_disponibilidades_sheets --from=sheets

Autor: Claude Code  
Data: Janeiro 2025
"""

import warnings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = "⚠️  DEPRECATED: Use os comandos canônicos em ingestao/"

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-type',
            type=str,
            choices=['usuarios', 'eventos', 'disponibilidades', 'all'],
            default='all',
            help='Tipo de dados para importar (delega para comandos canônicos)'
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
            '--verbose',
            action='store_true',
            help='Mostrar informações detalhadas'
        )

    def handle(self, *args, **options):
        # Emitir warning de deprecação
        warnings.warn(
            "Deprecated: use 'python manage.py import_... (ingestao)'.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.stdout.write(
            self.style.WARNING(
                "⚠️  AVISO: Este comando está DEPRECATED!\n"
                "Use os comandos canônicos:\n"
                "  python manage.py ingestao.import_usuarios --from=sheets\n"
                "  python manage.py ingestao.import_eventos_abas --from=sheets\n"
                "  python manage.py ingestao.import_disponibilidades_sheets --from=sheets\n"
            )
        )
        
        data_type = options['data_type']
        dry_run = options['dry_run']
        clear = options['clear']
        verbose = options['verbose']
        
        # Delegar para comandos canônicos
        commands_to_run = []
        
        if data_type in ['usuarios', 'all']:
            commands_to_run.append('import_usuarios')
        
        if data_type in ['eventos', 'all']:
            commands_to_run.append('import_eventos_abas')
        
        if data_type in ['disponibilidades', 'all']:
            commands_to_run.append('import_disponibilidades_sheets')
        
        # Executar comandos canônicos
        for command in commands_to_run:
            self.stdout.write(f"\n🔄 Executando comando canônico: {command}")
            
            try:
                call_command(
                    command,
                    from='sheets',
                    dry_run=dry_run,
                    clear=clear,
                    verbose=verbose
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro no comando {command}: {e}")
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Delegação para comandos canônicos concluída!\n"
                "Lembre-se: Use os comandos canônicos diretamente no futuro."
            )
        )