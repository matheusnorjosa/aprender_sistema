"""
Seed idempotente para templates de acoes/notificacoes (32 passos).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.models import AcaoTemplate, AcaoTemplateExecutor


@dataclass(frozen=True)
class AcaoTemplateSeed:
    ordem: int
    nome: str
    descricao_prazo: str
    tipo_ancora: str
    dias_prazo_uteis: int
    ref_evento_externo: str = ""
    ref_acao_ordem: int | None = None


GROUPS_TO_ENSURE: list[str] = [
    "Comercial",
    "Relacionamento",
    "Logística Viagens",
    "Logística Galpão",
    "DAT",
    "Coordenador",
    "Gerente",
]


ACTIONS_SEED: list[AcaoTemplateSeed] = [
    AcaoTemplateSeed(
        ordem=1,
        nome="ENTREGA DOS MATERIAIS",
        descricao_prazo="Até 21 dias úteis após ordem fornecimento",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="ORDEM_FORNECIMENTO",
        dias_prazo_uteis=21,
    ),
    AcaoTemplateSeed(
        ordem=2,
        nome="BOAS VINDAS",
        descricao_prazo="Até 7 dias úteis após entrega prazo",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=1,
        dias_prazo_uteis=7,
    ),
    AcaoTemplateSeed(
        ordem=3,
        nome="PRIMEIRO CONTATO/SME",
        descricao_prazo="Até 5 dias úteis após coordenação ser informada sobre o Município",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="COORDENACAO_INFORMADA_MUNICIPIO",
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=4,
        nome="REUNIÃO DE ARTICULAÇÃO/ SME",
        descricao_prazo="Até 5 dias úteis após a a reunião de alinhamento (formato virtual) / Até 10 dias se formato presencial",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="REUNIAO_ALINHAMENTO",
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=5,
        nome="PRIMEIRA FORMAÇÃO / PRESENCIAL OU HÍBRIDA",
        descricao_prazo="Até 20 dias úteis após a reunião de alinhamento",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=4,
        dias_prazo_uteis=20,
    ),
    AcaoTemplateSeed(
        ordem=6,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 1ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=5,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=7,
        nome="SEGUNDA FORMAÇÃO / REMOTA",
        descricao_prazo="Até 30 dias úteis após a 1ª Formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=5,
        dias_prazo_uteis=30,
    ),
    AcaoTemplateSeed(
        ordem=8,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 1ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=5,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=9,
        nome="APLICAÇÃO PRIMEIRA AVALIAÇÃO",
        descricao_prazo="Até 60 dias úteis após o inicío do trabalho na sala de aula com o material",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="INICIO_TRABALHO_SALA",
        dias_prazo_uteis=60,
    ),
    AcaoTemplateSeed(
        ordem=10,
        nome="INSERÇÃO DOS DADOS NA PLATAFORMA PELO MUNICÍPIO PRIMEIRA AVALIAÇÃO",
        descricao_prazo="Até 20 dias úteis após a Consolidação dos Dados coletados",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="CONSOLIDACAO_DADOS_AVALIACAO_1",
        dias_prazo_uteis=20,
    ),
    AcaoTemplateSeed(
        ordem=11,
        nome="RELATÓRIO PARA O MUNICÍPIO PRIMEIRA AVALIAÇÃO",
        descricao_prazo="Até 10 dias úteis após a Consolidação dos Dados coletados",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="CONSOLIDACAO_DADOS_AVALIACAO_1",
        dias_prazo_uteis=10,
    ),
    AcaoTemplateSeed(
        ordem=12,
        nome="PRIMEIRO ACOMPANHAMENTO",
        descricao_prazo="Até 90 dias úteis após o início do trabalho na sala de aula com o material",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="INICIO_TRABALHO_SALA",
        dias_prazo_uteis=90,
    ),
    AcaoTemplateSeed(
        ordem=13,
        nome="COMPILAÇÃO DOS DADOS PELO FORMADOR(A) PRIMEIRO ACOMPANHAMENTO",
        descricao_prazo="Até 15 dias úteis após a realização do acompanhamento de sala",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=12,
        dias_prazo_uteis=15,
    ),
    AcaoTemplateSeed(
        ordem=14,
        nome="RELATÓRIO DOS DADOS PARA O MUNICÍPIO DO SEGUNDO ACOMPANHAMENTO",
        descricao_prazo="Até 15 dias úteis após a realização do acompanhamento de sala",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=12,
        dias_prazo_uteis=15,
    ),
    AcaoTemplateSeed(
        ordem=15,
        nome="TERCEIRA FORMAÇÃO/ PRESENCIAL OU HÍBRIDA",
        descricao_prazo="Até 30 dias úteis após a 2ª Formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=7,
        dias_prazo_uteis=30,
    ),
    AcaoTemplateSeed(
        ordem=16,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 3ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=15,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=17,
        nome="QUARTA FORMAÇÃO/ REMOTA",
        descricao_prazo="Até 20 dias úteis após início do semestre",
        tipo_ancora="MARCO_CALENDARIO",
        ref_evento_externo="INICIO_SEMESTRE",
        dias_prazo_uteis=20,
    ),
    AcaoTemplateSeed(
        ordem=18,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 4ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=17,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=19,
        nome="SEGUNDO ACOMPANHAMENTO",
        descricao_prazo="Até 10 dias úteis após a 4ª Formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=17,
        dias_prazo_uteis=10,
    ),
    AcaoTemplateSeed(
        ordem=20,
        nome="COMPILAÇÃO DOS DADOS PELO FORMADOR(A) SEGUNDO ACOMPANHAMENTO",
        descricao_prazo="Até 15 dias úteis após a realização do acompanhamento de sala",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=19,
        dias_prazo_uteis=15,
    ),
    AcaoTemplateSeed(
        ordem=21,
        nome="RELATÓRIO DOS DADOS PARA O MUNICÍPIO DO SEGUNDO ACOMPANHAMENTO",
        descricao_prazo="Até 15 dias úteis após a realização do acompanhamento de sala",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=19,
        dias_prazo_uteis=15,
    ),
    AcaoTemplateSeed(
        ordem=22,
        nome="QUINTA FORMAÇÃO/ PRESENCIAL OU HÍBRIDA",
        descricao_prazo="Até 30 dias úteis após a 4ª Formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=17,
        dias_prazo_uteis=30,
    ),
    AcaoTemplateSeed(
        ordem=23,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 5ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=22,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=24,
        nome="APLICAÇÃO DA SEGUNDA AVALIAÇÃO",
        descricao_prazo="Até 7 dias úteis após a 5ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=22,
        dias_prazo_uteis=7,
    ),
    AcaoTemplateSeed(
        ordem=25,
        nome="INSERÇÃO DOS DADOS NA PLATAFORMA PELO MUNICÍPIO SEGUNDA AVALIAÇÃO",
        descricao_prazo="Até 20 dias úteis após a Consolidação dos Dados coletados",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="CONSOLIDACAO_DADOS_AVALIACAO_2",
        dias_prazo_uteis=20,
    ),
    AcaoTemplateSeed(
        ordem=26,
        nome="RELATÓRIO PARA O MUNICÍPIO SEGUNDA AVALIAÇÃO",
        descricao_prazo="Até 10 dias úteis após a Consolidação dos Dados coletados",
        tipo_ancora="EVENTO_EXTERNO",
        ref_evento_externo="CONSOLIDACAO_DADOS_AVALIACAO_2",
        dias_prazo_uteis=10,
    ),
    AcaoTemplateSeed(
        ordem=27,
        nome="SEXTA FORMAÇÃO/ REMOTA",
        descricao_prazo="Até 15 dias úteis após a 5ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=22,
        dias_prazo_uteis=15,
    ),
    AcaoTemplateSeed(
        ordem=28,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 6ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=27,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=29,
        nome="SÉTIMA FORMAÇÃO/ REMOTA",
        descricao_prazo="Até 25 dias úteis após a 6ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=27,
        dias_prazo_uteis=25,
    ),
    AcaoTemplateSeed(
        ordem=30,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a 6ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=27,
        dias_prazo_uteis=5,
    ),
    AcaoTemplateSeed(
        ordem=31,
        nome="ATIVIDADE DE ESTUDO",
        descricao_prazo="Até 15 dias úteis após a 6ª formação",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=27,
        dias_prazo_uteis=15,
    ),
    AcaoTemplateSeed(
        ordem=32,
        nome="FEEDBACK DA EQUIPE TECNICA",
        descricao_prazo="Até 5 dias úteis após a atividade de estudo",
        tipo_ancora="ACAO_ANTERIOR",
        ref_acao_ordem=31,
        dias_prazo_uteis=5,
    ),
]


EXECUTORS_BY_ACTION: dict[int, list[str]] = {
    1: ["Logística Galpão"],
    2: ["Comercial", "Relacionamento", "DAT"],
}
for _ordem in range(3, 33):
    EXECUTORS_BY_ACTION[_ordem] = ["Coordenador", "Gerente"]


def _validate_seed_configuration() -> None:
    ordens = sorted(item.ordem for item in ACTIONS_SEED)
    expected = list(range(1, 33))
    if ordens != expected:
        raise ValueError("ACTIONS_SEED deve conter exatamente ordens de 1 a 32 sem gaps.")

    allowed_groups = set(GROUPS_TO_ENSURE)
    for ordem in expected:
        executors = EXECUTORS_BY_ACTION.get(ordem, [])
        if not executors:
            raise ValueError(f"Ação {ordem} sem executor configurado.")
        invalid = set(executors) - allowed_groups
        if invalid:
            raise ValueError(f"Ação {ordem} com grupos inválidos: {sorted(invalid)}")


def seed_acoes_notificacao(*, verbose: bool = False) -> dict[str, Any]:
    """
    Seed idempotente dos 32 templates e executores.
    """

    stats: dict[str, int] = {
        "groups_created": 0,
        "templates_created": 0,
        "templates_updated": 0,
        "executor_links_created": 0,
        "executor_links_removed": 0,
    }

    _validate_seed_configuration()

    with transaction.atomic():
        for group_name in GROUPS_TO_ENSURE:
            _, created = Group.objects.get_or_create(name=group_name)
            if created:
                stats["groups_created"] += 1
                if verbose:
                    print(f"[seed_acoes_notificacao] group created: {group_name}")

        by_ordem: dict[int, AcaoTemplate] = {}
        for item in sorted(ACTIONS_SEED, key=lambda seed: seed.ordem):
            ref_template = None
            if item.ref_acao_ordem is not None:
                ref_template = by_ordem[item.ref_acao_ordem]

            obj, created = AcaoTemplate.objects.update_or_create(
                ordem=item.ordem,
                defaults={
                    "nome": item.nome,
                    "descricao_prazo": item.descricao_prazo,
                    "tipo_ancora": item.tipo_ancora,
                    "dias_prazo_uteis": item.dias_prazo_uteis,
                    "ref_evento_externo": item.ref_evento_externo,
                    "ref_acao_template": ref_template,
                    "ativo": True,
                },
            )
            if created:
                stats["templates_created"] += 1
            else:
                stats["templates_updated"] += 1
            by_ordem[item.ordem] = obj

        for ordem, groups in EXECUTORS_BY_ACTION.items():
            template = by_ordem[ordem]
            desired = set(groups)
            existing = set(
                AcaoTemplateExecutor.objects.filter(acao_template=template).values_list("group__name", flat=True)
            )

            for group_name in desired - existing:
                group = Group.objects.get(name=group_name)
                AcaoTemplateExecutor.objects.create(acao_template=template, group=group, ativo=True)
                stats["executor_links_created"] += 1

            stale_names = existing - desired
            if stale_names:
                deleted, _ = AcaoTemplateExecutor.objects.filter(
                    acao_template=template, group__name__in=stale_names
                ).delete()
                stats["executor_links_removed"] += deleted

    return stats
