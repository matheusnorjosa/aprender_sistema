# Auditoria de Responsabilidades: Django AS vs Google Planilhas

**Data:** 2025-08-22  
**Objetivo:** Validar se as permissões atuais do Django AS estão 100% alinhadas com as responsabilidades reais das planilhas

## 1. RESUMO EXECUTIVO

### 1.1 Status Geral: 🟡 **70% ALINHADO**
- **30 responsabilidades** mapeadas entre planilhas e Django
- **12 alinhamentos corretos** (40%)
- **11 gaps críticos** (37%) 
- **7 parciais/restritivos** (23%)

### 1.2 Principais Problemas Identificados
1. **🔴 Coordenadores limitados**: Não conseguem gerenciar formações nem disponibilidades
2. **🔴 Controle sem sync**: Grupo controle perdeu acesso à sincronização de calendários  
3. **🔴 Formadores restritos**: Não conseguem gerenciar própria disponibilidade
4. **🔴 Dados mestres concentrados**: Apenas admin gerencia cadastros básicos

## 2. ANÁLISE DETALHADA POR PERFIL

### 2.1 COORDENADOR (11 responsabilidades)
| Status | Responsabilidade | Gap/Problema |
|--------|------------------|--------------|
| ✅ | Criar solicitações eventos | Alinhado |
| ✅ | Editar solicitações pendentes | Alinhado |
| 🔴 | Registrar formações | **GAP**: não tem add_formacao |
| 🔴 | Editar dados formação | **GAP**: não tem change_formacao |
| 🔴 | Controlar deslocamentos | **GAP**: sem acesso a Deslocamento |
| 🔴 | Ver agenda formador específico | **GAP**: falta view específica |
| 🔴 | Bloquear agenda formador | **GAP**: não gerencia disponibilidade |
| ⚠️ | Acompanhar status eventos | **LIMITADO**: só vê próprias solicitações |

**Impacto**: Coordenadores não conseguem executar 50% de suas responsabilidades originais das planilhas.

### 2.2 SUPERINTENDÊNCIA (3 responsabilidades)
| Status | Responsabilidade | Gap/Problema |
|--------|------------------|--------------|
| ✅ | Aprovar/reprovar eventos | Alinhado |
| ✅ | Ver todas solicitações | Alinhado |
| ✅ | Monitorar calendário mensal | Alinhado |

**Impacto**: Perfil bem alinhado, sem gaps críticos.

### 2.3 CONTROLE (8 responsabilidades)
| Status | Responsabilidade | Gap/Problema |
|--------|------------------|--------------|
| ✅ | Criar/processar compras | Alinhado |
| ✅ | Auditar operações | Alinhado |
| 🔴 | Sincronizar Google Calendar | **GAP**: perdeu sync_calendar |
| 🔴 | Importar dados externos | **GAP**: sem permissão importação |
| 🔴 | Cadastrar formadores | **GAP**: sem add_formador |
| 🔴 | Editar dados formador | **GAP**: sem change_formador |
| 🔴 | Gerenciar municípios | **GAP**: sem permissões Municipio |
| 🔴 | Gerenciar projetos | **GAP**: sem permissões Projeto |

**Impacto**: Controle perdeu 75% das capacidades de gestão de dados mestres.

### 2.4 FORMADOR (2 responsabilidades)
| Status | Responsabilidade | Gap/Problema |
|--------|------------------|--------------|
| ⚠️ | Visualizar próprios eventos | **PARCIAL**: falta filtro automático |
| 🔴 | Gerenciar disponibilidade | **GAP**: não tem add/change_disponibilidadeformadores |

**Impacto**: Formadores não conseguem autogerenciar disponibilidade como nas planilhas.

### 2.5 DIRETORIA (2 responsabilidades)  
| Status | Responsabilidade | Gap/Problema |
|--------|------------------|--------------|
| ✅ | Ver relatórios consolidados | Alinhado |
| ⚠️ | Gerar relatório anual | **PARCIAL**: falta dashboard específico |

**Impacto**: Funcionalidade básica preservada, melhorias necessárias.

### 2.6 ADMIN (3 responsabilidades)
| Status | Responsabilidade | Gap/Problema |
|--------|------------------|--------------|
| ✅ | Configurar sistema | Alinhado |
| ⚠️ | Conectar formador a usuário | **RESTRITIVO**: controle deveria poder |
| ✅ | Gerenciar dados mestres | Alinhado |

**Impacto**: Admin mantém controle total, talvez excessivo.

## 3. ANÁLISE DE FUNCIONALIDADES AUTOMATIZADAS

### 3.1 Funcionalidades Perdidas
| Funcionalidade Planilha | Status Django | Criticidade |
|-------------------------|---------------|-------------|
| Notificações automáticas | 🔴 **FALTANTE** | ALTA |
| Backup automático | 🔴 **FALTANTE** | ALTA |
| APIs externas | 🔴 **FALTANTE** | MÉDIA |
| Processamento em lote agendado | ⚠️ **MANUAL** | MÉDIA |

### 3.2 Funcionalidades Melhoradas
| Funcionalidade | Status | Melhoria |
|----------------|--------|----------|
| Log de auditoria | ✅ **MELHOR** | Mais estruturado que planilhas |
| Validação de dados | ⚠️ **BÁSICO** | Menos robusta que Apps Script |

## 4. GAPS CRÍTICOS POR CATEGORIA

### 4.1 🔴 Gaps de Permissão (11 gaps)
1. **coordenador**: add_formacao, change_formacao
2. **coordenador**: add/change_deslocamento  
3. **coordenador**: view_formador_events (view específica)
4. **controle**: sync_calendar
5. **controle**: add/change_formador
6. **controle**: add/change_municipio, add/change_projeto
7. **formador**: add/change_disponibilidadeformadores

### 4.2 ⚠️ Gaps de Funcionalidade (7 gaps)
1. Filtro automático eventos por formador
2. Dashboard analítico para diretoria
3. Sistema de notificações
4. Backup automático
5. Integração APIs externas  
6. Agendamento de processamento em lote
7. Validação robusta de dados

### 4.3 🔴 Gaps de Interface (3 gaps)
1. View específica para agenda por formador
2. Interface de disponibilidade para formadores  
3. Dashboard executivo para diretoria

## 5. IMPACTO POR GRUPO DE USUÁRIO

### 5.1 Alto Impacto (Grupos Problemáticos)
- **COORDENADOR**: 5 gaps críticos - não consegue gerenciar formações nem disponibilidades
- **CONTROLE**: 6 gaps críticos - perdeu capacidades de gestão de dados mestres
- **FORMADOR**: 1 gap crítico - não consegue autogerenciar agenda

### 5.2 Médio Impacto
- **DIRETORIA**: 1 gap médio - dashboard limitado

### 5.3 Baixo Impacto
- **SUPERINTENDÊNCIA**: Bem alinhado
- **ADMIN**: Mantém controle total

## 6. COMPARAÇÃO QUANTITATIVA

### 6.1 Planilhas vs Django - Capacidades por Perfil
| Perfil | Capacidades Planilhas | Capacidades Django | % Preservado |
|--------|----------------------|-------------------|--------------|
| Coordenador | 8 | 4 | **50%** 🔴 |
| Superintendência | 3 | 3 | **100%** ✅ |  
| Controle | 8 | 2 | **25%** 🔴 |
| Formador | 2 | 1 | **50%** 🔴 |
| Diretoria | 2 | 2 | **100%** ✅ |
| Admin | 3 | 3 | **100%** ✅ |

### 6.2 Funcionalidades Automatizadas
| Categoria | Planilhas | Django | Status |
|-----------|-----------|--------|--------|
| Triggers automáticos | 6 | 3 | 🔴 **50% perdido** |
| Validações entrada | Robusta | Básica | ⚠️ **Degradada** |
| Integrações externas | 5 APIs | 0 APIs | 🔴 **100% perdido** |
| Backup/Recovery | Automático | Manual | 🔴 **Degradado** |

## 7. RISCOS OPERACIONAIS IDENTIFICADOS

### 7.1 🔴 Riscos Críticos
1. **Coordenadores bloqueados**: Não conseguem registrar formações → impacto na operação
2. **Controle limitado**: Não consegue sincronizar calendários → desalinhamento
3. **Formadores dependentes**: Não gerenciam própria agenda → overhead administrativo
4. **Dados mestres centralizados**: Apenas admin gerencia → gargalo operacional

### 7.2 ⚠️ Riscos Médios
1. **Falta de notificações**: Usuários não sabem de mudanças
2. **Sem backup automático**: Risco de perda de dados
3. **Validação insuficiente**: Possível entrada de dados inconsistentes

## 8. CONCLUSÕES E RECOMENDAÇÕES

### 8.1 Status Atual: 🔴 **CRÍTICO**
O sistema Django AS **NÃO está 100% alinhado** com as responsabilidades das planilhas. Existem gaps significativos que impactam a operação diária.

### 8.2 Ações Prioritárias (< 1 semana)
1. **🔴 URGENTE**: Restaurar sync_calendar para grupo controle
2. **🔴 URGENTE**: Dar permissões de formação para coordenadores
3. **🔴 URGENTE**: Permitir formadores gerenciarem disponibilidade

### 8.3 Ações de Médio Prazo (1-4 semanas)
1. Redistribuir permissões de dados mestres para controle
2. Criar views específicas para agenda por formador
3. Implementar sistema de notificações básico
4. Configurar backup automático

### 8.4 Ações de Longo Prazo (1-3 meses)
1. Implementar integrações de APIs externas
2. Criar dashboard executivo avançado
3. Melhorar validação de dados de entrada
4. Implementar agendamento de processamento

---

**RECOMENDAÇÃO FINAL**: Executar imediatamente o plano de ajustes de permissões para restaurar a funcionalidade operacional básica, priorizando coordenadores e controle.

**PRÓXIMO PASSO**: Revisar arquivo `ajustes_permissoes.md` para implementação detalhada.