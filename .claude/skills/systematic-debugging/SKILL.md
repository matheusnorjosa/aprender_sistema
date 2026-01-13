# Systematic Debugging

Debug estruturado em 4 fases obrigatórias. **NUNCA** tente fix sem investigar root cause primeiro.

## Regra de Ouro

> "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST"

Fixes baseados em sintomas mascaram problemas e desperdiçam tempo.

## As 4 Fases Obrigatórias

### Fase 1: Investigação de Root Cause

1. **Examinar** mensagens de erro completamente
2. **Reproduzir** o problema consistentemente
3. **Revisar** mudanças recentes (git log, git diff)
4. **Coletar** evidências diagnósticas nos limites dos componentes
5. **Rastrear** fluxo de dados backward para identificar origem

```bash
# Comandos úteis
git log --oneline -20
git diff HEAD~5
docker compose logs backend --tail=100
```

### Fase 2: Análise de Padrões

1. **Localizar** código similar que funciona
2. **Estudar** implementações de referência completamente
3. **Catalogar** TODAS as diferenças entre funcionando vs quebrado
4. **Entender** dependências e assumptions

```bash
# Buscar implementações similares
grep -r "pattern_similar" apps/
```

### Fase 3: Hipótese e Teste

1. **Formular** hipótese específica sobre root cause
2. **Testar** com mudanças MÍNIMAS
3. **Verificar** resultados
4. **Iterar** APENAS se hipótese falhar

**REGRA**: Nunca adicionar múltiplos fixes simultaneamente!

### Fase 4: Implementação

1. **Escrever** teste que falha primeiro (TDD)
2. **Implementar** fix ÚNICO e direcionado ao root cause
3. **Verificar** que solução funciona
4. **Se 3+ fixes falharem** → PARAR e questionar arquitetura

## Red Flags - Você Está Pulando o Processo

- [ ] Tentando quick fix antes de investigar
- [ ] Mudando múltiplas variáveis ao mesmo tempo
- [ ] Pulando criação de teste
- [ ] Fazendo tentativas repetidas sem reconsiderar approach

## Quando 3+ Fixes Falham

**PARE IMEDIATAMENTE.**

Isso sinaliza que o design pattern pode estar fundamentalmente errado. Inicie discussão arquitetural:

1. O modelo de dados está correto?
2. A abstração faz sentido?
3. Estamos lutando contra o framework?
4. Precisa de refactor antes de fix?

## Métricas de Sucesso

| Approach | Tempo Médio | Taxa 1º Fix |
|----------|-------------|-------------|
| Sistemático | 15-30 min | 95% |
| Trial & Error | 2-3 horas | 40% |

## Exemplo de Uso

```
Problema: Teste test_availability_check falha intermitentemente

Fase 1 - Investigação:
- Erro: "AssertionError: expected 0 conflicts, got 1"
- Reproduz: ~30% das vezes
- Mudanças recentes: PR #380 alterou timezone handling
- Evidência: Falha mais comum às 00:00-01:00 UTC

Fase 2 - Padrões:
- Código similar em test_solicitacao.py funciona
- Diferença: test_availability usa datetime.now() vs fixture

Fase 3 - Hipótese:
- "datetime.now() causa race condition em boundary de dia"
- Teste: Fixar datetime com freezegun
- Resultado: 100% passa

Fase 4 - Implementação:
- Teste: test_availability_timezone_boundary
- Fix: Usar freezegun em todos os testes de availability
- Verificação: 50 runs sem falha
```

## Integração com Projeto AS

Para bugs em:
- **Disponibilidade (RD-01~08)**: Verificar timezone America/Fortaleza
- **Aprovação (PA-01~07)**: Verificar permissões RBAC
- **Google Calendar**: Verificar tokens e rate limits
- **ETL**: Verificar idempotência e rollback
