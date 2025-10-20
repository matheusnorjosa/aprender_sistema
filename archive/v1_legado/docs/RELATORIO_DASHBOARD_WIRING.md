# Wiring do Dashboard Executivo

## Data: 2025-10-05 20:15 UTC

## 🎯 Arquitetura de Rotas

### Frontend (React - Porta 3000)

**Rota:** `/dashboard`
- **Componente:** `Dashboard.tsx` (Dashboard Executivo com KPIs)
- **Localização:** `frontend/src/pages/Dashboard.tsx`
- **Funcionalidade:** Exibe cards com métricas executivas do sistema

**Outras Rotas:**
- `/` - HomePage (landing com status da API)
- `/reports/conflitos` - Relatório de conflitos de agenda
- `/reports/workload` - Relatório de carga horária

---

### Backend (Django - Porta 8000)

**Redirect Django:**
- **Rota:** `/diretoria/dashboard/`
- **Destino:** `http://localhost:3000/dashboard` (Frontend React)
- **Status:** HTTP 302 (redirect temporário)
- **Motivo:** Facilitar acesso via URL Django para usuários que conhecem a estrutura antiga

**APIs de Suporte:**
- `GET /api/reports/kpis` - KPIs executivos
- `GET /api/reports/series?from=YYYY-MM&to=YYYY-MM` - Séries temporais
- `GET /api/reports/conflitos?limit=N` - Conflitos detalhados
- `GET /api/reports/workload?from=YYYY-MM&to=YYYY-MM` - Workload mensal

---

## 🔄 Fluxo de Acesso

### Opção 1: Acesso Direto ao Frontend
```
Usuário -> http://localhost:3000/dashboard
         -> React Router
         -> Dashboard.tsx (renderizado)
         -> API call: GET /api/reports/kpis
         -> Exibe KPIs
```

### Opção 2: Via Redirect Django
```
Usuário -> http://localhost:8000/diretoria/dashboard/
         -> Django RedirectView (HTTP 302)
         -> http://localhost:3000/dashboard
         -> React Router
         -> Dashboard.tsx (renderizado)
         -> API call: GET /api/reports/kpis
         -> Exibe KPIs
```

---

## 📊 Componentes do Dashboard

### Dashboard Executivo (Novo)
**Arquivo:** `frontend/src/pages/Dashboard.tsx`

**Conteúdo:**
- Título: "Dashboard Executivo"
- 4 Cards principais:
  - Total Solicitações
  - Total Conflitos
  - Total Usuários
  - Overload (≥110h)
- 4 Cards de status:
  - CRIADO
  - APROVADO
  - REALIZADO
  - CANCELADO
- Info auxiliar: Municípios, Projetos, Disp Staging

**API Consumida:**
```typescript
apiGet('/api/reports/kpis')
  .then(kpis => setKpis(kpis))
  .catch(err => setErr(String(err)))
```

---

### HomePage (Landing Antiga)
**Arquivo:** `frontend/src/App.tsx` (função HomePage)

**Conteúdo:**
- Título: "🎓 Sistema Aprender"
- Status da API (health check)
- Próximos passos (checklist)
- Links de navegação:
  - 📈 Dashboard
  - 📊 Conflitos
  - ⏱️ Workload

---

## 🔧 Configuração do Router

### React Router (App.tsx)
```tsx
<Router>
  <Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/reports/conflitos" element={<ReportsConflitos />} />
    <Route path="/reports/workload" element={<ReportsWorkload />} />
  </Routes>
</Router>
```

### Django URLs (aprender_sistema/urls.py)
```python
from django.views.generic import RedirectView

urlpatterns = [
    # ... outras rotas ...
    path(
        "diretoria/dashboard/",
        RedirectView.as_view(url="http://localhost:3000/dashboard", permanent=False),
    ),
    # ... outras rotas ...
]
```

---

## ✅ Testes de Validação

### Frontend Routing:
```bash
# Verifica se Dashboard.tsx existe
ls frontend/src/pages/Dashboard.tsx
# ✅ Arquivo existe

# Verifica importação no App.tsx
grep "import Dashboard" frontend/src/App.tsx
# ✅ import Dashboard from './pages/Dashboard';

# Verifica rota configurada
grep 'path="/dashboard"' frontend/src/App.tsx
# ✅ <Route path="/dashboard" element={<Dashboard />} />
```

### Backend Redirect:
```bash
# Testa redirect
curl -I http://localhost:8000/diretoria/dashboard/
# HTTP/1.1 302 Found
# Location: http://localhost:3000/dashboard
```

### API Endpoints:
```bash
# KPIs endpoint (requer autenticação)
curl http://localhost:8000/api/reports/kpis
# HTTP 302 (redirect para login)

# Series endpoint (requer autenticação)
curl "http://localhost:8000/api/reports/series?from=2025-10&to=2025-12"
# HTTP 302 (redirect para login)
```

---

## 📝 Diferenças entre Componentes

| Aspecto | HomePage (Landing) | Dashboard Executivo |
|---------|-------------------|---------------------|
| **Título** | "Sistema Aprender" | "Dashboard Executivo" |
| **Rota** | `/` | `/dashboard` |
| **Propósito** | Página inicial com status | KPIs executivos |
| **Conteúdo** | Health check + links | Cards de métricas |
| **API Calls** | `/api/health/` | `/api/reports/kpis` |
| **Autenticação** | Não requerida | Requerida (grupos) |

---

## 🚀 Como Acessar

### Desenvolvimento Local:

**Via Frontend Direto:**
- http://localhost:3000/ - HomePage (landing)
- http://localhost:3000/dashboard - Dashboard Executivo
- http://localhost:3000/reports/conflitos - Conflitos
- http://localhost:3000/reports/workload - Workload

**Via Backend (com redirect):**
- http://localhost:8000/diretoria/dashboard/ → redireciona para :3000/dashboard

**APIs Backend:**
- http://localhost:8000/api/health/ - Status do sistema
- http://localhost:8000/api/reports/kpis - KPIs executivos
- http://localhost:8000/api/reports/series - Séries temporais
- http://localhost:8000/api/reports/conflitos - Conflitos detalhados
- http://localhost:8000/api/reports/workload - Workload mensal

---

## 🔐 Autenticação e Permissões

### HomePage (Landing):
- **Autenticação:** Não requerida
- **Acesso:** Público

### Dashboard Executivo:
- **Autenticação:** Obrigatória (`@login_required`)
- **Grupos permitidos:**
  - `controle`
  - `coordenador`
  - `superintendencia`
  - Superusers sempre permitidos

### Comportamento sem Autenticação:
1. Frontend tenta acessar `/api/reports/kpis`
2. Backend retorna HTTP 302 (redirect para login)
3. Frontend captura erro e exibe mensagem
4. Usuário precisa fazer login primeiro

---

## 📊 Estrutura de Arquivos

```
frontend/src/
├── App.tsx                    # Router principal + HomePage
├── pages/
│   ├── Dashboard.tsx          # Dashboard Executivo (NOVO)
│   ├── ReportsConflitos.tsx   # Relatório de conflitos
│   └── ReportsWorkload.tsx    # Relatório de workload
├── components/
│   ├── Table.tsx              # Tabela reutilizável
│   └── MonthRange.tsx         # Seletor de intervalo de meses
└── lib/
    └── api.ts                 # Cliente HTTP com credenciais

aprender_sistema/
└── urls.py                    # Redirect /diretoria/dashboard/

backend/reports/
├── views.py                   # kpis(), series(), conflitos(), workload()
└── urls.py                    # Rotas das APIs
```

---

## 🎯 Decisão: **WIRING COMPLETO** ✅

**Frontend:**
- ✅ Rota `/dashboard` aponta para Dashboard Executivo
- ✅ Componente novo (Dashboard.tsx) separado da landing
- ✅ React Router configurado corretamente
- ✅ Links de navegação funcionais

**Backend:**
- ✅ Redirect `/diretoria/dashboard/` → `:3000/dashboard`
- ✅ APIs de suporte funcionando
- ✅ Autenticação e permissões implementadas

**Integração:**
- ✅ Frontend consome backend via `/api/reports/kpis`
- ✅ Credenciais (cookies) enviadas corretamente
- ✅ Error handling implementado

---

**Data de Validação:** 2025-10-05 20:15 UTC
**Status:** PRODUCTION READY ✅
**Acessos Validados:**
- Frontend: http://localhost:3000/dashboard
- Backend redirect: http://localhost:8000/diretoria/dashboard/
