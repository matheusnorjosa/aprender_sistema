# Roteiro: conferir as telas depois da carga da virada (#1900)

- **Para quê:** fechou a issue #1900 (Onda H, 09/11/2026). Depois de cada passo da carga, e no fim, as telas mostram o número certo.
- **Base:** commit `f72dc4ae` (09/11/2026). Caminhos relativos à raiz do repo; as linhas citadas (l.N) são desse commit e podem ter andado.
- **Fora do repo:** `ESTADO_*.md`, a `LISTA`, os scripts `*_ler.py` e os relatórios citados ficam na pasta de liberação do dono.
- **Quem roda:** o engenheiro. O dono lê a tabela de resultados (seção 6) e dá o OK de cada passo.

**Para o dono, em poucas linhas.** A carga entra em passos. Depois de cada passo eu conto no banco e abro as telas.
O número da tela tem de ser igual ao do banco e ao do relatório da carga. Se um número não bate, eu paro.
Nada é corrigido sem o seu OK. O evento de dois projetos aparece nos dois projetos, mas conta uma vez no total.

## 0. Preparação

1. Janela combinada, sem gente usando (`v2/docs/specs/backend/imports.spec.md` l.208). Backup < 24 h, dry-run verde e OK do dono antes de cada `--apply` (`.claude/CLAUDE.md`, "REGRA").
2. Contagens só por script de leitura no container web, no molde dos scripts `*_ler.py` da pasta de liberação. Saída só com números e `u<id>`/`s<id>`: nada de nome, CPF ou e-mail.
3. Rodar a `foto()` abaixo **antes** e **depois** de cada passo. Guardar nos relatórios da liberação, em `conferencia_telas_<passo>_<data>.txt`.
4. O "hoje" do Dashboard é o dia de Fortaleza desde o #2197 (`timezone.localdate()`, `views_dashboard.py`): a conta vale a qualquer hora.
5. Navegador: superusuário. Para os perfis, ver seção 3 (não precisa da senha de ninguém).

```python
# SÓ LEITURA. Saída sem dado pessoal.
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from apps.core.models import (Usuario, Produto, DATCompra, DATRegistro, EquipeGerencia,
                              Solicitacao, Participation, PlanoFormacoes, AvailabilityBlock,
                              Deslocamento, DATCadastro)
from apps.core.services.solicitacao_projetos import q_tem_projeto, contar_por_projeto
from apps.core.services.availability_service import ENFORCED_ROLES  # FORMADOR, COORD_ACOMPANHA
from apps.core.services.solicitacao_scope import scope_solicitacoes
from apps.core.rbac.policies import resolve_public_policies
S = Solicitacao.objects
def foto():
    hoje = timezone.localdate()  # o mesmo "hoje" do Dashboard (dia de Fortaleza)
    apr = S.filter(status="aprovado")
    return {
        "usuarios_ativos": Usuario.objects.filter(is_superuser=False, is_active=True).count(),
        "produtos": Produto.objects.count(),
        "vinculos_vigentes": EquipeGerencia.vigentes_em().count(),
        "compras": DATCompra.objects.count(),
        "compras_sem_produto": DATCompra.objects.filter(produto__isnull=True).count(),
        "pares_com_compra": DATCompra.objects.filter(ativo=True, quantidade__gt=0)
                              .values("municipio_id", "projeto_id").distinct().count(),
        "registros_sem_ano": DATRegistro.objects.filter(ano__isnull=True).count(),
        "eventos": S.count(),
        "por_status": dict(S.order_by().values_list("status").annotate(n=Count("id"))),
        "fila_pendentes": S.filter(status="pendente", projeto__fluxo__in=["SUPER", "NAO_SUPER"]).count(),
        "pendentes_sem_fluxo": S.filter(status="pendente").exclude(projeto__fluxo__in=["SUPER", "NAO_SUPER"]).count(),
        "aprovados_futuros": apr.filter(inicio__date__gte=hoje).count(),
        "formadores_aprovados": Participation.objects.filter(solicitacao__status="aprovado", usuario__isnull=False,
                                  role="FORMADOR").values("usuario_id").distinct().count(),
        "gcal": dict(apr.order_by().values_list("gcal_status").annotate(n=Count("id"))),
        "marca_fora_do_sistema": S.filter(publicado_fora_do_sistema=True).count(),
        "combos": S.filter(projeto_2__isnull=False).count(),
    }
print(foto())
```

## 1. Passo a passo da carga

Ordem da spec (`imports.spec.md` l.124-136 e l.206): contas → produto → compras → eventos (`solicitacao` + `participation`) → A5 → adoção do Google.
O `equipe_gerencia` não tem lugar escrito na spec. Uso a ordem do `ESTADO_2026-09-29.md` (l.227-229): depois das contas e antes das compras.
Em cada passo: **N do relatório = diferença da `foto()` = número da tela.** O dry-run espelha o apply (l.147, l.208).

### P1. Contas (`--allow-entity usuario`, execução própria; l.206)

| Tela (rota, página) | O que conferir | Conta no banco |
|---|---|---|
| Usuários (`/dat/admin/usuarios`, `UsuariosPage`) | Total da lista, filtro Situação = Ativo, sobe exatamente o `applied` de `usuario` | `foto()["usuarios_ativos"]` (o superusuário não aparece para o DAT: `views/admin.py` l.338-351) |
| Usuários, 3 contas novas por `u<id>` | Abrem; Setor = "Sem lotação" até o P3 (`UsuariosPage.tsx` l.253) | `EquipeGerencia.vigentes_em().filter(usuario_id=U).count() == 0` |

### P2. Produto (`--allow-entity produto`, sozinha; l.206, l.177-183)

| Tela | O que conferir | Conta no banco |
|---|---|---|
| Produtos (`/dat/admin/produtos`, `ProdutosPage`) | Total sobe `would_create` aprovado (57 menos os vetados; portão em l.183) | `Produto.objects.count()`; por projeto `Produto.objects.filter(projeto_id=P).count()` |
| Compras (`/controle/compras`) | Nada muda: a ligação compra→produto só acontece no P4 (l.153) | `foto()["compras_sem_produto"]` igual ao de antes |

### P3. Lotação (`--allow-entity equipe_gerencia`; l.140)

| Tela | O que conferir | Conta no banco |
|---|---|---|
| Usuários | Coluna Setor das contas com vínculo novo deixa de ser "Sem lotação" | `vinculos_vigentes` sobe o `applied` de `equipe_gerencia` |
| Grade Mensal (`/solicitacoes/disponibilidade`, `MonthlyPage`), gerência G, aba Formadores | Nº de pessoas da lista | `EquipeGerencia.vigentes_em().filter(gerencia_id=G, papel="FORMADOR").values("usuario_id").distinct().count()` (`monthly_grid_service.py` l.97-110; aba Coordenadores: `papel="COORDENADOR"`) |
| Usuários, cada `u<id>` de `lotacao_perdida_contas` | Conferir a lotação. A lista pode trazer conta a mais (seção 4) | — |
| (sem tela) | Nova fotografia das permissões: `rbac_diff --comparar` (LISTA item 28; `rbac.spec.md` l.158) | quem ganha/perde = só o esperado pelo P3 |

### P4. Compras (`--allow-entity dat_compra --as-user <cpf>`; l.206 passos 4-5, l.144-159)

| Tela | O que conferir | Conta no banco |
|---|---|---|
| Compras (`/controle/compras`, `ComprasPage`) | "Resultados: N registros" sem filtro; com filtro Projeto, para 3 projetos | `DATCompra.objects.count()`; `DATCompra.objects.filter(projeto_id=P).count()` |
| Compras | Compras sem produto caem em `would_ligar_produto` (soma do l.154 fecha) | `foto()["compras_sem_produto"]` |
| Painel de Compras (`/dashboards/compras`) | Linha "N com compra · M com evento · K pendentes" (`ComprasDashboardPage.tsx` l.611): N = M + K | N = `foto()["pares_com_compra"]` (`views/dat_module.py` l.648-736) |
| Mapa (`/mapa-brasil`), UF X, cartão "Compras" | Pares município × projeto com compra | `DATCompra.objects.filter(ativo=True, quantidade__gt=0, municipio__uf=X).values("municipio_id","projeto_id").distinct().count()` (`dat.spec.md`, item "DATCompra libera par") |
| Registros (`/dat/registros`), filtro Coleção F e Ano A | Soma da coluna Códs | `DATRegistro.objects.filter(projeto_geral_id=F, ano=A).aggregate(Sum("nr_codigos"))`; `registros_sem_ano` só o balde NÃO_CLASSIFICADAS (split, l.140 e l.167) |

### P5. Eventos (`--mode virada --apply --allow-entity solicitacao --allow-entity participation`, **sem `--as-user`**; l.206-219)

| Tela | O que conferir | Conta no banco |
|---|---|---|
| (relatório) | `virada_aplicada` = `por_entidade.solicitacao.virada` do dry-run (l.208) | — |
| Dashboard (`/dashboards`) | Eventos Futuros, Aprovados, Total Formadores, Aprovações Pendentes | `aprovados_futuros`, `por_status["aprovado"]`, `formadores_aprovados`, `por_status["pendente"]` (`views_dashboard.py` l.68-85) |
| Aprovações (`/solicitacoes/aprovacoes`), Pendentes, superusuário | Total da lista. Sobe `super_volta_pendente` + novos pendentes; cai os `cancelado_vira_reprovado` que estavam pendentes (l.214) | `foto()["fila_pendentes"]` (`views_solicitacao.py` l.525-539) |
| Pré-agenda (`/controle/pre-agenda`) | Total da lista de Solicitações | `por_status["aprovado"]` (`views_preagenda.py` l.39-58) |
| Painel do Google (`/dashboards/gcal`) | 4 contadores no período padrão (hoje −30 a +30 dias, `GCalDashboardPage.tsx` l.198-199) | `S.filter(status="aprovado", inicio__date__range=(d0, d1)).values("gcal_status").annotate(n=Count("id"))` |
| Grade Mensal, 3 formadores (`u<id>`), 2 dias cada | Eventos listados na célula do dia, no dia certo de Fortaleza (H.3a da issue) | `S.filter(status="aprovado", participations__role__in=ENFORCED_ROLES, participations__usuario_id=U, inicio__lt=fim_dia, fim__gt=ini_dia).distinct().count()` (`monthly_grid_service.py` l.152-163) |
| Meus Eventos (`/solicitacoes/meus-eventos`) da formadora Y | Total da lista | `S.filter(Q(participations__role__in=["FORMADOR","COORD_ACOMPANHA","CONVIDADO"]) \| Q(coordenador_id=Y) \| Q(coordenador__isnull=True, usuario_id=Y), participations__usuario_id=Y, status="aprovado").distinct().count()` (`views/me.py` l.87-101) |
| Minhas Solicitações (`/solicitacoes/minhas`) da coordenadora X | Total e futuros | `S.filter(usuario_id=X).count()`; futuros `+ .filter(inicio__gte=timezone.now())` (`views_solicitacao.py` l.477-480) |
| Por projeto e coleção, contra a planilha (H.1 da issue) | Para 5 projetos: eventos não reprovados no sistema = linhas do `solicitacao.csv` do pacote com o projeto e `cancelado` falso | `S.filter(q_tem_projeto(pk=P)).exclude(status="reprovado").count()`; coleção: `q_tem_projeto(projeto_geral_id=F)`. A diferença só pode vir dos contadores do relatório (`data_suspeita`, `fora_do_escopo`, `existente_fora_do_csv`, rejeitos) |
| Combos | Sobe `conjunto_criado` + `conjunto_preenchido`, no máximo 26 (l.211) | `foto()["combos"]` |

**Planos fora deste passo.** O passo "o evento aprovado aparece em Planos" (H.3 da issue) saiu: aprovar evento não alimenta o Plano Anual, por desenho; o dono fechou a #1900 sem ele (09/11/2026).

A Grade é renovada por um `invalidate_availability_cache(None)` no commit (l.218). Número velho na tela: recarregar antes de anotar divergência.

### P6. A5: o "Sistema" aprova o que a planilha aprovou (LISTA item 29; `imports.spec.md` l.214)

| Tela | O que conferir | Conta no banco |
|---|---|---|
| Aprovações, Pendentes | Cai o número de eventos que o script aprovou | `S.filter(status="pendente", projeto__fluxo="SUPER").count()` |
| Dashboard, Pré-agenda, Grade | "Aprovados" sobe o mesmo número; os eventos aparecem na Grade dos formadores | mesmas contas do P5 |

### P7. Adoção do Event ID (`conferir_gcal_adocao` → dry-run → `--apply --allow-entity gcal_adocao --gcal-verificado`; l.221-227)

| Tela | O que conferir | Conta no banco |
|---|---|---|
| Painel do Google | "Publicado" sobe o nº de adotados | `S.filter(status="aprovado", gcal_status="PUBLISHED").count()` |
| Pré-agenda, 3 `s<id>` adotados | Tag "Publicado" no lugar de "Na agenda pela planilha" (`pages.spec.md` l.296) | `foto()["marca_fora_do_sistema"]` cai o mesmo nº |
| Publicar (`/solicitacoes/publicacao`) | O adotado oferece Atualizar. Nada vai ao Google sozinho (l.221) | — |

### Se outras entidades entrarem na carga

| Entidade | Tela | Conta no banco |
|---|---|---|
| `plano_formacao` (+ `formacao`, `acompanhamento`, `prova`) | Plano Anual, filtro ano A: total e coluna Progresso (`pages.spec.md` l.302-304) | `PlanoFormacoes.objects.filter(ano=A).count()` |
| `availability_block` | Bloqueios (`/solicitacoes/bloqueios`) e Grade | `AvailabilityBlock.objects.filter(status="aprovado", usuario_id=U).count()` |
| `deslocamento` | Deslocamentos (`/solicitacoes/deslocamentos`) e Grade | `Deslocamento.objects.filter(usuario_id=U).count()` |
| `dat_registro`, `dat_cadastro` | Registros (`/dat/registros`), Cadastros (`/dat/cadastros`) | `DATRegistro.objects.filter(ano=A).count()`; `DATCadastro.objects.filter(ano=A).count()` |

## 2. Conferência entre telas (no fim, e depois do P5)

| # | O mesmo número | Telas | Regra |
|---|---|---|---|
| X1 | Aprovados | Dashboard "Aprovados" = total da Pré-agenda = soma dos 4 contadores do Painel do Google sem filtro de data | os três leem `status="aprovado"` sem escopo |
| X2 | Pendentes | Dashboard "Aprovações Pendentes" = Aprovações (superusuário) + `pendentes_sem_fluxo` | `pendentes_sem_fluxo` deve ser 0 (0 de 3.260 sem projeto em 28/10: `solicitacao-approval.spec.md` l.69) |
| X3 | Eventos por UF | Soma do "Total de Eventos" das UFs do Mapa = `S.exclude(municipio__isnull=True).count()` | o Mapa conta todos os status (`map_metrics.py` l.264, l.335-343) |
| X4 | Compras | Mapa: soma das UFs no cartão "Compras" = "N com compra" do Painel de Compras | a mesma lista de pares (`dat.spec.md`) |
| X5 | Grade × Meus Eventos | Para a formadora Y no mês M: eventos da Grade ≤ eventos de Meus Eventos no mês | Meus Eventos soma CONVIDADO e o responsável |
| C1 | Combo no total | Total de eventos, Dashboard, Mapa: o combo conta **uma** vez | FK, sem `distinct` (PA-04, adendo dois projetos, `politica-aprovacao.spec.md` l.97) |
| C2 | Combo por projeto | Soma dos projetos (top do Mapa) = `S.filter(projeto__isnull=False).count() + foto()["combos"]` | `sum(v["count"] for v in contar_por_projeto(S.all()).values())` |
| C3 | Filtro pelo 2º projeto | Projeto B filtrado no Mapa, na Grade e na busca do Painel do Google acha o evento "A / B" | `S.filter(q_tem_projeto(pk=B)).count()` |
| C4 | Rótulo | Minhas, Aprovações e Pré-agenda mostram "A / B" na ordem das vagas. Petrolina: `MIUDEZAS / UNI DUNI TÊ` (`gcal.spec.md` l.88) | `rotulo_dos_projetos` (`solicitacao_projetos.py` l.68-76) |
| C5 | Compra × combo | Par (município, B) com compra não fica pendente no Painel de Compras se há evento "A / B" no município | `q_tem_projeto` nas pendências (`dat_module.py` l.674-690) |
| C6 | Regra 2 intacta | Escopo e aprovação leem só a vaga 1; seguro só se gerência e fluxo forem iguais | `S.filter(projeto_2__isnull=False).exclude(projeto__gerencia_id=F("projeto_2__gerencia_id")).count() == 0`; idem com `projeto__fluxo=F("projeto_2__fluxo")` |

## 3. Por perfil

Como conferir sem a senha da pessoa: Usuários → abrir a conta → "O que vê no menu hoje" (`UsuariosPage.tsx` l.1107; `rbac.spec.md` l.97).
No banco: `resolve_public_policies(u)` e `scope_solicitacoes(S.all(), u).count()`. (Pode gravar cache do Redis; não grava no banco.)
Login real só com conta de teste da gerência isolada (receita citada na issue, comentário de 16/10).
Poder só da lotação: `RBAC_FONTE=lotacao` (`rbac.spec.md` l.114). Escopo = gerência do **projeto** (l.117).

| Perfil | De onde vem o poder | Deve ver | Não deve ver | Conta objetiva |
|---|---|---|---|---|
| Superusuário | `is_superuser` (`rbac.spec.md` l.111, l.150) | Tudo, inclusive `/dat/importacoes` e `/dat/admin/equipe-gerencia` (`AppRoutes.tsx` l.71, l.151, l.159) | — | Aprovações = `fila_pendentes` |
| DAT | Vínculo EQUIPE/GERENTE na gerência DAT → pacote `ADMIN_OPERACIONAL` (l.129; `services/rbac_pacotes.py`) | Admin DAT, Registros, Cadastros, Compras, Painel de Compras, Mapa, Grade, Aprovações (qualquer gerência e fluxo, l.128), Pré-agenda, Plano Anual, Painel do Google, Nova/Minhas | `/dashboards` (sem `view_overview_dashboard`), Publicar, Importações, conta do superusuário | `scope_solicitacoes(...)` = `S.count()` (global) |
| Controle | Vínculo EQUIPE/GERENTE na gerência CONTROLE → pacote `CONTROLE` (l.128) | Aprovações (qualquer evento), Compras, Pré-agenda, Plano Anual, Controle, Grade, Painel do Google, Pendências de compras (`/dashboards/compras` só com a lista de pendências, `view_compras_pendencias`; decisão do dono de 09/11/2026) | Admin DAT, Mapa, `/dashboards`, os blocos agregados do Painel de Compras (pedem `view_compras_dashboard` ou `manage_admin_registries`, `rbac/policies.py` l.144) | global, como o DAT |
| Gerente da Superintendência | Papel GERENTE vigente na `SUPERINTENDENCIA` (l.128) | Aprovações: decide só SUPER da Superintendência (PA-02, `politica-aprovacao.spec.md` l.82); vê o resto com "Fora do que você aprova" (`pages.spec.md` l.260); Nova/Minhas; Grade | Compras, Controle, Admin DAT, Mapa, Painel do Google | decidíveis ≤ `S.filter(status="pendente", projeto__fluxo="SUPER", projeto__gerencia__nome="SUPERINTENDENCIA").count()` |
| Coordenadora | Papel COORDENADOR vigente em G: criar e editar (`DIREITOS_PAPEL`, l.116) | Nova (só projetos de G, l.117), Minhas, Grade (só gerências G/C/A, `pages.spec.md` l.276), Bloqueios, Deslocamentos, Meus Eventos | Aprovações, Compras, Controle, Admin DAT, Publicar (só APOIO) | `scope_solicitacoes(S.all(), u).count() == S.filter(usuario=u).count()` |
| Formadora | Papel FORMADOR: nenhum direito de evento (l.116) | Meus Eventos, Bloqueios (os próprios), Perfil | Nova, Minhas, Grade (FORMADOR sozinho é recusado, `pages.spec.md` l.276), Deslocamentos | Meus Eventos = conta do P5 |

## 4. Limites conhecidos (olhar no ensaio e na carga)

| Limite | Onde está escrito | O que fazer |
|---|---|---|
| Lista do lote B (`solicitante_cpf_sem_cadastro_eventos`) pode trazer evento que não nasceria por outro motivo (apagado, fim antes do início) | `imports.spec.md` l.140 (`solicitacao`) | Conferir cada `evento_id` contra esses motivos no ensaio |
| `lotacao_perdida_contas` pode trazer conta que não perderia nada | l.140 (`equipe_gerencia`) | Erro para o lado seguro; conferir no form de Usuários |
| Petrolina: gêmeos EV001469–71 × EV003557–59 | `ESTADO_2026-09-29.md` l.246; `combo_2036_sem_principal_2026-11-08.md` (relatórios da liberação) l.232 | Decidir no ensaio, antes do P5. Miudezas fica na vaga 1, UNI DUNI TÊ na 2 (l.211); conferir `conjunto_preenchido_sobre_trava` |
| Evento que a carga não completa como combo (`conjunto_nao_aplicado:*`, `conjunto_nao_resolve`, `conjunto_invalido`) | l.191, l.211 | Vai para a lista do dono; completar é passo à parte, com OK |
| Linha com data suspeita fica toda de fora | l.212 | Conferir os `s<id>` de `virada.data_suspeita` |
| Evento que saiu da planilha não é reprovado pela carga | l.219 | Script à parte, com a lista conferida |
| COORDENADOR que não é o dono não aparece em Meus Eventos; evento importado não ocupa a agenda do responsável | l.202; l.140 (`coordenador_acompanha` = False) | Não é divergência na Grade nem em Meus Eventos |
| Papel do bloqueio medido hoje; nomes antigos de coleção podem dar `projeto_nao_resolvido` no portão dos 57 | `ESTADO_2026-09-29.md` l.232-233 | Medir de novo no dia da carga |
| Combo com fluxo diferente falharia aberto (vaga 1 NAO_SUPER, vaga 2 SUPER) | `politica-aprovacao.spec.md` l.97 | Conta C6 tem de dar 0 |

## 5. Regra de parada

- Qualquer número que não bate (tela × banco × relatório) **para o próximo passo da carga**.
- Investigar só com leitura. Anotar a hipótese na tabela.
- **Nenhum data-fix sem o OK do dono.** Correção é passo à parte, com ensaio.
- Recomeçar só com a linha da tabela fechada e o OK registrado.

## 6. Registro dos resultados

Salvar nos relatórios da liberação, em `conferencia_telas_virada_<data>.md`. Uma linha por conferência.

| Passo | Tela (rota) | Perfil | Esperado (relatório) | Banco (ORM) | Tela | Bate? | Observação / `s<id>` `u<id>` | OK do dono |
|---|---|---|---|---|---|---|---|---|
| P1 | `/dat/admin/usuarios` | superusuário | | | | | | |
| P2 | `/dat/admin/produtos` | superusuário | | | | | | |
| … | | | | | | | | |
| X1 | Dashboard × Pré-agenda × Painel do Google | superusuário | — | | | | | |

A conferência fecha com todas as linhas "Bate? = sim", as seções 2 e 3 completas e o resumo para o dono no `ESTADO`.
