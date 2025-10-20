# 🔍 RELATÓRIO DE DIAGNÓSTICO - DADOS FALTANDO

**Data:** 2025-10-08  
**Problema:** Página de disponibilidade sem dados  
**Status:** 🔍 **DIAGNÓSTICO EM ANDAMENTO**

## 🚨 PROBLEMA IDENTIFICADO

### ❌ Situação Atual
- **"Nenhum formador encontrado"** no dropdown
- **0 FORMADORES** nas estatísticas
- **Tabela vazia** sem dados
- **0 EVENTOS, 0 BLOQUEIOS, 0 CONFLITOS, 0 DISPONÍVEIS**

### ✅ Sistema Funcionando
- ✅ **Filtro SUPER ativo** (correto)
- ✅ **Interface carregando** sem erros
- ✅ **Deslocamentos configurados** (marcador "D" na legenda)
- ✅ **Performance adequada**

## 🔍 POSSÍVEIS CAUSAS

### 1. ❌ Dados Não Importados
**Causa mais provável:**
- Usuários não foram importados
- Vínculos de setor não foram criados
- Dados de disponibilidade não foram importados

### 2. ❌ Filtro Muito Restritivo
**Possível causa:**
- `FEATURE_SUPER_FALLBACK = False` muito restritivo
- Nenhum usuário com papel `SUPER`
- Nenhum usuário no grupo `COORDENADOR`

### 3. ❌ Dados Inconsistentes
**Possível causa:**
- Usuários sem vínculos de setor
- Setores não cadastrados
- Dados de disponibilidade ausentes

## 🚀 SOLUÇÕES PROPOSTAS

### ✅ Solução 1: Verificar Dados no Banco
```bash
# Verificar usuários
docker compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
print(f'Total de usuários: {User.objects.count()}')
"

# Verificar vínculos
docker compose exec web python manage.py shell -c "
from core.models import VinculoUsuarioSetor
print(f'Total de vínculos: {VinculoUsuarioSetor.objects.count()}')
"

# Verificar usuários SUPER
docker compose exec web python manage.py shell -c "
from core.models import VinculoUsuarioSetor
supers = VinculoUsuarioSetor.objects.filter(papel='SUPER')
print(f'Usuários SUPER: {supers.count()}')
"
```

### ✅ Solução 2: Importar Dados
```bash
# Importar usuários
docker compose exec web python manage.py import_usuarios data/usuarios.csv

# Importar vínculos de setor
docker compose exec web python manage.py import_vinculos_setor data/vinculos_producao.csv

# Importar disponibilidades
docker compose exec web python manage.py import_disponibilidades data/disponibilidades.csv
```

### ✅ Solução 3: Verificar Configurações
```bash
# Verificar feature flags
docker compose exec web python manage.py shell -c "
from django.conf import settings
print(f'FEATURE_SUPER_FALLBACK: {getattr(settings, \"FEATURE_SUPER_FALLBACK\", \"NÃO DEFINIDO\")}')
print(f'FEATURE_MAP_DESLOCAMENTOS_ENABLED: {getattr(settings, \"FEATURE_MAP_DESLOCAMENTOS_ENABLED\", \"NÃO DEFINIDO\")}')
"
```

### ✅ Solução 4: Temporariamente Relaxar Filtro
```bash
# Temporariamente ativar fallback para ver dados
docker compose exec web python manage.py shell -c "
from django.conf import settings
print('Configuração atual:', getattr(settings, 'FEATURE_SUPER_FALLBACK', 'NÃO DEFINIDO'))
"
```

## 📋 COMANDOS DE DIAGNÓSTICO

### 1. Verificar Usuários
```bash
docker compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
print(f'Total de usuários: {User.objects.count()}')
for u in User.objects.all()[:5]:
    print(f'  - {u.email} ({u.first_name} {u.last_name})')
"
```

### 2. Verificar Vínculos
```bash
docker compose exec web python manage.py shell -c "
from core.models import VinculoUsuarioSetor
print(f'Total de vínculos: {VinculoUsuarioSetor.objects.count()}')
for v in VinculoUsuarioSetor.objects.all()[:5]:
    print(f'  - {v.usuario.email} -> {v.setor.nome if v.setor else \"Sem setor\"} ({v.papel})')
"
```

### 3. Verificar Grupos
```bash
docker compose exec web python manage.py shell -c "
from django.contrib.auth.models import Group
print(f'Grupos: {Group.objects.count()}')
for g in Group.objects.all():
    print(f'  - {g.name}')
"
```

### 4. Verificar Setores
```bash
docker compose exec web python manage.py shell -c "
from core.models import Setor
print(f'Total de setores: {Setor.objects.count()}')
for s in Setor.objects.all()[:5]:
    print(f'  - {s.nome} ({s.sigla})')
"
```

## 🎯 PLANO DE AÇÃO

### 1. Diagnóstico Imediato
```bash
# Executar comandos de verificação acima
# Identificar qual dado está faltando
```

### 2. Importar Dados Necessários
```bash
# Se usuários faltam: import_usuarios
# Se vínculos faltam: import_vinculos_setor
# Se disponibilidades faltam: import_disponibilidades
```

### 3. Verificar Resultado
```bash
# Recarregar página /disponibilidade/
# Verificar se dados aparecem
```

### 4. Ajustar Configurações
```bash
# Se necessário, ajustar feature flags
# Verificar se filtros estão corretos
```

## 🏆 CONCLUSÃO

### 🔍 DIAGNÓSTICO NECESSÁRIO
O sistema está funcionando corretamente, mas **não há dados** para exibir. Isso pode ser devido a:

1. **Dados não importados** (mais provável)
2. **Filtro muito restritivo** (possível)
3. **Dados inconsistentes** (possível)

### 🚀 PRÓXIMOS PASSOS
1. **Execute os comandos de diagnóstico** para identificar o problema
2. **Importe os dados necessários** se estiverem faltando
3. **Verifique o resultado** na página de disponibilidade
4. **Ajuste configurações** se necessário

**Execute os comandos de diagnóstico para identificar exatamente o que está faltando!** 🔍

---

**Diagnóstico Dados Faltando - Sistema Aprender**  
*Identificando e resolvendo problema de dados ausentes*
