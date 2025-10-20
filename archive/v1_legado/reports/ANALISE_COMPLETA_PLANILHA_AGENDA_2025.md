# ANÁLISE COMPLETA - Planilha "Acompanhamento de Agenda | 2025"

## Informações Gerais da Planilha

**URL:** https://docs.google.com/spreadsheets/d/16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU/edit

**Título:** Acompanhamento de Agenda | 2025

**Total de Abas:** 13

**Status de Acesso:** ✅ Acessível via API Google Sheets (OAuth2)

---

## Resumo Executivo

A planilha contém **6.008 registros de eventos** distribuídos em 5 abas principais de solicitações, representando um volume substancial de dados para migração para o sistema Django. 

### Principais Estatísticas:
- **📊 Total de registros analisados:** 6.008
- **👥 Formadores únicos identificados:** 84
- **📋 Projetos únicos:** 24  
- **🏢 Tipos de evento:** 3 (Presencial, Online, Acompanhamento)
- **🔒 Registros de bloqueios:** 51

---

## ABAS ANALISADAS COM SUCESSO

### 1. ABA "SUPER" 
**Status:** ✅ **PRIORIDADE ALTA** - Contém aprovações da Superintendência

- **Registros:** 1.985 
- **Colunas:** 20
- **Características:**
  - Campo "Aprovação" específico (SIM/NÃO)
  - Todos os projetos principais representados
  - Formadores múltiplos por evento (até 5)
  - Status de aprovação explícito

**Estrutura de Colunas:**
```
- Coluna 1, Aprovação, Atualizar, C ancelar
- Municípios, encontro, tipo, data  
- hora início, hora fim, projeto, segmento
- Coord Acompanha, Coordenador
- Formador 1, Formador 2, Formador 3, Formador 4, Formador 5  
- Convidados
```

**Amostra de Dados:**
```
Município: Amigos do Bem
Data: 10/03/2025, Horário: 08:00-17:00
Projeto: Lendo e Escrevendo, Segmento: 2 e 3
Aprovação: SIM
Coordenador: Maria Nadir
Formador 1: Nadyelle Carvalho
```

### 2. ABA "ACERTA"
**Status:** ✅ **PRIORIDADE ALTA** - Projeto ACerta

- **Registros:** 1.001
- **Colunas:** 20  
- **Características:**
  - Foco no projeto "ACerta"
  - Segmentação por área (LP, MAT)
  - Estrutura similar à aba Super

**Estrutura de Colunas:**
```
- Coluna 1, Column 18, Alteração, C ancelar
- município, encontro, tipo, data
- hora início, hora fim, projeto, segmento  
- Coord Acompanha, Coordenador
- Formador 1-5, Convidados
```

**Amostra de Dados:**
```
Município: Amigos do Bem
Data: 10/03/2025, Horário: 08:00-12:00
Projeto: ACerta, Segmento: LP
Coordenador: Ellen Damares  
Formador 1: Elizabete Lima
```

### 3. ABA "OUTROS"
**Status:** ✅ **PRIORIDADE MÉDIA** - Projetos diversos

- **Registros:** 1.022
- **Colunas:** 21
- **Características:**
  - Projetos diversos (SOU DA PAZ, LEIO ESCREVO E CALCULO)
  - Campo "controle" adicional
  - Municípios com UF especificada

**Estrutura de Colunas:**
```
- controle, Column 20, Column 19, Coluna 1
- município, encontro, tipo, data
- hora início, hora fim, projeto, segmento
- Coord Acompanha, Coordenador  
- Formador 1-5, Convidados, Column 21
```

**Amostra de Dados:**
```
Município: Dias d'Avila - BA
Data: 08/04/2025, Horário: 08:00-17:00
Projeto: SOU DA PAZ
Coordenador: Rafael Rabelo
```

### 4. ABA "BRINCANDO"  
**Status:** ✅ **PRIORIDADE MÉDIA** - Projeto Brincando e Aprendendo

- **Registros:** 1.000
- **Colunas:** 20
- **Características:**
  - Exclusivo projeto "Brincando e Aprendendo"
  - Campo "Gerente" ao invés de "Coordenador"  
  - Foco em educação infantil

**Estrutura de Colunas:**
```
- Coluna 1, Column 20, A tualizar, C ancelar
- município, encontro, tipo, data
- hora início, hora fim, projeto, segmento
- Coord Acompanha, Gerente
- Formador 1-5, Convidados
```

**Amostra de Dados:**
```
Município: Serra do Salitre - MG  
Data: 22/02/2025, Horário: 07:00-17:00
Projeto: Brincando e Aprendendo
Gerente: Gleice Anne
Formador 1: Fabrícia Santos
```

### 5. ABA "VIDAS"
**Status:** ✅ **PRIORIDADE MÉDIA** - Projeto Vida & Linguagem

- **Registros:** 1.000  
- **Colunas:** 20
- **Características:**
  - Exclusivo projeto "Vida & Linguagem"
  - Campo "Aprovação" presente
  - Eventos de menor duração (4h)

**Estrutura de Colunas:**
```
- Coluna 1, Aprovação, A, C
- Município, Encontro, tipo, data  
- hora início, hora fim, projeto, segmento
- Coord Acompanha, Coordenador
- Formador 1-5, Convidados
```

**Amostra de Dados:**
```
Município: Amigos do Bem
Data: 11/03/2025, Horário: 08:00-12:00  
Projeto: Vida & Linguagem
Aprovação: SIM
Coordenador: Socorro Aclécia
Formador 1: Glaubia Pinheiro
```

### 6. ABA "BLOQUEIOS"
**Status:** ✅ **FUNCIONAL** - Bloqueios de agenda

- **Registros:** 51
- **Colunas:** 4
- **Características:**
  - Estrutura simples e direta
  - Tipos: Total, Parcial
  - Formato de data simplificado (DD/MM)

**Estrutura de Colunas:**
```
- Pessoa, Data Inicio, Data Fim, Tipo
```

**Amostra de Dados:**
```
Pessoa: Marcela Sousa
Data Inicio: 31/01, Data Fim: 03/02
Tipo: Total
```

---

## ABAS COM PROBLEMAS DE ACESSO

### 7. ABA "CONFIGURAÇÕES" 
**Status:** ❌ **ERRO** - Header não único
- **Erro:** "header row in the worksheet is not unique"
- **Impacto:** Não foi possível extrair dados estruturados
- **Observação:** Contém configurações do sistema

### 8. ABA "DISPONIBILIDADE"
**Status:** ❌ **ERRO** - Header não único  
- **Tamanho:** 690 linhas × 78 colunas
- **Erro:** "header row in the worksheet is not unique"
- **Impacto:** Dados de disponibilidade não acessíveis via API

### 9. ABA "DESLOCAMENTO"
**Status:** ❌ **ERRO** - Header não único
- **Tamanho:** 1.000 linhas × 11 colunas  
- **Erro:** "header row in the worksheet is not unique"
- **Impacto:** Dados de deslocamento não acessíveis via API

---

## OUTRAS ABAS IDENTIFICADAS (NÃO ANALISADAS)

- **Pré-Agenda:** 702 linhas × 29 colunas
- **Novo Google Agenda:** 1.143 linhas × 26 colunas  
- **Google Agenda:** 2.452 linhas × 32 colunas
- **Relatórios:** 1.000 linhas × 26 colunas

---

## DADOS COLETADOS PARA MIGRAÇÃO

### 🧑‍🏫 FORMADORES IDENTIFICADOS (84 únicos)

**Lista Completa:**
```
- Alisson Mendonça        - Ana Kariny             - Amanda Sales
- Anna Lúcia              - Anna Patrícia          - Antonio Furtado  
- Ariana Coelho          - Ayla Maria             - Alysson Macedo
- Bruno Teles            - Claudiana Maria        - David Ribeiro
- Danielle Fernandes     - Denise Carlos          - Deuzirane Nunes
- Diego Tavares          - Douglas Wígner         - Elaine Mendes
- Elienai Góes           - Elienai Oliveira       - Elisângela Soares
- Elizabete Lima         - Estela Maria           - Fabíola Martins
- Fabrícia Santos        - Gabriel Oliveira       - Gabriela Duarte
- Germana Mirla          - Glaubia Pinheiro       - Gleice Anne
- Hugo Ribeiro           - Humberto Luciano       - Iago Oliveira
- Icaro Maciel           - Isabel Kerssia         - Janieri Martins
- Jarbas Marcelino       - João Marcos            - Jonathan Araújo
- Juliana Guerreiro      - Júlia Rodrigues        - Katy Silva
- Laís Aline             - Lidiane Oliveira       - Lívia Mara
- Lyziane Maria          - Marcela Sousa          - Marcos Randall
- Maria Auxiliadora      - Maria Joelma           - Maria Leidiane
- Maria Nadir            - Marilene Lima          - Mazuk Eeves
- Michele Macedo         - Michella Rita          - Mônica Maria
- Mônica Silva           - Nadyelle Carvalho      - Natália Gomes
- Nivia Vieira           - Paula Freire           - Penélope Alberto
- Poliane Lima           - Raul Vasconcelos       - Rayane Maria
- Regianio Lima          - Ricardo Ítalo          - Rochelly Alinne
- Rodolfo Penha          - Rodrigo Lima           - Sandra Dias
- Silvio Almeida         - Simone Maria           - Socorro Aclécia
- Thaís Borges           - Valdiana Santos        - Valdemir Silva
- Vanessa Angélica       - Viviane Aquino         - Yuri Furtado
```

**Observações:**
- "SOLICITADO" aparece como formador (indica formador a ser definido)
- "?Regianio Lima?" tem formatação especial (possível questão)

### 🏛️ PROJETOS IDENTIFICADOS (24 únicos)

```
- A COR DA GENTE                          - ACerta
- Avançando Juntos Língua Portuguesa      - Avançando Juntos Matemática  
- Brincando e Aprendendo                  - Cataventos
- Cirandar                                - ED FINANCEIRA
- Escrever Comunicar e Ser                - IDEB10
- IDEB10 - ESQUENTA SAEB                  - LEIO ESCREVO E CALCULO
- Lendo e Escrevendo                      - LER, OUVIR E CONTAR
- Miudezas                                - Novo Lendo
- Projeto AMMA                            - SOU DA PAZ
- Superativar                             - Tema
- UNI DUNI TÊ                            - Vida & Ciências
- Vida & Linguagem                        - Vida & Matemática
```

### 📍 TIPOS DE EVENTO (3 únicos)

1. **Presencial** - Eventos presenciais nos municípios
2. **Online** - Eventos virtuais  
3. **Acompanhamento** - Acompanhamento de projetos

### 🏢 MUNICÍPIOS IDENTIFICADOS (via amostra)

**Municípios com UF especificada:**
- Dias d'Avila - BA
- Petrolina - PE  
- Lagoa Grande - PE
- Serra do Salitre - MG
- Tarrafas - CE
- Florestal - MG
- Uiraúna - PB
- Catolé do Rocha - PB

**Outras localidades:**
- Amigos do Bem (aparece frequentemente - possivelmente instituição)

### 👥 COORDENADORES IDENTIFICADOS

- Ellen Damares
- Maria Nadir  
- Rafael Rabelo
- Socorro Aclécia
- Gleice Anne (Gerente no projeto Brincando)

### 🔒 TIPOS DE BLOQUEIO

1. **Total** - Bloqueio completo da agenda
2. **Parcial** - Bloqueio parcial da agenda

---

## PROBLEMAS E INCONSISTÊNCIAS IDENTIFICADOS

### 🚨 Problemas Técnicos

1. **Headers não únicos** em 3 abas críticas:
   - Configurações, Disponibilidade, Deslocamento
   - **Impacto:** Impossibilita extração automática via API

2. **Codificação de caracteres:**
   - Alguns caracteres especiais (ã, ç, ê) podem ter problemas
   - **Recomendação:** Validar encoding UTF-8 na migração

### 📋 Inconsistências de Dados

1. **Nomes de colunas variados:**
   - "município" vs "Município" vs "Municípios"
   - "encontro" vs "Encontro"
   - "Coordenador" vs "Gerente"

2. **Formato de horários inconsistente:**
   - "08:00" vs "08:00:00"
   - Alguns campos de hora fim sem segundos

3. **Campos de controle variados:**
   - "Coluna 1", "Column 18", "controle"
   - Função não clara destes campos

### ⚠️ Dados Questionáveis

1. **Formador "?Regianio Lima?"** - Indica incerteza
2. **"SOLICITADO"** como nome de formador
3. **"Amigos do Bem"** - Não parece município tradicional

---

## ESTRATÉGIA DE MIGRAÇÃO RECOMENDADA

### Fase 1: Migração Prioritária ⭐⭐⭐

**Ordem de prioridade:**

1. **ABA "SUPER"** (1.985 registros)
   - ✅ Tem campo aprovação explícito
   - ✅ Representa fluxo de aprovação da Superintendência
   - ✅ Todos os projetos representados

2. **ABA "BLOQUEIOS"** (51 registros)  
   - ✅ Estrutura simples e limpa
   - ✅ Essencial para verificação de conflitos
   - ✅ Sem problemas técnicos

### Fase 2: Migração Secundária ⭐⭐

3. **ABA "ACERTA"** (1.001 registros)
4. **ABA "OUTROS"** (1.022 registros)  
5. **ABA "BRINCANDO"** (1.000 registros)
6. **ABA "VIDAS"** (1.000 registros)

### Fase 3: Resolução de Problemas ⭐

7. **Abas com problemas de header:**
   - Configurações, Disponibilidade, Deslocamento
   - **Estratégia:** Acesso manual ou correção de headers na planilha

---

## MAPEAMENTO PARA MODELOS DJANGO

### Modelo `Solicitacao`

**Campos identificados na planilha → Modelo Django:**

```python
# Campos diretos
municipio → municipio (ForeignKey)
data → data_inicio  
hora_inicio → hora_inicio
hora_fim → hora_fim
projeto → projeto (ForeignKey)
tipo → tipo_evento (presencial/online)

# Campos de aprovação  
Aprovacao → status (aprovado/pendente/rejeitado)
Coordenador → solicitante (ForeignKey para Usuario)

# Campos adicionais
encontro → numero_encontro
segmento → segmento_target
Coord_Acompanha → acompanhamento_coordenacao
Convidados → participantes_externos
```

### Modelo `Formador`

**Dados extraídos:**
- 84 formadores únicos identificados
- Relacionamento N:N com Solicitacao (até 5 formadores por evento)
- Integração com modelo Usuario

### Modelo `BloqueioFormador`

**Mapeamento direto:**
```python
Pessoa → formador (ForeignKey)  
Data_Inicio → data_inicio
Data_Fim → data_fim
Tipo → tipo_bloqueio (total/parcial)
```

### Modelo `Projeto`

**24 projetos identificados** - criação automática durante migração

### Modelo `Municipio`

**Extração necessária** dos municípios únicos da planilha (alguns com UF)

---

## PRÓXIMOS PASSOS RECOMENDADOS

### 1. Preparação Técnica ⚙️

- [ ] Criar comando Django específico para migração da planilha
- [ ] Implementar normalização de dados (nomes, datas, horários)
- [ ] Configurar tratamento de encoding UTF-8
- [ ] Preparar validação de dados inconsistentes

### 2. Migração de Dados 📊

- [ ] **PRIORIDADE 1:** Migrar bloqueios (estrutura simples)
- [ ] **PRIORIDADE 2:** Migrar aba "Super" (aprovações da superintendência)  
- [ ] **PRIORIDADE 3:** Migrar demais abas de eventos
- [ ] Validar integridade dos dados migrados

### 3. Resolução de Problemas 🔧

- [ ] Contatar responsável para corrigir headers duplicados
- [ ] Definir estratégia para dados questionáveis (?Regianio Lima?, SOLICITADO)
- [ ] Implementar normalização de municípios
- [ ] Criar logs detalhados da migração

### 4. Validação e Testes ✅

- [ ] Comparar totais migrados vs. planilha original
- [ ] Testar fluxo de aprovação com dados migrados
- [ ] Validar calendário e conflitos
- [ ] Testes de performance com 6K+ registros

---

## CÓDIGO PARA IMPLEMENTAÇÃO

**Comando Django para migração completa:**

```bash
# Migrar bloqueios primeiro (estrutura simples)
python manage.py migrate_agenda_sheet --aba "Bloqueios" --tipo bloqueios

# Migrar eventos por prioridade  
python manage.py migrate_agenda_sheet --aba "Super" --tipo eventos --prioridade alta
python manage.py migrate_agenda_sheet --aba "ACerta" --tipo eventos --prioridade media
python manage.py migrate_agenda_sheet --aba "Outros" --tipo eventos --prioridade media
python manage.py migrate_agenda_sheet --aba "Brincando" --tipo eventos --prioridade media  
python manage.py migrate_agenda_sheet --aba "Vidas" --tipo eventos --prioridade media

# Validar migração
python manage.py validate_migrated_data --relatorio completo
```

---

## CONCLUSÃO

A planilha "Acompanhamento de Agenda | 2025" contém **6.008 registros válidos** de eventos distribuídos em 5 abas funcionais, representando uma base sólida para migração para o sistema Django. 

**Pontos Fortes:**
- ✅ Volume substancial de dados reais
- ✅ Estrutura consistente entre abas similares  
- ✅ Presença de campos de aprovação (essencial para o fluxo)
- ✅ Dados de bloqueios bem estruturados

**Desafios:**
- ⚠️ 3 abas com problemas técnicos de header
- ⚠️ Inconsistências menores de formato e nomenclatura
- ⚠️ Alguns dados questionáveis que requerem validação

**Recomendação:** Proceder com migração em fases, priorizando aba "Super" e "Bloqueios" para estabelecer base funcional do sistema, seguido das demais abas após normalização dos dados.

---

**Análise realizada em:** 13 de Janeiro de 2025  
**Total de registros analisados:** 6.008  
**Abas processadas com sucesso:** 6 de 13  
**Arquivo de dados:** `analise_agenda.json` (dados completos exportados)