# DAT-P04-GCAL-v2: Add CalendarSyncLog model
# Created manually to avoid Deslocamento migration conflicts

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0056_remove_marcadorplanilha_disponibilidade_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CalendarSyncLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_hash",
                    models.CharField(
                        db_index=True,
                        help_text="Hash SHA1 do evento para garantir idempotência",
                        max_length=40,
                        verbose_name="Hash Externo",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("created", "Criado"),
                            ("updated", "Atualizado"),
                            ("skipped", "Ignorado (sem mudanças)"),
                            ("duplicado_remoto", "Duplicado remoto detectado"),
                            ("error", "Erro"),
                        ],
                        max_length=20,
                        verbose_name="Ação",
                    ),
                ),
                (
                    "event_id",
                    models.CharField(
                        blank=True,
                        help_text="ID do evento no Google Calendar",
                        max_length=255,
                        null=True,
                        verbose_name="ID do Evento",
                    ),
                ),
                ("summary", models.CharField(max_length=255, verbose_name="Título")),
                (
                    "start_iso",
                    models.CharField(
                        help_text="Data/hora início em formato ISO 8601",
                        max_length=50,
                        verbose_name="Início (ISO)",
                    ),
                ),
                (
                    "end_iso",
                    models.CharField(
                        help_text="Data/hora fim em formato ISO 8601",
                        max_length=50,
                        verbose_name="Fim (ISO)",
                    ),
                ),
                (
                    "run_id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        help_text="UUID único para rastrear lotes de sincronização",
                        verbose_name="ID da Execução",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True, null=True, verbose_name="Mensagem de Erro"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Criado em"),
                ),
            ],
            options={
                "verbose_name": "Log de Sincronização Google Calendar",
                "verbose_name_plural": "Logs de Sincronização Google Calendar",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="calendarsynclog",
            index=models.Index(
                fields=["external_hash"], name="core_calend_externa_75e60c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="calendarsynclog",
            index=models.Index(
                fields=["run_id", "-created_at"], name="core_calend_run_id_6689a2_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="calendarsynclog",
            index=models.Index(
                fields=["action", "-created_at"], name="core_calend_action_145eb7_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="calendarsynclog",
            index=models.Index(
                fields=["-created_at"], name="core_calend_created_c131f3_idx"
            ),
        ),
    ]
