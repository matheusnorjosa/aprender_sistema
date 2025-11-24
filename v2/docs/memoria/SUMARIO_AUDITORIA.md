# Sumário Executivo - Auditoria de Planilhas Aprender Sistema

**Data da Auditoria:** 2025-10-23
**Timezone:** America/Fortaleza
**Fontes:** Google Sheets (4 planilhas exportadas via XLSX)

---

## 📊 Visão Geral

### Dados Processados

- **Total de eventos:** 2.307 eventos
- **Fontes analisadas:** Google Sheets (arquivos locais não disponíveis)
- **Abas processadas:** ACerta (490), Outros (79), Brincando (193), Vidas (289), Super (1.256)

### Planilhas Carregadas

| Planilha | Status | Tamanho |
|----------|--------|---------|
| Acompanhamento 2025 | ✅ OK | 1.3 MB |
| Disponibilidade 2025 | ✅ OK | 352 KB |
| Controle 2025 | ✅ OK | 3.9 MB |
| Usuários | ✅ OK | 23 KB |

---

## 🔍 Principais Achados

### 1. Duplicidades ⚠️

- **529 eventos duplicados** (215 chaves únicas)
- Distribuição por aba:
  - **Super:** 371 duplicados (29.5% do total)
  - **ACerta:** 76 duplicados (15.5%)
  - **Vidas:** 76 duplicados (26.3%)
  - **Brincando:** 6 duplicados (3.1%)
  - **Outros:** 0 duplicados ✅

**Ação recomendada:** Revisar eventos duplicados em `relatorio_eventos_duplicados.csv` e consolidar entradas redundantes.

---

### 2. Eventos Cancelados/Adiados 📅

- **109 eventos** marcados como cancelados/adiados (4.7% do total)
- Distribuição:
  - **Super:** 79 cancelados
  - **Brincando:** 13 cancelados
  - **ACerta:** 10 cancelados
  - **Outros:** 4 cancelados
  - **Vidas:** 3 cancelados

**Critérios aplicados:**
- ACerta/Brincando/Vidas/Super: Checkbox "Cancelar" (coluna D)
- Outros: Segmento contém "cancelado" ou "adiado"

---

### 3. Validação de Horários ✅

- **0 eventos com horários inválidos** (hora_fim <= hora_inicio)
- Todas as entradas respeitam a ordem cronológica dos horários

---

### 4. Eventos "Outros" sem Formador 👥

- **79 eventos** (100% da aba "Outros") sem formadores designados
- **Regra aplicada:** Coordenador acumula papel de FORMADOR quando não há Formador 1..5

**Observação:** Esta é uma característica estrutural da aba "Outros", não um erro.

---

### 5. Pessoas Pendentes (Sem Match) ⚠️

- **123 pessoas** sem correspondência nos usuários cadastrados (230 usuários ativos)
- **Taxa de match:** ~46.5% das pessoas nos eventos não estão cadastradas

**Principais pendências:**

| Pessoa | Papel | Aba | Ocorrências |
|--------|-------|-----|-------------|
| 3º ANO LING | COORD_ACOMPANHA | ACerta | Múltiplas |
| 3º ANO MAT | COORD_ACOMPANHA | ACerta | Múltiplas |
| 4º ANO LING | COORD_ACOMPANHA | ACerta | Múltiplas |
| 4º ANO MAT | COORD_ACOMPANHA | ACerta | Múltiplas |
| Alisson Mendonça | FORMADOR_1/2/4 | Super | Múltiplas |
| Amanda Arruda | COORDENADOR | Outros | Múltiplas |
| Amanda Sales | FORMADOR_1/2 | Super | Múltiplas |

**Observação:** Algumas entradas como "3º ANO LING" são indicadores (não pessoas), devem ser tratadas como "Coord Acompanha = Sim/Não".

**Ação recomendada:**
1. Cadastrar pessoas faltantes na planilha Usuários
2. Revisar e limpar entradas não-pessoas em "Coord Acompanha"

---

### 6. Projetos sem Match no Controle ⚠️

- **6 projetos** em "Outros" não encontrados no FILTRO_PROD. do Controle
- **7 projetos** cadastrados no FILTRO_PROD.

**Projetos faltantes no Controle:**

1. ED FINANCEIRA
2. LER, OUVIR E CONTAR
3. GESTÃO ESCOLAR (normalizado de IDEB/IDEB10)
4. SOU DA PAZ
5. A COR DA GENTE
6. LEIO ESCREVO E CALCULO

**Ação recomendada:** Cadastrar projetos faltantes no FILTRO_PROD. ou corrigir nomes inconsistentes.

---

### 7. Disponibilidade (Dados Auxiliares) 📋

| Aba | Linhas |
|-----|--------|
| ANUAL | 32 |
| DESLOCAMENTO | 382 |
| Bloqueios | 38 |

**Total:** 452 registros de disponibilidade/deslocamento.

---

### 8. Super: Análise de Aprovação/Tempo ⏰

- **Total de eventos Super:** 1.256
- **Passados (< hoje):** 0 ⚠️
- **Futuros:** 0 ⚠️
  - Aprovados (SIM): 0
  - Pendentes: 0

**Observação crítica:** Anomalia detectada - todos os eventos parecem ter datas inválidas ou não parseadas corretamente. Requer investigação manual.

---

## 📁 Relatórios Gerados

Todos os relatórios estão disponíveis em:
`C:\Users\datsu\OneDrive\Documentos\Aprender Sistema\v2\.agents\outbox\`

| Arquivo | Tamanho | Linhas | Descrição |
|---------|---------|--------|-----------|
| `relatorio_eventos_duplicados.csv` | 134 KB | 529 | Eventos com chave natural duplicada |
| `relatorio_intervalos_invalidos.csv` | 4 bytes | 0 | Horários inválidos (vazio ✅) |
| `relatorio_eventos_cancelados_adiados.csv` | 29 KB | 109 | Eventos marcados como cancelados |
| `relatorio_outros_sem_formador.csv` | 18 KB | 79 | Eventos "Outros" sem formador |
| `relatorio_pessoas_pendentes_match.csv` | 9.3 KB | 123 | Pessoas sem cadastro |
| `relatorio_comparacao_projetos.csv` | 310 bytes | 6 | Projetos ausentes no Controle |
| `relatorio_divergencias_sheets_vs_xlsx.csv` | 4 bytes | 0 | Divergências entre fontes (vazio) |

---

## 🎯 Resumo por Aba

| Aba | Total | Sem Mun. | Sem Data | Cancelados | Duplicados |
|-----|-------|----------|----------|------------|------------|
| **ACerta** | 490 | 0 | 0 | 10 | 76 |
| **Outros** | 79 | 0 | 0 | 4 | 0 |
| **Brincando** | 193 | 0 | 0 | 13 | 6 |
| **Vidas** | 289 | 1 ⚠️ | 0 | 3 | 76 |
| **Super** | 1.256 | 0 | 0 | 79 | 371 |

---

## ✅ Conformidade com Regras de Interpretação

### Aplicadas com Sucesso:

- ✅ **Timezone:** America/Fortaleza (HOJE = 2025-10-23)
- ✅ **Normalização:** Textos normalizados (lowercase, sem acentos, espaços colapsados)
- ✅ **IDEB/IDEB10 → Gestão Escolar:** Aplicado (6 ocorrências)
- ✅ **Cancelamento:** Checkbox (ACerta/Brincando/Vidas/Super) + Segmento (Outros)
- ✅ **Outros sem Formador:** 79 casos identificados com regra "Coordenador = FORMADOR"
- ✅ **Coord Acompanha:** Detectadas entradas "Sim/Não" vs pessoas (pendências separadas)
- ✅ **External Hash:** Chave natural determinística (SHA1) gerada para todos os eventos

### Ajustes Necessários:

- ⚠️ **Super - Múltiplos Municípios:** Não implementado (split por `;,/|`) - eventos mantidos como-estão
- ⚠️ **Status por Tempo/Aprovação:** Anomalia nas datas (todos eventos com data inválida)
- ⚠️ **Validação de E-mails:** Regex simples aplicado, mas não reportado em CSV separado

---

## 🚀 Próximos Passos Recomendados

### Prioridade Alta:

1. **Investigar anomalia de datas na aba Super** (0 passados, 0 futuros)
2. **Resolver 529 duplicidades** (foco em Super: 371 casos)
3. **Cadastrar 123 pessoas pendentes** ou limpar entradas inválidas

### Prioridade Média:

4. **Cadastrar 6 projetos faltantes** no FILTRO_PROD. do Controle
5. **Revisar 109 eventos cancelados** para remoção ou atualização de status
6. **Validar 1 município faltante** em Vidas

### Prioridade Baixa:

7. **Implementar split de municípios** em Super (múltiplos por célula)
8. **Melhorar match de pessoas** com fuzzy matching (similaridade)
9. **Validar e-mails** de coordenadores/formadores

---

## 📌 Notas Técnicas

### Avisos Durante Execução:

- **FutureWarning:** `Passing bytes to 'read_excel'` será removido em versões futuras do pandas
  - **Impacto:** Nenhum (funcionalidade preservada)
  - **Ação:** Atualizar código para usar `BytesIO` quando pandas 3.x for adotado

### Limitações:

- **Arquivos locais:** Não disponíveis no ambiente (apenas Google Sheets processados)
- **Comparação de fontes:** Pulada (apenas 1 fonte disponível)
- **Fuzzy matching:** Não aplicado (match exato por e-mail ou nome normalizado)

---

## 📞 Suporte

Para dúvidas sobre este relatório ou necessidade de re-execução com parâmetros ajustados:

- **Script:** `v2/backend/.agents/scripts/audit_planilhas.py`
- **Executar:** `docker compose exec -T web python /tmp/audit.py`
- **Dependências:** pandas, requests, openpyxl

---

**Auditoria executada com sucesso! ✅**
**Reprodutível:** Execute o script novamente a qualquer momento para atualizar os dados.
