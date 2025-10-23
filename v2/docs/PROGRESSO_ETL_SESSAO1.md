# Relatório de Progresso - Correção do ETL (Sessão 1)

**Data**: 2025-10-22
**Branch**: `fix/etl-complete-refactor`
**Commits**: `b08dbd7`, `6d6a56f`

---

## 📊 RESUMO EXECUTIVO

### ✅ O QUE FOI COMPLETADO (Fases 0-3)

**Fase 0: Preparação** ✅
- Branch criada: `fix/etl-complete-refactor`
- Estado inicial registrado: 2 usuários, 0 municípios, 0 projetos

**Fase 1: Correções Críticas** ✅ (Commit: `b08dbd7`)
- ✅ Bug CPF corrigido: `row[1] → row[2]` em `loaders.py:85`
- ✅ Parser Municípios: busca aba "FILTRO_PROD." coluna B
- ✅ Parser Projetos: busca aba "FILTRO_PROD." coluna E
- ✅ **Resultado**: 235 registros importados!
  - 117 Usuários (era 1/108) ✅
  - 87 Municípios (era 0) ✅
  - 31 Projetos (era 0) ✅

**Fase 2: Novos Modelos** ✅
- Verificado: todos os modelos necessários já existem
- Compra ✅, Deslocamento ✅, AcaoControle ✅, AcaoDAT ✅

**Fase 3: Novos Parsers** ✅ (Commit: `6d6a56f`)
- ✅ `parse_bloqueios.py` criado (108 linhas)
- ✅ `parse_deslocamentos.py` criado (115 linhas)
- ✅ `parse_acompanhamento.py` criado (242 linhas)
  - Suporta 5 abas: ACerta, Outros, Super, Brincando, Vidas
  - Trata aprovações da aba Super

---

## 🚧 O QUE FALTA (Fases 4-6)

### Fase 4: Atualizar Comando etl_all (3h estimadas)

**Arquivo**: `v2/backend/apps/dat_ingest/management/commands/etl_all.py`

**Tarefas pendentes**:

1. **Importar novos módulos**:
```python
from apps.dat_ingest.services.parse_bloqueios import parse_bloqueios
from apps.dat_ingest.services.parse_deslocamentos import parse_deslocamentos
from apps.dat_ingest.services.parse_acompanhamento import parse_todas_abas_acompanhamento
```

2. **Adicionar método `import_bloqueios()`**:
```python
def import_bloqueios(self, data_dir, dry_run, force):
    filepath = data_dir / "Cópia de Disponibilidade _ 2025.xlsx"
    bloqueios_data = parse_bloqueios(filepath)

    for b in bloqueios_data:
        formador = self.find_usuario(b['formador_nome'])
        if formador:
            AvailabilityBlock.objects.create(
                usuario=formador,
                tipo=b['tipo'],
                inicio=b['inicio'],
                fim=b['fim'],
                motivo=b['motivo']
            )
```

3. **Adicionar método `import_deslocamentos()`**:
```python
def import_deslocamentos(self, data_dir, dry_run, force):
    filepath = data_dir / "Cópia de Disponibilidade _ 2025.xlsx"
    deslocamentos_data = parse_deslocamentos(filepath)

    for d in deslocamentos_data:
        formador = self.find_usuario(d['formador_nome'])
        origem = self.find_municipio(d['origem_nome_uf'])
        destino = self.find_municipio(d['destino_nome_uf'])

        if formador and origem and destino:
            Deslocamento.objects.create(
                usuario=formador,
                origem=origem.nome,
                destino=destino.nome,
                start_date=d['saida'].date(),
                end_date=d['chegada'].date(),
                duracao_minutos=d['duracao_minutos'],
                meio_transporte=d['meio_transporte']
            )
```

4. **Adicionar método `import_solicitacoes()`** (MAIS COMPLEXO):
```python
def import_solicitacoes(self, data_dir, dry_run, force):
    filepath = data_dir / "Cópia de Acompanhamento de Agenda _ 2025.xlsx"
    solicitacoes_data = parse_todas_abas_acompanhamento(filepath)

    for s in solicitacoes_data:
        municipio = self.find_municipio(s['municipio_nome_uf'])
        projeto = self.find_projeto(s['projeto_nome'])
        coordenador = self.find_usuario(s['coordenador_nome'])

        if municipio and projeto:
            solicitacao = Solicitacao.objects.create(
                usuario=coordenador,
                municipio=municipio,
                projeto=projeto,
                tipo=s['tipo'],
                encontro=s['encontro'],
                segmento=s['segmento'],
                coordenador_acompanha=s['coordenador_acompanha'],
                coordenador=coordenador,
                inicio=s['inicio'],
                fim=s['fim'],
                status=s['status']
            )

            # Criar Participations para formadores
            for formador_nome in s['formadores']:
                formador = self.find_usuario(formador_nome)
                if formador:
                    Participation.objects.create(
                        solicitacao=solicitacao,
                        usuario=formador,
                        papel='formador'
                    )
```

5. **Atualizar método `handle()`**:
```python
def handle(self, *args, **options):
    # ... código existente ...

    # NOVAS CHAMADAS:
    self.stdout.write("\n📅 FASE 4: Solicitações")
    self.import_solicitacoes(data_dir, dry_run, force)

    self.stdout.write("\n🚫 FASE 5: Bloqueios e Deslocamentos")
    self.import_bloqueios(data_dir, dry_run, force)
    self.import_deslocamentos(data_dir, dry_run, force)
```

6. **Helpers de busca FK** (já existem, verificar):
```python
def find_municipio(self, nome_uf):
    if " - " in nome_uf:
        nome, uf = nome_uf.split(" - ", 1)
        return Municipio.objects.filter(
            nome__iexact=nome.strip(),
            uf__iexact=uf.strip()
        ).first()
    return Municipio.objects.filter(nome__iexact=nome_uf.strip()).first()

def find_projeto(self, nome):
    return Projeto.objects.filter(nome__iexact=nome.strip()).first()

def find_usuario(self, nome):
    partes = nome.split()
    if len(partes) >= 2:
        return Usuario.objects.filter(
            first_name__iexact=partes[0],
            last_name__icontains=" ".join(partes[1:])
        ).first()
    return Usuario.objects.filter(first_name__icontains=nome).first()
```

---

### Fase 5: Validação Completa (2h estimadas)

**Script de validação** (`v2/backend/scripts/validate_etl.py`):

```python
from apps.core.models import *

# Contagens esperadas
ESPERADO = {
    'usuarios': 117,
    'municipios': 87,
    'projetos': 31,
    'solicitacoes': (400, 450),  # ~420
    'participations': (1200, 1800),  # ~1500
    'bloqueios': (30, 70),  # ~50
    'deslocamentos': (50, 150),  # ~100
}

# Validar
for entidade, esperado in ESPERADO.items():
    count = eval(f"{entidade.capitalize()}.objects.count()")
    if isinstance(esperado, tuple):
        min_esp, max_esp = esperado
        status = "✅" if min_esp <= count <= max_esp else "❌"
        print(f"{status} {entidade}: {count} (esperado: {min_esp}-{max_esp})")
    else:
        status = "✅" if count == esperado else "❌"
        print(f"{status} {entidade}: {count} (esperado: {esperado})")
```

**Validações adicionais**:
- Integridade referencial (FK órfãos)
- Datas inválidas (fim < início)
- Solicitações sem formadores
- CPFs duplicados

---

### Fase 6: Testes e Deploy (2h estimadas)

1. **Executar testes**:
```bash
docker compose exec web python manage.py test apps.core.tests
docker compose exec web python manage.py test apps.dat_ingest.tests
```

2. **Validar frontend**:
```bash
curl http://localhost:8000/api/options/municipios/ | jq length  # Esperado: 87
curl http://localhost:8000/api/options/projetos/ | jq length   # Esperado: 31
curl http://localhost:8000/api/options/formadores/ | jq length # Esperado: 117
```

3. **Criar PR**:
```bash
gh pr create --title "fix(etl): Correção completa do ETL - importa ~2.500 registros" \
  --body "$(cat docs/PR_TEMPLATE.md)"
```

---

## 📁 ARQUIVOS MODIFICADOS/CRIADOS

### ✅ Modificados (Commit b08dbd7):
- `v2/backend/apps/dat_ingest/services/loaders.py` (+80 -47 linhas)
  - Corrige indexação de CPF
  - Corrige parsers de Municípios e Projetos

### ✅ Criados (Commit 6d6a56f):
- `v2/backend/apps/dat_ingest/services/parse_bloqueios.py` (108 linhas)
- `v2/backend/apps/dat_ingest/services/parse_deslocamentos.py` (115 linhas)
- `v2/backend/apps/dat_ingest/services/parse_acompanhamento.py` (242 linhas)

### 🚧 Pendentes de modificação:
- `v2/backend/apps/dat_ingest/management/commands/etl_all.py` (adicionar 3 importadores)

### 📚 Documentação criada:
- `v2/docs/relatorio_planilhas_google_sheets.md` (análise completa)
- `v2/docs/relatorio_planilhas_arquivos_locais.md` (diagnóstico técnico)
- `v2/docs/PLANO_CORRECAO_ETL.md` (plano parte 1)
- `v2/docs/PLANO_CORRECAO_ETL_PARTE2.md` (plano parte 2)
- `v2/docs/PROGRESSO_ETL_SESSAO1.md` (este arquivo)

---

## 🎯 PRÓXIMA SESSÃO - ROTEIRO

**Tempo estimado**: 3-4 horas

1. **Continuar de onde parou**:
```bash
git checkout fix/etl-complete-refactor
git pull
```

2. **Executar Fase 4** (~3h):
   - Editar `etl_all.py`
   - Adicionar 3 importadores
   - Testar com `--dry-run`
   - Executar importação real

3. **Executar Fase 5** (~1h):
   - Criar script de validação
   - Executar validações
   - Corrigir problemas encontrados

4. **Executar Fase 6** (~1h):
   - Executar testes
   - Validar frontend
   - Fazer commit final
   - Criar PR

---

## 📊 MÉTRICAS DE PROGRESSO

```
FASES CONCLUÍDAS: 3/6 (50%)
COMMITS REALIZADOS: 2
ARQUIVOS CRIADOS: 7
LINHAS DE CÓDIGO: ~1.000
REGISTROS IMPORTADOS: 235/2.500 (9%)
TOKENS USADOS: ~115k/200k (57%)
```

**Status Geral**: ✅ **NO PRAZO**

---

## 🔍 PROBLEMAS CONHECIDOS

1. **Nomes de formadores podem não bater**:
   - Planilha: "João Silva"
   - Usuários: "João da Silva"
   - Solução: implementar fuzzy matching ou normalização

2. **Municípios sem UF**:
   - Ex: "AMIGOS DO BEM" (não tem " - CE")
   - Solução: assumir UF vazio ou padrão

3. **Datas/horas com formatos variados**:
   - Algumas células vêm como float
   - Solução: try/except robusto nos parsers

4. **Coordenadores podem não existir em Usuários**:
   - Solução: permitir coordenador=null

---

## 💡 LIÇÕES APRENDIDAS

1. ✅ **Sempre inspecionar a planilha real antes de assumir estrutura**
2. ✅ **Docker no Windows precisa de rebuild para pegar alterações**
3. ✅ **Emojis em nomes de abas são válidos (ℹ️, 🟥, ☑️)**
4. ✅ **Staging tables são úteis para debugging**
5. ✅ **Commits pequenos e frequentes facilitam tracking**

---

## 🚀 COMO CONTINUAR

### Opção A: Executar Fase 4 manualmente

1. Editar `v2/backend/apps/dat_ingest/management/commands/etl_all.py`
2. Adicionar os 3 métodos de importação documentados acima
3. Executar: `docker compose exec web python manage.py etl_all --dry-run`
4. Se OK, executar: `docker compose exec web python manage.py etl_all`

### Opção B: Pedir ao Claude para continuar

Simplesmente dizer: "Continue a execução do plano a partir da Fase 4"

---

**Sessão finalizada em**: 2025-10-22
**Próxima sessão**: A combinar
**Responsável**: Claude Code + Operador
