# Documentação e Histórico do Projeto - Aprender Sistema (AS)

## 1. Visão Geral do Projeto

O projeto **Aprender Sistema (AS)** tem como objetivo substituir planilhas por um sistema web integrado para solicitação, aprovação e criação de eventos educacionais, com verificação automática de conflitos de agenda e logs de auditoria.

### Stack Tecnológica
- **Backend**: Python 3.13 + Django 5.2
- **Banco de Dados**: PostgreSQL 15
- **Containerização**: Docker + docker-compose
- **Frontend**: Templates Django + Bootstrap 5.3
- **Integração**: Google Calendar API + Google Meet

### Fuso Horário
- Padrão: `America/Fortaleza`

## 2. Requisitos Funcionais

### RF01 - Gerenciamento de Dados Mestres
**Descrição**: O Admin do Sistema deve poder gerenciar todos os dados mestres do sistema, incluindo cadastros de referência e configurações base necessárias para o funcionamento da aplicação.

**Atores**: Admin do Sistema

**Pré-condições**: 
- Usuário autenticado com papel "Admin do Sistema"
- Acesso ao Django Admin ou interface específica

**Fluxo Principal**:
1. Admin acessa a interface de administração
2. Seleciona a categoria de dados mestres a gerenciar
3. Realiza operações CRUD (Create, Read, Update, Delete) conforme necessário
4. Sistema registra alterações no log de auditoria
5. Dados são persistidos no banco de dados

**Pós-condições**:
- Dados mestres atualizados no sistema
- Log de auditoria registrado
- Validações de integridade mantidas

**Dados Mestres Gerenciados**:
- Projetos
- Municípios
- Tipos de Evento
- Formadores
- Configurações de Disponibilidade

### RF02 - Solicitar Evento
**Descrição**: Permitir que coordenadores criem solicitações de eventos educacionais.

### RF03 - Verificar Conflitos
**Descrição**: Verificar automaticamente conflitos de agenda dos formadores.

### RF04 - Aprovar/Reprovar Solicitações
**Descrição**: Permitir que superintendência e diretoria aprovem ou reprovem solicitações.

### RF05 - Criar Evento no Google Calendar
**Descrição**: Criar automaticamente eventos no Google Calendar após aprovação.

### RF06 - Gerar Link do Google Meet
**Descrição**: Gerar automaticamente links do Google Meet para eventos online.

### RF07 - Logs de Auditoria
**Descrição**: Registrar todas as ações realizadas no sistema para auditoria.

## 3. Papéis e Perfis de Usuário

### Hierarquia de Papéis
1. **Coordenador**: Criação de solicitações
2. **Superintendência**: Aprovação de solicitações
3. **Controle**: Gestão de eventos e calendar
4. **Formador**: Consulta de agendamentos
5. **Admin do Sistema**: Gestão completa dos dados mestres
6. **Diretoria**: Aprovação final de solicitações

### Permissões por Papel

#### Admin do Sistema
- **Projetos**: CRUD completo
- **Municípios**: CRUD completo  
- **Tipos de Evento**: CRUD completo
- **Formadores**: CRUD completo
- **Solicitações**: CRUD completo
- **Aprovações**: CRUD completo
- **Eventos Google Calendar**: CRUD completo
- **Disponibilidade de Formadores**: CRUD completo
- **Logs de Auditoria**: CRUD completo

## 4. Modelo de Dados

### 4.1 Entidades Principais - Dados Mestres (RF01)

#### Tabela: core_projeto
**Descrição**: Cadastro dos projetos educacionais disponíveis no sistema.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | UUID | Identificador único | PRIMARY KEY |
| nome | VARCHAR(255) | Nome do projeto | UNIQUE, NOT NULL |
| descricao | TEXT | Descrição detalhada | NULLABLE |
| ativo | BOOLEAN | Status do projeto | DEFAULT TRUE |

**Índices**:
- `PRIMARY KEY (id)`
- `UNIQUE INDEX (nome)`
- `INDEX (nome)` para ordenação

#### Tabela: core_municipio
**Descrição**: Cadastro dos municípios onde os eventos podem ocorrer.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | UUID | Identificador único | PRIMARY KEY |
| nome | VARCHAR(255) | Nome do município | NOT NULL |
| uf | VARCHAR(2) | Unidade Federativa | DEFAULT '' |
| ativo | BOOLEAN | Status do município | DEFAULT TRUE |

**Índices**:
- `PRIMARY KEY (id)`
- `UNIQUE INDEX (nome, uf)`
- `INDEX (nome, uf)` para busca e ordenação

#### Tabela: core_tipievento
**Descrição**: Tipos de eventos educacionais suportados pelo sistema.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | UUID | Identificador único | PRIMARY KEY |
| nome | VARCHAR(255) | Nome do tipo de evento | UNIQUE, NOT NULL |
| online | BOOLEAN | Indica se é evento online | DEFAULT FALSE |
| ativo | BOOLEAN | Status do tipo | DEFAULT TRUE |

**Índices**:
- `PRIMARY KEY (id)`
- `UNIQUE INDEX (nome)`
- `INDEX (nome)` para ordenação

#### Tabela: core_formador
**Descrição**: Cadastro dos formadores disponíveis para ministrar eventos.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | UUID | Identificador único | PRIMARY KEY |
| nome | VARCHAR(255) | Nome completo do formador | NOT NULL |
| email | VARCHAR(255) | E-mail do formador | UNIQUE, NOT NULL |
| area_atuacao | VARCHAR(255) | Área de especialização | NULLABLE |
| ativo | BOOLEAN | Status do formador | DEFAULT TRUE |

**Índices**:
- `PRIMARY KEY (id)`
- `UNIQUE INDEX (email)`
- `INDEX (email)` para busca rápida
- `INDEX (nome)` para ordenação

### 4.2 Entidades de Controle de Usuários

#### Tabela: core_usuario (extends AbstractUser)
**Descrição**: Usuários do sistema com papéis específicos.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | INTEGER | Identificador único | PRIMARY KEY |
| username | VARCHAR(150) | Nome de usuário | UNIQUE, NOT NULL |
| email | VARCHAR(254) | E-mail do usuário | NULLABLE |
| papel | VARCHAR(50) | Papel do usuário no sistema | NOT NULL |

**Valores para papel**:
- `coordenador`: Coordenador
- `superintendencia`: Superintendência  
- `controle`: Controle
- `formador`: Formador
- `admin`: Admin do Sistema
- `diretoria`: Diretoria

### 4.3 Entidades Operacionais

#### Tabela: core_solicitacao
**Descrição**: Solicitações de eventos criadas pelos coordenadores.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | UUID | Identificador único | PRIMARY KEY |
| usuario_solicitante_id | INTEGER | FK para Usuario | FOREIGN KEY, NOT NULL |
| projeto_id | UUID | FK para Projeto | FOREIGN KEY, NOT NULL |
| municipio_id | UUID | FK para Municipio | FOREIGN KEY, NOT NULL |
| tipo_evento_id | UUID | FK para TipoEvento | FOREIGN KEY, NOT NULL |
| titulo_evento | VARCHAR(255) | Título do evento | NOT NULL |
| data_solicitacao | TIMESTAMP | Data de criação | AUTO_NOW_ADD |
| data_inicio | TIMESTAMP | Data/hora de início | NOT NULL |
| data_fim | TIMESTAMP | Data/hora de fim | NOT NULL |
| numero_encontro_formativo | VARCHAR(50) | Número do encontro | NULLABLE |
| coordenador_acompanha | BOOLEAN | Coordenador acompanha | DEFAULT FALSE |
| observacoes | TEXT | Observações adicionais | NULLABLE |
| status | VARCHAR(20) | Status da solicitação | DEFAULT 'Pendente' |
| usuario_aprovador_id | INTEGER | FK para Usuario aprovador | FOREIGN KEY, NULLABLE |
| data_aprovacao_rejeicao | TIMESTAMP | Data da decisão | NULLABLE |
| justificativa_rejeicao | TEXT | Justificativa se reprovado | NULLABLE |

**Índices**:
- `PRIMARY KEY (id)`
- `INDEX (data_inicio)`
- `INDEX (data_fim)`
- `INDEX (status)`
- `INDEX (data_solicitacao)` para ordenação DESC

#### Tabela: core_formadoressolicitacao
**Descrição**: Relacionamento many-to-many entre Solicitações e Formadores.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | INTEGER | Identificador único | PRIMARY KEY |
| solicitacao_id | UUID | FK para Solicitacao | FOREIGN KEY, NOT NULL |
| formador_id | UUID | FK para Formador | FOREIGN KEY, NOT NULL |

**Índices**:
- `PRIMARY KEY (id)`
- `UNIQUE INDEX (solicitacao_id, formador_id)`

### 4.4 Entidades de Auditoria

#### Tabela: core_logauditoria
**Descrição**: Registro de todas as ações realizadas no sistema para auditoria.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|-------------|
| id | UUID | Identificador único | PRIMARY KEY |
| usuario_id | INTEGER | FK para Usuario | FOREIGN KEY, NULLABLE |
| data_hora | TIMESTAMP | Data/hora da ação | AUTO_NOW_ADD |
| acao | VARCHAR(255) | Descrição da ação | NOT NULL |
| entidade_afetada_id | UUID | ID da entidade modificada | NULLABLE |
| detalhes | TEXT | Detalhes adicionais | NULLABLE |

**Índices**:
- `PRIMARY KEY (id)`
- `INDEX (data_hora)` para ordenação DESC
- `INDEX (usuario_id)`

## 5. Implementação do RF01

### 5.1 Permissões Configuradas

O sistema implementa permissões específicas para o papel "Admin do Sistema" através do comando de gerenciamento `setup_roles.py`:

```python
"Admin do Sistema": [
    (models.Projeto, ["add", "view", "change", "delete"]),
    (models.Municipio, ["add", "view", "change", "delete"]),
    (models.TipoEvento, ["add", "view", "change", "delete"]),
    (models.Formador, ["add", "view", "change", "delete"]),
    (models.Solicitacao, ["add", "view", "change", "delete"]),
    (models.Aprovacao, ["add", "view", "change", "delete"]),
    (models.EventoGoogleCalendar, ["add", "view", "change", "delete"]),
    (models.DisponibilidadeFormadores, ["add", "view", "change", "delete"]),
    (models.LogAuditoria, ["add", "view", "change", "delete"]),
]
```

### 5.2 Interface Django Admin

Todas as entidades de dados mestres são registradas no Django Admin com interfaces específicas para gerenciamento:

- **ProjetoAdmin**: Gestão de projetos com filtros por status
- **MunicipioAdmin**: Gestão de municípios com filtros por UF e status  
- **TipoEventoAdmin**: Gestão de tipos de evento com filtros por modalidade
- **FormadorAdmin**: Gestão de formadores com busca por nome, email e área

### 5.3 Validações de Integridade

- **Projetos**: Nome único obrigatório
- **Municípios**: Combinação nome+UF única
- **Tipos de Evento**: Nome único obrigatório
- **Formadores**: Email único obrigatório

## 6. Comandos de Gerenciamento

### Configuração de Papéis
```bash
docker exec -it aprender_web python manage.py setup_roles
```

### Importação de Dados Mestres
```bash
docker exec -it aprender_web python manage.py runscript core.scripts.import_projetos
docker exec -it aprender_web python manage.py runscript core.scripts.import_municipios
docker exec -it aprender_web python manage.py runscript core.scripts.import_tiposdeevento
docker exec -it aprender_web python manage.py runscript core.scripts.import_formadores
```

## 7. Histórico de Desenvolvimento

### Versão 1.0 - Implementação Base
- ✅ Estrutura base do projeto Django
- ✅ Modelos de dados para entidades mestres
- ✅ Sistema de autenticação com papéis
- ✅ Interface Django Admin
- ✅ Permissões por papel
- ✅ Comandos de importação de dados
- ✅ RF01 - Gerenciamento de Dados Mestres implementado

### Próximas Implementações
- 🔄 RF02 - Interface de solicitação de eventos
- 🔄 RF03 - Verificação automática de conflitos
- 🔄 RF04 - Fluxo de aprovação
- 🔄 RF05/RF06 - Integração com Google Calendar/Meet
- 🔄 Interface web responsiva para usuários finais

## 8. Considerações Técnicas

### Segurança
- Autenticação obrigatória para todas as funcionalidades
- Controle de acesso baseado em papéis (RBAC)
- Logs de auditoria para todas as operações
- Validação de integridade referencial

### Performance
- Índices otimizados para consultas frequentes
- UUIDs para identificadores únicos
- Relacionamentos eficientes com ForeignKeys

### Manutenibilidade
- Código seguindo padrões PEP8
- Separação clara de responsabilidades
- Documentação inline no código
- Testes automatizados para validação