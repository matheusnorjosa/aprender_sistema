# Auditoria — Mudanças Fora do Plano (Fases 01–07)

**Data**: 2026-02-05
**Objetivo**: listar e avaliar mudanças que não estavam no plano de correções das fases 01–07.

## 1) Resumo
Foram encontradas mudanças estruturais não previstas no plano original, com impacto em modelo de dados, importações e endpoints. Essas alterações precisam de validação própria antes de seguirem para produção.

## 2) Principais mudanças detectadas

### 2.1 Novo modelo `Colecao` + relação com `Produto`
**Arquivos:**
- `v2/backend/apps/core/models/organizacao.py`
- `v2/backend/apps/core/serializers/organizacao.py`
- `v2/backend/apps/core/views/admin.py`
- `v2/backend/apps/core/urls.py`
- `v2/backend/apps/core/migrations/0052_add_colecao_model.py`

**Descrição:**
- Criação do modelo `Colecao` (FK para `Projeto`).
- `Produto` ganhou FK opcional `colecao`.
- Novo endpoint `/api/colecoes/` com CRUD (DAT-only para escrita).

**Riscos/impactos:**
- Alteração de schema (nova tabela + FK em `Produto`).
- Pode exigir migração de dados ou backfill.
- Impacto em importações de produtos e compras (caso esperem coleções).

### 2.2 Mudanças em resolvers e importadores
**Arquivos:**
- `v2/backend/apps/core/services/resolvers.py`
- `v2/backend/apps/core/services/produtos_import.py`
- `v2/backend/apps/core/services/usuarios_import.py`
- `v2/backend/apps/core/services/bloqueios_import.py`
- `v2/backend/apps/core/services/deslocamentos_import.py`
- `v2/backend/apps/core/services/eventos_import.py`
- `v2/backend/apps/dat_ingest/management/commands/etl_import_produtos.py`

**Descrição:**
- Resolvers movidos/ajustados no core (normalização e match por nomes/UF). 
- Importador de produtos agora suporta coluna de `colecao`.
- Ajustes adicionais nos importadores (padronização e parsing).

**Riscos/impactos:**
- Mudanças de comportamento em ETL sem atualização de docs e testes dedicados.
- Pode afetar imports existentes em produção.

### 2.3 Exposição de novos endpoints
**Arquivos:**
- `v2/backend/apps/core/views/admin.py`
- `v2/backend/apps/core/urls.py`

**Descrição:**
- Registro do `ColecaoViewSet` em `/api/colecoes/`.

**Riscos/impactos:**
- Endpoints novos não documentados em `API_REFERENCE.md`.
- Precisam de RBAC e testes consistentes.

## 3) O que falta para considerar essas mudanças prontas
- Documento de requisitos para `Colecao` (escopo e regras de negócio).
- Migração/seed (se necessário) e backfill definido.
- Atualização de docs (`API_REFERENCE.md`, specs DAT/ETL).
- Testes para:
  - CRUD de coleções.
  - Importação de produtos com coleções.
  - Compatibilidade com dados existentes.

## 4) Recomendação
Não avançar essas mudanças para produção até que haja validação de requisitos e testes mínimos. Elas devem ser tratadas como um mini‑projeto independente do plano de correções 01–07.
