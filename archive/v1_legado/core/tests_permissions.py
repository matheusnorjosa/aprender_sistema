# core/tests_permissions.py
"""
Testes específicos para o sistema de grupos e permissões Django
implementado para substituir as checagens baseadas em user.papel
"""

from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Aprovacao,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


class GroupsAndPermissionsSetupTest(TestCase):
    """Testa se a migration de grupos e permissões foi executada corretamente"""

    def test_groups_exist(self):
        """Testa se todos os grupos foram criados"""
        expected_groups = [
            "superintendencia",
            "coordenador",
            "formador",
            "controle",
            "diretoria",
            "admin",
        ]

        for group_name in expected_groups:
            with self.subTest(group=group_name):
                self.assertTrue(
                    Group.objects.filter(name=group_name).exists(),
                    f"Grupo '{group_name}' não foi criado",
                )

    def test_custom_permissions_exist(self):
        """Testa se as permissões customizadas foram criadas"""
        # Verificar permissão sync_calendar
        self.assertTrue(
            Permission.objects.filter(codename="sync_calendar").exists(),
            "Permissão 'sync_calendar' não foi criada",
        )

        # Verificar permissão view_relatorios
        self.assertTrue(
            Permission.objects.filter(codename="view_relatorios").exists(),
            "Permissão 'view_relatorios' não foi criada",
        )

    def test_group_permissions_assignment(self):
        """Testa se as permissões foram corretamente associadas aos grupos"""
        # Superintendência
        superintendencia = Group.objects.get(name="superintendencia")
        perm_codes = list(
            superintendencia.permissions.values_list("codename", flat=True)
        )
        expected_perms = [
            "view_solicitacao",
            "change_solicitacao",
            "view_aprovacao",
            "add_aprovacao",
            "view_logauditoria",
        ]

        for perm in expected_perms:
            with self.subTest(group="superintendencia", permission=perm):
                self.assertIn(
                    perm, perm_codes, f"Superintendência deveria ter permissão '{perm}'"
                )

        # Coordenador
        coordenador = Group.objects.get(name="coordenador")
        perm_codes = list(coordenador.permissions.values_list("codename", flat=True))
        expected_perms = ["add_solicitacao", "view_solicitacao"]

        for perm in expected_perms:
            with self.subTest(group="coordenador", permission=perm):
                self.assertIn(
                    perm, perm_codes, f"Coordenador deveria ter permissão '{perm}'"
                )

        # Controle
        controle = Group.objects.get(name="controle")
        perm_codes = list(controle.permissions.values_list("codename", flat=True))
        self.assertIn(
            "sync_calendar",
            perm_codes,
            "Controle deveria ter permissão 'sync_calendar'",
        )

        # Diretoria
        diretoria = Group.objects.get(name="diretoria")
        perm_codes = list(diretoria.permissions.values_list("codename", flat=True))
        self.assertIn(
            "view_relatorios",
            perm_codes,
            "Diretoria deveria ter permissão 'view_relatorios'",
        )


class UserGroupSyncTest(TestCase):
    """Testa se o signal de sincronização usuário <-> grupo funciona"""

    def setUp(self):
        # Garantir que os grupos existem
        Group.objects.get_or_create(name="coordenador")
        Group.objects.get_or_create(name="formador")
        Group.objects.get_or_create(name="superintendencia")
        Group.objects.get_or_create(name="controle")
        Group.objects.get_or_create(name="diretoria")
        Group.objects.get_or_create(name="admin")

    def test_user_automatically_assigned_to_group_on_creation(self):
        """Testa se usuário é automaticamente adicionado ao grupo correto ao ser criado"""
        user = Usuario.objects.create_user(
            username="test_coordenador",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # Verificar se foi adicionado ao grupo correto
        self.assertTrue(user.groups.filter(name="coordenador").exists())

        # Verificar se não está em outros grupos
        other_groups = user.groups.exclude(name="coordenador").count()
        self.assertEqual(other_groups, 0)

    def test_user_group_updated_when_papel_changes(self):
        """Testa se o grupo é atualizado quando o papel do usuário muda"""
        user = Usuario.objects.create_user(
            username="test_user",
            email="user@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # Confirmar grupo inicial
        self.assertTrue(user.groups.filter(name="coordenador").exists())

        # Mudar papel e salvar
        user.papel = "formador"
        user.save()

        # Verificar nova associação
        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name="formador").exists())
        self.assertFalse(user.groups.filter(name="coordenador").exists())

    def test_user_with_invalid_papel_not_assigned_to_group(self):
        """Testa que usuários com papel inválido não são adicionados a grupos"""
        user = Usuario.objects.create_user(
            username="test_invalid",
            email="invalid@test.com",
            password="testpass123",
            papel="papel_inexistente",
        )

        # Não deve estar em nenhum grupo de papel
        role_groups = [
            "coordenador",
            "formador",
            "superintendencia",
            "controle",
            "diretoria",
            "admin",
        ]
        for group_name in role_groups:
            self.assertFalse(
                user.groups.filter(name=group_name).exists(),
                f"Usuário com papel inválido não deveria estar no grupo '{group_name}'",
            )


class PermissionBasedViewsTest(TestCase):
    """Testa se as views estão respeitando o sistema de permissões"""

    def setUp(self):
        self.client = Client()

        # Criar grupos necessários
        self.coord_group = Group.objects.get_or_create(name="coordenador")[0]
        self.super_group = Group.objects.get_or_create(name="superintendencia")[0]
        self.form_group = Group.objects.get_or_create(name="formador")[0]
        self.contr_group = Group.objects.get_or_create(name="controle")[0]
        self.diret_group = Group.objects.get_or_create(name="diretoria")[0]

        # Adicionar permissões aos grupos
        # Coordenador
        coord_perms = Permission.objects.filter(
            codename__in=["add_solicitacao", "view_solicitacao"]
        )
        self.coord_group.permissions.set(coord_perms)

        # Superintendência
        super_perms = Permission.objects.filter(
            codename__in=["view_aprovacao", "add_aprovacao", "view_solicitacao"]
        )
        self.super_group.permissions.set(super_perms)

        # Formador
        form_perms = Permission.objects.filter(
            codename__in=["add_disponibilidadeformadores", "view_solicitacao"]
        )
        self.form_group.permissions.set(form_perms)

        # Controle - precisa da permissão customizada
        sync_perm = Permission.objects.filter(codename="sync_calendar").first()
        if sync_perm:
            self.contr_group.permissions.add(sync_perm)

        # Diretoria - precisa da permissão customizada
        relat_perm = Permission.objects.filter(codename="view_relatorios").first()
        if relat_perm:
            self.diret_group.permissions.add(relat_perm)

        # Criar usuários
        self.coordenador = Usuario.objects.create_user(
            username="coordenador_perm",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )
        self.coordenador.groups.add(self.coord_group)

        self.superintendencia = Usuario.objects.create_user(
            username="super_perm",
            email="super@test.com",
            password="testpass123",
            papel="superintendencia",
        )
        self.superintendencia.groups.add(self.super_group)

        self.formador = Usuario.objects.create_user(
            username="formador_perm",
            email="formador@test.com",
            password="testpass123",
            papel="formador",
        )
        self.formador.groups.add(self.form_group)

        self.controle = Usuario.objects.create_user(
            username="controle_perm",
            email="controle@test.com",
            password="testpass123",
            papel="controle",
        )
        self.controle.groups.add(self.contr_group)

        self.diretoria = Usuario.objects.create_user(
            username="diretoria_perm",
            email="diretoria@test.com",
            password="testpass123",
            papel="diretoria",
        )
        self.diretoria.groups.add(self.diret_group)

        # Criar dados de teste
        self.projeto = Projeto.objects.create(nome="Projeto Teste")
        self.municipio = Municipio.objects.create(nome="São Paulo", uf="SP")
        self.tipo_evento = TipoEvento.objects.create(nome="Workshop")

    def test_solicitacao_create_requires_add_solicitacao_permission(self):
        """Testa se a criação de solicitação requer permissão add_solicitacao"""
        url = reverse("core:solicitar_evento")

        # Coordenador deve conseguir acessar
        self.client.login(username="coordenador_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Superintendência NÃO deve conseguir acessar (não tem add_solicitacao)
        self.client.login(username="super_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_aprovacoes_requires_view_aprovacao_permission(self):
        """Testa se aprovações requer permissão view_aprovacao"""
        url = reverse("core:aprovacoes_pendentes")

        # Superintendência deve conseguir acessar
        self.client.login(username="super_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Coordenador NÃO deve conseguir acessar
        self.client.login(username="coordenador_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Formador NÃO deve conseguir acessar
        self.client.login(username="formador_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueio_requires_add_disponibilidade_permission(self):
        """Testa se bloqueio de agenda requer permissão add_disponibilidadeformadores"""
        url = reverse("core:bloqueio_novo")

        # Formador deve conseguir acessar
        self.client.login(username="formador_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Coordenador NÃO deve conseguir acessar
        self.client.login(username="coordenador_perm", password="testpass123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_controle_views_require_sync_calendar_permission(self):
        """Testa se views do controle requerem permissão sync_calendar"""
        urls = [
            "core:controle_google_calendar",
            "core:controle_api_status",
        ]

        for url_name in urls:
            with self.subTest(url=url_name):
                url = reverse(url_name)

                # Controle deve conseguir acessar
                self.client.login(username="controle_perm", password="testpass123")
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                # Coordenador NÃO deve conseguir acessar
                self.client.login(username="coordenador_perm", password="testpass123")
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_diretoria_views_require_view_relatorios_permission(self):
        """Testa se views da diretoria requerem permissão view_relatorios"""
        urls = [
            "core:diretoria_dashboard",
            "core:diretoria_relatorios",
            "core:diretoria_api_metrics",
        ]

        for url_name in urls:
            with self.subTest(url=url_name):
                url = reverse(url_name)

                # Diretoria deve conseguir acessar
                self.client.login(username="diretoria_perm", password="testpass123")
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                # Coordenador NÃO deve conseguir acessar
                self.client.login(username="coordenador_perm", password="testpass123")
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)


class TemplatePermissionsTest(TestCase):
    """Testa se os templates estão usando corretamente o sistema de permissões"""

    def setUp(self):
        self.client = Client()

        # Criar grupos e permissões
        self.coord_group = Group.objects.get_or_create(name="coordenador")[0]
        coord_perms = Permission.objects.filter(
            codename__in=["add_solicitacao", "view_solicitacao"]
        )
        self.coord_group.permissions.set(coord_perms)

        self.form_group = Group.objects.get_or_create(name="formador")[0]
        form_perms = Permission.objects.filter(
            codename__in=["add_disponibilidadeformadores"]
        )
        self.form_group.permissions.set(form_perms)

        # Criar usuários
        self.coordenador = Usuario.objects.create_user(
            username="coord_template",
            email="coord@test.com",
            password="testpass123",
            papel="coordenador",
        )
        self.coordenador.groups.add(self.coord_group)

        self.formador = Usuario.objects.create_user(
            username="form_template",
            email="form@test.com",
            password="testpass123",
            papel="formador",
        )
        self.formador.groups.add(self.form_group)

    def test_coordenador_sees_coordination_menu(self):
        """Testa se coordenador vê menu de coordenação baseado em permissões"""
        self.client.login(username="coord_template", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seção de coordenação
        self.assertContains(response, "Coordenação")
        self.assertContains(response, "Solicitar Evento")
        self.assertContains(response, "Meus Eventos")

        # NÃO deve ver seções de outros perfis baseadas em outras permissões
        self.assertNotContains(response, "Monitor Google Calendar")

    def test_formador_sees_formador_menu(self):
        """Testa se formador vê menu específico baseado em permissões"""
        self.client.login(username="form_template", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # Deve ver seção de formador
        self.assertContains(response, "Formador")
        self.assertContains(response, "Bloqueio de Agenda")

        # NÃO deve ver funcionalidades de coordenador
        self.assertNotContains(response, "Solicitar Evento")
        self.assertNotContains(response, "Coordenação")

    def test_user_without_permissions_sees_no_restricted_content(self):
        """Testa que usuário sem permissões não vê conteúdo restrito"""
        # Criar usuário sem grupos/permissões
        user_no_perms = Usuario.objects.create_user(
            username="no_perms", email="no@test.com", password="testpass123"
        )

        self.client.login(username="no_perms", password="testpass123")
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)

        # NÃO deve ver nenhuma seção específica de perfil
        self.assertNotContains(response, "Coordenação")
        self.assertNotContains(response, "Formador")
        self.assertNotContains(response, "Superintendência")
        self.assertNotContains(response, "Controle")
        self.assertNotContains(response, "Diretoria")


class PermissionMigrationIntegrityTest(TestCase):
    """Testa integridade da migração e consistência do sistema"""

    def test_all_views_using_permission_system(self):
        """Verifica se views críticas estão usando PermissionRequiredMixin"""
        from core.views import (
            AprovacaoDetailView,
            AprovacoesPendentesView,
            BloqueioCreateView,
            DiretoriaExecutiveDashboardView,
            GoogleCalendarMonitorView,
            SolicitacaoCreateView,
        )

        # Verificar se as views têm permission_required definido
        self.assertTrue(hasattr(SolicitacaoCreateView, "permission_required"))
        self.assertTrue(hasattr(AprovacoesPendentesView, "permission_required"))
        self.assertTrue(hasattr(AprovacaoDetailView, "permission_required"))
        self.assertTrue(hasattr(BloqueioCreateView, "permission_required"))
        self.assertTrue(hasattr(GoogleCalendarMonitorView, "permission_required"))
        self.assertTrue(hasattr(DiretoriaExecutiveDashboardView, "permission_required"))

    def test_superuser_bypass_works(self):
        """Testa se superuser ainda consegue acessar tudo"""
        admin = Usuario.objects.create_superuser(
            username="admin_test", email="admin@test.com", password="testpass123"
        )

        self.client.login(username="admin_test", password="testpass123")

        # Deve conseguir acessar todas as views principais
        urls_to_test = [
            "core:home",
            "core:solicitar_evento",
            "core:aprovacoes_pendentes",
            "core:bloqueio_novo",
        ]

        for url_name in urls_to_test:
            with self.subTest(url=url_name):
                url = reverse(url_name)
                response = self.client.get(url)
                self.assertIn(
                    response.status_code, [200, 302]
                )  # 200 OK ou 302 redirect válido

    def test_backward_compatibility_papel_field_still_works(self):
        """Testa se o campo papel ainda funciona durante a transição"""
        user = Usuario.objects.create_user(
            username="compat_test",
            email="compat@test.com",
            password="testpass123",
            papel="coordenador",
        )

        # O campo papel ainda deve estar acessível
        self.assertEqual(user.papel, "coordenador")

        # E o usuário deve estar no grupo correto (via signal)
        self.assertTrue(user.groups.filter(name="coordenador").exists())
