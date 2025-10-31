# Testes E2E (Playwright) - Aprender Sistema v2

## Fase 2 - Plano DAT/GCal 2025-10-29

Testes end-to-end do fluxo **Solicitação → Google Calendar** usando Playwright.

---

## 📋 Pré-requisitos

- **Node.js 18+** (para Playwright)
- **Docker + Docker Compose** (backend + banco)
- **Chromium** instalado via Playwright

---

## 🚀 Setup Inicial

### 1. Instalar Dependências

```bash
cd v2/tests/playwright
npm install
```

### 2. Instalar Browsers

```bash
npx playwright install --with-deps chromium
```

### 3. Criar Seeds E2E

```bash
cd ../../infra
make seed-e2e
```

**Ou manualmente**:
```bash
cd ../../infra
docker compose exec -T web python manage.py seed_e2e_users
```

---

## ⚙️ Variáveis de Ambiente

Criar `.env` em `v2/tests/playwright/` (opcional):

```bash
BASE_URL=http://localhost:5173
GCAL_CLIENT=fake
```

**Nota**: `GCAL_CLIENT=fake` é obrigatório para testes (evita dependência de credenciais reais).

---

## 🧪 Executar Testes

### Via NPM (no diretório playwright/)

```bash
# Headless (CI-friendly)
npm run test

# Com UI interativa
npm run test:ui

# Headed mode (ver browser)
npm run test:headed

# Debug mode (passo-a-passo)
npm run test:debug

# Ver relatório HTML
npm run test:report
```

### Via Makefile (no diretório infra/)

```bash
cd v2/infra

# Criar seeds E2E
make seed-e2e

# Rodar testes headless
make test-e2e

# Rodar com UI interativa
make test-e2e-ui

# Rodar headed mode
make test-e2e-headed
```

---

## 📁 Estrutura de Arquivos

```
v2/tests/playwright/
├── e2e/
│   └── solicitacao-calendar.spec.ts    # Teste principal (4 test cases)
├── fixtures/
│   ├── auth-helpers.ts                 # Login/logout helpers
│   └── selectors.ts                    # Selectors centralizados
├── types.d.ts                          # Tipos TypeScript
├── playwright.config.js                # Configuração Playwright
├── tsconfig.json                       # Configuração TypeScript
├── package.json                        # Dependências npm
└── README.md                           # Este arquivo
```

---

## 🌱 Seeds E2E

**Comando**: `python manage.py seed_e2e_users`

**Cria**:
- **4 usuários** (todos com senha `testpass123`):
  - `coord_e2e@test.com` (grupo: Coordenador)
  - `super_e2e@test.com` (grupo: Superintendência)
  - `controle_e2e@test.com` (grupo: Controle)
  - `formador_e2e@test.com` (sem grupo específico)
- **1 município**: Salvador (BA)
- **1 projeto**: TESTE E2E (fluxo: SUPER)

**Comando é idempotente** (pode rodar múltiplas vezes sem duplicar dados).

---

## 🔄 Fluxo do Teste

### Test Case 1: Criar Solicitação (Coordenador)
1. Login como `coord_e2e@test.com`
2. Navegar para `/solicitacoes/nova`
3. Preencher formulário (projeto: TESTE E2E, município: Salvador, formador: Formador E2E)
4. Salvar e capturar ID da solicitação criada
5. **Assert**: `status = 'pendente'`, `gcal_event_id = null`

### Test Case 2: Aprovar Solicitação (Superintendência)
1. Login como `super_e2e@test.com`
2. Navegar para `/aprovacoes`
3. Encontrar solicitação criada
4. Aprovar com justificativa
5. **Assert**: `status = 'aprovado'`

### Test Case 3: Preview + Publish GCal (Controle)
1. Login como `controle_e2e@test.com`
2. Navegar para `/pre-agenda`
3. Fazer preview (validar payload)
4. Publicar no Google Calendar (fake client)
5. **Assert**:
   - `gcal_event_id` match `/^fake-event-\d+/`
   - `gcal_payload_hash` tem 64 caracteres (SHA256)

### Test Case 4: Validar AuditLog
1. Consultar API `/api/audit-log/`
2. **Assert**: Pelo menos 3 logs (CREATE, APPROVE, PUBLISH)

---

## 🐛 Troubleshooting

### Erro: "locator not found"

**Causa**: Seletor CSS/XPath mudou no frontend.

**Solução**:
1. Atualizar selectors em `fixtures/selectors.ts`
2. Adicionar `data-testid` nos componentes React (recomendado):
   ```jsx
   <button data-testid="btn-aprovar">Aprovar</button>
   ```

### Erro: "Timeout waiting for response"

**Causa**: Backend lento ou não está rodando.

**Solução**:
1. Verificar status: `cd v2/infra && docker compose ps`
2. Aumentar timeout em `playwright.config.js`:
   ```js
   use: {
     actionTimeout: 15000,  // 15s
     navigationTimeout: 45000,  // 45s
   }
   ```

### Erro: "GCAL_CLIENT not fake"

**Causa**: Variável não configurada.

**Solução**:
1. Criar `.env` em `v2/tests/playwright/`:
   ```
   GCAL_CLIENT=fake
   ```
2. Ou exportar: `export GCAL_CLIENT=fake`

### Erro: "solicitacaoId not set by previous test"

**Causa**: Testes rodaram fora de ordem ou primeiro teste falhou.

**Solução**:
1. Rodar testes sequencialmente (configurado em `playwright.config.js`):
   ```js
   fullyParallel: false,
   workers: 1,
   ```
2. Verificar logs do primeiro teste case.

### Erro: "Seeds E2E não criados"

**Causa**: Comando `seed_e2e_users` não foi executado.

**Solução**:
```bash
cd v2/infra
make seed-e2e
```

---

## 📊 Relatórios

Playwright gera relatórios automáticos em:
- **HTML Report**: `v2/tests/playwright/test-results/html/index.html`
- **JSON Report**: `v2/tests/playwright/test-results/results.json`

**Ver relatório**:
```bash
npm run test:report
```

---

## 🚀 CI/CD (Futuro)

Draft workflow preparado: `.github/workflows/e2e-tests.yml.draft`

**Necessidades**:
- Docker Compose up (db, redis, web)
- Node.js 18 para Playwright
- `GCAL_CLIENT=fake`
- Tempo estimado: 3-5 min por run

---

## 📝 Notas

- **Fake GCal Client**: Testes usam client fake para evitar dependência de credenciais reais.
- **Padrão fake**: `gcal_event_id = fake-event-{timestamp}`
- **Limpeza de dados**: Seeds são idempotentes; testes não limpam dados após execução.
- **Browser headless**: Configurado por padrão (CI-friendly).

---

## 📚 Referências

- [Playwright Docs](https://playwright.dev/docs/intro)
- [Playwright TypeScript](https://playwright.dev/docs/test-typescript)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Plano DAT/GCal](../../docs/PLANO_DAT_GCAL_2025-10-29.md)

---

**Última atualização**: 2025-10-29 (Fase 2 - Testes E2E completos)
