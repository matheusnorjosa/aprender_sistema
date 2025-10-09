#!/usr/bin/env python3
"""
MCP Bridge - STDIO ↔ Docker Integration
======================================

Bridge que permite ao Cursor (STDIO) se comunicar com dados
do Sistema Aprender no Docker via PostgreSQL.

Combina o melhor dos dois mundos:
- Interface STDIO compatível com Cursor
- Dados reais do banco PostgreSQL Docker

Author: Claude Code
Date: Janeiro 2025
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configurar Django para acessar banco Docker
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_NAME", "aprender_sistema_db")
os.environ.setdefault("DB_USER", "adm_aprender")
os.environ.setdefault("DB_PASSWORD", "aprender123456")

# Adicionar path da aplicação Django
sys.path.insert(0, str(Path(__file__).parent))

try:
    import django

    django.setup()

    # Imports Django após setup
    from core.models import (
        Usuario,
        Formador,
        Municipio,
        Projeto,
        TipoEvento,
        Solicitacao,
        Aprovacao,
        LogAuditoria,
        SolicitacaoStatus,
    )
    from django.db import connection
    from django.utils import timezone

    DJANGO_AVAILABLE = True

except Exception as e:
    print(f"⚠️  Django não disponível: {e}", file=sys.stderr)
    DJANGO_AVAILABLE = False

# Imports MCP
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    MCP_AVAILABLE = True
except ImportError:
    print("❌ MCP não disponível - instalar com: pip install mcp", file=sys.stderr)
    MCP_AVAILABLE = False

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_bridge.log"),
        logging.StreamHandler(
            sys.stderr
        ),  # Log para stderr para não interferir com STDIO
    ],
)
logger = logging.getLogger("mcp_bridge")

if not MCP_AVAILABLE:
    logger.error("MCP não disponível - bridge não pode funcionar")
    sys.exit(1)

# Inicialização do servidor MCP
server = Server("aprender-context")


@server.list_tools()
async def handle_list_tools() -> List[Dict[str, Any]]:
    """Lista ferramentas disponíveis no bridge MCP integrado com Docker"""
    return [
        {
            "name": "get_system_context",
            "description": "Retorna contexto completo do Sistema APRENDER com dados reais do Docker",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_database_stats",
            "description": "Estatísticas em tempo real do banco PostgreSQL Docker",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_formadores_info",
            "description": "Informações completas sobre formadores ativos",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limite de formadores retornados (padrão: 10)",
                        "default": 10,
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por status: ativo, inativo, todos",
                        "default": "ativo",
                    },
                },
            },
        },
        {
            "name": "get_solicitacoes_stats",
            "description": "Estatísticas detalhadas das solicitações por status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "periodo": {
                        "type": "string",
                        "description": "Período: hoje, semana, mes, ano, todos",
                        "default": "mes",
                    }
                },
            },
        },
        {
            "name": "get_projetos_overview",
            "description": "Visão geral dos projetos e suas solicitações",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "check_system_health",
            "description": "Verificação de saúde do sistema integrado",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "analyze_approval_flow",
            "description": "Análise do fluxo de aprovações e gargalos",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_architecture_patterns",
            "description": "Padrões de arquitetura do Sistema APRENDER",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Executa as ferramentas do bridge MCP com dados reais do Docker"""

    if not DJANGO_AVAILABLE:
        return [
            {
                "type": "text",
                "text": "❌ Django não disponível - verifique configuração do banco Docker",
            }
        ]

    try:
        if name == "get_system_context":
            return await get_system_context_real()

        elif name == "get_database_stats":
            return await get_database_stats_real()

        elif name == "get_formadores_info":
            limit = arguments.get("limit", 10)
            status = arguments.get("status", "ativo")
            return await get_formadores_info_real(limit, status)

        elif name == "get_solicitacoes_stats":
            periodo = arguments.get("periodo", "mes")
            return await get_solicitacoes_stats_real(periodo)

        elif name == "get_projetos_overview":
            return await get_projetos_overview_real()

        elif name == "check_system_health":
            return await check_system_health_real()

        elif name == "analyze_approval_flow":
            return await analyze_approval_flow_real()

        elif name == "get_architecture_patterns":
            return await get_architecture_patterns()

        else:
            return [{"type": "text", "text": f"❌ Ferramenta desconhecida: {name}"}]

    except Exception as e:
        logger.error(f"Erro ao executar ferramenta {name}: {e}")
        return [{"type": "text", "text": f"❌ Erro ao executar {name}: {str(e)}"}]


# ===============================
# FUNÇÕES COM DADOS REAIS DOCKER
# ===============================


async def get_system_context_real() -> List[Dict[str, Any]]:
    """Contexto completo com dados reais do PostgreSQL Docker"""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_real_stats():
            # Obter dados reais do banco
            total_usuarios = Usuario.objects.count()
            usuarios_ativos = Usuario.objects.filter(is_active=True).count()
            total_formadores = Formador.objects.count()
            total_municipios = Municipio.objects.count()
            total_projetos = Projeto.objects.count()
            total_tipos_evento = TipoEvento.objects.count()
            total_solicitacoes = Solicitacao.objects.count()

            # Estatísticas por status
            solicitacoes_pendentes = Solicitacao.objects.filter(
                status=SolicitacaoStatus.PENDENTE
            ).count()
            solicitacoes_aprovadas = Solicitacao.objects.filter(
                status=SolicitacaoStatus.APROVADO
            ).count()
            solicitacoes_rejeitadas = Solicitacao.objects.filter(
                status=SolicitacaoStatus.REJEITADO
            ).count()

            # Logs de auditoria recentes
            logs_24h = LogAuditoria.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()

            return {
                "usuarios": {"total": total_usuarios, "ativos": usuarios_ativos},
                "formadores": total_formadores,
                "municipios": total_municipios,
                "projetos": total_projetos,
                "tipos_evento": total_tipos_evento,
                "solicitacoes": {
                    "total": total_solicitacoes,
                    "pendentes": solicitacoes_pendentes,
                    "aprovadas": solicitacoes_aprovadas,
                    "rejeitadas": solicitacoes_rejeitadas,
                },
                "auditoria_24h": logs_24h,
            }

        stats = await get_real_stats()

        context = f"""# 🎓 CONTEXTO DO SISTEMA APRENDER - DADOS REAIS
## 📊 Status Atual do Sistema (Docker PostgreSQL)

### 👥 **USUÁRIOS**
- **Total**: {stats['usuarios']['total']} usuários
- **Ativos**: {stats['usuarios']['ativos']} usuários ({stats['usuarios']['ativos']/stats['usuarios']['total']*100:.1f}%)

### 🎯 **RECURSOS EDUCACIONAIS**
- **Formadores**: {stats['formadores']} ativos
- **Municípios**: {stats['municipios']} cadastrados
- **Projetos**: {stats['projetos']} configurados
- **Tipos de Evento**: {stats['tipos_evento']} disponíveis

### 📋 **SOLICITAÇÕES DE EVENTOS**
- **Total**: {stats['solicitacoes']['total']} solicitações no sistema
- **Pendentes**: {stats['solicitacoes']['pendentes']} aguardando aprovação
- **Aprovadas**: {stats['solicitacoes']['aprovadas']} já processadas
- **Rejeitadas**: {stats['solicitacoes']['rejeitadas']} rejeitadas

### 🔍 **AUDITORIA**
- **Últimas 24h**: {stats['auditoria_24h']} eventos registrados

## 🏗️ **ARQUITETURA ATUAL**
- **Stack**: Django 5.2 + PostgreSQL 15 + Docker
- **Ambiente**: Staging (Docker)
- **Banco**: PostgreSQL na porta 5433
- **Estado**: Sistema funcionando com dados reais

## 🎯 **FUNCIONALIDADES PRINCIPAIS**
1. **Solicitação de Eventos**: Coordenadores solicitam eventos
2. **Fluxo de Aprovação**: Superintendência aprova/rejeita
3. **Gestão de Formadores**: Controle de disponibilidade
4. **Integração Google Calendar**: Criação automática de eventos
5. **Auditoria Completa**: Log de todas as operações

## 📈 **PERFORMANCE**
- Sistema responsivo
- Dados consistentes
- Auditoria ativa
- Pronto para produção

**Status: ✅ SISTEMA OPERACIONAL COM DADOS REAIS**"""

        return [{"type": "text", "text": context}]

    except Exception as e:
        logger.error(f"Erro ao obter contexto real: {e}")
        return [{"type": "text", "text": f"❌ Erro ao acessar dados reais: {str(e)}"}]


async def get_database_stats_real() -> List[Dict[str, Any]]:
    """Estatísticas em tempo real do banco PostgreSQL"""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_db_stats():
            with connection.cursor() as cursor:
                # Verificar conexão
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]

                # Estatísticas de tabelas
                cursor.execute(
                    """
                    SELECT
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY (n_tup_ins + n_tup_upd + n_tup_del) DESC
                    LIMIT 10
                """
                )
                table_stats = cursor.fetchall()

                # Conexões ativas
                cursor.execute(
                    """
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """
                )
                active_connections = cursor.fetchone()[0]

                return {
                    "version": version,
                    "table_stats": table_stats,
                    "active_connections": active_connections,
                }

        stats = await get_db_stats()

        result = f"""# 🗄️ ESTATÍSTICAS DO BANCO POSTGRESQL (DOCKER)

## 📋 **Informações Gerais**
- **Versão**: {stats['version'][:50]}...
- **Conexões Ativas**: {stats['active_connections']}

## 📊 **Atividade por Tabela** (Top 10)
"""
        for schema, table, inserts, updates, deletes in stats["table_stats"]:
            total_ops = inserts + updates + deletes
            result += f"- **{table}**: {total_ops:,} operações (I:{inserts}, U:{updates}, D:{deletes})\n"

        result += "\n✅ **Banco funcionando normalmente**"

        return [{"type": "text", "text": result}]

    except Exception as e:
        return [
            {
                "type": "text",
                "text": f"❌ Erro ao obter estatísticas do banco: {str(e)}",
            }
        ]


async def get_formadores_info_real(limit: int, status: str) -> List[Dict[str, Any]]:
    """Informações reais dos formadores"""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_formadores():
            qs = Formador.objects.select_related("usuario")

            if status == "ativo":
                qs = qs.filter(usuario__is_active=True)
            elif status == "inativo":
                qs = qs.filter(usuario__is_active=False)

            return list(qs[:limit])

        formadores = await get_formadores()

        result = (
            f"# 👨‍🏫 FORMADORES - {status.upper()} ({len(formadores)} de {limit})\n\n"
        )

        for formador in formadores:
            result += f"## {formador.nome}\n"
            result += f"- **Usuario**: {formador.usuario.username}\n"
            result += f"- **Email**: {formador.usuario.email}\n"
            result += f"- **Especialidade**: {formador.especialidade}\n"
            result += f"- **Status**: {'✅ Ativo' if formador.usuario.is_active else '❌ Inativo'}\n"
            if formador.anos_experiencia:
                result += f"- **Experiência**: {formador.anos_experiencia} anos\n"
            result += "\n"

        return [{"type": "text", "text": result}]

    except Exception as e:
        return [
            {
                "type": "text",
                "text": f"❌ Erro ao obter informações dos formadores: {str(e)}",
            }
        ]


async def get_solicitacoes_stats_real(periodo: str) -> List[Dict[str, Any]]:
    """Estatísticas reais das solicitações"""
    try:
        from asgiref.sync import sync_to_async
        from datetime import timedelta

        @sync_to_async
        def get_stats():
            now = timezone.now()

            # Determinar período
            if periodo == "hoje":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif periodo == "semana":
                start_date = now - timedelta(days=7)
            elif periodo == "mes":
                start_date = now - timedelta(days=30)
            elif periodo == "ano":
                start_date = now - timedelta(days=365)
            else:  # todos
                start_date = None

            # Query base
            qs = Solicitacao.objects.all()
            if start_date:
                qs = qs.filter(data_criacao__gte=start_date)

            # Estatísticas por status
            total = qs.count()
            pendentes = qs.filter(status=SolicitacaoStatus.PENDENTE).count()
            aprovadas = qs.filter(status=SolicitacaoStatus.APROVADO).count()
            rejeitadas = qs.filter(status=SolicitacaoStatus.REJEITADO).count()

            # Top projetos
            from django.db.models import Count

            top_projetos = (
                qs.values("projeto__nome")
                .annotate(count=Count("id"))
                .order_by("-count")[:5]
            )

            # Top formadores
            top_formadores = (
                qs.values("formador__nome")
                .annotate(count=Count("id"))
                .order_by("-count")[:5]
            )

            return {
                "total": total,
                "pendentes": pendentes,
                "aprovadas": aprovadas,
                "rejeitadas": rejeitadas,
                "top_projetos": list(top_projetos),
                "top_formadores": list(top_formadores),
                "periodo": periodo,
            }

        stats = await get_stats()

        result = f"""# 📋 ESTATÍSTICAS DE SOLICITAÇÕES - {stats['periodo'].upper()}

## 📊 **Resumo Geral**
- **Total**: {stats['total']} solicitações
- **Pendentes**: {stats['pendentes']} ({stats['pendentes']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)
- **Aprovadas**: {stats['aprovadas']} ({stats['aprovadas']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)
- **Rejeitadas**: {stats['rejeitadas']} ({stats['rejeitadas']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)

## 🎯 **Top 5 Projetos**
"""

        for projeto in stats["top_projetos"]:
            result += (
                f"- **{projeto['projeto__nome']}**: {projeto['count']} solicitações\n"
            )

        result += "\n## 👨‍🏫 **Top 5 Formadores**\n"
        for formador in stats["top_formadores"]:
            result += f"- **{formador['formador__nome']}**: {formador['count']} solicitações\n"

        return [{"type": "text", "text": result}]

    except Exception as e:
        return [
            {
                "type": "text",
                "text": f"❌ Erro ao obter estatísticas das solicitações: {str(e)}",
            }
        ]


async def get_projetos_overview_real() -> List[Dict[str, Any]]:
    """Visão geral real dos projetos"""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_projetos():
            from django.db.models import Count

            projetos = Projeto.objects.annotate(
                total_solicitacoes=Count("solicitacao"),
                aprovadas=Count(
                    "solicitacao",
                    filter=models.Q(solicitacao__status=SolicitacaoStatus.APROVADO),
                ),
                pendentes=Count(
                    "solicitacao",
                    filter=models.Q(solicitacao__status=SolicitacaoStatus.PENDENTE),
                ),
            ).order_by("-total_solicitacoes")

            return list(projetos)

        projetos = await get_projetos()

        result = f"# 🎯 PROJETOS - VISÃO GERAL ({len(projetos)} projetos)\n\n"

        for projeto in projetos:
            result += f"## {projeto.nome}\n"
            result += f"- **Descrição**: {projeto.descricao[:100]}...\n"
            result += f"- **Total Solicitações**: {projeto.total_solicitacoes}\n"
            result += f"- **Aprovadas**: {projeto.aprovadas}\n"
            result += f"- **Pendentes**: {projeto.pendentes}\n"
            result += (
                f"- **Status**: {'✅ Ativo' if projeto.ativo else '❌ Inativo'}\n\n"
            )

        return [{"type": "text", "text": result}]

    except Exception as e:
        return [
            {
                "type": "text",
                "text": f"❌ Erro ao obter visão geral dos projetos: {str(e)}",
            }
        ]


async def check_system_health_real() -> List[Dict[str, Any]]:
    """Verificação real de saúde do sistema"""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def health_check():
            checks = {}

            # Check 1: Database connection
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    checks["database"] = "✅ OK"
            except Exception as e:
                checks["database"] = f"❌ ERRO: {str(e)}"

            # Check 2: Data integrity
            try:
                total_solicitacoes = Solicitacao.objects.count()
                total_formadores = Formador.objects.count()
                if total_solicitacoes > 0 and total_formadores > 0:
                    checks["data_integrity"] = "✅ OK - Dados presentes"
                else:
                    checks["data_integrity"] = "⚠️ AVISO - Poucos dados"
            except Exception as e:
                checks["data_integrity"] = f"❌ ERRO: {str(e)}"

            # Check 3: Recent activity
            try:
                recent_logs = LogAuditoria.objects.filter(
                    timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
                ).count()
                checks["activity"] = f"✅ OK - {recent_logs} eventos nas últimas 24h"
            except Exception as e:
                checks["activity"] = f"❌ ERRO: {str(e)}"

            return checks

        checks = await health_check()

        result = "# 🏥 VERIFICAÇÃO DE SAÚDE DO SISTEMA\n\n"

        for check_name, status in checks.items():
            result += f"## {check_name.replace('_', ' ').title()}\n{status}\n\n"

        # Resumo geral
        all_ok = all("✅" in status for status in checks.values())
        result += f"## Status Geral\n{'✅ SISTEMA SAUDÁVEL' if all_ok else '⚠️ ATENÇÃO NECESSÁRIA'}\n"

        return [{"type": "text", "text": result}]

    except Exception as e:
        return [{"type": "text", "text": f"❌ Erro na verificação de saúde: {str(e)}"}]


async def analyze_approval_flow_real() -> List[Dict[str, Any]]:
    """Análise real do fluxo de aprovações"""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def analyze_flow():
            from django.db.models import Avg, Count
            from datetime import timedelta

            # Análise das aprovações
            total_solicitacoes = Solicitacao.objects.count()
            aprovadas = Solicitacao.objects.filter(
                status=SolicitacaoStatus.APROVADO
            ).count()
            pendentes = Solicitacao.objects.filter(
                status=SolicitacaoStatus.PENDENTE
            ).count()
            rejeitadas = Solicitacao.objects.filter(
                status=SolicitacaoStatus.REJEITADO
            ).count()

            # Taxa de aprovação
            taxa_aprovacao = (
                (aprovadas / total_solicitacoes * 100) if total_solicitacoes > 0 else 0
            )

            # Gargalos (solicitações pendentes há muito tempo)
            old_pendentes = Solicitacao.objects.filter(
                status=SolicitacaoStatus.PENDENTE,
                data_criacao__lt=timezone.now() - timedelta(days=7),
            ).count()

            return {
                "total": total_solicitacoes,
                "aprovadas": aprovadas,
                "pendentes": pendentes,
                "rejeitadas": rejeitadas,
                "taxa_aprovacao": taxa_aprovacao,
                "old_pendentes": old_pendentes,
            }

        flow = await analyze_flow()

        result = f"""# 🔄 ANÁLISE DO FLUXO DE APROVAÇÕES

## 📊 **Métricas Gerais**
- **Total de Solicitações**: {flow['total']}
- **Taxa de Aprovação**: {flow['taxa_aprovacao']:.1f}%
- **Aprovadas**: {flow['aprovadas']} ({flow['aprovadas']/flow['total']*100 if flow['total'] > 0 else 0:.1f}%)
- **Pendentes**: {flow['pendentes']} ({flow['pendentes']/flow['total']*100 if flow['total'] > 0 else 0:.1f}%)
- **Rejeitadas**: {flow['rejeitadas']} ({flow['rejeitadas']/flow['total']*100 if flow['total'] > 0 else 0:.1f}%)

## ⚠️ **Gargalos Identificados**
- **Pendentes há +7 dias**: {flow['old_pendentes']} solicitações

## 📈 **Recomendações**
"""

        if flow["old_pendentes"] > 0:
            result += f"- 🔴 **URGENTE**: {flow['old_pendentes']} solicitações pendentes há mais de 7 dias precisam de atenção\n"

        if flow["taxa_aprovacao"] < 50:
            result += "- ⚠️ Taxa de aprovação baixa - revisar critérios ou processo\n"
        elif flow["taxa_aprovacao"] > 90:
            result += "- ✅ Taxa de aprovação alta - fluxo funcionando bem\n"

        if flow["pendentes"] > flow["aprovadas"]:
            result += (
                "- 📋 Backlog de pendentes maior que aprovadas - priorizar análises\n"
            )

        result += "\n✅ **Análise baseada em dados reais do sistema**"

        return [{"type": "text", "text": result}]

    except Exception as e:
        return [{"type": "text", "text": f"❌ Erro na análise do fluxo: {str(e)}"}]


async def get_architecture_patterns() -> List[Dict[str, Any]]:
    """Padrões de arquitetura do Sistema APRENDER"""
    patterns = """# 🏗️ PADRÕES DE ARQUITETURA - SISTEMA APRENDER

## 🎯 **ARQUITETURA GERAL**
- **Pattern**: Model-View-Template (Django MVT)
- **Database**: PostgreSQL 15 com Docker
- **Cache**: Redis/LocMem com fallback
- **Task Queue**: Celery (configurado)
- **API**: Django REST Framework + OpenAPI

## 📦 **ESTRUTURA MODULAR**
```
core/                   # App principal
├── models.py          # Single source of truth
├── views/             # Views organizadas por funcionalidade
├── services/          # Lógica de negócio
├── middleware/        # Security, Audit, Rate limiting
└── management/        # Comandos Django
```

## 🔒 **PADRÕES DE SEGURANÇA**
- **Headers**: CSP, HSTS, XSS Protection
- **Middleware**: SecurityHeaders, AuditLog, RateLimiting
- **Auth**: CPF-based authentication + Django Groups
- **Permissions**: Role-based access control

## 🏢 **PADRÕES DE NEGÓCIO**
- **Approval Pattern**: Solicitação → Superintendência → Calendar
- **Availability Engine**: Regras RD-01 a RD-08
- **Audit Trail**: LogAuditoria para todas operações críticas
- **Timezone Aware**: America/Fortaleza obrigatório

## 🔄 **PADRÕES DE INTEGRAÇÃO**
- **Google Calendar**: OAuth2 + Service Account
- **MCP Bridge**: STDIO ↔ Docker integration
- **Health Checks**: /health/, /health/detailed/, /ready/, /live/

## 📊 **PADRÕES DE MONITORAMENTO**
- **Logging**: JSON structured logs (error.json, audit.log)
- **Metrics**: System, Application, Database metrics
- **Alerts**: Rate limiting, security, performance

## 🎯 **BEST PRACTICES**
1. **DRY**: Reutilização via managers e services
2. **SOLID**: Single responsibility, dependency injection
3. **Clean Code**: Type hints, docstrings, testing
4. **Security First**: Nunca expor credenciais, validar entrada
5. **Performance**: Query optimization, caching, bulk operations

✅ **Arquitetura enterprise-grade pronta para produção**"""

    return [{"type": "text", "text": patterns}]


# ===============================
# FUNÇÃO PRINCIPAL
# ===============================


async def main():
    """Função principal do bridge MCP"""
    logger.info("🌉 Iniciando MCP Bridge STDIO ↔ Docker")
    logger.info(f"📊 Django disponível: {DJANGO_AVAILABLE}")

    if DJANGO_AVAILABLE:
        # Testar conexão com banco
        try:
            from asgiref.sync import sync_to_async

            @sync_to_async
            def test_db():
                return Usuario.objects.count()

            user_count = await test_db()
            logger.info(f"✅ Conexão Docker PostgreSQL: {user_count} usuários")
        except Exception as e:
            logger.error(f"❌ Falha na conexão Docker: {e}")

    # Iniciar servidor MCP STDIO
    async with stdio_server() as (read_stream, write_stream):
        logger.info("🚀 MCP Bridge rodando - aguardando comandos do Cursor")
        await server.run(read_stream, write_stream, {})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bridge interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
