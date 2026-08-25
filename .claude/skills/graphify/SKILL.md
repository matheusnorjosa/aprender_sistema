---
name: graphify
description: "Build/query a navigable knowledge graph of a codebase. Use when onboarding to an unfamiliar codebase, answering cross-module how-does-X-relate-to-Y, or tracing dependencies before a refactor."
trigger: /graphify
---

# /graphify

Turn any folder of files into a navigable knowledge graph with community detection, an honest audit
trail, and three outputs: interactive HTML, GraphRAG-ready JSON, and a plain-language GRAPH_REPORT.md.

Three things it does that Claude alone cannot:
1. **Persistent graph** — relationships are stored in `graphify-out/graph.json` and survive across sessions. Ask questions weeks later without re-reading everything.
2. **Honest audit trail** — every edge is tagged EXTRACTED, INFERRED, or AMBIGUOUS. You know what was found vs invented.
3. **Cross-document surprise** — community detection finds connections between concepts in different files you would never think to ask about directly.

## Command surface

```
/graphify [<path>|<github-url> ...]   # build a graph (default path: current directory)
/graphify query "<question>"          # traverse the graph for an answer (--dfs, --budget N)
/graphify path "A" "B"                # shortest path between two concepts
/graphify explain "Concept"           # plain-language explanation of one node
/graphify add <url>                   # fetch a URL into ./raw, then update the graph
```

Build flags (combine freely): `--mode deep`, `--update`, `--directed`, `--cluster-only`, `--no-viz`,
`--svg`, `--graphml`, `--neo4j[-push <uri>]`, `--mcp`, `--watch`, `--wiki`, `--obsidian[-dir <path>]`,
`--branch <b>`, `--whisper-model <name>`. Multiple URLs build each repo and merge into one cross-repo
graph.

## Route by command

Pick the matching reference, then follow its steps in order. Do not skip steps.

- **Building a graph** (any `/graphify <path>` or `<github-url>`, with or without build flags) →
  `reference/build-pipeline.md` (Steps 0–9: clone, install, detect, transcribe, extract, build,
  cluster, label, export, report).
- **Querying an existing graph** (`query`, `path`, `explain`) → `reference/query-and-navigate.md`.
- **Keeping a graph current** (`--update`, `--cluster-only`, `add`, `--watch`, git hook, CLAUDE.md
  integration) → `reference/update-and-maintain.md`.

The interpreter resolved in build Step 1 is written to `graphify-out/.graphify_python`; every later
bash block uses `$(cat graphify-out/.graphify_python)` instead of `python3`. Query and maintenance
subcommands re-resolve it first if `graphify-out/` was deleted (guard in the reference files).

## Honesty Rules (apply to every branch)

- Never invent an edge. If unsure, use AMBIGUOUS.
- Never skip the corpus-size check warning (Step 2: >2M words or >200 files).
- Always show token cost in the report.
- Never hide cohesion scores behind symbols — show the raw number.
- Never run HTML viz on a graph with more than 5,000 nodes without warning the user.
