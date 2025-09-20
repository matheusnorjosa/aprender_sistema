"""
Comando para validar código após mudança estrutural Usuario único.
Verifica compatibilidade e identifica arquivos que precisam ser atualizados.
"""

import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings


class Command(BaseCommand):
    help = 'Valida código após mudança estrutural Usuario único (Formador → Usuario)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Aplica correções automáticas quando possível'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas'
        )

    def handle(self, *args, **options):
        self.fix_mode = options['fix']
        self.verbose = options['verbose']

        self.stdout.write(f"\n🔍 VALIDAÇÃO DE ESTRUTURA USUARIO ÚNICO")
        if self.fix_mode:
            self.stdout.write(f"   Modo: CORREÇÃO AUTOMÁTICA ATIVADA")
        else:
            self.stdout.write(f"   Modo: APENAS VERIFICAÇÃO")

        # Estatísticas
        self.problemas_encontrados = {
            'imports_formador': [],
            'referencias_formador_objects': [],
            'relacionamentos_obsoletos': [],
            'forms_desatualizados': [],
            'views_incompativeis': [],
            'templates_obsoletos': [],
            'servicos_incompativeis': [],
            'testes_desatualizados': []
        }

        # Executar validações
        self._validar_modelos()
        self._validar_forms()
        self._validar_views()
        self._validar_servicos()
        self._validar_comandos_management()
        self._validar_templates()
        self._validar_testes()

        # Relatório final
        self._gerar_relatorio()

    def _validar_modelos(self):
        """Valida compatibilidade dos modelos"""
        self.stdout.write(f"\n📋 VALIDANDO MODELOS...")

        try:
            from core.models import Usuario, Formador

            # Verificar se Usuario tem campos de formador
            usuario_fields = [f.name for f in Usuario._meta.fields]
            required_formador_fields = [
                'formador_ativo', 'area_especializacao', 'anos_experiencia'
            ]

            missing_fields = []
            for field in required_formador_fields:
                if field not in usuario_fields:
                    missing_fields.append(field)

            if missing_fields:
                self.stdout.write(f"   ❌ Campos faltantes no Usuario: {missing_fields}")
                self.problemas_encontrados['relacionamentos_obsoletos'].append({
                    'arquivo': 'core/models.py',
                    'problema': f'Campos faltantes: {missing_fields}',
                    'tipo': 'modelo_incompleto'
                })
            else:
                self.stdout.write(f"   ✅ Usuario tem todos os campos de formador")

            # Verificar relacionamentos
            try:
                # Verificar se FormadoresSolicitacao aponta para Usuario
                from core.models import FormadoresSolicitacao
                if hasattr(FormadoresSolicitacao, 'usuario'):
                    self.stdout.write(f"   ✅ FormadoresSolicitacao.usuario existe")
                else:
                    self.stdout.write(f"   ❌ FormadoresSolicitacao.usuario não encontrado")

                # Verificar DisponibilidadeFormadores
                from core.models import DisponibilidadeFormadores
                if hasattr(DisponibilidadeFormadores, 'usuario'):
                    self.stdout.write(f"   ✅ DisponibilidadeFormadores.usuario existe")
                else:
                    self.stdout.write(f"   ❌ DisponibilidadeFormadores.usuario não encontrado")

            except ImportError as e:
                self.stdout.write(f"   ⚠️  Erro ao importar modelos: {e}")

        except Exception as e:
            self.stdout.write(f"   ❌ Erro na validação de modelos: {e}")

    def _validar_forms(self):
        """Valida formulários que usam Formador"""
        self.stdout.write(f"\n📝 VALIDANDO FORMULÁRIOS...")

        forms_file = Path('core/forms.py')
        if forms_file.exists():
            with open(forms_file, 'r', encoding='utf-8') as f:
                conteudo = f.read()

            problemas = []

            # Verificar import de Formador
            if 'from core.models import' in conteudo and 'Formador' in conteudo:
                problemas.append("Import de Formador ainda presente")

            # Verificar SolicitacaoForm
            if 'Formador.objects.filter' in conteudo:
                problemas.append("SolicitacaoForm usa Formador.objects.filter")

            # Verificar FormadorForm
            if 'class FormadorForm' in conteudo:
                problemas.append("FormadorForm ainda existe (pode ser removido)")

            if problemas:
                for problema in problemas:
                    self.stdout.write(f"   ❌ {problema}")
                self.problemas_encontrados['forms_desatualizados'].extend(problemas)

                if self.fix_mode:
                    self._corrigir_forms(forms_file, conteudo)
            else:
                self.stdout.write(f"   ✅ Formulários compatíveis")

    def _corrigir_forms(self, forms_file, conteudo):
        """Aplica correções no arquivo de formulários"""
        self.stdout.write(f"   🔧 Corrigindo forms.py...")

        # Corrigir SolicitacaoForm para usar Usuario
        conteudo_corrigido = re.sub(
            r'Formador\.objects\.filter\(ativo=True\)',
            'Usuario.objects.filter(formador_ativo=True)',
            conteudo
        )

        # Remover import de Formador se não for mais usado
        if 'FormadorForm' not in conteudo_corrigido:
            conteudo_corrigido = re.sub(
                r', Formador',
                '',
                conteudo_corrigido
            )

        with open(forms_file, 'w', encoding='utf-8') as f:
            f.write(conteudo_corrigido)

        self.stdout.write(f"   ✅ forms.py corrigido")

    def _validar_views(self):
        """Valida views que usam Formador"""
        self.stdout.write(f"\n👁️ VALIDANDO VIEWS...")

        views_dir = Path('core/views')
        problemas_views = []

        # Verificar todos os arquivos de views
        for view_file in views_dir.glob('*.py'):
            with open(view_file, 'r', encoding='utf-8') as f:
                conteudo = f.read()

            problemas_arquivo = []

            # Verificar imports problemáticos
            if 'from ..models import' in conteudo and 'Formador' in conteudo:
                problemas_arquivo.append("Import de Formador")

            # Verificar uso direto de Formador.objects
            if 'Formador.objects' in conteudo:
                problemas_arquivo.append("Uso de Formador.objects")

            # Verificar FormadorForm
            if 'FormadorForm' in conteudo:
                problemas_arquivo.append("Uso de FormadorForm")

            if problemas_arquivo:
                problemas_views.append({
                    'arquivo': str(view_file),
                    'problemas': problemas_arquivo
                })

        if problemas_views:
            for item in problemas_views:
                self.stdout.write(f"   ❌ {item['arquivo']}: {', '.join(item['problemas'])}")
            self.problemas_encontrados['views_incompativeis'].extend(problemas_views)
        else:
            self.stdout.write(f"   ✅ Views compatíveis")

    def _validar_servicos(self):
        """Valida services que usam Formador"""
        self.stdout.write(f"\n⚙️ VALIDANDO SERVIÇOS...")

        services_dir = Path('core/services')
        if not services_dir.exists():
            self.stdout.write(f"   ⚠️  Diretório de serviços não encontrado")
            return

        problemas_servicos = []

        for service_file in services_dir.glob('*.py'):
            with open(service_file, 'r', encoding='utf-8') as f:
                conteudo = f.read()

            problemas = []

            # Verificar imports de Formador
            if 'from core.models import' in conteudo and 'Formador' in conteudo:
                problemas.append("Import de Formador")

            # Verificar type hints com Formador
            if ': "Formador"' in conteudo or ': Formador' in conteudo:
                problemas.append("Type hints com Formador")

            # Verificar uso direto
            if 'Formador.objects' in conteudo:
                problemas.append("Uso de Formador.objects")

            if problemas:
                problemas_servicos.append({
                    'arquivo': str(service_file),
                    'problemas': problemas
                })

        if problemas_servicos:
            for item in problemas_servicos:
                self.stdout.write(f"   ❌ {item['arquivo']}: {', '.join(item['problemas'])}")
            self.problemas_encontrados['servicos_incompativeis'].extend(problemas_servicos)
        else:
            self.stdout.write(f"   ✅ Serviços compatíveis")

    def _validar_comandos_management(self):
        """Valida comandos de management que usam Formador"""
        self.stdout.write(f"\n⚡ VALIDANDO COMANDOS MANAGEMENT...")

        commands_dir = Path('core/management/commands')
        problemas_comandos = []

        for command_file in commands_dir.glob('*.py'):
            if command_file.name in ['__init__.py', 'migrate_formador_to_usuario.py']:
                continue

            with open(command_file, 'r', encoding='utf-8') as f:
                conteudo = f.read()

            problemas = []

            # Verificar imports de Formador
            if 'from core.models import' in conteudo and 'Formador' in conteudo:
                problemas.append("Import de Formador")

            # Verificar uso direto
            if 'Formador.objects' in conteudo:
                problemas.append("Uso de Formador.objects")

            if problemas:
                problemas_comandos.append({
                    'arquivo': str(command_file),
                    'problemas': problemas
                })

        if problemas_comandos:
            for item in problemas_comandos:
                self.stdout.write(f"   ❌ {item['arquivo']}: {', '.join(item['problemas'])}")
            self.problemas_encontrados['relacionamentos_obsoletos'].extend(problemas_comandos)
        else:
            self.stdout.write(f"   ✅ Comandos management compatíveis")

    def _validar_templates(self):
        """Valida templates que podem referenciar formador"""
        self.stdout.write(f"\n🎨 VALIDANDO TEMPLATES...")

        templates_dir = Path('core/templates')
        if not templates_dir.exists():
            self.stdout.write(f"   ⚠️  Diretório de templates não encontrado")
            return

        problemas_templates = []

        for template_file in templates_dir.rglob('*.html'):
            with open(template_file, 'r', encoding='utf-8') as f:
                conteudo = f.read()

            problemas = []

            # Verificar referências a formador (sem o atributo)
            if 'formador.' in conteudo and 'usuario.formador' not in conteudo:
                problemas.append("Referência direta a 'formador.'")

            # Verificar loops sobre formadores
            if 'for formador in' in conteudo:
                problemas.append("Loop 'for formador in'")

            if problemas:
                problemas_templates.append({
                    'arquivo': str(template_file),
                    'problemas': problemas
                })

        if problemas_templates:
            for item in problemas_templates:
                self.stdout.write(f"   ❌ {item['arquivo']}: {', '.join(item['problemas'])}")
            self.problemas_encontrados['templates_obsoletos'].extend(problemas_templates)
        else:
            self.stdout.write(f"   ✅ Templates compatíveis")

    def _validar_testes(self):
        """Valida testes que usam Formador"""
        self.stdout.write(f"\n🧪 VALIDANDO TESTES...")

        test_dirs = [Path('tests'), Path('core/tests')]
        problemas_testes = []

        for test_dir in test_dirs:
            if not test_dir.exists():
                continue

            for test_file in test_dir.rglob('test*.py'):
                with open(test_file, 'r', encoding='utf-8') as f:
                    conteudo = f.read()

                problemas = []

                # Verificar imports de Formador
                if 'from core.models import' in conteudo and 'Formador' in conteudo:
                    problemas.append("Import de Formador")

                # Verificar criação de instâncias
                if 'Formador.objects.create' in conteudo:
                    problemas.append("Criação de Formador")

                # Verificar assertions com formador
                if '.formador' in conteudo and 'usuario.formador' not in conteudo:
                    problemas.append("Assertions com .formador")

                if problemas:
                    problemas_testes.append({
                        'arquivo': str(test_file),
                        'problemas': problemas
                    })

        if problemas_testes:
            for item in problemas_testes:
                self.stdout.write(f"   ❌ {item['arquivo']}: {', '.join(item['problemas'])}")
            self.problemas_encontrados['testes_desatualizados'].extend(problemas_testes)
        else:
            self.stdout.write(f"   ✅ Testes compatíveis")

    def _gerar_relatorio(self):
        """Gera relatório final da validação"""
        self.stdout.write(f"\n📊 RELATÓRIO DE VALIDAÇÃO:")

        total_problemas = sum(len(problemas) for problemas in self.problemas_encontrados.values())

        if total_problemas == 0:
            self.stdout.write(self.style.SUCCESS("   ✅ SISTEMA TOTALMENTE COMPATÍVEL!"))
            self.stdout.write(f"   📋 Estrutura Usuario único está funcionando corretamente")
        else:
            self.stdout.write(f"   ⚠️  {total_problemas} problema(s) encontrado(s)")

            for categoria, problemas in self.problemas_encontrados.items():
                if problemas:
                    self.stdout.write(f"\n   📂 {categoria.upper().replace('_', ' ')}:")
                    for problema in problemas[:5]:  # Mostrar primeiros 5
                        if isinstance(problema, dict):
                            arquivo = problema.get('arquivo', 'Desconhecido')
                            detalhes = problema.get('problemas', problema.get('problema', 'Sem detalhes'))
                            self.stdout.write(f"      • {arquivo}: {detalhes}")
                        else:
                            self.stdout.write(f"      • {problema}")

                    if len(problemas) > 5:
                        self.stdout.write(f"      ... e mais {len(problemas) - 5} problema(s)")

        # Próximos passos
        self.stdout.write(f"\n🎯 PRÓXIMOS PASSOS RECOMENDADOS:")

        if self.problemas_encontrados['forms_desatualizados']:
            self.stdout.write(f"   1. Atualizar core/forms.py para usar Usuario ao invés de Formador")

        if self.problemas_encontrados['views_incompativeis']:
            self.stdout.write(f"   2. Atualizar views para usar Usuario.objects.filter(formador_ativo=True)")

        if self.problemas_encontrados['servicos_incompativeis']:
            self.stdout.write(f"   3. Atualizar serviços para usar Usuario como tipo")

        if self.problemas_encontrados['relacionamentos_obsoletos']:
            self.stdout.write(f"   4. Executar comando migrate_formador_to_usuario.py")

        if self.problemas_encontrados['testes_desatualizados']:
            self.stdout.write(f"   5. Atualizar testes para nova estrutura")

        if total_problemas == 0:
            self.stdout.write(f"   🎉 Sistema pronto para uso com Usuario único!")
        else:
            self.stdout.write(f"   📝 Considere executar com --fix para correções automáticas")

        # Comandos úteis
        self.stdout.write(f"\n🔧 COMANDOS ÚTEIS:")
        self.stdout.write(f"   python manage.py migrate_formador_to_usuario --dry-run")
        self.stdout.write(f"   python manage.py mapear_usuarios_unicos --dry-run")
        self.stdout.write(f"   python manage.py test core.tests")

        if self.fix_mode:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Correções automáticas aplicadas onde possível"))
        else:
            self.stdout.write(f"\n💡 Execute com --fix para aplicar correções automáticas")