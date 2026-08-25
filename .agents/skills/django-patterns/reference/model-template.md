# Model template — AS v2

Generic Django 5.2 model scaffold. Inline deltas that are AS-v2-specific (re-export
layout, timezone constant, RBAC) live in `SKILL.md`; this file is the full skeleton to
copy when creating a model under `apps/core/models/<domain>.py`.

Principles:
1. Constraints + validation belong in the DB (CheckConstraint / UniqueConstraint).
2. Timezone-aware `DateTimeField` — storage UTC, display `America/Fortaleza`.
3. `related_name` always explicit; FK `on_delete=PROTECT` for business data.
4. `Meta.indexes` for every filter/order field.
5. After adding the model, re-export it in `apps/core/models/__init__.py`.

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class ExampleModel(models.Model):
    """
    Brief description of the model.

    Business Rules:
    - Rule 1 (e.g., RD-01: Non-overlapping)
    - Rule 2 (e.g., PA-01: Manual approval required)

    Relationships:
    - FK to Usuario (solicitante)
    - M2M to Usuario (participantes)
    """

    nome = models.CharField(
        max_length=200,
        verbose_name="Nome",
        help_text="Nome descritivo do exemplo",
    )

    # FK — always related_name; PROTECT for business data
    solicitante = models.ForeignKey(
        "Usuario",
        on_delete=models.PROTECT,
        related_name="exemplos_solicitados",
        verbose_name="Solicitante",
    )

    # Timezone-aware (stored UTC)
    inicio = models.DateTimeField(verbose_name="Data/Hora de Início")
    fim = models.DateTimeField(verbose_name="Data/Hora de Fim")

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADO = "aprovado", "Aprovado"
        REPROVADO = "reprovado", "Reprovado"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        verbose_name="Status",
    )

    prioridade = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3,
        verbose_name="Prioridade",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exemplo"
        verbose_name_plural = "Exemplos"
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                check=models.Q(fim__gt=models.F("inicio")),
                name="valid_time_range",
            ),
            models.UniqueConstraint(
                fields=["solicitante", "inicio"],
                name="unique_solicitante_inicio",
            ),
        ]

        indexes = [
            models.Index(fields=["status", "inicio"]),
            models.Index(fields=["solicitante", "-created_at"]),
        ]

    def clean(self):
        """Validation that can't be a DB constraint (needs Python/relations)."""
        super().clean()
        if self.inicio and self.fim and self.fim <= self.inicio:
            raise ValidationError({"fim": "Fim deve ser posterior ao início"})

    def save(self, *args, **kwargs):
        """full_clean() runs validators + clean() before persisting."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.status})"
```

Real examples in the codebase:
- `apps/core/models/dat_registro.py` — `save()` calls `_calcular_nr_codigos()` to derive
  `nr_codigos` automatically.
- `apps/core/models/plano_formacoes.py` — `recalcular_ch()` method + `taxa_realizacao` property.
