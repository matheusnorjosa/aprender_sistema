"""
Service para importacao de EquipeGerencia via upload.

Padrao: dry_run + (gerencia, usuario, papel) para idempotencia.

Colunas esperadas (flexiveis):
- setor / gerencia (obrigatorio): nome do setor
- papel / funcao (obrigatorio): GERENTE, COORDENADOR, APOIO, FORMADOR
- usuario_cpf / cpf (opcional)
- usuario_email / email (opcional)
- usuario_nome / nome (opcional)
- coordenador_supervisor (opcional, obrigatorio apenas para papel APOIO)
- ativo (opcional): se a atribuicao esta ativa (default: True)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db import transaction

import pandas as pd

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.services.resolvers import resolve_user_by_email, resolve_user_by_name

# Mapeamento de nomes de setor -> nome_setor canonico
SETOR_MAPPING = {
    "Superintendência": "Superintendência",
    "Super": "Superintendência",
    "SUPER": "Superintendência",
    "Brincando e Aprendendo": "Brincando e Aprendendo",
    "Brincando": "Brincando e Aprendendo",
    "ACerta": "ACerta",
    "Acerta": "ACerta",
    "ACERTA": "ACerta",
    "Fluir das Emoções": "Fluir",
    "Fluir": "Fluir",
    "FLUIR": "Fluir",
    "Vidas": "Vidas",
    "VIDAS": "Vidas",
    "A Cor da Gente": "A Cor da Gente",
    "Sou da Paz": "Sou da Paz",
    "Educação Financeira": "Educação Financeira",
    "Ed Financeira": "Educação Financeira",
    "Ler, Ouvir e Contar": "Ler, Ouvir e Contar",
    "Ler Ouvir e Contar": "Ler, Ouvir e Contar",
    "Avançando Juntos": "Avançando Juntos",
    "IDEB10": "IDEB10",
    "My Companion": "My Companion",
}

# Mapeamento de nome de papel -> papel canonico
PAPEL_MAPPING = {
    "Gerentes": "GERENTE",
    "Gerente": "GERENTE",
    "GERENTE": "GERENTE",
    "Coordenadores": "COORDENADOR",
    "Coordenador": "COORDENADOR",
    "COORDENADOR": "COORDENADOR",
    "Apoio de Coordenação": "APOIO",
    "Apoio": "APOIO",
    "APOIO": "APOIO",
    "Formadores": "FORMADOR",
    "Formador": "FORMADOR",
    "FORMADOR": "FORMADOR",
}


def import_equipe_gerencia_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa equipe/gerencia de CSV/XLSX.

    Returns:
        {
            "stats": {"created": N, "updated": N, "unchanged": N, "skipped": {...},
                      "gerencias_created": N, "gerencias_existing": N},
            "pendencias": {"setor_missing": [...], "papel_missing": [...], "usuario_not_found": [...],
                           "apoio_supervisor_missing": [...], "outros": [...]},
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {
            "setor_missing": 0,
            "papel_missing": 0,
            "usuario_not_found": 0,
            "apoio_supervisor_missing": 0,
            "other": 0,
        },
        "gerencias_created": 0,
        "gerencias_existing": 0,
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "setor_missing": [],
        "papel_missing": [],
        "usuario_not_found": [],
        "apoio_supervisor_missing": [],
        "outros": [],
    }

    rows = _load_file(path)

    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                _process_row(row, idx, stats, pendencias)
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
        df = pd.read_csv(file_path, dtype=str, encoding="utf-8-sig")
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

    row_dict = row.to_dict()
    lower_map = {str(k).strip().lower(): v for k, v in row_dict.items()}

    # Setor / Gerencia
    for key in ["setor", "gerencia", "gerência", "nome_setor", "setor_nome"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["setor"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["setor"] = ""

    # Papel / Funcao
    for key in ["papel", "funcao", "função", "role", "cargo"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["papel"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["papel"] = ""

    # Usuario identificadores
    for key in ["usuario_cpf", "cpf", "documento", "doc"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["usuario_cpf"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["usuario_cpf"] = ""

    for key in ["usuario_email", "email", "e-mail"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["usuario_email"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["usuario_email"] = ""

    for key in ["usuario_nome", "nome", "nome_completo", "usuario"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["usuario_nome"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["usuario_nome"] = ""

    # Coordenador supervisor (apenas para APOIO)
    for key in ["coordenador_supervisor", "supervisor", "coordenador"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["coordenador_supervisor"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["coordenador_supervisor"] = ""

    # Status ativo
    for key in ["ativo", "is_active", "active", "status"]:
        if key in lower_map:
            val = lower_map[key]
            val_str = str(val).strip().lower() if val and str(val) != "nan" else ""
            normalized["is_active"] = val_str not in ("nao", "não", "false", "0", "inativo", "n")
            break
    else:
        normalized["is_active"] = True

    return normalized


def _generate_gerencia_nome(nome_setor: str) -> str:
    """Gera nome de gerencia baseado no setor."""
    mapping = {
        "Superintendência": "SUPERINTENDENCIA",
        "Brincando e Aprendendo": "GERENCIA BRINCANDO",
        "ACerta": "GERENCIA ACERTA",
        "Fluir": "GERENCIA FLUIR",
        "Vidas": "GERENCIA VIDAS",
        "A Cor da Gente": "GERENCIA A COR DA GENTE",
        "Sou da Paz": "GERENCIA SOU DA PAZ",
        "Educação Financeira": "GERENCIA ED FINANCEIRA",
        "Ler, Ouvir e Contar": "GERENCIA LER OUVIR E CONTAR",
        "Avançando Juntos": "GERENCIA AVANCANDO JUNTOS",
        "IDEB10": "GERENCIA IDEB10",
        "My Companion": "GERENCIA MY COMPANION",
    }
    return mapping.get(nome_setor, f"GERENCIA {nome_setor.upper()}")


def _get_or_create_gerencia(nome_setor: str, stats: dict[str, Any]) -> Gerencia | None:
    """Obtém ou cria uma Gerencia pelo nome do setor."""
    nome_setor = SETOR_MAPPING.get(nome_setor, nome_setor)
    nome_gerencia = _generate_gerencia_nome(nome_setor)

    gerencia = Gerencia.objects.filter(nome_setor__iexact=nome_setor).first()
    if gerencia:
        stats["gerencias_existing"] += 1
        return gerencia

    gerencia = Gerencia.objects.filter(nome__iexact=nome_setor).first()
    if gerencia:
        stats["gerencias_existing"] += 1
        return gerencia

    gerencia = Gerencia.objects.filter(nome__iexact=nome_gerencia).first()
    if gerencia:
        stats["gerencias_existing"] += 1
        return gerencia

    gerencia, created = Gerencia.objects.get_or_create(
        nome=nome_gerencia,
        defaults={
            "nome_setor": nome_setor,
            "ativo": True,
        },
    )
    if created:
        stats["gerencias_created"] += 1
    else:
        stats["gerencias_existing"] += 1
    return gerencia


def _resolve_usuario(cpf: str, email: str, nome: str) -> Usuario | None:
    """Resolve usuario por CPF > email > nome."""
    cpf_norm = "".join([c for c in cpf if c.isdigit()])
    if cpf_norm:
        user = Usuario.objects.filter(cpf=cpf_norm).first()
        if user:
            return user

    if email:
        user = resolve_user_by_email(email)
        if user:
            return user

    if nome:
        user = resolve_user_by_name(nome)
        if user:
            return user

    return None


def _resolve_usuario_from_value(value: str) -> Usuario | None:
    """Resolve usuario a partir de um unico valor (cpf/email/nome)."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    if "@" in value:
        return resolve_user_by_email(value)

    digits = "".join([c for c in value if c.isdigit()])
    if len(digits) >= 11:
        user = Usuario.objects.filter(cpf=digits).first()
        if user:
            return user

    return resolve_user_by_name(value)


def _resolve_papel(raw: str) -> str:
    if not raw:
        return ""
    if raw in PAPEL_MAPPING:
        return PAPEL_MAPPING[raw]
    # Normalizar por upper
    upper = raw.upper()
    if upper in PAPEL_MAPPING:
        return PAPEL_MAPPING[upper]
    return upper


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
) -> None:
    """Processa um registro de equipe/gerencia."""
    setor_raw = row.get("setor", "").strip()
    papel_raw = row.get("papel", "").strip()

    if not setor_raw:
        stats["skipped"]["setor_missing"] += 1
        pendencias["setor_missing"].append({"linha": linha_num, "erro": "Setor/gerencia ausente"})
        return

    if not papel_raw:
        stats["skipped"]["papel_missing"] += 1
        pendencias["papel_missing"].append({"linha": linha_num, "erro": "Papel/funcao ausente"})
        return

    setor = SETOR_MAPPING.get(setor_raw, setor_raw)
    papel = _resolve_papel(papel_raw)

    if papel not in {"GERENTE", "COORDENADOR", "APOIO", "FORMADOR"}:
        stats["skipped"]["papel_missing"] += 1
        pendencias["papel_missing"].append(
            {"linha": linha_num, "erro": f"Papel invalido: {papel_raw}", "papel": papel_raw}
        )
        return

    gerencia = _get_or_create_gerencia(setor, stats)
    if not gerencia:
        stats["skipped"]["setor_missing"] += 1
        pendencias["setor_missing"].append(
            {"linha": linha_num, "erro": "Gerencia nao encontrada", "setor": setor}
        )
        return

    usuario = _resolve_usuario(
        row.get("usuario_cpf", "").strip(),
        row.get("usuario_email", "").strip(),
        row.get("usuario_nome", "").strip(),
    )
    if not usuario:
        stats["skipped"]["usuario_not_found"] += 1
        pendencias["usuario_not_found"].append(
            {
                "linha": linha_num,
                "setor": setor,
                "papel": papel,
                "usuario_nome": row.get("usuario_nome", "").strip(),
                "usuario_email": row.get("usuario_email", "").strip(),
                "usuario_cpf": row.get("usuario_cpf", "").strip(),
            }
        )
        return

    supervisor: Usuario | None = None
    if papel == "APOIO":
        supervisor_val = row.get("coordenador_supervisor", "").strip()
        supervisor = _resolve_usuario_from_value(supervisor_val) if supervisor_val else None
        if not supervisor:
            stats["skipped"]["apoio_supervisor_missing"] += 1
            pendencias["apoio_supervisor_missing"].append(
                {
                    "linha": linha_num,
                    "setor": setor,
                    "usuario_nome": row.get("usuario_nome", "").strip(),
                    "erro": "APOIO requer coordenador_supervisor valido",
                }
            )
            return

    is_active = bool(row.get("is_active", True))

    existing = EquipeGerencia.objects.filter(gerencia=gerencia, usuario=usuario, papel=papel).first()
    if existing:
        updated = False
        update_fields = []

        if papel == "APOIO" and supervisor and existing.coordenador_supervisor_id != supervisor.id:
            existing.coordenador_supervisor = supervisor
            updated = True
            update_fields.append("coordenador_supervisor")

        if existing.ativo != is_active:
            existing.ativo = is_active
            updated = True
            update_fields.append("ativo")

        if updated:
            existing.save(update_fields=update_fields)
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
        return

    EquipeGerencia.objects.create(
        gerencia=gerencia,
        usuario=usuario,
        papel=papel,
        coordenador_supervisor=supervisor,
        ativo=is_active,
    )
    stats["created"] += 1
