#!/usr/bin/env python3
"""
Servidor MCP para fornecer contexto do Sistema APRENDER
Adaptado para estrutura existente do projeto.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Union
from mcp.server import Server
from mcp.server.stdio import stdio_server
import ijson
import orjson
from mistletoe import Document
import pandas as pd
import numpy as np

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do servidor MCP
server = Server("aprender-context")

# Diretório base da documentação (pasta raiz do projeto)
DOCS_DIR = Path(__file__).parent.parent

@server.list_tools()
async def handle_list_tools() -> List[Dict[str, Any]]:
    """Lista ferramentas disponíveis no servidor MCP"""
    return [
        {
            "name": "get_architecture_patterns",
            "description": "Retorna padrões de arquitetura do Sistema APRENDER",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_python_patterns",
            "description": "Retorna padrões de código Python/Django do sistema",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_security_guidelines",
            "description": "Retorna diretrizes de segurança do sistema",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_business_rules",
            "description": "Retorna regras de negócio específicas do Sistema APRENDER",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_category": {
                        "type": "string",
                        "description": "Categoria da regra (approval, permissions, hierarchy, availability, calendar)"
                    }
                },
            },
        },
        {
            "name": "validate_code_pattern",
            "description": "Valida se código segue padrões do Sistema APRENDER",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Código Python/Django para validar"
                    },
                    "context": {
                        "type": "string",
                        "description": "Contexto do código (view, model, service, api, command, form)"
                    }
                },
            },
        },
        {
            "name": "check_security_vulnerabilities",
            "description": "Verifica vulnerabilidades de segurança no código",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Código Python/Django para analisar"
                    }
                },
            }
        },
        {
            "name": "get_system_context",
            "description": "Retorna contexto completo do Sistema APRENDER",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_project_structure",
            "description": "Retorna estrutura e organização do projeto Django",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "process_large_json",
            "description": "Processa arquivos JSON grandes de forma eficiente (streaming/chunking)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Caminho para o arquivo JSON"
                    },
                    "method": {
                        "type": "string",
                        "description": "Método: 'streaming', 'chunks', ou 'auto'",
                        "default": "auto"
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Tamanho do chunk (padrão: 1000)",
                        "default": 1000
                    }
                },
                "required": ["filename"]
            },
        },
        {
            "name": "process_large_markdown",
            "description": "Processa arquivos Markdown grandes dividindo por seções",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Caminho para o arquivo Markdown"
                    },
                    "method": {
                        "type": "string",
                        "description": "Método: 'sections' ou 'tokens'",
                        "default": "sections"
                    }
                },
                "required": ["filename"]
            },
        },
        {
            "name": "analyze_file_structure",
            "description": "Analisa estrutura de arquivos grandes sem carregar tudo na memória",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Caminho para o arquivo"
                    }
                },
                "required": ["filename"]
            },
        },
        {
            "name": "analyze_data_with_pandas",
            "description": "Análise avançada de dados usando Pandas - estatísticas, agrupamentos, filtros e insights",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data_source": {
                        "type": "string",
                        "description": "Fonte dos dados: 'json_file', 'csv_file', 'system_data' ou dados JSON diretos"
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "Tipo de análise: 'statistics', 'grouping', 'filtering', 'insights', 'summary'",
                        "enum": ["statistics", "grouping", "filtering", "insights", "summary", "correlation"]
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Colunas específicas para análise (opcional)"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filtros para aplicar aos dados (opcional)"
                    },
                    "group_by": {
                        "type": "string",
                        "description": "Coluna para agrupamento (opcional)"
                    }
                },
                "required": ["data_source", "analysis_type"]
            },
        }
    ]

def _read_documentation_file(filename: str) -> Optional[str]:
    """Lê um arquivo de documentação."""
    file_path = DOCS_DIR / filename
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erro ao ler arquivo {filename}: {e}")
    return None

def _extract_section_from_content(content: str, section_name: str) -> str:
    """Extrai uma seção específica do conteúdo baseado no cabeçalho."""
    if not content:
        return f"Conteúdo não encontrado para seção '{section_name}'"

    lines = content.split('\n')
    section_lines = []
    in_section = False
    current_level = 0

    for line in lines:
        # Detectar início da seção
        if section_name.lower() in line.lower() and line.strip().startswith('#'):
            in_section = True
            current_level = len(line) - len(line.lstrip('#'))
            section_lines.append(line)
            continue

        # Se estamos na seção
        if in_section:
            # Verificar se chegou em uma nova seção do mesmo nível ou superior
            if line.strip().startswith('#'):
                line_level = len(line) - len(line.lstrip('#'))
                if line_level <= current_level:
                    break
            section_lines.append(line)

    if section_lines:
        return "\n".join(section_lines)
    else:
        return f"Seção '{section_name}' não encontrada no documento"

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Executa as ferramentas do servidor MCP"""

    try:
        if name == "get_architecture_patterns":
            content = _read_documentation_file("ARQUITETURA_REFERENCIA.md")
            if content:
                return [{"type": "text", "text": content}]
            return [{"type": "text", "text": "📋 Arquivo de arquitetura não encontrado. Verifique se ARQUITETURA_REFERENCIA.md existe na raiz do projeto."}]

        elif name == "get_python_patterns":
            content = _read_documentation_file("PADROES_CODIGO_PYTHON.md")
            if content:
                return [{"type": "text", "text": content}]
            return [{"type": "text", "text": "📋 Arquivo de padrões Python não encontrado. Verifique se PADROES_CODIGO_PYTHON.md existe na raiz do projeto."}]

        elif name == "get_security_guidelines":
            content = _read_documentation_file("GUIA_SEGURANCA.md")
            if content:
                return [{"type": "text", "text": content}]
            return [{"type": "text", "text": "📋 Arquivo de segurança não encontrado. Verifique se GUIA_SEGURANCA.md existe na raiz do projeto."}]

        elif name == "get_business_rules":
            category = arguments.get("rule_category", "all")

            # Buscar regras específicas na documentação
            context_content = _read_documentation_file("CLAUDE_CONTEXT_PACKAGE.md")
            claude_content = _read_documentation_file("CLAUDE.md")

            if category == "approval":
                # Buscar informações de aprovação em ambos arquivos
                approval_info = []
                if context_content:
                    section = _extract_section_from_content(context_content, "aprovação")
                    if "não encontrada" not in section:
                        approval_info.append("=== CLAUDE_CONTEXT_PACKAGE.md ===")
                        approval_info.append(section)

                if claude_content:
                    section = _extract_section_from_content(claude_content, "aprovação")
                    if "não encontrada" not in section:
                        approval_info.append("=== CLAUDE.md ===")
                        approval_info.append(section)

                if approval_info:
                    return [{"type": "text", "text": "\n\n".join(approval_info)}]

            elif category == "permissions":
                permission_info = []
                if context_content:
                    section = _extract_section_from_content(context_content, "permissões")
                    if "não encontrada" not in section:
                        permission_info.append(section)

                if permission_info:
                    return [{"type": "text", "text": "\n".join(permission_info)}]

            elif category == "hierarchy":
                hierarchy_info = []
                if context_content:
                    section = _extract_section_from_content(context_content, "hierarquia")
                    if "não encontrada" not in section:
                        hierarchy_info.append(section)

                if hierarchy_info:
                    return [{"type": "text", "text": "\n".join(hierarchy_info)}]

            elif category == "availability":
                # Regras específicas de disponibilidade do Sistema APRENDER
                availability_rules = """
# Regras de Disponibilidade - Sistema APRENDER

## Códigos de Disponibilidade
- **E** → Evento confirmado
- **M** → Mais de um evento
- **D** → Deslocamento
- **P** → Bloqueio parcial
- **T** → Bloqueio total
- **X** → Conflito

## Regras de Negócio
1. **Não-sobreposição**: Um formador não pode ter dois eventos sobrepostos
2. **Bloqueio Total (T)**: Impede quaisquer eventos no intervalo
3. **Bloqueio Parcial (P)**: Impede eventos apenas no subintervalo bloqueado
4. **Buffer de Deslocamento**: Tempo mínimo entre municípios diferentes
5. **Timezone**: Sempre usar America/Fortaleza (UTC-3)

## Verificações Obrigatórias
- Conflitos por eventos aprovados
- Bloqueios de formadores
- Buffer de deslocamento entre municípios
- Limite diário de horas por formador
"""
                return [{"type": "text", "text": availability_rules}]

            elif category == "calendar":
                calendar_rules = """
# Integração Google Calendar - Sistema APRENDER

## Fluxo de Integração
1. Solicitação → Aprovação Manual → Criação no Calendar
2. NUNCA criar eventos automaticamente sem aprovação
3. Sempre gerar link Google Meet automaticamente
4. Usar timezone America/Fortaleza

## Configurações
- **Calendar ID**: Configurado em settings.py
- **OAuth2**: Service Account configurado
- **Escopo**: calendar.events scope obrigatório

## Política de Aprovação Manual (PA-01 a PA-07)
- PA-01: Sem auto-aprovação
- PA-02: Apenas Superintendência pode aprovar
- PA-03: Integrações só após aprovação manual
"""
                return [{"type": "text", "text": calendar_rules}]

            # Se categoria não específica ou 'all', retornar contexto completo
            if context_content:
                return [{"type": "text", "text": context_content}]

            return [{"type": "text", "text": f"📋 Regras para categoria '{category}' não encontradas nos documentos disponíveis."}]

        elif name == "validate_code_pattern":
            code = arguments.get("code", "")
            context = arguments.get("context", "")

            validation_results = []

            # Verificações básicas Python/Django
            if "def " in code:
                # Verificar type hints
                if "->" not in code and ":" not in code.split("def ")[1].split("(")[0]:
                    validation_results.append("⚠️ AVISO: Função sem type hints (requerido no Sistema APRENDER)")

                # Verificar docstring
                if '"""' not in code and "'''" not in code:
                    validation_results.append("⚠️ AVISO: Função sem docstring (padrão Sistema APRENDER)")

            # Verificar uso de logging em vez de print
            if "print(" in code:
                validation_results.append("❌ ERRO: Usar logging em vez de print (padrão Sistema APRENDER)")

            # Verificar tratamento de exceções
            if "except:" in code and "except Exception" not in code:
                validation_results.append("⚠️ AVISO: Bloco except muito genérico (especificar Exception)")

            # Verificações específicas por contexto Django
            if context == "view":
                if "request.POST" in code or "request.GET" in code:
                    if "clean(" not in code and "is_valid(" not in code:
                        validation_results.append("❌ ERRO: Dados de entrada não validados (usar forms.is_valid())")

                if not any(perm in code for perm in ["@login_required", "@permission_required", "has_perm"]):
                    validation_results.append("❌ ERRO: View sem verificação de permissão (obrigatório no Sistema APRENDER)")

                # Verificar timezone awareness
                if "datetime.now()" in code:
                    validation_results.append("⚠️ AVISO: Usar timezone.now() em vez de datetime.now() (timezone aware)")

            elif context == "model":
                if "models.Model" not in code and "class" in code:
                    validation_results.append("❌ ERRO: Model não herda de models.Model")

                if "class Meta:" not in code and "class" in code:
                    validation_results.append("⚠️ AVISO: Model sem classe Meta (recomendado para Sistema APRENDER)")

                # Verificar timezone em DateTimeField
                if "DateTimeField" in code and "timezone" not in code:
                    validation_results.append("⚠️ AVISO: DateTimeField deve ser timezone-aware")

            elif context == "service":
                # Verificações específicas para services do Sistema APRENDER
                if "from core.models import" not in code and "import" in code:
                    validation_results.append("⚠️ AVISO: Services devem importar models da core")

                if "transaction.atomic" not in code and ("save(" in code or "delete(" in code):
                    validation_results.append("⚠️ AVISO: Operações de BD em services devem usar transaction.atomic")

            elif context == "command":
                # Verificações para management commands
                if "BaseCommand" not in code:
                    validation_results.append("❌ ERRO: Command deve herdar de BaseCommand")

                if "handle(" not in code:
                    validation_results.append("❌ ERRO: Command deve implementar método handle()")

            elif context == "form":
                # Verificações para forms Django
                if "forms.Form" not in code and "forms.ModelForm" not in code:
                    validation_results.append("❌ ERRO: Form deve herdar de forms.Form ou forms.ModelForm")

                if "clean_" in code and "ValidationError" not in code:
                    validation_results.append("⚠️ AVISO: Método clean_ deve usar ValidationError para erros")

            result = "\n".join(validation_results) if validation_results else "✅ Código segue os padrões do Sistema APRENDER"
            return [{"type": "text", "text": result}]

        elif name == "check_security_vulnerabilities":
            code = arguments.get("code", "")

            vulnerabilities = []

            # Verificar SQL injection potencial
            if "execute(" in code and ("%" in code or ".format(" in code or "f\"" in code):
                vulnerabilities.append("🔴 RISCO: Possível SQL injection - usar parâmetros nomeados ou ORM Django")

            # Verificar hardcoded secrets
            secret_indicators = ["password", "secret", "key", "token", "api_key"]
            if any(secret in code.lower() for secret in secret_indicators):
                if "=" in code and ("'" in code or '"' in code):
                    vulnerabilities.append("🔴 RISCO: Possível segredo hardcoded - usar variáveis de ambiente")

            # Verificar validação de entrada Django
            if "request.POST" in code or "request.GET" in code:
                if "is_valid(" not in code and "clean(" not in code:
                    vulnerabilities.append("🔴 RISCO: Dados de entrada não validados - usar Django Forms")

            # Verificar XSS em templates/responses
            if "HttpResponse" in code and "mark_safe" in code:
                vulnerabilities.append("🟡 RISCO: Uso de mark_safe pode permitir XSS - validar conteúdo")

            # Verificar permissões em operações críticas
            critical_operations = ["delete(", "update(", "save(", "create("]
            if any(op in code for op in critical_operations):
                if "has_perm" not in code and "permission_required" not in code:
                    vulnerabilities.append("🔴 RISCO: Operação crítica sem verificação de permissão")

            # Verificar uso seguro de eval/exec
            if "eval(" in code or "exec(" in code:
                vulnerabilities.append("🔴 RISCO: Uso de eval/exec é perigoso - evitar ou validar entrada")

            # Verificar configurações Django em produção
            if "DEBUG = True" in code:
                vulnerabilities.append("🟡 RISCO: DEBUG=True não deve ser usado em produção")

            # Verificar CSRF protection
            if "@csrf_exempt" in code:
                vulnerabilities.append("🟡 RISCO: csrf_exempt remove proteção CSRF - usar apenas se necessário")

            result = "\n".join(vulnerabilities) if vulnerabilities else "✅ Nenhuma vulnerabilidade óbvia detectada"
            return [{"type": "text", "text": result}]

        elif name == "get_system_context":
            context_content = _read_documentation_file("CLAUDE_CONTEXT_PACKAGE.md")
            if context_content:
                return [{"type": "text", "text": context_content}]
            return [{"type": "text", "text": "📋 Contexto do sistema não encontrado. Verifique se CLAUDE_CONTEXT_PACKAGE.md existe."}]

        elif name == "get_project_structure":
            structure_info = """
# Estrutura do Sistema APRENDER

## Organização de Pastas
```
Sistema APRENDER/
├── aprender_sistema/           # Configurações Django
│   ├── settings.py            # Configurações unificadas
│   ├── urls.py               # URLs principais
│   └── wsgi.py               # WSGI para produção
├── core/                     # App principal Django
│   ├── models.py            # Modelos de dados
│   ├── admin.py             # Django Admin
│   ├── views/               # Views organizadas
│   │   ├── base.py         # Views base e dashboard
│   │   ├── gestao_views.py # Gestão de recursos
│   │   ├── mapa_views.py   # Mapa de disponibilidade
│   │   └── diretoria_views.py # Aprovações
│   ├── templates/core/      # Templates Django
│   ├── services/            # Serviços de negócio
│   │   ├── data_services.py # Processamento dados
│   │   └── calendar_codes.py # Google Calendar
│   ├── management/commands/ # Comandos Django
│   └── migrations/          # Migrações BD
├── neural_system/           # Sistema MCP (IA)
├── docs/                    # Documentação
├── scripts/                 # Scripts auxiliares
├── tests/                   # Testes
├── static/                  # Arquivos estáticos
└── requirements.txt         # Dependências
```

## Convenções do Projeto
- **Models**: core/models.py (um arquivo para simplicidade)
- **Views**: Separadas por funcionalidade em core/views/
- **Services**: Lógica de negócio em core/services/
- **Templates**: Organizados em core/templates/core/
- **URLs**: Sistema de namespaces e nomes descritivos
- **Timezone**: Sempre America/Fortaleza
- **Ambiente**: Docker unificado (desenvolvimento/produção)
"""
            return [{"type": "text", "text": structure_info}]

        elif name == "process_large_json":
            filename = arguments.get("filename", "")
            method = arguments.get("method", "auto")
            chunk_size = arguments.get("chunk_size", 1000)
            
            if not filename:
                return [{"type": "text", "text": "❌ Erro: filename é obrigatório"}]
            
            try:
                # Análise do arquivo
                analysis = _analyze_file_structure(filename)
                if analysis.get("error"):
                    return [{"type": "text", "text": f"❌ Erro ao analisar arquivo: {analysis['error']}"}]
                
                # Determinar método se auto
                if method == "auto":
                    method = analysis.get("recommended_method", "chunks")
                
                # Processar arquivo
                if method == "streaming":
                    chunks = list(_process_json_streaming(filename))
                    result = f"✅ Processado via streaming: {len(chunks)} itens encontrados"
                else:
                    chunks = list(_process_json_chunks(filename, chunk_size))
                    result = f"✅ Processado via chunks: {len(chunks)} chunks de {chunk_size} itens"
                
                # Adicionar informações da análise
                result += f"\n\n📊 Análise do arquivo:\n"
                result += f"• Tamanho: {analysis.get('size_mb', 0):.2f} MB\n"
                result += f"• Tokens estimados: {analysis.get('estimated_tokens', 0):,}\n"
                result += f"• Método recomendado: {analysis.get('recommended_method', 'chunks')}\n"
                
                return [{"type": "text", "text": result}]
                
            except Exception as e:
                return [{"type": "text", "text": f"❌ Erro ao processar arquivo: {str(e)}"}]

        elif name == "process_large_markdown":
            filename = arguments.get("filename", "")
            method = arguments.get("method", "sections")
            
            if not filename:
                return [{"type": "text", "text": "❌ Erro: filename é obrigatório"}]
            
            try:
                # Análise do arquivo
                analysis = _analyze_file_structure(filename)
                if analysis.get("error"):
                    return [{"type": "text", "text": f"❌ Erro ao analisar arquivo: {analysis['error']}"}]
                
                # Processar arquivo
                if method == "sections":
                    sections = list(_process_markdown_sections(filename))
                    result = f"✅ Processado por seções: {len(sections)} seções encontradas"
                else:
                    chunks = list(_process_markdown_tokens(filename))
                    result = f"✅ Processado por tokens: {len(chunks)} chunks encontrados"
                
                # Adicionar informações da análise
                result += f"\n\n📊 Análise do arquivo:\n"
                result += f"• Tamanho: {analysis.get('size_mb', 0):.2f} MB\n"
                result += f"• Tokens estimados: {analysis.get('estimated_tokens', 0):,}\n"
                
                if analysis.get("structure_info", {}).get("sections"):
                    result += f"• Seções identificadas: {analysis['structure_info']['sections']}\n"
                    if analysis["structure_info"].get("section_titles"):
                        result += f"• Primeiras seções: {', '.join(analysis['structure_info']['section_titles'][:5])}\n"
                
                return [{"type": "text", "text": result}]
                
            except Exception as e:
                return [{"type": "text", "text": f"❌ Erro ao processar arquivo: {str(e)}"}]

        elif name == "analyze_file_structure":
            filename = arguments.get("filename", "")
            
            if not filename:
                return [{"type": "text", "text": "❌ Erro: filename é obrigatório"}]
            
            try:
                analysis = _analyze_file_structure(filename)
                
                if analysis.get("error"):
                    return [{"type": "text", "text": f"❌ Erro: {analysis['error']}"}]
                
                result = f"📊 Análise do arquivo: {analysis['filename']}\n\n"
                result += f"📁 Informações básicas:\n"
                result += f"• Tamanho: {analysis['size_bytes']:,} bytes ({analysis['size_mb']:.2f} MB)\n"
                result += f"• Extensão: {analysis['extension']}\n"
                result += f"• Tokens estimados: {analysis['estimated_tokens']:,}\n"
                result += f"• Método recomendado: {analysis['recommended_method']}\n\n"
                
                if analysis.get("structure_info"):
                    result += f"🏗️ Estrutura:\n"
                    for key, value in analysis["structure_info"].items():
                        if isinstance(value, list):
                            result += f"• {key}: {len(value)} itens\n"
                            if len(value) <= 10:
                                result += f"  - {', '.join(map(str, value))}\n"
                        else:
                            result += f"• {key}: {value}\n"
                
                return [{"type": "text", "text": result}]
                
            except Exception as e:
                return [{"type": "text", "text": f"❌ Erro ao analisar arquivo: {str(e)}"}]

        elif name == "analyze_data_with_pandas":
            data_source = arguments.get("data_source", "")
            analysis_type = arguments.get("analysis_type", "")
            columns = arguments.get("columns", [])
            filters = arguments.get("filters", {})
            group_by = arguments.get("group_by", "")
            
            if not data_source or not analysis_type:
                return [{"type": "text", "text": "❌ Erro: data_source e analysis_type são obrigatórios"}]
            
            try:
                # Carregar dados
                df = _load_data_with_pandas(data_source)
                if df is None:
                    return [{"type": "text", "text": f"❌ Erro: Não foi possível carregar dados de {data_source}"}]
                
                # Aplicar filtros se fornecidos
                if filters:
                    df = _apply_pandas_filters(df, filters)
                
                # Selecionar colunas específicas se fornecidas
                if columns:
                    available_columns = [col for col in columns if col in df.columns]
                    if available_columns:
                        df = df[available_columns]
                
                # Executar análise
                result = _perform_pandas_analysis(df, analysis_type, group_by)
                
                return [{"type": "text", "text": result}]
                
            except Exception as e:
                return [{"type": "text", "text": f"❌ Erro na análise com Pandas: {str(e)}"}]

        else:
            return [{"type": "text", "text": f"❌ Ferramenta desconhecida: {name}"}]

    except Exception as e:
        logger.error(f"Erro ao executar ferramenta {name}: {e}")
        return [{"type": "text", "text": f"❌ Erro ao executar ferramenta: {str(e)}"}]

async def main():
    """Função principal do servidor MCP"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, {})

# Funções auxiliares para processamento de arquivos grandes

def _analyze_file_structure(filename: str) -> Dict[str, Any]:
    """Analisa estrutura do arquivo sem carregar tudo na memória"""
    try:
        file_path = Path(filename)
        if not file_path.exists():
            return {"error": f"Arquivo não encontrado: {filename}"}
        
        file_size = file_path.stat().st_size
        
        analysis = {
            'filename': filename,
            'size_bytes': file_size,
            'size_mb': file_size / (1024 * 1024),
            'extension': file_path.suffix.lower(),
            'estimated_tokens': 0,
            'recommended_method': '',
            'structure_info': {}
        }
        
        # Estimar tokens (aproximadamente 4 caracteres por token)
        analysis['estimated_tokens'] = file_size // 4
        
        if file_path.suffix.lower() == '.json':
            analysis['recommended_method'] = 'streaming' if file_size > 5 * 1024 * 1024 else 'chunks'
            
            # Analisar estrutura JSON
            try:
                with open(filename, 'rb') as f:
                    parser = ijson.parse(f)
                    structure = {}
                    for prefix, event, value in parser:
                        if event == 'start_map':
                            structure[prefix] = 'object'
                        elif event == 'start_array':
                            structure[prefix] = 'array'
                        elif event in ['string', 'number', 'boolean']:
                            structure[prefix] = type(value).__name__
                    analysis['structure_info'] = structure
            except Exception as e:
                analysis['structure_info'] = {'error': f'Não foi possível analisar estrutura: {str(e)}'}
        
        elif file_path.suffix.lower() in ['.md', '.txt']:
            analysis['recommended_method'] = 'sections'
            
            # Analisar estrutura Markdown
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    sections = re.findall(r'^## ([^#\n]+)', content, re.MULTILINE)
                    analysis['structure_info'] = {
                        'sections': len(sections),
                        'section_titles': sections[:10]  # Primeiras 10 seções
                    }
            except Exception as e:
                analysis['structure_info'] = {'error': f'Não foi possível analisar estrutura: {str(e)}'}
        
        return analysis
        
    except Exception as e:
        return {"error": f"Erro ao analisar arquivo: {str(e)}"}

def _process_json_streaming(filename: str) -> Iterator[Dict[str, Any]]:
    """Processa JSON em streaming usando ijson"""
    try:
        with open(filename, 'rb') as file:
            for item in ijson.items(file, 'item'):
                yield item
    except Exception as e:
        logger.error(f"Erro no processamento streaming: {e}")
        return

def _process_json_chunks(filename: str, chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
    """Processa JSON em chunks usando orjson"""
    try:
        with open(filename, 'rb') as file:
            data = orjson.loads(file.read())
            
            if isinstance(data, list):
                for i in range(0, len(data), chunk_size):
                    yield data[i:i+chunk_size]
            elif isinstance(data, dict):
                # Para objetos, divide por chaves
                keys = list(data.keys())
                for i in range(0, len(keys), chunk_size):
                    chunk_keys = keys[i:i+chunk_size]
                    yield {k: data[k] for k in chunk_keys}
    except Exception as e:
        logger.error(f"Erro no processamento por chunks: {e}")
        return

def _process_markdown_sections(filename: str) -> Iterator[str]:
    """Processa Markdown dividindo por seções (## )"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Divide por seções principais
        sections = re.split(r'\n(?=## )', content)
        
        for section in sections:
            if section.strip():
                yield section.strip()
    except Exception as e:
        logger.error(f"Erro no processamento Markdown: {e}")
        return

def _process_markdown_tokens(filename: str, max_tokens: int = 20000) -> Iterator[str]:
    """Processa Markdown dividindo por tokens"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Divide por parágrafos primeiro
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Estimar tokens (aproximadamente 4 caracteres por token)
            estimated_tokens = len(current_chunk + paragraph) // 4
            
            if estimated_tokens > max_tokens:
                if current_chunk:
                    yield current_chunk
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            yield current_chunk
    except Exception as e:
        logger.error(f"Erro no processamento por tokens: {e}")
        return

# Funções auxiliares para análise com Pandas

def _load_data_with_pandas(data_source: str) -> Optional[pd.DataFrame]:
    """Carrega dados de diferentes fontes usando Pandas"""
    try:
        if data_source.startswith('json_file:'):
            # Carregar de arquivo JSON
            filename = data_source.replace('json_file:', '')
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.json_normalize(data)
        
        elif data_source.startswith('csv_file:'):
            # Carregar de arquivo CSV
            filename = data_source.replace('csv_file:', '')
            return pd.read_csv(filename)
        
        elif data_source == 'system_data':
            # Dados do sistema APRENDER (exemplo)
            return _load_system_data_sample()
        
        elif data_source.startswith('json_data:'):
            # Dados JSON diretos
            json_str = data_source.replace('json_data:', '')
            data = json.loads(json_str)
            return pd.json_normalize(data)
        
        else:
            # Tentar carregar como arquivo
            if Path(data_source).exists():
                if data_source.endswith('.json'):
                    with open(data_source, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return pd.json_normalize(data)
                elif data_source.endswith('.csv'):
                    return pd.read_csv(data_source)
            
        return None
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return None

def _load_system_data_sample() -> pd.DataFrame:
    """Carrega dados de exemplo do Sistema APRENDER"""
    # Dados de exemplo baseados no sistema real
    data = {
        'formador_id': [1, 2, 3, 4, 5],
        'nome': ['João Silva', 'Maria Santos', 'Pedro Costa', 'Ana Lima', 'Carlos Oliveira'],
        'status': ['ativo', 'ativo', 'bloqueado', 'ativo', 'ativo'],
        'projeto_id': [1, 2, 1, 3, 2],
        'solicitacoes_aprovadas': [15, 23, 8, 31, 19],
        'solicitacoes_pendentes': [2, 1, 0, 3, 1],
        'ultima_atividade': ['2025-09-20', '2025-09-19', '2025-09-15', '2025-09-20', '2025-09-18']
    }
    return pd.DataFrame(data)

def _apply_pandas_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Aplica filtros aos dados usando Pandas"""
    try:
        for column, condition in filters.items():
            if column in df.columns:
                if isinstance(condition, dict):
                    # Filtro complexo
                    if 'equals' in condition:
                        df = df[df[column] == condition['equals']]
                    elif 'contains' in condition:
                        df = df[df[column].str.contains(condition['contains'], na=False)]
                    elif 'greater_than' in condition:
                        df = df[df[column] > condition['greater_than']]
                    elif 'less_than' in condition:
                        df = df[df[column] < condition['less_than']]
                else:
                    # Filtro simples
                    df = df[df[column] == condition]
        return df
    except Exception as e:
        logger.error(f"Erro ao aplicar filtros: {e}")
        return df

def _perform_pandas_analysis(df: pd.DataFrame, analysis_type: str, group_by: str = "") -> str:
    """Executa análise específica usando Pandas"""
    try:
        result = f"📊 Análise Pandas - {analysis_type.upper()}\n"
        result += f"📈 Dados: {len(df)} registros, {len(df.columns)} colunas\n\n"
        
        if analysis_type == "statistics":
            result += _get_statistics_analysis(df)
        
        elif analysis_type == "grouping":
            if group_by and group_by in df.columns:
                result += _get_grouping_analysis(df, group_by)
            else:
                result += "⚠️ Coluna para agrupamento não especificada ou não encontrada\n"
                result += f"Colunas disponíveis: {', '.join(df.columns.tolist())}\n"
        
        elif analysis_type == "filtering":
            result += _get_filtering_analysis(df)
        
        elif analysis_type == "insights":
            result += _get_insights_analysis(df)
        
        elif analysis_type == "summary":
            result += _get_summary_analysis(df)
        
        elif analysis_type == "correlation":
            result += _get_correlation_analysis(df)
        
        else:
            result += f"❌ Tipo de análise '{analysis_type}' não suportado\n"
            result += "Tipos disponíveis: statistics, grouping, filtering, insights, summary, correlation\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Erro na análise: {e}")
        return f"❌ Erro na análise: {str(e)}"

def _get_statistics_analysis(df: pd.DataFrame) -> str:
    """Análise estatística dos dados"""
    result = "📊 ESTATÍSTICAS DESCRITIVAS:\n\n"
    
    # Estatísticas numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        result += "🔢 Colunas Numéricas:\n"
        stats = df[numeric_cols].describe()
        result += stats.to_string()
        result += "\n\n"
    
    # Estatísticas categóricas
    categorical_cols = df.select_dtypes(include=['object']).columns
    if len(categorical_cols) > 0:
        result += "📝 Colunas Categóricas:\n"
        for col in categorical_cols[:5]:  # Limitar a 5 colunas
            result += f"• {col}: {df[col].nunique()} valores únicos\n"
            top_values = df[col].value_counts().head(3)
            result += f"  Top 3: {dict(top_values)}\n"
        result += "\n"
    
    return result

def _get_grouping_analysis(df: pd.DataFrame, group_by: str) -> str:
    """Análise de agrupamento"""
    result = f"📊 ANÁLISE POR AGRUPAMENTO: {group_by}\n\n"
    
    # Contagem por grupo
    group_counts = df[group_by].value_counts()
    result += f"📈 Contagem por {group_by}:\n"
    result += group_counts.to_string()
    result += "\n\n"
    
    # Estatísticas numéricas por grupo
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        result += f"🔢 Estatísticas numéricas por {group_by}:\n"
        grouped_stats = df.groupby(group_by)[numeric_cols].agg(['mean', 'sum', 'count'])
        result += grouped_stats.to_string()
        result += "\n\n"
    
    return result

def _get_filtering_analysis(df: pd.DataFrame) -> str:
    """Análise de filtros possíveis"""
    result = "🔍 ANÁLISE DE FILTROS DISPONÍVEIS:\n\n"
    
    for col in df.columns:
        if df[col].dtype == 'object':
            unique_values = df[col].unique()[:10]  # Primeiros 10 valores
            result += f"• {col}: {len(df[col].unique())} valores únicos\n"
            result += f"  Exemplos: {', '.join(map(str, unique_values))}\n"
        elif pd.api.types.is_numeric_dtype(df[col]):
            result += f"• {col}: numérico (min: {df[col].min()}, max: {df[col].max()})\n"
        result += "\n"
    
    return result

def _get_insights_analysis(df: pd.DataFrame) -> str:
    """Análise de insights automáticos"""
    result = "💡 INSIGHTS AUTOMÁTICOS:\n\n"
    
    # Insights sobre dados faltantes
    missing_data = df.isnull().sum()
    if missing_data.sum() > 0:
        result += "⚠️ Dados Faltantes:\n"
        for col, missing in missing_data.items():
            if missing > 0:
                result += f"• {col}: {missing} valores faltantes ({missing/len(df)*100:.1f}%)\n"
        result += "\n"
    
    # Insights sobre distribuição
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        result += "📊 Distribuição Numérica:\n"
        for col in numeric_cols[:3]:  # Primeiras 3 colunas numéricas
            skewness = df[col].skew()
            result += f"• {col}: assimetria {skewness:.2f} "
            if abs(skewness) > 1:
                result += "(altamente assimétrico)\n"
            elif abs(skewness) > 0.5:
                result += "(moderadamente assimétrico)\n"
            else:
                result += "(aproximadamente simétrico)\n"
        result += "\n"
    
    # Insights sobre correlações
    if len(numeric_cols) > 1:
        result += "🔗 Correlações Fortes (>0.7):\n"
        corr_matrix = df[numeric_cols].corr()
        strong_corr = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    strong_corr.append(f"• {corr_matrix.columns[i]} ↔ {corr_matrix.columns[j]}: {corr_val:.2f}")
        
        if strong_corr:
            result += "\n".join(strong_corr[:5])  # Máximo 5 correlações
        else:
            result += "Nenhuma correlação forte encontrada\n"
        result += "\n"
    
    return result

def _get_summary_analysis(df: pd.DataFrame) -> str:
    """Resumo geral dos dados"""
    result = "📋 RESUMO GERAL DOS DADOS:\n\n"
    
    result += f"📊 Dimensões: {len(df)} linhas × {len(df.columns)} colunas\n"
    result += f"💾 Memória: {df.memory_usage(deep=True).sum() / 1024:.1f} KB\n\n"
    
    result += "📝 Tipos de Dados:\n"
    dtype_counts = df.dtypes.value_counts()
    for dtype, count in dtype_counts.items():
        result += f"• {dtype}: {count} colunas\n"
    result += "\n"
    
    result += "🔍 Primeiras 5 Linhas:\n"
    result += df.head().to_string()
    result += "\n\n"
    
    return result

def _get_correlation_analysis(df: pd.DataFrame) -> str:
    """Análise de correlações"""
    result = "🔗 ANÁLISE DE CORRELAÇÕES:\n\n"
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < 2:
        return result + "❌ Necessário pelo menos 2 colunas numéricas para análise de correlação\n"
    
    corr_matrix = df[numeric_cols].corr()
    result += "📊 Matriz de Correlação:\n"
    result += corr_matrix.to_string()
    result += "\n\n"
    
    # Correlações mais fortes
    result += "🔥 Correlações Mais Fortes:\n"
    corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            corr_pairs.append((abs(corr_val), corr_val, corr_matrix.columns[i], corr_matrix.columns[j]))
    
    corr_pairs.sort(reverse=True)
    for abs_corr, corr, col1, col2 in corr_pairs[:5]:
        result += f"• {col1} ↔ {col2}: {corr:.3f}\n"
    
    return result

if __name__ == "__main__":
    asyncio.run(main())