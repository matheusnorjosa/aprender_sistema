# Auditoria Completa: Google Sheets + Apps Script 2025

**Data:** 2025-08-22  
**Objetivo:** Verificação final e cruzada entre planilhas (Sheets) e projetos Apps Script

## 1. INVENTÁRIO COMPLETO

### 1.1 Projetos Apps Script
| Projeto | Arquivos | Linhas Código | Última Mod | Owner |
|---------|----------|---------------|------------|-------|
| **Acompanhamento de Agenda** | Code.gs, appsscript.json | 319 linhas | - | - |
| **Disponibilidade** | Code.gs, appsscript.json | 315 linhas | - | - |
| **Planilha de Controle - 2025** | Code.gs, appsscript.json | 416 linhas | - | - |

### 1.2 Planilhas Google Sheets
| Planilha | ID | Abas | Fórmulas |
|----------|----|----- |----------|
| **Acompanhamento de Agenda _ 2025** | 1CKhz8j2x... | Super, ACerta, Vidas, Outros, Brincando, Google Agenda, Configurações | CONCATENATE, IMPORTRANGE |
| **Disponibilidade _ 2025** | 1fsCeGUz... | MENSAL, ANUAL, DESLOCAMENTO, Bloqueios, Eventos, Configurações | SUMPRODUCT, NETWORKDAYS |
| **Planilha de Controle - 2025** | 1P6YG3sI... | 🟥 COMPRAS, 🟥 AÇÕES, ℹ️ FILTRO_PROD., 🟥 COORD, ℹ️ FORMAÇÕES, etc. | QUERY, IMPORTRANGE |

## 2. ANÁLISE DE TRIGGERS E AUTOMAÇÕES

### 2.1 Triggers Críticos Identificados
| Script | Trigger | Função | Frequência | Risco |
|--------|---------|---------|------------|-------|
| **Acompanhamento** | onEdit | createCalendarEvent() | Cada edição | 🔴 ALTO |
| **Acompanhamento** | timeBased | autoSync() | A cada hora | 🟡 MÉDIO |
| **Disponibilidade** | onEdit | updateAvailabilityFromBlocking() | Cada edição | 🟡 MÉDIO |
| **Disponibilidade** | timeBased | dailyUpdate() | Diário 06:00 | 🟡 MÉDIO |
| **Controle** | onEdit | handleComprasEdit() | Cada edição | 🔴 ALTO |
| **Controle** | timeBased | autoProcessCompras() | A cada 2h | 🔴 ALTO |

### 2.2 Permissões OAuth
```
Acompanhamento de Agenda:
- calendar (escrita/leitura)
- spreadsheets (escrita/leitura)
- external_request (APIs externas)
- drive.file (arquivos)

Disponibilidade:
- calendar.readonly (só leitura)
- spreadsheets (escrita/leitura)
- external_request (APIs externas)

Planilha de Controle:
- spreadsheets (escrita/leitura)
- drive.file (arquivos)
- external_request (APIs externas)
- admin.directory.user.readonly (diretório)
```

## 3. RISCOS DE SEGURANÇA CRÍTICOS

### 🔴 RISCOS CRÍTICOS
1. **Tokens Hardcoded**:
   - `getApiToken()` retorna "fallback-token-123" (Acompanhamento:293)
   - `getApiToken()` retorna "sistema-controle-token-789" (Controle:350)
   - `getERPToken()` retorna "erp-fallback-token" (Controle:415)

2. **APIs Externas Não Validadas**:
   - `https://api.aprender.com/formadores` (Acompanhamento:273)
   - `https://api.sistema-interno.com/disponibilidade` (Acompanhamento:299)
   - `https://api.sistema-compras.com/pedidos` (Controle:126)
   - `https://api.sistema-rh.com/coordenadores` (Controle:221)
   - `https://api.erp-empresa.com/importar` (Controle:371)

3. **Dados Sensíveis Expostos**:
   - Emails hardcoded (Disponibilidade:267-271)
   - Dados financeiros em APIs de compras
   - Informações de RH e coordenadores

### 🟡 RISCOS MÉDIOS
1. **Processamento Automático**: Scripts rodando sem supervisão humana
2. **Falta de Validação**: Dados externos sem sanitização
3. **Logs Inadequados**: Erro handling básico

## 4. DEPENDÊNCIAS CRÍTICAS

### 4.1 Fluxo Planilha → Script
| Planilha | Coluna/Célula | Script | Função |
|----------|---------------|--------|--------|
| Super!A:A | "SIM" | Acompanhamento | markForProcessing() |
| Super!B:B | "APROVADO" | Acompanhamento | createCalendarEvent() |
| 🟥 COMPRAS!B:B | Produto | Controle | validateProduto() |
| 🟥 COMPRAS!C:C | Quantidade | Controle | updateEstoque() |
| Bloqueios!A:D | Dados completos | Disponibilidade | updateAvailabilityFromBlocking() |

### 4.2 Fórmulas Intercomunicadas
```
Configurações → Agenda:
=IMPORTRANGE("1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA","ℹ️ CONFIG!A:A")

Google Agenda → Super:
=CONCATENATE(Configurações!$B$2," - ",Super!D2," - ",Super!E2)

Disponibilidade → Cálculos:
=SUMPRODUCT((MONTH(Eventos!C:C)=MONTH(TODAY()))*(Eventos!E:E<>""))
```

## 5. MATRIZ DE IMPACTO 2025

| Componente | Usuários | Frequência | Dados Críticos | Impacto Falha |
|------------|----------|------------|-----------------|---------------|
| **Acompanhamento Agenda** | 50+ formadores | Diário | Eventos/Calendários | 🔴 CRÍTICO |
| **Controle Compras** | 10 gestores | Contínuo | Dados financeiros | 🔴 CRÍTICO |
| **Disponibilidade** | 50+ formadores | Semanal | Planejamento RH | 🟡 ALTO |

## 6. GAPS IDENTIFICADOS

### 6.1 Gaps Técnicos
- ❌ **Sem backup automatizado** de dados críticos
- ❌ **Sem versionamento** de scripts
- ❌ **Sem monitoring** de falhas em produção
- ❌ **Sem rate limiting** em APIs externas
- ❌ **Sem validação** de dados de entrada

### 6.2 Gaps de Segurança
- ❌ **Tokens em plaintext** no código
- ❌ **Sem HTTPS validation** para APIs
- ❌ **Sem audit log** de alterações críticas
- ❌ **Permissões muito amplas** (admin.directory)
- ❌ **Sem encryption** de dados sensíveis

### 6.3 Gaps Operacionais
- ❌ **Sem documentação** técnica atualizada
- ❌ **Sem processo de deploy** controlado
- ❌ **Sem disaster recovery** plan
- ❌ **Dependência de pessoa única** para manutenção

## 7. PLANO DE SUBSTITUIÇÃO RECOMENDADO

### 7.1 Migração Django (PRIORIDADE ALTA)
```python
# Já implementado:
✅ Models completos (planilhas/models.py)
✅ Sistema de import (management commands)
✅ Testes automatizados
✅ Sistema de auditoria

# Próximos passos:
🔄 Migrar triggers críticos para Django
🔄 Implementar API segura para integrações
🔄 Criar dashboard para substituir planilhas
```

### 7.2 Cronograma Sugerido
| Fase | Duração | Descrição |
|------|---------|-----------|
| **Fase 1** | 2 semanas | Migrar dados críticos + APIs básicas |
| **Fase 2** | 3 semanas | Interface web + automações básicas |
| **Fase 3** | 2 semanas | Migrar triggers complexos |
| **Fase 4** | 1 semana | Desativação gradual dos scripts |

## 8. CONCLUSÕES E RECOMENDAÇÕES

### 8.1 Status Atual: 🔴 **RISCO ALTO**
- Sistema crítico rodando com falhas de segurança graves
- Dependência excessiva de Apps Script não monitorado
- Dados sensíveis expostos em múltiplos pontos

### 8.2 Ações Imediatas (< 1 semana)
1. **🔴 URGENTE**: Substituir todos os tokens hardcoded por PropertiesService
2. **🔴 URGENTE**: Implementar logs de auditoria para todas as operações
3. **🟡 IMPORTANTE**: Backup manual diário até migração completa

### 8.3 Ações de Médio Prazo (1-2 meses)
1. Migração completa para Django (já 70% pronto)
2. Implementação de API gateway segura
3. Dashboard web para substituir planilhas críticas

### 8.4 Benefícios da Migração
- ✅ **Segurança**: Controle total sobre tokens e APIs
- ✅ **Confiabilidade**: Backup, monitoring, error handling
- ✅ **Escalabilidade**: Suporte a mais usuários e dados
- ✅ **Manutenibilidade**: Código versionado e testado
- ✅ **Auditoria**: Log completo de todas as operações

---

**RECOMENDAÇÃO FINAL**: Prosseguir imediatamente com a migração para Django, priorizando os módulos de maior risco (Acompanhamento de Agenda e Controle de Compras).