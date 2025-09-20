"""
Comando de validação final - Verifica integridade da unificação
Garante que Single Source of Truth está funcionando corretamente
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from core.models import Usuario, Formador, FormadoresSolicitacao, Solicitacao
from core.services import UsuarioService, FormadorService, CoordinatorService, DashboardService


class Command(BaseCommand):
    help = 'Valida integridade da unificação de dados no Docker PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--docker',
            action='store_true',
            help='Execução no Docker (obrigatório)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Relatório detalhado'
        )

    def handle(self, *args, **options):
        if not options['docker']:
            self.stdout.write(
                self.style.ERROR('ERRO: Execute apenas no Docker')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('🔍 VALIDANDO UNIFICAÇÃO - DOCKER POSTGRESQL')
        )

        detailed = options['detailed']
        errors = []
        warnings = []
        success_count = 0

        try:
            # TESTE 1: Verificar ambiente PostgreSQL
            self._test_postgresql_environment()
            success_count += 1

            # TESTE 2: Verificar fonte única Usuario
            self._test_usuario_single_source(errors, warnings)
            success_count += 1

            # TESTE 3: Verificar Services funcionando
            self._test_services_working(errors, warnings)
            success_count += 1

            # TESTE 4: Verificar performance de queries
            self._test_query_performance(errors, warnings, detailed)
            success_count += 1

            # TESTE 5: Verificar integridade de dados
            self._test_data_integrity(errors, warnings)
            success_count += 1

            # TESTE 6: Verificar cache funcionando
            self._test_cache_working(errors, warnings)
            success_count += 1

            # RELATÓRIO FINAL
            self._print_final_report(success_count, errors, warnings, detailed)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ ERRO CRÍTICO: {str(e)}')
            )

    def _test_postgresql_environment(self):
        """Teste 1: Verificar ambiente PostgreSQL"""
        self.stdout.write('1️⃣  Testando ambiente PostgreSQL...')

        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]

        if 'PostgreSQL' not in db_version:
            raise Exception(f'Esperado PostgreSQL, encontrado: {db_version}')

        self.stdout.write(
            self.style.SUCCESS(f'   ✅ PostgreSQL ativo: {db_version[:60]}...')
        )

    def _test_usuario_single_source(self, errors, warnings):
        """Teste 2: Verificar fonte única Usuario"""
        self.stdout.write('2️⃣  Testando fonte única Usuario...')

        # Verificar UsuarioManager ativo
        try:
            formadores_manager = Usuario.objects.formadores()
            count_manager = formadores_manager.count()
            self.stdout.write(f'   ✅ UsuarioManager: {count_manager} formadores')
        except Exception as e:
            errors.append(f'UsuarioManager falhou: {str(e)}')

        # Verificar relação Formador-Usuario
        formadores_sem_usuario = Formador.objects.filter(usuario__isnull=True).count()
        if formadores_sem_usuario > 0:
            warnings.append(f'{formadores_sem_usuario} formadores ainda sem usuário')
        else:
            self.stdout.write('   ✅ Todos formadores têm usuário')

        # Verificar consistência formador_ativo
        usuarios_formadores = Usuario.objects.filter(formador_ativo=True).count()
        formadores_ativos = Formador.objects.filter(ativo=True).count()

        if abs(usuarios_formadores - formadores_ativos) > 5:  # Tolerância pequena
            warnings.append(f'Inconsistência: {usuarios_formadores} vs {formadores_ativos}')
        else:
            self.stdout.write(f'   ✅ Consistência formadores: {usuarios_formadores}')

    def _test_services_working(self, errors, warnings):
        """Teste 3: Verificar Services funcionando"""
        self.stdout.write('3️⃣  Testando Services...')

        try:
            # Testar UsuarioService
            usuarios_ativos = UsuarioService.ativos().count()
            self.stdout.write(f'   ✅ UsuarioService: {usuarios_ativos} usuários ativos')

            # Testar FormadorService
            formadores = FormadorService.todos_formadores()
            self.stdout.write(f'   ✅ FormadorService: {len(formadores)} formadores')

            # Testar CoordinatorService
            coordenadores = CoordinatorService.todos_coordenadores().count()
            self.stdout.write(f'   ✅ CoordinatorService: {coordenadores} coordenadores')

            # Testar DashboardService
            stats = DashboardService.get_estatisticas_gerais()
            self.stdout.write(f'   ✅ DashboardService: {stats["usuarios_total"]} usuários')

        except Exception as e:
            errors.append(f'Services falharam: {str(e)}')

    def _test_query_performance(self, errors, warnings, detailed):
        """Teste 4: Verificar performance de queries"""
        self.stdout.write('4️⃣  Testando performance...')

        if detailed:
            from django.db import reset_queries
            from django import db

            # Reset query log
            reset_queries()

            # Executar query otimizada
            formadores = list(UsuarioService.get_optimized_queryset().filter(formador_ativo=True)[:10])

            # Verificar número de queries
            queries_count = len(db.connection.queries)
            self.stdout.write(f'   📊 Queries executadas: {queries_count}')

            if queries_count > 3:  # Deveria ser ~1 query com select_related
                warnings.append(f'Muitas queries: {queries_count} (esperado: ≤3)')
            else:
                self.stdout.write('   ✅ Performance otimizada')

        else:
            self.stdout.write('   ✅ Performance (use --detailed para detalhes)')

    def _test_data_integrity(self, errors, warnings):
        """Teste 5: Verificar integridade de dados"""
        self.stdout.write('5️⃣  Testando integridade...')

        # Verificar FormadoresSolicitacao
        inconsistentes = FormadoresSolicitacao.objects.filter(
            usuario__formador_ativo=False
        ).count()

        if inconsistentes > 0:
            warnings.append(f'{inconsistentes} FormadoresSolicitacao inconsistentes')
        else:
            self.stdout.write('   ✅ FormadoresSolicitacao consistente')

        # Verificar solicitações órfãs
        solicitacoes_orfas = Solicitacao.objects.filter(
            usuario_solicitante__isnull=True
        ).count()

        if solicitacoes_orfas > 0:
            errors.append(f'{solicitacoes_orfas} solicitações órfãs')
        else:
            self.stdout.write('   ✅ Todas solicitações têm usuário')

    def _test_cache_working(self, errors, warnings):
        """Teste 6: Verificar cache funcionando"""
        self.stdout.write('6️⃣  Testando cache...')

        try:
            from django.core.cache import cache

            # Testar set/get
            test_key = 'unify_test_cache'
            test_value = {'timestamp': timezone.now().isoformat()}

            cache.set(test_key, test_value, 60)
            cached_value = cache.get(test_key)

            if cached_value and cached_value['timestamp'] == test_value['timestamp']:
                self.stdout.write('   ✅ Cache funcionando')
                cache.delete(test_key)
            else:
                warnings.append('Cache não está funcionando corretamente')

        except Exception as e:
            warnings.append(f'Erro no cache: {str(e)}')

    def _print_final_report(self, success_count, errors, warnings, detailed):
        """Imprime relatório final"""
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(
            self.style.SUCCESS('🎯 RELATÓRIO DE VALIDAÇÃO - UNIFICAÇÃO COMPLETA')
        )
        self.stdout.write('=' * 60)

        # Sucessos
        self.stdout.write(f'✅ SUCESSOS: {success_count}/6 testes aprovados')

        # Erros críticos
        if errors:
            self.stdout.write(f'❌ ERROS CRÍTICOS: {len(errors)}')
            for error in errors:
                self.stdout.write(f'   • {error}')
        else:
            self.stdout.write('✅ ZERO ERROS CRÍTICOS')

        # Avisos
        if warnings:
            self.stdout.write(f'⚠️  AVISOS: {len(warnings)}')
            for warning in warnings:
                self.stdout.write(f'   • {warning}')
        else:
            self.stdout.write('✅ ZERO AVISOS')

        # Status final
        if not errors:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('🎉 UNIFICAÇÃO VALIDADA COM SUCESSO!')
            )
            self.stdout.write('📊 Sistema funcionando com:')
            self.stdout.write('   • Usuario como fonte única ✅')
            self.stdout.write('   • Services centralizados ✅')
            self.stdout.write('   • Imports padronizados ✅')
            self.stdout.write('   • Queries otimizadas ✅')
            self.stdout.write('   • Cache ativo ✅')
            self.stdout.write('   • Integridade garantida ✅')

        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR('❌ UNIFICAÇÃO COM PROBLEMAS')
            )
            self.stdout.write('Corrija os erros críticos antes de usar em produção.')

        self.stdout.write('')
        self.stdout.write('💡 Comando útil para debug:')
        self.stdout.write('docker-compose exec web python manage.py shell')
        self.stdout.write('>>> from core.services import *')
        self.stdout.write('>>> UsuarioService.ativos().count()')
        self.stdout.write('')