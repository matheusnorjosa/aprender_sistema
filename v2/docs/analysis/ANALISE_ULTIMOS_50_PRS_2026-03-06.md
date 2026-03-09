# Analise dos Ultimos 50 PRs Mergeados

Data da analise: 2026-03-06
Escopo: ultimos 50 PRs mergeados em `main` no repositorio `matheusnorjosa/aprender_sistema`.

## Metodo de avaliacao
1. Coleta dos 50 PRs mergeados via GitHub CLI (`gh pr list --state merged --limit 50`).
2. Cruzamento com issues abertas/fechadas para verificar se referencias do PR estao resolvidas.
3. Sinal de regressao por revert explicito no historico (`git log --grep "Revert.*#PR"`).
4. Sinal de qualidade: presenca de evidencia de testes no corpo do PR e ausencia de checks required com falha/pending no snapshot atual.

## Resultado consolidado
- PRs analisados: **50**
- Alta confianca de resolucao: **33**
- Confianca media (referencia a issue fechada, sem `Closes` explicito): **9**
- Confianca media (sem referencia de issue): **7**
- Confianca media (referencia a issue ainda aberta): **1**
- PR com issue de fechamento explicita ainda aberta: **0**
- Sinal de revert explicito detectado: **0**
- PRs com evidencia de testes/validacao no corpo: **47/50**
- PRs sem evidencia explicita de testes no corpo: **3** (#773, #770, #760)

## Observacoes principais
- Nao foi encontrado PR mergeado recentemente com issue de fechamento explicita permanecendo aberta.
- O unico caso com referencia para issue aberta e o **PR #687**, que referencia a **#677** (canary xdist). Esse caso e esperado: #677 e uma trilha continua de evidencias e permanece aberta por desenho.
- PRs sem referencia de issue (ex.: #773, #770, #765) podem estar corretos tecnicamente, mas perdem rastreabilidade formal de objetivo.

## Casos de confianca media (requerem validacao humana de negocio)

### A) Referenciam issue fechada, mas sem `Closes` explicito
| PR | Titulo | Issues mencionadas |
|---|---|---|
| #769 | fix(rbac): alinhar dashboard de compras (DAT + Diretoria) (#565) | 565 |
| #768 | fix(security): restringe escopo da grade mensal sem gerencia_id (#567) | 567 |
| #751 | fix(security): validar redirect URI OAuth e magic bytes nos uploads (#746 #747) | 743,744,745,746,747,748,750 |
| #750 | fix(security): resposta de login uniforme contra account enumeration (#745) | 743,745,749 |
| #748 | fix(security): blindar aprovacoes de solicitacao contra race condition (#744) | 743,744 |
| #737 | bug(frontend-contract): align CurrentUser with /api/me contract | 699 |
| #736 | ci(api-contract): harden OpenAPI for critical frontend endpoints | 703 |
| #731 | test(frontend-contract): matriz funcional crítica no checklist (#705) | 705 |
| #718 | docs(compras): análise scripts Google Sheets e plano end-to-end | 712,713,714,715,716,717 |

### B) Sem referencia de issue
| PR | Titulo |
|---|---|
| #773 | fix(security): bump django-allauth para 65.14.1 (CVE-2026-27982) |
| #770 | fix(frontend): atualizar runtime alpine para destravar gate de release |
| #765 | feat(infra): Watchtower auto-deploy, /api/version/ endpoint e alinhamento 3-VMs |
| #760 | chore: stop tracking AGENTS.md files |
| #740 | ci(telemetry): estabilizar baseline com filtro main/push |
| #726 | ci(monitoring): reduzir falso positivo no runtime telemetry |
| #693 | ci(frontend): remove deps deprecated do lighthouse e fixar Chrome no CI |

### C) Referencia issue ainda aberta
| PR | Titulo | Issue aberta | Nota |
|---|---|---|---|
| #687 | ci(xdist): rastrear evidências do canary e backlog de estabilização | #677 | Epic/trilha continua (nao necessariamente falha do PR) |

## Recomendacao pratica
1. Padronizar todos os PRs com `Closes #issue` ou `Refs #issue` + criterio de aceite no corpo.
2. Manter comentario final de fechamento na issue com: "resultado esperado", "testes executados", "rollback".
3. Para PR sem issue (hotfix), abrir issue retroativa curta para rastreabilidade.
