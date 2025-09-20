"""
Comando UNIFICADO para consolidar todas as referências de dados
Migra Formador → Usuario (fonte única) no Docker PostgreSQL

EXECUÇÃO NO DOCKER:
docker-compose exec web python manage.py unify_data_references --docker
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.contrib.auth.models import Group
from django.utils import timezone
from core.models import Usuario, Formador, FormadoresSolicitacao, DisponibilidadeFormadores

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Unifica todas as referências de dados - Docker PostgreSQL centralizao'

    def add_arguments(self, parser):
        parser.add_argument(
            '--docker',
            action='store_true',
            help='Execução no ambiente Docker (OBRIGATÓRIO)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulação sem alterar dados'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força execução mesmo com dados existentes'
        )

    def handle(self, *args, **options):
        if not options['docker']:
            self.stdout.write(
                self.style.ERROR('ERRO: Este comando DEVE ser executado no Docker')
            )
            self.stdout.write(
                self.style.WARNING('Use: docker-compose exec web python manage.py unify_data_references --docker')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('🐳 INICIANDO UNIFICAÇÃO NO DOCKER POSTGRESQL')
        )

        dry_run = options['dry_run']
        force = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO SIMULAÇÃO - Nenhum dado será alterado'))

        with transaction.atomic():
            try:
                # FASE 1: Verificar ambiente Docker
                self._verificar_ambiente_docker()

                # FASE 2: Migrar Formador → Usuario
                self._migrar_formadores_para_usuarios(dry_run, force)

                # FASE 3: Atualizar relacionamentos
                self._atualizar_relacionamentos(dry_run)

                # FASE 4: Verificar integridade
                self._verificar_integridade()

                if not dry_run:
                    self.stdout.write(
                        self.style.SUCCESS('✅ UNIFICAÇÃO COMPLETA - DOCKER POSTGRESQL')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('🔍 SIMULAÇÃO COMPLETA - Use sem --dry-run para aplicar')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ ERRO NA UNIFICAÇÃO: {str(e)}')
                )
                raise

    def _verificar_ambiente_docker(self):
        """Verifica se está rodando no ambiente Docker correto"""
        self.stdout.write('🔍 Verificando ambiente Docker...')

        # Verificar se é PostgreSQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]

        if 'PostgreSQL' not in db_version:
            raise Exception(f'ERRO: Esperado PostgreSQL, encontrado: {db_version}')

        self.stdout.write(
            self.style.SUCCESS(f'✅ Docker PostgreSQL detectado: {db_version[:50]}...')
        )

        # Verificar modelos
        total_usuarios = Usuario.objects.count()
        total_formadores = Formador.objects.count()

        self.stdout.write(f'📊 Estado atual: {total_usuarios} usuários, {total_formadores} formadores')

    def _migrar_formadores_para_usuarios(self, dry_run, force):
        """Migra dados de Formador para Usuario (fonte única)"""
        self.stdout.write('🔄 Iniciando migração Formador → Usuario...')

        formadores = Formador.objects.select_related('usuario', 'area_atuacao').all()
        migrados = 0
        criados = 0

        for formador in formadores:
            try:
                if formador.usuario:
                    # Formador já tem Usuario associado - atualizar dados
                    usuario = formador.usuario
                    updated = False

                    # Consolidar campos do Formador no Usuario
                    if not usuario.formador_ativo:
                        usuario.formador_ativo = formador.ativo
                        updated = True

                    if not usuario.area_atuacao and formador.area_atuacao:
                        usuario.area_atuacao = formador.area_atuacao
                        updated = True

                    # Garantir grupo formador
                    grupo_formador, _ = Group.objects.get_or_create(name='formador')
                    if not usuario.groups.filter(name='formador').exists():
                        if not dry_run:
                            usuario.groups.add(grupo_formador)
                        updated = True

                    if updated and not dry_run:
                        usuario.save()

                    migrados += 1
                    self.stdout.write(f'📝 Migrado: {formador.nome} → {usuario.username}')

                else:
                    # Formador sem Usuario - criar Usuario
                    if not dry_run:
                        usuario = Usuario.objects.create_user(
                            username=self._gerar_username_unico(formador.nome),
                            email=formador.email,
                            first_name=formador.nome.split()[0] if formador.nome.split() else '',
                            last_name=' '.join(formador.nome.split()[1:]) if len(formador.nome.split()) > 1 else '',
                            formador_ativo=formador.ativo,
                            area_atuacao=formador.area_atuacao
                        )

                        # Adicionar ao grupo formador
                        grupo_formador, _ = Group.objects.get_or_create(name='formador')
                        usuario.groups.add(grupo_formador)

                        # Conectar Formador ao Usuario
                        formador.usuario = usuario
                        formador.save()

                    criados += 1
                    self.stdout.write(f'🆕 Criado: {formador.nome} → novo usuário')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro ao migrar {formador.nome}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'✅ Migração concluída: {migrados} atualizados, {criados} criados')
        )

    def _gerar_username_unico(self, nome):
        """Gera username único baseado no nome"""
        base_username = nome.lower().replace(' ', '_')[:30]
        username = base_username
        contador = 1

        while Usuario.objects.filter(username=username).exists():
            username = f"{base_username}_{contador}"
            contador += 1

        return username

    def _atualizar_relacionamentos(self, dry_run):
        """Atualiza relacionamentos para usar Usuario único"""
        self.stdout.write('🔗 Atualizando relacionamentos...')

        # FormadoresSolicitacao já usa Usuario - verificar consistência
        inconsistencias = FormadoresSolicitacao.objects.filter(
            usuario__formador_ativo=False
        ).count()

        if inconsistencias > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {inconsistencias} inconsistências em FormadoresSolicitacao')
            )

        # DisponibilidadeFormadores já usa Usuario - verificar
        disponibilidades = DisponibilidadeFormadores.objects.filter(
            usuario__isnull=True
        ).count()

        if disponibilidades > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {disponibilidades} disponibilidades sem usuário')
            )

        self.stdout.write('✅ Relacionamentos verificados')

    def _verificar_integridade(self):
        """Verifica integridade dos dados após migração"""
        self.stdout.write('🔍 Verificando integridade...')

        # Verificar se todos os formadores têm Usuario
        formadores_sem_usuario = Formador.objects.filter(usuario__isnull=True).count()
        if formadores_sem_usuario > 0:
            raise Exception(f'ERRO: {formadores_sem_usuario} formadores ainda sem usuário')

        # Verificar se todos os usuários formadores têm grupo correto
        usuarios_formadores = Usuario.objects.filter(formador_ativo=True)
        sem_grupo = usuarios_formadores.exclude(groups__name='formador').count()
        if sem_grupo > 0:
            raise Exception(f'ERRO: {sem_grupo} usuários formadores sem grupo')

        # Estatísticas finais
        stats = {
            'total_usuarios': Usuario.objects.count(),
            'usuarios_formadores': Usuario.objects.filter(formador_ativo=True).count(),
            'formadores_legacy': Formador.objects.count(),
            'solicitacoes_formador': FormadoresSolicitacao.objects.count(),
            'disponibilidades': DisponibilidadeFormadores.objects.count()
        }

        self.stdout.write('📊 ESTATÍSTICAS FINAIS:')
        for key, value in stats.items():
            self.stdout.write(f'   {key}: {value}')

        self.stdout.write(
            self.style.SUCCESS('✅ Integridade verificada - DADOS UNIFICADOS NO DOCKER')
        )