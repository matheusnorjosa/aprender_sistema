"""
Comando para popular o banco de dados com os dados extraídos das planilhas
Utiliza os arquivos JSON extraídos em archive/temp_data/
"""

import json
import re
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Usuario, Municipio, Setor, Projeto, TipoEvento, 
    Formador, Solicitacao, DisponibilidadeFormadores
)


class Command(BaseCommand):
    help = "Popula o banco com dados extraídos das planilhas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula a importação sem salvar no banco",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Limpa dados existentes antes de importar",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.clear_existing = options["clear_existing"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN ==="))

        try:
            # Carregar dados extraídos
            self.load_extracted_data()
            
            with transaction.atomic():
                if self.clear_existing and not self.dry_run:
                    self.clear_existing_data()
                
                # 1. Criar estrutura organizacional básica
                self.create_basic_structure()
                
                # 2. Importar usuários
                self.import_users()
                
                # 3. Criar formadores
                self.create_formadores()
                
                # 4. Criar usuários de teste
                self.create_test_users()
                
                if self.dry_run:
                    self.stdout.write(
                        self.style.WARNING("DRY-RUN: Transação revertida")
                    )
                    transaction.set_rollback(True)
                else:
                    self.stdout.write(
                        self.style.SUCCESS("Dados importados com sucesso!")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro na importacao: {str(e)}")
            )
            raise

    def load_extracted_data(self):
        """Carrega os dados extraídos das planilhas"""
        try:
            with open('archive/temp_data/extracted_all_data.json', 'r', encoding='utf-8') as f:
                self.extracted_data = json.load(f)
            
            self.stdout.write(
                self.style.SUCCESS("Dados extraidos carregados com sucesso")
            )
            
            # Estatísticas dos dados
            usuarios_count = len(self.extracted_data.get('usuarios', {}).get('worksheets', {}).get('Ativos', {}).get('data', []))
            self.stdout.write(f"Usuarios encontrados: {usuarios_count}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro ao carregar dados: {str(e)}")
            )
            raise

    def clear_existing_data(self):
        """Limpa dados existentes do banco"""
        self.stdout.write("Limpando dados existentes...")
        
        # Ordem inversa para respeitar foreign keys
        from core.models import FormadoresSolicitacao, Aprovacao
        
        # Primeiro, apagar relacionamentos
        FormadoresSolicitacao.objects.all().delete()
        Aprovacao.objects.all().delete()
        
        # Depois, apagar modelos principais
        Solicitacao.objects.all().delete()
        DisponibilidadeFormadores.objects.all().delete()
        Formador.objects.all().delete()
        Usuario.objects.filter(is_superuser=False).delete()
        
        self.stdout.write("Dados limpos")

    def create_basic_structure(self):
        """Cria estrutura organizacional básica"""
        self.stdout.write("Criando estrutura organizacional...")
        
        # Criar grupos Django
        grupos = [
            'superintendencia',
            'coordenador', 
            'formador',
            'controle',
            'diretoria',
            'admin'
        ]
        
        for grupo_name in grupos:
            group, created = Group.objects.get_or_create(name=grupo_name)
            if created and not self.dry_run:
                self.stdout.write(f"  Grupo criado: {grupo_name}")
        
        # Criar setores
        setores_data = [
            {'nome': 'Superintendência', 'sigla': 'SUPER', 'vinculado_superintendencia': True},
            {'nome': 'ACerta', 'sigla': 'ACERTA', 'vinculado_superintendencia': False},
            {'nome': 'Vidas', 'sigla': 'VIDAS', 'vinculado_superintendencia': False},
            {'nome': 'Vidas M', 'sigla': 'VIDAS_M', 'vinculado_superintendencia': False},
            {'nome': 'Brincando e Aprendendo', 'sigla': 'BRINC', 'vinculado_superintendencia': False},
            {'nome': 'IDEB10', 'sigla': 'IDEB10', 'vinculado_superintendencia': False},
            {'nome': 'Outros', 'sigla': 'OUTROS', 'vinculado_superintendencia': False},
        ]
        
        for setor_data in setores_data:
            setor, created = Setor.objects.get_or_create(
                nome=setor_data['nome'],
                defaults={
                    'sigla': setor_data['sigla'],
                    'vinculado_superintendencia': setor_data['vinculado_superintendencia']
                }
            )
            if created and not self.dry_run:
                self.stdout.write(f"  Setor criado: {setor.nome}")
        
        # Criar municípios básicos (serão expandidos depois)
        municipios_basicos = [
            'Fortaleza', 'Caucaia', 'Maracanaú', 'Sobral', 'Juazeiro do Norte',
            'Crato', 'Itapipoca', 'Aquiraz', 'Pacatuba', 'Maranguape'
        ]
        
        for municipio_nome in municipios_basicos:
            municipio, created = Municipio.objects.get_or_create(
                nome=municipio_nome,
                defaults={'ativo': True}
            )
            if created and not self.dry_run:
                self.stdout.write(f"  Municipio criado: {municipio.nome}")
        
        # Criar tipos de evento básicos
        tipos_evento = [
            {'nome': 'Formação Inicial', 'online': False},
            {'nome': 'Formação Continuada', 'online': False},
            {'nome': 'Workshop', 'online': True},
            {'nome': 'Seminário', 'online': True},
            {'nome': 'Palestra', 'online': True},
            {'nome': 'Mesa Redonda', 'online': False},
        ]
        
        for tipo_data in tipos_evento:
            tipo, created = TipoEvento.objects.get_or_create(
                nome=tipo_data['nome'],
                defaults={
                    'online': tipo_data['online'],
                    'ativo': True
                }
            )
            if created and not self.dry_run:
                self.stdout.write(f"  Tipo de evento criado: {tipo.nome}")
        
        # Criar projetos básicos
        projetos_basicos = [
            {'nome': 'Alfabetização', 'setor': 'Superintendência'},
            {'nome': 'Matemática Básica', 'setor': 'ACerta'},
            {'nome': 'Competências Socioemocionais', 'setor': 'Vidas'},
            {'nome': 'Educação Infantil', 'setor': 'Brincando e Aprendendo'},
            {'nome': 'IDEB e Avaliações', 'setor': 'IDEB10'},
        ]
        
        for projeto_data in projetos_basicos:
            try:
                setor = Setor.objects.get(nome=projeto_data['setor'])
                projeto, created = Projeto.objects.get_or_create(
                    nome=projeto_data['nome'],
                    defaults={
                        'setor': setor,
                        'ativo': True
                    }
                )
                if created and not self.dry_run:
                    self.stdout.write(f"  Projeto criado: {projeto.nome}")
            except Setor.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Setor nao encontrado: {projeto_data['setor']}")
                )

    def import_users(self):
        """Importa usuários da planilha extraída"""
        self.stdout.write("Importando usuarios...")
        
        usuarios_data = self.extracted_data.get('usuarios', {}).get('worksheets', {}).get('Ativos', {}).get('data', [])
        
        if not usuarios_data:
            self.stdout.write(self.style.WARNING("Nenhum usuario encontrado nos dados"))
            return
        
        headers = self.extracted_data.get('usuarios', {}).get('worksheets', {}).get('Ativos', {}).get('headers', [])
        
        # Mapear índices das colunas
        nome_idx = self._find_header_index(headers, 'Nome')
        nome_completo_idx = self._find_header_index(headers, 'Nome Completo')
        cpf_idx = self._find_header_index(headers, 'CPF')
        telefone_idx = self._find_header_index(headers, 'Telefone')
        email_idx = self._find_header_index(headers, 'Email')
        cargo_idx = self._find_header_index(headers, 'Cargo')
        gerencia_idx = self._find_header_index(headers, 'Gerência')
        
        imported_count = 0
        skipped_count = 0
        
        for row_data in usuarios_data:
            try:
                # Extrair dados da linha
                nome = self._get_cell_value(row_data, nome_idx, '').strip()
                nome_completo = self._get_cell_value(row_data, nome_completo_idx, '').strip()
                cpf_raw = self._get_cell_value(row_data, cpf_idx, '').strip()
                telefone = self._get_cell_value(row_data, telefone_idx, '').strip()
                email = self._get_cell_value(row_data, email_idx, '').strip()
                cargo = self._get_cell_value(row_data, cargo_idx, '').strip()
                gerencia = self._get_cell_value(row_data, gerencia_idx, '').strip()
                
                # Limpar e validar CPF
                cpf = re.sub(r'[^0-9]', '', cpf_raw)
                
                # Validações básicas
                if not nome or not cpf or len(cpf) != 11:
                    skipped_count += 1
                    continue
                
                # Limpar email (remover tabs e espaços)
                email = re.sub(r'\s+', '', email)
                if not email or '@' not in email:
                    email = f"{cpf}@temp.local"  # Email temporário
                
                # Determinar setor baseado na gerência
                setor = self._map_gerencia_to_setor(gerencia)
                
                # Determinar grupo baseado no cargo
                grupo_name = self._map_cargo_to_grupo(cargo)
                
                if not self.dry_run:
                    # Criar usuário
                    usuario, created = Usuario.objects.get_or_create(
                        cpf=cpf,
                        defaults={
                            'username': cpf,  # Username será o CPF
                            'first_name': nome,
                            'last_name': nome_completo.replace(nome, '').strip(),
                            'email': email,
                            'telefone': telefone,
                            'setor': setor,
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        # Definir senha padrão (CPF)
                        usuario.set_password(cpf)
                        usuario.save()
                        
                        # Adicionar ao grupo
                        if grupo_name:
                            try:
                                grupo = Group.objects.get(name=grupo_name)
                                usuario.groups.add(grupo)
                            except Group.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(f"Grupo nao encontrado: {grupo_name}")
                                )
                        
                        imported_count += 1
                        
                        if imported_count % 10 == 0:  # Progress feedback
                            self.stdout.write(f"  Importados: {imported_count}")
                else:
                    imported_count += 1  # Simular para dry-run
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Erro ao importar usuario {nome}: {str(e)}")
                )
                skipped_count += 1
        
        self.stdout.write(f"Usuarios importados: {imported_count}")
        self.stdout.write(f"Usuarios ignorados: {skipped_count}")

    def create_formadores(self):
        """Cria registros de formadores baseados nos usuários importados"""
        self.stdout.write("Criando formadores...")
        
        formadores_group = Group.objects.filter(name='formador').first()
        if not formadores_group:
            self.stdout.write(self.style.WARNING("Grupo 'formador' nao encontrado"))
            return
        
        usuarios_formadores = Usuario.objects.filter(groups=formadores_group)
        created_count = 0
        
        for usuario in usuarios_formadores:
            if not self.dry_run:
                formador, created = Formador.objects.get_or_create(
                    usuario=usuario,
                    defaults={
                        'nome': usuario.get_full_name() or usuario.first_name,
                        'email': usuario.email,
                        'ativo': True,
                    }
                )
                if created:
                    created_count += 1
            else:
                created_count += 1  # Simular para dry-run
        
        self.stdout.write(f"Formadores criados: {created_count}")

    def create_test_users(self):
        """Cria usuários de teste para demonstração"""
        self.stdout.write("Criando usuarios de teste...")
        
        test_users_data = [
            {
                'username': 'admin',
                'password': 'admin123',
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'email': 'admin@aprender.local',
                'cpf': '00000000001',
                'groups': ['admin'],
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'superintendente',
                'password': 'super123',
                'first_name': 'Maria',
                'last_name': 'Superintendente',
                'email': 'superintendente@aprender.local',
                'cpf': '11111111111',
                'groups': ['superintendencia'],
                'is_staff': True,
            },
            {
                'username': 'coordenador',
                'password': 'coord123',
                'first_name': 'João',
                'last_name': 'Coordenador',
                'email': 'coordenador@aprender.local',
                'cpf': '22222222222',
                'groups': ['coordenador'],
            },
            {
                'username': 'formador_teste',
                'password': 'form123',
                'first_name': 'Ana',
                'last_name': 'Formadora',
                'email': 'formadora@aprender.local',
                'cpf': '33333333333',
                'groups': ['formador'],
            },
            {
                'username': 'controle',
                'password': 'ctrl123',
                'first_name': 'Carlos',
                'last_name': 'Controle',
                'email': 'controle@aprender.local',
                'cpf': '44444444444',
                'groups': ['controle'],
            },
        ]
        
        created_count = 0
        for user_data in test_users_data:
            if not self.dry_run:
                try:
                    # Verificar se já existe
                    if Usuario.objects.filter(username=user_data['username']).exists():
                        continue
                    
                    # Obter setor padrão
                    setor = Setor.objects.filter(nome='Superintendência').first()
                    
                    # Criar usuário
                    usuario = Usuario.objects.create(
                        username=user_data['username'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        email=user_data['email'],
                        cpf=user_data['cpf'],
                        telefone='85 99999-9999',
                        setor=setor,
                        is_active=True,
                        is_staff=user_data.get('is_staff', False),
                        is_superuser=user_data.get('is_superuser', False),
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
                                self.style.WARNING(f"Grupo nao encontrado: {group_name}")
                            )
                    
                    # Criar formador se necessário
                    if 'formador' in user_data['groups']:
                        Formador.objects.get_or_create(
                            usuario=usuario,
                            defaults={
                                'nome': usuario.get_full_name(),
                                'email': usuario.email,
                                'ativo': True,
                            }
                        )
                    
                    created_count += 1
                    self.stdout.write(f"  Usuario de teste criado: {user_data['username']}")
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Erro ao criar usuario {user_data['username']}: {str(e)}")
                    )
            else:
                created_count += 1  # Simular para dry-run
        
        self.stdout.write(f"Usuarios de teste criados: {created_count}")

    def _find_header_index(self, headers, search_header):
        """Encontra o índice de um cabeçalho na lista"""
        for i, header in enumerate(headers):
            if header and search_header.lower() in header.lower():
                return i
        return -1

    def _get_cell_value(self, row_data, index, default=''):
        """Obtém valor de uma célula com tratamento de índice inválido"""
        if index == -1 or index >= len(row_data):
            return default
        return str(row_data[index]) if row_data[index] is not None else default

    def _map_gerencia_to_setor(self, gerencia):
        """Mapeia gerência para setor"""
        mapeamento = {
            'superintendência': 'Superintendência',
            'acerta': 'ACerta',
            'vidas': 'Vidas',
            'vidas m': 'Vidas M',
            'brincando': 'Brincando e Aprendendo',
            'ideb10': 'IDEB10',
            'outros': 'Outros',
        }
        
        gerencia_lower = gerencia.lower().strip()
        for key, setor_name in mapeamento.items():
            if key in gerencia_lower:
                try:
                    return Setor.objects.get(nome=setor_name)
                except Setor.DoesNotExist:
                    pass
        
        # Setor padrão
        return Setor.objects.filter(nome='Outros').first()

    def _map_cargo_to_grupo(self, cargo):
        """Mapeia cargo para grupo Django"""
        cargo_lower = cargo.lower().strip()
        
        if 'formador' in cargo_lower:
            return 'formador'
        elif 'coordenador' in cargo_lower:
            return 'coordenador'
        elif 'superintend' in cargo_lower:
            return 'superintendencia'
        elif 'diretor' in cargo_lower:
            return 'diretoria'
        elif 'controle' in cargo_lower:
            return 'controle'
        
        return 'formador'  # Padrão

    def _get_areas_atuacao_default(self, setor):
        """Obtém áreas de atuação padrão baseadas no setor"""
        if not setor:
            return 'Geral'
        
        mapeamento = {
            'ACerta': 'Matemática, Língua Portuguesa',
            'Vidas': 'Competências Socioemocionais, Projeto de Vida',
            'Vidas M': 'Competências Socioemocionais, Projeto de Vida',
            'Brincando e Aprendendo': 'Educação Infantil, Ludicidade',
            'IDEB10': 'Avaliações, Indicadores Educacionais',
            'Superintendência': 'Gestão, Coordenação, Todas as áreas',
        }
        
        return mapeamento.get(setor.nome, 'Geral')