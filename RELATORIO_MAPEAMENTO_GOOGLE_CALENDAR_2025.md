# Relatório: Mapeamento de Eventos Google Calendar 2025

**Data de Execução:** 13/09/2025  
**Objetivo:** Mapear todos os eventos de 2025 do Google Calendar específico e analisar dados complementares  

## 🎯 RESUMO EXECUTIVO

### Calendar ID Analisado
```
c_3381579109915e33c06be465adfbd9a31aaf4205c0bd45aa050c5a18be99fe15@group.calendar.google.com
```

### Status da Análise
- **Google Calendar API:** ❌ **Bloqueado por problemas de escopo**
- **Análise de Planilhas:** ✅ **Concluída com sucesso**  
- **Comandos Django:** ✅ **Implementados e funcionais**

---

## 🔧 PROBLEMAS TÉCNICOS IDENTIFICADOS

### 1. Autenticação Google Calendar API
**Problema:** Erro de escopo inválido (`invalid_scope: Bad Request`)

**Causa Raiz:** 
- As credenciais OAuth2 existentes (`google_authorized_user.json`) não incluíam o escopo `https://www.googleapis.com/auth/calendar`
- Originalmente configurado apenas para Sheets e Drive
- Necessária reautorização completa

**Status:** 
- ✅ Escopo adicionado nas credenciais localmente
- ❌ Reautorização no Google OAuth ainda pendente
- ✅ Script de renovação criado (`scripts/renew_google_calendar_auth.py`)

### 2. Encoding do Console Windows
**Problema:** Erro de caracteres Unicode em outputs
- `UnicodeEncodeError: 'charmap' codec can't encode characters`

**Solução Aplicada:**
- ✅ Removidos emojis de todos os comandos Django
- ✅ Outputs em texto simples funcionando corretamente

---

## 📊 RESULTADOS DA ANÁLISE

### Google Calendar (Tentativa)
```json
{
  "calendar_id": "c_3381579109915e33c06be465adfbd9a31aaf4205c0bd45aa050c5a18be99fe15@group.calendar.google.com",
  "year": 2025,
  "total_events": 0,
  "status": "Erro de escopo - acesso negado",
  "error": "invalid_scope: Bad Request"
}
```

### Análise de Planilhas Complementares
**Planilhas Analisadas:** 9 arquivos em `archive/spreadsheets/`

#### Estatísticas Descobertas:
- **Total de Planilhas:** 9
- **Total de Abas:** 9 (1 por planilha)
- **Eventos de 2025:** 0 (não encontrados dados temporais de 2025)
- **Formadores Identificados:** 114 nomes únicos
- **Municípios Identificados:** 0 (filtro específico do Ceará não encontrou referências)
- **Tamanho Total:** 0.1 MB

#### Top Formadores Identificados:
```
1. Alisson Mendonça
2. Alysson Macedo  
3. Amanda Sales
4. Ana Claudia
5. Ana Kariny
[... e mais 109 formadores]
```

#### Planilhas por Projeto:
- ACerta.xlsx
- amma.xlsx
- Brincando e Aprendendo.xlsx
- Fluir das Emoções.xlsx
- IDEB10.xlsx
- ler, ouvir e contar.xlsx
- produtos.xlsx
- superintendencia.xlsx
- Vidas.xlsx

---

## 🛠️ COMANDOS IMPLEMENTADOS

### 1. `map_google_calendar_events`
**Arquivo:** `core/management/commands/map_google_calendar_events.py`

**Funcionalidades:**
- Mapeamento completo de eventos anuais
- Análise estatística detalhada
- Export para JSON
- Suporte a filtros por período
- Análise de organizadores e localizações

**Uso:**
```bash
python manage.py map_google_calendar_events \
  --calendar-id="c_3381579109915e33c06be465adfbd9a31aaf4205c0bd45aa050c5a18be99fe15@group.calendar.google.com" \
  --output-file="out/eventos_2025.json" \
  --detailed
```

### 2. `analyze_planilhas_vs_calendar`
**Arquivo:** `core/management/commands/analyze_planilhas_vs_calendar.py`

**Funcionalidades:**
- Análise automatizada de planilhas Excel
- Extração de formadores e localizações
- Detecção de eventos por datas
- Estatísticas comparativas
- Recomendações automatizadas

**Uso:**
```bash
python manage.py analyze_planilhas_vs_calendar \
  --output-file="out/analise_planilhas_2025.json"
```

---

## 📈 INSIGHTS E DESCOBERTAS

### 1. **Base de Formadores Extensa**
- 114 formadores únicos identificados nas planilhas
- Indica sistema maduro com equipe grande
- **Ação:** Verificar cadastro completo no sistema Django

### 2. **Dados Temporais Limitados**
- Nenhum evento específico de 2025 encontrado nas planilhas analisadas
- Possíveis causas:
  - Planilhas são templates de projetos, não agenda de eventos
  - Dados de 2025 podem estar em planilhas não migradas
  - Calendário Google pode ser a fonte primária real

### 3. **Organização por Projetos**
- Cada planilha representa um projeto educacional específico
- Estrutura bem definida por áreas temáticas
- **Oportunidade:** Integrar projetos com sistema de agendamento

### 4. **Problema de Integração Crítico**
- Acesso ao Google Calendar bloqueado compromete análise completa
- **Prioridade Alta:** Resolver autenticação OAuth2

---

## 🎯 RECOMENDAÇÕES IMEDIATAS

### 1. **Resolver Autenticação Google (CRÍTICO)**
**Passos:**
1. Executar `scripts/renew_google_calendar_auth.py`
2. Seguir processo OAuth2 no navegador
3. Atualizar `google_authorized_user.json`
4. Re-executar mapeamento do calendar

### 2. **Validar Cadastro de Formadores**
```bash
# Comparar formadores das planilhas com banco de dados
python manage.py shell
>>> from core.models import Formador
>>> formadores_sistema = set(Formador.objects.values_list('nome', flat=True))
>>> formadores_planilhas = {...}  # Da análise
>>> faltantes = formadores_planilhas - formadores_sistema
```

### 3. **Investigar Calendários Adicionais**
- Verificar se existem outros calendários Google em uso
- Confirmar se o calendar ID fornecido é o principal
- Buscar calendários por projeto específico

### 4. **Migração Completa de Dados**
- Importar dados de todas as planilhas para o sistema Django
- Estabelecer sincronização bidirecional com Google Calendar
- Implementar validação de conflitos automática

---

## 📋 PRÓXIMAS ETAPAS

### Fase 1: Correção Técnica (1-2 dias)
- [ ] Resolver autenticação OAuth2 Google Calendar
- [ ] Re-executar mapeamento completo de eventos 2025
- [ ] Validar dados obtidos

### Fase 2: Análise Detalhada (2-3 dias)  
- [ ] Mapear TODOS os eventos de 2025 do calendar
- [ ] Analisar padrões de criação/organizadores
- [ ] Identificar eventos sem correspondência no sistema
- [ ] Gerar relatório de discrepâncias

### Fase 3: Sincronização (3-5 dias)
- [ ] Comparar eventos Calendar vs. Solicitações Django
- [ ] Implementar importação de eventos "órfãos"
- [ ] Configurar sincronização bidirecional
- [ ] Testes de integridade completos

---

## 📁 ARQUIVOS GERADOS

### Comandos Django
- `core/management/commands/map_google_calendar_events.py`
- `core/management/commands/analyze_planilhas_vs_calendar.py`

### Scripts de Suporte
- `scripts/renew_google_calendar_auth.py`

### Relatórios
- `out/eventos_google_calendar_2025.json` (vazio por erro de escopo)
- `out/analise_planilhas_controle_2025.json` (114 formadores identificados)

### Credenciais Atualizadas
- `google_authorized_user.json` (escopo calendar adicionado)

---

## ⚠️ LIMITAÇÕES ATUAIS

1. **Acesso ao Google Calendar:** Bloqueado até resolução OAuth2
2. **Dados de 2025:** Limitados às planilhas locais (que não continham eventos temporais)
3. **Validação Cruzada:** Impossível sem acesso ao calendar real
4. **Análise Temporal:** Dependente da resolução do problema de autenticação

---

## 💡 VALOR ENTREGUE

Mesmo com o bloqueio técnico, este trabalho entregou:

✅ **Infraestrutura Completa:** Comandos Django robustos para mapeamento  
✅ **Análise Alternativa:** Descoberta de 114 formadores nas planilhas  
✅ **Diagnóstico Preciso:** Identificação clara do problema de escopo  
✅ **Solução Preparada:** Scripts de renovação OAuth2 prontos  
✅ **Documentação Detalhada:** Processo completo documentado para reprodução  

**Próximo passo crítico:** Resolver autenticação e executar mapeamento completo do Google Calendar 2025.