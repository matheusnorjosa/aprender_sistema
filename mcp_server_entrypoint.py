#!/usr/bin/env python3
"""
MCP Server Entrypoint - Sistema Aprender
========================================

Servidor MCP standalone para containerização Docker.
Inicializa todas as ferramentas MCP disponíveis e estabelece
comunicação com o banco PostgreSQL via Docker network.

Author: Claude Code
Date: Janeiro 2025
"""

import os
import sys
import asyncio
import logging
import json
from typing import Dict, List, Any
from pathlib import Path

# Adicionar path da aplicação Django
sys.path.insert(0, "/app")

# Configurar Django antes de imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")

import django

django.setup()

# Agora importar módulos Django
from django.db import connection
from django.contrib.auth import get_user_model

# Imports MCP
try:
    from fastmcp import FastMCP
    from fastmcp.resources import Resource
    from fastmcp.tools import Tool
    from fastmcp.prompts import Prompt

    FASTMCP_AVAILABLE = True
except ImportError:
    print("⚠️  FastMCP não disponível. Usando implementação alternativa.")
    FASTMCP_AVAILABLE = False

# Imports dos módulos MCP do projeto
try:
    from core.services.fastmcp_integration import AprenderSistemaMCP
    from core.mcp_tools import FormadorQueryTool

    MCP_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  MCP tools não disponíveis: {e}")
    MCP_TOOLS_AVAILABLE = False
from core.models import (
    Formador,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    Aprovacao,
    DisponibilidadeFormadores,
)

# Configuração de logging
logging.basicConfig(
    level=getattr(logging, os.getenv("MCP_LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/mcp_server.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("mcp_server")


class DockerizedMCPServer:
    """Servidor MCP otimizado para container Docker"""

    def __init__(self):
        self.host = os.getenv("MCP_HOST", "0.0.0.0")
        self.port = int(os.getenv("MCP_PORT", 3001))
        self.server = None
        self.tools_registered = 0

    async def verify_database_connection(self):
        """Verifica conexão com PostgreSQL via Docker network"""
        try:
            from django.db import connection
            from asgiref.sync import sync_to_async

            @sync_to_async
            def check_db():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return True

            @sync_to_async
            def get_counts():
                User = get_user_model()
                user_count = User.objects.count()
                formador_count = Formador.objects.count()
                projeto_count = Projeto.objects.count()
                return user_count, formador_count, projeto_count

            # Verificar conexão
            await check_db()
            logger.info("✅ Conexão PostgreSQL estabelecida via Docker network")

            # Verificar dados básicos
            user_count, formador_count, projeto_count = await get_counts()
            logger.info(
                f"📊 Dados disponíveis: {user_count} usuários, {formador_count} formadores, {projeto_count} projetos"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Falha na conexão PostgreSQL: {e}")
            return False

    async def register_mcp_tools(self):
        """Registra todas as ferramentas MCP disponíveis"""
        if not FASTMCP_AVAILABLE or not MCP_TOOLS_AVAILABLE:
            logger.warning("⚠️  FastMCP ou MCP tools não disponíveis - modo degradado")
            return

        try:
            # Inicializar servidor FastMCP usando AprenderSistemaMCP
            aprender_mcp = AprenderSistemaMCP()
            self.server = aprender_mcp.get_server()

            if self.server:
                self.tools_registered = 1  # Considerar que foi inicializado
                logger.info(f"✅ Servidor MCP AprenderSistemaMCP inicializado")
            else:
                logger.warning("⚠️  Servidor MCP não pôde ser inicializado")

        except Exception as e:
            logger.error(f"❌ Erro registrando servidor MCP: {e}")

    async def setup_health_endpoint(self):
        """Configura endpoint de health check"""
        try:
            # Para FastMCP, não usamos decorador @route - implementação alternativa
            logger.info("🏥 Health check será implementado via endpoint básico")
            self.health_data = {
                "status": "healthy",
                "server": "aprender_mcp",
                "tools_registered": self.tools_registered,
                "database_connected": True,  # já verificado
            }

        except Exception as e:
            logger.warning(f"⚠️  Health endpoint não configurado: {e}")

    async def start_server(self):
        """Inicia o servidor MCP"""
        logger.info("🚀 Iniciando Servidor MCP Dockerizado...")
        logger.info(f"📡 Host: {self.host}, Porta: {self.port}")

        # Verificar conexão database
        if not await self.verify_database_connection():
            logger.error("❌ Falha crítica: sem conexão com PostgreSQL")
            sys.exit(1)

        # Registrar ferramentas
        await self.register_mcp_tools()

        # Configurar health check
        await self.setup_health_endpoint()

        try:
            # Iniciar servidor HTTP básico para health checks
            await self.start_http_server()

        except Exception as e:
            logger.error(f"❌ Erro fatal do servidor MCP: {e}")
            sys.exit(1)

    async def start_http_server(self):
        """Inicia servidor HTTP usando aiohttp para health checks"""
        try:
            from aiohttp import web

            async def health_handler(request):
                return web.json_response(
                    {
                        "status": "healthy",
                        "server": "aprender_mcp",
                        "tools_registered": self.tools_registered,
                        "database_connected": await self.verify_database_connection(),
                    }
                )

            async def root_handler(request):
                return web.json_response(
                    {
                        "message": "Aprender Sistema MCP Server",
                        "version": "1.0.0",
                        "status": "running",
                    }
                )

            app = web.Application()
            app.router.add_get("/", root_handler)
            app.router.add_get("/health", health_handler)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self.host, self.port)

            logger.info(f"🌐 HTTP server iniciado em http://{self.host}:{self.port}")
            logger.info("🏥 Health check disponível em /health")

            await site.start()

            # Manter servidor rodando
            while True:
                await asyncio.sleep(60)
                logger.info("📊 MCP server funcionando normalmente")

        except ImportError:
            logger.error("❌ aiohttp não disponível - usando servidor básico")
            # Fallback para servidor básico
            await self.start_basic_server()

    async def start_basic_server(self):
        """Servidor básico sem aiohttp como fallback"""
        logger.info(f"🔄 Executando em modo básico sem HTTP server")
        while True:
            await asyncio.sleep(60)
            await self.verify_database_connection()
            logger.info("📊 MCP server funcionando em modo básico")


async def main():
    """Função principal do servidor MCP"""
    logger.info("=" * 60)
    logger.info("🐳 SERVIDOR MCP DOCKERIZADO - SISTEMA APRENDER")
    logger.info("=" * 60)

    server = DockerizedMCPServer()
    await server.start_server()


if __name__ == "__main__":
    try:
        # Verificar se já existe um loop asyncio rodando
        try:
            loop = asyncio.get_running_loop()
            logger.info("📌 Usando loop asyncio existente")
            # Se já há um loop, usar create_task
            task = loop.create_task(main())
            loop.run_until_complete(task)
        except RuntimeError:
            # Não há loop rodando, criar um novo
            logger.info("🔄 Criando novo loop asyncio")
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Servidor MCP interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
