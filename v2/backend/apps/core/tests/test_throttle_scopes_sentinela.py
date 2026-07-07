"""Sentinela da config de throttle (rate-limit) do DRF.

Esta classe de bug ja mordeu 2x nesta base:
- `change_password` (#1502): definido no dict base mas ausente do override de dev, que
  SUBSTITUI o dict inteiro (`if ENVIRONMENT == "development"`) -> runtime quebrava com
  "No default throttle rate set for 'change_password' scope".
- `oauth`: usado em `OAuthThrottle.scope` mas ausente dos dicts (so funcionava por causa
  de um `rate` hardcodado na classe).

Estes testes barram AMBOS os modos de falha, para o CI reprovar antes de chegar em prod:
1. os dicts base e dev de `DEFAULT_THROTTLE_RATES` tem exatamente as mesmas chaves;
2. todo scope de throttle USADO em views (`throttle_scope = "..."` ou `scope = "..."`
   numa classe *Throttle) tem rate definido em `DEFAULT_THROTTLE_RATES`.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import ast
from pathlib import Path

from django.conf import settings


def _throttle_base_name(base: ast.expr) -> str:
    """Nome da classe-base (Name `UserRateThrottle` ou Attribute `throttling.UserRateThrottle`)."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def _str_const(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _assign_targets_value(node: ast.AST) -> tuple[list[ast.expr], ast.expr | None]:
    """Normaliza Assign (`x = v`) e AnnAssign (`x: T = v`) para (targets, value).

    Cobrir AnnAssign importa: num codebase Pyright-strict, `throttle_scope: str = "x"`
    e `scope: ClassVar[str] = "x"` sao idiomaticos e nao seriam `ast.Assign`.
    """
    if isinstance(node, ast.Assign):
        return node.targets, node.value
    if isinstance(node, ast.AnnAssign):
        return [node.target], node.value  # value pode ser None (anotacao pura)
    return [], None


def _collect_used_scopes() -> set[str]:
    """Varre apps/**/*.py (menos testes) coletando scopes de throttle efetivamente usados.

    Cobre `throttle_scope = "X"` / `throttle_scope: str = "X"` / `foo.throttle_scope = "X"`
    e `scope = "X"` / `scope: ... = "X"` dentro de classes custom `*Throttle`.
    """
    apps_dir = Path(settings.BASE_DIR) / "apps"
    scopes: set[str] = set()
    for py in apps_dir.rglob("*.py"):
        posix = py.as_posix()
        if "/tests/" in posix or py.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # `throttle_scope = "X"` (atributo de view) OU `foo.throttle_scope = "X"`.
            targets, value = _assign_targets_value(node)
            for tgt in targets:
                name = tgt.id if isinstance(tgt, ast.Name) else tgt.attr if isinstance(tgt, ast.Attribute) else None
                if name == "throttle_scope":
                    literal = _str_const(value)
                    if literal:
                        scopes.add(literal)
            # `scope = "X"` dentro de uma classe custom *Throttle (LoginThrottle, OAuthThrottle...).
            if isinstance(node, ast.ClassDef) and any(_throttle_base_name(b).endswith("Throttle") for b in node.bases):
                for stmt in node.body:
                    s_targets, s_value = _assign_targets_value(stmt)
                    if any(isinstance(t, ast.Name) and t.id == "scope" for t in s_targets):
                        literal = _str_const(s_value)
                        if literal:
                            scopes.add(literal)
    return scopes


def _throttle_rate_dicts_from_source() -> list[set[str]]:
    """Chaves de cada dict literal de throttle no settings.py (identificado por conter anon+user)."""
    src = (Path(settings.BASE_DIR) / "config" / "settings.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    dicts: list[set[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = {v for v in (_str_const(k) for k in node.keys) if v is not None}
            if {"anon", "user"} <= keys:
                dicts.append(keys)
    return dicts


def test_dicts_base_e_dev_de_throttle_tem_as_mesmas_chaves():
    """O bloco `if ENVIRONMENT==development` SUBSTITUI o dict inteiro -> chaves devem casar."""
    dicts = _throttle_rate_dicts_from_source()
    assert len(dicts) >= 2, "esperava >= 2 dicts DEFAULT_THROTTLE_RATES (base + override de dev)"
    base = dicts[0]
    for other in dicts[1:]:
        diff = base ^ other
        assert not diff, (
            f"DEFAULT_THROTTLE_RATES base e dev divergem nas chaves: {sorted(diff)}. "
            "Como o override de dev substitui o dict inteiro, TODA chave precisa existir "
            "nos dois blocos (senao o scope some em um dos ambientes)."
        )


def test_todo_scope_de_throttle_usado_tem_rate_definido():
    """Scope usado numa view sem rate no dict = 'No default throttle rate set' em runtime."""
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    used = _collect_used_scopes()
    assert used, "nao encontrei nenhum scope de throttle usado — o coletor pode ter quebrado"
    missing = used - set(rates)
    assert not missing, (
        f"Scopes de throttle usados em views sem rate em DEFAULT_THROTTLE_RATES: {sorted(missing)}. "
        "Adicione o rate no dict base E no override de dev (config/settings.py)."
    )
