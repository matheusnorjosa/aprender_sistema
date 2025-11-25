# Backlog: Frontend Code-Splitting

## Status Atual (2025-11-25)

**Build output:**
```
dist/assets/index-P8cEm4kX.js   1,749.61 kB │ gzip: 539.64 kB

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

## Problema

O bundle JavaScript principal está com **1.7 MB** (539 kB gzipped), excedendo o limite recomendado de 500 kB. Isso pode impactar:
- **Tempo de carregamento inicial** (especialmente em conexões lentas)
- **Parsing/compilation** do JavaScript no navegador
- **Core Web Vitals** (FCP, TTI)

## Análise de Componentes Pesados

Principais bibliotecas no bundle (estimativa):
- **React + React-DOM**: ~140 kB (gzipped)
- **Ant Design**: ~300-400 kB (gzipped, com ícones)
- **Leaflet** (mapa): ~40-50 kB
- **date-fns**: ~20-30 kB
- **Application code**: restante

## Estratégias de Code-Splitting

### Opção 1: Route-Based Splitting (Recomendado)

Dividir por rotas principais usando React.lazy():

```javascript
// src/App.jsx
import { lazy, Suspense } from 'react';

// Lazy load páginas principais
const Dashboard = lazy(() => import('./pages/Dashboard/DashboardPage'));
const Solicitacoes = lazy(() => import('./pages/Solicitacoes/SolicitacoesPage'));
const MapaBrasil = lazy(() => import('./pages/MapaBrasil/MapaBrasilPage'));
const PreAgenda = lazy(() => import('./pages/PreAgenda/PreAgendaPage'));
const Aprovacoes = lazy(() => import('./pages/Aprovacoes/ApprovacoesPage'));

// No router
<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/solicitacoes" element={<Solicitacoes />} />
    {/* ... */}
  </Routes>
</Suspense>
```

**Benefício esperado**: Redução de ~40-50% no bundle inicial

### Opção 2: Component-Level Splitting

Lazy load componentes pesados:

```javascript
// Leaflet map (usado apenas em MapaBrasil)
const MapView = lazy(() => import('./components/MapView'));

// Chart libraries (se houver dashboards)
const Charts = lazy(() => import('./components/Charts'));
```

### Opção 3: Vendor Splitting (Manual Chunks)

Configurar `vite.config.js` para separar vendors:

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'leaflet-vendor': ['leaflet', 'react-leaflet'],
          'utils': ['date-fns', 'dayjs'],
        }
      }
    }
  }
}
```

**Benefício esperado**:
- Cache de vendors separado (não invalida em mudanças de código)
- Chunks paralelos (download concorrente)

### Opção 4: Ant Design Tree-Shaking

Importar apenas componentes usados:

```javascript
// Antes (importa tudo)
import { Button, Table, Modal } from 'antd';

// Depois (tree-shaking automático já funciona com ES modules)
// Verificar se há imports de subpaths desnecessários
```

## Plano de Implementação

### Fase 1: Quick Wins (2-3h)

1. **Vendor splitting** via manualChunks
2. **Lazy load MapaBrasil** (página com Leaflet)
3. **Verificar imports desnecessários** (Ant Design icons não usados)

### Fase 2: Route-Based Splitting (3-4h)

1. Implementar React.lazy() nas rotas principais
2. Adicionar Suspense com loading spinner
3. Testar carregamento de cada rota

### Fase 3: Medições e Ajustes (2h)

1. Usar **Lighthouse** para medir FCP/TTI antes e depois
2. Analisar **bundle analyzer** (rollup-plugin-visualizer)
3. Ajustar chunks se necessário

## Estimativa

- **Esforço total**: 7-9h
- **Complexidade**: Média
- **Prioridade**: Baixa (otimização, não-bloqueante)
- **Impacto**: Médio (melhora performance, não adiciona features)

## Métricas de Sucesso

**Antes:**
- Bundle principal: 1,749.61 kB (539.64 kB gzipped)
- FCP: ~X segundos (não medido)

**Meta (após code-splitting):**
- Bundle inicial: <800 kB (<250 kB gzipped)
- FCP: redução de 20-30%
- Chunks: 4-6 chunks (main + 3-5 lazy)

## Referências

- [Vite Code Splitting](https://vitejs.dev/guide/features.html#code-splitting)
- [React.lazy documentation](https://react.dev/reference/react/lazy)
- [Rollup manualChunks](https://rollupjs.org/configuration-options/#output-manualchunks)
- Build warning: `npm run build` output (2025-11-25)

## Próximos Passos

1. Criar issue no GitHub: "chore(frontend): evaluate code-splitting to reduce bundle size"
2. Adicionar milestone "v2.1" (otimização pós-MVP)
3. Priorizar após features críticas (RF01-RF07)

## Commits de Referência

- Auditoria bundle size: Sistema audit 2025-11-25
