# Documentação de Testes - Dashboard com Dados Reais

## 📋 Visão Geral

Este documento descreve a suíte completa de testes implementada para o dashboard do Sistema Aprender, que conecta dados reais do banco de dados em substituição aos valores simulados anteriores.

### 🎯 Objetivos dos Testes

- ✅ **Funcionalidade:** Verificar se todos os recursos funcionam corretamente
- ⚡ **Performance:** Garantir resposta rápida com cache otimizado  
- 🔒 **Confiabilidade:** Assegurar consistência dos dados
- 🔄 **Compatibilidade:** Manter backward compatibility
- 📊 **Métricas:** Validar cálculos de estatísticas avançadas

---

## 🗂️ Estrutura dos Testes

### COMMIT 1: API Básica (`test_dashboard_api.py`)
```python
class DashboardStatsAPITestCase(TestCase):
    """Testes fundamentais da API dashboard"""
```

**Funcionalidades testadas:**
- ✅ Autenticação obrigatória
- ✅ Schema JSON correto
- ✅ Tipos de dados válidos
- ✅ Cálculos de estatísticas básicas

**Cenários cobertos:**
- Eventos no mês atual vs mês passado
- Contagem de formadores ativos/inativos
- Solicitações pendentes por status
- Municípios distintos atendidos

---

### COMMIT 2: Template (`test_dashboard_template.py`)
```python
class DashboardTemplateTestCase(TestCase):
    """Testes de renderização e integração do template"""
```

**Funcionalidades testadas:**
- ✅ Renderização sem erro
- ✅ Presença de elementos essenciais
- ✅ URLs da API incluídas
- ✅ JavaScript functions disponíveis
- ✅ CSRF tokens corretos

**Elementos validados:**
- `id="eventos-count"`, `id="formadores-count"`, etc.
- `loadDashboardStats()` function
- `animateCounter()` function
- URL da API dashboard

---

### COMMIT 3: Filtros (`test_dashboard_filters.py`)
```python
class DashboardFiltersTestCase(TestCase):
    """Testes de filtros dinâmicos"""
```

**Funcionalidades testadas:**
- ✅ Filtro por período (7/30/90/365 dias)
- ✅ Filtro por projeto
- ✅ Filtro por município
- ✅ Combinação de filtros
- ✅ Validação de parâmetros inválidos

**Cenários específicos:**
- Período de 7 dias deve retornar ≤ eventos que 30 dias
- Filtro por projeto deve reduzir contagem
- Filtros combinados funcionam corretamente
- Parâmetros inválidos não quebram a API

---

### COMMIT 4: Performance (`test_dashboard_performance.py`)
```python
class DashboardPerformanceTestCase(TestCase):
    """Testes de performance e cache"""
```

**Funcionalidades testadas:**
- ⚡ Cache cold vs warm (deve ser >20% mais rápido)
- 🔑 Chaves de cache únicas por usuário
- 🔄 Consistência dos dados cached
- 💾 Fallback quando cache indisponível
- ⏱️ Tempo de resposta < 1s (cold), < 0.1s (warm)

**Métricas de performance:**
- **Cold cache:** < 1 segundo
- **Warm cache:** < 0.1 segundo  
- **Queries:** ≤ 6 queries por requisição
- **Cache speedup:** Mínimo 20% melhoria

---

### COMMIT 5: Métricas Avançadas (`test_metricas_avancadas.py`)
```python
class MetricasAvancadasTestCase(TestCase):
    """Testes das métricas avançadas"""
```

**Funcionalidades testadas:**
- 📊 Taxa de aprovação (aprovadas/total × 100)
- 🏆 Top 5 formadores por horas trabalhadas
- 🌍 Top 5 municípios por volume de eventos
- 📈 Tendência semanal (últimas 4 semanas)
- 🔧 Compatibilidade com API anterior

**Cálculos validados:**
- **Taxa aprovação:** `(aprovadas / total) * 100`
- **Horas formadores:** Soma de `(data_fim - data_inicio)`
- **Volume municípios:** Count eventos aprovados
- **Tendência:** Agregação por `TruncWeek()`

---

### COMMIT 6: Suíte Completa (`test_dashboard_suite.py`)
```python
class DashboardTestSuite(TestCase):
    """Suíte consolidada de todos os testes"""
```

**Funcionalidades testadas:**
- 🔄 Integração end-to-end
- 🔙 Compatibilidade retroativa
- 🧪 Testes de regressão
- 💥 Casos extremos (dados vazios, filtros inválidos)
- 📊 Relatório consolidado

---

## 🚀 Executando os Testes

### Execução Básica

```bash
# Todos os testes do dashboard
python manage.py test core.test_dashboard_suite

# Teste específico por commit
python manage.py test core.test_dashboard_api        # COMMIT 1
python manage.py test core.test_dashboard_template   # COMMIT 2
python manage.py test core.test_dashboard_filters    # COMMIT 3
python manage.py test core.test_dashboard_performance # COMMIT 4
python manage.py test core.test_metricas_avancadas   # COMMIT 5

# Teste individual
python manage.py test core.test_dashboard_api.DashboardStatsAPITestCase.test_dashboard_stats_api_json_schema
```

### Validação Completa com Script

```bash
# Execução básica
python validate_dashboard_tests.py

# Com verbose e coverage
python validate_dashboard_tests.py --verbose --coverage

# Apenas coverage
python validate_dashboard_tests.py -c
```

### Saída Esperada
```
=============================================================
 RELATÓRIO DA SUÍTE DE TESTES DO DASHBOARD
=============================================================
API Básica (COMMIT 1): 4 testes
Template (COMMIT 2): 2 testes
Filtros (COMMIT 3): 2 testes
Performance (COMMIT 4): 2 testes
Métricas Avançadas (COMMIT 5): 2 testes
Integração (COMMIT 6): 3 testes
-------------------------------------------------------------
TOTAL DE TESTES EXECUTADOS: 15
=============================================================

🎯 SCORE GERAL: 100% (4/4)
🏆 EXCELENTE - Dashboard pronto para produção!
```

---

## 🧪 Cenários de Teste

### Dados de Teste Criados

Cada suíte cria um conjunto consistente de dados:

```python
# Usuários
coordenador = User(username='test_user', papel='coordenador')

# Projetos  
projeto_alpha = Projeto(nome='Projeto Alpha')
projeto_beta = Projeto(nome='Projeto Beta')

# Municípios
sao_paulo = Municipio(nome='São Paulo', uf='SP')
rio_janeiro = Municipio(nome='Rio de Janeiro', uf='RJ')

# Formadores
joao = Formador(nome='João', ativo=True)
maria = Formador(nome='Maria', ativo=True)
pedro = Formador(nome='Pedro', ativo=False)  # Inativo

# Eventos com diferentes status e períodos
evento_aprovado_recente = Solicitacao(
    status=APROVADO, 
    data_inicio=agora - 5 dias,
    duracao=4 horas
)
evento_aprovado_antigo = Solicitacao(
    status=APROVADO,
    data_inicio=agora - 25 dias, 
    duracao=6 horas
)
evento_pendente = Solicitacao(
    status=PENDENTE,
    data_inicio=agora + 5 dias
)
evento_reprovado = Solicitacao(
    status=REPROVADO,
    data_inicio=agora - 10 dias
)
```

### Assertions Típicas

```python
# Schema da API
self.assertIn('estatisticas', data)
self.assertIn('metricas_avancadas', data)
self.assertIsInstance(stats['eventos_periodo'], int)

# Performance
self.assertLess(warm_time, cold_time)  # Cache é mais rápido
self.assertLess(response_time, 1.0)    # < 1 segundo

# Filtros
self.assertGreaterEqual(eventos_30d, eventos_7d)  # 30d >= 7d
self.assertIn('Projeto: Alpha', filtros_aplicados)

# Métricas
self.assertEqual(taxa_aprovacao, 75.0)  # (3/4) * 100
self.assertEqual(top_formadores[0]['nome'], 'João')
```

---

## 📊 Métricas de Qualidade

### Cobertura de Código
- **Meta:** ≥ 90% cobertura para código do dashboard
- **Comando:** `python validate_dashboard_tests.py --coverage`
- **Relatório:** Gerado em `htmlcov/index.html`

### Performance Benchmarks
- **Cold cache:** < 1000ms
- **Warm cache:** < 100ms  
- **Speedup:** Mínimo 5x melhoria
- **Queries:** ≤ 6 por requisição

### Qualidade dos Testes
- **Isolamento:** Cada teste limpa cache/dados
- **Determinismo:** Resultados consistentes
- **Cobertura:** Casos normais + extremos
- **Documentação:** Todos os testes documentados

---

## 🔧 Troubleshooting

### Problemas Comuns

**❌ Cache não funciona**
```python
# Verificar configuração
from django.core.cache import cache
cache.set('test', 'value', 30)
print(cache.get('test'))  # Deve retornar 'value'
```

**❌ Queries lentas**
```python
# Debug queries
from django.db import connection
print(connection.queries)  # Listar todas as queries
```

**❌ Dados inconsistentes**
```python
# Verificar timezone
from django.utils import timezone
print(timezone.now())  # Deve usar timezone correto
```

### Debug de Testes

```bash
# Executar teste específico com debug
python manage.py test core.test_dashboard_api.DashboardStatsAPITestCase.test_eventos_mes_calculation --debug-mode

# Manter banco de dados de teste
python manage.py test --keepdb

# Verbose output
python manage.py test -v 2
```

---

## 🔄 Manutenção dos Testes

### Adicionando Novos Testes

1. **Escolher módulo correto:**
   - API básica → `test_dashboard_api.py`
   - Template → `test_dashboard_template.py`
   - Filtros → `test_dashboard_filters.py`
   - Performance → `test_dashboard_performance.py`
   - Métricas → `test_metricas_avancadas.py`
   - Integração → `test_dashboard_suite.py`

2. **Seguir padrões:**
   ```python
   def test_nova_funcionalidade(self):
       """Descrição clara do que o teste valida"""
       # Arrange - preparar dados
       # Act - executar ação
       # Assert - verificar resultado
   ```

3. **Atualizar suíte:**
   - Adicionar ao `test_dashboard_suite.py`
   - Atualizar `validate_dashboard_tests.py`
   - Documentar neste arquivo

### Atualizando Após Mudanças

**Mudança na API:**
1. Atualizar `test_dashboard_api.py`
2. Verificar compatibilidade em `test_dashboard_suite.py`
3. Executar suíte completa

**Nova métrica:**
1. Adicionar teste em `test_metricas_avancadas.py`
2. Verificar performance em `test_dashboard_performance.py`
3. Atualizar documentação

---

## 📈 Roadmap de Testes

### ✅ Implementado (Commits 1-6)
- API básica com dados reais
- Template rendering  
- Filtros dinâmicos
- Cache e performance
- Métricas avançadas
- Suíte de integração

### 🔮 Futuras Melhorias
- Testes de carga com múltiplos usuários
- Testes de acessibilidade
- Testes cross-browser
- Monitoring de performance em produção
- Testes de segurança (SQL injection, XSS)

---

## 🏆 Critérios de Aceite

**Para considerar os testes completos, deve atender:**

✅ **Funcionalidade (100%):** Todos os recursos testados  
✅ **Performance (95%+):** Cache e otimizações funcionais  
✅ **Cobertura (90%+):** Código relevante coberto  
✅ **Confiabilidade (100%):** Testes determinísticos  
✅ **Manutenibilidade (95%+):** Código organizado e documentado  

**Comando de validação final:**
```bash
python validate_dashboard_tests.py --coverage
# Deve retornar: 🏆 EXCELENTE - Dashboard pronto para produção!
```