# Plano de Refatoração Frontend - Redução de Over-Engineering

**Data:** 2025-12-30
**Status:** Planejado
**Estimativa Total:** ~4.000 linhas reduzidas

---

## Sumário Executivo

Análise identificou oportunidades de simplificação no frontend do módulo DAT:

| Problema | Impacto | Issue |
|----------|---------|-------|
| Código duplicado (CRUD) | ~2.000 linhas | #302 |
| Arquivos >1000 linhas | ~2.000 linhas | #303 |
| Arquivo obsoleto | 467 linhas | #304 |

**Total estimado de redução:** ~4.000 linhas (17% do frontend)

---

## Fase 1: Fundação (Issue #302)

### Objetivo
Criar hook `useCrudOperations` para eliminar código duplicado.

### Entregáveis
1. `src/hooks/useCrudOperations.js` - Hook principal
2. `src/hooks/useCrudOperations.test.js` - Testes unitários
3. Refatoração de 1 página como proof of concept

### Código do Hook

```javascript
// src/hooks/useCrudOperations.js
import { useState, useCallback } from 'react';
import { message, Modal } from 'antd';

/**
 * Hook para operações CRUD com tratamento de erro padronizado.
 *
 * @param {Object} config
 * @param {Function} config.listFn - Função para listar registros
 * @param {Function} config.createFn - Função para criar registro
 * @param {Function} config.updateFn - Função para atualizar registro
 * @param {Function} config.deleteFn - Função para deletar registro
 * @param {string} config.entityName - Nome da entidade (para mensagens)
 * @returns {Object} Estado e handlers CRUD
 */
export function useCrudOperations({
  listFn,
  createFn,
  updateFn,
  deleteFn,
  entityName = 'registro',
}) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = useCallback(async (params = {}) => {
    setLoading(true);
    try {
      const response = await listFn(params);
      setData(response.results || response);
      if (response.count !== undefined) {
        setPagination(prev => ({ ...prev, total: response.count }));
      }
    } catch (error) {
      message.error(`Erro ao carregar ${entityName}s: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [listFn, entityName]);

  const handleCreate = useCallback(async (values) => {
    try {
      await createFn(values);
      message.success(`${entityName} criado com sucesso`);
      fetchData();
      return true;
    } catch (error) {
      message.error(`Erro ao criar ${entityName}: ${error.message}`);
      return false;
    }
  }, [createFn, entityName, fetchData]);

  const handleUpdate = useCallback(async (id, values) => {
    try {
      await updateFn(id, values);
      message.success(`${entityName} atualizado com sucesso`);
      fetchData();
      return true;
    } catch (error) {
      message.error(`Erro ao atualizar ${entityName}: ${error.message}`);
      return false;
    }
  }, [updateFn, entityName, fetchData]);

  const confirmDelete = useCallback((record, options = {}) => {
    const { idField = 'id', nameField = 'nome' } = options;

    Modal.confirm({
      title: `Excluir ${entityName}?`,
      content: record[nameField]
        ? `Deseja excluir "${record[nameField]}"? Esta ação não pode ser desfeita.`
        : 'Esta ação não pode ser desfeita.',
      okText: 'Excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteFn(record[idField]);
          message.success(`${entityName} excluído com sucesso`);
          fetchData();
        } catch (error) {
          message.error(`Erro ao excluir ${entityName}: ${error.message}`);
        }
      },
    });
  }, [deleteFn, entityName, fetchData]);

  return {
    // Estado
    loading,
    data,
    pagination,

    // Ações
    fetchData,
    handleCreate,
    handleUpdate,
    confirmDelete,

    // Setters (para casos especiais)
    setData,
    setPagination,
  };
}

export default useCrudOperations;
```

### Dependências
- Nenhuma (pode ser implementado independentemente)

### Critérios de Aceite
- [ ] Hook criado e exportado
- [ ] Testes com >80% cobertura
- [ ] 1 página refatorada como exemplo
- [ ] Documentação JSDoc completa

---

## Fase 2: Refatoração de Páginas (Issue #303)

### Objetivo
Dividir páginas grandes em componentes menores (<300 linhas cada).

### Estrutura Alvo

```
pages/DATModule/
├── Cadastros/
│   ├── index.jsx           # Container (~100 linhas)
│   ├── CadastrosTable.jsx  # Tabela (~200 linhas)
│   ├── CadastrosForm.jsx   # Modal form (~200 linhas)
│   ├── CadastrosStats.jsx  # Estatísticas (~100 linhas)
│   └── constants.js        # Constantes (~50 linhas)
├── Coordenadores/
│   ├── index.jsx
│   ├── CoordenadoresTable.jsx
│   ├── CoordenadoresForm.jsx
│   ├── AlocacoesModal.jsx
│   └── constants.js
├── DATRegistros/
│   ├── index.jsx
│   ├── DATRegistrosTable.jsx
│   ├── DATRegistrosForm.jsx
│   └── constants.js
└── Formacoes/
    ├── index.jsx
    ├── FormacoesTable.jsx
    ├── FormacoesForm.jsx
    └── constants.js
```

### Ordem de Execução

| Ordem | Página | Linhas Atuais | Meta | Prioridade |
|-------|--------|---------------|------|------------|
| 1 | CadastrosPage | 1.169 | ~650 | Alta |
| 2 | CoordenadoresPage | 1.148 | ~600 | Alta |
| 3 | DATRegistrosPage | 1.013 | ~500 | Média |
| 4 | FormacoesPage | 1.008 | ~500 | Média |

### Dependências
- Depende de #302 (hook) para máxima redução

### Critérios de Aceite
- [ ] Cada componente < 300 linhas
- [ ] Todos os testes E2E passando
- [ ] Funcionalidade 100% preservada
- [ ] Imports atualizados em App.jsx/rotas

---

## Fase 3: Limpeza (Issue #304)

### Objetivo
Remover arquivo obsoleto.

### Ação
```bash
git rm v2/frontend/src/pages/Solicitacoes/NewSolicitacaoPage.old.jsx
```

### Verificação Prévia
```bash
# Confirmar que não há imports
grep -r "NewSolicitacaoPage.old" v2/frontend/src/
# Deve retornar vazio
```

### Dependências
- Nenhuma (pode ser feito a qualquer momento)

---

## Cronograma Sugerido

```
Semana 1: Fase 1 (Hook useCrudOperations)
├── Dia 1-2: Implementar hook + testes
├── Dia 3: Refatorar CadastrosPage como PoC
└── Dia 4-5: Code review + ajustes

Semana 2-3: Fase 2 (Refatoração de Páginas)
├── Dia 1-3: CadastrosPage completo
├── Dia 4-6: CoordenadoresPage
├── Dia 7-8: DATRegistrosPage
└── Dia 9-10: FormacoesPage

Semana 3: Fase 3 + Finalização
├── Deletar arquivo obsoleto
├── Testes E2E completos
└── Documentação final
```

---

## Métricas de Sucesso

| Métrica | Antes | Depois | Redução |
|---------|-------|--------|---------|
| Linhas totais (7 páginas DAT) | 7.200 | ~3.500 | 51% |
| Arquivo mais longo | 1.169 | ~300 | 74% |
| Código duplicado | ~2.000 | ~200 | 90% |
| Arquivos obsoletos | 1 | 0 | 100% |

---

## Issues Relacionadas

- #302 - Hook useCrudOperations
- #303 - Split large DATModule pages
- #304 - Remove obsolete file

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar funcionalidade | Média | Alto | Testes E2E antes/depois |
| Introduzir bugs | Média | Médio | Code review rigoroso |
| Atrasos | Baixa | Baixo | Fases independentes |

---

## Aprovação

- [ ] Tech Lead
- [ ] QA
- [ ] Product Owner (se afetar entregas)
