# aprender_sistema/core/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import AprovacaoStatus, Formador, Solicitacao
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
            "projeto",
            "municipio",
            "tipo_evento",
            "titulo_evento",
            "data_inicio",
            "data_fim",
            "numero_encontro_formativo",
            "coordenador_acompanha",
            "observacoes",
            "formadores",
        ]
        widgets = {
            "projeto": forms.Select(
                attrs={
                    "class": "form-select modern-select",
                    "style": 'background-image: url(\'data:image/svg+xml;charset=US-ASCII,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="%23007bff" viewBox="0 0 16 16"><path d="M7.247 11.14L2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/></svg>\'); background-repeat: no-repeat; background-position: right 0.75rem center; background-size: 16px 12px; padding-right: 2.5rem;',
                    "autocomplete": "organization",
                }
            ),
            "municipio": forms.Select(
                attrs={
                    "class": "form-select modern-select",
                    "style": 'background-image: url(\'data:image/svg+xml;charset=US-ASCII,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="%23007bff" viewBox="0 0 16 16"><path d="M7.247 11.14L2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/></svg>\'); background-repeat: no-repeat; background-position: right 0.75rem center; background-size: 16px 12px; padding-right: 2.5rem;',
                    "autocomplete": "address-level2",
                }
            ),
            "tipo_evento": forms.Select(
                attrs={
                    "class": "form-select modern-select",
                    "style": 'background-image: url(\'data:image/svg+xml;charset=US-ASCII,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="%23007bff" viewBox="0 0 16 16"><path d="M7.247 11.14L2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/></svg>\'); background-repeat: no-repeat; background-position: right 0.75rem center; background-size: 16px 12px; padding-right: 2.5rem;',
                }
            ),
            "titulo_evento": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: 1º e 2º anos",
                    "maxlength": "255",
                    "autocomplete": "off",
                }
            ),
            "data_inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "data_fim": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "numero_encontro_formativo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: 1º Encontro, Módulo 1, etc.",
                }
            ),
            "coordenador_acompanha": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observações adicionais sobre o evento",
                }
            ),
        }
        labels = {
            "projeto": "Projeto",
            "municipio": "Município",
            "tipo_evento": "Tipo de Evento",
            "titulo_evento": "Segmento",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customizar a exibição dos formadores para mostrar apenas o nome
        self.fields["formadores"].label_from_instance = lambda obj: obj.nome

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get("data_inicio")
        df = cleaned.get("data_fim")
        formadores = cleaned.get("formadores")
        titulo = cleaned.get("titulo_evento")

        # Validação básica de datas
        if di and df and df <= di:
            raise ValidationError(
                _("A data/hora de término deve ser maior que a de início.")
            )

        # Validação de duração mínima (30 minutos)
        if di and df:
            duracao = df - di
            if duracao.total_seconds() < 1800:  # 30 minutos em segundos
                raise ValidationError(
                    _("O evento deve ter duração mínima de 30 minutos.")
                )

        # Validação de data futura
        if di:
            from django.utils import timezone

            now = timezone.now()
            if di <= now:
                raise ValidationError(_("A data de início deve ser no futuro."))

        # Validação de título
        if titulo and len(titulo.strip()) < 3:
            raise ValidationError(
                _("O título do evento deve ter pelo menos 3 caracteres.")
            )

        # Verificação de conflitos
        if di and df and formadores and len(formadores) > 0:
            municipio = cleaned.get("municipio")
            conflitos = check_conflicts(formadores, di, df, municipio)
            msgs = []
            if conflitos["bloqueios"]:
                linhas = []
                for b in conflitos["bloqueios"]:
                    # RD-08: Incluir código de conflito (T ou P) na mensagem
                    tipo_codigo = (
                        "T"
                        if (
                            b.tipo_bloqueio.upper() == "T"
                            or b.tipo_bloqueio.lower() == "total"
                        )
                        else "P"
                    )
                    data_formatada = b.data_bloqueio.strftime("%d/%m")
                    hora_inicio = b.hora_inicio.strftime("%H:%M")
                    hora_fim = b.hora_fim.strftime("%H:%M")
                    linhas.append(
                        f"- [{tipo_codigo}] {b.formador.nome} indisponível em {data_formatada} {hora_inicio}-{hora_fim}"
                    )
                msgs.append("Conflitos de disponibilidade:\n" + "\n".join(linhas))
            if conflitos["solicitacoes"]:
                linhas = []
                for s in conflitos["solicitacoes"]:
                    # RD-08: Código E para eventos confirmados
                    nomes = ", ".join([f.nome for f in s.formadores.all()])
                    data_inicio = s.data_inicio.strftime("%d/%m %H:%M")
                    data_fim = s.data_fim.strftime("%d/%m %H:%M")
                    linhas.append(
                        f"- [E] {s.titulo_evento} ({data_inicio}-{data_fim}) — Formadores: {nomes}"
                    )
                msgs.append(
                    "Conflitos com solicitações aprovadas:\n" + "\n".join(linhas)
                )
            if conflitos["deslocamentos"]:
                linhas = []
                for d in conflitos["deslocamentos"]:
                    # RD-08: Código D para deslocamento
                    sol = d["solicitacao"]
                    gap = d["gap_minutes"]
                    required = d["required_minutes"]
                    data_inicio = sol.data_inicio.strftime("%d/%m %H:%M")
                    data_fim = sol.data_fim.strftime("%d/%m %H:%M")
                    linhas.append(
                        f"- [D] Buffer insuficiente para {sol.titulo_evento} em {sol.municipio} ({data_inicio}-{data_fim}) — Gap: {gap:.0f}min, necessário: {required}min"
                    )
                msgs.append("Conflitos de deslocamento:\n" + "\n".join(linhas))
            if conflitos["capacidade_diaria"]:
                linhas = []
                for c in conflitos["capacidade_diaria"]:
                    # RD-08: Código M para mais de um evento (capacidade excedida)
                    formador = c["formador"]
                    data_formatada = c["data"].strftime("%d/%m")
                    total = c["total_com_novo"]
                    limite = c["limite_diario"]
                    excesso = c["excesso"]
                    linhas.append(
                        f"- [M] {formador.nome} em {data_formatada}: capacidade diária excedida ({total:.1f}h/{limite}h, excesso: {excesso:.1f}h)"
                    )
                msgs.append("Conflitos de capacidade diária:\n" + "\n".join(linhas))
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


# -------- Bloqueio de Agenda (Apps Script -> Django) --------
class BloqueioAgendaForm(forms.Form):
    formador = forms.ModelChoiceField(
        queryset=Formador.objects.filter(ativo=True).order_by("nome"),
        label="Formador",
        required=True,
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "style": "font-size: 1rem; padding: 0.75rem;",
            }
        ),
    )
    inicio = forms.DateField(
        label="Data de Início",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "style": "font-size: 1rem; padding: 0.75rem;",
            }
        ),
    )
    fim = forms.DateField(
        label="Data de Fim",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "style": "font-size: 1rem; padding: 0.75rem;",
            }
        ),
    )
    TIPO_CHOICES = (("Total", "Total"), ("Parcial", "Parcial"))
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        label="Tipo de Bloqueio",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customizar a exibição do formador para mostrar apenas o nome
        self.fields["formador"].label_from_instance = lambda obj: obj.nome
