# aprender_sistema/core/forms.py
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import AprovacaoStatus, Municipio, Projeto, Setor, TipoEvento, Solicitacao, Usuario
from core.services.conflicts import check_conflicts
from core.services import FormadorService, UsuarioService
from core.validators import CPFValidator

# COMPATÍVEL: Import direto do Formador para manter compatibilidade temporária
from core.models import Formador


# -------- RF02: Solicitação --------
class SolicitacaoForm(forms.ModelForm):
    formadores = forms.ModelMultipleChoiceField(
        queryset=None,  # Será definido no __init__
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Formadores",
        help_text="Selecione os formadores que participarão do evento",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Usar FormadorService - fonte única
        self.fields['formadores'].queryset = FormadorService.get_formadores_queryset().order_by('first_name', 'last_name')

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
        self.fields["formadores"].label_from_instance = lambda obj: obj.nome_completo
        
        # 1.2 UI/UX: Tornar campos opcionais (mantém obrigatório formadores, data, projeto, município, tipo)
        self.fields["numero_encontro_formativo"].required = False
        self.fields["titulo_evento"].required = False  # "Segmento" conforme solicitado

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

        # Validação de título (apenas se informado, já que é opcional)
        if titulo and titulo.strip() and len(titulo.strip()) < 3:
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
        queryset=Usuario.objects.filter(formador_ativo=True).order_by("first_name", "last_name"),
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
        self.fields["formador"].label_from_instance = lambda obj: obj.nome_completo


# -------- AUTENTICAÇÃO CUSTOMIZADA (CPF + SENHA SIMPLES) --------

class CPFAuthenticationForm(AuthenticationForm):
    """
    Formulário de login customizado usando CPF como username
    """
    username = forms.CharField(
        max_length=11,
        label="CPF",
        help_text="Digite apenas os números do CPF (sem pontos ou traço)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678901',
            'autocomplete': 'username',
        })
    )
    
    password = forms.CharField(
        label="Senha",
        help_text="Mínimo 4 caracteres (apenas letras e números)",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha',
            'autocomplete': 'current-password',
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Limpar CPF (remover qualquer formatação)
        cpf_limpo = ''.join(filter(str.isdigit, username))
        
        if len(cpf_limpo) != 11:
            raise ValidationError("CPF deve conter exatamente 11 dígitos.")
        
        return cpf_limpo

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def get_invalid_login_error(self):
        return ValidationError(
            "CPF ou senha incorretos. Verifique se o CPF está correto e tem 11 dígitos.",
            code='invalid_login',
        )


class CPFUserCreationForm(UserCreationForm):
    """
    Formulário de criação de usuário com CPF obrigatório e senha simples
    """
    cpf = forms.CharField(
        max_length=11,
        label="CPF",
        help_text="Digite apenas os números do CPF (sem pontos ou traço)",
        validators=[CPFValidator()],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678901',
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        label="Nome",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        label="Sobrenome", 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = ('username', 'cpf', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remover help text complexo das senhas
        self.fields['password1'].help_text = "Mínimo 4 caracteres (apenas letras e números)"
        self.fields['password2'].help_text = "Digite a mesma senha novamente"
        
        # Estilizar campos
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        # Limpar CPF
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Verificar se já existe
        if Usuario.objects.filter(cpf=cpf_limpo).exists():
            raise ValidationError("Este CPF já está cadastrado no sistema.")
        
        return cpf_limpo

    def save(self, commit=True):
        user = super().save(commit=False)
        user.cpf = self.cleaned_data['cpf']
        if commit:
            user.save()
        return user


# -------- GESTÃO ADMINISTRATIVA --------

class FormadorForm(forms.ModelForm):
    """
    Formulário para gestão de formadores - FONTE ÚNICA Usuario
    Convertido para usar Usuario ao invés de Formador separado
    """

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'area_atuacao', 'formador_ativo', 'municipio', 'setor']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do formador'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sobrenome do formador'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemplo.com'
            }),
            'area_atuacao': forms.Select(attrs={
                'class': 'form-select'
            }),
            'municipio': forms.Select(attrs={
                'class': 'form-select'
            }),
            'setor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'formador_ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
            'area_atuacao': 'Área de Atuação',
            'municipio': 'Município',
            'setor': 'Setor',
            'formador_ativo': 'Ativo como Formador'
        }
        help_texts = {
            'first_name': 'Nome do formador',
            'last_name': 'Sobrenome do formador',
            'email': 'E-mail único para contato e notificações',
            'area_atuacao': 'Grupo/área de atuação do formador',
            'municipio': 'Município de origem do formador',
            'setor': 'Setor de vinculação',
            'formador_ativo': 'Marque para ativar como formador'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customizar querysets usando Services centralizados
        self.fields['area_atuacao'].queryset = Group.objects.all().order_by('name')
        self.fields['municipio'].queryset = Municipio.objects.filter(ativo=True).order_by('nome')
        self.fields['setor'].queryset = Setor.objects.all().order_by('nome')
        # Tornar campos opcionais
        self.fields['area_atuacao'].required = False
        self.fields['municipio'].required = False
        self.fields['setor'].required = False

    def save(self, commit=True):
        usuario = super().save(commit=False)
        # Garantir que o usuário seja adicionado ao grupo formador se formador_ativo=True
        if commit:
            usuario.save()
            if usuario.formador_ativo:
                formador_group, _ = Group.objects.get_or_create(name='formador')
                usuario.groups.add(formador_group)
            else:
                # Remover do grupo se não for mais formador ativo
                formador_group = Group.objects.filter(name='formador').first()
                if formador_group:
                    usuario.groups.remove(formador_group)
        return usuario


class MunicipioForm(forms.ModelForm):
    """Formulário para gestão de municípios"""
    
    UF_CHOICES = [
        ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
        ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
        ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
        ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
        ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')
    ]
    
    uf = forms.ChoiceField(
        choices=[('', 'Selecione...')] + UF_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='UF',
        help_text='Estado do município'
    )
    
    class Meta:
        model = Municipio
        fields = ['nome', 'uf', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do município'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'nome': 'Nome do Município',
            'ativo': 'Ativo'
        }
        help_texts = {
            'nome': 'Nome oficial do município',
            'ativo': 'Desmarque para desativar o município'
        }


class ProjetoForm(forms.ModelForm):
    """Formulário para gestão de projetos"""
    
    class Meta:
        model = Projeto
        fields = ['nome', 'descricao', 'setor', 'codigo_produto', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do projeto'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrição detalhada do projeto'
            }),
            'setor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'codigo_produto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código do produto (opcional)'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'nome': 'Nome do Projeto',
            'descricao': 'Descrição',
            'setor': 'Setor Responsável',
            'codigo_produto': 'Código do Produto',
            'ativo': 'Ativo'
        }
        help_texts = {
            'nome': 'Nome único do projeto',
            'descricao': 'Descrição detalhada do projeto (opcional)',
            'setor': 'Setor organizacional responsável',
            'codigo_produto': 'Código do produto da planilha (opcional)',
            'ativo': 'Desmarque para desativar o projeto'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customizar queryset para setor
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')
        # Tornar campos opcionais
        self.fields['setor'].required = False
        self.fields['descricao'].required = False
        self.fields['codigo_produto'].required = False


class TipoEventoForm(forms.ModelForm):
    """Formulário para gestão de tipos de evento"""
    
    class Meta:
        model = TipoEvento
        fields = ['nome', 'online', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do tipo de evento'
            }),
            'online': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'nome': 'Nome do Tipo de Evento',
            'online': 'É um evento online?',
            'ativo': 'Ativo'
        }
        help_texts = {
            'nome': 'Nome único do tipo de evento',
            'online': 'Marque se este tipo de evento é realizado online',
            'ativo': 'Desmarque para desativar este tipo de evento'
        }
