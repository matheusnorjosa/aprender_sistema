# ADR-019 — Métricas: composition OR de 3 vias em vez de policy unificada

| Field        | Value                                                                                  |
| ------------ | -------------------------------------------------------------------------------------- |
| **Status**   | Accepted                                                                               |
| **Date**     | 2026-04-27                                                                             |
| **Deciders** | Backend (Aprender Sistema) — RBAC Onda 2 A3 / Lote 4.2.b2                               |
| **Issue**    | [#1268](https://github.com/matheusnorjosa/aprender_sistema/issues/1268) — RBAC C3 metrics semantic review |
| **Related**  | [RBAC_NAMING.md](../RBAC_NAMING.md), [rbac_authorization_matrix.md](../rbac_authorization_matrix.md) |

## Contexto

Três endpoints de métricas de gestão precisam ser acessíveis a **três setores por
motivos legítimos distintos**:

| Capability                | Setor       | Motivo legítimo   |
| ------------------------- | ----------- | ----------------- |
| `run_daily_operations`    | Controle    | operar            |
| `supervise_operations`    | Diretoria   | supervisionar     |
| `manage_admin_registries` | DAT         | validar / suportar|

Os endpoints são:

- `apps/core/views/metrics/dashboard_metrics.py::productivity_metrics`
- `apps/core/views/metrics/dashboard_metrics.py::quality_metrics`
- `apps/core/views/metrics/formador_metrics.py::formadores_metrics`

Na Onda 2 A3 (β, 2026-04-27) adicionou-se `manage_admin_registries` (DAT como ator
transversal) à composição já existente. A pergunta de revisão (C3, #1268): **consolidar
os três `HasPerm(...) | ...` numa policy única?**

## Decisão

**Manter a composition OR ad-hoc** em cada endpoint:

```python
[HasPerm("run_daily_operations") | HasPerm("supervise_operations") | HasPerm("manage_admin_registries")]
```

**Não** consolidar numa policy única. Os três endpoints protegem **objetos
semanticamente diferentes** (produtividade de pessoas × qualidade de fluxo × registros
administrativos); uma policy única (ex.: `can_view_management_metrics`) daria a impressão
de um único intent de autorização quando na verdade são três motivos legítimos que hoje
coincidem no conjunto de capabilities, mas podem divergir. Ver o critério de "match de
intent vs. capability" em [RBAC_NAMING.md](../RBAC_NAMING.md).

Precedente: **Lote 4.2.b2** — composition OR é tática e aceitável para ≤ 3 capabilities
quando os objetos protegidos são distintos.

## Consequências

- **Aceito**: os três endpoints repetem o predicado OR. É duplicação de *forma*, não de
  *intent* — não deve ser "DRY-forçado" numa policy.
- **Guard-rail**: uma futura consolidação em policy única exige revisão semântica
  (confirmar que os três objetos passaram a compartilhar o mesmo intent). Sem isso,
  conflaria intenções distintas.
- Os comentários inline nos três endpoints referenciam este ADR.
