# DAT Module (Regras de Negócio)

O módulo DAT gerencia ações, cadastros, coordenadores e registros operacionais.
**Arquivos**: `apps/core/models/dat_*.py`

## DAT-01: Workflow de Ações (`DATAcao`)

**Model**: `DATAcao` (`apps/core/models/dat_acao.py`) — chave única: municipio + projeto

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

**Model**: `DATRegistro` (`apps/core/models/dat_registro.py`) — chave única: municipio + projeto_geral + projeto

**Seções**:
1. **Dados Básicos**: município, projeto, aluno_qtde, professor_qtde
2. **Plataforma FORMAR**: turma_id, nr_codigos, chaves, instruções, envio
3. **Plataforma AVALIAR**: recebidos, validados, importados

**Cálculo automático de códigos** (`save()` override):
```python
# Tipo: por_aluno
nr_codigos = ceil(aluno_qtde / projeto_geral.divisor_aluno)

# Tipo: por_professor
nr_codigos = ceil(professor_qtde * projeto_geral.multiplicador_professor)
```

**Campo `usa_avaliar`**: Sincronizado automaticamente com `projeto_geral.usa_avaliar`

## DAT-03: Cadastros (`DATCadastro`)

**Model**: `DATCadastro` (`apps/core/models/dat_cadastro.py`) — chave única: municipio + projeto_geral + plataforma
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
- `DATArea`: Agrupa municípios por região (nome, descrição)
- `DATCoordenador`: Usuario responsável por área (FK → Usuario, FK → DATArea)
