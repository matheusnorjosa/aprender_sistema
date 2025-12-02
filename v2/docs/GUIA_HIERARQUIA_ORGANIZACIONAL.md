# 📚 Guia de Uso: Hierarquia Organizacional - AS v2

**Data**: 2025-12-01
**Versão**: 1.0

---

## 🎯 O que foi implementado?

Este guia explica como usar as novas funcionalidades de hierarquia organizacional implementadas no AS v2:

1. **Modelo EquipeGerencia** - Rastreamento formal de hierarquia dentro de cada gerência
2. **Grupo "Apoio de Coordenação"** - Novo perfil de usuário com permissões específicas
3. **Correção de Projetos** - Todos os projetos agora estão corretamente vinculados às gerências

---

## 👥 Modelo EquipeGerencia

### O que é?

O modelo `EquipeGerencia` permite registrar formalmente a estrutura hierárquica dentro de cada gerência:

```
Gerente (1)
  └── Coordenador (N)
      └── Apoio de Coordenação (N)
          └── Formadores (N)
```

### Como usar?

#### 1. Acessar Django Admin

```
http://localhost:8002/admin/core/equipegerencia/
```

#### 2. Criar novo registro de equipe

**Campos obrigatórios**:
- **Gerencia**: Selecione a gerência (ex: GERENCIA 2, SUPERINTENDENCIA)
- **Usuario**: Selecione o usuário a ser vinculado
- **Papel**: Escolha um dos 4 papéis:
  - `GERENTE` - Gerente da gerência
  - `COORDENADOR` - Coordenador de projetos
  - `APOIO` - Apoio de Coordenação
  - `FORMADOR` - Formador/Instrutor

**Campos opcionais**:
- **Coordenador supervisor**: Obrigatório APENAS se papel = APOIO
  - Indica qual coordenador este apoio auxilia
- **Ativo**: Marcar como inativo para remover da equipe (sem deletar registro)

#### 3. Exemplo prático

**Cenário**: Registrar equipe da GERENCIA 2 (Vidas)

```python
# Via Django shell (python manage.py shell)
from apps.core.models import Gerencia, Usuario, EquipeGerencia

# 1. Buscar gerência
vidas = Gerencia.objects.get(nome='GERENCIA 2')

# 2. Registrar gerente
joao = Usuario.objects.get(username='joao.silva')
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=joao,
    papel='GERENTE',
)

# 3. Registrar coordenador
maria = Usuario.objects.get(username='maria.santos')
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=maria,
    papel='COORDENADOR',
)

# 4. Registrar apoio (auxilia Maria)
ana = Usuario.objects.get(username='ana.oliveira')
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=ana,
    papel='APOIO',
    coordenador_supervisor=maria,  # Ana auxilia Maria
)

# 5. Registrar formadores
for username in ['carlos.lima', 'luiza.costa', 'rafael.alves']:
    formador = Usuario.objects.get(username=username)
    EquipeGerencia.objects.create(
        gerencia=vidas,
        usuario=formador,
        papel='FORMADOR',
    )
```

#### 4. Constraints e Validações

**Unique Together**: Um usuário não pode ter o mesmo papel duas vezes na mesma gerência
```python
# ❌ ERRO: João já é GERENTE da GERENCIA 2
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=joao,
    papel='GERENTE',  # Duplicado!
)
```

**Check Constraint**: Apoio DEVE ter coordenador supervisor
```python
# ❌ ERRO: Apoio sem supervisor
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=ana,
    papel='APOIO',
    coordenador_supervisor=None,  # OBRIGATÓRIO para APOIO!
)
```

---

## 🔐 Grupo "Apoio de Coordenação"

### O que é?

Novo perfil de usuário com permissões intermediárias entre Coordenador e Formador.

### Permissões

O grupo "Apoio de Coordenação" tem **5 permissões**:

| Permissão | Descrição |
|-----------|-----------|
| `view_solicitacao` | Ver solicitações existentes |
| `add_solicitacao` | Criar novas solicitações (como coordenador) |
| `view_municipio` | Ver lista de municípios |
| `view_projeto` | Ver lista de projetos |
| `view_usuario` | Ver lista de usuários (para auxiliar coordenador) |

### Como atribuir?

#### 1. Via Django Admin

```
http://localhost:8002/admin/auth/user/
```

1. Abrir usuário
2. Seção "Permissões"
3. Campo "Grupos" → Adicionar "Apoio de Coordenação"
4. Salvar

#### 2. Via Django Shell

```python
from django.contrib.auth.models import Group
from apps.core.models import Usuario

# Buscar grupo
apoio_group = Group.objects.get(name='Apoio de Coordenação')

# Atribuir ao usuário
ana = Usuario.objects.get(username='ana.oliveira')
ana.groups.add(apoio_group)

# Verificar
print(ana.groups.all())  # [<Group: Apoio de Coordenação>]
```

### Acesso no Frontend

Usuários do grupo "Apoio de Coordenação" têm acesso a:

**Menu Lateral**:
- ✅ Página Inicial
- ✅ Grade Mensal
- ✅ Bloqueios
- ✅ Solicitações → Minhas Solicitações
- ✅ Solicitações → Nova Solicitação
- ✅ Ops → Deslocamentos

**Restrições**:
- ❌ Aprovações (apenas Superintendência)
- ❌ Pré-agenda (apenas Controle)
- ❌ Controle/DAT (apenas Controle)
- ❌ Admin DAT (apenas DAT/Superuser)

---

## 🏢 Gerências Individuais

### O que são?

Projetos onde **1 pessoa = Gerente + Coordenador + Formador** ao mesmo tempo.

**Exemplos**:
- A COR DA GENTE
- GESTÃO ESCOLAR
- ED FINANCEIRA
- TRÂNSITO LEGAL

### Como configurar?

**Solução implementada**: Atribuir **múltiplos grupos** ao mesmo usuário.

#### Exemplo

```python
from django.contrib.auth.models import Group
from apps.core.models import Usuario

# Buscar usuário
daniele = Usuario.objects.get(username='daniele.souza')

# Buscar grupos
gerencia = Group.objects.get(name='Gerência')
coordenador = Group.objects.get(name='Coordenador')
formador = Group.objects.get(name='Formador')

# Atribuir os 3 grupos
daniele.groups.add(gerencia, coordenador, formador)

# Verificar
print(daniele.groups.values_list('name', flat=True))
# ['Gerência', 'Coordenador', 'Formador']
```

**Resultado**: Daniele terá acesso a todas as funcionalidades dos 3 perfis.

---

## 📊 Correção de Projetos → Gerências

### O que foi corrigido?

Todos os projetos agora estão vinculados às gerências corretas.

### Situação Final

```
GERENCIA 2 (Vidas)        →  5 projetos
  - VIDA E CIÊNCIAS
  - VIDA E LINGUAGEM
  - VIDA E MATEMÁTICA
  - Avançando Juntos Matemática ← CORRIGIDO
  - Avançando Juntos Português ← CORRIGIDO

GERENCIA 3 (Fluir)        →  4 projetos
  - FLUIR DAS EMOÇÕES (+ 3 coleções)

GERENCIA 4 (ACerta)       →  7 projetos
  - ACerta ← CORRIGIDO (902 eventos!)
  - ACERTA MAT/PORT, ECS, LEIO ESCREVO E CALCULO, SUPERATIVAR x2

GERENCIA 5 (Brincando)    →  1 projeto
  - BRINCANDO E APRENDENDO

GERENCIA 6 (Sou da Paz)   →  1 projeto
  - SOU DA PAZ

GERENCIA INDIVIDUAL       →  3 projetos
  - A COR DA GENTE
  - GESTÃO ESCOLAR
  - ED FINANCEIRA
  - TRÂNSITO LEGAL

SUPERINTENDENCIA (Super)  → 11 projetos
  - Cataventos ← CORRIGIDO (16 eventos, fluxo SUPER)
  - CIRANDAR, LENDO E ESCREVENDO, NOVO LENDO, etc.
```

### Projetos Marcados como Teste

**Projetos ocultos** (`is_test=True`):
- Brincando (0 solicitações - não usado)
- Vidas (0 solicitações - não usado)

Estes projetos NÃO aparecem em produção, mas ficam no banco para histórico.

---

## 🛠️ Comandos Úteis

### Verificar Grupos

```bash
python manage.py shell

>>> from django.contrib.auth.models import Group
>>> Group.objects.all().values_list('name', flat=True)
['Superintendência', 'Coordenador', 'Apoio de Coordenação', 'Formador', 'Controle', 'DAT', 'Gerência']
```

### Listar Equipe de uma Gerência

```python
from apps.core.models import Gerencia, EquipeGerencia

vidas = Gerencia.objects.get(nome='GERENCIA 2')
equipe = EquipeGerencia.objects.filter(gerencia=vidas, ativo=True)

for membro in equipe:
    print(f"{membro.usuario.name} - {membro.get_papel_display()}")
```

### Listar Gerências de um Usuário

```python
from apps.core.models import Usuario, EquipeGerencia

maria = Usuario.objects.get(username='maria.santos')
equipes = EquipeGerencia.objects.filter(usuario=maria, ativo=True)

for eq in equipes:
    print(f"{eq.gerencia.nome} - {eq.get_papel_display()}")
```

### Verificar Permissões de um Usuário

```python
from apps.core.models import Usuario

ana = Usuario.objects.get(username='ana.oliveira')

# Grupos
print("Grupos:", ana.groups.values_list('name', flat=True))

# Permissões (via grupos)
perms = ana.get_group_permissions()
for perm in sorted(perms):
    print(f"  - {perm}")
```

---

## 📝 Próximos Passos

### Operacional

1. **Popular dados de EquipeGerencia**:
   - Atribuir gerentes às 7 gerências
   - Vincular coordenadores
   - Registrar apoios com supervisores
   - Vincular formadores

2. **Atribuir grupo "Apoio de Coordenação"**:
   - Identificar usuários que são apoios
   - Atribuir grupo via Admin
   - Testar acesso no frontend

3. **Configurar Gerências Individuais**:
   - Atribuir múltiplos grupos aos usuários de projetos individuais

### Técnica (Futuro)

4. **Criar endpoints API**:
   - `/api/gerencias/{id}/equipe/` - Listar equipe
   - `/api/usuarios/{id}/equipes/` - Listar gerências do usuário

5. **Melhorias no Admin**:
   - Inline de EquipeGerencia na página de Gerencia
   - Filtros e ações customizadas

6. **Dashboards**:
   - Organograma visual por gerência
   - Relatórios de hierarquia

---

## 🆘 Troubleshooting

### Erro: "apoio_requires_supervisor"

**Problema**: Tentando criar Apoio sem coordenador supervisor

**Solução**:
```python
# ❌ Errado
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=ana,
    papel='APOIO',
    # Falta coordenador_supervisor!
)

# ✅ Correto
EquipeGerencia.objects.create(
    gerencia=vidas,
    usuario=ana,
    papel='APOIO',
    coordenador_supervisor=maria,  # ← Obrigatório
)
```

### Erro: "UNIQUE constraint failed"

**Problema**: Tentando criar registro duplicado (mesma gerência + usuário + papel)

**Solução**: Verificar se registro já existe
```python
from apps.core.models import EquipeGerencia

# Verificar antes de criar
exists = EquipeGerencia.objects.filter(
    gerencia=vidas,
    usuario=joao,
    papel='GERENTE'
).exists()

if not exists:
    EquipeGerencia.objects.create(...)
```

### Grupo "Apoio de Coordenação" não existe

**Problema**: Grupo não foi criado durante migrations

**Solução**: Rodar seed_rbac
```bash
python manage.py seed_rbac --verbose
```

---

## 📚 Documentação Relacionada

- [PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md](PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md) - Análise completa e decisões
- [RBAC_COMPLETO.md](RBAC_COMPLETO.md) - Guia completo de permissões
- [MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md](MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md) - Estrutura organizacional

---

**Última atualização**: 2025-12-01 18:45 BRT
**Versão**: 1.0
**Autor**: Claude Code + Datsuke
