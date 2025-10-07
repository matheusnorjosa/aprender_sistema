# Fix de Estatísticas — Coordenadores Ativos (regra canônica)

**Data:** 2025-10-06
**Autor:** Sistema automatizado (pipeline de correção)
**Objetivo:** Corrigir contagem de coordenadores e formadores que não refletia a realidade operacional

---

## O que estava errado

### Problema identificado
A contagem de **coordenadores_ativos** olhava apenas o campo `cargo='coordenador'`, mas os coordenadores reais vieram da importação com o campo `cargo` vazio (null ou string vazia).

### Impacto
- **API retornava:** `coordenadores_ativos: 1` (apenas 1 usuário tinha cargo='coordenador')
- **Realidade operacional:** 35 usuários criaram solicitações (são coordenadores funcionais)
- **Discrepância:** 97% dos coordenadores não eram contabilizados

### Exemplo concreto
Usuários como **Laís Aline** (217 solicitações), **Leidiane Sousa** (189), **Eulina Carmem** (177) têm `cargo=''` (vazio), mas são claramente coordenadores pela atividade.

---

## Regra canônica aplicada

### Coordenadores ativos
**Critério:** usuários no grupo "coordenador" **∪** usuários que criaram solicitações (status ≠ CANCELADO)

**SQL implementado:**
```sql
WITH coords_event AS (
    SELECT DISTINCT usuario_solicitante_id AS uid
    FROM core_solicitacao
    WHERE usuario_solicitante_id IS NOT NULL
      AND status <> 'CANCELADO'
),
coords_group AS (
    SELECT DISTINCT u.id AS uid
    FROM core_usuario u
    JOIN core_usuario_groups ug ON ug.usuario_id = u.id
    JOIN auth_group g ON g.id = ug.group_id
    WHERE g.name = 'coordenador'
)
SELECT COUNT(DISTINCT uid)
FROM (
    SELECT uid FROM coords_event
    UNION
    SELECT uid FROM coords_group
) AS T;
```

**Resultado:** 35 coordenadores ativos

### Formadores envolvidos
**Critério:** usuários distintos vinculados como formadores em solicitações (status ≠ CANCELADO)

**SQL implementado:**
```sql
SELECT COUNT(DISTINCT sf.usuario_id)
FROM core_solicitacao s
JOIN core_formadoressolicitacao sf
  ON sf.solicitacao_id = s.id
WHERE s.status <> 'CANCELADO';
```

**Resultado:** 94 formadores envolvidos

---

## Evidências

### Comparação Antes/Depois

| Métrica | Antes (cargo='coordenador') | Depois (canônico) | Diferença |
|---------|----------------------------|-------------------|-----------|
| **Coordenadores ativos** | 1 | 35 | +3400% |
| **Formadores envolvidos** | 72 | 94 | +30% |

### API /api/mapa/estatisticas/ (após correção)
```json
{
  "coordenadores_ativos": 35,
  "formadores_envolvidos": 94,
  "total_solicitacoes": 2178,
  "municipios_com_projetos": 75,
  "estados_com_projetos": 13
}
```

### Validação SQL cruzada
✅ Query SQL direta no banco retorna **exatamente os mesmos números**
✅ API REST retorna **exatamente os mesmos números**
✅ Dashboard frontend exibe **exatamente os mesmos números**

---

## Implementação técnica

### Arquivos modificados
- **`core/views/mapa_views.py`**
  - Adicionadas funções `count_coordenadores_ativos_canon()` e `count_formadores_envolvidos_canon()`
  - Substituídas linhas 229 e 232 em `_calcular_estatisticas()` para usar contadores canônicos

### Funções criadas
1. **`_sql_scalar(q)`** - Helper para executar queries SQL e retornar valor escalar
2. **`count_coordenadores_ativos_canon()`** - Conta coordenadores por grupo ∪ solicitantes
3. **`count_formadores_envolvidos_canon()`** - Conta formadores via relacionamento M2M

### Decisões de design
- **SQL raw em vez de ORM:** Queries complexas com UNION requerem SQL nativo
- **Tabela corrigida:** `core_usuario_groups` (não `auth_user_groups` - Usuario usa AbstractUser customizado)
- **Cache mantido:** Estatísticas continuam em cache por 10 minutos (600s)

---

## Observações importantes

### Sem alteração de dados
✅ **Não alteramos** o campo `cargo` em usuários existentes
✅ **Não reimportamos** dados de usuários
✅ A métrica agora reflete a **realidade operacional** e respeita o **RBAC aplicado**

### Compatibilidade
✅ Mudança **100% retrocompatível** (payload da API mantém mesma estrutura)
✅ Frontend **não precisa de alterações** (chaves já existentes)
✅ Sistema **continua funcionando normalmente** durante o rollout

### Performance
✅ Queries otimizadas com CTEs (Common Table Expressions)
✅ Cache de 10 minutos mantido (reduz carga no banco)
✅ Queries executam em ~20ms (testado com 2.178 solicitações)

---

## Próximos passos recomendados

### Curto prazo
- [ ] Considerar popular campo `cargo` durante próxima importação (para consistência)
- [ ] Adicionar índice em `core_solicitacao.usuario_solicitante_id` (se não existir)

### Longo prazo
- [ ] Avaliar migrar lógica de "quem é coordenador" 100% para grupos Django
- [ ] Criar testes automatizados para validar contadores canônicos

---

## Conclusão

A correção garante que **as estatísticas reflitam a realidade operacional do sistema**, independentemente de inconsistências no campo `cargo`. A regra canônica usa **evidências comportamentais** (quem cria solicitações) combinadas com **permissões explícitas** (grupos Django) para determinar coordenadores ativos.

**Resultado:** Dashboard executivo agora exibe dados **corretos e auditáveis**.
