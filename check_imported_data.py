#!/usr/bin/env python3
"""
Verificar dados importados no sistema
"""

import os
import sys

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from core.models import Usuario, Setor, Municipio, Projeto, TipoEvento


def main():
    print("🔍 VERIFICAÇÃO DOS DADOS IMPORTADOS")
    print("=" * 50)

    print(f"\n📊 ESTATÍSTICAS GERAIS:")
    print(f"  • Usuários: {Usuario.objects.count()}")
    print(f"  • Setores: {Setor.objects.count()}")
    print(f"  • Municípios: {Municipio.objects.count()}")
    print(f"  • Projetos: {Projeto.objects.count()}")
    print(f"  • Tipos de Evento: {TipoEvento.objects.count()}")

    print(f"\n👥 USUÁRIOS IMPORTADOS:")
    for u in Usuario.objects.all()[:10]:
        print(f"  • {u.get_full_name() or u.username}")
        print(f"    Cargo: '{u.cargo}'")
        print(f"    Setor: {u.setor}")
        print(f"    Ativo: {u.is_active}")
        print()

    print(f"\n🏢 SETORES:")
    for s in Setor.objects.all():
        print(f"  • {s.nome} (sigla: {s.sigla})")

    print(f"\n🏘️ MUNICÍPIOS:")
    for m in Municipio.objects.all():
        print(f"  • {m.nome} - {m.uf}")

    print(f"\n📋 PROJETOS:")
    for p in Projeto.objects.all():
        print(f"  • {p.nome} (setor: {p.setor})")

    print(f"\n🏷️ TIPOS DE EVENTO:")
    for t in TipoEvento.objects.all():
        print(f"  • {t.nome} (online: {t.online})")


if __name__ == "__main__":
    main()
