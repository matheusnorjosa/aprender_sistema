"""
Comando para criar dados de exemplo para demonstração do sistema
"""

import random
from datetime import datetime, timedelta
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    Usuario, Formador, Solicitacao, SolicitacaoStatus, 
    Municipio, Projeto, TipoEvento, Setor
)


class Command(BaseCommand):
    help = "Cria dados de exemplo para demonstração do sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula a criação sem salvar no banco",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN ==="))

        try:
            with transaction.atomic():
                # Criar usuários de exemplo
                self.create_demo_users()
                
                # Criar solicitações de exemplo
                self.create_sample_solicitacoes()
                
                if self.dry_run:
                    self.stdout.write(
                        self.style.WARNING("DRY-RUN: Transação revertida")
                    )
                    transaction.set_rollback(True)
                else:
                    self.stdout.write(
                        self.style.SUCCESS("Dados de exemplo criados com sucesso!")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro na criação de dados: {str(e)}")
            )
            raise

    def create_demo_users(self):
        """Cria usuários de demonstração"""
        self.stdout.write("Criando usuarios de demonstracao...")
        
        # Verificar se grupos existem
        groups_needed = ['coordenador', 'formador', 'superintendencia', 'controle']
        for group_name in groups_needed:
            group, created = Group.objects.get_or_create(name=group_name)
            if created and not self.dry_run:
                self.stdout.write(f"  Grupo criado: {group_name}")

        # Obter setor padrão
        setor_default = Setor.objects.first()

        demo_users = [
            {
                'username': 'coord_demo',
                'password': 'demo123',
                'first_name': 'Maria',
                'last_name': 'Coordenadora Demo',
                'email': 'coord.demo@aprender.local',
                'cpf': '12345678901',
                'groups': ['coordenador'],
            },
            {
                'username': 'formador_demo',
                'password': 'demo123',
                'first_name': 'João',
                'last_name': 'Formador Demo',
                'email': 'formador.demo@aprender.local',
                'cpf': '12345678902',
                'groups': ['formador'],
            },
            {
                'username': 'formador_demo2',
                'password': 'demo123',
                'first_name': 'Ana',
                'last_name': 'Silva Demo',
                'email': 'ana.demo@aprender.local',
                'cpf': '12345678903',
                'groups': ['formador'],
            },
            {
                'username': 'super_demo',
                'password': 'demo123',
                'first_name': 'Carlos',
                'last_name': 'Superintendente Demo',
                'email': 'super.demo@aprender.local',
                'cpf': '12345678904',
                'groups': ['superintendencia'],
                'is_staff': True,
            },
        ]
        
        created_count = 0
        for user_data in demo_users:
            if not self.dry_run:
                # Verificar se já existe
                if Usuario.objects.filter(username=user_data['username']).exists():
                    continue
                
                try:
                    # Criar usuário
                    usuario = Usuario.objects.create(
                        username=user_data['username'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        email=user_data['email'],
                        cpf=user_data['cpf'],
                        telefone='85 99999-0000',
                        setor=setor_default,
                        is_active=True,
                        is_staff=user_data.get('is_staff', False),
                    )
                    
                    # Definir senha
                    usuario.set_password(user_data['password'])
                    usuario.save()
                    
                    # Adicionar a grupos
                    for group_name in user_data['groups']:
                        try:
                            group = Group.objects.get(name=group_name)
                            usuario.groups.add(group)
                        except Group.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"Grupo não encontrado: {group_name}")
                            )
                    
                    # Criar formador se necessário
                    if 'formador' in user_data['groups']:
                        # Verificar se já existe formador com mesmo email
                        if not Formador.objects.filter(email=usuario.email).exists():
                            Formador.objects.create(
                                usuario=usuario,
                                nome=usuario.get_full_name(),
                                email=usuario.email,
                                ativo=True,
                            )
                    
                    created_count += 1
                    self.stdout.write(f"  Usuario criado: {user_data['username']}")
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Erro ao criar usuario {user_data['username']}: {str(e)}")
                    )
            else:
                created_count += 1  # Simular para dry-run
        
        self.stdout.write(f"Usuarios de demonstracao criados: {created_count}")

    def create_sample_solicitacoes(self):
        """Cria solicitações de exemplo"""
        self.stdout.write("Criando solicitacoes de exemplo...")
        
        # Obter dados necessários
        coordenadores = Usuario.objects.filter(groups__name='coordenador')
        formadores = Formador.objects.filter(ativo=True)
        municipios = list(Municipio.objects.filter(ativo=True)[:10])
        projetos = list(Projeto.objects.filter(ativo=True)[:10])
        tipos_evento = list(TipoEvento.objects.filter(ativo=True))
        
        if not all([coordenadores.exists(), formadores.exists(), municipios, projetos, tipos_evento]):
            self.stdout.write(
                self.style.WARNING("Dados insuficientes para criar solicitações de exemplo")
            )
            return
        
        # Criar solicitações variadas
        sample_solicitacoes = []
        
        # Solicitação pendente
        sample_solicitacoes.append({
            'titulo': 'Formação em Alfabetização - Turma Janeiro',
            'descricao': 'Formação inicial para professores do 1º ano do ensino fundamental, focando em métodos de alfabetização.',
            'data_inicio': timezone.now() + timedelta(days=15),
            'data_fim': timezone.now() + timedelta(days=15, hours=4),
            'municipio': random.choice(municipios),
            'projeto': random.choice(projetos),
            'tipo_evento': random.choice(tipos_evento),
            'status': SolicitacaoStatus.PENDENTE,
            'observacoes': 'Primeira turma do ano, priorizar formadores experientes.',
        })
        
        # Solicitação aprovada
        sample_solicitacoes.append({
            'titulo': 'Workshop de Matemática Lúdica',
            'descricao': 'Workshop prático sobre uso de jogos e atividades lúdicas no ensino de matemática.',
            'data_inicio': timezone.now() + timedelta(days=25),
            'data_fim': timezone.now() + timedelta(days=25, hours=6),
            'municipio': random.choice(municipios),
            'projeto': random.choice(projetos),
            'tipo_evento': random.choice(tipos_evento),
            'status': SolicitacaoStatus.APROVADO,
            'observacoes': 'Incluir materiais práticos para as atividades.',
        })
        
        # Solicitação em pré-agenda
        sample_solicitacoes.append({
            'titulo': 'Seminário de Competências Socioemocionais',
            'descricao': 'Seminário sobre desenvolvimento de competências socioemocionais em ambiente escolar.',
            'data_inicio': timezone.now() + timedelta(days=30),
            'data_fim': timezone.now() + timedelta(days=30, hours=8),
            'municipio': random.choice(municipios),
            'projeto': random.choice(projetos),
            'tipo_evento': random.choice(tipos_evento),
            'status': SolicitacaoStatus.PRE_AGENDA,
            'observacoes': 'Aguardando confirmação de disponibilidade do auditório.',
        })
        
        # Solicitação para próxima semana
        sample_solicitacoes.append({
            'titulo': 'Formação Continuada - IDEB e Avaliações',
            'descricao': 'Formação sobre interpretação de dados do IDEB e preparação para avaliações externas.',
            'data_inicio': timezone.now() + timedelta(days=7),
            'data_fim': timezone.now() + timedelta(days=7, hours=5),
            'municipio': random.choice(municipios),
            'projeto': random.choice(projetos),
            'tipo_evento': random.choice(tipos_evento),
            'status': SolicitacaoStatus.PENDENTE,
            'observacoes': 'Solicitação urgente para preparação das escolas.',
        })
        
        created_count = 0
        for sol_data in sample_solicitacoes:
            if not self.dry_run:
                try:
                    coordenador = random.choice(coordenadores)
                    
                    solicitacao = Solicitacao.objects.create(
                        solicitante=coordenador,
                        titulo=sol_data['titulo'],
                        descricao=sol_data['descricao'],
                        data_inicio=sol_data['data_inicio'],
                        data_fim=sol_data['data_fim'],
                        municipio=sol_data['municipio'],
                        projeto=sol_data['projeto'],
                        tipo_evento=sol_data['tipo_evento'],
                        status=sol_data['status'],
                        observacoes=sol_data['observacoes'],
                        publico_estimado=random.randint(20, 80),
                        necessita_transporte=random.choice([True, False]),
                        necessita_lanche=random.choice([True, False]),
                        necessita_almoco=random.choice([True, False]),
                    )
                    
                    # Adicionar formadores à solicitação
                    num_formadores = random.randint(1, min(3, formadores.count()))
                    formadores_selecionados = random.sample(list(formadores), num_formadores)
                    
                    for formador in formadores_selecionados:
                        from core.models import FormadoresSolicitacao
                        FormadoresSolicitacao.objects.get_or_create(
                            solicitacao=solicitacao,
                            formador=formador
                        )
                    
                    created_count += 1
                    self.stdout.write(f"  Solicitacao criada: {sol_data['titulo'][:50]}...")
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Erro ao criar solicitacao: {str(e)}")
                    )
            else:
                created_count += 1  # Simular para dry-run
        
        self.stdout.write(f"Solicitacoes de exemplo criadas: {created_count}")