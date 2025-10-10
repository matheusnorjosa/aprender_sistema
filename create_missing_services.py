#!/usr/bin/env python3
"""
🔧 CRIAÇÃO DE SERVICES FALTANTES - SISTEMA APRENDER
==================================================

Script para criar services que estão faltando para completar
o Single Source of Truth.

Author: Claude Code
Date: Setembro 2025
"""

import logging
import os
import sys

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.db.models import QuerySet

from core.models import Setor, TipoEvento

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_missing_services():
    """Cria services que estão faltando"""
    print("🔧 CRIANDO SERVICES FALTANTES")
    print("=" * 40)

    # Adicionar SetorService ao data_services.py
    add_setor_service()

    # Adicionar TipoEventoService ao data_services.py
    add_tipo_evento_service()

    # Atualizar __init__.py
    update_services_init()

    print("\n✅ Services criados com sucesso!")


def add_setor_service():
    """Adiciona SetorService ao data_services.py"""
    print("\n🏢 Criando SetorService...")

    setor_service_code = '''
class SetorService(BaseService):
    """
    Service para Setores - FONTE ÚNICA
    """

    @classmethod
    def get_base_queryset(cls) -> QuerySet:
        """QuerySet base otimizado para setores"""
        from core.models import Setor
        return Setor.objects.all().order_by('nome')

    @classmethod
    def ativos(cls) -> QuerySet:
        """Setores ativos"""
        return cls.get_base_queryset().filter(ativo=True)

    @classmethod
    def superintendencia(cls) -> QuerySet:
        """Setor superintendência"""
        return cls.ativos().filter(vinculado_superintendencia=True)

    @classmethod
    def outros_setores(cls) -> QuerySet:
        """Outros setores (não superintendência)"""
        return cls.ativos().filter(vinculado_superintendencia=False)
'''

    # Adicionar ao final do arquivo data_services.py
    with open("core/services/data_services.py", "a", encoding="utf-8") as f:
        f.write(setor_service_code)

    print("  ✅ SetorService adicionado")


def add_tipo_evento_service():
    """Adiciona TipoEventoService ao data_services.py"""
    print("\n📅 Criando TipoEventoService...")

    tipo_evento_service_code = '''
class TipoEventoService(BaseService):
    """
    Service para Tipos de Evento - FONTE ÚNICA
    """

    @classmethod
    def get_base_queryset(cls) -> QuerySet:
        """QuerySet base otimizado para tipos de evento"""
        from core.models import TipoEvento
        return TipoEvento.objects.all().order_by('nome')

    @classmethod
    def ativos(cls) -> QuerySet:
        """Tipos de evento ativos"""
        return cls.get_base_queryset().filter(ativo=True)

    @classmethod
    def online(cls) -> QuerySet:
        """Tipos de evento online"""
        return cls.ativos().filter(online=True)

    @classmethod
    def presenciais(cls) -> QuerySet:
        """Tipos de evento presenciais"""
        return cls.ativos().filter(online=False)

    @classmethod
    def para_formulario(cls) -> QuerySet:
        """Tipos de evento para uso em formulários"""
        return cls.ativos().order_by('nome')
'''

    # Adicionar ao final do arquivo data_services.py
    with open("core/services/data_services.py", "a", encoding="utf-8") as f:
        f.write(tipo_evento_service_code)

    print("  ✅ TipoEventoService adicionado")


def update_services_init():
    """Atualiza __init__.py para incluir novos services"""
    print("\n📦 Atualizando __init__.py...")

    init_content = '''"""
Services Layer - Centralizacao da logica de negocio
Implementa Single Source of Truth e DRY principles
"""

from .data_services import (
    UsuarioService,
    FormadorService,
    CoordinatorService,
    DashboardService,
    MunicipioService,
    SetorService,
    TipoEventoService
)
from .data_master_service import (
    DataMasterService,
    ProjetoService,
    MunicipioServiceCentralizado
)

__all__ = [
    'UsuarioService',
    'FormadorService',
    'CoordinatorService',
    'DashboardService',
    'MunicipioService',
    'SetorService',
    'TipoEventoService',
    'DataMasterService',
    'ProjetoService',
    'MunicipioServiceCentralizado'
]
'''

    with open("core/services/__init__.py", "w", encoding="utf-8") as f:
        f.write(init_content)

    print("  ✅ __init__.py atualizado")


def main():
    """Função principal"""
    try:
        create_missing_services()

    except Exception as e:
        logger.error(f"❌ Erro ao criar services: {str(e)}")
        raise


if __name__ == "__main__":
    main()
