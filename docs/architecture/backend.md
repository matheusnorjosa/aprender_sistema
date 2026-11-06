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
├── api_schemas.py    # Schemas drf-spectacular (arquivo, não diretório)
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

A lista de compras é `core_dat_compra` (`DATCompra`, endpoint `/api/dat/compras-materiais/`): a regra da
compra (`services/compra_elegibilidade.py`), as pendências, o dashboard e o Mapa leem só ela.

- leitura/escrita: DAT e Controle, pelo pacote do perfil da gerência (`CanViewComprasStats` no `DATCompraViewSet`, `views/dat_module.py`); excluir exige `execute_restricted_operations` (DAT). A Superintendência não tem acesso. Gates por endpoint: tabela do `v2/docs/API_REFERENCE.md`.
- contrato: `quantidade`, `quantidade_utilizada`, `valor_unitario` etc.

A lista antiga `core_compra` (`Compra`) saiu de uso em 06/11/2026 (G29, etapa 1): nenhuma rota a lê nem
a grava (`/api/compras/`, `/api/controle/compras/` e `/api/controle/import-compras/` respondem 404) e o
Django admin só a consulta. A tabela fica até a etapa 2, depois de backup e OK do dono. Ver
`v2/docs/specs/backend/imports.spec.md`.

## Services

A lógica de negócio está isolada em `apps/core/services/` (~50 módulos). Os principais:

- `availability_service.py`: verificação de conflitos (RD-01..RD-08)
- `solicitacao_approval.py` / `solicitacao_publish.py`: fluxo de aprovação e publicação
- `gcal_sync_service.py` + `gcal_*_client.py`: integração Google Calendar (fake/google/oauth)
- `export_contract_importer.py` e os `*_import.py`: pipeline de importação
- `monthly_grid_service.py`: grade mensal de disponibilidade

## Type Hints

Pyright roda em **modo strict** sobre `apps/core`, `apps/dev_tools` e `config`
(`v2/backend/pyproject.toml`, `[tool.pyright]`), excluindo `migrations`. É um check
bloqueante de PR: `[required] backend typecheck (pyright)`.

Exemplo real (`check_conflicts` em `apps/core/services/availability_service.py`) — note os
argumentos **keyword-only** e o retorno `CheckResult`:

```python
def check_conflicts(
    *, usuario: Usuario, inicio: datetime, fim: datetime, municipio: Municipio | None = None
) -> CheckResult:
    ...
```

`check_conflicts` tem cache de 5 min e é **consultivo**; enforcement usa
`check_conflicts_uncached` dentro da transação.
