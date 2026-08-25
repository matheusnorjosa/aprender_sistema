# aprender_sistema

Instruções de projeto para agentes. As instruções detalhadas vivem em
`.claude/CLAUDE.md`; este arquivo cobre o que é da raiz do repositório.

## graphify — ferramenta sob demanda, não fonte canônica

Existe um grafo de conhecimento gerado em `graphify-out/`. Ele **não** é leitura
obrigatória, e não deve ser tratado como mapa de arquitetura.

> [!warning] Por que a instrução anterior foi removida
> Até 2026-08-25 este arquivo mandava ler `graphify-out/GRAPH_REPORT.md` antes de
> responder qualquer pergunta de arquitetura. A auditoria de 2026-08-24 mediu o
> custo dessa instrução:
>
> - **O grafo não está no git** (`.gitignore:619`). Em clone limpo ou CI, a
>   instrução apontava para o vazio.
> - **`graphify-out/wiki/index.md` não existe.** A regra mandava navegá-lo.
> - **Seis dos dez «god nodes»** que ele apresenta como *core abstractions* são
>   fixtures de teste (`factory_boy`). Quem obedecia concluía que o núcleo do
>   sistema são fábricas de teste.
> - **Sete cópias que se contradizem**, resolvidas pelo diretório de trabalho.
>   Uma é de 2026-04-29 — 347 commits atrás — e é a única sem carimbo de commit,
>   o que desliga a própria detecção de obsolescência da ferramenta.
> - O grafo lista `apps.dat_ingest` como comunidade viva. O módulo **foi
>   removido** no #971.
>
> Registro completo: `v2/docs/plans/PLAN_doc_drift_2026-08-25.md`, decisão D2.

**Quando usar.** Como ferramenta exploratória, ciente de que a saída pode estar
velha. Regenere antes de confiar:

```bash
graphify update .          # AST-only, sem custo de API
```

**Onde está a verdade de arquitetura.** Nas specs canônicas de `v2/docs/specs/`
(índice em `INDEX_SDD.md`) e, para estado de defeito, em
`v2/docs/audits/ACHADOS_REAIS.md`. Ver `.claude/CLAUDE.md`.
