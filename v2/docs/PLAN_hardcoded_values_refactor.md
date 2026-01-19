# Plano: Refatoração de Valores Hardcoded

**Epic**: #437 (a ser criado)
**Data**: 2026-01-19
**Prioridade**: Alta (Dívida Técnica)

---

## Contexto

Auditoria identificou valores hardcoded no frontend e backend que deveriam ser configuráveis ou centralizados em constantes. Isso dificulta manutenção, testes e customização.

---

## Issues do Epic

| Issue | Título | Prioridade | Estimativa |
|-------|--------|------------|------------|
| #438 | `[HARDCODE-01]` Criar estrutura de constantes frontend | CRÍTICO | 1h |
| #439 | `[HARDCODE-02]` Consolidar cores no ThemeContext | CRÍTICO | 2h |
| #440 | `[HARDCODE-03]` Corrigir anos hardcoded (dinâmico) | CRÍTICO | 30min |
| #441 | `[HARDCODE-04]` Corrigir lista de UFs incompleta | CRÍTICO | 30min |
| #442 | `[HARDCODE-05]` Mover portas OAuth para env vars | CRÍTICO | 1h |
| #443 | `[HARDCODE-06]` Centralizar timeouts no backend | MÉDIO | 1h |
| #444 | `[HARDCODE-07]` Centralizar page sizes | MÉDIO | 1h |
| #445 | `[HARDCODE-08]` Consolidar listas de UF duplicadas | MÉDIO | 1h |
| #446 | `[HARDCODE-09]` Mover URLs externas para config | MÉDIO | 30min |

**Total Estimado**: ~9 horas

---

## Issue #438: Criar Estrutura de Constantes Frontend

### Objetivo
Criar arquivos de constantes centralizados para layout, timing, pagination e validation.

### Arquivos a Criar

```
v2/frontend/src/constants/
├── index.js          # Re-export all
├── layout.js         # Dimensões de layout
├── timing.js         # Intervalos, delays, timeouts
├── pagination.js     # Tamanhos de página
└── validation.js     # Limites de caracteres, min/max
```

### Implementação

#### `constants/layout.js`
```javascript
/**
 * Layout constants - Centralized dimensions
 */

export const LAYOUT = {
  // Sidebar
  SIDEBAR_WIDTH: 250,

  // Input widths
  INPUT_WIDTH_SMALL: 200,
  INPUT_WIDTH_MEDIUM: 300,
  INPUT_WIDTH_LARGE: 400,

  // Dialog/Modal widths
  DIALOG_WIDTH_SMALL: 520,
  DIALOG_WIDTH_MEDIUM: 600,
  DIALOG_WIDTH_LARGE: 800,
  DIALOG_WIDTH_XLARGE: 900,

  // Table scroll widths
  TABLE_SCROLL_SMALL: 800,
  TABLE_SCROLL_MEDIUM: 1000,
  TABLE_SCROLL_LARGE: 1200,
  TABLE_SCROLL_XLARGE: 1400,
};
```

#### `constants/timing.js`
```javascript
/**
 * Timing constants - Intervals, delays, timeouts
 */

export const TIMING = {
  // Polling intervals
  ALERT_POLL_INTERVAL_MS: 30000,      // 30 seconds

  // Cooldowns
  TOAST_COOLDOWN_MS: 120000,          // 2 minutes

  // CSRF
  CSRF_TOKEN_TTL_MS: 30 * 60 * 1000,  // 30 minutes

  // Debounce
  DEBOUNCE_DEFAULT_MS: 300,
  DEBOUNCE_SEARCH_MS: 400,

  // Delays
  GCAL_DETAIL_LOAD_DELAY_MS: 2000,
};
```

#### `constants/pagination.js`
```javascript
/**
 * Pagination constants - Page sizes
 */

export const PAGE_SIZES = {
  TINY: 5,
  SMALL: 10,
  DEFAULT: 15,
  MEDIUM: 20,
  LARGE: 50,
  XLARGE: 100,
  ALL: 1000,  // For "load all" scenarios
};

export const DEFAULT_PAGE_SIZE = PAGE_SIZES.DEFAULT;
```

#### `constants/validation.js`
```javascript
/**
 * Validation constants - Character limits, min/max values
 */

export const VALIDATION = {
  // Character limits
  MAX_CHARS_SHORT: 50,
  MAX_CHARS_MEDIUM: 100,
  MAX_CHARS_LONG: 300,
  MAX_CHARS_TEXT: 500,
  MAX_CHARS_DESCRIPTION: 1000,

  // Numeric limits (ConfiguracoesPage)
  SESSION_COOKIE_AGE_MIN: 300,
  SESSION_COOKIE_AGE_MAX: 86400,
  TRAVEL_BUFFER_MIN: 30,
  TRAVEL_BUFFER_MAX: 480,
  BATCH_SIZE_MIN: 50,
  BATCH_SIZE_MAX: 1000,
};
```

#### `constants/index.js`
```javascript
/**
 * Constants barrel export
 */

export * from './layout';
export * from './timing';
export * from './pagination';
export * from './validation';
```

### Arquivos a Modificar

1. **`App.jsx`**: Usar `LAYOUT.SIDEBAR_WIDTH`
2. **`api/config.js`**: Usar `TIMING.CSRF_TOKEN_TTL_MS`
3. **`hooks/useDebouncedOptions.js`**: Usar `TIMING.DEBOUNCE_DEFAULT_MS`
4. **`components/RemoteSelect.jsx`**: Usar `TIMING.DEBOUNCE_SEARCH_MS`
5. **`pages/Dashboards/GCalDashboardPage.jsx`**: Usar `TIMING.GCAL_DETAIL_LOAD_DELAY_MS`

### Verificação
- [ ] Build passa sem erros
- [ ] Lint passa
- [ ] App funciona normalmente

---

## Issue #439: Consolidar Cores no ThemeContext

### Objetivo
Mover todas as cores hardcoded de componentes para o ThemeContext.

### Cores a Migrar

| Arquivo | Cor | Uso |
|---------|-----|-----|
| `LoginPage.jsx:39` | `#004B3D` | Background página |
| `LoginPage.jsx:57` | `#E5EDE5` | Background card |
| `LoginPage.jsx:60` | `#004B3D` | Texto título |
| `App.jsx:325` | `#006B52` | Sidebar background |
| `App.jsx:335` | `rgba(255,255,255,0.1)` | Border sidebar |
| `App.jsx:511` | `#f0f2f5` | Content background |
| `GoogleIntegrationCard.jsx` | `#ff4d4f`, `#faad14`, `#52c41a` | Status colors |

### Implementação

#### Atualizar `ThemeContext.jsx`

```javascript
// Adicionar ao arquivo existente:

export const BRAND_COLORS = {
  // Primary brand colors
  primary: '#006B52',
  primaryDark: '#004B3D',
  primaryLight: '#E5EDE5',

  // Backgrounds
  pageBackground: '#f0f2f5',
  cardBackground: '#ffffff',
  sidebarBackground: '#006B52',

  // Borders
  borderLight: 'rgba(255, 255, 255, 0.1)',
  borderDefault: '#d9d9d9',

  // Status colors (use Ant Design tokens when possible)
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  info: '#1890ff',

  // Status backgrounds
  successBg: '#f6ffed',
  warningBg: '#fffbe6',
  errorBg: '#fff2f0',
};

// Hook para acessar cores
export function useBrandColors() {
  const { isDark } = useTheme();
  return {
    ...BRAND_COLORS,
    // Override for dark mode if needed
    pageBackground: isDark ? '#141414' : BRAND_COLORS.pageBackground,
    cardBackground: isDark ? '#1f1f1f' : BRAND_COLORS.cardBackground,
    sidebarBackground: isDark ? '#141414' : BRAND_COLORS.sidebarBackground,
  };
}
```

#### Atualizar `LoginPage.jsx`

```javascript
import { useBrandColors } from '../../contexts/ThemeContext';

export default function LoginPage({ onLoginSuccess }) {
  const colors = useBrandColors();

  return (
    <div style={{ background: colors.primaryDark, ... }}>
      <div style={{ background: colors.primaryLight, ... }}>
        <h2 style={{ color: colors.primaryDark, ... }}>
```

#### Atualizar `App.jsx`

```javascript
import { useBrandColors } from './contexts/ThemeContext';

function AppContent() {
  const colors = useBrandColors();

  // Usar colors.sidebarBackground, colors.pageBackground, etc.
```

### Verificação
- [ ] Cores consistentes em light/dark mode
- [ ] Login page renderiza corretamente
- [ ] Sidebar com cores corretas

---

## Issue #440: Corrigir Anos Hardcoded

### Objetivo
Substituir anos hardcoded por cálculo dinâmico.

### Arquivos Afetados

1. **`ComprasPage.jsx:72-74`**
```javascript
// ANTES:
const ANO_OPTIONS = [2024, 2025, 2026].map(...)

// DEPOIS:
const currentYear = new Date().getFullYear();
const ANO_OPTIONS = [currentYear - 1, currentYear, currentYear + 1].map(...)
```

2. **`PlanoFormacoesPage.jsx:556`**
```javascript
// ANTES:
title="Formacoes 2025"

// DEPOIS:
title={`Formações ${new Date().getFullYear()}`}
```

### Verificação
- [ ] Anos corretos aparecem nos dropdowns
- [ ] Título dinâmico no PlanoFormacoes

---

## Issue #441: Corrigir Lista de UFs Incompleta

### Objetivo
Corrigir `MunicipiosPage.jsx` que lista apenas 9 estados em vez de 27.

### Problema
```javascript
// Linha 164 - Apenas 9 estados do Nordeste
options={['BA', 'CE', 'PE', 'RN', 'SE', 'AL', 'PB', 'PI', 'MA'].map(...)}
```

### Solução
Usar a lista completa de UFs que já existe em outros arquivos:

```javascript
// Importar de constants ou criar arquivo centralizado
import { UF_LIST } from '../../constants/brazil';

// Usar:
options={UF_LIST.map(uf => ({ value: uf, label: uf }))}
```

### Criar `constants/brazil.js`
```javascript
/**
 * Brazilian geography constants
 */

export const UF_LIST = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
];

export const UF_NORDESTE = ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'];
```

**Nota**: Se a restrição a 9 estados for intencional (escopo do projeto), documentar isso no código.

---

## Issue #442: Mover Portas OAuth para Env Vars

### Objetivo
Remover hardcodes de portas no fluxo OAuth.

### Arquivo: `views_oauth.py`

```python
# ANTES (linhas 121-136):
if ':5173' in origin:
    frontend_origin = origin
if ':8002' not in origin:
    frontend_origin = origin
if not frontend_origin:
    frontend_origin = "http://localhost:5173"

# DEPOIS:
from django.conf import settings

FRONTEND_DEV_PORT = getattr(settings, 'FRONTEND_DEV_PORT', '5173')
BACKEND_PORT = getattr(settings, 'BACKEND_PORT', '8002')

if f':{FRONTEND_DEV_PORT}' in origin:
    frontend_origin = origin
if f':{BACKEND_PORT}' not in origin:
    frontend_origin = origin
if not frontend_origin:
    frontend_origin = os.getenv('FRONTEND_URL', f'http://localhost:{FRONTEND_DEV_PORT}')
```

### Adicionar em `settings.py`
```python
# OAuth Frontend/Backend ports (dev)
FRONTEND_DEV_PORT = os.getenv('FRONTEND_DEV_PORT', '5173')
BACKEND_PORT = os.getenv('BACKEND_PORT', '8002')
```

---

## Issue #443: Centralizar Timeouts no Backend

### Objetivo
Mover todos os timeouts hardcoded para settings.

### Constantes a Criar em `settings.py`

```python
# ================================================================
# TIMEOUTS & CACHE
# ================================================================
CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))  # 5 min
REDIS_LOCK_TIMEOUT = int(os.getenv('REDIS_LOCK_TIMEOUT', 300))  # 5 min

# Google API
GOOGLE_API_TIMEOUT = int(os.getenv('GOOGLE_API_TIMEOUT', 10))  # 10 sec
GOOGLE_OAUTH_TIMEOUT = int(os.getenv('GOOGLE_OAUTH_TIMEOUT', 600))  # 10 min
GOOGLE_API_MAX_RETRIES = int(os.getenv('GOOGLE_API_MAX_RETRIES', 3))

# Circuit Breaker
GCAL_CIRCUIT_BREAKER_FAIL_MAX = int(os.getenv('GCAL_CB_FAIL_MAX', 5))
GCAL_CIRCUIT_BREAKER_RESET_TIMEOUT = int(os.getenv('GCAL_CB_RESET_TIMEOUT', 60))

# Celery
CELERY_DEFAULT_RETRY_DELAY = int(os.getenv('CELERY_RETRY_DELAY', 300))
```

### Arquivos a Modificar

1. **`views_options.py`**: Substituir `timeout=300` por `timeout=settings.CACHE_DEFAULT_TIMEOUT`
2. **`preagenda_to_gcal.py`**: Usar `settings.REDIS_LOCK_TIMEOUT`
3. **`google_oauth.py`**: Usar `settings.GOOGLE_API_TIMEOUT`
4. **`circuit_breaker.py`**: Usar settings para fail_max e reset_timeout
5. **`tasks.py`, `tasks_backup.py`**: Usar `settings.CELERY_DEFAULT_RETRY_DELAY`

---

## Issue #444: Centralizar Page Sizes

### Objetivo
Usar constantes de paginação em vez de valores hardcoded.

### Frontend

Modificar arquivos para usar `PAGE_SIZES` de `constants/pagination.js`:

| Arquivo | Atual | Novo |
|---------|-------|------|
| `UsuariosPage.jsx:34` | `pageSize: 10` | `PAGE_SIZES.SMALL` |
| `GruposPage.jsx:48` | `page_size: 1000` | `PAGE_SIZES.ALL` |
| `GCalDashboardPage.jsx:154` | `pageSize = 20` | `PAGE_SIZES.MEDIUM` |
| `ApprovalsPage.jsx:440` | `pageSize: 20` | `PAGE_SIZES.MEDIUM` |
| `FormacoesPage.jsx:74` | `pageSize: 15` | `PAGE_SIZES.DEFAULT` |
| `useCrudOperations.js:51` | `pageSize = 15` | `PAGE_SIZES.DEFAULT` |
| `api/etl.js:25` | `limit = 20` | `PAGE_SIZES.MEDIUM` |

---

## Issue #445: Consolidar Listas de UF Duplicadas

### Objetivo
Centralizar lista de UFs que está duplicada em 5 arquivos.

### Arquivos com Duplicação

1. `DATModule/Cadastros/constants.jsx` - 27 UFs
2. `DATModule/AcoesPage.jsx` - 27 UFs
3. `DATModule/ComprasPage.jsx` - 27 UFs
4. `DATModule/DATRegistros/constants.jsx` - 27 UFs
5. `AdminDAT/MunicipiosPage.jsx` - 9 UFs (Nordeste)

### Solução

1. Criar `constants/brazil.js` (ver Issue #441)
2. Importar em todos os arquivos

```javascript
// Em cada arquivo:
import { UF_LIST } from '../../constants/brazil';

// Substituir a lista hardcoded por:
const UF_OPTIONS = UF_LIST.map(uf => ({ value: uf, label: uf }));
```

---

## Issue #446: Mover URLs Externas para Config

### Objetivo
Mover URLs de plataformas externas para configuração.

### URLs Identificadas

1. **Frontend** `Cadastros/constants.jsx:23`
   - `https://www.aprenderformar.com.br/plataforma/`

2. **Frontend** `Cadastros/constants.jsx:36`
   - `https://avaliar.aprenderformar.com.br/`

3. **Backend** `dat_registro.py:324`
   - `https://www.aprenderformar.com.br/plataforma/course/view.php?id={id}`

### Solução

#### Frontend: Criar `constants/urls.js`
```javascript
/**
 * External URLs configuration
 */

export const EXTERNAL_URLS = {
  FORMAR_PLATFORM: import.meta.env.VITE_FORMAR_URL || 'https://www.aprenderformar.com.br/plataforma/',
  AVALIAR_PLATFORM: import.meta.env.VITE_AVALIAR_URL || 'https://avaliar.aprenderformar.com.br/',
};
```

#### Backend: Adicionar em `settings.py`
```python
# External Platforms
FORMAR_PLATFORM_BASE_URL = os.getenv(
    'FORMAR_PLATFORM_URL',
    'https://www.aprenderformar.com.br/plataforma'
)
```

#### Modificar `dat_registro.py`
```python
from django.conf import settings

@property
def turma_formar_url(self) -> str | None:
    if self.turma_formar_id:
        return f"{settings.FORMAR_PLATFORM_BASE_URL}/course/view.php?id={self.turma_formar_id}"
    return None
```

---

## Ordem de Execução

```
Fase 1 (Crítico - Paralelo):
├── #438: Criar estrutura de constantes
├── #440: Corrigir anos hardcoded
├── #441: Corrigir lista UFs incompleta
└── #442: Mover portas OAuth

Fase 2 (Crítico - Sequencial após #438):
└── #439: Consolidar cores no ThemeContext

Fase 3 (Médio - Paralelo):
├── #443: Centralizar timeouts backend
├── #444: Centralizar page sizes
├── #445: Consolidar listas UF duplicadas
└── #446: Mover URLs externas
```

---

## Verificação Final

- [ ] Todos os builds passam (frontend + backend)
- [ ] Todos os testes passam
- [ ] Pyright sem erros
- [ ] ESLint sem erros
- [ ] App funciona em dev
- [ ] Nenhum valor hardcoded crítico restante
