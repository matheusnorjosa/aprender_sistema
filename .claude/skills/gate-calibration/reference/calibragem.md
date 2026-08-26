# Os nove gates, e o número que decidiu cada calibragem

Registro de 2026-08 (PRs #1847 → #1870). A coluna que importa é a última: sem o
número medido, a calibragem seria chute.

| gate | sinal | medido | decisão |
|---|---|---|---|
| `check_doc_impact` d1 | issue resolvida × doc que a cita | `Closes #N` em 27,7% dos fixes | **bloqueia** — preciso e raro |
| `check_doc_impact` d2 | código × spec que o declara | dispara em **60%** dos commits, média 2,6 specs | **avisa** — bloquear trava o repo |
| `check_doc_impact` d3 | `sources_of_truth` encolhendo | 21/21 specs em drift; as verdes eram as que não declaravam nada | **bloqueia** sem justificativa |
| `check_doc_impact` d4 | status rebaixado | **zero** rebaixamentos em 60 commits | **bloqueia** sobre baseline limpo |
| `check_agent_instructions` | citação a caminho apagado | 12 achados, 2 reais (17%) → **83%** com o discriminador de git | **bloqueia** + allowlist |
| `check_adr_numbers` | número de ADR repetido | 1 colisão; `docs/` em 018 e `v2/docs/` já com 019 | **bloqueia** + allowlist de 1 |
| `check_required_checks` | rótulo `[required]` × ruleset | 19 declaram, 10 exigidos, **9 falsos** | **avisa** (conserto é de admin) |
| `check_required_checks` | context exigido sem job | **zero** hoje | **bloqueia** (trava merge; conserta no PR) |
| `check_doc_links` F.5 | caminho em crase que não resolve | 211 refs, 22 não resolvem, **~11 acionáveis** (50%) | **avisa** — abaixo da barra |
| `check_issue_drift` | issue fechada descrita como aberta | 146 citadas em 305 lugares; **59 suspeitas** após filtro | **ratchet** — nem bloqueia nem avisa |
| `doc_drift_report` | drift em repouso | 21/21 em drift, 95% recebem commit em 7 dias | **relatório** — barrar sempre = barrar sempre |

## Os três padrões que este repositório prova que funcionam

Não é opinião: é o histórico dos gates que pegaram e dos que não pegaram.

**Limpar primeiro, trancar depois com allowlist** — `check-no-legacy-js`. Usado
em `citacoes-apagadas-allowlist.txt` e `adr-numeros-allowlist.txt`. Toda entrada
carrega motivo; as temporárias dizem quando sair, e saíram (o Lote C removeu as
três dele no dia seguinte).

**Ratchet sobre piso medido** — cobertura vitest, subida 3× em 4 dias. Usado no
`check_issue_drift`. O piso é por raiz, e o gate imprime «aperte o piso» quando
a contagem cai. **Aperte no mesmo PR**: entre dois merges o piso ficou 27 com a
realidade em 22, e 5 vagas de folga não quebram nada visivelmente — que é o que
as torna o pior desfecho.

**Auto-teste com caso «baseline limpo passa»** — `test_rbac_lint.py`. Sem esse
caso o gate nasce vermelho e é desligado antes de pegar o primeiro caso novo.

## O que este repositório prova que NÃO funciona

- **`[required]` no nome sem estar no ruleset** — 9 de 19 jobs. O nome informa
  errado sobre a própria proteção, e ninguém tinha como saber sem abrir a config.
- **Cron** — `ci-runtime-telemetry` falhou 26 execuções consecutivas e ninguém
  viu, porque é `schedule`-only e não aparece em PR nenhum.
- **Path filter em check `[required]`** — deixa o check «Expected» eterno e trava
  merge. Escopo se resolve **dentro** do job.

> A conclusão prática para mantenedor solo: **bloqueio não é o que faz um gate
> pegar — formato é.** O único checkbox verificado por máquina do repo tem 100%
> de adesão em 25 de 25 PRs, com o gate fora do ruleset.

## Onde a saída de escape mora

Todo gate que bloqueia precisa de uma, senão vira imposto e é contornado por
fora. O contrato usado aqui:

```
doc-nao-afetada: <caminho> — <justificativa com ≥10 caracteres>
```

Regras que o mantêm honesto, todas testadas:

- só vale **fora** de comentário HTML — escondido não é revisável, e isso também
  impede que o texto-exemplo do template vire waiver automático em todo PR
- placeholder (`...`, `xxx`, `<motivo>`) não conta como justificativa
- a saída do gate **ensina** o formato, senão ninguém o encontra
