# 🔐 Política de Segurança - Sistema Aprender

## 📋 Índice

- [Versões Suportadas](#-versões-suportadas)
- [Reportar Vulnerabilidades](#-reportar-vulnerabilidades)
- [Políticas de Segurança](#-políticas-de-segurança)
- [Padrões de Desenvolvimento Seguro](#-padrões-de-desenvolvimento-seguro)
- [Gestão de Segredos](#-gestão-de-segredos)
- [Integrações Externas](#-integrações-externas)
- [Compliance](#-compliance)
- [Auditoria e Logs](#-auditoria-e-logs)
- [Resposta a Incidentes](#-resposta-a-incidentes)

## 🛡️ Versões Suportadas

Mantemos suporte de segurança para as seguintes versões:

| Versão | Suporte de Segurança |
|--------|---------------------|
| 1.3.x  | ✅ Completo |
| 1.2.x  | ✅ Críticas apenas |
| 1.1.x  | ❌ Descontinuado |
| < 1.1  | ❌ Descontinuado |

**Política de Atualizações**:
- Correções críticas são aplicadas imediatamente
- Atualizações menores são lançadas mensalmente
- Versões major recebem suporte por 12 meses

## 🚨 Reportar Vulnerabilidades

### Como Reportar

Para reportar uma vulnerabilidade de segurança, **NÃO** abra uma issue pública. Use um dos canais seguros:

#### 📧 Email Seguro (Preferencial)
- **Email**: security@aprender.com
- **Criptografia**: PGP (chave disponível em https://aprender.com/.well-known/pgp-keys.asc)
- **Resposta**: Confirmação em 24h, análise completa em 72h

#### 🔒 GitHub Security Advisories
1. Acesse: [Security tab](https://github.com/USUARIO/aprender_sistema/security)
2. Clique em "Report a vulnerability"
3. Preencha o formulário detalhado

### Informações Necessárias

Inclua no seu report:
- **Descrição** clara da vulnerabilidade
- **Passos para reproduzir**
- **Impacto potencial** (CVSS score se possível)
- **Versões afetadas**
- **PoC ou evidências** (se disponível)
- **Sugestões de correção** (opcional)

### Processo de Resposta

1. **Confirmação** (24h): Recebimento confirmado
2. **Triagem** (72h): Classificação de severidade
3. **Investigação** (1-2 semanas): Análise técnica completa
4. **Correção** (urgente para críticas): Desenvolvimento do fix
5. **Disclosure** (coordenado): Publicação após correção

### SLA por Severidade

| Severidade | Tempo de Resposta | Tempo de Correção |
|------------|------------------|-------------------|
| **Crítica** | 4 horas | 24 horas |
| **Alta** | 24 horas | 1 semana |
| **Média** | 72 horas | 2 semanas |
| **Baixa** | 1 semana | Próxima release |

## 🔒 Políticas de Segurança

### Autenticação e Autorização

#### Senhas e Credenciais
- **Complexidade mínima**: 8 caracteres, maiúscula, minúscula, número
- **Rotação**: Recomendada a cada 90 dias
- **2FA**: Obrigatório para administradores e superintendência
- **Bloqueio**: Após 5 tentativas incorretas (15min)

#### Sessões
- **Timeout**: 4 horas de inatividade
- **Invalidação**: Logout em todos os dispositivos após mudança de senha
- **Cookies**: Secure, HttpOnly, SameSite=Strict em produção

### Controle de Acesso

#### Princípios
- **Least Privilege**: Permissões mínimas necessárias
- **Role-Based Access**: Baseado em perfis de usuário
- **Segregation of Duties**: Separação entre solicitante/aprovador

#### Perfis de Acesso
| Perfil | Permissões | Dados Sensíveis |
|--------|------------|----------------|
| **Formador** | Bloqueios próprios | CPF próprio |
| **Coordenador** | Solicitações | CPF próprio, dados eventos |
| **Controle** | Pré-agenda | Todos os dados |
| **Superintendência** | Aprovações | Todos os dados |
| **Diretoria** | Relatórios | Dados agregados |
| **Admin** | Sistema completo | Todos os dados |

### Proteção de Dados

#### Dados Pessoais (LGPD)
- **CPF**: Hasheado em produção, mascarado em logs
- **Telefone/Email**: Criptografados na base
- **Dados de acesso**: Logs anonimizados após 90 dias
- **Consentimento**: Explícito para uso de dados

#### Backups
- **Frequência**: Diário (produção), semanal (staging)
- **Criptografia**: AES-256 para backups
- **Retenção**: 90 dias (operacional), 7 anos (compliance)
- **Teste**: Restore mensal para validação

## 🛠️ Padrões de Desenvolvimento Seguro

### Code Reviews Obrigatórios

Todos os PRs devem ter:
- [ ] **Security review** por membro sênior
- [ ] **SAST scan** (Static Application Security Testing)
- [ ] **Dependency check** para vulnerabilidades conhecidas
- [ ] **Input validation** review
- [ ] **Authorization check** review

### Checklist de Segurança

#### Para cada nova feature:
- [ ] Input validation implementada
- [ ] Output encoding aplicado
- [ ] Authorization checks em todas as rotas
- [ ] Logs de auditoria adicionados
- [ ] Testes de segurança incluídos
- [ ] Documentação de segurança atualizada

#### Para integrações externas:
- [ ] Timeout e retry configurados
- [ ] Rate limiting implementado
- [ ] Error handling que não vaza informações
- [ ] Credenciais via variáveis de ambiente
- [ ] Logs de integração (sem dados sensíveis)

### Ferramentas Obrigatórias

```yaml
# .pre-commit-config.yaml (já implementado)
- repo: https://github.com/PyCQA/bandit
  hooks:
    - id: bandit  # Security linting
- repo: https://github.com/Lucas-C/pre-commit-hooks
  hooks:
    - id: remove-private-key  # Prevent key commits
```

## 🔑 Gestão de Segredos

### Variáveis de Ambiente

#### Produção
```bash
# Críticas (nunca em logs)
SECRET_KEY=xxx
DATABASE_URL=postgresql://xxx
GOOGLE_CREDENTIALS_JSON={"type":"service_account"...}

# Configuração
ENVIRONMENT=production
ALLOWED_HOSTS=aprender.com,api.aprender.com
CSRF_TRUSTED_ORIGINS=https://aprender.com
```

#### Desenvolvimento
```bash
# Use .env.example como base
cp .env.example .env
# Configure apenas as necessárias para desenvolvimento
```

### Rotação de Secrets

| Secret | Rotação | Responsável |
|--------|---------|-------------|
| **SECRET_KEY** | Anual | DevOps |
| **DB Password** | Trimestral | DevOps |
| **Google Service Account** | Anual | Admin |
| **API Keys externas** | Semestral | DevOps |

### Secrets em CI/CD

- **GitHub Secrets**: Para credenciais de deploy
- **Environment separation**: Produção ≠ Staging ≠ Development
- **Minimal access**: Cada ambiente só acessa seus próprios secrets
- **Audit trail**: Logs de uso de secrets

## 🌐 Integrações Externas

### Google Calendar API
- **Scopes mínimos**: Apenas calendário específico
- **Service Account**: Dedicado para o sistema
- **Rate limiting**: Respeitado (100 requests/user/100s)
- **Error handling**: Graceful degradation
- **Monitoring**: Alertas para falhas de sync

### Google Sheets API
- **Read-only access**: Para importação de dados históricos
- **Validation**: Todos os dados importados são validados
- **Audit**: Log completo de importações

### Segurança de Integrações
```python
# Exemplo de padrão seguro
class GoogleCalendarService:
    def __init__(self):
        self.timeout = 30  # Timeout obrigatório
        self.max_retries = 3
        
    def create_event(self, event_data):
        try:
            # Validar dados antes de enviar
            self.validate_event_data(event_data)
            # Implementar com retry e timeout
            return self.api_call_with_retry(event_data)
        except Exception as e:
            # Log sem dados sensíveis
            logger.error(f"Calendar integration failed: {type(e).__name__}")
            raise IntegrationError("Failed to create calendar event")
```

## ⚖️ Compliance

### LGPD (Lei Geral de Proteção de Dados)
- **Base legal**: Interesse legítimo (gestão educacional)
- **Finalidade**: Agendamento de eventos formativos
- **Minimização**: Apenas dados necessários
- **Transparência**: Política de privacidade clara
- **Direitos**: Portal para exercício de direitos

### ISO 27001 (Controles Aplicáveis)
- **A.9**: Controle de acesso
- **A.10**: Criptografia
- **A.12**: Segurança operacional
- **A.14**: Desenvolvimento seguro

### Auditoria Externa
- **Frequência**: Anual
- **Escopo**: Controles técnicos e processos
- **Relatório**: Disponível para stakeholders

## 📊 Auditoria e Logs

### Eventos Auditados
- **Autenticação**: Login/logout (sucesso e falha)
- **Autorização**: Acessos negados
- **Dados**: CRUD em models críticos
- **Integrações**: Calls para APIs externas
- **Administração**: Mudanças de configuração

### Formato de Logs
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "event": "approval_created",
  "user_id": "admin",
  "resource": "solicitacao_123",
  "action": "approve",
  "ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "previous_status": "pending",
    "new_status": "approved"
  }
}
```

### Retenção de Logs
- **Aplicação**: 90 dias (local), 1 ano (backup)
- **Auditoria**: 7 anos (compliance)
- **Anonização**: Após 90 dias (dados pessoais)

## 🚨 Resposta a Incidentes

### Classificação de Incidentes

#### Severidade 1 - Crítica
- **Exemplos**: Data breach, RCE, admin compromise
- **Resposta**: Imediata (< 1 hora)
- **Escalação**: CTO + Legal + Compliance

#### Severidade 2 - Alta  
- **Exemplos**: SQL injection, privilege escalation
- **Resposta**: 4 horas
- **Escalação**: Lead Developer + Security Officer

#### Severidade 3 - Média
- **Exemplos**: XSS, information disclosure
- **Resposta**: 24 horas
- **Escalação**: Development Team

### Playbook de Resposta

1. **Contenção** (minutos)
   - Isolar sistemas afetados
   - Preservar evidências
   - Comunicar internamente

2. **Investigação** (horas)
   - Análise de logs
   - Identificação de causa raiz
   - Avaliação de impacto

3. **Remediação** (dias)
   - Aplicar correções
   - Validar efetividade
   - Restaurar serviços

4. **Comunicação** (conforme necessário)
   - Stakeholders internos
   - Usuários afetados
   - Autoridades (se aplicável)

5. **Post-Mortem** (sempre)
   - Documentar timeline
   - Identificar melhorias
   - Atualizar processos

### Contatos de Emergência

- **Security Officer**: security@aprender.com
- **CTO**: cto@aprender.com  
- **Legal**: legal@aprender.com
- **24/7 Hotline**: +55 85 9999-9999

## 📞 Recursos Adicionais

### Documentação
- **Security Wiki**: https://wiki.aprender.com/security
- **OWASP Top 10**: Guia interno de mitigações
- **Secure Coding**: Padrões e exemplos

### Treinamento
- **Onboarding**: Módulo de segurança obrigatório
- **Continuous**: Workshops trimestrais
- **Phishing**: Simulações semestrais

### Ferramentas
- **SAST**: Bandit (Python), ESLint security plugin
- **DAST**: OWASP ZAP (staging environment)
- **SCA**: Safety (Python dependencies)
- **Monitoring**: Alertas customizados no Grafana

---

## 🏷️ Versioning

Esta política segue versionamento semântico:
- **Major**: Mudanças que afetam compliance
- **Minor**: Adição de novos controles
- **Patch**: Correções e clarificações

**Versão atual**: 1.0.0  
**Última atualização**: 2025-09-11  
**Próxima revisão**: 2025-12-11  

---

<div align="center">
  <strong>🛡️ Security First - Sistema Aprender</strong><br>
  <em>Protegendo dados educacionais com excelência técnica</em>
</div>