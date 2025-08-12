# aprender_sistema/core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser # Importar para estender o modelo de usuário padrão
import uuid # Para usar UUID como chave primária

# 1. Modelo de Usuários (Estendendo o padrão do Django)
# Usaremos o AbstractUser para adicionar um campo 'papel' ao modelo de usuário padrão do Django.
class Usuario(AbstractUser):
    # Definir as opções de papel (role) para o usuário
    ROLES = (
        ('coordenador', 'Coordenador'),
        ('superintendencia', 'Superintendência'),
        ('controle', 'Controle'),
        ('formador', 'Formador'),
        ('admin', 'Admin do Sistema'),
        ('diretoria', 'Diretoria'),
    )
    # Adicionar o campo 'papel' ao modelo de usuário
    papel = models.CharField(max_length=50, choices=ROLES, default='coordenador')
    # O id já é gerenciado pelo AbstractUser, mas podemos adicionar um UUID se quisermos um PK diferente
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.username # Ou self.email, dependendo de como você quer exibir

# 2. Modelo de Projetos
class Projeto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Projeto")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"

    def __str__(self):
        return self.nome

# 3. Modelo de Municípios
class Municipio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Município")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"

    def __str__(self):
        return self.nome

# 4. Modelo de Formadores
class Formador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, verbose_name="Nome do Formador")
    email = models.EmailField(max_length=255, unique=True, verbose_name="E-mail")
    area_atuacao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Área de Atuação")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Formador"
        verbose_name_plural = "Formadores"

    def __str__(self):
        return self.nome

# 5. Modelo de Tipos de Evento
class TipoEvento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Tipo de Evento")
    online = models.BooleanField(default=False, verbose_name="É Online?")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Tipo de Evento"
        verbose_name_plural = "Tipos de Evento"

    def __str__(self):
        return self.nome
