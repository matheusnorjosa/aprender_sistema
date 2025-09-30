# core/backends.py
"""
Backend de autenticação customizado para login via CPF
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class CPFAuthenticationBackend(BaseBackend):
    """
    Autentica usuários usando CPF (apenas números) como username
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # Limpar CPF (remover qualquer formatação que possa ter)
            cpf_limpo = ''.join(filter(str.isdigit, username))
            
            # Buscar usuário por CPF (usando only para campos que existem)
            user = User.objects.only('id', 'username', 'email', 'password', 'is_active', 'is_staff', 'is_superuser', 'cpf', 'telefone', 'cargo', 'municipio_id', 'setor_id', 'area_atuacao_id').get(cpf=cpf_limpo)
            
            # Verificar senha
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # Fallback: tentar username normal também
            try:
                user = User.objects.only('id', 'username', 'email', 'password', 'is_active', 'is_staff', 'is_superuser', 'cpf', 'telefone', 'cargo', 'municipio_id', 'setor_id', 'area_atuacao_id').get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                pass
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.only('id', 'username', 'email', 'password', 'is_active', 'is_staff', 'is_superuser', 'cpf', 'telefone', 'cargo', 'municipio_id', 'setor_id', 'area_atuacao_id').get(pk=user_id)
        except User.DoesNotExist:
            return None