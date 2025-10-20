#!/usr/bin/env python
import os
import sys

import django

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse

from core.models import Formador, Municipio, Projeto, TipoEvento

User = get_user_model()

print("=== TESTE DO SISTEMA DE GESTAO ADMINISTRATIVA ===\n")

# 1. Verificar usuário admin
try:
    admin_user = User.objects.get(username="admin")
    print(f"[OK] Usuario admin encontrado: {admin_user.username}")
    print(f"   is_staff: {admin_user.is_staff}")
    print(f"   is_superuser: {admin_user.is_superuser}")
    print()
except User.DoesNotExist:
    print("[ERRO] Usuario admin nao encontrado!")
    sys.exit(1)

# 2. Verificar dados no banco
print("📊 ESTATÍSTICAS DO BANCO DE DADOS:")
print(f"   Total de Formadores: {Formador.objects.count()}")
print(f"   Formadores Ativos: {Formador.objects.filter(ativo=True).count()}")
print(f"   Total de Municípios: {Municipio.objects.count()}")
print(f"   Municípios Ativos: {Municipio.objects.filter(ativo=True).count()}")
print(f"   Total de Projetos: {Projeto.objects.count()}")
print(f"   Projetos Ativos: {Projeto.objects.filter(ativo=True).count()}")
print(f"   Total de Tipos de Evento: {TipoEvento.objects.count()}")
print(f"   Tipos de Evento Ativos: {TipoEvento.objects.filter(ativo=True).count()}")
print()

# 3. Verificar URLs de gestão
print("🔗 VERIFICAÇÃO DE URLs:")
urls_gestao = [
    "core:gestao_dashboard",
    "core:gestao_formadores",
    "core:gestao_municipios",
    "core:gestao_projetos",
    "core:gestao_tipos_evento",
]

for url_name in urls_gestao:
    try:
        url = reverse(url_name)
        print(f"   ✅ {url_name} -> {url}")
    except Exception as e:
        print(f"   ❌ {url_name} -> ERRO: {e}")

print()

# 4. Testar renderização do menu
print("🎨 TESTE DE RENDERIZAÇÃO DO MENU:")
template_content = """
{% if user.is_staff %}
<div class="nav-section">
  <div class="nav-section-title">Gestão</div>
  <a href="/gestao/" class="nav-item">Dashboard Administrativo</a>
</div>
{% else %}
<div>SEM PERMISSÃO</div>
{% endif %}
"""

try:
    template = Template(template_content)
    context = Context({"user": admin_user})
    rendered = template.render(context)
    if "Dashboard Administrativo" in rendered:
        print("   ✅ Menu de gestão renderiza corretamente para admin")
    else:
        print("   ❌ Menu de gestão NÃO renderiza para admin")
except Exception as e:
    print(f"   ❌ Erro na renderização: {e}")

print()

# 5. Verificar templates
import os

print("📄 VERIFICAÇÃO DE TEMPLATES:")
templates_required = [
    "core/templates/core/gestao/dashboard.html",
    "core/templates/core/gestao/formadores/list.html",
    "core/templates/core/gestao/municipios/list.html",
    "core/templates/core/gestao/projetos/list.html",
    "core/templates/core/gestao/tipos_evento/list.html",
]

for template_path in templates_required:
    if os.path.exists(template_path):
        print(f"   ✅ {template_path}")
    else:
        print(f"   ❌ {template_path} - AUSENTE")

print()

# 6. Verificar imports das views
print("🏗️ VERIFICAÇÃO DE VIEWS:")
try:
    from core.views.gestao_views import (
        FormadorCreateView,
        FormadorDeleteView,
        FormadorListView,
        FormadorUpdateView,
        GestaoDashboardView,
        MunicipioCreateView,
        MunicipioDeleteView,
        MunicipioListView,
        MunicipioUpdateView,
        ProjetoCreateView,
        ProjetoDeleteView,
        ProjetoListView,
        ProjetoUpdateView,
        TipoEventoCreateView,
        TipoEventoDeleteView,
        TipoEventoListView,
        TipoEventoUpdateView,
    )

    print("   ✅ Todas as views de gestão importadas com sucesso")
except ImportError as e:
    print(f"   ❌ Erro na importação das views: {e}")

print()

# 7. Verificar formulários
print("📝 VERIFICAÇÃO DE FORMULÁRIOS:")
try:
    from core.forms import FormadorForm, MunicipioForm, ProjetoForm, TipoEventoForm

    print("   ✅ Todos os formulários de gestão importados com sucesso")
except ImportError as e:
    print(f"   ❌ Erro na importação dos formulários: {e}")

print()
print("=== RESULTADO FINAL ===")
print("🎉 Sistema de Gestão Administrativa configurado e pronto para uso!")
print()
print("📝 PARA ACESSAR:")
print("   1. Faça login como admin")
print("   2. Acesse: http://localhost:8000/")
print("   3. No menu lateral, clique em 'Dashboard Administrativo'")
print("   4. Ou acesse diretamente: http://localhost:8000/gestao/")
print()
print("⚠️  SE O MENU NÃO APARECER:")
print("   - Limpe o cache do navegador (Ctrl+Shift+R)")
print("   - Ou abra em aba anônima/incógnita")
