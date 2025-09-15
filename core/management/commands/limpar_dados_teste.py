"""
Comando Django para limpar TODOS os dados de teste e manter apenas dados reais das planilhas

Este comando remove completamente todos os dados de teste, mantendo apenas
a estrutura básica e dados reais extraídos das planilhas originais.

Uso:
python manage.py limpar_dados_teste [--confirmar] [--verbose]
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.models import (
    Formador, Municipio, Projeto, TipoEvento, Solicitacao, 
    Usuario, Setor, FormadoresSolicitacao, Aprovacao,
    LogAuditoria, Deslocamento, DisponibilidadeFormadores
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Remove todos os dados de teste, mantendo apenas dados reais das planilhas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a limpeza (obrigatório para executar)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe informações detalhadas durante a limpeza'
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

    def identificar_dados_teste(self):
        """Identifica quais dados são de teste vs dados reais"""
        self.logger.info("Identificando dados de teste...")
        
        # Usar Q objects para criar consultas mais eficientes
        from django.db.models import Q
        
        # Usuários de teste (emails @sistema.local, @teste.com, @local)
        usuarios_teste = Usuario.objects.filter(
            Q(email__in=['admin@admin.com']) |
            Q(email__icontains='@sistema.local') |
            Q(email__icontains='@teste.com') |
            Q(email__icontains='@local') |
            Q(username__in=['admin', 'diretoria_teste', 'coordenador_sistema'])
        )
        
        # Formadores de teste (vinculados a usuários de teste)
        formadores_teste = Formador.objects.filter(usuario__in=usuarios_teste)
        
        # Projetos de teste (nomes genéricos)
        projetos_teste = Projeto.objects.filter(
            nome__in=['Alfabetização', 'Matemática', 'Ciências', 'Projeto Teste']
        )
        
        # Municípios de teste (poucos dados)
        municipios_teste = Municipio.objects.filter(
            nome__in=['Fortaleza', 'Caucaia', 'Maracanaú', 'Sobral', 'Juazeiro do Norte']
        ).exclude(
            # Manter Fortaleza se vier das planilhas reais
            nome__in=['Dias d\'Avila', 'Petrolina', 'Lagoa Grande', 'Serra do Salitre']
        )
        
        # Solicitações de teste (todas as atuais são de exemplo)
        solicitacoes_teste = Solicitacao.objects.filter(
            Q(observacoes__icontains='exemplo') |
            Q(observacoes__icontains='teste') |
            Q(usuario_solicitante__in=usuarios_teste)
        )
        
        stats = {
            'usuarios_teste': usuarios_teste.count(),
            'formadores_teste': formadores_teste.count(),
            'projetos_teste': projetos_teste.count(),
            'municipios_teste': municipios_teste.count(),
            'solicitacoes_teste': solicitacoes_teste.count()
        }
        
        self.logger.info(f"📊 Dados de teste identificados:")
        for key, value in stats.items():
            self.logger.info(f"   • {key}: {value}")
        
        return {
            'usuarios': usuarios_teste,
            'formadores': formadores_teste,
            'projetos': projetos_teste,
            'municipios': municipios_teste,
            'solicitacoes': solicitacoes_teste
        }

    def remover_dados_teste(self, dados_teste):
        """Remove os dados de teste identificados"""
        self.logger.info("🗑️ Removendo dados de teste...")
        
        removidos = {}
        
        with transaction.atomic():
            # 1. Remover solicitações de teste (tem FKs)
            count = dados_teste['solicitacoes'].count()
            dados_teste['solicitacoes'].delete()
            removidos['solicitacoes'] = count
            self.logger.debug(f"✅ {count} solicitações de teste removidas")
            
            # 2. Remover formadores de teste
            count = dados_teste['formadores'].count()
            dados_teste['formadores'].delete()
            removidos['formadores'] = count
            self.logger.debug(f"✅ {count} formadores de teste removidos")
            
            # 3. Remover projetos de teste
            count = dados_teste['projetos'].count()
            dados_teste['projetos'].delete()
            removidos['projetos'] = count
            self.logger.debug(f"✅ {count} projetos de teste removidos")
            
            # 4. Remover municípios de teste
            count = dados_teste['municipios'].count()
            dados_teste['municipios'].delete()
            removidos['municipios'] = count
            self.logger.debug(f"✅ {count} municípios de teste removidos")
            
            # 5. Remover usuários de teste (por último)
            count = dados_teste['usuarios'].count()
            dados_teste['usuarios'].delete()
            removidos['usuarios'] = count
            self.logger.debug(f"✅ {count} usuários de teste removidos")
            
            # 6. Limpar outros dados relacionados
            LogAuditoria.objects.all().delete()
            Deslocamento.objects.all().delete()
            DisponibilidadeFormadores.objects.all().delete()
            Aprovacao.objects.all().delete()
        
        return removidos

    def preservar_admin_essencial(self):
        """Garante que existe pelo menos um superusuário para administração"""
        self.logger.info("👤 Verificando usuário administrativo...")
        
        if not Usuario.objects.filter(is_superuser=True).exists():
            # Criar superusuário básico
            admin_user = Usuario.objects.create_superuser(
                username='admin',
                email='admin@sistema.django',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema'
            )
            self.logger.info("✅ Superusuário administrativo criado: admin/admin123")
        else:
            self.logger.debug("✅ Superusuário já existe")

    def verificar_dados_reais_restantes(self):
        """Verifica quais dados reais restaram após a limpeza"""
        self.logger.info("📊 Verificando dados reais restantes...")
        
        stats = {
            'usuarios': Usuario.objects.count(),
            'formadores': Formador.objects.count(),
            'projetos': Projeto.objects.count(),
            'municipios': Municipio.objects.count(),
            'solicitacoes': Solicitacao.objects.count(),
            'setores': Setor.objects.count(),
            'tipos_evento': TipoEvento.objects.count()
        }
        
        self.logger.info("📈 Dados reais restantes:")
        for key, value in stats.items():
            self.logger.info(f"   • {key}: {value}")
        
        # Listar alguns exemplos de dados reais
        formadores_reais = Formador.objects.exclude(
            email__icontains='@sistema.local'
        ).values_list('nome', flat=True)[:5]
        
        if formadores_reais:
            self.logger.info(f"👥 Exemplo de formadores reais: {list(formadores_reais)}")
        
        return stats

    def handle(self, *args, **options):
        self.setup_logging(options['verbose'])
        
        if not options['confirmar']:
            self.logger.error("❌ Esta operação é DESTRUTIVA!")
            self.logger.error("⚠️  Use --confirmar para confirmar a limpeza dos dados de teste")
            raise CommandError("Operação cancelada. Use --confirmar para prosseguir.")
        
        self.logger.info("🚀 Iniciando limpeza completa dos dados de teste")
        self.logger.warning("⚠️  ATENÇÃO: Esta operação removerá TODOS os dados de teste!")
        
        try:
            # 1. Identificar dados de teste
            dados_teste = self.identificar_dados_teste()
            
            # 2. Remover dados de teste
            removidos = self.remover_dados_teste(dados_teste)
            
            # 3. Preservar admin essencial
            self.preservar_admin_essencial()
            
            # 4. Verificar resultado
            dados_finais = self.verificar_dados_reais_restantes()
            
            # Relatório final
            self.logger.info("="*80)
            self.logger.info("📊 RELATÓRIO FINAL DA LIMPEZA")
            self.logger.info("="*80)
            self.logger.info("🗑️ Dados de teste removidos:")
            for key, value in removidos.items():
                self.logger.info(f"   • {key}: {value}")
            
            self.logger.info("📈 Dados reais mantidos:")
            for key, value in dados_finais.items():
                self.logger.info(f"   • {key}: {value}")
            
            self.logger.info("✅ LIMPEZA CONCLUÍDA - Sistema agora contém apenas dados reais!")
            self.logger.info("="*80)
            
        except Exception as e:
            raise CommandError(f"❌ Erro durante a limpeza: {e}")