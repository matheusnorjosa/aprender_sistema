# Backend

## Stack

- **Python 3.12** com PEP 695 (type hints modernos)
- **Django 5.1** com DRF
- **Celery** para tarefas assíncronas
- **Pyright** para type checking (strict mode)

## Estrutura Modular

O backend segue uma estrutura modular (PRs #213-#217):

```
apps/core/
├── models/           # Modelos Django
│   ├── usuario.py
│   ├── solicitacao.py
│   ├── availability.py
│   └── ...
├── serializers/      # DRF Serializers
├── views/            # DRF ViewSets
├── services/         # Lógica de negócio
│   └── gcal/         # Integração Google Calendar
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
    status = models.CharField()  # pendente, aprovado, reprovado
    gcal_status = models.CharField()  # NOT_PUBLISHED, PENDING, PUBLISHED, ERROR
```

### Usuario

Modelo customizado de usuário com RBAC:

```python
class Usuario(AbstractUser):
    # Grupos: Setor + Função
    # Setor: Superintendência, DAT, Vidas, etc.
    # Função: Formador, Coordenador, Gerente
```

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
  - escrita: pipelines/importações de controle e rotinas ETL
- `core_dat_compra`
  - leitura/escrita: DAT e Superintendência (CRUD operacional DAT)

### Contratos mínimos

- `/api/controle/compras/` retorna `quantidade` (não `valor`).
- `/api/dat/compras-materiais/` retorna contrato DAT (`quantidade`, `quantidade_utilizada`, `valor_unitario`, etc.).

## Services

A lógica de negócio está isolada em services:

- `availability_service.py`: Verificação de conflitos
- `gcal_sync_service.py`: Sincronização com Google Calendar
- `approval_service.py`: Fluxo de aprovação

## Type Hints

100% do código crítico está tipado (42 arquivos, ~18,000 linhas):

```python
def check_conflicts(
    usuario: Usuario,
    inicio: datetime,
    fim: datetime,
    municipio: Municipio
) -> AvailabilityResult:
    ...
```
