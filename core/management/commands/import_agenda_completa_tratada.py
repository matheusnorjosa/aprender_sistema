"""
Comando DEPRECATED: Importação de Agenda Completa Tratada
=========================================================

⚠️  DEPRECATED: Este comando foi substituído pelo comando canônico em ingestao/
Use: python manage.py ingestao.import_eventos_abas --from=sheets --aba=all

Autor: Claude Code  
Data: Janeiro 2025
"""

import warnings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = "⚠️  DEPRECATED: Use o comando canônico ingestao.import_eventos_abas"

    def add_arguments(self, parser):
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
                "Use o comando canônico:\n"
                "  python manage.py ingestao.import_eventos_abas --from=sheets --aba=all\n"
            )
        )
        
        dry_run = options['dry_run']
        clear = options['clear']
        verbose = options['verbose']
        
        # Delegar para comando canônico
        self.stdout.write("\n🔄 Executando comando canônico: ingestao.import_eventos_abas")
        
        try:
            call_command(
                'ingestao.import_eventos_abas',
                from='sheets',
                aba='all',
                dry_run=dry_run,
                clear=clear,
                verbose=verbose
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ Delegação para comando canônico concluída!\n"
                    "Lembre-se: Use 'ingestao.import_eventos_abas' diretamente no futuro."
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erro no comando canônico: {e}")
            )
            raise CommandError(f"Falha na delegação: {e}")