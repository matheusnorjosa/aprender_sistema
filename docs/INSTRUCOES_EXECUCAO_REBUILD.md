# 🚀 INSTRUÇÕES PARA EXECUÇÃO DO REBUILD

**Data:** 2025-10-08  
**Status:** 📋 **INSTRUÇÕES PRONTAS**  
**Objetivo:** Resolver problema dos dados faltando

## 🎯 PROBLEMA IDENTIFICADO

**Situação atual:**
- ❌ "Nenhum formador encontrado" na página
- ❌ 0 FORMADORES, 0 EVENTOS, 0 BLOQUEIOS
- ❌ Tabela vazia sem dados
- ✅ Sistema funcionando (interface, filtros, performance)

**Causa:** Dados não foram importados do Google Sheets

## 🚀 SOLUÇÃO - EXECUÇÃO MANUAL

### ✅ PASSO 1: Limpar Dados Existentes
```bash
docker compose exec web python manage.py flush --noinput
```

### ✅ PASSO 2: Aplicar Migrações
```bash
docker compose exec web python manage.py migrate
```

### ✅ PASSO 3: Criar Dados de Teste
```bash
docker compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
from core.models import Setor, VinculoUsuarioSetor, Solicitacao, Participante
from django.utils import timezone
import datetime

User = get_user_model()

# Criar setores
setores_data = [
    {'nome': 'Superintendência', 'sigla': 'SUPER', 'vinculado_superintendencia': True},
    {'nome': 'ACerta', 'sigla': 'ACERTA', 'vinculado_superintendencia': False},
    {'nome': 'Brincando', 'sigla': 'BRINC', 'vinculado_superintendencia': False},
    {'nome': 'Vidas', 'sigla': 'VIDAS', 'vinculado_superintendencia': False},
]

for s_data in setores_data:
    setor, created = Setor.objects.get_or_create(
        nome=s_data['nome'],
        defaults={'sigla': s_data['sigla'], 'ativo': True, 'vinculado_superintendencia': s_data['vinculado_superintendencia']}
    )
    print(f'Setor: {setor.nome}')

# Criar usuários e vínculos
users_data = [
    {'email': 'admin@super.com', 'first_name': 'Admin', 'last_name': 'Super', 'papel': 'SUPER'},
    {'email': 'coord1@acerta.com', 'first_name': 'Coordenador', 'last_name': 'ACerta', 'papel': 'COORDENADOR'},
    {'email': 'form1@acerta.com', 'first_name': 'Formador', 'last_name': 'ACerta', 'papel': 'FORMADOR'},
    {'email': 'coord2@brincando.com', 'first_name': 'Coordenador', 'last_name': 'Brincando', 'papel': 'COORDENADOR'},
    {'email': 'form2@brincando.com', 'first_name': 'Formador', 'last_name': 'Brincando', 'papel': 'FORMADOR'},
]

for u_data in users_data:
    user, created = User.objects.get_or_create(
        email=u_data['email'],
        defaults={
            'username': u_data['email'],
            'first_name': u_data['first_name'],
            'last_name': u_data['last_name'],
            'is_active': True
        }
    )

    # Determinar setor baseado no papel
    if u_data['papel'] == 'SUPER':
        setor = Setor.objects.get(nome='Superintendência')
    elif 'acerta' in u_data['email']:
        setor = Setor.objects.get(nome='ACerta')
    elif 'brincando' in u_data['email']:
        setor = Setor.objects.get(nome='Brincando')
    else:
        setor = Setor.objects.get(nome='Vidas')

    # Criar vínculo
    vinculo, created = VinculoUsuarioSetor.objects.get_or_create(
        usuario=user,
        setor=setor,
        papel=u_data['papel'],
        defaults={'ativo': True}
    )

    print(f'Usuário: {user.email} -> {setor.nome} ({u_data[\"papel\"]})')

print('Dados de teste criados com sucesso!')
"
```

### ✅ PASSO 4: Verificar Resultado
```bash
docker compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
from core.models import Setor, VinculoUsuarioSetor, Solicitacao, Participante

User = get_user_model()

print('=== RESUMO DOS DADOS ===')
print(f'Usuários: {User.objects.count()}')
print(f'Setores: {Setor.objects.count()}')
print(f'Vínculos: {VinculoUsuarioSetor.objects.count()}')
print(f'Solicitações: {Solicitacao.objects.count()}')
print(f'Participantes: {Participante.objects.count()}')

print('\\n=== USUÁRIOS SUPER ===')
from core.models import VinculoUsuarioSetor
supers = VinculoUsuarioSetor.objects.filter(papel='SUPER')
print(f'Usuários SUPER: {supers.count()}')
for v in supers:
    print(f'  - {v.usuario.email} -> {v.setor.nome}')
"
```

### ✅ PASSO 5: Testar Página
```bash
# Acesse: http://localhost:8000/disponibilidade/
# Verifique se os dados aparecem
```

## 🎯 RESULTADO ESPERADO

### ✅ Após Execução
- ✅ **Usuários criados** (5 usuários de teste)
- ✅ **Setores criados** (4 setores)
- ✅ **Vínculos criados** (5 vínculos usuário-setor-papel)
- ✅ **Usuário SUPER** (admin@super.com)
- ✅ **Página funcionando** com dados visíveis

### ✅ Validações
- ✅ **Usuários SUPER visíveis** na página
- ✅ **Filtros funcionando** corretamente
- ✅ **Interface responsiva** com dados
- ✅ **Sistema estável** e funcional

## 🚨 ALTERNATIVA - IMPORTAR DADOS REAIS

### ✅ Se quiser dados reais do Google Sheets:
```bash
# 1. Configurar credenciais do Google Sheets
# 2. Executar import_usuarios
docker compose exec web python manage.py import_usuarios data/usuarios.csv

# 3. Executar import_vinculos_setor
docker compose exec web python manage.py import_vinculos_setor data/vinculos_producao.csv

# 4. Executar import_eventos_abas
docker compose exec web python manage.py import_eventos_abas data/eventos.csv

# 5. Executar import_disponibilidades
docker compose exec web python manage.py import_disponibilidades data/disponibilidades.csv
```

## 🏆 CONCLUSÃO

### ✅ SOLUÇÃO PRONTA
Execute os comandos acima na ordem para resolver o problema dos dados faltando.

### 🚀 PRÓXIMOS PASSOS
1. **Execute os comandos** na ordem
2. **Verifique o resultado** na página
3. **Confirme que os dados aparecem**
4. **Teste as funcionalidades**

**O sistema está pronto - só precisamos dos dados!** 🎉

---

**Instruções Execução Rebuild - Sistema Aprender**  
*Solução para problema de dados faltando*
