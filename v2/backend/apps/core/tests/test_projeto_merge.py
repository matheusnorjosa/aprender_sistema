"""
Merge de Projetos duplicados no golden DB (RELAY 26, re-verificado ao vivo 2026-08-27).

Contexto: 3 pares VIDA existem repartidos — o nome canônico (caps) carrega
planos/DATAcao, e uma linha operacional na forma "&" carrega compra/solic/datcompra.
São o MESMO projeto real; a divisão veio de imports com formas de nome diferentes
antes de o resolver (#1372) ser aplicado de ponta a ponta. O merge reconcilia numa
única linha canônica (sem renomear — o sobrevivente já tem o nome canônico).

Invariantes provados aqui:
- reparent acontece ANTES do delete (relações PROTECT como Colecao bloqueariam senão);
- dry-run (default) não muta nada, mas reporta o que faria;
- idempotente (2ª execução pula a duplicata já mesclada);
- survivor ausente falha alto (não cria nada silenciosamente).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import pytest

from apps.core.models import Colecao, Projeto
from apps.core.services.projeto_merge import merge_projeto_duplicates
from apps.core.tests.factories import ProjetoFactory

pytestmark = pytest.mark.django_db


class TestApply:
    def test_reparents_all_relations_and_deletes_dup(self):
        survivor = ProjetoFactory(nome="CANONICO X", codigo="CANON_X", fluxo="NAO_SUPER", ativo=True)
        dup = ProjetoFactory(nome="Canonico & X", codigo="dup_x", fluxo="NAO_SUPER", ativo=True)
        # Colecao.projeto é PROTECT: se o reparent não vier antes do delete, o delete estoura.
        Colecao.objects.create(nome="Col Dup", projeto=dup)
        Colecao.objects.create(nome="Col Surv", projeto=survivor)

        report = merge_projeto_duplicates(pairs=[("CANONICO X", "Canonico & X")], apply=True)

        assert not Projeto.objects.filter(nome="Canonico & X").exists(), "duplicata deve ser deletada"
        assert set(Colecao.objects.filter(projeto=survivor).values_list("nome", flat=True)) == {
            "Col Dup",
            "Col Surv",
        }, "todas as coleções passam para o sobrevivente"
        entry = report["pairs"][0]
        assert entry["status"] == "merged"
        assert entry["reparented"]["Colecao"] == 1


class TestDryRun:
    def test_default_is_dry_run_and_mutates_nothing(self):
        survivor = ProjetoFactory(nome="CANONICO Y", codigo="CANON_Y", fluxo="NAO_SUPER", ativo=True)
        dup = ProjetoFactory(nome="Canonico & Y", codigo="dup_y", fluxo="NAO_SUPER", ativo=True)
        Colecao.objects.create(nome="Col Dup Y", projeto=dup)

        report = merge_projeto_duplicates(pairs=[("CANONICO Y", "Canonico & Y")])  # apply omitido

        assert Projeto.objects.filter(nome="Canonico & Y").exists(), "dry-run não deleta a duplicata"
        assert Colecao.objects.filter(projeto=dup).count() == 1, "dry-run não move relações"
        entry = report["pairs"][0]
        assert entry["status"] == "would_merge"
        assert entry["reparented"]["Colecao"] == 1, "mas reporta o que FARIA"


class TestIdempotent:
    def test_second_run_skips_already_merged(self):
        ProjetoFactory(nome="CANONICO Z", codigo="CANON_Z", fluxo="NAO_SUPER", ativo=True)
        ProjetoFactory(nome="Canonico & Z", codigo="dup_z", fluxo="NAO_SUPER", ativo=True)
        merge_projeto_duplicates(pairs=[("CANONICO Z", "Canonico & Z")], apply=True)

        report = merge_projeto_duplicates(pairs=[("CANONICO Z", "Canonico & Z")], apply=True)

        assert report["pairs"][0]["status"] == "skip"


class TestFailsLoud:
    def test_missing_survivor_raises(self):
        ProjetoFactory(nome="Dup Orfa", codigo="dorfa", fluxo="NAO_SUPER", ativo=True)
        with pytest.raises(ValueError):
            merge_projeto_duplicates(pairs=[("SURVIVOR INEXISTENTE", "Dup Orfa")], apply=True)
