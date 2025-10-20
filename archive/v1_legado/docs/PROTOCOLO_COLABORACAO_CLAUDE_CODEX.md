# 🤝 PROTOCOLO DE COLABORAÇÃO: Claude Code + Codex CLI

## 🎯 OBJETIVO

Estabelecer workflow colaborativo entre Claude Code e Codex CLI no projeto Aprender Sistema, garantindo conhecimento equivalente e complementaridade de habilidades.

## 📋 STATUS DO ONBOARDING

### ✅ Concluído:
- **WSL2 + Ubuntu**: Configurado e funcional
- **Codex CLI**: Instalado via NVM (v0.36.0)
- **Login OpenAI**: Autenticado com sucesso
- **Contexto Documentado**:
  - `CODEX_CONTEXT_PACKAGE.md` criado
  - `CODEX_QUICK_START.md` criado
  - `codex-wsl.sh` configurado

### ⚠️ Pendente:
- **Teste de Execução**: Codex CLI ainda com problemas de execução
- **Comunicação Direta**: Testar chat Claude ↔ Codex
- **Workflow Definido**: Protocolos de trabalho em equipe

## 🔧 COMO INICIAR CODEX MANUALMENTE

### Comando para WSL:
```bash
# Abrir WSL
wsl

# Navegar para o projeto
cd "/mnt/c/Users/datsu/OneDrive/Documentos/Aprender Sistema"

# Configurar Node.js
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
export BROWSER=wslview

# Verificar status
echo "📁 Diretório: $(pwd)"
ls -la CODEX_*.md

# Iniciar Codex
codex
```

### Primeira Sessão Recomendada:
```bash
# No Codex CLI, executar:
cat CODEX_CONTEXT_PACKAGE.md
cat CODEX_QUICK_START.md
cat CLAUDE.md | head -50
docker-compose ps
```

## 📞 PROTOCOLO DE COMUNICAÇÃO

### Formato de Mensagens:

**Claude Code:**
```
🧠 Claude: [mensagem]
📊 Contexto: [informação relevante]
🎯 Sugestão: [próxima ação]
```

**Codex CLI:**
```
🤖 Codex: [mensagem]
⚡ Execução: [comando executado]
📈 Resultado: [output obtido]
```

### Coordenação de Tarefas:

1. **Claude** analisa o contexto e histórico
2. **Codex** executa comandos e implementações
3. **Ambos** validam resultados cruzadamente
4. **Claude** documenta descobertas para futuras sessões

## 🔄 WORKFLOW COLABORATIVO

### Cenário 1: Nova Funcionalidade
```
Claude: Analisa requisitos + contexto histórico
  ↓
Codex: Implementa código + testes
  ↓
Claude: Revisa implementação + documenta
  ↓
Codex: Aplica correções + deploy
```

### Cenário 2: Debug de Problema
```
Claude: Identifica contexto do problema
  ↓
Codex: Executa diagnósticos + logs
  ↓
Claude: Analisa padrões + causa raiz
  ↓
Codex: Implementa fix + verifica
```

### Cenário 3: Análise de Dados
```
Codex: Executa queries + extrações
  ↓
Claude: Interpreta resultados + insights
  ↓
Codex: Gera relatórios + visualizações
  ↓
Claude: Documenta achados + recomendações
```

## 📚 CONHECIMENTO COMPARTILHADO

### Arquivos que AMBOS devem conhecer:
- `CODEX_CONTEXT_PACKAGE.md` - Contexto geral ⭐
- `CLAUDE.md` - Histórico completo ⭐
- `.claude/CLAUDE.md` - Diretrizes técnicas ⭐
- `core/models.py` - Estrutura de dados ⭐
- `docker-compose.yml` - Ambiente atual ⭐

### Especialização por Assistente:

**Claude Code (Especialista em):**
- Contexto histórico das sessões
- Regras de negócio complexas
- Análise de padrões e arquitetura
- Documentação e planejamento

**Codex CLI (Especialista em):**
- Execução de comandos
- Implementação de código
- Testes e debugging
- Deploy e automação

## 🚀 PRÓXIMOS PASSOS

### Imediato:
1. **Usuário** abre WSL manualmente
2. **Usuário** executa comandos de configuração
3. **Codex** lê arquivos de contexto
4. **Claude + Codex** iniciam primeira colaboração

### Médio Prazo:
1. Resolver problemas de execução Codex CLI
2. Automatizar workflow colaborativo
3. Criar templates de comunicação
4. Documentar casos de sucesso

### Longo Prazo:
1. Integração automatizada Claude ↔ Codex
2. Dashboard de colaboração
3. Métricas de produtividade conjunta
4. Evolução contínua do protocolo

## 💡 BENEFÍCIOS ESPERADOS

### Para o Projeto:
- **Redundância**: Dois assistentes com conhecimento completo
- **Especialização**: Cada um focado em suas forças
- **Velocidade**: Paralelização de tarefas
- **Qualidade**: Validação cruzada constante

### Para o Usuário:
- **Produtividade**: Dois assistentes trabalhando juntos
- **Confiabilidade**: Backup automático de conhecimento
- **Flexibilidade**: Escolher assistente por tarefa
- **Aprendizado**: Observar colaboração AI-AI

---

**🎯 Objetivo Final**: Criar o primeiro exemplo de colaboração produtiva Claude ↔ Codex em um projeto real de produção.