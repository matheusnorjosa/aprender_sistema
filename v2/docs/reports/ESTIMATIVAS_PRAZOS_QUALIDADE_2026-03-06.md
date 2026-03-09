# Estimativas de Prazo por Fase - Plano de Qualidade do Sistema

Data: 2026-03-06
Base de referencia: backlog `v2/docs/reports/BACKLOG_QUALIDADE_SISTEMA_2026-03-06.md`.

## 1. Premissas de Estimativa

- Time minimo recomendado:
  - 2 engenheiros backend
  - 1 engenheiro frontend
  - 0.5 devops
  - 0.5 QA
- Capacidade media considerada: 80% (20% para interrupcoes, suporte e hotfix).
- Estimativas abaixo em dias uteis e janela de calendario.
- Dependencias tecnicas respeitadas (caminho critico no final do documento).

## 2. Estimativa por Issue

| Issue | Faixa (dias uteis) | Janela calendario estimada |
|---|---:|---|
| ASQ-001 | 3-5 | 1 semana |
| ASQ-002 | 2-4 | 0.5 a 1 semana |
| ASQ-003 | 2-3 | 0.5 semana |
| ASQ-004 | 5-8 | 1.5 semana |
| ASQ-005 | 6-10 | 2 semanas |
| ASQ-006 | 2-4 | 0.5 a 1 semana |
| ASQ-007 | 3-5 | 1 semana |
| ASQ-008 | 4-6 | 1 semana |
| ASQ-009 | 3-5 | 1 semana |
| ASQ-010 | 8-12 | 2 a 3 semanas |
| ASQ-011 | 6-10 | 2 semanas |
| ASQ-012 | 3-5 | 1 semana |
| ASQ-013 | 6-10 | 2 semanas |
| ASQ-014 | 5-8 | 1.5 semana |
| ASQ-015 | 4-6 | 1 semana |

## 3. Estimativa por Fase

| Fase | Issues | Faixa (dias uteis) | Duracao calendario estimada |
|---|---|---:|---|
| Fase 1 - Core backend | ASQ-001, ASQ-002, ASQ-003, ASQ-006, ASQ-008 | 13-22 | 2 a 3 semanas |
| Fase 2 - Carga pesada/Cache | ASQ-005, ASQ-007, ASQ-004 | 14-23 | 2.5 a 3.5 semanas |
| Fase 3 - Frontend sustain | ASQ-009, ASQ-010, ASQ-011 | 17-27 | 3 a 4 semanas |
| Fase 4 - Observabilidade/CI | ASQ-012, ASQ-015 | 7-11 | 1.5 a 2 semanas |
| Fase 5 - HA e consistencia | ASQ-013, ASQ-014 | 11-18 | 2 a 3 semanas |

## 4. Cronograma Geral (estimativa)

### Cenario realista (com paralelizacao parcial)
- Duracao total: 11 a 15 semanas.
- Sequencia recomendada:
  1. Fase 1
  2. Fase 2
  3. Fase 3
  4. Fase 4
  5. Fase 5

### Cenario acelerado (mais paralelizacao)
- Duracao total: 9 a 12 semanas.
- Requisitos:
  - backend e frontend executando trilhas em paralelo apos Fase 1.
  - devops antecipando ASQ-012 enquanto Fase 3 roda.

### Cenario conservador (com mudancas de escopo)
- Duracao total: 14 a 20 semanas.
- Causas comuns:
  - dependencias de negocio na ASQ-002.
  - retrabalho de UX no fluxo de import assyncrono (ASQ-005).
  - complexidade de operacao em HA/replicacao (ASQ-013/014).

## 5. Caminho Critico

1. ASQ-001
2. ASQ-002
3. ASQ-005
4. ASQ-004
5. ASQ-010
6. ASQ-013
7. ASQ-014

Qualquer atraso nesse caminho desloca o prazo final.

## 6. Marcos de Controle Recomendados

- Marco M1 (fim Fase 1): fluxos criticos backend estaveis e medidos.
- Marco M2 (fim Fase 2): sem processamento pesado no request thread.
- Marco M3 (fim Fase 3): frontend com arquitetura mais modular e tipada.
- Marco M4 (fim Fase 4): monitoracao e CI com guard rails de performance.
- Marco M5 (fim Fase 5): escala horizontal ativa com consistencia controlada.

## 7. Criterios para considerar o programa concluido

- 100% das issues ASQ-001 a ASQ-015 entregues com testes e criterios de aceitacao cumpridos.
- Nenhum gap critico remanescente no relatorio tecnico.
- SLOs acordados monitorados por dashboard e alerta.
- Documentacao atualizada com arquitetura final e runbooks.
