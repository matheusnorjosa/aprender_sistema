"""
PR A da arquitetura de permissões (ADR-020): pacote de capacidades por perfil de gerência.

`services/rbac_pacotes.py` só tem constantes e nada lê o pacote ainda (a fórmula da união é o
PR B). Estes testes travam a tabela: todo perfil tem linha explícita, capacidade técnica nunca
entra em pacote, PADRAO e APROVACAO são vazios e o pacote está contido no grupo de setor do seed,
para que o PR B não dê poder novo a ninguém.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from apps.core.models import EquipeGerencia, Gerencia
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED
from apps.core.services.rbac_pacotes import PACOTE, PAPEIS_COM_PACOTE, PERFIL_PERMITIDO, TECNICAS

# parents[0]=tests, [1]=core, [2]=apps, [3]=backend root (local: v2/backend, container: /app)
BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _grupos_do_seed(codename: str) -> set[str]:
    return set(next(item.group_names for item in FUNCTIONAL_PERMISSIONS_SEED if item.codename == codename))


def test_todo_perfil_tem_linha_explicita():
    assert set(PACOTE) == set(Gerencia.Perfil.values)


def test_nenhuma_capacidade_tecnica_em_pacote():
    assert TECNICAS == frozenset({"import_spreadsheet"})
    for perfil, capacidades in PACOTE.items():
        assert not capacidades & TECNICAS, perfil


def test_padrao_e_aprovacao_vazios():
    assert PACOTE[Gerencia.Perfil.PADRAO] == frozenset()
    assert PACOTE[Gerencia.Perfil.APROVACAO] == frozenset()


def test_codenames_do_pacote_existem_no_seed():
    do_seed = {item.codename for item in FUNCTIONAL_PERMISSIONS_SEED}
    for perfil, capacidades in PACOTE.items():
        assert capacidades <= do_seed, (perfil, capacidades - do_seed)


def test_pacote_contido_no_grupo_do_seed():
    """Limite: compara constante com constante. A prova contra o banco é o ensaio do PR 5."""
    grupo_do_perfil = {
        Gerencia.Perfil.ADMIN_OPERACIONAL: "DAT",
        Gerencia.Perfil.CONTROLE: "Controle",
        Gerencia.Perfil.DIRETORIA: "Diretoria",
    }
    for perfil, grupo in grupo_do_perfil.items():
        for codename in PACOTE[perfil]:
            assert grupo in _grupos_do_seed(codename), (perfil, codename)


def test_papeis_com_pacote_sao_equipe_e_gerente():
    """D3 (a): só EQUIPE e GERENTE recebem o pacote; os dois são papéis válidos do vínculo."""
    assert frozenset({EquipeGerencia.PAPEL_EQUIPE, "GERENTE"}) == PAPEIS_COM_PACOTE
    assert {valor for valor, _ in EquipeGerencia.PAPEL_CHOICES} >= PAPEIS_COM_PACOTE


def test_perfil_permitido_so_tem_perfis_com_pacote():
    assert PERFIL_PERMITIDO == {
        "GERENCIA DAT": Gerencia.Perfil.ADMIN_OPERACIONAL,
        "CONTROLE": Gerencia.Perfil.CONTROLE,
    }


def test_import_do_modulo_nao_cria_ciclo():
    """O módulo é só constantes: não importa nada do projeto, e `rbac_permissions` sobe com ele.

    Em `rbac/` ele quebraria a subida no PR B (`rbac/__init__` → `helpers` → `rbac_permissions`
    pela metade). Processo limpo, para nenhum import deste processo de teste mascarar o ciclo.
    """
    fonte = (BACKEND_ROOT / "apps" / "core" / "services" / "rbac_pacotes.py").read_text(encoding="utf-8")
    importados = {
        n.module if isinstance(n, ast.ImportFrom) else a.name
        for n in ast.walk(ast.parse(fonte))
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in n.names
    }
    assert importados <= {"__future__"}, importados

    codigo = "; ".join(
        (
            "import django",
            "django.setup()",
            "import apps.core.services.rbac_pacotes",
            "import apps.core.services.rbac_permissions",
            "print('ok')",
        )
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=BACKEND_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip().endswith("ok")
