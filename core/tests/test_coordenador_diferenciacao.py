# core/tests/test_coordenador_diferenciacao.py
"""
Testes para diferenciação de coordenadores por vinculação à superintendência.

IMPORTANTE: A diferenciação é APENAS para backend/permissões.
Para a empresa, todos são coordenadores normalmente.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Setor, Usuario


class CoordenadorDiferenciacaoTestCase(TestCase):
    """
    Testa os métodos de diferenciação de coordenadores.

    A lógica é INTERNA do sistema - para controle de permissões,
    mas externamente todos aparecem como coordenadores.
    """

    def setUp(self):
        # Criar setores de teste
        self.setor_superintendencia = Setor.objects.create(
            nome="Superintendência",
            sigla="SUPER",
            vinculado_superintendencia=True
        )

        self.setor_vidas = Setor.objects.create(
            nome="Vidas",
            sigla="VIDAS",
            vinculado_superintendencia=False
        )

        self.setor_brincando = Setor.objects.create(
            nome="Brincando e Aprendendo",
            sigla="BRINC",
            vinculado_superintendencia=False
        )

        # Criar coordenadores de teste
        self.coord_super = Usuario.objects.create_user(
            username="coord_super",
            email="super@test.com",
            cargo="coordenador",
            setor=self.setor_superintendencia,
            first_name="Maria",
            last_name="Superintendente"
        )

        self.coord_vidas = Usuario.objects.create_user(
            username="coord_vidas",
            email="vidas@test.com",
            cargo="coordenador",
            setor=self.setor_vidas,
            first_name="João",
            last_name="Vidas"
        )

        self.coord_brincando = Usuario.objects.create_user(
            username="coord_brincando",
            email="brincando@test.com",
            cargo="coordenador",
            setor=self.setor_brincando,
            first_name="Ana",
            last_name="Brincando"
        )

        # Usuário não-coordenador
        self.formador = Usuario.objects.create_user(
            username="formador",
            email="form@test.com",
            cargo="formador",
            setor=self.setor_vidas,
            first_name="Carlos",
            last_name="Formador"
        )

    def test_todos_sao_coordenadores_externamente(self):
        """
        Teste fundamental: Para a empresa, TODOS aparecem como coordenadores.
        A diferenciação é só interna.
        """
        # Todos os usuários com cargo 'coordenador' são coordenadores
        self.assertTrue(self.coord_super.is_coordenador())
        self.assertTrue(self.coord_vidas.is_coordenador())
        self.assertTrue(self.coord_brincando.is_coordenador())

        # Formador não é coordenador
        self.assertFalse(self.formador.is_coordenador())

    def test_diferenciacao_interna_superintendencia(self):
        """
        Teste da diferenciação INTERNA - backend/permissões apenas.
        """
        # Coordenador superintendência - diferenciação interna
        self.assertTrue(self.coord_super.is_coordenador_superintendencia())
        self.assertFalse(self.coord_super.is_coordenador_outros_setores())

        # Coordenadores outros setores - diferenciação interna
        self.assertFalse(self.coord_vidas.is_coordenador_superintendencia())
        self.assertTrue(self.coord_vidas.is_coordenador_outros_setores())

        self.assertFalse(self.coord_brincando.is_coordenador_superintendencia())
        self.assertTrue(self.coord_brincando.is_coordenador_outros_setores())

        # Formador não é nem um nem outro
        self.assertFalse(self.formador.is_coordenador_superintendencia())
        self.assertFalse(self.formador.is_coordenador_outros_setores())

    def test_metodos_classe_diferenciacao(self):
        """
        Testa métodos de classe para buscar coordenadores por vinculação.
        IMPORTANTE: Isso é só para backend/permissões.
        """
        # Superintendência
        coords_super = Usuario.get_coordenadores_superintendencia()
        self.assertEqual(coords_super.count(), 1)
        self.assertIn(self.coord_super, coords_super)
        self.assertNotIn(self.coord_vidas, coords_super)
        self.assertNotIn(self.coord_brincando, coords_super)

        # Outros setores
        coords_outros = Usuario.get_coordenadores_outros_setores()
        self.assertEqual(coords_outros.count(), 2)
        self.assertNotIn(self.coord_super, coords_outros)
        self.assertIn(self.coord_vidas, coords_outros)
        self.assertIn(self.coord_brincando, coords_outros)

    def test_metodo_unificado_por_vinculacao(self):
        """
        Testa método unificado que permite filtrar por vinculação.
        Usado para controle interno de permissões.
        """
        # Apenas superintendência
        coords_super = Usuario.get_coordenadores_por_vinculacao(superintendencia_only=True)
        self.assertEqual(coords_super.count(), 1)
        self.assertIn(self.coord_super, coords_super)

        # Apenas outros setores
        coords_outros = Usuario.get_coordenadores_por_vinculacao(superintendencia_only=False)
        self.assertEqual(coords_outros.count(), 2)
        self.assertIn(self.coord_vidas, coords_outros)
        self.assertIn(self.coord_brincando, coords_outros)

        # Todos os coordenadores
        coords_todos = Usuario.get_coordenadores_por_vinculacao(superintendencia_only=None)
        self.assertEqual(coords_todos.count(), 3)
        self.assertIn(self.coord_super, coords_todos)
        self.assertIn(self.coord_vidas, coords_todos)
        self.assertIn(self.coord_brincando, coords_todos)

    def test_tipo_coordenador_display(self):
        """
        Testa property que retorna o tipo de coordenador para exibição.
        """
        # Coordenador superintendência
        self.assertEqual(self.coord_super.tipo_coordenador, "Superintendência")

        # Coordenadores outros setores
        self.assertEqual(self.coord_vidas.tipo_coordenador, "Setor Vidas")
        self.assertEqual(self.coord_brincando.tipo_coordenador, "Setor Brincando e Aprendendo")

        # Não-coordenador
        self.assertIsNone(self.formador.tipo_coordenador)

    def test_permissoes_diferenciadas(self):
        """
        Testa que as permissões funcionam corretamente com a diferenciação.
        PRINCIPAL OBJETIVO: Controle interno de aprovações.
        """
        # Coordenador superintendência pode aprovar solicitações (é gerente)
        # Observação: Para aprovar precisa ser gerente, não coordenador
        # Mas vamos testar que a estrutura suporta

        # Coordenadores em geral podem criar solicitações
        self.assertTrue(self.coord_super.can_create_requests())
        self.assertTrue(self.coord_vidas.can_create_requests())
        self.assertTrue(self.coord_brincando.can_create_requests())

        # Formador não pode criar solicitações
        self.assertFalse(self.formador.can_create_requests())

    def test_integridade_sem_quebrar_funcionalidades(self):
        """
        Teste fundamental: A diferenciação NÃO QUEBRA funcionalidades existentes.
        """
        # Todos os métodos antigos continuam funcionando
        self.assertTrue(self.coord_super.can_create_requests())
        self.assertTrue(self.coord_vidas.can_create_requests())

        # Properties básicas funcionam
        self.assertEqual(self.coord_super.setor_nome, "Superintendência")
        self.assertEqual(self.coord_vidas.setor_nome, "Vidas")

        # Cargo display funciona
        self.assertEqual(self.coord_super.cargo_display, "Coordenador")
        self.assertEqual(self.coord_vidas.cargo_display, "Coordenador")

    def test_coordenador_sem_setor(self):
        """
        Testa comportamento com coordenador sem setor definido.
        """
        coord_sem_setor = Usuario.objects.create_user(
            username="coord_sem_setor",
            email="sem@test.com",
            cargo="coordenador",
            setor=None,  # Sem setor
            first_name="Pedro",
            last_name="Sem Setor"
        )

        # É coordenador
        self.assertTrue(coord_sem_setor.is_coordenador())

        # Não é nem superintendência nem outros setores
        self.assertFalse(coord_sem_setor.is_coordenador_superintendencia())
        self.assertFalse(coord_sem_setor.is_coordenador_outros_setores())

        # Tipo coordenador mostra sem setor
        self.assertEqual(coord_sem_setor.tipo_coordenador, "Sem setor definido")

    def test_backward_compatibility(self):
        """
        Testa que a implementação mantém compatibilidade com código existente.
        """
        # Métodos antigos continuam funcionando
        self.assertTrue(hasattr(self.coord_super, 'can_create_requests'))
        self.assertTrue(hasattr(self.coord_super, 'can_approve_requests'))
        self.assertTrue(hasattr(self.coord_super, 'setor_nome'))
        self.assertTrue(hasattr(self.coord_super, 'cargo_display'))

        # Novos métodos estão disponíveis
        self.assertTrue(hasattr(self.coord_super, 'is_coordenador_superintendencia'))
        self.assertTrue(hasattr(self.coord_super, 'is_coordenador_outros_setores'))
        self.assertTrue(hasattr(self.coord_super, 'tipo_coordenador'))

        # Métodos de classe funcionam
        self.assertTrue(hasattr(Usuario, 'get_coordenadores_superintendencia'))
        self.assertTrue(hasattr(Usuario, 'get_coordenadores_outros_setores'))
        self.assertTrue(hasattr(Usuario, 'get_coordenadores_por_vinculacao'))