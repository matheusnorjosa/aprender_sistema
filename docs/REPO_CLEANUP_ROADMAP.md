# 🧹 Roadmap de Higienização - Sistema Aprender

## 📋 Status Geral

**Status**: 🟡 **EM PROGRESSO** (Fase 1/4 concluída)  
**Última atualização**: 2025-09-11  
**Responsável**: Claude Code Assistant  

---

## ✅ **FASE 1 - SEGURANÇA & ESTRUTURA BASE** *(CONCLUÍDA)*

### Segurança (100%)
- [x] Varredura de segredos executada
- [x] Relatório de segurança criado (`docs/security/secret_scan.md`)
- [x] `.gitignore` otimizado com proteções

### Documentação Base (100%)  
- [x] README.md profissional criado
- [x] Estrutura de diretórios `docs/` iniciada

---

## 🚧 **FASE 2 - ARQUIVOS PADRÃO & CI/CD** *(PRÓXIMA)*

### A) Arquivos de Projeto Padrão
- [ ] `CONTRIBUTING.md` - Guidelines de contribuição
- [ ] `SECURITY.md` - Política de segurança
- [ ] `CHANGELOG.md` - Histórico de versões (formato Keep a Changelog)
- [ ] `CODEOWNERS` - Revisores por diretório
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` - Template de PR

### B) Issue Templates
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md` (atualizar existente)
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md` (atualizar existente)  
- [ ] `.github/ISSUE_TEMPLATE/chore.md` - Tarefas técnicas

### C) CI/CD Pipeline
- [ ] `.github/workflows/ci_dev.yml` - Pipeline para dev
- [ ] `.github/workflows/ci_homolog.yml` - Pipeline para staging
- [ ] `.github/workflows/ci_main.yml` - Pipeline para produção
- [ ] `dependabot.yml` - Atualizações automáticas

**Estimativa**: 4-6 horas

---

## 🚧 **FASE 3 - DOCKER & AUTOMAÇÃO** 

### A) Docker Otimizado
- [ ] `docker/dev/Dockerfile` - Imagem de desenvolvimento
- [ ] `docker/prod/Dockerfile` - Imagem de produção (multi-stage)
- [ ] `docker-compose.dev.yml` - Ambiente de desenvolvimento
- [ ] `docker-compose.prod.yml` - Ambiente de produção
- [ ] Health checks implementados

### B) Automação Make/Scripts
- [ ] `Makefile` - Comandos padronizados
- [ ] `scripts/setup.sh` - Setup automático
- [ ] `scripts/test.sh` - Execução de testes
- [ ] `scripts/lint.sh` - Lint e formatação
- [ ] `scripts/deploy.sh` - Deploy automático

### C) Pre-commit Hooks
- [ ] Atualizar `.pre-commit-config.yaml` existente
- [ ] Adicionar `detect-private-key` hook
- [ ] Configurar `pyproject.toml` para lint configs

**Estimativa**: 3-4 horas

---

## 🚧 **FASE 4 - LIMPEZA & DOCUMENTAÇÃO AVANÇADA**

### A) Limpeza de Arquivos
- [ ] Remover arquivos `.xlsx` desnecessários
- [ ] Limpar arquivos `extracted_*.json` grandes
- [ ] Organizar scripts soltos na raiz
- [ ] Mover arquivos de teste para `tests/`

### B) Documentação Operacional  
- [ ] `docs/ops/deploy.md` - Guia de deploy detalhado
- [ ] `docs/ops/releases.md` - Processo de releases
- [ ] `docs/ops/troubleshooting.md` - Resolução de problemas
- [ ] `docs/dev/setup.md` - Setup de desenvolvimento

### C) Documentação de Segurança
- [ ] `docs/security/secrets_management.md` - Gestão de segredos
- [ ] `docs/security/google_integrations.md` - Setup Google APIs
- [ ] `docs/security/deployment_security.md` - Segurança em produção

**Estimativa**: 2-3 horas

---

## 🎯 **ENTREGÁVEIS POR FASE**

### Fase 2 - Entregáveis
```
PR-002-ci-cd-setup/
├── .github/workflows/
│   ├── ci_dev.yml
│   ├── ci_homolog.yml  
│   └── ci_main.yml
├── .github/ISSUE_TEMPLATE/
│   └── chore.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md  
└── CODEOWNERS
```

### Fase 3 - Entregáveis
```
PR-003-docker-automation/
├── docker/
│   ├── dev/Dockerfile
│   └── prod/Dockerfile
├── scripts/
│   ├── setup.sh
│   ├── test.sh
│   └── deploy.sh
├── Makefile
├── docker-compose.dev.yml
└── docker-compose.prod.yml
```

### Fase 4 - Entregáveis
```
PR-004-docs-cleanup/
├── docs/
│   ├── ops/
│   │   ├── deploy.md
│   │   └── releases.md
│   ├── dev/setup.md
│   └── security/
│       ├── secrets_management.md
│       └── google_integrations.md
└── cleanup: arquivos desnecessários removidos
```

---

## 🔄 **PROCESSO DE EXECUÇÃO**

### Como Executar Cada Fase

1. **Solicitar fase específica**:
   ```
   "Claude, execute a Fase 2 do roadmap de higienização"
   ```

2. **Acompanhar progresso**:
   - Cada fase gerará 1 PR temático
   - Documentação será atualizada em tempo real
   - Relatório de progresso ao final de cada fase

3. **Validação**:
   - CI verde em todas as branches
   - README funcionando (setup from scratch)
   - Deploy de staging funcionando

---

## 📊 **MÉTRICAS DE SUCESSO**

### Critérios de Aceite Global
- [ ] ✅ Zero segredos no repositório e histórico
- [ ] ✅ CI/CD verde em dev/homolog/main  
- [ ] ✅ Deploy automático configurado
- [ ] ✅ README permite setup do zero
- [ ] ✅ Estrutura navegável e maintível
- [ ] ✅ Pre-commit hooks funcionando
- [ ] ✅ Docker multi-stage otimizado
- [ ] ✅ Documentação completa para novos devs

### Métricas Técnicas
- **Tempo de setup**: < 10 minutos (com Docker)
- **Tempo de CI**: < 5 minutos por pipeline
- **Cobertura de testes**: > 80%
- **Linting**: 100% aprovação
- **Segurança**: Zero vulnerabilidades conhecidas

---

## 📞 **COMO CONTINUAR**

Para continuar a higienização, solicite:

```bash
# Opção 1: Próxima fase completa
"Claude, execute a Fase 2 completa do roadmap"

# Opção 2: Tarefa específica
"Claude, crie os workflows de CI/CD para dev/homolog/main"

# Opção 3: Urgente
"Claude, preciso fazer deploy em produção hoje, o que é crítico?"
```

---

**🎯 LEMBRETE**: Esta higienização segue as melhores práticas de DevOps e garante que o projeto esteja pronto para colaboração profissional e deploy seguro em produção.