"""AS v2 — Serviço de exportação de dados do titular (LGPD art. 18-V, portabilidade).

SSOT do "dossiê de um titular": tanto o command `lgpd_export` (ferramenta de admin/DPO)
quanto o endpoint self-service `GET /api/me/export/` chamam `build_lgpd_export_data`. Um
único lugar evita o field-drift que já matou o `lgpd_export` (duas cópias divergem e
apodrecem). O serviço só MONTA o dossiê — I/O (arquivo/HTTP) e a trilha de auditoria são
responsabilidade do caller (contexto diferente: admin CLI vs. titular autenticado).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from django.utils import timezone

# Chaves de contagem expostas na trilha de auditoria (o FATO, nunca a PII).
COUNT_KEYS = (
    "solicitations_created",
    "events_as_formador",
    "availability_blocks",
    "approvals_made",
)


def _serialize(obj: Any) -> Any:
    """Converte recursivamente datetime/date/time/Decimal para tipos JSON."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def build_lgpd_export_data(user: Any, *, include_audit: bool = True, include_gcal: bool = False) -> dict[str, Any]:
    """Monta o dossiê LGPD de `user` (JSON-serializável).

    `include_audit`: inclui as últimas 100 entradas de AuditLog do usuário.
    `include_gcal`: inclui METADADOS da credencial Google (nunca os tokens).
    """
    from apps.core.models import AuditLog, AvailabilityBlock, GoogleOAuthCredential, Solicitacao

    data: dict[str, Any] = {
        "export_info": {
            "generated_at": timezone.now().isoformat(),
            "system": "Aprender Sistema v2",
            "purpose": "LGPD Data Portability (Art. 18, V)",
        },
        "personal_data": {
            "id": user.id,
            "username": user.username,
            "cpf": user.cpf,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "cargo": getattr(user, "cargo", None),
            "matricula": getattr(user, "matricula", None),
            "telefone": getattr(user, "telefone", None),
            "setores": list(user.setores) if hasattr(user, "setores") else [],
            "funcoes": list(user.funcoes) if hasattr(user, "funcoes") else [],
            "groups": list(user.groups.values_list("name", flat=True)),
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
    }

    # Solicitacoes criadas pelo titular. Campos reais: usuario/inicio/fim.
    data["solicitations_created"] = list(
        Solicitacao.objects.filter(usuario=user).values(
            "id",
            "status",
            "inicio",
            "fim",
            "municipio__nome",
            "projeto__nome",
            "tipo_evento__nome",
            "created_at",
            "updated_at",
        )
    )

    # Eventos onde o titular e' formador (formadores = M2M com Usuario).
    data["events_as_formador"] = list(
        Solicitacao.objects.filter(formadores=user).values(
            "id",
            "status",
            "inicio",
            "fim",
            "municipio__nome",
        )
    )

    # Blocos de disponibilidade (dono = `usuario`, nao `formador`).
    data["availability_blocks"] = list(
        AvailabilityBlock.objects.filter(usuario=user).values(
            "id",
            "tipo",
            "inicio",
            "fim",
            "motivo",
            "created_at",
        )
    )

    # Aprovacoes feitas pelo titular (do AuditLog).
    data["approvals_made"] = list(
        AuditLog.objects.filter(
            usuario=user,
            action__in=["APROVAR", "APPROVE", "REPROVAR", "REJECT"],
        )
        .order_by("-created_at")[:50]
        .values("id", "action", "details", "created_at")
    )

    if include_audit:
        data["audit_logs"] = list(
            AuditLog.objects.filter(usuario=user)
            .order_by("-created_at")[:100]
            .values("id", "action", "model_name", "details", "created_at")
        )
    else:
        data["audit_logs"] = "(excluded from export)"

    if include_gcal:
        gcal_cred = GoogleOAuthCredential.objects.filter(user=user).first()
        if gcal_cred:
            data["gcal_credentials"] = {
                "has_credential": True,
                "google_email": gcal_cred.google_email,
                "created_at": gcal_cred.created_at.isoformat(),
                "last_used_at": (gcal_cred.last_used_at.isoformat() if gcal_cred.last_used_at else None),
                "tokens": "(excluded for security)",
            }
        else:
            data["gcal_credentials"] = None
    else:
        data["gcal_credentials"] = "(excluded from export)"

    return _serialize(data)


def export_counts(data: dict[str, Any]) -> dict[str, int]:
    """Contagens por seção para a trilha de auditoria (o FATO, nunca a PII)."""
    return {key: len(data[key]) for key in COUNT_KEYS if isinstance(data.get(key), list)}
