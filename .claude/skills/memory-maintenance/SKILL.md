---
name: memory-maintenance
description: Manter o dir de memórias (~/.claude/projects/.../memory/) e o índice MEMORY.md saudáveis — podar memória morta e corrigir o índice sem perder conhecimento. Use quando o dir inflar, o MEMORY.md encostar no cap de leitura (~24.4KB), ou você quiser limpar órfãs. Cobre a régua índice-vs-wikilink, a classificação A/B/C com grep -F, e o safety-grep obrigatório antes de deletar.
---

# Memory maintenance — podar morto, corrigir o índice, sem perder conhecimento

O dir de memórias acumula (sessões antigas, programas concluídos). Este skill limpa **com disciplina**:
provar que uma memória está morta antes de deletar, e nunca perder uma decisão que só vive ali.

## Régua central: índice-vs-wikilink (decide o que é ponteiro de índice)

- **Ponteiro de índice** (`[Título](arquivo.md)` no `MEMORY.md`) = **"preciso achar do zero, sem contexto"**:
  reference/decisão reusável, programa ativo, gotcha que morde em qualquer tarefa.
- **`[[wikilink]]` a partir de outra memória** = **"acho pelo tópico pai"**: nota de apoio niche (path de
  OS, snapshot de sessão, detalhe de um módulo) — encontrada **quando você está no assunto**.
- Só promove a índice o que merece **discoverability top-level**. Apoio fica linkado do contexto — não bloata.

## Fato central (contra-intuitivo — não erre isto)

**Deletar arquivo órfão limpa o DIR, NÃO encolhe o `MEMORY.md`.** O índice = as LINHAS de ponteiro;
órfã não tem linha. São DUAS limpezas:
- **Encolher MEMORY.md** exige remover LINHAS de índice (= dropar/deletar memória INDEXADA). As indexadas
  são as vivas → pouco a cortar sem perda. **~22KB é o piso honesto p/ ~250 memórias.**
- **Limpar o DIR** = deletar arquivos órfãos+mortos. Não mexe no índice.
- Re-indexar uma memória valiosa **CRESCE** o índice — e vale (corrige drop, preserva decisão). O objetivo
  é **índice honesto + dir sem lixo**, não "índice menor a qualquer custo".

## Procedimento

1. **Inventário.** `find <memdir> -maxdepth 1 -name "*.md" | wc -l` + `du -sh <memdir>`.
   ⚠️ `ls | wc -l` pode dar 1 (glitch RTK/glob) — use `find` ou Python.

2. **Classificar cada arquivo** (delegue a varredura de N arquivos a um agente com `grep -F`).
   ⚠️ **`grep -F` LITERAL** — os metacaracteres `()[]` de markdown/wikilink quebram regex e fazem
   TUDO parecer órfã. A forma wikilink = nome do arquivo com `_`→`-`.
   - **A INDEXADO**: `(arquivo.md)` OU `[[arquivo-com-hifen]]` aparece em `MEMORY.md`. → mantém.
   - **B CROSS-LINKADO só**: não no índice, mas OUTRA `.md` o cita. → **DEIXA** (alcançável); re-indexa
     só se for reference substancial reusável fora do contexto imediato.
   - **C ÓRFÃ TOTAL**: nem índice, nem cross-link, nem **handle nos CLAUDE.md** (checar os 3:
     `~/.claude/CLAUDE.md`, `<repo>/CLAUDE.md`, `<repo>/.claude/CLAUDE.md` — alguns são citados por handle
     tipo `pr-sweep-session-2026-06-16`). → candidata a deletar.

3. **Alvo em C = datadas-antigas-de-trabalho-concluído** (`*_session_*`, `*_2026_04/05/06_*` de programas
   fechados) cujo conteúdo foi absorvido por summaries indexados.

4. **Skim as que "carregam decisão" ANTES de deletar.** Se uma decisão específica só vive naquele arquivo
   (ex.: uma escolha de arquitetura, política de importer, credencial de teste), **RE-INDEXA em vez de
   deletar**. As decisões costumam estar em memórias `feedback_*` indexadas — confirme lá primeiro.

5. **Safety-grep OBRIGATÓRIO antes de `rm`** (é findings-crosscheck aplicado a remoção — o "0 refs" é uma
   afirmação a PROVAR):
   ```bash
   grep -rlF -e "arquivo.md" -e "[[arquivo-com-hifen]]" <memdir>/*.md <os 3 CLAUDE.md> | grep -v "^arquivo.md$"
   ```
   0 hits = safe. Faça isso para CADA candidata antes de apagar qualquer uma.

6. **Deleta as safe.** Depois **re-indexa os valiosos que caíram do índice** — um rewrite de compactação do
   MEMORY.md pode dropar uma reference viva (aconteceu com `plan-crosscheck`). Verifica no fim: nenhum
   ponteiro pendurado p/ arquivo deletado; cada re-indexado resolve para arquivo existente.

## Guardrails

- **Nunca deleta sem o safety-grep** (passo 5) — inclusive os 3 CLAUDE.md.
- **Nunca deleta uma decisão que só vive num arquivo** — re-indexa.
- A **decisão de deletar é do dono** para lotes grandes: classifica + traz a lista (nome · bytes · o que é),
  ordenada da mais-claramente-morta primeiro, e pede aprovação.
- Delegar a **classificação** (leitura larga de N arquivos) a um agente; a **decisão** fica com você/o dono.

## Precedente

2026-08-26: 267→254 memórias, DIR −92KB (13 datadas mortas deletadas após safety-grep), 7 valiosas
re-indexadas (corrigido um drop de compactação + preservadas decisões como D6/β-metrics do
`rbac_access_policy_realignment`). Conhecimento correlato: a memória `reference-memory-index-maintenance`
e o skill `findings-crosscheck` (mesma disciplina de "provar, não assumir").
