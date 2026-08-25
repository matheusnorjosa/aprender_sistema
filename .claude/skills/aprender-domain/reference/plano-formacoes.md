# PlanoFormacoes (Regras de Negócio)

Estrutura de formações anuais por Município + Projeto.
**Arquivos**: `apps/core/models/plano_formacoes.py`, `formacao.py`, `acompanhamento.py`, `prova.py`

## FORM-01: Estrutura do Plano

**Model**: `PlanoFormacoes` (`apps/core/models/plano_formacoes.py`) — chave única `(municipio, projeto)`

**Relacionamentos**:
- 1 PlanoFormacoes → até 15 `Formacao` (via `related_name="formacoes"`)
- 1 PlanoFormacoes → até 2 `Acompanhamento` (via `related_name="acompanhamentos"`)
- 1 PlanoFormacoes → até 3 `Prova` (via `related_name="provas"`)

**Campos principais**:
- `municipio`: FK → Municipio (PROTECT)
- `projeto`: FK → Projeto (PROTECT)
- `coordenador`: FK → **Usuario** (SET_NULL, opcional) — a PESSOA que coordenou o evento, resolvida por CPF (#1849). NÃO é a lista de governança `DATCoordenador`
- `ano`: PositiveSmallIntegerField — dimensão temporal por ano (natural key `municipio+projeto+ano`)
- `ch_total`: DecimalField (soma das CH das formações)
- `ch_estudo`: DecimalField (CH adicional de estudo)
- `ch_anual`: DecimalField (ch_total + ch_estudo)
- `ativo`: BooleanField (soft delete)
- `created_by`, `updated_by`: FK → Usuario (auditoria)

**Methods/Properties**:
- `recalcular_ch()`: Recalcula CH baseado nas formações
- `total_formacoes`: Formações com data definida
- `formacoes_realizadas`: Formações com realizada=True
- `taxa_realizacao`: (realizadas/total) × 100

## FORM-02: Formação Individual

**Model**: `Formacao` (`apps/core/models/formacao.py`) — chave única `(plano, numero_formacao)`

**Campos**:
- `plano`: FK → PlanoFormacoes (CASCADE)
- `numero_formacao`: 1-15 (validators MinValue/MaxValue)
- `data_formacao`: DateField (nullable)
- `carga_horaria`: DecimalField (default 4.00h)
- `modalidade`: Enum (`presencial`, `online`)
- `horario_inicio`, `horario_fim`: TimeField (opcionais)
- `local_formacao`: CharField (endereço ou link)
- `formador_nome`: CharField
- `status`: Enum (`agendada`, `realizada`, `cancelada`, `reagendada`)
- `realizada`: BooleanField

**Properties**:
- `duracao_horas`: Calcula duração se horários definidos
- `modalidade_abrev`: "Pres." ou "Onl." para tabelas

## FORM-03: Acompanhamentos

**Model**: `Acompanhamento` (`apps/core/models/acompanhamento.py`) — chave única `(plano, tipo)`

**Campos**:
- `plano`: FK → PlanoFormacoes (CASCADE)
- `tipo`: Enum (`primeiro`, `segundo`)
- `data_acompanhamento`: DateField (nullable)
- `realizado`: BooleanField
- `observacoes`: TextField (max 500 chars)

**Property**: `numero` → 1 ou 2 (baseado no tipo)

## FORM-04: Provas

**Model**: `Prova` (`apps/core/models/prova.py`) — chave única `(plano, numero_prova)`

**Campos**:
- `plano`: FK → PlanoFormacoes (CASCADE)
- `numero_prova`: 1-3 (validators + CheckConstraint)
- `data_prova`: DateField (nullable)
- `realizada`: BooleanField
- `observacoes`: TextField (max 500 chars)
