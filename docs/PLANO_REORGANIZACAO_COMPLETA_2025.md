# 🚀 PLANO COMPLETO DE REORGANIZAÇÃO - SISTEMA APRENDER 2025

## 📋 **VISÃO GERAL**

Agora que temos acesso total às planilhas originais do Google Drive, vamos fazer uma **reorganização completa** do sistema para:
- ✅ Limpar dados antigos/duplicados
- ✅ Normalizar estrutura de dados
- ✅ Implementar fonte única de verdade
- ✅ Preparar para dados de 2025

---

## 🎯 **OBJETIVOS PRINCIPAIS**

1. **🧹 Limpeza Completa**: Remover dados inconsistentes/duplicados
2. **📊 Normalização**: Estruturar dados de forma padronizada
3. **🔗 Integração**: Conectar com planilhas originais do Drive
4. **📅 Preparação 2025**: Otimizar para dados do próximo ano
5. **🛡️ Backup**: Preservar dados importantes antes da limpeza

---

## 📊 **FASE 1: ANÁLISE E AUDITORIA ATUAL**

### **1.1 Inventário de Dados Atuais**
- [ ] **Docker/PostgreSQL**: Analisar dados no banco
- [ ] **Arquivos Locais**: Mapear todos os JSONs/CSVs
- [ ] **Planilhas Importadas**: Verificar dados já importados
- [ ] **Backups**: Identificar backups importantes

### **1.2 Identificação de Problemas**
- [ ] **Duplicações**: Encontrar registros duplicados
- [ ] **Inconsistências**: Identificar dados conflitantes
- [ ] **Estruturas Antigas**: Mapear schemas desatualizados
- [ ] **Referências Quebradas**: Encontrar links inválidos

### **1.3 Mapeamento de Dependências**
- [ ] **Relacionamentos**: Mapear FK e dependências
- [ ] **Integrações**: Identificar sistemas conectados
- [ ] **APIs**: Verificar endpoints dependentes
- [ ] **Relatórios**: Mapear dashboards afetados

---

## 🧹 **FASE 2: LIMPEZA E BACKUP**

### **2.1 Backup Completo**
- [ ] **Backup PostgreSQL**: Dump completo do banco
- [ ] **Backup Arquivos**: Copiar todos os JSONs/CSVs
- [ ] **Backup Docker**: Exportar volumes
- [ ] **Backup Configurações**: Salvar settings

### **2.2 Limpeza do Docker**
- [ ] **Parar Containers**: Parar todos os serviços
- [ ] **Limpar Volumes**: Remover dados antigos
- [ ] **Reset PostgreSQL**: Recriar banco limpo
- [ ] **Limpar Logs**: Remover logs antigos

### **2.3 Limpeza de Arquivos Locais**
- [ ] **JSONs Antigos**: Mover para pasta de backup
- [ ] **CSVs Temporários**: Limpar arquivos temporários
- [ ] **Logs**: Limpar logs antigos
- [ ] **Cache**: Limpar cache do sistema

---

## 🏗️ **FASE 3: NOVA ESTRUTURA DE DADOS**

### **3.1 Design da Nova Estrutura**
- [ ] **Schema PostgreSQL**: Projetar nova estrutura
- [ ] **Tabelas Principais**: Definir entidades core
- [ ] **Relacionamentos**: Mapear FK otimizadas
- [ ] **Índices**: Projetar índices para performance

### **3.2 Estrutura Proposta**

#### **📊 Tabelas Principais:**
```sql
-- Usuários e Organização
usuarios (id, nome, email, cargo, gerencia, ativo)
projetos (id, nome, descricao, coordenador_id, ativo)
municipios (id, nome, uf, regiao, ativo)

-- Eventos e Formações
eventos (id, titulo, data_inicio, data_fim, projeto_id, municipio_id, status)
formadores_evento (evento_id, formador_id, papel)
disponibilidade (formador_id, data, status, observacoes)

-- Controle e Aprovação
solicitacoes (id, evento_id, usuario_id, status, data_solicitacao)
aprovacoes (id, solicitacao_id, aprovador_id, status, data_aprovacao)

-- Produtos e Compras
produtos (id, nome, categoria, descricao)
compras (id, produto_id, municipio_id, quantidade, data_compra)
```

### **3.3 Normalização de Dados**
- [ ] **Padronização**: Definir formatos padrão
- [ ] **Validação**: Criar regras de validação
- [ ] **Transformação**: Mapear dados antigos → novos
- [ ] **Migração**: Scripts de migração

---

## 🔄 **FASE 4: INTEGRAÇÃO COM PLANILHAS ORIGINAIS**

### **4.1 Mapeamento das Planilhas**
- [ ] **Planilha 1**: Disponibilidade | 2025
- [ ] **Planilha 2**: Controle - 2025
- [ ] **Planilha 3**: Agenda | 2025
- [ ] **Planilha 4**: Usuários

### **4.2 Scripts de Importação**
- [ ] **Importador Usuários**: Da planilha de usuários
- [ ] **Importador Eventos**: Da planilha de agenda
- [ ] **Importador Disponibilidade**: Da planilha de disponibilidade
- [ ] **Importador Controle**: Da planilha de controle

### **4.3 Sincronização Automática**
- [ ] **Webhooks**: Configurar atualizações automáticas
- [ ] **Scheduler**: Agendar sincronizações
- [ ] **Monitoramento**: Logs de sincronização
- [ ] **Alertas**: Notificações de erros

---

## 📅 **FASE 5: PREPARAÇÃO PARA 2025**

### **5.1 Dados de 2025 Identificados**
- [ ] **10.756 referências** ao ano 2025
- [ ] **Eventos/Formações**: 754 registros
- [ ] **Datas**: 8.220 registros
- [ ] **Projetos/Ações**: 15 registros

### **5.2 Estrutura para 2025**
- [ ] **Tabela eventos_2025**: Eventos específicos de 2025
- [ ] **Tabela disponibilidade_2025**: Disponibilidade para 2025
- [ ] **Tabela projetos_2025**: Projetos ativos em 2025
- [ ] **Tabela bloqueios_2025**: Bloqueios e indisponibilidades

### **5.3 Otimizações**
- [ ] **Índices por ano**: Otimizar consultas por 2025
- [ ] **Partitioning**: Separar dados por ano
- [ ] **Cache**: Cache para dados frequentes
- [ ] **APIs**: Endpoints otimizados

---

## 🛠️ **FASE 6: IMPLEMENTAÇÃO**

### **6.1 Desenvolvimento**
- [ ] **Scripts de Limpeza**: Automatizar limpeza
- [ ] **Scripts de Migração**: Migrar dados antigos
- [ ] **Scripts de Importação**: Importar das planilhas
- [ ] **APIs**: Criar endpoints para nova estrutura

### **6.2 Testes**
- [ ] **Testes Unitários**: Validar funções
- [ ] **Testes de Integração**: Validar importações
- [ ] **Testes de Performance**: Validar performance
- [ ] **Testes de Carga**: Validar com dados reais

### **6.3 Deploy**
- [ ] **Ambiente de Teste**: Deploy em ambiente de teste
- [ ] **Validação**: Validar com dados reais
- [ ] **Produção**: Deploy em produção
- [ ] **Monitoramento**: Monitorar pós-deploy

---

## 📊 **FASE 7: VALIDAÇÃO E MONITORAMENTO**

### **7.1 Validação de Dados**
- [ ] **Integridade**: Verificar integridade dos dados
- [ ] **Completude**: Verificar se todos os dados foram importados
- [ ] **Consistência**: Verificar consistência entre tabelas
- [ ] **Qualidade**: Validar qualidade dos dados

### **7.2 Monitoramento**
- [ ] **Logs**: Monitorar logs de importação
- [ ] **Performance**: Monitorar performance do sistema
- [ ] **Erros**: Monitorar erros e exceções
- [ ] **Alertas**: Configurar alertas automáticos

---

## ⏱️ **CRONOGRAMA ESTIMADO**

| Fase | Duração | Descrição |
|------|---------|-----------|
| **Fase 1** | 2-3 dias | Análise e auditoria |
| **Fase 2** | 1-2 dias | Limpeza e backup |
| **Fase 3** | 3-4 dias | Nova estrutura |
| **Fase 4** | 4-5 dias | Integração planilhas |
| **Fase 5** | 2-3 dias | Preparação 2025 |
| **Fase 6** | 5-7 dias | Implementação |
| **Fase 7** | 2-3 dias | Validação |

**Total Estimado: 19-27 dias**

---

## 🎯 **ENTREGÁVEIS**

### **📋 Documentação**
- [ ] **Especificação Técnica**: Nova estrutura de dados
- [ ] **Manual de Migração**: Como migrar dados
- [ ] **Manual de Importação**: Como importar das planilhas
- [ ] **Manual de Manutenção**: Como manter o sistema

### **💻 Código**
- [ ] **Scripts de Limpeza**: Automatizar limpeza
- [ ] **Scripts de Migração**: Migrar dados
- [ ] **Scripts de Importação**: Importar das planilhas
- [ ] **APIs**: Endpoints para nova estrutura

### **📊 Dados**
- [ ] **Banco Limpo**: PostgreSQL com nova estrutura
- [ ] **Dados Normalizados**: Dados de 2025 estruturados
- [ ] **Backups**: Backups de segurança
- [ ] **Logs**: Logs de todas as operações

---

## 🚨 **RISCOS E MITIGAÇÕES**

### **⚠️ Riscos Identificados**
1. **Perda de Dados**: Durante limpeza/migração
2. **Downtime**: Sistema indisponível durante migração
3. **Inconsistências**: Dados não migrados corretamente
4. **Performance**: Sistema lento após migração

### **🛡️ Mitigações**
1. **Backups Múltiplos**: Backup antes de cada operação
2. **Migração Gradual**: Migrar em etapas
3. **Validação Rigorosa**: Testar cada etapa
4. **Monitoramento**: Monitorar performance continuamente

---

## ✅ **CRITÉRIOS DE SUCESSO**

- [ ] **100% dos dados** de 2025 importados corretamente
- [ ] **0% de perda** de dados importantes
- [ ] **Performance** igual ou melhor que atual
- [ ] **Sistema estável** e funcionando
- [ ] **Documentação completa** entregue

---

## 🚀 **PRÓXIMOS PASSOS**

1. **✅ Aprovação do Plano**: Confirmar se está de acordo
2. **📋 Priorização**: Definir quais fases são mais críticas
3. **⏱️ Cronograma**: Ajustar cronograma conforme necessário
4. **🛠️ Início**: Começar pela Fase 1 (Análise e Auditoria)

---

**🎯 Objetivo Final**: Sistema limpo, organizado e otimizado para receber e processar todos os dados de 2025 de forma eficiente e estruturada.
