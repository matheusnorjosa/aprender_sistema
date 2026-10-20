# Serializer template — DRF read/write separation

Why separate read and write serializers:
- **Read** (GET): user-friendly — `StringRelatedField`, formatted fields, nested objects.
- **Write** (POST/PUT/PATCH): efficient — `PrimaryKeyRelatedField`, validation.

Live in `apps/core/serializers/<domain>.py`; re-export in `serializers/__init__.py`.

```python
from rest_framework import serializers
from apps.core.models import Solicitacao, Usuario, Municipio


class SolicitacaoReadSerializer(serializers.ModelSerializer):
    """Read-only — GET /api/solicitacoes/."""

    usuario = serializers.StringRelatedField()   # dono; uses model __str__()
    municipio = serializers.StringRelatedField()
    inicio_formatado = serializers.SerializerMethodField()
    formadores = UsuarioReadSerializer(many=True, read_only=True)  # M2M; watch N+1

    class Meta:
        model = Solicitacao
        fields = [
            "id", "usuario", "municipio", "inicio", "fim",
            "inicio_formatado", "status", "formadores",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_inicio_formatado(self, obj):
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Fortaleza")
        return obj.inicio.astimezone(tz).strftime("%d/%m/%Y %H:%M")


class SolicitacaoWriteSerializer(serializers.ModelSerializer):
    """Write + validation — POST/PUT/PATCH."""

    # O dono (`usuario`) NUNCA vem do payload: é somente-leitura aqui e o
    # `perform_create` da view grava `serializer.save(usuario=self.request.user)`.
    # Aceitar o dono do cliente = IDOR/spoofing.
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)

    # PrimaryKeyRelatedField: accept IDs, validate existence + scope
    municipio = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.filter(ativo=True)
    )
    formadores = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Usuario.objects.filter(is_active=True),
        required=False,
    )

    class Meta:
        model = Solicitacao
        fields = [
            "usuario", "municipio", "inicio", "fim",
            "status", "formadores", "observacoes",
        ]

    def validate_inicio(self, value):
        """Per-field validation."""
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Início deve ser no futuro")
        return value

    def validate(self, data):
        """Cross-field — runs after per-field validation."""
        if data["fim"] <= data["inicio"]:
            raise serializers.ValidationError({"fim": "Fim deve ser posterior ao início"})
        return data

    def create(self, validated_data):
        """Pop M2M before create, then .set()."""
        formadores = validated_data.pop("formadores", [])
        solicitacao = Solicitacao.objects.create(**validated_data)
        solicitacao.formadores.set(formadores)
        return solicitacao
```

Os papéis no evento (coordenador, formador, quem acompanha, convidado) moram em
`Participation` (related_name `participations`), não num campo `participantes`.

## Gotchas seen in AS v2

- **Model field with `default=` masks `required`**: a `ModelSerializer` accepts a payload
  without that field. When the field must be present, declare it explicitly as
  `serializers.ChoiceField(required=True)` (case: `Projeto.fluxo`, PR #1312).
- **Write-only / masked fields**: read serializer returns a masked value; write path gates
  behind an explicit "Alterar" flag (LGPD pattern).
- Read-only field: `meet_link = serializers.CharField(read_only=True)` or list it in
  `Meta.read_only_fields` (real field on Solicitacao, see
  `tests/test_solicitacao_serializer_meet_link.py`).
- Prefer separate endpoints over nested writes; if unavoidable, pop the nested data in
  `create()` and build children explicitly.

Real examples: `apps/core/serializers/solicitacao.py`, `serializers/usuario.py`,
`serializers/plano_formacoes.py`.
