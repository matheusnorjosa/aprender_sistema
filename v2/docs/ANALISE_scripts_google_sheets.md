# Análise: Scripts Google Sheets → Backend ETL → Gaps → Plano

**Data**: 2026-02-27
**Autor**: Claude Code (análise automatizada)
**Contexto**: Mapeamento das automações Google Apps Script das planilhas legadas para identificar regras de negócio, lacunas no sistema e plano de migração.

---

## 1. Visão Geral das Planilhas

O sistema legado é composto por **3 planilhas Google Sheets** com **11 scripts Apps Script** que gerenciam o fluxo completo: compras → agenda → disponibilidade → Google Calendar.

### Fluxo Legado

```
Planilha de Controle (compras/ações DAT)
        ↓
Planilha de Acompanhamento de Agenda
  (municípios com compra → solicitação manual de evento)
        ↓  MonitorarAgenda.js
Planilha de Disponibilidade
  (grade visual por formador)
        ↓  AgendaAutomation.js
Google Calendar
```

**Regra de negócio central**: apenas municípios que realizaram compras aparecem na Planilha de Acompanhamento de Agenda. Esta é a porta de entrada para criação de eventos.

---

## 2. Mapeamento Script por Script

---

### 2.1 `Acompanhamento de Agenda/AgendaAutomation.js`

**Planilha**: "Novo Google Agenda"
**Aba**: aba principal + "Relatórios"

#### Estrutura de Colunas

| Coluna | Índice | Nome | Equivalente no Sistema |
|--------|--------|------|------------------------|
| A | 0 | DELETE | flag de exclusão |
| B | 1 | UPDATE | flag de processamento |
| C | 2 | TITLE | `Solicitacao.titulo` |
| D | 3 | START_DATE | `Solicitacao.data_inicio` |
| E | 4 | END_DATE | `Solicitacao.data_fim` |
| F | 5 | START_TIME | hora início |
| G | 6 | END_TIME | hora fim |
| M | 12 | DESCRIPTION | `Solicitacao.descricao` |
| N | 13 | LOCATION | `Solicitacao.local` |
| P | 15 | GUESTS | emails convidados (campo ausente no sistema) |
| Q | 16 | EVENT_ID | `Solicitacao.gcal_event_id` |
| S | 18 | MEET_FLAG | `'s'` = criar Google Meet |
| T | 19 | COLOR | cor do evento no GCal |
| V | 21 | STATUS_PROCESSAMENTO | `AuditLog` |

#### Regras de Negócio

- **Parsing de título**: extrai `ADIADO`/`CANCELADO`, município, tipo de série, programa entre colchetes `[ACERTA LP]`
- **MEET_FLAG**: coluna S = `'s'` → cria Hangouts Meet automaticamente
- **Idempotência**: EVENT_ID armazenado → update, sem ID → create
- **Conflito automático**: edição de data/hora/formador dispara revalidação
- **Timezone fixo**: `America/Fortaleza` (UTC-3)
- **Cores do evento**: Basil, Blueberry, Flamingo, Banana, Tangerine, Peacock, Graphite, Lavender, Sage, Grape

#### Status de Implementação no Sistema

| Regra | Status |
|-------|--------|
| Criação/update/delete no GCal | ✅ `preagenda_to_gcal` |
| Google Meet automático | ✅ implementado |
| Timezone `America/Fortaleza` | ✅ RD-06 |
| STATUS_PROCESSAMENTO | ✅ `AuditLog` |
| Campo GUESTS (emails convidados) | ❌ não existe em `Solicitacao` |
| Cores do evento | ❌ não existe em `Solicitacao` |

---

### 2.2 `Acompanhamento de Agenda/Validar_duplicidade.js`

**Planilha**: "Acompanhamento de Agenda"
**Aba**: principal

#### Colunas

| Coluna | Campo |
|--------|-------|
| H | Data |
| I | Hora Início |
| J | Hora Fim |
| O-S | Formadores 1-5 (nome texto) |

#### Regras de Negócio

- Mesmo formador + mesma data + horários sobrepostos → conflito
- Fórmula: `início_A < fim_B AND fim_A > início_B`
- Status `"SOLICITADO"` = formador pendente → ignorado na validação
- Conflito: destaca célula em `#FF6545` + nota de aviso

#### Status de Implementação

| Regra | Status |
|-------|--------|
| Detecção de sobreposição | ✅ `availability_service.py` (RD-01) |
| Status "SOLICITADO" | ✅ `status='pendente'` em `Solicitacao` |
| Múltiplos formadores (até 5) | ⚠️ verificar se o sistema suporta múltiplos participantes |

---

### 2.3 `Acompanhamento de Agenda/LimparNomeProjeto.js`

**Planilha**: aba "Configurações"

#### Projetos Mapeados (remover prefixo "2026 ")

```
A Cor da Gente · ACerta · Brincando e Aprendendo · Cataventos · CIRANDAR
Educação Financeira · Escrever Comunicar e Ser · Fluir das Emoções (Nível 1/2/3)
GESTÃO ESCOLAR · Lendo e Escrevendo · Ler Ouvir e Contar · Novo Lendo
Projeto AMMA · Projeto AMMA e Novo Lendo · Sou da Paz
Superativar (Linguagens / Matemática) · Avançando Juntos (LP / Linguagens / Matemática)
TEMA · Uni Duni Tê · Vida & Ciências · Vida & Linguagem · Vida & Matemática
```

#### Risco ETL

> Se qualquer CSV exportado das planilhas trouxer nomes de projeto com prefixo `"2026 "`, o lookup por FK em `Projeto` vai falhar silenciosamente e o registro é rejeitado.

#### Status de Implementação

| Regra | Status |
|-------|--------|
| Normalização de nomes de projeto | ❌ ETL não faz strip do prefixo "2026 " |
| Projetos no modelo `Projeto` | ✅ existem, mas nomes exatos precisam ser verificados |

---

### 2.4 `Disponibilidade/form_bloqueio_back.js`

**Planilha destino**: ID `1WzFcU7VoDibblWGWBnDcPbsN095iYqrEBWyLtTpq8Ks` → aba "Bloqueios"
**Planilha usuários**: ID `1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI` → aba "Ativos"

#### Campos do Formulário de Bloqueio

| Campo | Equivalente no Sistema |
|-------|------------------------|
| `usuario` (nome) | `AvailabilityBlock.formador` |
| `email` | `AvailabilityBlock.formador.email` |
| `inicio` (YYYY-MM-DD) | `AvailabilityBlock.data_inicio` |
| `fim` (YYYY-MM-DD) | `AvailabilityBlock.data_fim` |
| `tipo` (Total/Partial/Buffer) | `AvailabilityBlock.tipo` → RD-02/03/04 |

#### Regras de Negócio

- Filtra apenas **Coordenadores** e **Formadores** do setor **Superintendência**
- Envia email de confirmação com datas formatadas (DD/MM/YYYY)

#### Status de Implementação

| Regra | Status |
|-------|--------|
| Bloqueios Total/Parcial/Buffer | ✅ RD-02, RD-03, RD-04 |
| `BLOQUEIOS_pronto.csv` → ETL | ✅ `etl_import_bloqueios` |
| Filtro apenas Superintendência | ⚠️ limitação da planilha, não regra de negócio — sistema suporta qualquer formador |

---

### 2.5 `Disponibilidade/MonitorarAgenda.js`

**Fluxo**: Lê aba **"Super"** do Acompanhamento → Grava em aba "Eventos" da Disponibilidade

#### Esta é a conexão crítica entre planilhas

```
Planilha Acompanhamento (aba "Super")
         ↓  importarEventosParaPlanilha()
Planilha Disponibilidade (aba "Eventos")
```

#### Mapeamento de Colunas (16 colunas importadas)

- Colunas 1,2 → identidade do evento
- Colunas 5-12 → data, hora, formador
- Colunas 14-19 → dados adicionais
- **Coluna R calculada**: `MIN(horas_trabalhadas, 8h)` — limite de 8h/dia por formador

#### Observação Importante

A aba **"Super"** é específica para projetos vinculados à **Superintendência** (fluxo SUPER). Outros projetos ficam em abas separadas (fluxo NAO_SUPER). O ETL atual trata os dois fluxos via `PA-01`/`PA-04`.

#### Status de Implementação

| Regra | Status |
|-------|--------|
| Limite 8h/dia por formador | ✅ RD-05 (`limite_diario`) |
| Diferenciação SUPER/NAO_SUPER | ✅ PA-01/PA-04 |
| Grade de disponibilidade visual | ✅ `Disponibilidade/` frontend |

---

### 2.6 `Planilha de Controle/Código.js`

**Planilha**: Planilha de Controle
**Abas**: `⚙️ CONFIG`, `ℹ️ DAT`, `☑️ CADASTROS`, `ℹ️ FILTRO_PROD.`, `ℹ️ FORMAÇÕES`

#### Ações DAT Registradas em CADASTROS

| Ação | Multi-projeto | Campo Valor |
|------|--------------|-------------|
| FORMAR - Criação de Curso | ✅ sim | ID do curso |
| FORMAR - Criação de Chaves | ✅ sim | Data |
| FORMAR - Criação de Instruções | ✅ sim | Data |
| FORMAR - Chaves enviadas | ✅ sim | Data |
| Códigos enviados | ✅ sim | Data |
| Reunião DAT | ❌ não | Data |

**Multi-projeto**: cria uma linha por projeto selecionado no `CADASTROS`.

#### Estrutura de Linha em CADASTROS

| Índice | Campo | Observação |
|--------|-------|------------|
| 0 | Município | — |
| 1 | Projeto | vazio se ação não requer projeto |
| 2 | Ação | tipo da ação DAT |
| 3 | (vazio) | coluna reservada |
| 4 | Valor | data ou ID do curso |
| 5 | Responsável | nome do responsável |
| 6 | Observações | opcional |

#### Fonte dos Dropdowns

- **Regiões**: `CONFIG!U2:U`
- **Projetos**: `CONFIG!W2:W` (exclui vazio e `#N/A`)
- **Municípios**: `CONFIG!T2:T` (exclui vazio, `#N/A`, e texto contendo `"INATIVO"`)

#### Status de Implementação

| Regra | Status |
|-------|--------|
| `AcaoDAT` model + choices | ✅ existe, mas tipos precisam ser verificados |
| Municípios com status INATIVO | ⚠️ verificar se `Municipio` tem campo `ativo` |
| ETL `etl_import_dat_cadastros` | ✅ existe |

---

### 2.7 `Planilha de Controle/generateQrCode.js`

**Propósito**: Gerar QR codes para cursos, salvos no Google Drive por município/projeto.

**Estrutura de pastas no Drive**:
```
Root (2025)
├── [Município]/
│   ├── [Projeto]/
│   │   └── qr_[projeto].png
```

**API externa**: `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=[url]`

#### Status de Implementação

| Funcionalidade | Status |
|----------------|--------|
| Geração de QR Code | ❌ não existe no sistema |
| Organização por município/projeto | ❌ não existe |

> Esta funcionalidade é auxiliar e não bloqueia o fluxo principal.

---

### 2.8 `Planilha de Controle/limparfiltros*.js` (3 arquivos)

Scripts de limpeza de filtros nas abas `ℹ️ FILTRO_PROD.`, `ℹ️ DAT`, `ℹ️ FORMAÇÕES`. Sem equivalente necessário no sistema.

---

## 3. Gaps Críticos: Fluxo Compras → GCal

### O Fio Condutor Ausente

O sistema tem todas as peças implementadas, mas **não há conexão explícita** entre elas:

```
LEGADO:
Compra registrada → município aparece no Acompanhamento → evento criado

SISTEMA (hoje):
Compra importada ✅    Solicitação criada ✅    GCal publicado ✅
       ↕ GAP                    ↕ GAP
 Nenhum município         Solicitação não sabe
 é "ativado" após        qual compra originou
 a compra               o evento
```

### Tabela de Gaps

| # | Gap | Onde falta | Impacto | Prioridade |
|---|-----|-----------|---------|------------|
| **G1** | ETL não normaliza nomes de projeto (strip "2026 ") | `etl_import_compras`, `import_compras_from_file` | Registros rejeitados silenciosamente | 🔴 Alta |
| **G2** | Nenhum município é "ativado" após importar compras | `SolicitacaoSerializer`, `options/municipios/` | Qualquer município pode solicitar evento sem ter feito compra | 🔴 Alta |
| **G3** | Tipos de `AcaoDAT` no modelo vs. planilha não verificados | `AcaoDAT` choices | Registros do ETL rejeitados | 🟡 Média |
| **G4** | Solicitação não referencia qual compra/produto gerou o evento | `Solicitacao` model | Sem rastreabilidade compra→evento | 🟡 Média |
| **G5** | Sem relatório "municípios com compra mas sem evento" | endpoint ou comando | Impossível saber quem está pendente | 🟡 Média |
| **G6** | Campo GUESTS (emails convidados) ausente em Solicitacao | `Solicitacao` model + serializer | Não é possível convidar participantes externos | 🟢 Baixa |

---

## 4. Importante: ETL é Migração Única

O ETL das planilhas é uma **operação única** para carregar dados históricos de 2026. Após o sistema entrar em produção:

- Todos os novos dados serão inseridos **diretamente no sistema** via UI/API
- As validações devem existir na **camada de serviço/serializer** (não só no ETL)
- O ETL deve usar os mesmos services que a API usa

```python
# ✅ Correto: ETL chama o mesmo service que a API
# service/compra_service.py
def criar_compra(data: dict, dry_run: bool = False) -> Compra:
    # validação aqui → vale para ETL e para API

# ETL command
compra_service.criar_compra(row, dry_run=dry_run)

# API serializer
class CompraSerializer:
    def create(self, validated_data):
        return compra_service.criar_compra(validated_data)
```

---

## 5. Referências

- Scripts: `v2/data/csv-import/2026/Scripts/`
- CSVs prontos: `v2/data/csv-import/2026/PRONTOS_PARA_IMPORTAR/`
- Plano de resolução: [PLAN_compras_flow_end_to_end.md](PLAN_compras_flow_end_to_end.md)
- Regras de disponibilidade: [GUIDE_AVAILABILITY.md](GUIDE_AVAILABILITY.md)
- Política de aprovação: ver `CLAUDE.md` → CP-02 (PA-01 a PA-07)
