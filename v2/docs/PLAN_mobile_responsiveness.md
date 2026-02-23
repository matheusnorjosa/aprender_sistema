# Plano de Implementação: Responsividade Mobile

**Data**: 2026-02-04
**Status**: Planejado
**Epic**: Mobile Responsiveness

---

## Visão Geral

Este plano documenta todas as melhorias necessárias para tornar o frontend do Aprender Sistema v2 totalmente responsivo para dispositivos móveis.

### Breakpoints Utilizados
- **Mobile**: < 768px (smartphones)
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

---

## Fase 1: Prioridade Alta (Crítico)

### Issue #1: Larguras Fixas em Select/Input Components

**Arquivos Afetados:**
- `src/pages/AdminDAT/GruposPage.tsx`
- `src/pages/AdminDAT/MunicipiosPage.tsx`
- `src/pages/AdminDAT/ProjetosPage.tsx`
- `src/pages/AdminDAT/UsuariosPage.tsx`
- `src/pages/Aprovacoes/ApprovalsPage.tsx`

**Problema:**
Componentes Select e Input com largura fixa em pixels (250px, 300px, 400px) que não se adaptam em telas menores.

**Solução:**
```tsx
// Antes
<Select style={{ width: 250 }} />

// Depois
<Select style={{ width: '100%', maxWidth: 250 }} />
// ou com classe CSS
<Select className="w-full sm:w-[250px]" />
```

**Critérios de Aceite:**
- [ ] Todos os Select devem ocupar 100% da largura em mobile
- [ ] Em desktop, manter largura máxima definida
- [ ] Sem overflow horizontal em telas de 375px

---

### Issue #2: Colunas de Tabela Responsivas

**Arquivos Afetados:**
- `src/pages/AdminDAT/UsuariosPage.tsx`
- `src/pages/AdminDAT/MunicipiosPage.tsx`
- `src/pages/AdminDAT/GruposPage.tsx`
- `src/pages/AdminDAT/ProjetosPage.tsx`
- `src/pages/Aprovacoes/ApprovalsPage.tsx`
- `src/pages/Solicitacoes/MySolicitacoesPage.tsx`
- `src/pages/DATModule/CadastrosPage.tsx`
- `src/pages/DATModule/FormacoesPage.tsx`
- `src/pages/DATModule/CoordenadoresPage.tsx`
- `src/pages/DATModule/AcoesPage.tsx`
- `src/pages/DATModule/ComprasPage.tsx`
- `src/pages/PreAgenda/PreAgendaPage.tsx`
- `src/pages/Deslocamentos/DeslocamentosPage.tsx`
- `src/pages/Dashboards/DashboardsPage.tsx`
- `src/pages/Dashboards/EquipeDashboardPage.tsx`
- `src/pages/Dashboards/GCalDashboardPage.tsx`

**Problema:**
Tabelas mostram todas as colunas em todas as resoluções, causando overflow horizontal e colunas ilegíveis.

**Solução:**
Usar prop `responsive` do Ant Design Table para ocultar colunas menos importantes em mobile:

```tsx
// Antes
{
  title: 'Criado em',
  dataIndex: 'created_at',
  width: 150,
}

// Depois
{
  title: 'Criado em',
  dataIndex: 'created_at',
  width: 150,
  responsive: ['md'], // Ocultar em < 768px
}
```

**Padrão de Colunas:**
| Coluna | Visibilidade |
|--------|--------------|
| ID/Nome | Sempre visível |
| Status | Sempre visível |
| Ações | Sempre visível |
| Datas | `responsive: ['md']` |
| Descrição | `responsive: ['lg']` |
| Detalhes secundários | `responsive: ['xl']` |

**Critérios de Aceite:**
- [ ] Máximo 3-4 colunas visíveis em mobile
- [ ] Colunas essenciais sempre visíveis (nome, status, ações)
- [ ] Indicador visual de scroll horizontal quando necessário

---

### Issue #3: Drawer/Modal Max-Width em Mobile

**Arquivos Afetados:**
- `src/pages/Disponibilidade/DetailsDrawer.tsx`
- Todos os modais de formulário

**Problema:**
Drawers e modais com max-width fixo não ocupam largura total em mobile.

**Solução:**
```tsx
// Drawer
<Drawer
  width={isMobile ? '100%' : 520}
  // ou
  className="w-full sm:max-w-lg"
/>

// Modal
<Modal
  width={isMobile ? '95vw' : 600}
/>
```

**Critérios de Aceite:**
- [ ] Drawers ocupam 100% da largura em mobile
- [ ] Modais ocupam 95vw em mobile com margem de 2.5vw
- [ ] Transições suaves ao abrir/fechar

---

## Fase 2: Prioridade Média

### Issue #4: Padding de Container Responsivo

**Arquivos Afetados:**
- Todas as páginas com `className="p-6"` ou `style={{ padding: '24px' }}`

**Problema:**
Padding de 24px em telas de 375px deixa apenas ~327px para conteúdo.

**Solução:**
```tsx
// Antes
className="p-6"

// Depois
className="p-4 sm:p-6"
```

**Critérios de Aceite:**
- [ ] Padding de 16px em mobile
- [ ] Padding de 24px em tablet/desktop
- [ ] Conteúdo não fica "espremido"

---

### Issue #5: Títulos com Tamanho Responsivo

**Arquivos Afetados:**
- Todas as páginas que usam `<Title level={2}>` ou `<Title level={3}>`

**Problema:**
Títulos com tamanho fixo podem ser muito grandes em mobile.

**Solução via CSS Global (já implementado parcialmente em App.css):**
```css
@media screen and (max-width: 768px) {
  .ant-typography h1, h1.ant-typography {
    font-size: 24px !important;
  }
  .ant-typography h2, h2.ant-typography {
    font-size: 20px !important;
  }
  .ant-typography h3, h3.ant-typography {
    font-size: 18px !important;
  }
}

@media screen and (max-width: 480px) {
  .ant-typography h1, h1.ant-typography {
    font-size: 20px !important;
  }
  .ant-typography h2, h2.ant-typography {
    font-size: 18px !important;
  }
}
```

**Critérios de Aceite:**
- [ ] Títulos legíveis em todas as resoluções
- [ ] Hierarquia visual mantida
- [ ] Sem quebra de layout por títulos grandes

---

### Issue #6: Formulários Empilhados em Mobile

**Arquivos Afetados:**
- `src/pages/AdminDAT/MunicipiosPage.tsx`
- `src/pages/AdminDAT/ProjetosPage.tsx`
- `src/pages/AdminDAT/UsuariosPage.tsx`
- `src/pages/Deslocamentos/DeslocamentosPage.tsx`
- `src/pages/DATModule/CadastrosPage.tsx`

**Problema:**
Formulários em grid não empilham corretamente em mobile.

**Solução:**
```tsx
// Usar grid responsivo
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  <Form.Item>...</Form.Item>
  <Form.Item>...</Form.Item>
</div>

// Ou Ant Design Row/Col
<Row gutter={[16, 16]}>
  <Col xs={24} md={12}>
    <Form.Item>...</Form.Item>
  </Col>
</Row>
```

**Critérios de Aceite:**
- [ ] Campos de formulário em coluna única em mobile
- [ ] 2 colunas em tablet
- [ ] Labels visíveis e não truncados

---

### Issue #7: Mapa do Brasil Responsivo

**Arquivos Afetados:**
- `src/pages/MapaBrasil/MapaBrasilPage.tsx`

**Problema:**
- Container do mapa com altura fixa
- Tooltips podem sair da tela
- Lista de estados pode precisar de ajustes

**Solução:**
```tsx
// Altura responsiva
className="h-[400px] sm:h-[500px] md:h-[600px]"

// Tooltip com posicionamento dinâmico
// Verificar se tooltip cabe na tela antes de posicionar
```

**Critérios de Aceite:**
- [ ] Mapa visível e interativo em mobile
- [ ] Tooltips não saem da viewport
- [ ] Zoom touch funciona corretamente

---

## Fase 3: Prioridade Baixa

### Issue #8: Login Page Padding Responsivo

**Arquivos Afetados:**
- `src/pages/Auth/LoginPage.tsx`

**Problema:**
Padding-top fixo de 60px pode ser muito em mobile.

**Solução:**
```tsx
className="min-h-screen pt-8 sm:pt-12 md:pt-16"
```

**Critérios de Aceite:**
- [ ] Formulário de login centralizado em todas as resoluções
- [ ] Espaçamento adequado em mobile

---

### Issue #9: Padronizar Breakpoints

**Arquivos Afetados:**
- Todo o codebase

**Problema:**
Uso inconsistente de breakpoints (Tailwind vs Ant Design).

**Solução:**
Documentar e padronizar:
```
Mobile: < 768px (Tailwind: sm, Ant: xs)
Tablet: 768px - 1024px (Tailwind: md, Ant: sm/md)
Desktop: > 1024px (Tailwind: lg/xl, Ant: lg/xl)
```

Usar constantes do `LAYOUT.MOBILE_BREAKPOINT` quando possível.

**Critérios de Aceite:**
- [ ] Documentação de breakpoints atualizada
- [ ] Consistência entre Tailwind e Ant Design

---

### Issue #10: Indicador de Scroll Horizontal em Tabelas

**Arquivos Afetados:**
- `src/App.css`
- Componentes de tabela

**Problema:**
Usuários não percebem que podem scrollar horizontalmente.

**Solução:**
```css
/* Indicador visual de scroll */
.ant-table-wrapper {
  position: relative;
}

.ant-table-wrapper::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 20px;
  background: linear-gradient(to right, transparent, rgba(0,0,0,0.05));
  pointer-events: none;
}

/* Ou usar scroll-snap para UX melhor */
.ant-table-content {
  scroll-snap-type: x mandatory;
}
```

**Critérios de Aceite:**
- [ ] Indicador visual quando há mais conteúdo à direita
- [ ] Scroll suave em touch devices

---

## Ordem de Execução

```
Fase 1 (Alta Prioridade) - Estimativa: 3-4 horas
├── Issue #1: Select/Input widths
├── Issue #2: Table columns responsive
└── Issue #3: Drawer/Modal width

Fase 2 (Média Prioridade) - Estimativa: 2-3 horas
├── Issue #4: Container padding
├── Issue #5: Title sizes (já parcial)
├── Issue #6: Form stacking
└── Issue #7: Map responsiveness

Fase 3 (Baixa Prioridade) - Estimativa: 1-2 horas
├── Issue #8: Login padding
├── Issue #9: Breakpoint standardization
└── Issue #10: Scroll indicators
```

---

## Verificação

Após implementação, testar em:
- [ ] iPhone SE (375px)
- [ ] iPhone 14 (390px)
- [ ] iPad Mini (768px)
- [ ] iPad Pro (1024px)
- [ ] Desktop (1920px)

Usar Chrome DevTools Device Toolbar para simular.

---

## Referências

- [Ant Design Responsive](https://ant.design/components/grid/#components-grid-demo-responsive)
- [Tailwind Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [LAYOUT Constants](../frontend/src/constants/layout.ts)
