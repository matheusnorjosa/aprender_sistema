---
status: canonical
last_verified: 2026-07-20
sources_of_truth:
  - v2/docs/audits/2026-07-17-system-module-audit.md
  - reverificação por execução contra main d08acfa5 (2026-07-20)
---

# Achados reais — auditoria modular M00–M28

> **Este é o documento vivo.** Atualize-o conforme cada achado for resolvido.
> O relatório da investigação (`2026-07-17-system-module-audit.md`) é histórico e imutável:
> guarda as 498 hipóteses, os vereditos e os erros do processo. Aqui ficam só os achados que
> **sobreviveram à refutação e foram reconfirmados por execução** contra o código atual.

## Como este documento nasceu

1. Auditoria modular de 29 módulos sobre o commit `90f6a048` → **498 achados**.
2. Pente fino adversarial: cada achado confrontado por um refutador; P0/P1 por um segundo
   cético independente → **P0 11→5, P1 181→52**, 224 notas trocadas, 4 refutados.
3. Reverificação por execução contra `main d08acfa5`, com os fatos reais do ambiente
   confirmados pelo dono → o que está abaixo.

A auditoria original **acertava os mecanismos e errava as consequências**. Por isso as
severidades daquele relatório não valem: valem as desta tabela.

## Situação em 2026-07-20

| | Qtd |
|---|---:|
| **P0 — vivos em produção** | **2** |
| P1 | 36 |
| P2 | 19 |
| **Total acionável** | **57** |
| Já corrigidos (não viram issue) | 4 |

Baseline da auditoria: `90f6a048`. Produção: `94f27651`. `main`: `d08acfa5`.
**Todos os 57 achados abaixo foram reconfirmados vivos em produção por execução.**

## Legenda de status

| Status | Significado |
|---|---|
| `aberto` | confirmado vivo, sem correção iniciada |
| `em andamento` | PR aberta |
| `resolvido` | corrigido e mergeado — anote o commit e a data |
| `em prod` | correção deployada e verificada em produção |
| `descartado` | reclassificado ou refutado depois — anote o porquê |

## Achados acionáveis

| ID | Sev. | Status | Título | Ator real | Issue | Resolvido em |
|---|---|---|---|---|---|---|
| `M03-01` | **P0** | aberto | rbac/imports: import de usuários permite auto-escalação a Gerente+Superintendência | — | #1610 | — |
| `M26-01` | **P0** | aberto | infra/DR: restore_db.sh roda `gzip -t` antes de decifrar e rejeita todo backup .age de producao | Nao depende de RBAC/grupo — o alcance e operacional. Qualquer operador… | #1611 | — |
| `M01-07` | **P1** | aberto | rbac/admin: salvar grupo revoga membros alem dos 100 primeiros (paginador global ignora page_si… | Superuser (1 ativo em prod) para a perda de dados no editor de grupos … | #1612 | — |
| `M02-09` | **P1** | aberto | imports/resolvers: rejeitar ambiguidade em vez de escolher com .first(), e corrigir normalizaçã… | DAT (3 ativos) e Superintendência (1 ativo) + superuser (1). Os endpoi… | #1613 | — |
| `M03-03` | **P1** | aberto | auth: lockout e throttle de login sao evadiveis por grafia do CPF e por sessao autenticada | Qualquer um dos 148 usuarios ativos autenticados (nenhum grupo necessa… | #1614 | — |
| `M04-01` | **P1** | aberto | imports/equipe-gerencia: import cria Gerência duplicada para "Brincando" e "Ed Financeira" e de… | DAT (3 membros ativos nao-superuser) + superuser (1). O endpoint POST … | #1615 | — |
| `M07-01` | **P1** | aberto | rbac/admin: DAT faz takeover de conta aprovadora (senha, desativação e hard delete) | — | #1616 | — |
| `M07-02` | **P1** | aberto | RBAC/admin de usuarios: DAT faz takeover de conta aprovadora (senha, e-mail, desativacao e hard… | DAT — 3 membros ativos nao-superuser. Probe confirma que DAT e o UNICO… | #1617 | — |
| `M07-03` | **P1** | aberto | RBAC/Auditoria: registrar AuditLog em todas as mutações de identidade do UsuarioAdminViewSet | 3 usuários ativos do grupo DAT (capability `manage_admin_registries`) … | #1618 | — |
| `M08-01` | **P1** | aberto | disponibilidade: PATCH transfere bloqueio aprovado para usuário arbitrário, sem policy nem Audi… | — | #1619 | — |
| `M08-12` | **P1** | aberto | imports/eventos: import de eventos grava solicitacao aprovada sem hard gate de disponibilidade … | Grupo DAT (3 membros ativos nao-superuser) + 1 superuser ativo. `Permi… | #1620 | — |
| `M09-05` | **P1** | aberto | Deslocamentos: UI exige delegacao que o backend nega — Coordenador nao consegue registrar nenhu… | Coordenador (42 ativos) e o ator principal: 100% dos creates pela UI f… | #1621 | — |
| `M09-06` | **P1** | aberto | Deslocamentos: filtros Origem/Destino inutilizaveis — pagina desmonta a cada tecla e o filtro f… | ~48 atores reais: Coordenador 42 + DAT 3 + Controle 1 + Superintendenc… | #1622 | — |
| `M10-01` | **P1** | aberto | solicitações: Gerente lê, edita e exclui solicitação de qualquer gerência (sem escopo ator×alvo… | Gerente — 9 usuários ativos não-superuser em produção. Ator real e num… | #1623 | — |
| `M10-02` | **P1** | aberto | solicitação: troca de projeto para fluxo SUPER mantém status aprovado (lavagem de aprovação, vi… | — | #1624 | — |
| `M10-03` | **P1** | aberto | solicitacoes: bloquear edicao e exclusao enquanto gcal_status=PENDING (publica conteudo diferen… | Ator real e amplo: o proprio owner da solicitacao. Em prod isso alcanc… | #1625 | — |
| `M10-04` | **P1** | aberto | solicitacoes: extra_participants aceita alvo arbitrário sem policy, sem limite e estoura 500 | Grande. `create` exige `HasPerm("create_solicitation")` (views_solicit… | #1626 | — |
| `M10-05` | **P1** | aberto | solicitacoes: edição não reconcilia participantes — convidados e COORD_ACOMPANHA ficam órfãos e… | Existe e é o fluxo comum: 42 Coordenadores ativos + 9 Gerentes + 1 sup… | #1627 | — |
| `M10-07` | **P1** | aberto | imports/eventos: reimport sobrescreve decisão de aprovação, owner e datas e reporta "unchanged" | DAT (3 membros ativos não-superuser) + superuser (1). `import_spreadsh… | #1628 | — |
| `M12-19` | **P1** | aberto | Pré-agenda: polling estoura o throttle do operador e a lista mostra total inalcançável | Sim. Rota `/pre-agenda` e `/controle/pre-agenda` sao gateadas por `Req… | #1629 | — |
| `M14-02` | **P1** | aberto | Grade mensal: evento com 2+ participantes multiplica CH, codigo e detalhes por participante | Amplo e real. `MonthlyAvailabilityView.permission_classes = [IsAuthent… | #1630 | — |
| `M14-05` | **P1** | aberto | Disponibilidade/Grade Mensal: unificar a população da grade — visão "Todas" usa coorte históric… | Permanentemente: Controle (1 ativo), DAT (3 ativos), superuser (1) — t… | #1631 | — |
| `M15-02` | **P1** | aberto | Compras DAT: validar invariantes de DATCompra (sobreuso, valor negativo, item vazio, produto de… | DAT (3 ativos) + Controle (1 ativo). O gate de create/update do DATCom… | #1632 | — |
| `M15-03` | **P1** | aberto | Compras: definir identidade real de `Compra` — hash sobre campos mutaveis duplica linha na corr… | DAT (3 ativos) e Controle (1 ativo) = 4 atores nao-superuser reais, ma… | #1633 | — |
| `M15-04` | **P1** | aberto | imports/compras: preview aceita linhas invalidas (quantidade vazia/decimal/negativa, data ausen… | DAT (3 membros ativos nao-superuser) + 1 superuser. O endpoint `POST /… | #1634 | — |
| `M15-05` | **P1** | aberto | imports/compras: usar UF e código do produto na resolução e gravar Compra.produto | DAT (3 membros ativos nao-superuser) + 1 superuser, via POST /api/cont… | #1635 | — |
| `M15-09` | **P1** | aberto | Compras (DATCompra): edição reassocia material para outro município/projeto silenciosamente | DAT (3 ativos) + Controle (1) + Assistente Administrativo (1, herda Co… | #1636 | — |
| `M15-10` | **P1** | aberto | DAT/Compras: formulario de Nova Compra descarta 5 campos, grava valor zero e esconde o erro por… | DAT (3 ativos) e Superintendencia (1 ativo) — quem tem acesso ao CRUD … | #1637 | — |
| `M16-07` | **P1** | aberto | DAT Registros: datas do formulario nao chegam ao banco — 3 campos FORMAR dao 400 e 3 campos AVA… | DAT (3 membros ativos nao-superuser) + 1 superuser. A capability que a… | #1638 | — |
| `M16-08` | **P1** | aberto | DAT Registros: opções de status da UI divergem dos choices do backend — save falha e estado de … | DAT (3 membros ativos) + superuser (1). O DATRegistroViewSet exige gru… | #1639 | — |
| `M17-01` | **P1** | aberto | DAT/imports: card "Importar CADASTROS DAT" grava AcaoDAT legacy, que nenhuma tela le | DAT (3 membros ativos nao-superuser) + 1 superuser. O gate do card e d… | #1640 | — |
| `M17-02` | **P1** | aberto | DAT (Ações/Cadastros): editar pelo modal apaga silenciosamente as datas do registro | DAT (3 ativos) via /dat/cadastros e Controle (1) + Assistente Administ… | #1641 | — |
| `M19-01` | **P1** | aberto | DAT/PlanoFormacoes: CH total e anual ficam um PATCH atrasadas ao atualizar formacao inline | DAT (3 membros ativos nao-superuser) + superuser (1). A action exige H… | #1642 | — |
| `M22-14` | **P1** | aberto | Import de bloqueios: resolucao por nome com fallback substring cria bloqueio auto-aprovado na a… | Grupo DAT (3 membros ativos nao-superuser) + 1 superuser ativo, via `H… | #1643 | — |
| `M23-02` | **P1** | aberto | auditoria: redigir CPF (`username`) nos AuditLog de LOGIN_FAILED, na escrita e na leitura | DAT (3 ativos), Controle (1), Superintendencia (1), Gerente (9) — 14 n… | #1644 | — |
| `M26-02` | **P1** | aberto | DR: restore_db.sh declara "Restore completed successfully!" com exit 0 apos um restore que perd… | Operador de DR com SSH na VM02 (na pratica o unico superuser/dono). Na… | #1645 | — |
| `M26-03` | **P1** | aberto | infra/DR: test_dr.sh nao exercita o backup cifrado — round-trip .age via restore_db.sh nunca fo… | Nao e achado de RBAC — nenhum grupo o alcanca e o censo nao muda a sev… | #1646 | — |
| `M27-24` | **P1** | aberto | frontend/nginx: restaurar os 7 headers de seguranca descartados pelo add_header aninhado | Qualquer visitante nao autenticado / atacante externo — o defeito esta… | #1647 | — |
| `M01-01` | **P2** | aberto | seguranca/rede: resolver de IP confia no primeiro X-Forwarded-For, permitindo forjar origem em … | Anonimo na internet (nao requer conta): o caminho /api/ e o unico prox… | #1660 (épico) | — |
| `M03-02` | **P2** | aberto | auth: login aceita requisição cross-origin e emite sessão (login-CSRF) | — | #1648 | — |
| `M03-10` | **P2** | aberto | PII/LGPD: remover CPF integral de `Usuario.__str__` e redigir `username` nos logs de auditoria | DAT (3 ativos) e Controle (1 ativo) — 4 usuarios nao-superuser reais. … | #1657 (épico) | — |
| `M04-05` | **P2** | aberto | imports: valor desconhecido de `dry_run` é tratado como APPLY em 11 views | — | #1649 | — |
| `M05-03` | **P2** | aberto | RBAC: excluir um Group deixa capabilities dos ex-membros em cache por ate 300s | apenas superuser (1 ativo em prod). DELETE /api/grupos/{id}/ e Superus… | #1667 (épico) | — |
| `M05-05` | **P2** | aberto | RBAC: mudança de Grupo×Capability via API não gera AuditLog e o delta pendente é atribuído ao p… | Somente superuser (1 ativo em prod) e operações via Django Admin / she… | #1657 (épico) | — |
| `M05-07` | **P2** | aberto | frontend: HomePage decide criacao de solicitacao por setor/funcao em vez da policy create_solic… | DAT (3 ativos nao-superuser) e Gerente (9 ativos) — ambos existem hoje… | #1655 (épico) | — |
| `M06-04` | **P2** | aberto | frontend/nginx: locations `/`, `/assets/`, imagens e `/health` perdem os 7 headers de segurança | Não é achado de RBAC — o censo de grupos não se aplica. A superfície a… | #1661 (épico) | — |
| `M08-07` | **P2** | aberto | disponibilidade: filtrar papeis ocupantes tambem na query de eventos existentes (CONVIDADO bloq… | Somente o superuser (1 ativo), via Django admin (`ParticipationAdmin`,… | #1664 (épico) | — |
| `M08-09` | **P2** | aberto | Disponibilidade (RD-05): capacidade diaria ignora eventos que cruzam a meia-noite | Qualquer usuario autenticado que crie/edite Solicitacao ou consulte /a… | #1664 (épico) | — |
| `M10-06` | **P2** | aberto | gcal: descrição do evento perde a seção "Equipe" — payload lê formadores/coordenador legados qu… | Qualquer criador de solicitação — Coordenador (42 ativos), Formador (9… | #1666 (épico) | — |
| `M11-04` | **P2** | aberto | aprovação: `ids` em lote sem validação decompõe string em dígitos e aprova alvo não nomeado | — | #1650 | — |
| `M12-15` | **P2** | aberto | oauth: vincular state do OAuth Google a sessao que o criou (identidade lida do sufixo mutavel) | Atacante precisa mintar um state via /oauth/google/start, que exige Ca… | #1652 | — |
| `M14-01` | **P2** | aberto | RBAC/Grade mensal: HasSectorAccess autoriza qualquer papel com vínculo e ignora `ativo` no ramo… | Depende de variável NÃO VERIFICADA. O gate só é alcançável por quem te… | #1656 (épico) | — |
| `M14-03` | **P2** | aberto | Disponibilidade: CH Ano na grade mensal soma so o mes consultado e repete o CH Mes | ~14 atores nao-superuser: DAT 3 + Controle 1 + Assistente Administrati… | #1663 (épico) | — |
| `M15-08` | **P2** | aberto | DAT/Compras: PATCH concorrente em DATCompra sobrescreve estoque (lost update) e duplo POST cria… | DAT (3 ativos), Controle (1), Assistente Administrativo lotado em Cont… | #1665 (épico) | — |
| `M16-04` | **P2** | aberto | DAT: PATCH concorrente perde update (lost update) em ProjetoGeral/DATRegistro | — | #1651 | — |
| `M18-05` | **P2** | aberto | DAT Coordenadores: edicao apaga data_admissao e vaza observacoes entre registros (detalhe/edica… | DAT (3 ativos) e Controle (1 ativo) + o superuser (1). O endpoint exig… | #1654 (épico) | — |
| `M18-06` | **P2** | aberto | Paginação: DRF ignora `page_size` e esconde até 77% das linhas nas telas DAT | DAT (3 ativos) e Superintendência (1 ativo) + 1 superuser — a permissã… | #1653 (épico) | — |

## P0 — detalhe

### M03-01 — rbac/imports: import de usuários permite auto-escalação a Gerente+Superintendência

- **Status:** aberto · **Vivo em produção** · reconfirmado 2026-07-20 · issue #1610
- **Ator real:** —

**Evidência de execução**

```text
Worktree C:\tmp\aprender_verify_main em d08acfa5 (HEAD da main).

1) Prova de execucao HTTP real (DRF APIClient, stack completa de middleware/URL/permissoes), DB isolado vm_m0301:
   docker exec -e DB_NAME=vm_m0301 aprender_vmain-web-1 pytest apps/core/tests/test_probe_m0301.py -q --no-migrations -p no:cacheprovider -s

   Cadeia: usuario `dat_attacker` (cpf 11144477735) apenas no grupo DAT -> POST /api/usuarios/import/?dry_run=false
   com CSV: `cpf,nome,grupos` / `11144477735,Dat Attacker,"Gerente,Superintendencia"`

   Saida observada:
     GRUPOS ANTES: ['DAT']
     HTTP STATUS: 200
     BODY: {'stats': {'created': 0, 'updated': 0, 'unchanged': 1, 'skipped': {'cpf_invalid': 0, 'nome_missing': 0, 'superuser_protected': 0, 'other': 0}}, 'pendencias': {...todas vazias...}, 'dry_run'
     GRUPOS DEPOIS: ['DAT', 'Gerente', 'Superintendencia']
     ESCALOU: True
     1 passed

   HTTP 200, zero pendencias, zero skips: o ator concedeu a si proprio Gerente + Superintendencia.

2) Prova de que a correcao nao existe em producao:
   git diff --stat 94f27651 HEAD -- v2/backend/apps/core/services/usuarios_import.py v2/backend/apps/core/views_import_usuarios.py
     -> saida VAZIA (arquivos byte-identicos entre prod 94f27651 e main d08acfa5)
   git log --oneline 94f27651..HEAD -- <mesmos arquivos>
     -> nenhum commit
   git log --oneline 90f6a048..HEAD -- v2/backend/apps/core/services/usuarios_import.py
     -> nenhum commit (inalterado desde o baseline da auditoria)

3) Busca por guard: grep "SuperuserOnly|allowlist|actor" nos dois arquivos retorna apenas
   views_import_usuarios.py:113, um comentario sobre allowlist de SUFIXO de arquivo (#1343, path-injection) — nada de RBAC.

Arquivo de probe removido; `git status --porcelain` nao lista test_probe_m0301.py.
```

### M26-01 — infra/DR: restore_db.sh roda `gzip -t` antes de decifrar e rejeita todo backup .age de producao

- **Status:** aberto · **Vivo em produção** · reconfirmado 2026-07-20 · issue #1611
- **Ator real:** Nao depende de RBAC/grupo — o alcance e operacional. Qualquer operador/SRE com acesso a VM02_DB que execute a ferramenta oficial de restore durante um incidente. O censo de grupos e irrelevante aqui (Diretoria/Apoio de Coordenacao nao entram). Impacto potencial: 148 usuarios ativos, todo o banco de producao.

**Evidência de execução**

```text
HEAD do worktree = d08acfa5. `restore_db.sh:91` executa `gzip -t "$BACKUP_FILE"` incondicionalmente; o branch `.age` so aparece em `:113-119`. Paridade host/container: md5 34849168dbee9bb49c5c47212e83

Historico (arquivo v2/infra/scripts/restore_db.sh):
  git log --oneline 94f27651..HEAD -- <arq>  => VAZIO  (prod == main neste ponto; defeito VIVO em prod)
  git log --oneline 90f6a048..HEAD -- <arq>  => VAZIO  (nada mudou desde a auditoria)
  ultimo commit no arquivo: a7428bc8 (#1543) — corrigiu a SELECAO de .age (:36,:56,:61), nao a VERIFICACAO.

Prod grava exclusivamente .age: backup_db.sh:44-52 (fail-closed sem recipient; nome vira .sql.gz.age quando ha recipient) + docker-compose.prod.yml:197 (BACKUP_AGE_RECIPIENT=age1h52qdv3m...).

Probe isolado (container aprender_vmain-web-1, DB_NAME=rv_m26_01):
  head -c22 do artefato .age => "age-encryption.org/v1"
  gzip -t <.age>       => "gzip: ...: not in gzip format"  exit=1
  gzip -t <.sql.gz>    => exit=0   (controle)

End-to-end pela ferramenta oficial, TRES caminhos de entrada, todos abortam:
 (A) arquivo explicito:
     printf 'yes\n' | bash /app/infra/scripts/restore_db.sh /tmp/m26probe/backup_full_20260720_010000.sql.gz.age
     -> "[..] Verifying backup integrity... / gzip: ...: not in gzip format / ERROR: Backup file is corrupted!"  EXIT_CODE=1
 (B) --latest (dir com .sql.gz antigo + .age recente): mesma saida, mesmo abort.
 (C) interativo, selecao "1": mesma saida, mesmo abort.
Em nenhum caso passou da linha 91 — DROP DATABASE (linha 107) NUNCA alcancado (fail-closed, sem destruicao de dados).

Cobertura: zero. `find . -name "*.bats"` => apenas v2/infra/deployer/tests/{hooks_check_backup,integration,lib_gc,lib_guards,systemd_units}.bats. Nenhum teste referencia restore_db.

Achado adicional (mesma correcao): restore_db.sh:17 hardcoda BACKUP_DIR="/var/backups/aprender" e ignora a env var, enquanto backup_db.sh:31 usa BACKUP_DIR="${BACKUP_DIR:-/backups}". Provado: com -e B

Nota operacional: `command -v age` no container web => MISSING. Mesmo apos corrigir a ordem, o restore precisa rodar onde o binario `age` exista — verificar host/imagem alvo.
[CORRIGIDO EM 2026-07-24 — ver "Retificacao" abaixo: o probe rodou num container de DEV. A imagem de PRODUCAO tem o binario `age` (Dockerfile.prod:56).]

Higiene: nenhum arquivo de probe criado no host; artefatos de container removidos (/tmp/m26probe e /var/backups/aprender). `git status --porcelain` mostra apenas test_probe_m1608.py e test_probe_m1702
```

#### Contexto

`v2/infra/scripts/restore_db.sh` executa `gzip -t "$BACKUP_FILE"` **incondicionalmente** na Step 1 (linha 91), antes do branch que trata artefatos cifrados com `age` (linhas 113-119).

Producao grava **exclusivamente** `backup_full_*.sql.gz.age`:
- `backup_db.sh:44-52` — fail-CLOSED: sem `BACKUP_AGE_RECIPIENT` e sem `BACKUP_ALLOW_PLAINTEXT=1` o backup aborta; com recipient o nome do arquivo vira `.sql.gz.age`.
- `v2/infra/docker-compose.prod.yml:197` — `BACKUP_AGE_RECIPIENT: age1h52qdv3m73yv75ussvuten7ckhkhr5axl3kgjnadl89j5ux265ls2jda8c` definido.

Um artefato `age` comeca com o cabecalho de texto `age-encryption.org/v1`, que nao e gzip. Logo `gzip -t` retorna 1 e o script aborta com **`ERROR: Backup file is corrupted!`** — mensagem factualmente falsa. Resultado: **o unico formato de backup que existe em producao nao pode ser restaurado pela ferramenta oficial de restore.**

Agravantes:
- A mensagem e ativamente enganosa. Sob pressao de incidente, um operador pode concluir que a cadeia inteira de backups esta corrompida e desistir do restore.
- Atinge os **tres** caminhos de entrada (arquivo explicito, `--latest`, modo interativo) — a selecao ja e ciente de `.age` (`:36,:56,:61`), so a verificacao nao e.
- Zero cobertura: nao existe `.bats` para `restore_db.sh` (os unicos bats do repo cobrem `v2/infra/deployer/`).
- Bug secundario adjacente: `BACKUP_DIR` esta **hardcoded** em `restore_db.sh:17` (`/var/backups/aprender`) e nao respeita a env var, enquanto `backup_db.sh:31` usa `BACKUP_DIR="${BACKUP_DIR:-/backups}"`. Dentro do container (mount `/var/backups/aprender:/backups`) o `--latest` nao acha nada.

Atenuante: a falha e **fail-closed** — para na linha 91, ANTES do `DROP DATABASE` da linha 107. Nao ha destruicao de dados, e um operador experiente pode contornar manualmente com `age -d -i /etc/backup-key.txt <arq> | gunzip | psql`. O dano e RTO estourado + perda de confianca no DR, nao perda de dados.

#### Evidencia

Ambiente: worktree em `d08acfa5` (main), container `aprender_vmain-web-1`, `DB_NAME=rv_m26_01`.

Paridade host/container confirmada (`md5sum` = `34849168dbee9bb49c5c47212e838568` nos dois).

**O codigo nao mudou nem desde a auditoria nem em relacao a prod:**
```
$ git log --oneline 94f27651..HEAD -- v2/infra/scripts/restore_db.sh
(vazio)
$ git log --oneline 90f6a048..HEAD -- v2/infra/scripts/restore_db.sh
(vazio)
```
Ultimo commit a tocar o arquivo: `a7428bc8 fix(backup): fecha as camadas silenciosas do DR (fail-closed, pipefail, .age) (#1543)` — corrigiu a **selecao** de `.age` mas nao a **verificacao**.

**Probe isolado do `gzip -t`:**
```
== head do .age ==
age-encryption.org/v1
== gzip -t no .age ==
gzip: .../backup_full_20260720_010000.sql.gz.age: not in gzip format
exit=1
== gzip -t no controle .sql.gz ==
exit=0
```

**End-to-end pela ferramenta oficial, caminho de arquivo explicito:**
```
$ printf 'yes\n' | bash /app/infra/scripts/restore_db.sh /tmp/m26probe/backup_full_20260720_010000.sql.gz.age
Backup file: /tmp/m26probe/backup_full_20260720_010000.sql.gz.age
Database: rv_m26_01
[Mon Jul 20 16:38:11 UTC 2026] Starting restore...
[Mon Jul 20 16:38:11 UTC 2026] Verifying backup integrity...
gzip: /tmp/m26probe/backup_full_20260720_010000.sql.gz.age: not in gzip format
ERROR: Backup file is corrupted!
EXIT_CODE=1
```

**`--latest` (diretorio com `.sql.gz` antigo + `.age` recente):**
```
[..] Verifying backup integrity...
gzip: /var/backups/aprender/backup_full_20260720_010000.sql.gz.age: not in gzip format
ERROR: Backup file is corrupted!
```

**Modo interativo, selecao "1" (mais recente):**
```
[..] Verifying backup integrity...
gzip: /var/backups/aprender/backup_full_20260720_010000.sql.gz.age: not in gzip format
ERROR: Backup file is corrupted!
```

Em nenhum caso a execucao passou da linha 91 — o `DROP DATABASE` (linha 107) nunca foi alcancado.

#### Correcao proposta

Tornar a Step 1 ciente do formato, espelhando o branch que ja existe na Step 4:

```bash
# Step 1: Verify backup integrity
echo "[$(date)] Verifying backup integrity..."
if echo "$BACKUP_FILE" | grep -q '\.age$'; then
    BACKUP_AGE_KEY="${BACKUP_AGE_KEY:-/etc/backup-key.txt}"
    if [ ! -r "$BACKUP_AGE_KEY" ]; then
        echo -e "${RED}ERROR: chave age nao legivel: $BACKUP_AGE_KEY${NC}"; exit 1
    fi
    if ! age -d -i "$BACKUP_AGE_KEY" "$BACKUP_FILE" | gzip -t; then
        echo -e "${RED}ERROR: backup cifrado invalido (falha ao decifrar ou gzip corrompido)!${NC}"
        exit 1
    fi
else
    if ! gzip -t "$BACKUP_FILE"; then
        echo -e "${RED}ERROR: Backup file is corrupted!${NC}"; exit 1
    fi
fi
echo -e "${GREEN}Backup integrity OK${NC}"
```

Notas:
- `set -o pipefail` no topo (hoje so `set -e`) para que a falha do `age` no pipe nao seja mascarada pelo exit 0 do `gzip -t` — mesma classe de bug ja corrigida em `backup_db.sh` pelo #1543.
- Corrigir junto `restore_db.sh:17` para `BACKUP_DIR="${BACKUP_DIR:-/var/backups/aprender}"`.
- Falhar cedo se `age` nao estiver no PATH e o alvo for `.age`. ~~a imagem `web` atual **nao tem** o binario `age`~~ — **retificado em 2026-07-24**: a imagem de **producao** instala `age` (`v2/infra/Dockerfile.prod:56`, junto com `postgresql-client`); quem **nao** tem e a imagem de **dev** (`v2/infra/Dockerfile.dev`, sem `age`). O guard continua valendo como defesa, mas o restore em producao roda onde `age` existe.

#### Retificacao de 2026-07-24 — o probe do `age` mediu o ambiente errado

O probe original (`command -v age` no container `aprender_vmain-web-1`) rodou sobre a imagem de
**desenvolvimento**, e a conclusao "a imagem web nao tem `age`" foi generalizada para producao.

Evidencia contraria: `v2/infra/Dockerfile.prod:47-57` instala explicitamente `age` na camada de
runtime, com o comentario *"cifra os dumps de DB em repouso (backup_db.sh + BACKUP_AGE_RECIPIENT;
#1455). O recipient (chave publica) ja esta no Env de prod, mas o binario faltava"* — ou seja, a
ausencia foi um bug **ja corrigido**. `v2/infra/Dockerfile.dev` nao instala `age`.

Consequencia pratica: o contorno manual `age -d -i <chave> <arq> | gunzip | psql` **roda** no
worker de producao. O `M26-01` continua **P0 e vivo** — o defeito e a ordem das operacoes em
`restore_db.sh:91`, nao a falta do binario.

Mesma classe de erro que o `M27-05` (porta 8000): conclusao tirada de um ponto de observacao que
nao era o ambiente sob analise.

#### Teste RED

Criar `v2/infra/scripts/tests/restore_db.bats` (primeira cobertura do script):

1. `restore .age passa na verificacao de integridade` — gerar `.sql.gz` valido, cifrar com `age -r`, invocar o script com stubs de `psql` no PATH, assertar que a saida contem `Backup integrity OK` e **nao** contem `Backup file is corrupted`.
2. `restore .age realmente corrompido falha` — truncar o corpo cifrado; assertar exit != 0 e que nenhum `DROP DATABASE` foi emitido ao stub de `psql`.
3. `restore .sql.gz simples continua funcionando` (nao-regressao).
4. `BACKUP_DIR respeita a env var` — `--latest` com `BACKUP_DIR` apontando para tmpdir seleciona o artefato de la.

Provar o RED antes do fix: hoje o caso 1 falha com `not in gzip format` / `Backup file is corrupted!`.

#### Verificacao GREEN

- `bats v2/infra/scripts/tests/restore_db.bats` — 4/4 verdes.
- Ensaio de DR real em staging: `backup_db.sh` com `BACKUP_AGE_RECIPIENT` -> gera `.age` -> `restore_db.sh --latest` -> restaura -> conferir `TABLE_COUNT` e contagem de linhas de tabelas-chave (`core_usuario`, `core_solicitacao`) contra a origem.
- Registrar a data do ensaio em `v2/docs/DISASTER_RECOVERY.md` / `BACKUP_OPERATIONS.md`.

#### Risco de rollout

Baixo. Muda apenas um script de operacao manual, sem caminho de codigo da aplicacao, sem migration, sem deploy de imagem (a menos que se opte por instalar `age` na imagem, que ai precisa de rebuild). O comportamento para `.sql.gz` simples fica identico. O risco maior e **nao** corrigir: o DR segue nao exercitado e a ferramenta oficial continua reportando corrupcao falsa durante um incidente real.

## Causas raiz (épicos)

Achados que compartilham uma causa raiz devem ser corrigidos estruturalmente, não com N
patches pontuais.

| Causa raiz | Sev. | Achados | Issue | Status |
|---|---|---|---|---|
| paginacao-global-sem-page-size | P1 | `M01-07`, `M18-06` | #1653 | aberto |
| list-serializer-como-fonte-de-detalhe | P1 | `M15-09`, `M17-02`, `M18-05` | #1654 | aberto |
| contrato-fe-be-sem-ssot | P1 | `M15-10`, `M16-07`, `M16-08`, `M09-05`, `M05-07` | #1655 | aberto |
| escopo-ator-alvo-ausente | P0 | `M22-01`, `M07-02`, `M10-01`, `M10-04`, `M14-01` | #1656 | aberto |
| auditoria-nao-invariante-e-pii | P1 | `M07-03`, `M05-05`, `M23-02`, `M03-10` | #1657 | aberto |
| resolvers-por-rotulo-humano | P1 | `M02-09`, `M04-01`, `M22-14`, `M15-05` | #1658 | aberto |
| import-bypassa-invariantes | P1 | `M08-12`, `M10-07`, `M17-01`, `M15-04` | #1659 | aberto |
| chave-de-seguranca-nao-canonica | P1 | `M03-03`, `M01-01` | #1660 | aberto |
| nginx-add-header-heranca | P2 | `M06-04`, `M27-24` | #1661 | aberto |
| dr-restore-nao-exercitado | P0 | `M26-01`, `M26-02`, `M26-03` | #1662 | aberto |
| grade-mensal-agregacao-e-populacao | P1 | `M14-02`, `M14-03`, `M14-05` | #1663 | aberto |
| motor-disponibilidade-sem-ssot-de-regra | P2 | `M08-07`, `M08-09` | #1664 | aberto |
| compras-sem-invariantes-nem-identidade | P1 | `M15-02`, `M15-03`, `M15-08` | #1665 | aberto |
| solicitacao-participantes-sem-ssot | P1 | `M10-05`, `M10-06` | #1666 | aberto |
| estado-derivado-obsoleto-apos-escrita | P2 | `M05-03`, `M19-01` | #1667 | aberto |
| frontend-ciclo-de-requisicoes | P1 | `M09-06`, `M12-19` | #1668 | aberto |

## Já corrigidos — não abrir issue

Registrados para memória: foram apontados pela auditoria e **já estavam resolvidos** quando
o relatório foi lido. É a prova de que uma auditoria longa envelhece e precisa ser revalidada
contra `HEAD` antes de virar fila de trabalho.

| ID | Situação | O que fechou |
|---|---|---|
| `M05-01` | corrigido em prod | v2/backend/apps/core/views/admin.py:494-500 — `GroupViewSet.get_permissions()`: list/retrieve → `HasPerm("manage_purchases_and_materials")`, TODO o resto (creat… |
| `M05-02` | corrigido em prod | C:\tmp\aprender_verify_main\v2\backend\apps\core\views\admin.py:492-499 — GroupViewSet.get_permissions() devolve [SuperuserOnly()] para toda action que nao seja… |
| `M02-10` | corrigido em prod | v2/frontend/public/sw.js:161 — `if (pathname.startsWith('/api/me/')) return false;` dentro de `isCacheableApiRoute()`. Não é um guard HTTP (não devolve status):… |
| `M06-03` | corrigido so na main | C:\tmp\aprender_verify_main\v2\frontend\eslint.config.js:38 — bloco com files: ['src/**/*.{ts,tsx}'] + tseslint.configs.recommended. Nao e guard HTTP (achado de… |

`M22-01` foi removido da lista acionável por ser **duplicata de `M03-01`** — mesmo defeito,
contado duas vezes no relatório original.

## Premissas de ambiente — confirmadas pelo dono em 2026-07-20

Fatos observados diretamente em produção. Substituem qualquer inferência feita a partir
do repositório, de `.env.production.example` ou do ambiente de desenvolvimento.

#### F2 — SHA em produção ✅

- Produção: `v2026.07.18-94f2765` (`94f27651`)
- Baseline da auditoria: `90f6a048` (**23 commits atrás**)
- `main` em 2026-07-20: `d08acfa5` (**33 commits à frente da baseline**)

Consequência: 3 de 12 achados reverificados já estavam corrigidos (25%). `M05-01` e
`M05-02` fechados em produção pelo `82dfa0f2` (#1567).

#### F3 — Censo de grupos ✅

Membros **ativos, não-superuser**, em produção:

| Grupo | Ativos |
|---|---:|
| Formador | 94 |
| Coordenador | 42 |
| Gerente | 9 |
| DAT | 3 |
| Controle | 1 |
| Superintendência | 1 |
| Assistente Administrativo | 1 |
| Diretoria | **0** |
| Apoio de Coordenação | **0** |

Total de usuários ativos: 148. **Superusers ativos: 1.**

Consequências:
- `M03-01` (P0) é **vivo e alcançável por 3 contas reais** do DAT — não é latente.
- Achados alcançáveis apenas por Diretoria ou Apoio de Coordenação **não têm ator hoje**.
- **Bus factor de 1 superuser.** Agravado pelo #1567, que tornou a administração de
  Grupo×Capability superuser-only. Se essa conta cair, ninguém administra RBAC.
  A auditoria já tinha isso como decisão pendente em M05 (superuser primário + backup).

#### F4 — Google Calendar ✅ ATIVO

- `GCAL_AUTH_MODE = oauth`
- `GCAL_CLIENT = google` (cliente real, **não** stub)
- `GCAL_ALLOWED_DOMAIN = aprendereditora.com.br`
- `GCAL_OAUTH_CLIENT_ID` preenchido (72 chars)
- `GCAL_OAUTH_CLIENT_SECRET` preenchido (35 chars)
- `GCAL_ENCRYPTION_KEY` preenchido (44 chars — tamanho de chave Fernet)
- `GCAL_OAUTH_REDIRECT_URI` preenchido (57 chars)
- `GCAL_CALENDAR_ID` preenchido (7 chars — compatível com `primary`)
- `GCAL_SERVICE_ACCOUNT_JSON` **não existe**

Consequência: os 13 achados de M12 que dependiam de OAuth ativo têm a premissa
**confirmada** — não são teóricos e **nenhum** é despriorizado. Destaque para `M12-15`
(state de OAuth de um usuário aceito no callback de outro) e para o uso do
`GCAL_CALENDAR_ID` global no cancelamento em vez do calendário do operador.

#### F1 — Porta 8000 ✅ (parcial)

O dono testou por **4G, fora da rede corporativa**: a porta **não responde**. A porta
está protegida por allowlist de firewall externo (Golden).

Refuta o achado `M27-05` como "exposição pública" — os probes anteriores rodaram de
dentro da rede allowlisted e concluíram além do que o ponto de observação sustentava.

O que **permanece** verdadeiro: `docker-compose.prod.yml:100-101` publica em `0.0.0.0`
sem bind em `127.0.0.1`, então o firewall externo é a **única** camada protegendo um
canal em texto claro que serve a API e o `/admin` do Django, fora do TLS e do `limit_req`.
Reclassificado P0 → **P2**, defesa em profundidade. Correção que preserva o consumidor
legítimo (`deployer/apply.sh:73-80` usa `confirm_localhost`):
`127.0.0.1:${BACKEND_HOST_PORT}:8000`.

#### Ainda não verificado

- **F5** — conteúdo real dos envs no Portainer, comparado 1-a-1 com o template. 18 achados
  dependem disso, e é o único fato com potencial de **promover** algo a P0 (ex.: `DEBUG=True`).
- **F7** — o beat roda? Existe backup restaurável? Se não houver, `M26-01` volta a P0.
  Precedente relevante: #1537, backup que nunca rodou.
- **F1 (resto)** — configuração do edge real. O Nginx Proxy Manager é **externo ao
  repositório** (`docker-compose.prod.yml:329-339`); se ele **anexa** `X-Forwarded-For` em
  vez de sobrescrever, `M01-01` e `M03-03` sobem para P1 (bypass remoto de lockout/throttle).
- **F6** — homônimos e duplicatas nos dados reais (`M02-09`, `M22-14`): dano atual ou preventivo?

---

## Por que este documento existe separado

O erro mais caro da auditoria não foi um achado errado — foi um achado **certo no mecanismo e
errado na consequência**, sustentado por uma premissa de ambiente que ninguém tinha medido.
O caso exemplar foi o `M27-05`: dois agentes concluíram "porta 8000 aberta na internet" a
partir de probes rodados de dentro da rede allowlisted. O dono refutou testando pelo 4G.

A lição vale para qualquer auditoria futura deste sistema:

- Confirmação por um segundo observador **do mesmo ponto de observação** não é independência.
- Premissa de ambiente não medida erra nos **dois** sentidos: inflou o `M27-05`, e teria
  deflacionado os 13 achados de GCal se alguém tivesse assumido stub por conveniência.
- Auditoria sobre codebase que recebe ~30 commits/mês nasce envelhecendo. Fixe o SHA no
  cabeçalho e revalide contra `HEAD` antes de publicar.
