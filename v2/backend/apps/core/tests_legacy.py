"""
Core app tests
"""

import pytest
from django.test import TestCase
from .models import Usuario, Municipio, Projeto


class UsuarioModelTest(TestCase):
    """Tests for Usuario model"""

    def test_usuario_str(self):
        """Test Usuario string representation"""
        usuario = Usuario(username="test", cpf="12345678901", first_name="Test", last_name="User")
        assert str(usuario) == "Test User (12345678901)"

    def test_usuario_cpf_unique(self):
        """Test CPF uniqueness constraint"""
        Usuario.objects.create(username="user1", cpf="12345678901")
        with pytest.raises(Exception):
            Usuario.objects.create(username="user2", cpf="12345678901")


class MunicipioModelTest(TestCase):
    """Tests for Municipio model"""

    def test_municipio_str(self):
        """Test Municipio string representation"""
        municipio = Municipio(nome="Fortaleza", uf="CE")
        assert str(municipio) == "Fortaleza-CE"

    def test_municipio_ordering(self):
        """Test Municipio ordering"""
        Municipio.objects.create(nome="Sobral", uf="CE")
        Municipio.objects.create(nome="Fortaleza", uf="CE")
        municipios = list(Municipio.objects.all())
        assert municipios[0].nome == "Fortaleza"
        assert municipios[1].nome == "Sobral"


class ProjetoModelTest(TestCase):
    """Tests for Projeto model"""

    def test_projeto_str(self):
        """Test Projeto string representation"""
        projeto = Projeto(nome="ACerta")
        assert str(projeto) == "ACerta"
