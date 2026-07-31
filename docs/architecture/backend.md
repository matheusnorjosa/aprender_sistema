# Backend

## Stack

- **Python 3.12** com PEP 695 (type hints modernos)
- **Django 5.2 LTS** com DRF
- **Celery** para tarefas assíncronas
- **Pyright** para type checking (strict mode)

## Estrutura Modular

O backend segue uma estrutura modular (PRs #213-#217):

```
apps/core/
├── models/           # Modelos Django
│   ├── usuario.py
│   ├── solicitacao.py
│   ├── agenda.py     # AvailabilityBlock (disponibilidade)
│   └── ...
├── serializers/      # DRF Serializers
├── views/            # DRF ViewSets
├── views_gcal/       # Endpoints da integração GCal
├── services/         # Lógica de negócio
│   ├── gcal/         # Integração Google Calendar
│   └── oauth/        # Fluxo OAuth Google
├── rbac/             # Capabilities, policies, matrix.py (SSOT executável)
├── imports/          # Pipeline export-contract (hashing, normalização)
├── schemas/          # Schemas drf-spectacular
├── management/       # Management commands (import_export_contract, …)
└── tests/            # Testes unitários
```

## Modelos Principais

### Solicitacao

Representa uma solicitação de evento:

```python
class Solicitacao(models.Model):
    projeto = models.ForeignKey(Projeto)
    municipio = models.ForeignKey(Municipio)
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    status = models.CharField()  # Status: pendente, aprovado, reprovado
    gcal_status = models.CharField()  # GCalStatus: NONE, PENDING, PUBLISHED, ERROR
```

Os valores vêm de `TextChoices` aninhadas (`Solicitacao.Status`, `Solicitacao.GCalStatus`)
— use as constantes, não literais. O "não publicado" é `NONE`
(`apps/core/models/solicitacao.py:46-52`).

### Usuario

Modelo customizado de usuário com RBAC:

```python
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11, unique=True, db_index=True)  # 11 dígitos
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    # Grupos: Setor + Função (SSOT em apps/core/constants.py)
    # 13 setores: Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz,
    #             DAT, Controle, Diretoria, Comercial, Relacionamento,
    #             Logística Viagens, Logística Galpão
    # 5 funções:  Formador, Coordenador, Apoio de Coordenação, Gerente,
    #             Assistente Administrativo
```

A autorização usa `permission_classes = [HasPerm("codename")]`; checagem direta de
grupos (`user.groups.filter(name=...)`) é **banida** pelo `scripts/rbac_lint.py`
(check `[required] backend rbac-lint`). Ver [RBAC e Permissões](../guides/rbac.md).

## Fronteira de Domínio de Compras

O sistema possui dois domínios distintos de compras e eles não devem ser confundidos:

- `core_compra` (`core_compra` table, endpoint `/api/controle/compras/`)
- `core_dat_compra` (`core_dat_compra` table, endpoint `/api/dat/compras-materiais/`)

### Política oficial (fonte de verdade)

- Elegibilidade de solicitação (município + projeto) usa **somente** `core_compra`.
- Operação DAT de materiais/estoque usa **somente** `core_dat_compra`.
- Dashboard de compras DAT usa `core_dat_compra`.
- Importação de compras de controle (planilha de compras que libera solicitação) alimenta `core_compra`.

### Leitura e escrita por caso de uso

- `core_compra`
  - leitura: Controle e Superintendência
  - escrita: pipelines/importações de controle (`services/controle_imports.py`)
- `core_dat_compra`
  - leitura/escrita: DAT e Superintendência (CRUD operacional DAT)

### Contratos mínimos

- `/api/controle/compras/` retorna `quantidade` (não `valor`).
- `/api/dat/compras-materiais/` retorna contrato DAT (`quantidade`, `quantidade_utilizada`, `valor_unitario`, etc.).

## Services

A lógica de negócio está isolada em `apps/core/services/` (~40 módulos). Os principais:

- `availability_service.py`: verificação de conflitos (RD-01..RD-08)
- `solicitacao_approval.py` / `solicitacao_publish.py`: fluxo de aprovação e publicação
- `gcal_sync_service.py` + `gcal_*_client.py`: integração Google Calendar (fake/google/oauth)
- `export_contract_importer.py` e os `*_import.py`: pipeline de importação
- `monthly_grid_service.py`: grade mensal de disponibilidade
- `controle_imports.py`: importação de compras de controle (`core_compra`)

## Type Hints

Pyright roda em **modo strict** sobre `apps/core`, `apps/dev_tools` e `config`
(`v2/backend/pyproject.toml`, `[tool.pyright]`), excluindo `migrations`. É um check
bloqueante de PR: `[required] backend typecheck (pyright)`.

Exemplo real (`apps/core/services/availability_service.py:327-329`) — note os
argumentos **keyword-only** e o retorno `CheckResult`:

```python
def check_conflicts(
    *, usuario: Usuario, inicio: datetime, fim: datetime, municipio: Municipio | None = None
) -> CheckResult:
    ...
```

`check_conflicts` tem cache de 5 min e é **consultivo**; enforcement usa
`check_conflicts_uncached` dentro da transação.
