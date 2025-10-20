# Melhorias Futuras - Sistema Aprender v2

**Data de criação:** 2025-10-14
**Status:** Backlog de melhorias não-urgentes

---

## 🎯 Objetivo

Este documento mapeia melhorias de código que **não impactam a funcionalidade**, mas melhoram a qualidade e reduzem warnings.

**Prioridade:** BAIXA (sistema 100% funcional)

---

## ⚠️ Warnings do Ant Design a Resolver

### 1. `[antd: Spin] tip only work in nest or fullscreen pattern`

**Arquivo:** `v2/frontend/src/App.jsx` (linha ~55)

**Problema:**
```jsx
<Spin tip="Carregando...">
  {/* conteúdo */}
</Spin>
```

**Correção:**
```jsx
<Spin spinning={loading} size="large">
  {/* conteúdo */}
</Spin>
```

**OU** usar fullscreen:
```jsx
<Spin tip="Carregando..." spinning={loading} fullscreen />
```

**Impacto:** Zero (apenas warning visual)

---

### 2. `[antd: Menu] children is deprecated. Please use items instead`

**Arquivo:** `v2/frontend/src/App.jsx` (linha ~69)

**Problema:**
```jsx
<Menu mode="horizontal">
  <Menu.Item key="1">Item 1</Menu.Item>
  <Menu.Item key="2">Item 2</Menu.Item>
</Menu>
```

**Correção:**
```jsx
const menuItems = [
  { key: '1', label: 'Item 1' },
  { key: '2', label: 'Item 2' },
];

<Menu mode="horizontal" items={menuItems} />
```

**Impacto:** Zero (API antiga ainda funcional)

**Referência:** https://ant.design/components/menu#API

---

### 3. `findDOMNode is deprecated`

**Arquivo:** Interno do Ant Design (não é nosso código)

**Problema:**
- Ant Design v5 ainda usa `findDOMNode` internamente
- React 18 deprecou essa API

**Correção:**
- Aguardar atualização do Ant Design para v6 (quando lançar)
- OU ignorar (não impacta funcionalidade)

**Impacto:** Zero (problema interno do framework)

**Nota:** Não podemos corrigir, pois está no código do Ant Design.

---

### 4. `[antd: Card] bordered is deprecated. Please use variant instead`

**Arquivo:** `v2/frontend/src/pages/Disponibilidade.jsx` (linha ~81)

**Problema:**
```jsx
<Card bordered={false}>
  {/* conteúdo */}
</Card>
```

**Correção:**
```jsx
<Card variant="borderless">
  {/* conteúdo */}
</Card>
```

**Impacto:** Zero (API antiga ainda funcional)

**Referência:** https://ant.design/components/card#API

---

## 📋 Checklist de Implementação (quando priorizar)

- [ ] Corrigir `<Spin tip>` no App.jsx
- [ ] Migrar Menu de `children` para `items` API
- [ ] Corrigir Card `bordered` → `variant`
- [ ] ~~Corrigir findDOMNode~~ (aguardar Ant Design v6)

---

## 🔧 Como Implementar

**1. Criar branch:**
```bash
git checkout -b chore/fix-antd-warnings
```

**2. Aplicar correções** (seguir exemplos acima)

**3. Testar:**
```bash
npm run dev
# Verificar console: warnings devem desaparecer
```

**4. Commit:**
```bash
git add .
git commit -m "chore(frontend): fix Ant Design deprecation warnings"
```

**5. PR:**
```bash
git push origin chore/fix-antd-warnings
# Criar PR no GitHub
```

---

## 📊 Benefícios

✅ Console mais limpo (melhor DX)
✅ Código preparado para Ant Design v6
✅ Seguir best practices do framework
✅ Reduzir ruído em logs de desenvolvimento

---

## ⚠️ Não-Urgente

**Por quê?**
- Sistema 100% funcional
- Warnings não afetam usuários
- API antiga ainda suportada pelo Ant Design
- Pode ser feito em qualquer momento

**Quando fazer?**
- Quando houver tempo disponível
- Antes de upgrade do Ant Design para v6
- Durante refatoração de código
- Em sprint de melhorias técnicas

---

**Criado em:** 2025-10-14
**Por:** Claude Code (Anthropic)
**Motivo:** Mapear melhorias não-urgentes identificadas durante PR 8/N
