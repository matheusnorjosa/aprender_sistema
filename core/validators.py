# core/validators.py
"""
Validadores customizados para senhas simplificadas
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class SimplifiedPasswordValidator:
    """
    Validador de senha simplificado:
    - Mínimo 4 caracteres
    - Apenas letras e números (alfanumérico)
    """
    
    def validate(self, password, user=None):
        if len(password) < 4:
            raise ValidationError(
                _("A senha deve ter pelo menos 4 caracteres."),
                code='password_too_short',
            )
        
        if not re.match(r'^[a-zA-Z0-9]+$', password):
            raise ValidationError(
                _("A senha deve conter apenas letras e números."),
                code='password_not_alphanumeric',
            )
    
    def get_help_text(self):
        return _(
            "Sua senha deve ter pelo menos 4 caracteres e "
            "conter apenas letras e números."
        )


class CPFValidator:
    """
    Validador para campo CPF
    """
    
    def __call__(self, value):
        # Remove qualquer formatação
        cpf_numbers = ''.join(filter(str.isdigit, value))
        
        if len(cpf_numbers) != 11:
            raise ValidationError(
                _("CPF deve conter exatamente 11 dígitos."),
                code='cpf_invalid_length',
            )
        
        # Verificação básica de CPF válido (algoritmo)
        if not self._is_valid_cpf(cpf_numbers):
            raise ValidationError(
                _("CPF inválido."),
                code='cpf_invalid',
            )
    
    def _is_valid_cpf(self, cpf):
        """
        Valida CPF usando o algoritmo oficial
        """
        # CPFs inválidos conhecidos
        if cpf in ['00000000000', '11111111111', '22222222222', 
                   '33333333333', '44444444444', '55555555555',
                   '66666666666', '77777777777', '88888888888', 
                   '99999999999']:
            return False
        
        # Cálculo do primeiro dígito verificador
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        remainder1 = sum1 % 11
        digit1 = 0 if remainder1 < 2 else 11 - remainder1
        
        # Cálculo do segundo dígito verificador
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        remainder2 = sum2 % 11
        digit2 = 0 if remainder2 < 2 else 11 - remainder2
        
        # Verificação final
        return cpf[9] == str(digit1) and cpf[10] == str(digit2)