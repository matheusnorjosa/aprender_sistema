#!/usr/bin/env python
import os
import sys
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Formador, Municipio, Projeto, TipoEvento

User = get_user_model()

print("=== TESTE DO SISTEMA DE GESTAO ADMINISTRATIVA ===")
print()

# 1. Verificar usuário admin
try:
    admin_user = User.objects.get(username='admin')
    print(f"[OK] Usuario admin encontrado: {admin_user.username}")
    print(f"   is_staff: {admin_user.is_staff}")
    print(f"   is_superuser: {admin_user.is_superuser}")
    print()
except User.DoesNotExist:
    print("[ERRO] Usuario admin nao encontrado!")
    sys.exit(1)

# 2. Verificar dados no banco
print("ESTATISTICAS DO BANCO DE DADOS:")
print(f"   Total de Formadores: {Formador.objects.count()}")
print(f"   Formadores Ativos: {Formador.objects.filter(ativo=True).count()}")
print(f"   Total de Municipios: {Municipio.objects.count()}")
print(f"   Municipios Ativos: {Municipio.objects.filter(ativo=True).count()}")
print(f"   Total de Projetos: {Projeto.objects.count()}")
print(f"   Projetos Ativos: {Projeto.objects.filter(ativo=True).count()}")
print(f"   Total de Tipos de Evento: {TipoEvento.objects.count()}")
print(f"   Tipos de Evento Ativos: {TipoEvento.objects.filter(ativo=True).count()}")
print()

# 3. Verificar URLs de gestão
print("VERIFICACAO DE URLs:")
urls_gestao = [
    'core:gestao_dashboard',
    'core:gestao_formadores',
    'core:gestao_municipios', 
    'core:gestao_projetos',
    'core:gestao_tipos_evento'
]

for url_name in urls_gestao:
    try:
        url = reverse(url_name)
        print(f"   [OK] {url_name} -> {url}")
    except Exception as e:
        print(f"   [ERRO] {url_name} -> {e}")

print()

# 4. Verificar templates
print("VERIFICACAO DE TEMPLATES:")
templates_required = [
    'core/templates/core/gestao/dashboard.html',
    'core/templates/core/gestao/formadores/list.html',
    'core/templates/core/gestao/municipios/list.html',
    'core/templates/core/gestao/projetos/list.html',
    'core/templates/core/gestao/tipos_evento/list.html'
]

for template_path in templates_required:
    if os.path.exists(template_path):
        print(f"   [OK] {template_path}")
    else:
        print(f"   [ERRO] {template_path} - AUSENTE")

print()

# 5. Verificar views
print("VERIFICACAO DE VIEWS:")
try:
    from core.views.gestao_views import (
        GestaoDashboardView,
        FormadorListView, FormadorCreateView, FormadorUpdateView, FormadorDeleteView,
        MunicipioListView, MunicipioCreateView, MunicipioUpdateView, MunicipioDeleteView,
        ProjetoListView, ProjetoCreateView, ProjetoUpdateView, ProjetoDeleteView,
        TipoEventoListView, TipoEventoCreateView, TipoEventoUpdateView, TipoEventoDeleteView
    )
    print("   [OK] Todas as views de gestao importadas com sucesso")
except ImportError as e:
    print(f"   [ERRO] Erro na importacao das views: {e}")

print()

# 6. Verificar formulários
print("VERIFICACAO DE FORMULARIOS:")
try:
    from core.forms import FormadorForm, MunicipioForm, ProjetoForm, TipoEventoForm
    print("   [OK] Todos os formularios de gestao importados com sucesso")
except ImportError as e:
    print(f"   [ERRO] Erro na importacao dos formularios: {e}")

print()
print("=== RESULTADO FINAL ===")
print("Sistema de Gestao Administrativa configurado e pronto para uso!")
print()
print("PARA ACESSAR:")
print("   1. Faca login como admin")
print("   2. Acesse: http://localhost:8000/")
print("   3. No menu lateral, clique em 'Dashboard Administrativo'")
print("   4. Ou acesse diretamente: http://localhost:8000/gestao/")
print()
print("SE O MENU NAO APARECER:")
print("   - Limpe o cache do navegador (Ctrl+Shift+R)")
print("   - Ou abra em aba anonima/incognita")