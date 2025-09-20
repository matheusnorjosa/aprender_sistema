"""
Comando Django para ajustar os papéis/grupos dos usuários baseado nos dados conhecidos.
Define coordenadores, gerentes e formadores nos grupos corretos.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from django.db import models
from core.models import Usuario


class Command(BaseCommand):
    help = 'Ajusta os papéis/grupos dos usuários baseado nos dados conhecidos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo simulação sem fazer alterações'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas do processo'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACAO - Nenhuma alteracao sera feita')
            )

        # Garantir que todos os grupos existem
        grupos_necessarios = [
            'coordenador',
            'superintendencia',
            'controle',
            'formador',
            'diretoria',
            'admin'
        ]

        for grupo_nome in grupos_necessarios:
            grupo, created = Group.objects.get_or_create(name=grupo_nome)
            if created and verbose:
                self.stdout.write(f"Grupo '{grupo_nome}' criado")

        # Mapeamento de usuários conhecidos por papel
        # Baseado nos dados das planilhas e análises anteriores
        coordenadores_conhecidos = {
            'Ellen Damares': {'email': 'coordenacao41@aprendereditora.com.br', 'cpf': '87521105320'},
            'Rafael Rabelo': {'email': 'coordenacao60@aprendereditora.com.br', 'cpf': '96288795372'},
            'Maria Nadir': {'nome_variacao': 'Maria Nadir'},  # Aparece como coordenadora nas planilhas
        }

        # Gerentes/Superintendência (baseado na análise de dados)
        gerentes_conhecidos = {
            'Aurea Lucia': {'nome_variacao': 'Aurea Lucia'},  # Mencionada nas análises
        }

        # Usuarios especiais (admin, controle)
        usuarios_especiais = {
            'admin': 'admin',  # superuser padrão
            'controle': 'controle_teste',  # usuário de controle
        }

        estatisticas = {
            'coordenadores_definidos': 0,
            'gerentes_definidos': 0,
            'formadores_mantidos': 0,
            'usuarios_especiais': 0,
            'erros': 0
        }

        with transaction.atomic():
            if dry_run:
                sid = transaction.savepoint()

            # 1. Definir coordenadores
            for nome, dados in coordenadores_conhecidos.items():
                try:
                    usuario = None

                    # Tentar encontrar por CPF primeiro
                    if 'cpf' in dados:
                        try:
                            usuario = Usuario.objects.get(cpf=dados['cpf'])
                        except Usuario.DoesNotExist:
                            pass

                    # Tentar encontrar por email
                    if not usuario and 'email' in dados:
                        try:
                            usuario = Usuario.objects.get(email=dados['email'])
                        except Usuario.DoesNotExist:
                            pass

                    # Tentar encontrar por nome
                    if not usuario:
                        # Buscar por nome completo ou parte do nome
                        usuarios_nome = Usuario.objects.filter(
                            models.Q(first_name__icontains=nome.split()[0]) |
                            models.Q(last_name__icontains=nome.split()[-1])
                        )
                        if usuarios_nome.count() == 1:
                            usuario = usuarios_nome.first()

                    if usuario:
                        if verbose:
                            self.stdout.write(f"Definindo {usuario.nome_completo} como COORDENADOR")

                        if not dry_run:
                            # Limpar grupos antigos relacionados
                            usuario.groups.clear()
                            # Adicionar ao grupo coordenador
                            usuario.groups.add(Group.objects.get(name='coordenador'))
                            # Definir cargo
                            usuario.cargo = 'coordenador'
                            usuario.save()

                        estatisticas['coordenadores_definidos'] += 1
                    else:
                        if verbose:
                            self.stdout.write(f"AVISO: Coordenador {nome} nao encontrado")

                except Exception as e:
                    estatisticas['erros'] += 1
                    self.stdout.write(
                        self.style.ERROR(f"Erro ao processar coordenador {nome}: {str(e)}")
                    )

            # 2. Definir gerentes/superintendência
            for nome, dados in gerentes_conhecidos.items():
                try:
                    # Buscar por nome
                    usuarios_nome = Usuario.objects.filter(
                        models.Q(first_name__icontains=nome.split()[0]) |
                        models.Q(last_name__icontains=nome.split()[-1])
                    )

                    if usuarios_nome.count() == 1:
                        usuario = usuarios_nome.first()
                        if verbose:
                            self.stdout.write(f"Definindo {usuario.nome_completo} como GERENTE/SUPERINTENDENCIA")

                        if not dry_run:
                            usuario.groups.clear()
                            usuario.groups.add(Group.objects.get(name='superintendencia'))
                            usuario.cargo = 'gerente'
                            usuario.save()

                        estatisticas['gerentes_definidos'] += 1
                    else:
                        if verbose:
                            self.stdout.write(f"AVISO: Gerente {nome} nao encontrado ou ambiguo")

                except Exception as e:
                    estatisticas['erros'] += 1
                    self.stdout.write(
                        self.style.ERROR(f"Erro ao processar gerente {nome}: {str(e)}")
                    )

            # 3. Manter formadores que já foram migrados (exceto coordenadores e gerentes)
            formadores_ativos = Usuario.objects.filter(formador_ativo=True)
            coordenadores_definidos = Usuario.objects.filter(groups__name='coordenador')
            gerentes_definidos = Usuario.objects.filter(groups__name='superintendencia')

            for usuario in formadores_ativos:
                # Não sobrescrever se já foi definido como coordenador ou gerente
                if (not coordenadores_definidos.filter(id=usuario.id).exists() and
                    not gerentes_definidos.filter(id=usuario.id).exists()):

                    if verbose:
                        self.stdout.write(f"Mantendo {usuario.nome_completo} como FORMADOR")

                    if not dry_run:
                        # Garantir que está no grupo formador (sem limpar outros grupos)
                        if not usuario.groups.filter(name='formador').exists():
                            usuario.groups.add(Group.objects.get(name='formador'))
                        # Manter cargo se não definido
                        if not usuario.cargo:
                            usuario.cargo = 'formador'
                            usuario.save()

                    estatisticas['formadores_mantidos'] += 1

            # 4. Definir usuários especiais
            for papel, username in usuarios_especiais.items():
                try:
                    usuario = Usuario.objects.get(username=username)
                    if verbose:
                        self.stdout.write(f"Definindo {usuario.username} como {papel.upper()}")

                    if not dry_run:
                        usuario.groups.clear()
                        usuario.groups.add(Group.objects.get(name=papel))
                        usuario.cargo = papel
                        usuario.save()

                    estatisticas['usuarios_especiais'] += 1

                except Usuario.DoesNotExist:
                    if verbose:
                        self.stdout.write(f"AVISO: Usuario {username} nao encontrado")
                except Exception as e:
                    estatisticas['erros'] += 1
                    self.stdout.write(
                        self.style.ERROR(f"Erro ao processar usuario especial {username}: {str(e)}")
                    )

            if dry_run:
                transaction.savepoint_rollback(sid)

        # Relatório final
        self.stdout.write(f"\nRELATORIO FINAL:")
        self.stdout.write(f"   Coordenadores definidos: {estatisticas['coordenadores_definidos']}")
        self.stdout.write(f"   Gerentes/Superintendencia: {estatisticas['gerentes_definidos']}")
        self.stdout.write(f"   Formadores mantidos: {estatisticas['formadores_mantidos']}")
        self.stdout.write(f"   Usuarios especiais: {estatisticas['usuarios_especiais']}")
        self.stdout.write(f"   Erros: {estatisticas['erros']}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nSimulacao concluida - Execute sem --dry-run para aplicar as alteracoes')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nPapeis ajustados com sucesso!')
            )

            # Mostrar estatísticas por grupo
            self.stdout.write(f"\nESTATISTICAS POR GRUPO:")
            for grupo_nome in grupos_necessarios:
                grupo = Group.objects.get(name=grupo_nome)
                count = grupo.user_set.count()
                self.stdout.write(f"   {grupo_nome}: {count} usuarios")