# DAT Module (Regras de Negócio)

O módulo DAT gerencia ações, cadastros, coordenadores e registros operacionais.
**Arquivos**: `apps/core/models/dat_*.py`

## DAT-01: Workflow de Ações (`DATAcao`)

**Model**: `DATAcao` (`apps/core/models/dat_acao.py`) — chave única: municipio + projeto + ano (`unique_dat_acao_municipio_projeto_ano`, `nulls_distinct=False`)

**Workflow de 4 etapas**:
1. **Carta** (`status_carta`, `data_carta`) - Envio de carta oficial
2. **Contato** (`status_contato`, `data_contato`) - Primeiro contato com município
3. **Reunião** (`status_reuniao`, `data_reuniao`) - Reunião de alinhamento
4. **Entrega** (`status_entrega`, `data_entrega`) - Entrega de materiais

**Status choices**: `pendente`, `em_andamento`, `concluido`, `cancelado`

**Properties**:
- `progresso`: 0-100% baseado em etapas concluídas
- `etapa_atual`: Nome da próxima etapa pendente

## DAT-02: Registros (`DATRegistro`)

**Model**: `DATRegistro` (`apps/core/models/dat_registro.py`) — chave única: municipio + projeto_geral + projeto + ano (`unique_dat_registro_municipio_projeto_ano`, `nulls_distinct=False`; `ano=None` é o bucket pendente)

**Seções**:
1. **Dados Básicos**: município, projeto, aluno_qtde, professor_qtde
2. **Plataforma FORMAR**: turma_id, nr_codigos, chaves, instruções, envio
3. **Plataforma AVALIAR**: recebidos, validados, importados

**Cálculo automático de códigos** (`save()` → `calcular_nr_codigos` em `apps/core/services/dat_codigos.py`):
`nr_codigos` é a SOMA, por compra ativa (`DATCompra`) do mesmo município + projeto com
`ano_uso == registro.ano` (cohort anual; `ano=None` conta só as compras `ano_uso IS NULL`),
de `codigos_da_compra` — `ceil` por compra, em `Decimal`:
```python
# Tipo: por_aluno (só compras de kit "Aluno")
codigos_da_compra = ceil(compra.quantidade / projeto_geral.divisor_aluno)

# Tipo: por_professor (só compras de kit "Professor")
codigos_da_compra = ceil(compra.quantidade * projeto_geral.multiplicador_professor)
```
Compras com `conta_para_codigos=False` não contam; `nao_aplicavel` dá `None`.
`aluno_qtde` / `professor_qtde` do registro NÃO entram na conta.

**Campo `usa_avaliar`**: Sincronizado automaticamente com `projeto_geral.usa_avaliar`

## DAT-03: Cadastros (`DATCadastro`)

**Model**: `DATCadastro` (`apps/core/models/dat_cadastro.py`) — chave única: municipio + projeto_geral + plataforma + ano (`unique_dat_cadastro_mun_proj_plat_ano`, `nulls_distinct=False`)
**Plataformas**: `FORMAR`, `AVALIAR`

**Workflow FORMAR** (4 etapas):
| Etapa | Status Field | Data Field | Qtde Field |
|-------|-------------|------------|------------|
| 1. Criação Curso | `status_criacao_curso` | `data_criacao_curso` | - |
| 2. Chaves | `status_chaves` | `data_chaves` | `quantidade_chaves` |
| 3. Instruções | `status_instrucoes` | `data_instrucoes` | - |
| 4. Envio | `status_envio` | `data_envio` | - |

**Workflow AVALIAR** (3 etapas):
| Etapa | Status Field | Data Field | Qtde Field |
|-------|-------------|------------|------------|
| 1. Recebidos | `status_recebidos` | `data_recebidos` | `quantidade_recebidos` |
| 2. Validados | `status_validados` | `data_validados` | `quantidade_validados` |
| 3. Importados | `status_importados` | `data_importados` | `quantidade_importados` |

**Status choices**: `pendente`, `em_andamento`, `concluido`, `erro`, `na`

**Properties**: `progresso_formar`, `progresso_avaliar`, `progresso`

## DAT-04: Coordenadores e Áreas

**Models**: `DATCoordenador`, `DATArea` (`apps/core/models/dat_coordenador.py`)
- `DATArea`: tabela de referência de áreas de atuação (nome, cor, ativo, ordem) — não guarda municípios
- `DATCoordenador`: cadastro autônomo do coordenador (nome, cpf, email, telefone, cargo,
  data_admissao, foto_url…); `area` é CharField livre. Sem FK para `DATArea` nem para o
  `Usuario` coordenado (as únicas FKs para `Usuario` são `created_by`/`updated_by`, de auditoria).
  **PII**: `cpf`, `email`/`email_alternativo`, `telefone`/`telefone_alternativo` — o CPF nunca é exposto em leitura.
