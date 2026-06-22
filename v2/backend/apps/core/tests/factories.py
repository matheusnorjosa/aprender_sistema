"""
factory_boy factories para os testes de apps.core (#1404).

Centraliza a criação de entidades de teste, substituindo o boilerplate
`Model.objects.create(...)` / `get_or_create(...)` espalhado pela suíte.

Escopo: estas factories criam INSTÂNCIAS por-teste. Elas NÃO semeiam dados de
referência (grupos RBAC, permissões funcionais) — isso é papel das fixtures de
sessão em `conftest.py` (`ensure_base_groups` + `seed_functional_permissions`),
que rodam mesmo sob `pytest --no-migrations`.

Convenções:
- Campos `unique` usam `factory.Sequence` (determinístico; nunca `hash()` —
  ver memória `deterministic-unique-in-pytest`).
- `TipoEventoFactory` e `GroupFactory` usam `django_get_or_create` para espelhar
  o padrão `get_or_create(nome=...)` predominante (reaproveita a mesma linha).
- `UsuarioFactory(groups=["Coordenador", ...])` anexa o usuário a grupos base
  já existentes (criados pelo seed de sessão).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group
from django.utils import timezone

import factory

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario


class GroupFactory(factory.django.DjangoModelFactory):
    """Grupo RBAC. `django_get_or_create` evita duplicar grupos base do seed."""

    class Meta:
        model = Group
        django_get_or_create = ("name",)

    name = "Coordenador"


class UsuarioFactory(factory.django.DjangoModelFactory):
    """Usuário de teste com CPF/username/email únicos e determinísticos."""

    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    first_name = "Test"
    last_name = "User"
    cpf = factory.Sequence(lambda n: str(n + 1).zfill(11))
    is_active = True

    class Params:
        # UsuarioFactory(superuser=True) → staff + superuser
        superuser = factory.Trait(is_staff=True, is_superuser=True)

    @factory.post_generation
    def password(self, create: bool, extracted, **kwargs):  # noqa: ANN001
        """
        Senha hasheada via set_password (default "testpass123"). Torna a factory
        drop-in para create_user/create_superuser inclusive em testes que
        autenticam por senha: UsuarioFactory(password="x") loga com "x".
        """
        if not create:
            return
        self.set_password(extracted if extracted else "testpass123")
        self.save()

    @factory.post_generation
    def groups(self, create: bool, extracted, **kwargs):  # noqa: ANN001
        """UsuarioFactory(groups=["Coordenador", "DAT"]) anexa aos grupos."""
        if not create or not extracted:
            return
        for name in extracted:
            group, _ = Group.objects.get_or_create(name=name)
            self.groups.add(group)


class MunicipioFactory(factory.django.DjangoModelFactory):
    """Município com nome único (constraint unique nome+uf)."""

    class Meta:
        model = Municipio

    nome = factory.Sequence(lambda n: f"Municipio {n}")
    uf = "CE"
    ativo = True


class ProjetoFactory(factory.django.DjangoModelFactory):
    """Projeto NAO_SUPER por padrão; `ProjetoFactory(super=True)` → fluxo SUPER."""

    class Meta:
        model = Projeto

    nome = factory.Sequence(lambda n: f"Projeto {n}")
    fluxo = "NAO_SUPER"
    ativo = True

    class Params:
        super = factory.Trait(fluxo="SUPER")


class TipoEventoFactory(factory.django.DjangoModelFactory):
    """Tipo de evento. `django_get_or_create` espelha o get_or_create(nome=...)."""

    class Meta:
        model = TipoEvento
        django_get_or_create = ("nome",)

    nome = "Formação"


class SolicitacaoFactory(factory.django.DjangoModelFactory):
    """
    Solicitação pendente por padrão (PA-01: a auto-aprovação NAO_SUPER vive na
    camada serializer/view, não no model — criar via ORM mantém `pendente`).
    """

    class Meta:
        model = Solicitacao

    usuario = factory.SubFactory(UsuarioFactory)
    tipo_evento = factory.SubFactory(TipoEventoFactory)
    municipio = factory.SubFactory(MunicipioFactory)
    projeto = factory.SubFactory(ProjetoFactory)
    inicio = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    fim = factory.LazyAttribute(lambda o: o.inicio + timedelta(hours=2))
    status = Solicitacao.Status.PENDENTE
