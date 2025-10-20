# 🔍 RELATÓRIO - PROBLEMA DE RECURSÃO INFINITA

**Data:** 2025-10-08  
**Status:** 🔍 **DIAGNÓSTICO REALIZADO**  
**Problema:** RecursionError no `MunicipioService.ativos()`

## 🚨 PROBLEMA RELATADO

### ❌ Erro
```python
RecursionError: maximum recursion depth exceeded
```

### 📍 Stack Trace
```
DiretoriaExecutiveDashboardView.get_context_data
  → MunicipioService.ativos().values(...).order_by(...)
    → core/services/data_services.py:433
      → MunicipioService.ativos() [RECURSÃO INFINITA]
```

## 🔍 DIAGNÓSTICO REALIZADO

### ✅ Código Analisado

**core/services/data_services.py:460-463:**
```python
@classmethod
def ativos(cls):
    """Municípios ativos otimizados"""
    from core.models import Municipio
    return Municipio.objects.filter(ativo=True).order_by('nome', 'uf')
```

**core/views/diretoria_views.py:54:**
```python
municipios_queryset = (
    MunicipioService.ativos().values("id", "nome", "uf").order_by("nome", "uf")
)
```

### ✅ Análise do Código

1. **Método `MunicipioService.ativos()`:**
   - ✅ **Parece correto**: Retorna `Municipio.objects.filter(ativo=True).order_by('nome', 'uf')`
   - ✅ **Não chama a si mesmo**: Usa `Municipio.objects` diretamente

2. **View que chama o método:**
   - ✅ **Sintaxe correta**: `MunicipioService.ativos().values(...).order_by(...)`
   - ⚠️ **Possível problema**: `.order_by('nome', 'uf')` duplicado (já está no `ativos()`)

3. **Modelo `Municipio`:**
   - ✅ **Sem manager customizado**: Usa `models.Manager()` padrão
   - ✅ **Sem método `ativos()`**: Não há conflito de nomes

## 🎯 POSSÍVEIS CAUSAS

### 1. ❓ Import Circular (Mais Provável)
**Problema:** Pode haver import circular entre `data_services.py` e `models.py`

**Evidência:**
```python
# core/services/data_services.py:462
from core.models import Municipio  # Import dentro do método
```

**Solução:**
- Mover import para o topo do arquivo
- Verificar se há importação circular

### 2. ❓ Redefinição Dinâmica do Método
**Problema:** Pode haver alguma redefinição do método `ativos()` em tempo de execução

**Solução:**
- Verificar se há decorators ou metaclasses que possam estar alterando o método
- Verificar se há patches ou mocks em testes

### 3. ❓ Problema com Linha 433
**Problema:** A linha 433 mencionada no stack trace não parece ter relação direta

**Código na linha 433:**
```python
# Linha 433 (comentário ou linha vazia no contexto examinado)
```

**Solução:**
- Verificar se a numeração das linhas está correta
- Verificar se há problema de sincronização entre código e erro

### 4. ❓ Cache ou Estado Compartilhado
**Problema:** Pode haver problema com cache ou estado compartilhado

**Solução:**
- Limpar cache do Django
- Reiniciar servidor de desenvolvimento

## 🚀 SOLUÇÕES PROPOSTAS

### ✅ Solução 1: Mover Import para o Topo
```python
# No topo de core/services/data_services.py
from core.models import Municipio

class MunicipioService(BaseService):
    @classmethod
    def ativos(cls):
        """Municípios ativos otimizados"""
        return Municipio.objects.filter(ativo=True).order_by('nome', 'uf')
```

### ✅ Solução 2: Remover `.order_by()` Duplicado na View
```python
# core/views/diretoria_views.py:54
municipios_queryset = (
    MunicipioService.ativos().values("id", "nome", "uf")
    # Remover .order_by("nome", "uf") - já está em ativos()
)
```

### ✅ Solução 3: Adicionar Proteção Anti-Recursão
```python
@classmethod
def ativos(cls):
    """Municípios ativos otimizados"""
    if hasattr(cls, '_in_ativos'):
        raise RecursionError("Recursão detectada em MunicipioService.ativos()")

    cls._in_ativos = True
    try:
        from core.models import Municipio
        return Municipio.objects.filter(ativo=True).order_by('nome', 'uf')
    finally:
        delattr(cls, '_in_ativos')
```

### ✅ Solução 4: Limpar Cache e Reiniciar
```bash
# Limpar cache do Django
docker compose exec web python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache limpo')"

# Reiniciar container web
docker compose restart web
```

## 🏆 RECOMENDAÇÕES

### ✅ Ações Imediatas
1. **Verificar imports circulares** entre `data_services.py` e `models.py`
2. **Remover `.order_by()` duplicado** na view
3. **Limpar cache** do Django
4. **Reiniciar servidor** de desenvolvimento

### ✅ Prevenção Futura
1. **Evitar imports dentro de métodos** quando possível
2. **Usar imports no topo do arquivo** para detectar circulares mais cedo
3. **Adicionar testes** para detectar recursão
4. **Documentar regras** anti-recursão

## 📋 PRÓXIMOS PASSOS

### ✅ Passo 1: Diagnóstico Adicional
```bash
# Verificar se há imports circulares
docker compose exec web python manage.py shell -c "
import core.services.data_services
import core.models
print('Imports OK')
"
```

### ✅ Passo 2: Testar Método Isoladamente
```bash
# Testar método ativos() diretamente
docker compose exec web python manage.py shell -c "
from core.services.data_services import MunicipioService
print('Total de municípios ativos:', MunicipioService.ativos().count())
"
```

### ✅ Passo 3: Aplicar Correção
```bash
# Aplicar correção conforme diagnóstico
# (ver soluções propostas acima)
```

## 🏆 CONCLUSÃO

### ✅ DIAGNÓSTICO INCONCLUSIVO
O código examinado **não mostra recursão óbvia**. Possíveis causas:
1. **Import circular** (mais provável)
2. **Redefinição dinâmica** do método
3. **Problema de sincronização** entre código e erro
4. **Cache ou estado compartilhado**

### 🚀 PRÓXIMOS PASSOS
1. **Execute os comandos de diagnóstico** acima
2. **Verifique os imports** circulares
3. **Aplique as correções** propostas
4. **Teste isoladamente** o método

**Execute os comandos de diagnóstico para identificar a causa exata do problema!** 🔍

---

**Relatório Problema Recursão - Sistema Aprender**  
*Diagnóstico e soluções para RecursionError*
