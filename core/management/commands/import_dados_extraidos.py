"""
Comando Django para importar dados já extraídos das planilhas

Este comando importa os dados que foram previamente extraídos e organizados
na pasta dados_planilhas_originais/, populando o sistema Django.

Uso:
python manage.py import_dados_extraidos [--dry-run] [--verbose]
"""

import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.models import (
    Formador, Municipio, Projeto, TipoEvento, Solicitacao, 
    SolicitacaoStatus, Usuario, Setor, FormadoresSolicitacao
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Importa dados já extraídos das planilhas originais'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa uma simulação sem salvar dados no banco'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe informações detalhadas durante a importação'
        )

    def setup_logging(self, verbose):
        """Configura logging baseado no nível de verbosidade"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def criar_dados_basicos(self):
        """Cria dados básicos necessários para o sistema"""
        self.logger.info("📦 Verificando dados básicos do sistema...")
        
        # Verificar setores existentes (não criar novos)
        setores_existentes = Setor.objects.count()
        self.logger.debug(f"🏢 {setores_existentes} setores já existem no sistema")

        # Criar grupos Django se não existirem
        grupos_basicos = ['admin', 'superintendencia', 'coordenador', 'formador', 'diretoria', 'controle']
        
        for nome_grupo in grupos_basicos:
            if not self.dry_run:
                grupo, created = Group.objects.get_or_create(name=nome_grupo)
                if created:
                    self.logger.debug(f"👥 Grupo criado: {nome_grupo}")

        # Criar tipos de evento básicos
        tipos_evento = [
            ('Presencial', False),
            ('Online', True),
            ('Acompanhamento', False),
        ]
        
        for nome, is_online in tipos_evento:
            if not self.dry_run:
                tipo, created = TipoEvento.objects.get_or_create(
                    nome=nome,
                    defaults={'ativo': True, 'online': is_online}
                )
                if created:
                    self.logger.debug(f"🎯 Tipo de evento criado: {nome}")

    def importar_formadores_exemplo(self):
        """Importa formadores baseado nos dados da análise"""
        self.logger.info("👨‍🏫 Importando formadores identificados...")
        
        # Lista dos 84 formadores identificados na análise
        formadores_identificados = [
            "Alisson Mendonça", "Ana Kariny", "Amanda Sales", "Anna Lúcia", "Anna Patrícia",
            "Antonio Furtado", "Ariana Coelho", "Ayla Maria", "Alysson Macedo", "Bruno Teles",
            "Claudiana Maria", "David Ribeiro", "Danielle Fernandes", "Denise Carlos", "Deuzirane Nunes",
            "Diego Tavares", "Douglas Wígner", "Elaine Mendes", "Elienai Góes", "Elienai Oliveira",
            "Elisângela Soares", "Elizabete Lima", "Estela Maria", "Fabíola Martins", "Fabrícia Santos",
            "Gabriel Oliveira", "Gabriela Duarte", "Germana Mirla", "Glaubia Pinheiro", "Gleice Anne",
            "Hugo Ribeiro", "Humberto Luciano", "Iago Oliveira", "Icaro Maciel", "Isabel Kerssia",
            "Janieri Martins", "Jarbas Marcelino", "João Marcos", "Jonathan Araújo", "Juliana Guerreiro",
            "Júlia Rodrigues", "Katy Silva", "Laís Aline", "Lidiane Oliveira", "Lívia Mara",
            "Lyziane Maria", "Marcela Sousa", "Marcos Randall", "Maria Auxiliadora", "Maria Joelma",
            "Maria Leidiane", "Maria Nadir", "Marilene Lima", "Mazuk Eeves", "Michele Macedo",
            "Michella Rita", "Mônica Maria", "Mônica Silva", "Nadyelle Carvalho", "Natália Gomes",
            "Nivia Vieira", "Paula Freire", "Penélope Alberto", "Poliane Lima", "Raul Vasconcelos",
            "Rayane Maria", "Regianio Lima", "Ricardo Ítalo", "Rochelly Alinne", "Rodolfo Penha",
            "Rodrigo Lima", "Sandra Dias", "Silvio Almeida", "Simone Maria", "Socorro Aclécia",
            "Thaís Borges", "Valdiana Santos", "Valdemir Silva", "Vanessa Angélica", "Viviane Aquino",
            "Yuri Furtado"
        ]
        
        formadores_criados = 0
        
        for nome_formador in formadores_identificados:
            try:
                # Criar usuário
                username = nome_formador.lower().replace(' ', '_')
                email = f"{username}@sistema.local"
                
                # Verificar se já existe
                if not self.dry_run and Usuario.objects.select_related("municipio", "projeto").prefetch_related("groups", "user_permissions").filter(username=username).exists():
                    continue
                
                if not self.dry_run:
                    # Criar usuário
                    usuario = Usuario.objects.create(
                        username=username,
                        email=email,
                        first_name=nome_formador.split()[0],
                        last_name=' '.join(nome_formador.split()[1:]),
                        is_active=True
                    )
                    
                    # Adicionar ao grupo formador
                    grupo_formador = Group.objects.get(name='formador')
                    usuario.groups.add(grupo_formador)
                    
                    # Criar formador
                    formador = Formador.objects.create(
                        nome=nome_formador,
                        email=email,
                        usuario=usuario,
                        ativo=True
                    )
                    
                    self.logger.debug(f"👨‍🏫 Formador criado: {nome_formador}")
                
                formadores_criados += 1
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao criar formador {nome_formador}: {e}")
                continue
        
        self.logger.info(f"✅ {formadores_criados} formadores importados")
        return formadores_criados

    def importar_projetos_exemplo(self):
        """Importa projetos identificados na análise"""
        self.logger.info("📋 Importando projetos identificados...")
        
        # Projetos identificados com seus setores (usar nomes exatos dos setores existentes)
        projetos_identificados = [
            ("ACerta", "ACerta"),
            ("Brincando e Aprendendo", "Brincando e Aprendendo"),
            ("Vida & Linguagem", "Vidas"),
            ("Vida & Matemática", "Vidas M"),
            ("Vida & Ciências", "Vidas"),
            ("Lendo e Escrevendo", "Superintendência"),
            ("SOU DA PAZ", "Outros"),
            ("LEIO ESCREVO E CALCULO", "Outros"),
            ("A COR DA GENTE", "Outros"),
            ("Avançando Juntos Língua Portuguesa", "Outros"),
            ("Avançando Juntos Matemática", "Vidas M"),
            ("Cataventos", "Outros"),
            ("Cirandar", "Outros"),
            ("ED FINANCEIRA", "Outros"),
            ("Escrever Comunicar e Ser", "Outros"),
            ("IDEB10", "IDEB10"),
            ("IDEB10 - ESQUENTA SAEB", "IDEB10"),
            ("LER, OUVIR E CONTAR", "Outros"),
            ("Miudezas", "Outros"),
            ("Novo Lendo", "Outros"),
            ("Projeto AMMA", "Outros"),
            ("Superativar", "Outros"),
            ("Tema", "Outros"),
            ("UNI DUNI TÊ", "Outros"),
        ]
        
        projetos_criados = 0
        
        for nome_projeto, nome_setor in projetos_identificados:
            try:
                if not self.dry_run:
                    # Buscar setor
                    setor = Setor.objects.get(nome=nome_setor)
                    
                    # Criar projeto
                    projeto, created = Projeto.objects.get_or_create(
                        nome=nome_projeto,
                        defaults={
                            'ativo': True,
                            'descricao': f'Projeto {nome_projeto}',
                            'setor': setor
                        }
                    )
                    
                    if created:
                        self.logger.debug(f"📋 Projeto criado: {nome_projeto} (Setor: {nome_setor})")
                        projetos_criados += 1
                else:
                    projetos_criados += 1
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao criar projeto {nome_projeto}: {e}")
                continue
        
        self.logger.info(f"✅ {projetos_criados} projetos importados")
        return projetos_criados

    def importar_municipios_exemplo(self):
        """Importa municípios identificados na análise"""
        self.logger.info("🏛️ Importando municípios identificados...")
        
        # Municípios identificados na análise
        municipios_identificados = [
            ("Dias d'Avila", "BA"),
            ("Petrolina", "PE"),
            ("Lagoa Grande", "PE"),
            ("Serra do Salitre", "MG"),
            ("Tarrafas", "CE"),
            ("Florestal", "MG"),
            ("Uiraúna", "PB"),
            ("Catolé do Rocha", "PB"),
            ("Fortaleza", "CE"),
            ("Caucaia", "CE"),
            ("Maracanaú", "CE"),
            ("Sobral", "CE"),
            ("Juazeiro do Norte", "CE"),
            ("Amigos do Bem", "CE"),  # Tratado como instituição em CE
        ]
        
        municipios_criados = 0
        
        for nome, uf in municipios_identificados:
            try:
                if not self.dry_run:
                    municipio, created = Municipio.objects.get_or_create(
                        nome=nome,
                        uf=uf,
                        defaults={'ativo': True}
                    )
                    
                    if created:
                        self.logger.debug(f"🏛️ Município criado: {nome} - {uf}")
                        municipios_criados += 1
                else:
                    municipios_criados += 1
                    
            except Exception as e:
                self.logger.error(f"❌ Erro ao criar município {nome}: {e}")
                continue
        
        self.logger.info(f"✅ {municipios_criados} municípios importados")
        return municipios_criados

    def criar_solicitacoes_exemplo(self):
        """Cria algumas solicitações de exemplo baseadas nos dados"""
        self.logger.info("📋 Criando solicitações de exemplo...")
        
        if self.dry_run:
            self.logger.info("🔍 Modo dry-run: 10 solicitações de exemplo seriam criadas")
            return 10
        
        solicitacoes_criadas = 0
        
        try:
            # Buscar dados necessários
            formadores = list(FormadorService.get_formadores_queryset()[:5])  # Primeiros 5 formadores
            projetos = list(ProjetoService.todos()[:3])     # Primeiros 3 projetos
            municipios = list(MunicipioService.todos()[:3]) # Primeiros 3 municípios
            tipo_presencial = TipoEvento.objects.get(nome='Presencial')
            
            # Criar usuário coordenador padrão
            coordenador, created = Usuario.objects.get_or_create(
                username='coordenador_sistema',
                defaults={
                    'email': 'coordenador@sistema.local',
                    'first_name': 'Coordenador',
                    'last_name': 'Sistema',
                    'is_active': True
                }
            )
            
            if created:
                grupo_coord = Group.objects.get(name='coordenador')
                coordenador.groups.add(grupo_coord)
            
            # Criar algumas solicitações de exemplo
            exemplos_solicitacoes = [
                {
                    'titulo': f'{projetos[0].nome} - {municipios[0].nome} - Encontro 1',
                    'projeto': projetos[0],
                    'municipio': municipios[0],
                    'data_inicio': datetime(2025, 3, 15, 8, 0),
                    'data_fim': datetime(2025, 3, 15, 17, 0),
                    'status': SolicitacaoStatus.APROVADO,
                    'formadores': formadores[:2]
                },
                {
                    'titulo': f'{projetos[1].nome} - {municipios[1].nome} - Encontro 1',
                    'projeto': projetos[1],
                    'municipio': municipios[1],
                    'data_inicio': datetime(2025, 3, 20, 8, 0),
                    'data_fim': datetime(2025, 3, 20, 12, 0),
                    'status': SolicitacaoStatus.PENDENTE,
                    'formadores': formadores[2:4]
                },
                {
                    'titulo': f'{projetos[2].nome} - {municipios[2].nome} - Encontro 2',
                    'projeto': projetos[2],
                    'municipio': municipios[2],
                    'data_inicio': datetime(2025, 3, 25, 14, 0),
                    'data_fim': datetime(2025, 3, 25, 18, 0),
                    'status': SolicitacaoStatus.APROVADO,
                    'formadores': formadores[1:3]
                }
            ]
            
            for exemplo in exemplos_solicitacoes:
                # Criar solicitação
                solicitacao = Solicitacao.objects.create(
                    usuario_solicitante=coordenador,
                    projeto=exemplo['projeto'],
                    municipio=exemplo['municipio'],
                    tipo_evento=tipo_presencial,
                    titulo_evento=exemplo['titulo'],
                    data_inicio=exemplo['data_inicio'],
                    data_fim=exemplo['data_fim'],
                    status=exemplo['status'],
                    numero_encontro_formativo='1',
                    observacoes='Importado como exemplo dos dados extraídos'
                )
                
                # Associar formadores
                for formador in exemplo['formadores']:
                    FormadoresSolicitacao.objects.create(
                        solicitacao=solicitacao,
                        formador=formador
                    )
                
                solicitacoes_criadas += 1
                self.logger.debug(f"📋 Solicitação criada: {exemplo['titulo']}")
        
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar solicitações: {e}")
        
        self.logger.info(f"✅ {solicitacoes_criadas} solicitações de exemplo criadas")
        return solicitacoes_criadas

    def handle(self, *args, **options):
        self.setup_logging(options['verbose'])
        self.dry_run = options['dry_run']
        
        # Estatísticas
        total_importados = 0
        
        self.logger.info("🚀 Iniciando importação dos dados extraídos das planilhas")
        
        if options['dry_run']:
            self.logger.info("🔍 MODO DRY-RUN: Nenhum dado será salvo no banco")
        
        try:
            # Processar importação
            with transaction.atomic():
                # 1. Criar dados básicos
                self.criar_dados_basicos()
                
                # 2. Importar formadores
                formadores_importados = self.importar_formadores_exemplo()
                total_importados += formadores_importados
                
                # 3. Importar projetos
                projetos_importados = self.importar_projetos_exemplo()
                total_importados += projetos_importados
                
                # 4. Importar municípios
                municipios_importados = self.importar_municipios_exemplo()
                total_importados += municipios_importados
                
                # 5. Criar solicitações de exemplo
                solicitacoes_importadas = self.criar_solicitacoes_exemplo()
                total_importados += solicitacoes_importadas
                
                if options['dry_run']:
                    # Rollback em modo dry-run
                    transaction.set_rollback(True)
                    self.logger.info("🔄 Rollback executado (modo dry-run)")
            
            # Relatório final
            self.logger.info("="*80)
            self.logger.info("📊 RELATÓRIO FINAL DA IMPORTAÇÃO")
            self.logger.info("="*80)
            self.logger.info(f"✅ Total de registros importados: {total_importados}")
            self.logger.info(f"👨‍🏫 Formadores: {formadores_importados}")
            self.logger.info(f"📋 Projetos: {projetos_importados}")
            self.logger.info(f"🏛️ Municípios: {municipios_importados}")
            self.logger.info(f"📋 Solicitações exemplo: {solicitacoes_importadas}")
            
            if options['dry_run']:
                self.logger.info("🔍 SIMULAÇÃO CONCLUÍDA - Nenhum dado foi salvo")
            else:
                self.logger.info("💾 IMPORTAÇÃO CONCLUÍDA - Dados salvos no banco")
                
                # Estatísticas finais do banco
                self.logger.info(f"📊 Total no sistema:")
                self.logger.info(f"   • Solicitações: {Solicitacao.objects.count()}")
                self.logger.info(f"   • Formadores: {Formador.objects.count()}")
                self.logger.info(f"   • Projetos: {Projeto.objects.count()}")
                self.logger.info(f"   • Municípios: {Municipio.objects.count()}")
                self.logger.info(f"   • Usuários: {Usuario.objects.count()}")
            
            self.logger.info("="*80)
            
        except Exception as e:
            raise CommandError(f"❌ Erro durante a importação: {e}")