from django.utils import timezone as tz
from core.services.integrations.calendar_types import GoogleEvent, GoogleAttendee

def _fmt_dt(dt):
    # garante ISO-8601 com timezone
    return tz.localtime(dt).isoformat()

def map_solicitacao_to_google_event(solic):
    # Campos principais
    summary = f"{solic.tipo_evento.nome} — {solic.titulo_evento}"
    # Descrição rica (ajuste conforme seu modelo)
    descr_parts = [
        f"Projeto: {solic.projeto.nome}",
        f"Municipio: {getattr(solic.municipio, 'nome', '')}",
        f"Solicitante: {solic.usuario_solicitante.get_full_name() or solic.usuario_solicitante.username}",
    ]
    if hasattr(solic, "observacoes") and solic.observacoes:
        descr_parts.append(f"Observações: {solic.observacoes}")
    description = "\n".join(descr_parts)

    # Participantes (formadores como attendees)
    attendees = []
    for f in solic.formadores.all():
        attendees.append(GoogleAttendee(email=f.email or "", display_name=f.nome or ""))

    location = getattr(solic.municipio, "nome", None)
    return GoogleEvent(
        summary=summary,
        description=description,
        start_iso=_fmt_dt(solic.data_inicio),
        end_iso=_fmt_dt(solic.data_fim),
        location=location,
        attendees=attendees,
        conference=True,
    )