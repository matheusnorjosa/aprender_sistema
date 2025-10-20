# PR 8/N - Hotfix: RemoteSelect Loop Infinito

**Data:** 2025-10-14
**Status:** ✅ Corrigido

---

## 🐛 Bug Identificado

### Problema #1: Loop Infinito no RemoteSelect

**Sintoma:**
```
Maximum update depth exceeded. This can happen when a component calls setState inside
useEffect, but useEffect either doesn't have a dependency array, or one of the
dependencies changes on every render.
```

**Causa Raiz:**
```jsx
// v2/frontend/src/components/RemoteSelect.jsx:81-91 (ANTES)
useEffect(() => {
  if (!disabled) {
    loadOptions('');
  }
}, [loadOptions, disabled]);  // ❌ loadOptions muda a cada render!
```

**Problema:**
- `loadOptions` é um `useCallback` que depende de `fetchOptions` e `extraParams`
- Se `extraParams` muda por referência, `loadOptions` é recriado
- `useEffect` detecta mudança em `loadOptions` → executa novamente
- Executa `loadOptions('')` → pode acionar re-render
- Ciclo infinito: render → useEffect → loadOptions → render...

---

### Problema #2: 403 Forbidden nos Endpoints Options API

**Sintoma:**
```
GET http://localhost:8002/api/options/municipios/ 403 (Forbidden)
GET http://localhost:8002/api/options/tipos-evento/ 403 (Forbidden)
GET http://localhost:8002/api/options/formadores/ 403 (Forbidden)
```

**Causa Raiz:**
- Usuário **não está autenticado**
- Endpoints Options API exigem `IsAuthenticated` permission
- Session cookie não está presente

---

## ✅ Correções Aplicadas

### Correção #1: RemoteSelect useEffect

**Arquivo:** `v2/frontend/src/components/RemoteSelect.jsx`

**Antes:**
```jsx
useEffect(() => {
  if (!disabled) {
    loadOptions('');
  }
  return () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
  };
}, [loadOptions, disabled]);  // ❌ Bug: loadOptions muda sempre
```

**Depois:**
```jsx
useEffect(() => {
  if (!disabled) {
    loadOptions('');
  }
  return () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [disabled, JSON.stringify(extraParams)]);  // ✅ Dependências estáveis
```

**Justificativa:**
- Removida dependência `loadOptions` (causa do loop)
- Mantida dependência `disabled` (necessária)
- Adicionada `JSON.stringify(extraParams)` (detecta mudanças reais em extraParams)
- `eslint-disable` para suprimir aviso sobre `loadOptions` ausente (seguro neste caso)

**Benefícios:**
- ✅ Loop infinito eliminado
- ✅ `useEffect` só executa quando `disabled` ou `extraParams` mudam de verdade
- ✅ Performance melhorada (menos execuções desnecessárias)

---

### Correção #2: Instruções de Autenticação

**Problema:** 403 Forbidden ocorre porque usuário não está logado.

**Solução:** Fazer login no Django Admin antes de abrir o frontend.

---

## 🧪 Como Testar

### Teste #1: Verificar Loop Eliminado

**Passos:**
1. Abrir http://localhost:5173/solicitar
2. Abrir DevTools (F12) → Console
3. Verificar: **NÃO deve haver** mensagens de loop infinito
4. Verificar: RemoteSelects carregam apenas **1 vez** ao montar

**Resultado Esperado:**
- ✅ Console limpo (sem erros de "Maximum update depth")
- ✅ Loading dos selects rápido
- ✅ Página responsiva

### Teste #2: Resolver 403 Forbidden

**Passos:**
1. Fazer login no Django Admin: http://localhost:8002/admin
   - Usuário: `admin` (ou seu superuser)
   - Senha: (sua senha)
2. Abrir em **nova aba** ou **mesma janela**: http://localhost:5173/solicitar
3. Verificar console: endpoints Options API devem retornar **200 OK**

**Resultado Esperado:**
```
✅ GET http://localhost:8002/api/options/municipios/ 200 (OK)
✅ GET http://localhost:8002/api/options/tipos-evento/ 200 (OK)
✅ GET http://localhost:8002/api/options/formadores/ 200 (OK)
```

---

## 📊 Análise Técnica

### Por que `JSON.stringify(extraParams)` é seguro?

**Problema:**
```jsx
// Se extraParams é criado inline no pai:
<RemoteSelect extraParams={{ municipioId: 1 }} />
// Cada render cria um NOVO objeto (referência diferente)
// useEffect detecta mudança mesmo que valores sejam iguais
```

**Solução:**
```jsx
JSON.stringify({ municipioId: 1 }) === JSON.stringify({ municipioId: 1 })
// true → useEffect NÃO executa novamente
```

**Alternativa (mais verbosa):**
```jsx
// Criar useMemo no componente pai:
const extraParams = useMemo(() => ({ municipioId }), [municipioId]);
<RemoteSelect extraParams={extraParams} />
```

**Escolha:** `JSON.stringify` é mais simples e igualmente eficaz.

---

### Por que 403 Forbidden?

**Arquitetura de Autenticação:**
```
Frontend (5173) → Backend (8002)
                ↓
         Session Cookie
         (sessionid=xxx)
                ↓
         IsAuthenticated
         permission check
```

**Fluxo Correto:**
1. Usuário faz login no Django Admin (8002)
2. Django cria session cookie `sessionid`
3. Cookie é enviado automaticamente em requisições subsequentes (CORS configurado com `credentials: 'include'`)
4. Backend valida sessão → permite acesso

**Se 403:**
- Cookie de sessão ausente ou expirado
- Usuário não logado
- CORS bloqueando cookies (mas já corrigimos isso)

---

## 🔧 Arquivos Modificados

**Frontend (1 arquivo):**
1. `v2/frontend/src/components/RemoteSelect.jsx` - useEffect corrigido (linha 92)

---

## 📝 Checklist de Validação

- [x] Loop infinito corrigido
- [x] Dependências do useEffect estáveis
- [ ] Usuário fez login no Django Admin
- [ ] Endpoints Options API retornam 200 OK
- [ ] RemoteSelects carregam dados corretamente
- [ ] Formulário "Nova Solicitação" funcional

---

## 🎯 Próximos Passos

1. **Fazer login:** http://localhost:8002/admin
2. **Recarregar frontend:** http://localhost:5173/solicitar
3. **Verificar console:** Deve estar limpo (sem 403, sem loop)
4. **Testar formulário:** Preencher e criar solicitação

---

## 🚀 Status

**Loop Infinito:** ✅ **CORRIGIDO**
**403 Forbidden:** ⚠️ **Requer ação do usuário** (fazer login)

---

**Gerado automaticamente em:** 2025-10-14 18:40 BRT
**Por:** Claude Code (Anthropic)
**Fix:** RemoteSelect useEffect dependencies
