# aprender_sistema/core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Projeto, Municipio, Formador, TipoEvento

# Para o nosso modelo de usuário personalizado, é uma boa prática
# estender o UserAdmin padrão para ter as funcionalidades completas.
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # Adicione o campo 'papel' à interface de usuário do admin
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('papel',)}),
    )
    # Mostra o campo 'papel' na lista de usuários
    list_display = UserAdmin.list_display + ('papel',)


# Registra os modelos de cadastros para que apareçam no painel de administração.
admin.site.register(Projeto)
admin.site.register(Municipio)
admin.site.register(Formador)
admin.site.register(TipoEvento)
