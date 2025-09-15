"""
Comando Django para RESET COMPLETO do banco de dados PostgreSQL
Remove ABSOLUTAMENTE TODOS os dados, deixando apenas estrutura e admin essencial

ATENÇÃO: Este comando é EXTREMAMENTE DESTRUTIVO!
Remove todos os dados das planilhas importadas e dados de teste.

Uso:
python manage.py reset_database_completo --confirmar-reset-total --verbose
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from core.models import *

User = get_user_model()

class Command(BaseCommand):
    help = 'RESET COMPLETO do banco de dados - Remove TODOS os dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar-reset-total',
            action='store_true',
            help='Confirma o RESET TOTAL (obrigatório para executar)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe informações detalhadas durante o reset'
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

    def mostrar_estado_atual(self):
        """Mostra o estado atual do banco antes da limpeza"""
        self.logger.info("ESTADO ATUAL DO BANCO DE DADOS:")
        self.logger.info("=" * 50)
        
        try:
            self.logger.info(f"Usuarios: {User.objects.count()}")
            self.logger.info(f"Formadores: {Formador.objects.count()}")
            self.logger.info(f"Municipios: {Municipio.objects.count()}")
            self.logger.info(f"Projetos: {Projeto.objects.count()}")
            self.logger.info(f"Solicitacoes: {Solicitacao.objects.count()}")
            self.logger.info(f"TipoEvento: {TipoEvento.objects.count()}")
            self.logger.info(f"Setores: {Setor.objects.count()}")
            self.logger.info(f"Groups: {Group.objects.count()}")
            
            # Mostrar alguns exemplos de dados
            if Formador.objects.count() > 0:
                self.logger.info("Alguns formadores existentes:")
                for f in Formador.objects.all()[:3]:
                    self.logger.info(f"  - {f.nome} | {f.email}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao mostrar estado atual: {e}")
        
        self.logger.info("=" * 50)

    def reset_completo_tabelas(self):
        """Remove TODOS os dados de TODAS as tabelas"""
        self.logger.info("INICIANDO RESET COMPLETO DE TODAS AS TABELAS")
        self.logger.warning("Esta operação removerá TODOS os dados!")
        
        with transaction.atomic():
            # Lista de todas as tabelas de modelos na ordem correta (respeitando FKs)
            modelos_para_limpar = [
                # Primeiro, tabelas com relacionamentos
                ('FormadoresSolicitacao', FormadoresSolicitacao),
                ('Aprovacao', Aprovacao),
                ('LogAuditoria', LogAuditoria),
                ('DisponibilidadeFormadores', DisponibilidadeFormadores),
                ('Deslocamento', Deslocamento),
                ('Solicitacao', Solicitacao),
                
                # Depois, tabelas principais
                ('Formador', Formador),
                ('TipoEvento', TipoEvento),
                ('Projeto', Projeto),
                ('Municipio', Municipio),
                ('Setor', Setor),
                
                # Por último, usuários (mantendo apenas admin)
                ('Usuario (todos exceto admin)', User),
            ]
            
            for nome_tabela, modelo in modelos_para_limpar:
                try:
                    if modelo == User:
                        # Para usuários, manter apenas o admin
                        usuarios_removidos = User.objects.exclude(is_superuser=True).count()
                        User.objects.exclude(is_superuser=True).delete()
                        self.logger.info(f"  ✅ {nome_tabela}: {usuarios_removidos} removidos (admin mantido)")
                    else:
                        count = modelo.objects.count()
                        modelo.objects.all().delete()
                        self.logger.info(f"  ✅ {nome_tabela}: {count} registros removidos")
                        
                except Exception as e:
                    self.logger.error(f"  ❌ Erro limpando {nome_tabela}: {e}")
            
            # Limpar grupos Django (exceto os essenciais)
            grupos_essenciais = ['admin', 'diretoria', 'superintendencia', 'coordenador', 'formador', 'controle']
            grupos_removidos = Group.objects.exclude(name__in=grupos_essenciais).count()
            Group.objects.exclude(name__in=grupos_essenciais).delete()
            self.logger.info(f"  ✅ Groups extra: {grupos_removidos} removidos (essenciais mantidos)")

    def reset_sequencias(self):
        """Reset das sequências do PostgreSQL para começar do 1"""
        self.logger.info("Resetando sequências do PostgreSQL...")
        
        try:
            with connection.cursor() as cursor:
                # Obter todas as sequências
                cursor.execute("""
                    SELECT sequence_name FROM information_schema.sequences 
                    WHERE sequence_schema = 'public'
                """)
                sequencias = cursor.fetchall()
                
                for (seq_name,) in sequencias:
                    try:
                        cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
                        self.logger.debug(f"  ✅ Sequência {seq_name} resetada")
                    except Exception as e:
                        self.logger.warning(f"  ⚠️ Erro resetando {seq_name}: {e}")
                        
                self.logger.info(f"✅ {len(sequencias)} sequências resetadas")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Erro resetando sequências: {e}")

    def criar_admin_essencial(self):
        """Garante que existe pelo menos um superusuário"""
        self.logger.info("Verificando usuário administrativo...")
        
        admin_users = User.objects.filter(is_superuser=True)
        
        if admin_users.count() == 0:
            # Criar superusuário
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@sistema.limpo',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema'
            )
            self.logger.info("✅ Superusuário admin criado: admin/admin123")
        else:
            admin = admin_users.first()
            self.logger.info(f"✅ Superusuário existente mantido: {admin.username}")

    def verificar_estado_final(self):
        """Verifica o estado final após limpeza"""
        self.logger.info("VERIFICANDO ESTADO FINAL:")
        self.logger.info("=" * 50)
        
        try:
            usuarios = User.objects.count()
            formadores = Formador.objects.count()
            municipios = Municipio.objects.count()
            projetos = Projeto.objects.count()
            solicitacoes = Solicitacao.objects.count()
            tipos_evento = TipoEvento.objects.count()
            setores = Setor.objects.count()
            
            self.logger.info(f"Usuarios: {usuarios} (deve ser 1 - apenas admin)")
            self.logger.info(f"Formadores: {formadores} (deve ser 0)")
            self.logger.info(f"Municipios: {municipios} (deve ser 0)")  
            self.logger.info(f"Projetos: {projetos} (deve ser 0)")
            self.logger.info(f"Solicitacoes: {solicitacoes} (deve ser 0)")
            self.logger.info(f"TipoEvento: {tipos_evento} (deve ser 0)")
            self.logger.info(f"Setores: {setores} (deve ser 0)")
            
            # Verificar se apenas admin existe
            if usuarios == 1:
                admin = User.objects.first()
                self.logger.info(f"Único usuário: {admin.username} (superuser: {admin.is_superuser})")
            
            # Status final
            total_dados = formadores + municipios + projetos + solicitacoes + tipos_evento + setores
            
            if total_dados == 0 and usuarios == 1:
                self.logger.info("🎉 RESET COMPLETO REALIZADO COM SUCESSO!")
                self.logger.info("Sistema está completamente limpo e pronto para uso")
            else:
                self.logger.warning("⚠️ Sistema ainda contém alguns dados")
                
        except Exception as e:
            self.logger.error(f"Erro verificando estado final: {e}")
        
        self.logger.info("=" * 50)

    def handle(self, *args, **options):
        self.setup_logging(options['verbose'])
        
        if not options['confirmar_reset_total']:
            self.logger.error("❌ OPERAÇÃO CANCELADA!")
            self.logger.error("Esta operação removerá TODOS os dados do banco!")
            self.logger.error("Use --confirmar-reset-total para confirmar o reset completo")
            raise CommandError("Reset cancelado. Use --confirmar-reset-total para prosseguir.")
        
        self.logger.warning("🚨 INICIANDO RESET COMPLETO DO BANCO DE DADOS")
        self.logger.warning("Esta operação é IRREVERSÍVEL!")
        self.logger.warning("Todos os dados serão perdidos permanentemente!")
        
        try:
            # 1. Mostrar estado atual
            self.mostrar_estado_atual()
            
            # 2. Reset completo das tabelas
            self.reset_completo_tabelas()
            
            # 3. Reset das sequências
            self.reset_sequencias()
            
            # 4. Criar admin essencial
            self.criar_admin_essencial()
            
            # 5. Verificar estado final
            self.verificar_estado_final()
            
            self.logger.info("🎉 RESET COMPLETO CONCLUÍDO COM SUCESSO!")
            self.logger.info("O banco de dados está agora completamente limpo")
            self.logger.info("Pronto para importar dados reais das planilhas")
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante o reset: {e}")
            raise CommandError(f"Falha no reset completo: {e}")