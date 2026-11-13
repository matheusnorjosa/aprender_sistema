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

from django.db.models import Q
from django.utils import timezone

# Chaves de contagem expostas na trilha de auditoria (o FATO, nunca a PII).
COUNT_KEYS = (
    "solicitations_created",
    "event_participations",
    "events_as_responsible",
    "events_as_formador_to_evaluate",
    "availability_blocks",
    "approvals_made",
)

# Campos do evento nas secoes que listam eventos pelo titular. A observacao do evento fica de fora: e texto
# livre de quem criou e pode citar outras pessoas.
_CAMPOS_DO_EVENTO = (
    "id",
    "status",
    "inicio",
    "fim",
    "municipio__nome",
    "projeto__nome",
    "projeto_2__nome",
    "tipo_evento__nome",
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
    from apps.core.models import (
        AuditLog,
        AvailabilityBlock,
        DATCoordenador,
        GoogleOAuthCredential,
        Participation,
        Solicitacao,
    )

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
            "projeto_2__nome",  # evento de dois projetos (#2036)
            "tipo_evento__nome",
            "created_at",
            "updated_at",
        )
    )

    # Eventos em que o titular participa, em qualquer papel (ART-17). A participacao mora em
    # `Participation`; o M2M `Solicitacao.formadores` nao e gravado pela API (0 linhas em producao em
    # 13/11/2026). So a linha do proprio titular: a observacao de outros participantes nao entra, nem a
    # observacao do evento.
    data["event_participations"] = list(
        Participation.objects.filter(usuario=user)
        .order_by("solicitacao__inicio", "solicitacao_id", "role")
        .values(
            "solicitacao_id",
            "role",
            "ch_horas",
            "observacao",
            "created_at",
            "solicitacao__status",
            "solicitacao__inicio",
            "solicitacao__fim",
            "solicitacao__municipio__nome",
            "solicitacao__projeto__nome",
            "solicitacao__projeto_2__nome",
            "solicitacao__tipo_evento__nome",
        )
    )

    # Eventos em que o titular e o coordenador responsavel ou o formador que quem criou pretende avaliar
    # (FK `formador_avaliado`; e intencao, nao avaliacao feita, e so o dossie a mostra ao formador):
    # fatos sobre a pessoa que nao dependem de `Participation` (o admin do Django troca a FK sem acertar
    # a participacao). Responsavel segue a regra de Meus eventos, da agenda e das horas: a FK `coordenador`
    # ou, sem ela, quem criou. O mesmo evento pode sair tambem em `event_participations` e em
    # `solicitations_created`.
    data["events_as_responsible"] = list(
        Solicitacao.objects.filter(Q(coordenador=user) | Q(coordenador__isnull=True, usuario=user))
        .order_by("inicio", "id")
        .values(*_CAMPOS_DO_EVENTO, "coordenador_acompanha")
    )
    data["events_as_formador_to_evaluate"] = list(
        Solicitacao.objects.filter(formador_avaliado=user).order_by("inicio", "id").values(*_CAMPOS_DO_EVENTO)
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

    # DATCoordenador casado por CPF (opcao A #1837): paridade acesso<->erasure. Se a
    # anonimizacao alcanca o coordenador por CPF, o dossie de acesso precisa inclui-lo —
    # senao o sistema apaga dado que se recusa a divulgar. Match so' com 11 digitos.
    cpf_digits = "".join(ch for ch in str(user.cpf or "") if ch.isdigit())
    data["dat_coordenador_records"] = (
        list(DATCoordenador.objects.filter(cpf=cpf_digits).values("id", "nome", "area", "email", "telefone", "cargo"))
        if len(cpf_digits) == 11
        else []
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
                # A credencial nao guarda o ultimo uso: `updated_at` e a ultima renovacao ou alteracao.
                "updated_at": gcal_cred.updated_at.isoformat(),
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
