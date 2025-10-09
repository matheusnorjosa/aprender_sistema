#!/usr/bin/env python
"""
Script para limpeza completa dos dados existentes do sistema Django
Foco: Remover todos os dados para implementação limpa
"""
import os
import sys
import django
from django.db import transaction
from django.core.management import call_command

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Usuario, Projeto, Municipio, TipoEvento, Setor, Solicitacao


def cleanup_system_data():
    """Limpa todos os dados existentes do sistema"""
    print("🧹 INICIANDO LIMPEZA COMPLETA DO SISTEMA")
    print("=" * 60)

    try:
        with transaction.atomic():
            # 1. Limpar solicitações (devem ser removidas primeiro por dependências)
            print("📋 Removendo solicitações...")
            solicitacoes_count = Solicitacao.objects.count()
            Solicitacao.objects.all().delete()
            print(f"   ✅ {solicitacoes_count} solicitações removidas")

            # 2. Limpar usuários (exceto admin)
            print("👥 Removendo usuários...")
            usuarios_count = Usuario.objects.exclude(username="admin").count()
            Usuario.objects.exclude(username="admin").delete()
            print(f"   ✅ {usuarios_count} usuários removidos (admin preservado)")

            # 3. Limpar projetos
            print("📚 Removendo projetos...")
            projetos_count = Projeto.objects.count()
            Projeto.objects.all().delete()
            print(f"   ✅ {projetos_count} projetos removidos")

            # 4. Limpar municípios
            print("🌍 Removendo municípios...")
            municipios_count = Municipio.objects.count()
            Municipio.objects.all().delete()
            print(f"   ✅ {municipios_count} municípios removidos")

            # 5. Limpar tipos de evento
            print("🎯 Removendo tipos de evento...")
            tipos_count = TipoEvento.objects.count()
            TipoEvento.objects.all().delete()
            print(f"   ✅ {tipos_count} tipos de evento removidos")

            # 6. Limpar setores
            print("🏢 Removendo setores...")
            setores_count = Setor.objects.count()
            Setor.objects.all().delete()
            print(f"   ✅ {setores_count} setores removidos")

            print("\n🎉 LIMPEZA COMPLETA FINALIZADA!")
            print("=" * 60)

            # Verificar estado final
            print("📊 ESTADO FINAL DO SISTEMA:")
            print(f"   👥 Usuários: {Usuario.objects.count()}")
            print(f"   📚 Projetos: {Projeto.objects.count()}")
            print(f"   🌍 Municípios: {Municipio.objects.count()}")
            print(f"   🎯 Tipos de Evento: {TipoEvento.objects.count()}")
            print(f"   🏢 Setores: {Setor.objects.count()}")
            print(f"   📋 Solicitações: {Solicitacao.objects.count()}")

            return True

    except Exception as e:
        print(f"❌ Erro durante a limpeza: {e}")
        return False


def verify_admin_user():
    """Verifica se o usuário admin ainda existe"""
    print("\n🔍 VERIFICANDO USUÁRIO ADMIN...")

    try:
        admin_user = Usuario.objects.get(username="admin")
        print(f"   ✅ Admin encontrado: {admin_user.username}")
        print(f"   📧 Email: {admin_user.email}")
        print(f"   🔑 É superuser: {admin_user.is_superuser}")
        print(f"   👔 É staff: {admin_user.is_staff}")
        print(f"   ✅ É ativo: {admin_user.is_active}")
        return True
    except Usuario.DoesNotExist:
        print("   ❌ Usuário admin não encontrado!")
        return False


if __name__ == "__main__":
    print("🚀 INICIANDO LIMPEZA DO SISTEMA APRENDER")
    print("⚠️  ATENÇÃO: Esta operação irá remover TODOS os dados existentes!")
    print("=" * 60)

    # Confirmação automática para execução em container
    print("✅ Confirmação automática para execução em container")

    # Executar limpeza
    success = cleanup_system_data()

    if success:
        # Verificar admin
        admin_ok = verify_admin_user()

        if admin_ok:
            print("\n✅ SISTEMA LIMPO E PRONTO PARA NOVA IMPLEMENTAÇÃO!")
        else:
            print("\n⚠️  Sistema limpo, mas usuário admin não encontrado")
    else:
        print("\n❌ ERRO NA LIMPEZA - Verifique os logs")
        sys.exit(1)
