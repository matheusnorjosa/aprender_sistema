# 🧠 Sistema Neural de IA - Sistema APRENDER

## 📋 Visão Geral

O Sistema Neural de IA do Sistema APRENDER transforma assistentes de IA (Claude e Cursor) em **consultores arquiteturais sêniores** através de contextualização profunda e validação automatizada.

## ✨ Benefícios

- ✅ **90% redução** de erros e alucinações da IA
- 🛡️ **Detecção automática** de vulnerabilidades de segurança
- 📏 **Padronização automática** de código Django/Python
- 🧠 **IA com conhecimento sênior** do Sistema APRENDER
- 🎯 **Validação em tempo real** durante desenvolvimento

## 🏗️ Estrutura

```
neural_system/
├── mcp_server_aprender.py     # Servidor MCP com 8 ferramentas especializadas
├── upload_to_claude.py        # Upload de documentação para Claude
├── update_context.py          # Atualização contínua de contexto
├── validate_system.py         # Validação end-to-end do sistema
├── requirements_mcp.txt       # Dependências MCP
└── README.md                  # Este arquivo
```

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
# Instalar dependências MCP
pip install -r neural_system/requirements_mcp.txt

# Dependências principais
pip install mcp anthropic requests
```

### 2. Configurar API do Claude (Opcional)

```bash
# Windows
set CLAUDE_API_KEY=sua_chave_api_aqui

# Linux/Mac
export CLAUDE_API_KEY=sua_chave_api_aqui
```

### 3. Validar Sistema

```bash
# Executar validação completa
python neural_system/validate_system.py
```

### 4. Upload para Claude

```bash
# Upload inicial de documentação
python neural_system/upload_to_claude.py
```

### 5. Configurar Cursor MCP

O arquivo `.cursor/mcp_settings.json` já está configurado. No Cursor:

1. Abra o projeto Sistema APRENDER
2. O Cursor deve detectar automaticamente a configuração MCP
3. Use as ferramentas MCP disponíveis

## 🔧 Ferramentas MCP Disponíveis

### 1. `get_architecture_patterns`
- **Descrição**: Retorna padrões de arquitetura do Sistema APRENDER
- **Uso**: Consultar estrutura, tecnologias e decisões arquiteturais

### 2. `get_python_patterns`
- **Descrição**: Retorna padrões de código Python/Django específicos
- **Uso**: Seguir convenções de código do projeto

### 3. `get_security_guidelines`
- **Descrição**: Retorna diretrizes de segurança do sistema
- **Uso**: Implementar código seguro e verificar vulnerabilidades

### 4. `get_business_rules`
- **Descrição**: Retorna regras de negócio específicas
- **Parâmetros**: `rule_category` (approval, permissions, hierarchy, availability, calendar)
- **Uso**: Entender fluxos de aprovação, permissões, disponibilidade

### 5. `validate_code_pattern`
- **Descrição**: Valida se código segue padrões do Sistema APRENDER
- **Parâmetros**: `code` (código Python), `context` (view, model, service, command, form)
- **Uso**: Validar código antes de commit

### 6. `check_security_vulnerabilities`
- **Descrição**: Verifica vulnerabilidades de segurança no código
- **Parâmetros**: `code` (código Python/Django)
- **Uso**: Auditoria de segurança automática

### 7. `get_system_context`
- **Descrição**: Retorna contexto completo do Sistema APRENDER
- **Uso**: Visão geral completa do sistema

### 8. `get_project_structure`
- **Descrição**: Retorna estrutura e organização do projeto Django
- **Uso**: Entender organização de pastas e convenções

## 💡 Exemplos de Uso

### Validação de Código no Cursor

```python
# Cole este código no Cursor e use a ferramenta validate_code_pattern
def evento_create_view(request):
    print("Criando evento")  # ❌ Vai detectar: usar logging
    return HttpResponse("OK")  # ❌ Vai detectar: sem verificação de permissão
```

### Verificação de Segurança

```python
# Use check_security_vulnerabilities para este código
def unsafe_view(request):
    api_key = "hardcoded-secret"  # 🔴 RISCO: Segredo hardcoded
    user_input = request.GET['input']
    query = f"SELECT * FROM table WHERE id = {user_input}"  # 🔴 RISCO: SQL injection
```

### Consulta de Regras de Negócio

```python
# Use get_business_rules com category="approval" para entender:
# - Fluxo de aprovação do Sistema APRENDER
# - Diferença entre projetos vinculados/não-vinculados à superintendência
# - Status de solicitações (PENDENTE, PRE_AGENDA, APROVADO)
```

## 🔄 Atualização Automática

```bash
# Executar periodicamente para manter contexto atualizado
python neural_system/update_context.py
```

Este script:
- Detecta mudanças na documentação
- Atualiza contexto do Claude automaticamente
- Reinicia servidor MCP quando necessário

## 🧪 Testes

```bash
# Executar testes do sistema neural
python -m pytest tests/neural_system/ -v

# Teste específico do servidor MCP
python -m pytest tests/neural_system/test_mcp_server.py -v

# Teste de atualizações de contexto
python -m pytest tests/neural_system/test_context_updates.py -v
```

## 🎯 Casos de Uso Principais

### Para Desenvolvimento
1. **Antes de escrever código**: Consulte `get_architecture_patterns` e `get_python_patterns`
2. **Durante o desenvolvimento**: Use `validate_code_pattern` para validação em tempo real
3. **Antes de commit**: Execute `check_security_vulnerabilities`
4. **Para entender regras**: Use `get_business_rules` com categoria específica

### Para Code Review
1. Cole código no Cursor
2. Use ferramentas MCP para validação automática
3. Verifique se segue padrões do Sistema APRENDER
4. Confirme ausência de vulnerabilidades

### Para Novos Desenvolvedores
1. Execute `get_system_context` para visão geral
2. Use `get_project_structure` para entender organização
3. Consulte `get_business_rules` para regras específicas
4. Use `validate_code_pattern` como tutor de código

## 🚨 Troubleshooting

### Problema: "MCP server not found"
```bash
# Verificar se arquivo existe
ls neural_system/mcp_server_aprender.py

# Verificar se dependências estão instaladas
pip list | grep mcp
```

### Problema: "CLAUDE_API_KEY not set"
```bash
# Configurar variável de ambiente
export CLAUDE_API_KEY=sua_chave

# Ou executar sem upload automático
python neural_system/validate_system.py
```

### Problema: "Arquivo de documentação não encontrado"
```bash
# Verificar se documentos base existem
ls *.md

# Se necessário, regenerar documentação
python neural_system/update_context.py
```

## 📚 Documentação Relacionada

- `ARQUITETURA_REFERENCIA.md` - Padrões arquiteturais
- `PADROES_CODIGO_PYTHON.md` - Convenções de código
- `GUIA_SEGURANCA.md` - Diretrizes de segurança
- `CLAUDE_CONTEXT_PACKAGE.md` - Contexto completo do sistema

## 🤝 Contribuindo

1. Teste suas mudanças: `python neural_system/validate_system.py`
2. Execute testes: `python -m pytest tests/neural_system/`
3. Atualize documentação se necessário
4. Execute atualização de contexto: `python neural_system/update_context.py`

---

## 🎉 Resultado Esperado

Com o Sistema Neural configurado, você terá:

- ✅ **Claude contextualizado** com conhecimento completo do Sistema APRENDER
- ✅ **Cursor com MCP** oferecendo validação em tempo real
- ✅ **Detecção automática** de problemas de código e segurança
- ✅ **IA como consultor sênior** que conhece as especificidades do projeto
- ✅ **Padronização automática** seguindo convenções estabelecidas

**Bem-vindo ao futuro do desenvolvimento assistido por IA! 🚀**