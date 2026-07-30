"""
Service para importacao de Usuarios via upload.

Padrao: dry_run + CPF para idempotencia (campo unico).

Colunas esperadas:
- cpf (obrigatorio): 11 digitos
- nome (obrigatorio): nome completo (first_name + last_name)
- email (opcional): email do usuario
- telefone (opcional): telefone
- cargo (opcional): cargo/funcao
- is_active (opcional): ativo/inativo (default: True)
- grupos (opcional): grupos separados por virgula — so aplicado quando o ator
  e superusuario (ver `_actor_pode_atribuir_grupos`); nos demais casos a coluna
  e ignorada e reportada em `pendencias["grupos_ignorados"]`. Nome de grupo que
  nao existe no banco sai em `pendencias["grupos_desconhecidos"]`, identico em
  dry_run e no apply.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import re
import secrets
import string
from pathlib import Path
from typing import Any

from django.contrib.auth.models import Group
from django.db import transaction

import pandas as pd

from apps.core.imports.normalization import normalize_active_flag, normalize_blank, normalize_cpf_digits
from apps.core.models import Usuario


def import_usuarios_from_file(*, path: str, dry_run: bool = True, actor: Any = None) -> dict[str, Any]:
    """
    Importa usuarios de CSV/XLSX.

    Args:
        path: Caminho do arquivo CSV/XLSX
        dry_run: Se True, nao persiste (rollback)
        actor: Usuario que disparou a importacao. Decide se a coluna `grupos`
            vale (ver `_actor_pode_atribuir_grupos`). Fail-closed: sem ator,
            nenhum grupo e atribuido.

    Returns:
        {
            "stats": {"created": N, "updated": N, "unchanged": N,
                      "grupos_ignorados": N, "grupos_desconhecidos": N,
                      "skipped": {...}},
            "pendencias": {"cpf_invalid": [...], "nome_missing": [...],
                           "grupos_ignorados": [...], "grupos_desconhecidos": [...],
                           "outros": [...]},
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "grupos_ignorados": 0,
        "grupos_desconhecidos": 0,
        "skipped": {"cpf_invalid": 0, "nome_missing": 0, "superuser_protected": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "cpf_invalid": [],
        "nome_missing": [],
        "superuser_protected": [],
        "grupos_ignorados": [],
        "grupos_desconhecidos": [],
        "outros": [],
    }

    # Carregar arquivo
    rows = _load_file(path)

    # Processar linhas.
    # ASQ-016: savepoint-per-row. Outer atomic still owns the dry-run
    # rollback; inner atomic isolates one bad row from the rest.
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():  # savepoint
                    _process_row(row, idx, stats, pendencias, dry_run, actor)
            except Exception as e:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append(
                    {
                        "linha": idx,
                        "erro": str(e),
                        "row": str(row),
                    }
                )

        if dry_run:
            transaction.set_rollback(True)

    return {
        "stats": stats,
        "pendencias": pendencias,
        "dry_run": dry_run,
        "file": path,
    }


def _load_file(path: str) -> list[dict[str, Any]]:
    """Carrega CSV ou XLSX com headers flexiveis."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(file_path, dtype=str)
    else:
        df = pd.read_excel(file_path, dtype=str)

    df = df.fillna("")
    df = df.dropna(how="all")

    rows = []
    for _, row in df.iterrows():
        normalized = _normalize_row(row)
        rows.append(normalized)

    return rows


def _normalize_row(row: Any) -> dict[str, Any]:
    """Normaliza headers do arquivo para padrao interno."""
    normalized: dict[str, Any] = {}

    # Criar mapa lower -> valor
    row_dict = row.to_dict()
    lower_map = {str(k).strip().lower(): v for k, v in row_dict.items()}

    # CPF
    for key in ["cpf", "documento", "cpf_usuario", "cpf_formador"]:
        if key in lower_map:
            normalized["cpf"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["cpf"] = ""

    # Nome completo
    for key in ["nome", "nome_completo", "name", "full_name", "nome_formador"]:
        if key in lower_map:
            normalized["nome"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["nome"] = ""

    # Email
    for key in ["email", "e-mail", "mail", "correio"]:
        if key in lower_map:
            normalized["email"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["email"] = ""

    # Telefone
    for key in ["telefone", "tel", "celular", "phone", "fone"]:
        if key in lower_map:
            normalized["telefone"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["telefone"] = ""

    # Cargo
    for key in ["cargo", "funcao", "função", "function", "role"]:
        if key in lower_map:
            normalized["cargo"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["cargo"] = ""

    # Status ativo — considera ativo por padrao, inativo apenas se explicitamente marcado
    for key in ["ativo", "is_active", "active", "status"]:
        if key in lower_map:
            normalized["is_active"] = normalize_active_flag(lower_map[key])
            break
    else:
        normalized["is_active"] = True

    # Grupos (separados por virgula)
    for key in ["grupos", "groups", "perfis", "profiles", "grupo", "perfil"]:
        if key in lower_map:
            normalized["grupos"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["grupos"] = ""

    return normalized


def _clean_cpf(cpf: str) -> str:
    """Remove formatacao do CPF (pontos, tracos, espacos).

    Compat wrapper preserved for callers within this module. Delegates to
    :func:`apps.core.imports.normalization.normalize_cpf_digits` —
    byte-equivalent for ASCII CPF inputs.
    """
    return normalize_cpf_digits(cpf)


def _validate_cpf(cpf: str) -> bool:
    """Valida se CPF tem 11 digitos numericos."""
    cleaned = _clean_cpf(cpf)
    return len(cleaned) == 11 and cleaned.isdigit()


def _parse_name(nome: str) -> tuple[str, str]:
    """Divide nome completo em first_name e last_name."""
    parts = nome.strip().split(maxsplit=1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    return first_name, last_name


def _generate_password(length: int = 12) -> str:
    """Gera senha aleatoria segura."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_username(cpf: str, email: str) -> str:
    """Gera username unico a partir do email ou CPF."""
    if email and "@" in email:
        base = email.split("@")[0]
        # Limpar caracteres invalidos
        base = re.sub(r"[^\w.]", "", base)
        if base:
            # Verificar se ja existe
            username = base
            counter = 1
            while Usuario.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1
            return username

    # Fallback: usar CPF
    username = f"user_{cpf}"
    counter = 1
    while Usuario.objects.filter(username=username).exists():
        username = f"user_{cpf}_{counter}"
        counter += 1
    return username


def _actor_pode_atribuir_grupos(actor: Any) -> bool:
    """Atribuir grupo e conceder privilegio, entao e exclusivo de superusuario.

    Mesma regra de `UsuarioAdminSerializer._actor_is_superuser` (P0-1, #1567):
    o import e um segundo caminho de escrita para a mesma coisa e precisa do
    mesmo gate. `manage_admin_registries` — a capability que abre o endpoint —
    e operacional (cadastro), nao Tier-0.

    Fail-closed: sem ator identificado, nenhum grupo e atribuido.
    """
    return bool(actor is not None and getattr(actor, "is_superuser", False))


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    dry_run: bool,
    actor: Any = None,
) -> None:
    """Processa uma linha do arquivo."""
    # Validar CPF
    cpf_raw = row.get("cpf", "")
    cpf = _clean_cpf(cpf_raw)

    if not _validate_cpf(cpf_raw):
        stats["skipped"]["cpf_invalid"] += 1
        pendencias["cpf_invalid"].append(
            {
                "linha": linha_num,
                "cpf": cpf_raw,
                "erro": "CPF invalido (deve ter 11 digitos)",
            }
        )
        return

    # Validar nome
    nome = row.get("nome", "").strip()
    if not nome:
        stats["skipped"]["nome_missing"] += 1
        pendencias["nome_missing"].append(
            {
                "linha": linha_num,
                "cpf": cpf,
                "erro": "Nome obrigatorio",
            }
        )
        return

    first_name, last_name = _parse_name(nome)
    email = row.get("email", "").strip()
    telefone = row.get("telefone", "").strip()
    cargo = row.get("cargo", "").strip()
    is_active = row.get("is_active", True)
    grupos_str = row.get("grupos", "").strip()

    # Verificar existencia por CPF (idempotencia)
    existing = Usuario.objects.filter(cpf=cpf).first()

    # P0-0 (Tier-0, auditoria 2026-07-17): importacao em lote NUNCA altera conta
    # superuser (senha/is_active/grupos/cadastrais). Um CSV nao e caminho
    # legitimo para mexer em privilegio Tier-0 — protecao incondicional.
    if existing is not None and existing.is_superuser:
        stats["skipped"]["superuser_protected"] += 1
        pendencias["superuser_protected"].append(
            {
                "linha": linha_num,
                "cpf": cpf,
                "erro": "Conta de superusuario nao pode ser alterada por importacao.",
            }
        )
        return

    # P0 Tier-0 (auditoria 2026-07-18): a coluna `grupos` concede privilegio —
    # inclusive autoridade de aprovacao (PA-01) — e nao cadastro. Quem nao e
    # superusuario importa dados, nunca privilegio. Decidido uma vez por linha
    # para que o relatorio saia identico em dry_run e no apply: o preview nao
    # pode prometer o que o apply nao faz.
    aplicar_grupos = bool(grupos_str) and _actor_pode_atribuir_grupos(actor)
    if grupos_str and not aplicar_grupos:
        stats["grupos_ignorados"] += 1
        pendencias["grupos_ignorados"].append(
            {
                "linha": linha_num,
                "cpf": cpf,
                "grupos": grupos_str,
                "erro": "Coluna 'grupos' ignorada: atribuicao de grupo e exclusiva de superusuario.",
            }
        )

    # Resolver os nomes ANTES de decidir persistir. Antes, dry_run nem consultava
    # o banco: era estruturalmente incapaz de avisar sobre um nome que o apply ia
    # descartar calado. Resolver aqui da a paridade e mata o silencio de uma vez.
    #
    # Nao resolvemos para ator sem autoridade: a coluna inteira ja foi ignorada, e
    # dizer "esse grupo nao existe" vazaria quais grupos existem para quem nao
    # manda neles.
    grupos_encontrados: list[Group] = []
    if aplicar_grupos:
        grupos_encontrados, grupos_desconhecidos = _resolve_grupos(grupos_str)
        if grupos_desconhecidos:
            stats["grupos_desconhecidos"] += 1
            pendencias["grupos_desconhecidos"].append(
                {
                    "linha": linha_num,
                    "cpf": cpf,
                    "grupos": grupos_desconhecidos,
                    "erro": "Grupo nao encontrado; os demais grupos da linha foram aplicados.",
                }
            )

    if existing:
        # Atualizar campos se houver mudancas
        updated = False
        update_fields = []

        if email and existing.email != email:
            existing.email = email
            updated = True
            update_fields.append("email")

        if telefone and existing.telefone != telefone:
            existing.telefone = telefone
            updated = True
            update_fields.append("telefone")

        if cargo and existing.cargo != cargo:
            existing.cargo = cargo
            updated = True
            update_fields.append("cargo")

        if first_name and existing.first_name != first_name:
            existing.first_name = first_name
            updated = True
            update_fields.append("first_name")

        if last_name and existing.last_name != last_name:
            existing.last_name = last_name
            updated = True
            update_fields.append("last_name")

        if existing.is_active != is_active:
            existing.is_active = is_active
            updated = True
            update_fields.append("is_active")

        if updated:
            if not dry_run:
                existing.save(update_fields=update_fields)
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1

        # Atualizar grupos mesmo se nao houve outras mudancas
        if aplicar_grupos and not dry_run:
            _assign_groups(existing, grupos_encontrados, actor=actor)

    else:
        # Criar novo usuario
        username = _generate_username(cpf, email)
        password = _generate_password()

        if not dry_run:
            usuario = Usuario.objects.create(
                cpf=cpf,
                username=username,
                email=email if email else f"{cpf}@placeholder.local",
                first_name=first_name,
                last_name=last_name,
                telefone=telefone,
                cargo=cargo,
                is_active=is_active,
            )
            usuario.set_password(password)
            usuario.save(update_fields=["password"])

            # Atribuir grupos
            if aplicar_grupos:
                _assign_groups(usuario, grupos_encontrados, actor=actor)

        stats["created"] += 1


def _resolve_grupos(grupos_str: str) -> tuple[list[Group], list[str]]:
    """Resolve nomes de grupo (comma-separated, case-insensitive) em objetos.

    Devolve `(encontrados, desconhecidos)`. Chamada tanto em dry_run quanto no
    apply, para que o preview enxergue exatamente o que o apply fara — inclusive
    os nomes que serao descartados.
    """
    encontrados: list[Group] = []
    desconhecidos: list[str] = []

    for nome_grupo in [g.strip() for g in grupos_str.split(",") if g.strip()]:
        grupo = Group.objects.filter(name__iexact=nome_grupo).first()
        if grupo is None:
            desconhecidos.append(nome_grupo)
        elif grupo not in encontrados:
            encontrados.append(grupo)

    return encontrados, desconhecidos


def _assign_groups(usuario: Usuario, grupos: list[Group], *, actor: Any = None) -> None:
    """Vincula os grupos ja resolvidos ao usuario.

    O gate de `actor` e repetido aqui de proposito: esta e a primitiva que
    escreve privilegio, e nao deve depender do chamador lembrar de verificar.
    Resolver nomes e reportar o que foi descartado sao responsabilidade de
    `_resolve_grupos` / `_process_row`, que tem o contexto do relatorio.
    """
    if not _actor_pode_atribuir_grupos(actor):
        return

    if grupos:
        # `add` e idempotente para M2M — nao precisa checar pertinencia antes.
        usuario.groups.add(*grupos)
