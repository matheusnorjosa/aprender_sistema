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
  já existentes (criados pelo seed de sessão). Grupo de FUNÇÃO com papel de gerência
  (Coordenador, Apoio, Gerente, Formador) vem junto com o vínculo vigente (`com_papel`),
  como o cadastro de usuário faz; `groups__gerencia=g` escolhe a gerência e
  `groups__vinculo=False` cria só o grupo (teste de "grupo sem vínculo"). Grupo de setor com
  capacidade (DAT, Controle, Diretoria) vem com o vínculo EQUIPE na gerência do pacote
  (`PACOTE_DO_GRUPO_DE_SETOR`, PR 12a), como os membros desses grupos em produção.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportPrivateImportUsage=false, reportIncompatibleVariableOverride=false

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

from django.contrib.auth.models import Group
from django.utils import timezone

import factory

from apps.core.models import DATCompra, EquipeGerencia, Gerencia, Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.equipe_gerencia import PAPEL_POR_FUNCAO

# Papel de gerência → grupo de função (inverso do cadastro). EQUIPE não tem grupo.
GRUPO_POR_PAPEL: dict[str, str] = {papel: grupo for grupo, papel in PAPEL_POR_FUNCAO.items()}

# Início de vigência fixo no passado: o vínculo segue vigente em teste com data congelada.
_INICIO_VINCULO = date(2000, 1, 1)


class GroupFactory(factory.django.DjangoModelFactory[Group]):
    """Grupo RBAC. `django_get_or_create` evita duplicar grupos base do seed."""

    class Meta:
        model = Group
        django_get_or_create = ("name",)

    name = "Coordenador"


class UsuarioFactory(factory.django.DjangoModelFactory[Usuario]):
    """Usuário de teste com CPF/username/email únicos e determinísticos."""

    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    # first_name/last_name vazios por padrão = fiéis a create_user/create_superuser
    # (que não preenchem nome). Importa p/ asserts em usuario_nome, que cai no
    # username quando get_full_name() é vazio. Passe explicitamente se precisar.
    first_name = ""
    last_name = ""
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
        """UsuarioFactory(groups=["Coordenador", "DAT"]) anexa aos grupos.

        Grupo de função com papel ganha o vínculo vigente junto (`com_papel`); DAT, Controle e
        Diretoria ganham o vínculo do pacote (`PACOTE_DO_GRUPO_DE_SETOR`). Opções:
        `groups__gerencia=g` (default: gerência neutra própria) e `groups__vinculo=False` (só o grupo).
        """
        if not create or not extracted:
            return
        com_vinculo = kwargs.get("vinculo", True)
        for name in extracted:
            if com_vinculo and name in PAPEL_POR_FUNCAO:
                com_papel(cast(Usuario, self), PAPEL_POR_FUNCAO[name], kwargs.get("gerencia"))
                continue
            group, _ = Group.objects.get_or_create(name=name)
            self.groups.add(group)
            if com_vinculo and name in PACOTE_DO_GRUPO_DE_SETOR:
                PACOTE_DO_GRUPO_DE_SETOR[name](cast(Usuario, self))


class GerenciaFactory(factory.django.DjangoModelFactory[Gerencia]):
    """Gerência neutra: perfil PADRAO (sem pacote) e `setor_canonico` vazio (não define escopo de setor)."""

    class Meta:
        model = Gerencia

    nome = factory.Sequence(lambda n: f"GERENCIA TESTE {n}")
    nome_setor = factory.Sequence(lambda n: f"Teste {n}")
    ativo = True


def com_papel(user: Usuario, papel: str, gerencia: Gerencia | None = None, **extra: Any) -> EquipeGerencia:
    """Dá a `user` o papel `papel` em `gerencia`: o grupo de função do papel e o vínculo vigente.

    É o par que o cadastro de usuário grava (função + lotação). O vínculo começa em 2000-01-01 e não
    tem fim; `extra` sobrescreve (ex.: `valid_to=...`, `ativo=False`). Sem `gerencia`, cria uma
    gerência neutra só deste vínculo (`GerenciaFactory`): sem pacote, sem setor e sem projeto, ela
    não muda o que a pessoa enxerga. Passe a gerência quando o teste depende dela.
    EQUIPE não tem grupo de função; só o vínculo é criado.
    """
    grupo = GRUPO_POR_PAPEL.get(papel)
    if grupo is not None:
        user.groups.add(Group.objects.get_or_create(name=grupo)[0])
    dados: dict[str, Any] = {"ativo": True, "valid_from": _INICIO_VINCULO, "valid_to": None, **extra}
    vinculo, _ = EquipeGerencia.objects.update_or_create(
        gerencia=gerencia or GerenciaFactory(), usuario=user, papel=papel, defaults=dados
    )
    return vinculo


def com_pacote_do_dat(user: Usuario) -> EquipeGerencia:
    """Vínculo EQUIPE na `GERENCIA DAT` (perfil ADMIN_OPERACIONAL): o pacote do DAT (PR 10).

    Desde a migration 0126 o grupo Superintendência não tem capacidade; quem aprova pela capacidade
    (`approve_solicitation`), publica no Google e exclui nos cadastros é o DAT pelo pacote. Testes
    cuja persona "Superintendência" representava esse poder ganham o vínculo por aqui.
    """
    from apps.core.services.rbac_permissions import invalidate_user_functional_permissions_cache

    gerencia, _ = Gerencia.objects.get_or_create(nome="GERENCIA DAT", defaults={"nome_setor": "DAT"})
    if gerencia.perfil != Gerencia.Perfil.ADMIN_OPERACIONAL:
        gerencia.perfil = Gerencia.Perfil.ADMIN_OPERACIONAL
        gerencia.save(update_fields=["perfil"])
    vinculo = com_papel(user, "EQUIPE", gerencia)
    invalidate_user_functional_permissions_cache(user.pk)
    return vinculo


def com_pacote_do_controle(user: Usuario, papel: str = "EQUIPE") -> EquipeGerencia:
    """Vínculo EQUIPE (ou GERENTE) na gerência `CONTROLE` (perfil CONTROLE): o pacote do Controle (PR 11).

    Desde o PR 11 (D1 de 06/10) o pacote CONTROLE tem `approve_solicitation`: quem trabalha no Controle
    aprova pelo vínculo, não pelo par de grupos Controle + Assistente Administrativo.
    """
    from apps.core.services.rbac_permissions import invalidate_user_functional_permissions_cache

    gerencia, _ = Gerencia.objects.get_or_create(nome="CONTROLE", defaults={"nome_setor": "Controle"})
    if gerencia.perfil != Gerencia.Perfil.CONTROLE:
        gerencia.perfil = Gerencia.Perfil.CONTROLE
        gerencia.save(update_fields=["perfil"])
    vinculo = com_papel(user, papel, gerencia)
    invalidate_user_functional_permissions_cache(user.pk)
    return vinculo


def com_pacote_da_diretoria(user: Usuario) -> EquipeGerencia:
    """Vínculo EQUIPE na gerência `DIRETORIA` (perfil DIRETORIA): o pacote da Diretoria (PR 12, C8).

    O pacote DIRETORIA é igual ao grupo Diretoria do seed. Em produção ninguém está no grupo nem existe a
    gerência; o vínculo é o caminho da Diretoria quando o grupo deixar de dar poder.
    """
    from apps.core.services.rbac_permissions import invalidate_user_functional_permissions_cache

    gerencia, _ = Gerencia.objects.get_or_create(nome="DIRETORIA", defaults={"nome_setor": "Diretoria"})
    if gerencia.perfil != Gerencia.Perfil.DIRETORIA:
        gerencia.perfil = Gerencia.Perfil.DIRETORIA
        gerencia.save(update_fields=["perfil"])
    vinculo = com_papel(user, "EQUIPE", gerencia)
    invalidate_user_functional_permissions_cache(user.pk)
    return vinculo


# Grupo de setor com capacidade → o vínculo que dá o mesmo poder pelo lugar (PR 12a). Em produção os
# membros desses grupos têm esse vínculo (medição de 16/10); a factory espelha isso.
PACOTE_DO_GRUPO_DE_SETOR = {
    "DAT": com_pacote_do_dat,
    "Controle": com_pacote_do_controle,
    "Diretoria": com_pacote_da_diretoria,
}


def com_vinculo_dos_grupos(user: Usuario) -> None:
    """Dá a `user` o vínculo do pacote de cada grupo de setor com capacidade que ele já tem (PR 12a).

    Para os testes que põem o grupo à mão (`user.groups.add(...)`) com o grupo como variável ou parâmetro.
    """
    for nome in user.groups.filter(name__in=PACOTE_DO_GRUPO_DE_SETOR).values_list("name", flat=True):
        PACOTE_DO_GRUPO_DE_SETOR[nome](user)


class MunicipioFactory(factory.django.DjangoModelFactory[Municipio]):
    """Município com nome único (constraint unique nome+uf)."""

    class Meta:
        model = Municipio

    nome = factory.Sequence(lambda n: f"Municipio {n}")
    uf = "CE"
    ativo = True


class ProjetoFactory(factory.django.DjangoModelFactory[Projeto]):
    """Projeto NAO_SUPER por padrão; `ProjetoFactory(super=True)` → fluxo SUPER."""

    class Meta:
        model = Projeto

    nome = factory.Sequence(lambda n: f"Projeto {n}")
    fluxo = "NAO_SUPER"
    ativo = True

    class Params:
        super = factory.Trait(fluxo="SUPER")


class TipoEventoFactory(factory.django.DjangoModelFactory[TipoEvento]):
    """Tipo de evento. `django_get_or_create` espelha o get_or_create(nome=...)."""

    class Meta:
        model = TipoEvento
        django_get_or_create = ("nome",)

    nome = "Formação"


class SolicitacaoFactory(factory.django.DjangoModelFactory[Solicitacao]):
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


def liberar_par(municipio: Municipio, projeto: Projeto, **extra) -> DATCompra:
    """Grava a compra que libera o par para a regra da compra (`services/compra_elegibilidade`).

    `DATCompra` ativa com `quantidade=1` por padrão; `extra` sobrescreve (ex.: `ativo=False`,
    `quantidade=0`, `ano_uso=2027`). O autor (`created_by`, obrigatório) é uma conta inativa fixa,
    para não aparecer nas listas de pessoas dos testes.
    """
    autor, _ = Usuario.objects.get_or_create(
        username="liberar_par_autor",
        defaults={"email": "liberar_par_autor@example.invalid", "cpf": "00000000000", "is_active": False},
    )
    dados = {"quantidade": 1, "created_by": autor, **extra}
    return DATCompra.objects.create(municipio=municipio, projeto=projeto, **dados)
