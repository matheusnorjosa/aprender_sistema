# Epic 1 — Labels capability-oriented

**Parent plan:** [master-plan.md](./master-plan.md)
**Dependências:** nenhuma (é o ponto de partida)
**Bloqueia:** Epic 2 (mensagens de erro usam os labels novos)
**Issues:** 1
**PR size total:** ~200 linhas
**Tempo estimado:** 2h de execução + 24h soak

---

## Por que este epic existe

A tela admin mostra "Operação DAT" para o administrador configurando permissões. Quando o departamento DAT mudar de nome/escopo, a label vira mentira semântica. O fix é: renomear 14 labels + 14 descriptions + 1 categoria para descreverem **o que a pessoa pode fazer**, não **quem faz hoje**.

Zero mudança de comportamento — codenames e grupos ficam intactos. É puro rename de texto user-visible.

## Escopo

### Dentro do escopo
- Reescrever `label` e `description` de 14 `FunctionalPermissionSeed` entries
- Renomear categoria `admin_dat` → `cadastros_administrativos` e `gerencia` → `supervisao`
- Migration data-only idempotente (usa `update_or_create` existente)
- Atualizar `CATEGORY_LABELS` no frontend
- Adicionar regression tests que proíbem nome de setor em labels/categorias
- Capturar baseline parity snapshot (referência para epics seguintes)

### Fora do escopo (epics posteriores)
- Renomear codenames (Epic 4)
- Renomear classes DRF (Epic 5)
- Eliminar hardcoded group checks (Epic 3)
- Introduzir `HasPerm` (Epic 2)

## Issues

- [ ] **Issue 1.1** — Rewrite labels + descriptions + categorias (single PR)

## Acceptance criteria

- [ ] Todos os 14 labels seguem forma `<Verbo infinitivo> <substantivo>` em português
- [ ] Nenhum label contém strings "DAT", "Controle", "Superintend", "Gerência", "Coordenação", "Formador", "Diretoria"
- [ ] Categoria `admin_dat` renomeada para `cadastros_administrativos`
- [ ] Categoria `gerencia` renomeada para `supervisao`
- [ ] Frontend `CATEGORY_LABELS` em `GruposPage.tsx` reflete mudança
- [ ] Migration `0073_rename_permission_labels.py` roda limpa em staging
- [ ] Testes `test_labels_are_capability_oriented` e `test_categories_are_capability_oriented` passam
- [ ] Baseline parity test salvo como snapshot JSON (ponto zero do refactor)
- [ ] Verificação manual em staging: abrir `Admin DAT → Grupos → Criar grupo`, confirmar labels novos

## Mapeamento old → new (referência canônica)

| codename (unchanged) | label atual | **label novo** | descrição nova | categoria nova |
|---|---|---|---|---|
| pode_aprovar_superintendencia | Aprovar/Reprovar (Superintendencia) | **Aprovar solicitações** | Aprovar ou reprovar solicitações pendentes | solicitacao |
| pode_aprovar_gerente_superintendencia | Aprovar em lote (Gerente da Superintendencia) | **Aprovar solicitações em lote** | Aprovar múltiplas solicitações em uma operação | solicitacao |
| pode_gerenciar_superintendencia_only | Operacao exclusiva da Superintendencia | **Executar operações restritas** | Operações destrutivas (exclusões críticas) | solicitacao |
| pode_criar_solicitacao_coord_dat | Criar solicitacao (Coordenacao/DAT) | **Criar solicitações de evento** | Submeter novas solicitações ao fluxo de aprovação | solicitacao |
| pode_importar_controle_super | Importacao (Controle/Superintendencia) | **Importar planilhas e dados** | Carregar dados em massa via CSV/XLSX | importacao |
| pode_operar_dat | Operacao DAT | **Administrar cadastros** | Gerenciar cadastros e configurações administrativas | cadastros_administrativos |
| pode_acessar_dashboard_compras | Dashboard de Compras | **Visualizar dashboard de compras** | Acesso ao painel de indicadores de compras | dashboard |
| pode_operar_dat_exclusivo | Operacao DAT (exclusiva) | **Administrar compras e materiais** | Operações administrativas restritas | cadastros_administrativos |
| pode_operar_controle_dat | Operacao compartilhada (Controle/DAT) | **Operar pré-agenda e relatórios** | Pré-agenda, relatórios gerenciais e publicações | operacao |
| pode_operar_controle | Operacao Controle | **Executar rotinas operacionais** | Imports, workflow diário, conferências | operacao |
| pode_operar_gerencia | Operacao Gerencial | **Exercer supervisão gerencial** | Atuação gerencial e supervisão de equipe | supervisao |
| pode_acessar_dashboard_overview | Dashboard Overview | **Visualizar dashboard geral** | Painel executivo de visão geral | dashboard |
| pode_acessar_map_metrics | Map Metrics | **Visualizar métricas geográficas** | Dashboards com distribuição por região | dashboard |
| pode_editar_como_owner_ou_privilegiado | Owner ou privilegiado | **Editar solicitações próprias ou privilegiadas** | Editar solicitações que você criou ou com privilégio | solicitacao |

## Fontes autoritativas

- [Nielsen Norman — Action-oriented labels](https://www.nngroup.com/articles/imperative-vs-declarative-labels/)
- [Microsoft Writing Style Guide — Action verbs](https://learn.microsoft.com/en-us/style-guide/)
- [GitLab — Permissions conventions: proibir `admin_`, `manage_`](https://docs.gitlab.com/development/permissions/conventions/)
