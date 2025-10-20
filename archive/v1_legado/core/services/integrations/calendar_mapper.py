from django.utils import timezone as tz

from core.services.integrations.calendar_types import GoogleAttendee, GoogleEvent


def _fmt_dt(dt):
    # garante ISO-8601 com timezone
    return tz.localtime(dt).isoformat()


def map_solicitacao_to_google_event(solic):
    # Campos principais - incluir [FORMAÇÕES] para facilitar identificação
    summary = f"[FORMAÇÕES] {solic.tipo_evento.nome} — {solic.titulo_evento}"

    # Descrição rica (ajuste conforme seu modelo)
    descr_parts = [
        f"🎯 Projeto: {solic.projeto.nome}",
        f"📍 Município: {getattr(solic.municipio, 'nome', '')}",
        f"👤 Solicitante: {solic.usuario_solicitante.get_full_name() or solic.usuario_solicitante.username}",
        f"🔢 ID Solicitação: {solic.id}",
    ]

    # Formadores na descrição
    formadores_nomes = [f.nome for f in solic.formadores.all()]
    if formadores_nomes:
        descr_parts.append(f"👨‍🏫 Formadores: {', '.join(formadores_nomes)}")

    if hasattr(solic, "observacoes") and solic.observacoes:
        descr_parts.append(f"📝 Observações: {solic.observacoes}")

    descr_parts.append("\n✅ Criado via Sistema Aprender")
    description = "\n".join(descr_parts)

    # Participantes (formadores como attendees)
    attendees = []
    for f in solic.formadores.all():
        if f.email:  # Só adicionar se tiver email
            attendees.append(GoogleAttendee(email=f.email, display_name=f.nome or ""))

    location = getattr(solic.municipio, "nome", None)
    return GoogleEvent(
        summary=summary,
        description=description,
        start_iso=_fmt_dt(solic.data_inicio),
        end_iso=_fmt_dt(solic.data_fim),
        location=location,
        attendees=attendees,
        conference=True,  # Sempre criar Google Meet
    )
