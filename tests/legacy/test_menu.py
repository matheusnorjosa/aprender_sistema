#!/usr/bin/env python
import os
import sys
import django

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()

# Get the admin user
try:
    admin_user = User.objects.get(username="admin")
    print(f"Usuário encontrado: {admin_user.username}")
    print(f"is_staff: {admin_user.is_staff}")
    print(f"is_superuser: {admin_user.is_superuser}")
    print(f"is_authenticated: {admin_user.is_authenticated}")

    # Read the base template
    with open("core/templates/core/base.html", "r", encoding="utf-8") as f:
        template_content = f.read()

    # Extract just the gestao menu section
    start_marker = "<!-- Gestão Administrativa"
    end_marker = "{% endif %}"

    start_idx = template_content.find(start_marker)
    if start_idx != -1:
        # Find the end of the gestao section
        search_start = start_idx
        for i in range(3):  # Look for the 3rd endif after the start
            search_start = template_content.find(end_marker, search_start) + len(
                end_marker
            )

        gestao_section = template_content[start_idx:search_start]
        print("\nSeção de Gestão encontrada no template:")
        print("-" * 50)
        print(
            gestao_section[:500] + "..."
            if len(gestao_section) > 500
            else gestao_section
        )

        # Test template rendering
        template = Template(
            """
        {% load static %}
        {{ user.is_staff }}
        {% if user.is_staff %}
        <div class="gestao-test">GESTÃO MENU VISÍVEL</div>
        {% else %}
        <div class="gestao-test">GESTÃO MENU OCULTO</div>
        {% endif %}
        """
        )

        context = Context({"user": admin_user})
        rendered = template.render(context)
        print(f"\nTeste de renderização:")
        print(rendered.strip())

    else:
        print("Seção de Gestão NÃO encontrada no template!")

except User.DoesNotExist:
    print("Usuário admin não encontrado!")
except Exception as e:
    print(f"Erro: {e}")
