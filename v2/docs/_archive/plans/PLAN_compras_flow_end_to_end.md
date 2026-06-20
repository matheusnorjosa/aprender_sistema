# Plano: Fluxo Compras End-to-End

**Data**: 2026-02-27
**Épico**: Compras → Solicitação → Google Calendar (entrega funcional)
**Referência de análise**: [ANALISE_scripts_google_sheets.md](../analysis/ANALISE_scripts_google_sheets.md)
**Status**: 🆕 Planejamento

---

## Objetivo

Entregar o fluxo completo e confiável:

```
Compra registrada (ETL ou UI)
        ↓
Município aparece como elegível
        ↓
Solicitação de evento criada (wizard)
        ↓
Aprovação (PA-01~07)
        ↓
Google Calendar publicado
```

---

## Contexto Crítico

> O ETL das planilhas é uma **migração única** (dados históricos de 2026).
> Após go-live, toda alimentação será feita diretamente no sistema via UI.
> **As validações DEVEM estar na camada service/serializer** — não só no ETL.

---

## Issues e Ordem de Execução

```
Issue #A (normalizar projetos)     ← desbloqueia #B e #C
Issue #B (ETL compras end-to-end)  ← desbloqueia #D
Issue #C (AcaoDAT tipos)           ← independente
Issue #D (municípios elegíveis)    ← desbloqueia #E
Issue #E (wizard frontend)         ← desbloqueia #F
Issue #F (relatório pendências)    ← fim do fluxo
```

---

## Issue #A — Normalizar nomes de projeto nos imports

**Tipo**: bug fix
**Prioridade**: 🔴 Crítica (desbloqueia B e C)
**Arquivos afetados**:
- `apps/core/services/controle_imports.py` (import_compras_from_file)
- `apps/core/services/colecoes_import.py`
- `apps/core/services/produtos_import.py`
- `apps/dat_ingest/management/commands/etl_import_dat_cadastros.py`

### Problema

Os scripts das planilhas (`LimparNomeProjeto.js`) removem o prefixo `"2026 "` dos nomes de projeto antes de salvar. Se o CSV exportado vier com esse prefixo, o lookup por FK em `Projeto` falha silenciosamente — o registro é descartado sem erro explícito.

**Exemplo**:
```
CSV: "2026 Novo Lendo"  →  Projeto.objects.get(nome="2026 Novo Lendo")  →  DoesNotExist
```

### Solução

Criar helper de normalização reutilizável e aplicar em todos os imports:

```python
# apps/core/services/_utils.py

_YEAR_PREFIXES = re.compile(r"^\d{4}\s+")
_NIVEL_MAP = {
    "Fluir das Emoções Nível 1": "Fluir das Emoções N1",
    "Fluir das Emoções Nível 2": "Fluir das Emoções N2",
    "Fluir das Emoções Nível 3": "Fluir das Emoções N3",
}

def normalize_project_name(raw: str) -> str:
    """Remove year prefix and normalize project name variants."""
    name = _YEAR_PREFIXES.sub("", raw.strip())
    return _NIVEL_MAP.get(name, name)

def lookup_projeto(nome_raw: str) -> Projeto | None:
    """Case-insensitive project lookup with name normalization."""
    nome = normalize_project_name(nome_raw)
    return Projeto.objects.filter(nome__iexact=nome).first()
```

### Testes

```python
# tests/test_utils_normalize.py
def test_strip_year_prefix():
    assert normalize_project_name("2026 Novo Lendo") == "Novo Lendo"
    assert normalize_project_name("2026 Fluir das Emoções Nível 1") == "Fluir das Emoções N1"
    assert normalize_project_name("ACerta") == "ACerta"  # sem prefixo, não muda

def test_lookup_projeto_case_insensitive(db):
    Projeto.objects.create(nome="Novo Lendo")
    assert lookup_projeto("2026 NOVO LENDO") is not None
```

---

## Issue #B — ETL Compras end-to-end (migração única)

**Tipo**: task (ETL + validação)
**Prioridade**: 🔴 Crítica
**Arquivos afetados**:
- `apps/core/services/controle_imports.py`
- `apps/dat_ingest/management/commands/etl_import_compras.py` (criar se não existe)
- `apps/core/serializers/compra.py`

### Problema

O CSV `COMPRAS_pronto.csv` (1.028 linhas) precisa ser importado de forma confiável e idempotente. O `import_compras_from_file` existe mas:
1. Não normaliza nomes de projeto (depende da Issue #A)
2. Não existe comando `etl_import_compras` standalone para dry-run seguro

### Estrutura do CSV

```
CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções
396,MIUDEZAS E DESCOBERTAS - BEBÊS - KIT ALUNO.,13,AMIGOS DO BEM,PE,2026-01-26,
```

### Mapeamento de Campos

| Coluna CSV | Campo no Modelo | Observação |
|-----------|-----------------|------------|
| CÓD | `Compra.codigo` (ou lookup em `Produto.codigo`) | Verificar se é FK ou código legado |
| Produto | `Compra.produto` (FK via nome) | Busca por nome normalizado |
| Quant. | `Compra.quantidade` | Integer |
| Município | `Compra.municipio` (FK via nome) | Case-insensitive |
| UF | auxiliar para resolver homônimos | Ex: "São Paulo - SP" vs "São Paulo - MG" |
| Data | `Compra.data` | Formato YYYY-MM-DD |
| Uso das coleções | `Compra.uso` | Texto livre |

### Solução

**Fase 1 — dry-run** (não grava nada):
```bash
docker exec aprender_v2-web-1 python manage.py etl_import_compras \
  --file=/app/data/csv-import/2026/PRONTOS_PARA_IMPORTAR/COMPRAS_pronto.csv \
  --dry-run
```

**Fase 2 — apply** (após validação do relatório):
```bash
docker exec aprender_v2-web-1 python manage.py etl_import_compras \
  --file=/app/data/csv-import/2026/PRONTOS_PARA_IMPORTAR/COMPRAS_pronto.csv
```

### Relatório esperado

```
[COMPRAS ETL] Processing 1028 rows...
  Created:   847
  Updated:     0
  Unchanged:   0
  Skipped:     0
PENDÊNCIAS:
  municipio_missing: 3 linhas
    - linha 45: "MUNICIPIO X" não encontrado
  produto_missing: 12 linhas
    - linha 89: CÓD 999 não encontrado
```

### Validação no Serializer (para inserção via UI)

```python
# apps/core/serializers/compra.py
class CompraSerializer(serializers.ModelSerializer):
    def validate(self, data):
        # Municipio deve existir
        if not Municipio.objects.filter(id=data['municipio'].id).exists():
            raise ValidationError("Município não encontrado.")
        # Produto deve existir (se informado)
        if data.get('produto') and not Produto.objects.filter(id=data['produto'].id, ativo=True).exists():
            raise ValidationError("Produto não ativo.")
        return data
```

### Testes

```python
# tests/test_import_compras.py (adicionar)
def test_normaliza_nome_projeto_com_prefixo_ano():
    """Compra com projeto '2026 Novo Lendo' deve ser resolvida corretamente."""

def test_resolve_municipio_por_nome_e_uf():
    """UF deve ser usado como desambiguador quando há municípios homônimos."""

def test_dry_run_nao_grava_no_banco():
    """dry_run=True não deve persistir nenhum registro."""

def test_idempotencia_segunda_importacao():
    """Segunda execução não deve criar duplicatas (external_hash)."""
```

---

## Issue #C — Validar e padronizar tipos de AcaoDAT

**Tipo**: bug fix + documentação
**Prioridade**: 🟡 Média
**Arquivos afetados**:
- `apps/core/models/workflow.py` (campo `tipo_acao`)
- `apps/dat_ingest/management/commands/etl_import_dat_cadastros.py`

### Problema

O campo `AcaoDAT.tipo_acao` é `CharField(max_length=120)` sem choices definidos. A planilha usa 6 valores específicos. Sem choices no modelo, qualquer string é aceita — incluindo variações de grafia que fragmentam os dados.

### Tipos definidos nas planilhas

```python
class TipoAcaoDAT(models.TextChoices):
    CRIACAO_CURSO       = "FORMAR - Criação de Curso",       "FORMAR - Criação de Curso"
    CRIACAO_CHAVES      = "FORMAR - Criação de Chaves",      "FORMAR - Criação de Chaves"
    CRIACAO_INSTRUCOES  = "FORMAR - Criação de Instruções",  "FORMAR - Criação de Instruções"
    CHAVES_ENVIADAS     = "FORMAR - Chaves enviadas",        "FORMAR - Chaves enviadas"
    CODIGOS_ENVIADOS    = "Códigos enviados",                "Códigos enviados"
    REUNIAO_DAT         = "Reunião DAT",                     "Reunião DAT"
```

### Solução

1. Adicionar `TipoAcaoDAT` choices ao model
2. Criar migration
3. ETL deve mapear variações de grafia para o valor canônico
4. Serializer rejeita valores fora dos choices

### Testes

```python
def test_tipo_acao_invalido_rejeitado():
    """AcaoDAT com tipo_acao fora dos choices deve levantar ValidationError."""

def test_etl_normaliza_variacao_de_grafia():
    """ETL deve mapear 'FORMAR-Criação de Curso' → 'FORMAR - Criação de Curso'."""
```

---

## Issue #D — Backend: municípios elegíveis filtrados por compras

**Tipo**: feature
**Prioridade**: 🔴 Alta (regra de negócio central)
**Arquivos afetados**:
- `apps/core/views/options.py` (ou onde fica `municipios_options`)
- `apps/core/serializers/solicitacao.py`
- `apps/core/tests/test_solicitacao.py`

### Problema

Hoje qualquer município pode ser usado em uma solicitação, mesmo sem ter registrado compra. A planilha só mostra municípios com compras — esta é uma regra de negócio explícita.

### Solução

**1. Endpoint `options/municipios/` aceita parâmetro `?com_compra=true`**:

```python
# apps/core/views/options.py
class MunicipioOptionsView(APIView):
    def get(self, request):
        qs = Municipio.objects.filter(ativo=True).order_by("nome")
        if request.query_params.get("com_compra") == "true":
            qs = qs.filter(compras__isnull=False).distinct()
        serializer = MunicipioOptionSerializer(qs, many=True)
        return Response(serializer.data)
```

**2. Serializer de Solicitação valida município**:

```python
# apps/core/serializers/solicitacao.py
def validate_municipio(self, value):
    if not Compra.objects.filter(municipio=value).exists():
        raise ValidationError(
            f"O município '{value.nome}' não possui compras registradas. "
            "Registre a compra antes de criar uma solicitação."
        )
    return value
```

> **Nota**: A validação no serializer vale tanto para a API quanto para qualquer futura importação via ETL.

### Testes (PA-01~07 equivalente para esta regra)

```python
# tests/test_solicitacao_municipio_eligibility.py

def test_municipio_sem_compra_rejeitado():
    """Criar solicitação para município sem compra deve retornar 400."""

def test_municipio_com_compra_aceito():
    """Criar solicitação para município com compra deve retornar 201."""

def test_options_municipios_sem_filtro_retorna_todos():
    """GET /options/municipios/ sem parâmetro retorna todos os ativos."""

def test_options_municipios_com_compra_filtra():
    """GET /options/municipios/?com_compra=true retorna só municípios com compra."""

def test_superuser_nao_e_bloqueado_por_compra():
    """Superuser pode criar solicitação para qualquer município (bypass de validação)."""
```

---

## Issue #E — Frontend: wizard filtra municípios com compra

**Tipo**: feature (frontend)
**Prioridade**: 🔴 Alta
**Arquivos afetados**:
- `src/pages/Solicitacoes/SolicitacaoWizard.tsx` (ou similar)
- `src/api/core.ts` ou `src/api/options.ts`

### Problema

O Wizard de Solicitação não filtra municípios por compras. O usuário pode selecionar um município sem compra e a API retornará 400 (após Issue #D).

### Solução

**1. Atualizar chamada ao endpoint**:

```typescript
// src/api/options.ts
export const getMunicipiosComCompra = () =>
  api.get<MunicipioOption[]>('/options/municipios/', { params: { com_compra: 'true' } });
```

**2. No step do Wizard onde o município é selecionado**:

```typescript
// Substituir:
const { data: municipios } = useQuery(['municipios'], getMunicipios);
// Por:
const { data: municipios } = useQuery(['municipios-com-compra'], getMunicipiosComCompra);
```

**3. Adicionar tooltip explicativo**:
```
"Apenas municípios com compras registradas podem solicitar eventos."
```

**4. Para superuser**: mostrar todos os municípios (usar endpoint sem filtro).

### Testes

```typescript
// SolicitacaoWizard.test.tsx
it('carrega apenas municípios com compra para usuário normal')
it('carrega todos os municípios para superuser')
it('exibe tooltip explicativo no campo de município')
```

---

## Issue #F — Relatório: municípios com compra sem evento agendado

**Tipo**: feature (relatório/auditoria)
**Prioridade**: 🟡 Média
**Arquivos afetados**:
- `apps/core/views/metrics/` (novo endpoint)
- `src/pages/Dashboards/ComprasDashboardPage.tsx` (adicionar seção)

### Problema

Não existe visibilidade de quais municípios compraram mas ainda não têm evento solicitado. Este é o principal gap de gestão — substitui o papel da Planilha de Acompanhamento de Agenda.

### Solução

**Backend — novo endpoint**:

```
GET /api/dat/compras-materiais/pendencias/
```

**Lógica**:
```python
@action(detail=False, methods=["get"])
def pendencias(self, request):
    """Municípios com compra mas sem solicitação aprovada ou em andamento."""
    municipios_com_compra = (
        Compra.objects.values("municipio_id", "municipio__nome", "municipio__uf", "projeto_id", "projeto__nome")
        .distinct()
    )
    municipios_com_evento = (
        Solicitacao.objects.exclude(status="cancelado")
        .values("municipio_id", "projeto_id")
        .distinct()
    )
    # Diferença: tem compra mas não tem evento
    pendentes = municipios_com_compra.exclude(
        municipio_id__in=municipios_com_evento.values("municipio_id")
    )
    return Response({"pendentes": list(pendentes), "total": pendentes.count()})
```

**Frontend — nova seção no ComprasDashboardPage**:

```
┌─────────────────────────────────────────────┐
│ Municípios Pendentes de Agendamento          │
│                                             │
│  94 compraram · 67 agendados · 27 pendentes │
│                                             │
│  [Tabela: Município | UF | Projeto | Data]  │
└─────────────────────────────────────────────┘
```

### Testes

```python
def test_pendencias_retorna_municipios_sem_evento():
def test_pendencias_exclui_municipios_com_evento_aprovado():
def test_pendencias_conta_por_projeto():
```

---

## Cronograma Sugerido

| Fase | Issues | Entregável | Ordem |
|------|--------|-----------|-------|
| 1 — Dados confiáveis | #A + #B + #C | COMPRAS importadas sem pendências | 1º |
| 2 — Regra de negócio | #D | Validação de eligibilidade no backend | 2º |
| 3 — UX | #E | Wizard correto no frontend | 3º |
| 4 — Visibilidade | #F | Dashboard de pendências | 4º |

---

## Checklist de Go-Live (após todas as issues)

```
[ ] ETL dry-run com 0 pendências críticas
[ ] ETL apply — 1.028 compras importadas
[ ] Teste: município sem compra rejeitado via API (400)
[ ] Teste: solicitação criada para município com compra (201)
[ ] Teste: aprovação → GCal publicado
[ ] Dashboard pendências mostra lista correta
[ ] Smoke test E2E: compra → solicitação → aprovação → GCal
```

---

## Referências

- Análise dos scripts: [ANALISE_scripts_google_sheets.md](../analysis/ANALISE_scripts_google_sheets.md)
- Regras de aprovação: `CLAUDE.md` → CP-02 (PA-01 a PA-07)
- Regras de disponibilidade: [GUIDE_AVAILABILITY.md](../GUIDE_AVAILABILITY.md)
- CSV de compras: `v2/data/csv-import/2026/PRONTOS_PARA_IMPORTAR/COMPRAS_pronto.csv`

