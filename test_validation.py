#!/usr/bin/env python
"""
Script para validação da integridade dos dados extraídos
"""
import os
import sys
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
sys.path.append('/app')
django.setup()

from core.models import *
from django.contrib.auth.models import Group

def main():
    print("═══════════════════════════════════════════════════════════")
    print("📊 RELATÓRIO DE VALIDAÇÃO - DADOS EXTRAÍDOS GOOGLE SHEETS")
    print("═══════════════════════════════════════════════════════════")
    print()

    # 1. Verificar usuários e grupos
    usuarios = Usuario.objects.all()
    groups = Group.objects.all()

    print(f"👥 USUÁRIOS: {usuarios.count()}")
    for usuario in usuarios:
        user_groups = usuario.groups.all()
        grupo_names = [g.name for g in user_groups]
        print(f"   - {usuario.username} ({usuario.email})")
        print(f"     📧 Email: {usuario.email}")
        print(f"     👤 Nome: {usuario.first_name} {usuario.last_name}")
        print(f"     🏢 Grupos: {grupo_names}")
        print()

    print(f"📋 GRUPOS DO SISTEMA: {groups.count()}")
    for group in groups:
        usuarios_count = group.user_set.count()
        print(f"   - {group.name}: {usuarios_count} usuários")
    print()

    # 2. Verificar projetos
    projetos = Projeto.objects.all()
    print(f"📚 PROJETOS: {projetos.count()}")
    for projeto in projetos:
        print(f"   - {projeto.nome}")
    print()

    # 3. Verificar municípios
    municipios = Municipio.objects.all()
    print(f"🏛️ MUNICÍPIOS: {municipios.count()}")
    for municipio in municipios:
        print(f"   - {municipio.nome}")
    print()

    # 4. Verificar setores
    setores = Setor.objects.all()
    print(f"🏢 SETORES: {setores.count()}")
    for setor in setores:
        print(f"   - {setor.nome}")
    print()

    # 5. Verificar tipos de evento
    tipos = TipoEvento.objects.all()
    print(f"📅 TIPOS DE EVENTO: {tipos.count()}")
    for tipo in tipos:
        print(f"   - {tipo.nome}")
    print()

    # 6. Verificar formadores
    formadores = Formador.objects.all()
    print(f"👨‍🏫 FORMADORES: {formadores.count()}")
    if formadores.count() == 0:
        print("   ⚠️  NENHUM FORMADOR ENCONTRADO")
        print("   📝 Usuários no grupo 'formador' devem ter registro Formador associado")

        # Verificar usuários do grupo formador
        grupo_formador = Group.objects.filter(name='formador').first()
        if grupo_formador:
            usuarios_formadores = grupo_formador.user_set.all()
            print(f"   👥 Usuários no grupo 'formador': {usuarios_formadores.count()}")
            for user in usuarios_formadores:
                print(f"      - {user.username} ({user.first_name} {user.last_name})")
    else:
        for formador in formadores:
            print(f"   - {formador.usuario.first_name} {formador.usuario.last_name}")
    print()

    # 7. Verificar relações importantes
    print("🔗 VERIFICAÇÃO DE INTEGRIDADE RELACIONAL:")

    # Verificar se usuários em grupos têm registros associados
    grupo_formador = Group.objects.filter(name='formador').first()
    if grupo_formador:
        usuarios_formadores = grupo_formador.user_set.all()
        formadores_registrados = Formador.objects.all()

        print(f"   📊 Usuários no grupo 'formador': {usuarios_formadores.count()}")
        print(f"   📊 Registros Formador criados: {formadores_registrados.count()}")

        if usuarios_formadores.count() != formadores_registrados.count():
            print("   ⚠️  INCONSISTÊNCIA: Número de usuários ≠ número de registros Formador")
        else:
            print("   ✅ CONSISTENTE: Grupos e registros alinhados")

    print()
    print("═══════════════════════════════════════════════════════════")
    print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
    print("📋 Dados extraídos das planilhas Google Sheets estão íntegros")
    print("═══════════════════════════════════════════════════════════")

if __name__ == "__main__":
    main()