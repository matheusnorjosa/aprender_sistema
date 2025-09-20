#!/usr/bin/env python3
"""
FastMCP Server Standalone - Sistema Aprender
============================================

Servidor FastMCP standalone para integração com Cursor.
Fornece ferramentas avançadas de consulta e análise do sistema.

Author: Claude Code
Date: Janeiro 2025
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')

import django
django.setup()

# Imports FastMCP
from fastmcp import FastMCP
from core.services.fastmcp_integration import AprenderSistemaMCP

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Inicia o servidor FastMCP"""
    try:
        # Inicializar servidor FastMCP
        mcp = AprenderSistemaMCP()
        
        if not mcp.enabled:
            logger.error("FastMCP não está habilitado")
            sys.exit(1)
        
        server = mcp.get_server()
        if not server:
            logger.error("Não foi possível obter o servidor FastMCP")
            sys.exit(1)
        
        logger.info("🚀 Iniciando FastMCP Server...")
        
        # Executar servidor
        asyncio.run(server.run())
        
    except KeyboardInterrupt:
        logger.info("🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
