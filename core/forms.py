# aprender_sistema/core/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import Solicitacao, Formador, AprovacaoStatus
from core.services.conflicts import check_conflicts

# -------- RF02: Solicitação --------
class SolicitacaoForm(forms.ModelForm):
    formadores = forms.ModelMultipleChoiceField(
        queryset=Formador.objects.filter(ativo=True).order_by("nome"),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Formadores",
        help_text="Selecione os formadores que participarão do evento",
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
            "projeto": forms.Select(attrs={"class": "form-select"}),
            "municipio": forms.Select(attrs={"class": "form-select"}),
            "tipo_evento": forms.Select(attrs={"class": "form-select"}),
            "titulo_evento": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Digite o título do evento",
                "maxlength": "255"
            }),
            "data_inicio": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control"
            }),
            "data_fim": forms.DateTimeInput(attrs={
                "type": "datetime-local", 
                "class": "form-control"
            }),
            "numero_encontro_formativo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: 1º Encontro, Módulo 1, etc."
            }),
            "coordenador_acompanha": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Observações adicionais sobre o evento"
            }),
        }
        labels = {
            "projeto": "Projeto",
            "municipio": "Município",
            "tipo_evento": "Tipo de Evento",
            "titulo_evento": "Título do Evento",
            "data_inicio": "Data/Hora de Início",
            "data_fim": "Data/Hora de Fim",
            "numero_encontro_formativo": "Número do Encontro Formativo",
            "coordenador_acompanha": "Coordenador acompanha o evento",
            "observacoes": "Observações",
        }
        help_texts = {
            "data_inicio": "Selecione a data e horário de início do evento",
            "data_fim": "Selecione a data e horário de término do evento",
            "numero_encontro_formativo": "Campo opcional para identificar a sequência do encontro",
            "coordenador_acompanha": "Marque se o coordenador participará do evento",
            "observacoes": "Informações adicionais relevantes para o evento",
        }

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get("data_inicio")
        df = cleaned.get("data_fim")
        formadores = cleaned.get("formadores")
        titulo = cleaned.get("titulo_evento")

        # Validação básica de datas
        if di and df and df <= di:
            raise ValidationError(_("A data/hora de término deve ser maior que a de início."))

        # Validação de duração mínima (30 minutos)
        if di and df:
            duracao = df - di
            if duracao.total_seconds() < 1800:  # 30 minutos em segundos
                raise ValidationError(_("O evento deve ter duração mínima de 30 minutos."))

        # Validação de data futura
        if di:
            from django.utils import timezone
            now = timezone.now()
            if di <= now:
                raise ValidationError(_("A data de início deve ser no futuro."))

        # Validação de título
        if titulo and len(titulo.strip()) < 3:
            raise ValidationError(_("O título do evento deve ter pelo menos 3 caracteres."))

        # Verificação de conflitos
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


# -------- RF04: Formulário de decisão --------
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


# -------- Bloqueio de Agenda (Apps Script -> Django) --------
class BloqueioAgendaForm(forms.Form):
    formador = forms.ModelChoiceField(
        queryset=Formador.objects.filter(ativo=True).order_by("nome"),
        label="Formador",
        required=True,
        widget=forms.Select(attrs={"class": "campo"})
    )
    inicio = forms.DateField(label="Início", widget=forms.DateInput(attrs={"type": "date"}))
    fim = forms.DateField(label="Fim", widget=forms.DateInput(attrs={"type": "date"}))
    TIPO_CHOICES = (("Total","Total"), ("Parcial","Parcial"))
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, label="Tipo")

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get("inicio")
        df = cleaned.get("fim")
        if di and df and df < di:
            raise ValidationError(_("A data final não pode ser menor que a inicial."))
        return cleaned
