# 🔍 AUDITORIA COMPLETA - DUPLICATAS E REDUNDÂNCIAS
**Sistema Aprender - Análise Detalhada**
**Data**: 30/09/2025 19:45
**Status**: 🚨 CRÍTICO - Múltiplas duplicatas identificadas

---

## 📊 RESUMO EXECUTIVO

### 🎯 Objetivo
Identificar TODAS as duplicatas, redundâncias e problemas de centralização no sistema.

### ⚠️ Problemas Críticos Identificados

| Categoria | Qtd Duplicatas | Impacto | Tamanho Total |
|-----------|---------------|---------|---------------|
| **Arquivos de Configuração** | 9 | 🔴 Alto | ~50KB |
| **Docker Files** | 7 | 🔴 Alto | ~30KB |
| **Arquivos .env** | 9 | 🔴 Alto | ~20KB |
| **Dados JSON** | 200+ | 🔴 **CRÍTICO** | **~200MB** |
| **Backups** | 15+ | 🟡 Médio | **68MB** |
| **Ambientes Virtuais** | 3 | 🟡 Médio | ~500MB |
| **Arquivos de Log** | 10+ | 🟢 Baixo | ~500KB |

**Total Desperdício Estimado**: ~800MB+ de arquivos duplicados/desnecessários

---

## 🚨 CATEGORIA 1: ARQUIVOS DE CONFIGURAÇÃO DUPLICADOS

### ⚙️ Settings.py (5 VERSÕES!)

```
aprender_sistema/
├── settings.py                    ✅ ATIVO (simplificado, 2.9KB)
├── settings_backup.py             ❌ DUPLICATA (8.8KB)
├── settings_production.py         ❌ DUPLICATA (12KB)
├── settings_simple.py             ❌ DUPLICATA (2.9KB) - IDÊNTICO ao settings.py
└── settings_unificado.py          ❌ DUPLICATA (8.9KB)

backups/removed_files/old_configs/
├── settings_backup.py             ❌ DUPLICATA ANTIGA
└── settings_production.py         ❌ DUPLICATA ANTIGA
```

**Recomendação**:
- ✅ **MANTER**: `settings.py` (atual, funcional)
- ❌ **REMOVER**: Todos os outros (4 arquivos = ~32KB)

---

### 🐳 Docker Files (7 VERSÕES!)

```
RAIZ:
├── docker-compose.yml             ✅ PRINCIPAL (8.3KB) - Unificado
├── docker-compose.dev.yml         ❌ DUPLICATA (4.4KB)
├── docker-compose.prod.yml        ❌ DUPLICATA (6.1KB)
├── docker-compose.unificado.yml   ❌ DUPLICATA (4.2KB)
├── Dockerfile                     ✅ PRINCIPAL (5.0KB)
├── Dockerfile.mcp                 🟡 ESPECIALIZADO (1.5KB) - Avaliar
└── Dockerfile.streamlit           ❌ DUPLICATA (979B)

docker/
├── dev/Dockerfile                 ❌ DUPLICATA
└── prod/Dockerfile                ❌ DUPLICATA

backups/removed_files/
└── Dockerfile.backup              ❌ DUPLICATA ANTIGA
```

**Recomendação**:
- ✅ **MANTER**: `docker-compose.yml` + `Dockerfile` (principais)
- 🟡 **AVALIAR**: `Dockerfile.mcp` (se necessário para MCPs)
- ❌ **REMOVER**: Todos os outros (6 arquivos = ~21KB)

---

### 🔐 Arquivos .env (9 VERSÕES!)

```
RAIZ:
├── .env.develop               ❌ DUPLICATA
├── .env.develop.example       ✅ MANTER (template)
├── .env.docker                ❌ DUPLICATA
├── .env.figma.example         🟡 ESPECIALIZADO
├── .env.main                  ❌ DUPLICATA
└── .env.main.example          ✅ MANTER (template)

backups/removed_files/
├── .env                       ❌ DUPLICATA ANTIGA
├── .env.example               ❌ DUPLICATA ANTIGA
└── .env.local                 ❌ DUPLICATA ANTIGA
```

**Recomendação**:
- ✅ **MANTER**: `.env.develop.example`, `.env.main.example` (templates)
- 🟡 **AVALIAR**: `.env.figma.example` (se usar Figma MCP)
- ❌ **REMOVER**: Arquivos .env ativos (devem ser locais, não versionados)
- ❌ **REMOVER**: Backups antigos (3 arquivos)

---

### 📦 Requirements.txt (3 VERSÕES)

```
RAIZ:
├── requirements.txt           ✅ PRINCIPAL (Django 4.2 LTS)
├── requirements-dev.txt       🟡 DESENVOLVIMENTO (dependências extras)

neural_system/
└── requirements_mcp.txt       ❌ DUPLICATA ou 🟡 ESPECIALIZADO?
```

**Recomendação**:
- ✅ **MANTER**: `requirements.txt` (principal)
- 🟡 **AVALIAR**: `requirements-dev.txt` (se tiver deps exclusivas de dev)
- 🟡 **AVALIAR**: `requirements_mcp.txt` (se tiver deps exclusivas de MCP)
- **ALTERNATIVA**: Unificar tudo em `requirements.txt` com seções

---

## 🚨 CATEGORIA 2: DADOS DUPLICADOS (CRÍTICO!)

### 📁 Pastas de Dados (4 PASTAS!)

```
dados/                         32MB  (extraídos + relatorios + backups)
dados_planilhas_originais/     2.3MB (arquivos tratados JSON)
dados_unificados/              5.9MB (dados limpos 2025-09-19)
fonte_unica_dados/             15MB  (estrutura organizada)

TOTAL: 55.2MB de dados potencialmente duplicados
```

**Análise de Sobreposição**:
```
dados/extraidos/              → Dados brutos extraídos
dados_planilhas_originais/    → Dados tratados (pós-processamento)
dados_unificados/             → Dados limpos (setembro 2025)
fonte_unica_dados/            → "Fonte única" (???)
```

**🔴 PROBLEMA**: 4 pastas com nomenclaturas diferentes, sem clareza sobre qual é a fonte de verdade!

**Recomendação**:
1. **Definir UMA fonte única** (provavelmente `fonte_unica_dados/`)
2. **Mover backups** para `backups/dados/`
3. **Arquivar ou remover** pastas antigas (dados/, dados_unificados/)
4. **Renomear** `dados_planilhas_originais/` para algo mais claro

---

### 📄 Arquivos JSON na Raiz (30+ ARQUIVOS GIGANTES!)

**Arquivos de Planilhas**:
```
agenda_planilha_20250924_193210.json                    6.0MB  ❌
controle_planilha_20250924_193154.json                  27MB   ❌ ENORME!
disponibilidade_planilha_20250924_193216.json           839KB  ❌
eventos_completos_20250924_172144.json                  7.3MB  ❌
formacoes_completas_20250924_172144.json                26MB   ❌ ENORME!
usuarios_completos_20250924_172144.json                 (não listado)

mapeamento_completo_todas_planilhas_20250924_192753.json  60MB  ❌ GIGANTE!!!
```

**Dados Processados**:
```
dados_frescos_completos_20250919_223942.json            4.2MB  ❌
dados_organizados_por_categoria_20250919_225631.json    47MB   ❌ GIGANTE!!!
dados_planilhas_faltantes_20250919_225022.json          34MB   ❌ GIGANTE!!!
dados_todas_planilhas_completas_20250919_224823.json    8.2MB  ❌
dados_tratados_organizados_20250919_225631.json         43MB   ❌ GIGANTE!!!
```

**Mapeamentos**:
```
mapeamento_completo_google_sheets_20250923_205009.json  113KB  ❌ DUPLICATA
mapeamento_completo_google_sheets_20250923_220315.json  113KB  ❌ DUPLICATA
mapeamento_coordenadores_20250919_170243.json           16KB   ❌
```

**Neural/Lighthouse**:
```
conversa glm4.5.json                                    2.1MB  ❌
lighthouse-home.json                                    468KB  ❌
lighthouse-login.json                                   464KB  ❌
lighthouse-mapa.json                                    469KB  ❌
lighthouse-solicitar.json                               469KB  ❌
neural_extraction_20250924_010124.json                  230B   ❌
neural_processed_data_20250924_010526.json              789B   ❌
neural_robust_processed_20250924_012620.json            4.7KB  ❌
neural_simple_processed_20250924_010631.json            451B   ❌
```

**TOTAL**: ~200MB de JSONs na raiz do projeto! 🔴

**Recomendação**:
1. **Mover TODOS os JSONs** para pastas apropriadas:
   - Planilhas → `dados_planilhas_originais/raw/`
   - Processados → `dados_unificados/processed/`
   - Mapeamentos → `dados/mapeamentos/`
   - Lighthouse → `reports/lighthouse/`
   - Neural → `neural_system/data/`
2. **Comprimir** arquivos grandes (>5MB) em .json.gz
3. **Adicionar ao .gitignore** arquivos temporários

---

## 🗃️ CATEGORIA 3: BACKUPS

### 📦 Pasta backups/ (68MB!)

```
backups/
├── removed_files/              (múltiplos arquivos removidos)
│   ├── backups/                ❌ BACKUP DE BACKUP!
│   ├── old_configs/            ❌ Configs antigas
│   ├── logs/                   ❌ Logs antigos
│   ├── .env, .env.local, etc   ❌ Envs antigas
│   └── *.sql (3 arquivos)      ❌ Dumps SQL antigos
├── removed_directories/
│   ├── .venv/                  ❌ VENV ANTIGO (~400MB?)
│   └── venv/                   ❌ VENV ANTIGO
└── backup_extensoes_cursor_*.txt  ❌ Duplicatas

RAIZ:
├── backup_extensoes_cursor_20250920_001500.txt  ❌ DUPLICATA
├── backup_extensoes_cursor_20250920_124041.txt  ❌ DUPLICATA
└── backup_pre_unificacao_20250919_180910.sql    ❌ Dump SQL antigo
```

**Recomendação**:
- ❌ **REMOVER COMPLETAMENTE**: `backups/removed_directories/.venv` e `venv/`
- ❌ **REMOVER**: Arquivos .sql antigos (já temos git history)
- ❌ **REMOVER**: Configs antigas (old_configs/)
- 🟡 **AVALIAR**: Se há algo crítico antes de deletar
- ✅ **COMPRIMIR**: Backups importantes em .tar.gz

---

## 🐍 CATEGORIA 4: AMBIENTES VIRTUAIS

### Ambientes Encontrados:

```
./.venv/                       ✅ ATIVO (Python 3.13.7)
./backups/removed_directories/.venv/  ❌ BACKUP (~400MB?)
./backups/removed_directories/venv/   ❌ BACKUP (~100MB?)
```

**Recomendação**:
- ✅ **MANTER**: `.venv/` (ambiente ativo)
- ❌ **REMOVER IMEDIATAMENTE**: Backups de venv (desperdício ~500MB!)

---

## 🐳 CATEGORIA 5: DOCKER - CENTRALIZAÇÃO

### Status Atual:

```bash
docker ps -a
# OUTPUT: Nenhum container rodando!

docker images
# OUTPUT: Nenhuma imagem construída!
```

**🔴 PROBLEMA CRÍTICO**: Sistema NÃO está usando Docker!

### Análise de Centralização:

**Ambiente Atual**:
- ✅ Python local: 3.13.7
- ✅ Django local: 4.2.24
- ✅ SQLite local: db.sqlite3 (128KB)
- ❌ **NÃO há containers Docker ativos**
- ❌ **NÃO há PostgreSQL em Docker**

**Configuração docker-compose.yml**:
- Define PostgreSQL na porta 5432/5433
- Define Django web app
- **MAS não está em execução!**

**Recomendação**:
1. **DECIDIR**: Docker OU Local? (não ambos!)
2. **Se Docker**:
   - Construir imagens: `docker-compose build`
   - Subir containers: `docker-compose up -d`
   - Migrar db.sqlite3 → PostgreSQL
3. **Se Local**:
   - Manter configuração atual
   - Remover arquivos Docker desnecessários
   - Focar em PostgreSQL local (se necessário)

---

## 📁 CATEGORIA 6: PASTAS DUPLICADAS/REDUNDANTES

### Pastas na Raiz (25 pastas!)

```
PRODUÇÃO:
✅ aprender_sistema/     (Django project)
✅ core/                 (Django app principal)
✅ api/                  (Django API)
✅ manage.py             (Django CLI)

DADOS (4 PASTAS DUPLICADAS!):
❌ dados/
❌ dados_planilhas_originais/
❌ dados_unificados/
🟡 fonte_unica_dados/     (qual a diferença?)
🟡 data/                  (outra pasta de dados?)

DESENVOLVIMENTO:
✅ .venv/                 (ambiente virtual)
✅ docs/                  (204 arquivos .md!)
✅ tests/                 (testes)
🟡 scripts/               (scripts auxiliares)
🟡 neural_system/         (sistema neural - necessário?)

RELATÓRIOS/LOGS:
🟡 reports/
🟡 relatorios/            (duplicata de reports?)
🟡 logs/
🟡 out/                   (output de quê?)
🟡 out_apps_script/       (output de Apps Script?)

ARQUIVOS ESTÁTICOS:
✅ static/
✅ staticfiles/
🟡 media/

BACKUP/ARQUIVO:
❌ backups/               (68MB - revisar)
❌ archive/               (arquivos arquivados)
🟡 ai_export/             (export para IA?)

TESTES/DEV:
🟡 teste-detectar-contexto/
🟡 .cursor/
🟡 .vscode/
```

**Recomendação**:
1. **Consolidar pastas de dados** em UMA única
2. **Mesclar** `reports/` e `relatorios/`
3. **Esclarecer** propósito de `out/`, `out_apps_script/`, `ai_export/`
4. **Limpar** `backups/` e `archive/`

---

## 📊 CATEGORIA 7: ARQUIVOS .md (204 ARQUIVOS!)

```
find . -name "*.md" -type f | wc -l
# OUTPUT: 204 arquivos Markdown!
```

**Principais concentrações**:
- `docs/`: ~70 arquivos
- Raiz: ~15 arquivos (CLAUDE.md, README.md, etc.)
- Subdiretorios: ~119 arquivos

**Recomendação**:
- 🟡 **Revisar**: Se há duplicatas de conteúdo
- 🟡 **Consolidar**: Documentação fragmentada
- ✅ **Organizar**: Índice principal em `docs/README.md`

---

## 🎯 PLANO DE AÇÃO PRIORITÁRIO

### 🔴 URGENTE (Fazer AGORA):

1. **Remover venvs de backup** (~500MB):
   ```bash
   rm -rf backups/removed_directories/.venv
   rm -rf backups/removed_directories/venv
   ```

2. **Mover JSONs gigantes da raiz** (~200MB):
   ```bash
   mkdir -p dados_planilhas_originais/raw
   mv *.json dados_planilhas_originais/raw/
   ```

3. **Remover settings duplicados**:
   ```bash
   rm aprender_sistema/settings_backup.py
   rm aprender_sistema/settings_production.py
   rm aprender_sistema/settings_simple.py
   rm aprender_sistema/settings_unificado.py
   ```

4. **Remover docker-compose duplicados**:
   ```bash
   rm docker-compose.dev.yml
   rm docker-compose.prod.yml
   rm docker-compose.unificado.yml
   rm Dockerfile.streamlit
   ```

**Economia Estimada**: ~700MB+

---

### 🟡 MÉDIO PRAZO (Esta semana):

5. **Consolidar pastas de dados**:
   - Escolher UMA como fonte de verdade
   - Mover backups para `backups/dados/`
   - Arquivar pastas antigas

6. **Limpar pasta backups/**:
   - Remover configs antigas
   - Remover .sql antigos
   - Comprimir o que for necessário manter

7. **Revisar .env files**:
   - Remover .env ativos do git
   - Manter apenas .example como template

8. **Decisão Docker**:
   - Definir se vai usar Docker ou não
   - Se sim: subir containers e migrar DB
   - Se não: limpar arquivos Docker desnecessários

---

### 🟢 LONGO PRAZO (Manutenção):

9. **Organizar documentação** (204 .md)
10. **Consolidar pastas** (reports/ vs relatorios/)
11. **Limpar logs antigos**
12. **Atualizar .gitignore** para evitar futuras duplicatas

---

## 📈 BENEFÍCIOS ESPERADOS

| Ação | Economia | Benefício |
|------|----------|-----------|
| Remover venvs backup | ~500MB | Espaço em disco |
| Mover JSONs da raiz | ~200MB | Organização |
| Remover configs duplicados | ~50KB | Clareza |
| Limpar backups/ | ~68MB | Limpeza |
| Consolidar dados/ | ~0MB | Lógica única |
| **TOTAL** | **~770MB** | **Sistema limpo e centralizado** |

---

## ✅ CHECKLIST DE VALIDAÇÃO

Após executar as ações:

- [ ] Apenas 1 settings.py existe
- [ ] Apenas 1 docker-compose.yml existe
- [ ] Apenas 1 Dockerfile principal existe
- [ ] JSONs organizados em pastas apropriadas
- [ ] backups/ contém apenas backups essenciais comprimidos
- [ ] Apenas 1 venv ativo (.venv/)
- [ ] Pasta de dados única e clara
- [ ] .gitignore atualizado
- [ ] Docker ativado OU desativado (decisão clara)
- [ ] Sistema funcional após limpeza

---

## 🚨 AVISOS IMPORTANTES

**ANTES DE DELETAR QUALQUER COISA**:
1. ✅ Criar backup completo: `git tag backup-pre-limpeza-$(date +%Y%m%d)`
2. ✅ Verificar que não há código ativo dependendo dos arquivos
3. ✅ Commitar mudanças atuais
4. ✅ Revisar cada arquivo antes de remover

**NÃO DELETAR SEM REVISAR**:
- Arquivos em `fonte_unica_dados/` (pode ter dados importantes)
- Arquivos em `neural_system/` (se estiver em uso)
- Configs específicas de MCPs (se estiverem ativos)

---

**Auditoria realizada por**: Claude Code
**Próximo passo**: Executar Plano de Ação Prioritário (URGENTE)
