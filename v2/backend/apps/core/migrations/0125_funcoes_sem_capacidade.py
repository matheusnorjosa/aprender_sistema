"""PR 8 das permissões (ADR-020, "o papel dá o poder"): grupo de FUNÇÃO não dá capacidade.

O direito de evento passa a vir do papel vigente na gerência (`rbac_pacotes.DIREITOS_PAPEL`, lido por
`rbac_permissions.capacidades_sem_cache`). Esta migration:

- apaga os pares capacidade × grupo de TODO grupo de função: os fixos (`FUNCAO_GROUPS` na data
  desta migration) e os classificados como FUNÇÃO na tela (`GroupClassificacao tipo=FUNCAO`);
- apaga a capacidade `approve_solicitation_batch` (grupos Gerente e Superintendência). Ela não
  porteia nenhuma rota; dava a "gestora" de solicitação, que agora é o papel GERENTE vigente.

A matriz do seed (`functional_permissions_seed.py`) muda junto; `rbac_diff --auditar` segue em 0.
Reverse recria a capacidade e os pares do seed anterior (grupos fixos; um par de grupo dinâmico,
que o seed nunca teve, não volta).
"""

from __future__ import annotations

from django.db import migrations

# Grupos de função na data desta migration (`apps.core.constants.FUNCAO_GROUPS`), congelados aqui.
FUNCOES: tuple[str, ...] = (
    "Formador",
    "Coordenador",
    "Apoio de Coordenação",
    "Gerente",
    "Assistente Administrativo",
)

BATCH = "approve_solicitation_batch"
BATCH_DEFAULTS = {
    "label": "Aprovar solicitações em lote",
    "description": "Aprovar múltiplas solicitações em uma operação.",
    "category": "solicitacao",
    "is_system": True,
}
BATCH_GRUPOS: tuple[str, ...] = ("Gerente", "Superintendência")

# Pares (grupo de função, capacidade) do seed anterior, para a reversa.
PARES_ANTERIORES: tuple[tuple[str, str], ...] = (
    ("Coordenador", "create_solicitation"),
    ("Apoio de Coordenação", "create_solicitation"),
    ("Gerente", "create_solicitation"),
    ("Coordenador", "edit_solicitation_as_owner_or_privileged"),
    ("Apoio de Coordenação", "edit_solicitation_as_owner_or_privileged"),
    ("Gerente", "edit_solicitation_as_owner_or_privileged"),
    ("Apoio de Coordenação", "publish_setor_solicitacao"),
    ("Assistente Administrativo", "manage_purchases_and_materials"),
    ("Assistente Administrativo", "operate_preagenda"),
    ("Assistente Administrativo", "run_daily_operations"),
)


def forwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    GroupClassificacao = apps.get_model("core", "GroupClassificacao")

    dinamicos = GroupClassificacao.objects.filter(tipo="funcao").values_list("group__name", flat=True)
    funcoes = set(FUNCOES) | set(dinamicos)
    pares = PermissaoFuncional.groups.through.objects.filter(group__name__in=funcoes)
    pares.delete()  # noqa: RBAC-migration-allowed
    PermissaoFuncional.objects.filter(codename=BATCH).delete()


def backwards(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    batch, _ = PermissaoFuncional.objects.update_or_create(codename=BATCH, defaults=BATCH_DEFAULTS)
    for nome in BATCH_GRUPOS:
        batch.groups.add(Group.objects.get_or_create(name=nome)[0])  # noqa: RBAC-migration-allowed
    for nome, codename in PARES_ANTERIORES:
        perm = PermissaoFuncional.objects.filter(codename=codename).first()
        if perm is None:
            continue
        perm.groups.add(Group.objects.get_or_create(name=nome)[0])  # noqa: RBAC-migration-allowed


class Migration(migrations.Migration):
    dependencies = [("core", "0124_solicitacao_observacoes_max_length")]
    operations = [migrations.RunPython(forwards, backwards)]
