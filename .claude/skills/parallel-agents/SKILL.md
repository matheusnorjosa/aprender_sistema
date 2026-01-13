# Parallel Agents

Coordenar múltiplos subagents trabalhando em paralelo para acelerar resolução de problemas independentes.

## Conceito Central

> "Dispatch one agent per independent problem domain. Let them work concurrently."

## Quando Usar

### USE quando tiver:
- 3+ arquivos de teste falhando com causas distintas
- Múltiplos subsistemas quebrados independentemente
- Problemas que NAO requerem contexto compartilhado
- Investigações que não interferem entre si

### NAO USE quando:
- Falhas estão relacionadas (mesma root cause)
- Requer entendimento do sistema completo
- Estado compartilhado entre problemas
- Mudanças podem conflitar

## O Padrão de 4 Passos

### 1. Identificar Domínios Independentes

Agrupe falhas pelo que está quebrado:

```
Exemplo: 6 testes falhando
├── test_availability.py (3 falhas) → Domínio: Disponibilidade
├── test_approval.py (2 falhas)    → Domínio: Aprovação
└── test_gcal.py (1 falha)         → Domínio: Google Calendar
```

### 2. Criar Tasks Focadas

Cada agent recebe:
- **Escopo específico**: Apenas seu domínio
- **Goal claro**: O que significa "done"
- **Constraints**: O que NAO fazer
- **Output esperado**: Formato do deliverable

### 3. Dispatch em Paralelo

Use o Task tool com múltiplos agents simultaneamente.

Exemplo de prompt para cada agent:
```
Agent 1: "Fix availability tests. Arquivos: test_availability.py.
         Erro: timezone mismatch. NAO altere código de produção.
         Deliverable: testes passando."

Agent 2: "Fix approval tests. Arquivos: test_approval.py.
         Erro: permission denied. NAO altere models.
         Deliverable: testes passando."

Agent 3: "Fix gcal tests. Arquivos: test_gcal.py.
         Erro: mock não configurado. NAO altere services.
         Deliverable: testes passando."
```

### 4. Review e Integração

Após agents completarem:
1. **Verificar** que fixes não conflitam
2. **Rodar** testes abrangentes (todos juntos)
3. **Merge** mudanças
4. **Validar** CI passa

## Prompts Efetivos

### BOM Prompt
```
Fix os testes em test_availability.py.

Contexto:
- 3 testes falhando: test_check_overlap, test_block_total, test_buffer
- Erro comum: "AssertionError: timezone mismatch"
- Causa provável: datetime.now() vs America/Fortaleza

Constraints:
- NAO altere código de produção (apps/core/services/)
- NAO altere outros arquivos de teste
- USE freezegun para fixar tempo

Deliverable:
- Testes passando
- Commit com mensagem descritiva
```

### RUIM Prompt
```
Fix all tests.
```

## Pitfalls Comuns

| Pitfall | Solução |
|---------|---------|
| Assignment vago | Especificar arquivos e erros |
| Contexto faltando | Incluir mensagens de erro |
| Constraints indefinidos | Explicitar o que NAO fazer |
| Output ambíguo | Definir deliverable concreto |

## Exemplo Real

**Situação**: 6 falhas em 3 arquivos

**Dispatch**:
- Agent A: abort logic (test_abort.py)
- Agent B: batch completion (test_batch.py)
- Agent C: race conditions (test_race.py)

**Resultado**: 3 agents completaram simultaneamente, zero conflitos, tempo total = tempo do mais lento (não soma).

## Vantagens

- **Paralelização** acelera investigação
- **Escopo focado** reduz carga cognitiva
- **Independência** elimina interferência
- **Velocidade** = fração do tempo sequencial

## Integração com Projeto AS

Domínios comuns para paralelizar:
- Testes de **Disponibilidade** (RD-01~08)
- Testes de **Aprovação** (PA-01~07)
- Testes de **Google Calendar**
- Testes de **ETL/Ingest**
- Testes de **Frontend** (separado de backend)
