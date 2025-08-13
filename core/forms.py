# aprender_sistema/core/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import Solicitacao, Formador
from core.services.conflicts import check_conflicts

class SolicitacaoForm(forms.ModelForm):
    formadores = forms.ModelMultipleChoiceField(
        queryset=Formador.objects.filter(ativo=True).order_by("nome"),
        widget=forms.CheckboxSelectMultiple,  # mude para SelectMultiple se preferir
        required=True,
        label="Formadores",
    )

    class Meta:
        model = Solicitacao
        fields = [
            "projeto", "municipio", "tipo_evento",
            "titulo_evento", "data_inicio", "data_fim",
            "numero_encontro_formativo", "coordenador_acompanha", "observacoes",
            "formadores",
        ]
        widgets = {
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get("data_inicio")
        df = cleaned.get("data_fim")
        formadores = cleaned.get("formadores")

        if di and df and df <= di:
            raise ValidationError(_("A data/hora de término deve ser maior que a de início."))

        if di and df and formadores and len(formadores) > 0:
            conflitos = check_conflicts(formadores, di, df)
            msgs = []

            if conflitos["bloqueios"]:
                linhas = []
                for b in conflitos["bloqueios"]:
                    linhas.append(f"- {b.formador.nome} indisponível em {b.data_bloqueio} {b.hora_inicio}-{b.hora_fim} ({b.tipo_bloqueio})")
                msgs.append("Conflitos de disponibilidade:\n" + "\n".join(linhas))

            if conflitos["solicitacoes"]:
                linhas = []
                for s in conflitos["solicitacoes"]:
                    nomes = ", ".join([f.nome for f in s.formadores.all()])
                    linhas.append(f"- {s.titulo_evento} ({s.data_inicio:%d/%m %H:%M}-{s.data_fim:%d/%m %H:%M}) — Formadores: {nomes}")
                msgs.append("Conflitos com solicitações aprovadas:\n" + "\n".join(linhas))

            if msgs:
                raise ValidationError("\n\n".join(msgs))

        return cleaned
    
# === RF04: Formulário de decisão de aprovação ===
from django import forms
from django.core.exceptions import ValidationError
from core.models import AprovacaoStatus

class AprovacaoDecisionForm(forms.Form):
    decisao = forms.ChoiceField(
        choices=AprovacaoStatus.choices,
        label="Decisão",
        widget=forms.RadioSelect,
    )
    justificativa = forms.CharField(
        label="Justificativa",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        decisao = cleaned.get("decisao")
        justificativa = cleaned.get("justificativa", "").strip()
        if decisao == AprovacaoStatus.REPROVADO and not justificativa:
            raise ValidationError("Justificativa é obrigatória para reprovar.")
        return cleaned
