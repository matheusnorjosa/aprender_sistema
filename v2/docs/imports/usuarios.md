# Importação: Usuários

Status: PR 1 — contrato fechado, **backend já implementado** (revisto 2026-05-05)
Versão: 2026-05-05 v0.2
Template: [templates/usuarios.template.csv](./templates/usuarios.template.csv)

> ⚠️ **Atualização v0.2**: a v0.1 tratava o service como "futuro PR 6". Na verdade `apps/core/services/usuarios_import.py` já existe e funciona com dry-run + idempotência por CPF + savepoint-per-row. Esta versão alinha o doc ao código real.

---

## 1. Objetivo

Importar/atualizar usuários do sistema (`apps.core.models.usuario.Usuario`) a partir da aba "Usuários" da planilha `sheets.banco`. Cobre:

- Criação de usuário novo (se CPF/email não existir).
- Atualização de dados não-chave (telefone, cargo) em usuário existente.
- Atribuição **automática de Setor** (grupo Django) conforme coluna `Gerência`.
- Atribuição **automática de Função** (grupo Django) conforme coluna `Cargo`, **com whitelist**.

Não cobre (gate manual obrigatório):
- Atribuição de função `Gerente` ou `Superintendência`.
- `is_superuser=True`.
- Atribuição de capabilities individuais (D17 — admin-driven).

---

## 2. Dados de origem esperados

Aba `Usuários` da planilha `sheets.banco`.

| Coluna planilha | Descrição |
|---|---|
| `Nome` | Nome curto (ex: "Maria Silva") |
| `Nome Completo` | Nome completo (ex: "Maria Silva de Souza") |
| `CPF` | 11 dígitos (com ou sem máscara) |
| `Telefone` | Telefone (com ou sem máscara, com ou sem DDD) |
| `Email` | Email institucional ou pessoal |
| `Cargo` | Função operacional (ex: "Formadora", "Coordenadora", "Assistente") |
| `Gerência` | Setor de trabalho (ex: "Superintendência", "Vidas", "DAT") |

---

## 3. Colunas obrigatórias

| Coluna CSV | Validação |
|---|---|
| `cpf` | 11 dígitos após normalização; dígito verificador válido |
| `email` | RFC 5322 simples; unique no banco |
| `nome_completo` | mínimo 2 palavras |
| `gerencia` | deve mapear para um `Setor` em `SETOR_GROUPS` |

---

## 4. Colunas opcionais

| Coluna CSV | Comportamento se vazio |
|---|---|
| `nome` | Derivar do `nome_completo` (primeiro nome) |
| `telefone` | Salvar string vazia; usuário consegue editar depois |
| `cargo` | Salvar string vazia; **NÃO atribui Função RBAC** automaticamente |

---

## 5. Normalizações esperadas (PR 2 — `normalization.py`)

| Campo | Função (futura) | Resultado |
|---|---|---|
| `cpf` | `normalize_cpf` | Strip máscara, validar 11 dígitos + DV |
| `telefone` | `normalize_phone` | E.164 ou padrão BR `(85) 99999-9999` |
| `email` | `normalize_email` | Lowercase, strip, validar shape |
| `nome` / `nome_completo` | `normalize_text_key` | Strip, title case (configurável) |
| `cargo` | `normalize_text_key` | Strip, lookup em mapa Cargo→Função |
| `gerencia` | `normalize_text_key` | Strip, lookup em `SETOR_GROUPS` |

Mapeamento `Cargo → Função RBAC` (proposta — confirmar com Matheus):

| `Cargo` planilha | Função RBAC | Aceito em import? |
|---|---|---|
| Formador / Formadora | Formador | ✅ sim |
| Coordenador / Coordenadora | Coordenador | ✅ sim |
| Apoio de Coordenação | Apoio de Coordenação | ✅ sim |
| Assistente Administrativo | Assistente Administrativo | ✅ sim |
| Gerente | Gerente | ⚠️ **revisão manual** — pode habilitar aprovação |
| Diretor / Superintendente | (sem mapeamento direto) | ❌ não atribuir; criar usuário sem Função |

---

## 6. Validações antes do upload (PR 6)

### Bloqueantes (linha rejeitada)
- CPF inválido (formato ou DV).
- Email mal-formado.
- `gerencia` não encontrada em `SETOR_GROUPS`.
- CPF duplicado **no próprio arquivo**.
- Email duplicado **no próprio arquivo**.

### Avisos (linha aceita com warning)
- CPF já existe no banco com nome diferente → atualizar telefone/cargo mas avisar.
- Email já existe no banco mas com CPF diferente → **rejeitar** (conflito de identidade).
- Telefone fora do padrão BR.
- `cargo` sem mapeamento → criar usuário sem Função.

---

## 7. Regras de duplicidade / hash

### Chave natural
`CPF` é a chave primária de identidade. `email` é secundária (unique constraint).

### `external_hash` (idempotência)
SHA1 ou SHA256 sobre:
```text
normalize_cpf(cpf) + "|" + normalize_email(email)
```

### Comportamento por match
| CPF existe | Email existe | Ação |
|---|---|---|
| Não | Não | Criar usuário novo + atribuir Setor (+ Função se mapeada) |
| Sim | Sim (mesmo user) | Atualizar telefone, cargo (se mapeado); manter grupos atuais |
| Sim | Não, ou email diferente | Atualizar email (com warning) |
| Sim | Sim (user diferente) | **Erro bloqueante** — conflito de identidade |
| Não | Sim | **Erro bloqueante** — não pode haver email sem CPF |

---

## 8. Models / services / endpoints relacionados (estado real do código — 2026-05-05)

| Componente | Caminho | Função | Status |
|---|---|---|---|
| Model `Usuario` | `apps/core/models/usuario.py` | `AbstractUser` custom + cpf único, telefone, cargo | ✅ existe |
| Model `Group` | Django auth | Setor (13) + Função (5) | ✅ existe |
| Constantes | `apps/core/constants.py:16-45` | `SETOR_GROUPS`, `FUNCAO_GROUPS`, `ALLOWED_USER_GROUPS` | ✅ existe |
| **Service** | `apps/core/services/usuarios_import.py` | `import_usuarios_from_file(path: str, dry_run: bool = True) -> dict` | ✅ **já implementado** |
| **Endpoint síncrono** | `POST /api/usuarios/import/` (`ImportUsuariosView` em `apps/core/views_import_usuarios.py`) | dry_run via query param `?dry_run=true\|false`; multipart `file=` no body | ✅ **já funciona** |
| Endpoint async | (não implementado para usuarios) | ASQ-005 Fase 1 só cobre `bloqueios`; Fase 2 migrará usuarios | ⏳ Fase 2 do ImportJob |
| Gate RBAC efetivo | `IsAuthenticated + HasPerm("manage_admin_registries")` | DAT + Diretoria (via cap `manage_admin_registries`) — **NÃO** `import_spreadsheet` | ✅ aplicado em prod |
| Validação de upload | `apps.core.upload_validators.validate_upload` | Magic bytes + tamanho + content-type | ✅ existe |
| Reconciliação | (não usa `resolvers.py` — Usuario é destino, não FK alvo) | — | — |

### Comportamento real do service (lido em código)

- **Idempotência**: por CPF (campo unique).
- **Transação**: `transaction.atomic()` externa para dry-run rollback + `transaction.atomic()` interno por linha (savepoint-per-row, padrão ASQ-016).
- **Retorno**:
  ```python
  {
      "stats": {"created": N, "updated": N, "unchanged": N, "skipped": {"cpf_invalid": N, "nome_missing": N, "other": N}},
      "pendencias": {"cpf_invalid": [...], "nome_missing": [...], "outros": [...]},
      "dry_run": bool,
      "file": str,
  }
  ```
- **Colunas esperadas pelo service** (docstring linha 6-13):
  - `cpf` (obrigatório, 11 dígitos)
  - `nome` (obrigatório, completo — vira first_name + last_name)
  - `email` (opcional)
  - `telefone` (opcional)
  - `cargo` (opcional)
  - `is_active` (opcional, default `True`)
  - `grupos` (opcional, separados por vírgula)

> ⚠️ **Atenção template CSV**: o cabeçalho atual do template (`nome,nome_completo,cpf,telefone,email,cargo,gerencia`) **não bate** com o cabeçalho aceito pelo service (`cpf,nome,email,telefone,cargo,is_active,grupos`). Ver §15 abaixo.

---

## 9. O que pode ser criado/atualizado

### Pode criar
- Novo `Usuario` (sem `is_superuser`, sem `is_staff`).
- Atribuir **Setor** (1 grupo) conforme `Gerência`.
- Atribuir **Função** (1 grupo) conforme `Cargo`, se estiver no whitelist do mapa.

### Pode atualizar
- `telefone`, `cargo` (string livre), `email` (com warning).
- Setor: **adicionar** um grupo de setor; **não remover** automaticamente.
- Função: **adicionar** Função do whitelist; **não remover** automaticamente.

---

## 10. O que NÃO deve acontecer automaticamente

- `is_superuser = True` — **nunca** vinda de import.
- `is_staff = True` — só via Admin (manual).
- Atribuir Função **`Gerente`** — exige aprovação humana (pode habilitar aprovação de solicitação).
- Atribuir Setor **`Superintendência` + Função `Gerente`** (composite) — pode aprovar fluxo SUPER (PA-02).
- Atribuir Função **`Assistente Administrativo`** combinada com Setor **`Controle`** — composite delega aprovação.
- Remover Setor/Função existente.
- Capabilities individuais (`PermissaoFuncional.groups`) — admin-driven (D17).
- Reset de senha — usuário recebe email de bem-vindo separado (fora deste import).

Mecânica sugerida (PR 6): linhas que cairiam em qualquer um desses casos viram **warning + log**, e o sistema cria o usuário **sem** a atribuição sensível, deixando para o admin completar.

---

## 11. Como auditar depois

### AuditLog
Filtrar:
```python
AuditLog.objects.filter(
    action="IMPORT_USUARIOS",
    created_at__gte=<timestamp>
).values(
    "usuario", "details__arquivo_hash",
    "details__linhas_criadas",
    "details__linhas_atualizadas",
    "details__linhas_warnings",
)
```

### Snapshot por arquivo
`ImportBatch` (PR 4 futura) registra:
- `arquivo_hash` (SHA256 do arquivo CSV inteiro).
- Linhas processadas e seu estado individual.

### Drift check
- Comparar `Usuario.objects.filter(date_joined__date=<dia_import>).count()` com `linhas_criadas`.
- Listar usuários com `groups.count() == 0` (criados sem Setor — sinal de mapa inválido).
- Listar usuários sem Função (`FUNCAO_GROUPS` não intersecciona com `user.groups`).

---

## 12. Riscos identificados

| Risco | Severidade | Mitigação |
|---|---|---|
| **CPF duplicado** entre planilha e banco | Alta | Bloqueante; whitelist explícita para forçar match |
| **Email duplicado** com CPF diferente | Alta | Bloqueante; conflito de identidade |
| Telefone em formatos heterogêneos | Média | `normalize_phone` aceita variantes; warning se inválido |
| Cargo/Gerência mapeando errado para grupo | Alta | Whitelist explícita; "Diretor" não vira Função; "Gerente" gera warning |
| Atribuição automática de `Gerente` Superintendência → aprovador SUPER inesperado | **Crítica** | NÃO atribuir automaticamente; gate manual sempre |
| Nome com acento variável (ex: "Sá" vs "Sa") | Baixa | `nome` é livre; chave é CPF |
| Encoding (latin-1 vs utf-8) | Média | Especificar UTF-8 no template; rejeitar se decode falhar |

---

## 13. Pendências para Matheus (revistas — só as que o código ainda não responde)

1. **Drift de cabeçalho do template** (ver §15): alinhar `sheets.banco` ao cabeçalho que o service aceita hoje (`cpf,nome,email,telefone,cargo,is_active,grupos`) **OU** ajustar service para aceitar o cabeçalho v0.1 (`nome,nome_completo,...,gerencia`). Decisão de produto.
2. **Mapa completo `Cargo` → Função RBAC**: confirmar termos reais da coluna `Cargo`. O service hoje só armazena texto livre em `Usuario.cargo`; **não atribui Função RBAC automaticamente**. Se atribuição automática for desejada, exige feature nova (não está no roadmap atual).
3. **Coluna `grupos` no service real** aceita lista separada por vírgula (`"DAT,Vidas,Formador"`). Confirmar se `sheets.banco` exporta nesse formato ou se prefere `gerencia` + `cargo` separados (transformação no client).
4. **Política de email**: aceita emails pessoais (`@gmail.com`) ou só institucional?
5. **Senha inicial**: o service hoje usa `set_unusable_password()` + token de reset (não confirmado se já dispara email; verificar `_process_row`). Se não dispara, criar fluxo de envio é PR separada.
6. **Cargo `"Gerente"`** + Setor `"Superintendência"`: política definitiva. Hoje o service simplesmente grava no campo `cargo` (texto) — não atribui grupo `Gerente` automaticamente. Atribuição via grupos só acontece pela coluna `grupos` explícita.
7. **`Assistente Administrativo` + `Controle`** (composite de aprovação): mesma situação. Atribuição automática violaria D17; só admin manual.
8. **Telefone obrigatório?** Hoje no model é opcional; service aceita vazio.

### Pendências que a v0.1 listava e o código já resolve

- ~~Como reconciliar usuário por CPF/email~~ → resolvido: CPF é chave (unique constraint).
- ~~`normalize_cpf` precisa ser criado~~ → existe lógica de validação básica em `_process_row`; consolidar em `apps/core/imports/normalization.py` é PR 3 do roadmap.
- ~~`normalize_phone`~~ → idem.
- ~~Como tratar `is_active`~~ → coluna opcional aceita pelo service, default `True`.

---

## 14. Histórico de versões

- 2026-05-05 — v0.1 — PR 1 (contrato inicial). Tratou service como "futuro".
- 2026-05-05 — v0.2 — Auditoria contra código. Confirmado: `usuarios_import.py` + `ImportUsuariosView` já existem e funcionam. Documenta cabeçalho real esperado. Reorienta pendências.

---

## 15. Drift conhecido: template CSV vs cabeçalho aceito pelo service

**Cabeçalho do template atual** (`templates/usuarios.template.csv`):
```text
nome,nome_completo,cpf,telefone,email,cargo,gerencia
```

**Cabeçalho aceito pelo service** (docstring `usuarios_import.py` linhas 6-13):
```text
cpf,nome,email,telefone,cargo,is_active,grupos
```

### Diferenças

| Coluna template v0.1 | Coluna service | Ação |
|---|---|---|
| `nome` + `nome_completo` | só `nome` (vira `first_name` + `last_name` via split) | Service usa **só `nome`** completo — eliminar `nome_completo` ou consolidar |
| `gerencia` | `grupos` (lista) | Renomear no template ou implementar `gerencia` no service |
| (ausente) | `is_active` (opcional) | Adicionar ao template como coluna opcional |

### Resolução proposta (decisão pendente Matheus)

**Opção A** — Atualizar template para casar com o service (caminho mais rápido):
```csv
cpf,nome,email,telefone,cargo,is_active,grupos
00000000000,Maria de Souza Exemplo,maria.exemplo@example.com,85999999999,Formadora,true,"Superintendência,Formador"
```

**Opção B** — Estender o service para aceitar o cabeçalho v0.1 (mantendo compatibilidade): mapear `nome_completo`→`nome`, `gerencia`→`grupos[0]`. Exige PR de runtime no service (fora do escopo desta PR).

A v0.2 da doc deixa o template original e marca esta decisão como pendência.
