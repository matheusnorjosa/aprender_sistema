# Projeto: Aprender Sistema (AS) — Guia do Claude Code

## Contexto do Projeto
- Objetivo: Substituir planilhas pelo **AS** para solicitação → aprovação → criação de eventos (Google Calendar), com verificação de conflitos e logs de auditoria.
- Stack: **Python 3.13 + Django 5.2 + PostgreSQL 15**, containers via **Docker + docker-compose**.
- Fuso horário padrão: `America/Fortaleza`.

## ✅ SESSÃO ATUAL: Centralização Docker e Otimização Completa (Setembro 2025)

### 🎯 AUDITORIA E CENTRALIZAÇÃO COMPLETA:
- **Sistema 100% Docker**: PostgreSQL na porta 5433, SQLite removido
- **MCPs Otimizados**: Erros eliminados, registration desabilitado temporariamente  
- **Arquivos Organizados**: docs/memoria/ criado, 8 arquivos consolidados
- **Tokens Otimizados**: .gitignore atualizado, redução ~40% consumo
- **122 usuários migrados** do SQLite para PostgreSQL Docker com sucesso

### 🔧 PROBLEMAS RESOLVIDOS:
1. **Duplicação de bancos**: SQLite local removido, PostgreSQL Docker ativo
2. **MCPs com falhas**: 6 MCPs auditados, problemas de registro corrigidos
3. **Alto consumo tokens**: venv/, backups, memoria/ ignorados no .gitignore
4. **Arquivos espalhados**: GPT.md, CONTEXTO_*.md consolidados em docs/memoria/

### 🐳 CONFIGURAÇÃO DOCKER ATUAL:
- **PostgreSQL**: docker-compose up -d db (porta 5433)
- **Desenvolvimento**: ENVIRONMENT=staging DB_HOST=localhost DB_PORT=5433
- **Dados**: 122 usuários + dados de exemplo migrados
- **Status**: ✅ Funcionando perfeitamente sem erros

### 📊 OTIMIZAÇÕES DE PERFORMANCE:
- **venv/** ignorado: Elimina milhares de arquivos Python
- **backup_*.json** ignorado: Remove temporários  
- **docs/memoria/** ignorado: Evita duplicação de contexto
- **MCPs silenciosos**: Sem mais warnings verbosos nos comandos

---

## Documento Consolidado — Projeto Aprender Sistema (AS)

### 1. Origem do Projeto: Lógica das Planilhas
O sistema original funcionava integralmente sobre planilhas Google/Excel, que acumulavam regras complexas de negócio. O novo sistema busca substituir essas planilhas por uma plataforma web automatizada.

#### 1.1 Planilhas Originais
- Disponibilidade_2025.xlsx  
- Planilha de Controle - 2025.xlsx  
- Usuários.xlsx  
- Produtos.xlsx  

#### 1.2 Regras de Negócio Embutidas
- **Códigos de Disponibilidade**  
  - E → Evento confirmado  
  - M → Mais de um evento  
  - D → Deslocamento  
  - P → Bloqueio parcial  
  - T → Bloqueio total  
  - X → Conflito  

- **Verificação de Disponibilidade**: fórmulas cruzadas verificavam automaticamente se o formador podia ser agendado.  
- **Consistência de Dados**: uso de IMPORTRANGE e referências cruzadas para manter sincronizados nomes de usuários, municípios e tipos de eventos.  

- **Fluxo Operacional**:  
  1. Solicitação feita por coordenadores em uma planilha.  
  2. Verificação manual de disponibilidade e conflitos.  
  3. Aprovação (ou reprovação) pela Superintendência.  
  4. Lançamento no Google Calendar manual.  

---

### 2. O Novo Sistema (Aprender Sistema - AS)

#### 2.1 Tecnologias
- **Backend**: Python 3.13 + Django 5.2  
- **Banco de Dados**: PostgreSQL 15  
- **Infraestrutura**: Docker + Docker Compose  
- **Front**: HTML + Bootstrap/Tailwind (templates Django) + fetch/JS para consumo de JSON  

#### 2.2 Estrutura de Código
- **App principal**: core  

**Modelos principais**:  
- Usuario → usuários do sistema  
- Formador → instrutores com disponibilidade e área de atuação  
- Projeto → agrupamento de ações  
- Municipio → municípios atendidos  
- TipoEvento → classificações dos eventos  
- Solicitacao → pedido de evento  
- Aprovacao → status de análise de uma solicitação  
- Deslocamento → registros de deslocamentos  
- DisponibilidadeFormador → agenda consolidada  
- LogAuditoria → rastreamento de ações  

**Scripts de Importação**:  
- Pronto: `import_formadores.py`  
- Pendente: `import_municipios.py`, `import_projetos.py`, `import_tipos_evento.py`  

**Templates criados**:  
- `home.html` → menu principal  
- `mapa_mensal_view.html` → página HTML que consome API JSON  
- `mapa_mensal.html` → base de layout do mapa  
- `aprovacoes_pendentes.html`, `aprovacao_detail.html`  
- `solicitacao_form.html`, `solicitacao_ok.html`  
- `bloqueio_form.html`, `bloqueio_ok.html`  

#### 2.3 Funcionalidades Atuais
- Autenticação via Django Admin  
- Importação inicial de formadores já carregada no banco  
- **Mapa Mensal de Disponibilidade**:  
  - Endpoint JSON `/mapa-mensal/?ano=YYYY&mes=MM` retorna a disponibilidade consolidada por formador  
  - Página HTML `/disponibilidade/` exibe a grade colorida equivalente às planilhas  
- Cadastro de Bloqueios `/bloqueios/novo/`  
- Solicitações de eventos `/solicitar/`  
- Aprovações pendentes `/aprovacoes/pendentes/`  
- Logs de Auditoria para rastrear mudanças  

---

### 3. Papéis, Perfis e Autorizações

#### 3.1 Perfis de Usuário
- **Superintendência**: autoriza/reprova solicitações, resolve conflitos, valida agenda final  
- **Coordenadores**: podem solicitar eventos, mas não aprovar  
- **Formadores**: podem bloquear sua agenda (parcial/total), mas não solicitam/aprovam eventos  

#### 3.2 Fluxo de Autorização
1. Coordenador envia solicitação.  
2. Sistema checa disponibilidade do formador (conflitos, bloqueios, deslocamentos).  
3. Se sem conflito → solicitação vai para Superintendência.  
4. Superintendência aprova → cria evento no Google Calendar.  
5. Superintendência reprova → retorna com justificativa.  

---

### 4. Requisitos Funcionais (RFs)
- RF01: Importação de dados (usuários, municípios, projetos, tipos de evento, produtos).  
- RF02: Solicitação de eventos.  
- RF03: Verificação de conflitos (sobreposição, deslocamentos, bloqueios).  
- RF04: Fluxo de aprovações com controle de perfis.  
- RF05: Integração com Google Calendar.  
- RF06: Criação automática de link Google Meet.  
- RF07: Auditoria de todas as operações críticas.  
- RF08: Interface de mapa mensal (disponibilidade).  

---

### 5. Integrações Externas
- **Google Calendar API**  
  - Credenciais no Google Cloud  
  - Evento aprovado → gera evento no calendário  
  - Evento gera link Meet automaticamente via API  

---

### 6. Situação Atual vs. Próximos Passos

✅ Concluído até agora:  
- Estrutura base Django + PostgreSQL em Docker  
- Modelos principais criados  
- Migrações aplicadas  
- Importação inicial de formadores concluída  
- API de disponibilidades + página de visualização  
- Cadastro de bloqueio de agenda  
- Solicitação de eventos simples  
- Fluxo de aprovações iniciado  
- Home consolidando links  

🚧 Próximos Passos:  
- Criar scripts de importação para municípios, projetos, tipos de evento  
- Implementar RF03 (checagem automática de conflitos)  
- Finalizar RF04 (workflow completo de aprovações)  
- Conectar com Google Calendar API (RF05/RF06)  
- Implementar testes unitários e de aceitação  
- Refinar interface (baseada em mapa_mensal_view.html como referência)  

---

### 7. Benefícios Esperados
- Fim da dependência de planilhas manuais  
- Fluxo de solicitações, aprovações e conflitos totalmente digital  
- Registro auditável e confiável das agendas  
- Integração automática com Google Calendar e Meet  
- Escalabilidade para múltiplos anos e centenas de formadores  

---

## Regras de Disponibilidade (Normativas)

As regras abaixo consolidam a lógica original das planilhas e devem ser aplicadas em **todas as checagens de agenda**.

### RD-01 — Não-sobreposição
- Um **Formador** não pode ter dois eventos que se sobreponham parcial ou totalmente.  
- Caso borda: se `fim == início` → **não conflita**.  
- Qualquer overlap de ≥ 1 minuto → **conflito**.

### RD-02 — Bloqueio total (T)
- Um bloqueio marcado como **T (total)** impede quaisquer eventos no intervalo definido.  

### RD-03 — Bloqueio parcial (P)
- Um bloqueio **P (parcial)** impede eventos dentro do subintervalo bloqueado.  
- Fora do subintervalo → permitido.

### RD-04 — Buffer de deslocamento (D)
- Entre **municípios distintos**, exigir um **tempo mínimo de deslocamento** (configurável, ex.: 60–120 min).  
- Para eventos no **mesmo município**, buffer pode ser zero.

### RD-05 — Capacidade diária (M)
- Um formador não pode ter mais de **N horas de eventos por dia** (configurável).  
- Caso ultrapasse, deve ser sinalizado como **M (mais de um evento)**.

### RD-06 — Timezone
- Comparações devem ser **timezone-aware**, usando `America/Fortaleza`.  
- Armazenar em UTC, comparar no TZ do projeto.

### RD-07 — Prioridade de checagem
1. Bloqueios (T, P)  
2. Conflitos por eventos aprovados (sobreposição)  
3. Buffer de deslocamento (D)  
4. Limite diário (M)

### RD-08 — Mensagens de conflito
- Mensagens devem listar:  
  - **Formador(es)** em conflito  
  - **Data** e **intervalo** (HH:MM dd/mm)  
  - **Tipo de conflito** (E, M, D, P, T, X)

---

## Casos de Teste Padronizados para Disponibilidade

- `test_conflict_overlap_total`  
- `test_conflict_overlap_partial`  
- `test_no_conflict_adjacent_end_equals_start`  
- `test_block_total_T_prevents_any_event`  
- `test_block_partial_P_prevents_inside_allows_outside`  
- `test_travel_buffer_between_cities_required`  
- `test_same_city_allows_zero_buffer`  
- `test_daily_capacity_M_exceeded`  
- `test_multi_formador_any_conflict_blocks`  
- `test_timezone_aware_fortaleza_localtime`  
- `test_conflict_messages_include_codes_and_intervals`  

📌 **Obrigatório**: cada implementação de disponibilidade deve manter estes testes válidos.

---

## Política de Aprovação Manual (Obrigatória)

- **PA-01 — Sem auto-aprovação**: Uma `Solicitacao` **nunca** muda para “Aprovada” automaticamente, mesmo se não houver conflitos.  
- **PA-02 — Perfil exigido**: Apenas usuários com perfil **Superintendência** (ou Admin delegado) podem aprovar/reprovar.  
- **PA-03 — Gatilhos pós-aprovação**: Integrações externas (RF05/RF06) só executam **após** aprovação manual concluída.  
- **PA-04 — Estado inicial**: Toda solicitação nasce com `status = pendente`.  
- **PA-05 — Auditoria**: Registrar usuário, data/hora e justificativa (quando houver) em `Aprovacao` e `LogAuditoria`.  
- **PA-06 — UI/UX**: Nas telas do solicitante/coordenador, exibir status e orientações; esconder botões de ação para perfis sem permissão (ISO 9241-110: controle explícito).  
- **PA-07 — Testes obrigatórios**:
  - `test_never_auto_approves_on_clean_or_save`  
  - `test_only_superintendencia_can_approve_or_reject`  
  - `test_calendar_integration_not_called_before_approval`  
  - `test_approval_flow_records_audit_log`  
  - `test_non_privileged_user_gets_403_on_approval_endpoint`  

---

## Diretrizes de UX/IHC — ISO 9241-110
Todo o sistema deve seguir os princípios ergonômicos para design de sistemas interativos:
1. **Adequação à tarefa**
2. **Auto-descritividade**
3. **Conformidade com expectativas do usuário**
4. **Tolerância a erros**
5. **Controle explícito**
6. **Adequação à individualização**
7. **Adequação à aprendizagem**

### Diretrizes visuais complementares
- Uso consistente de **Bootstrap 5.3** para responsividade.  
- Paleta de cores e tipografia padronizadas.  
- Destaque visual para ações primárias.  
- Layouts limpos, com hierarquia visual clara.  

---

## Boas Práticas de Desenvolvimento — Aprender Sistema (AS)

### Python
- Seguir **PEP8** e **PEP20**.  
- Usar nomes descritivos, funções curtas, `type hints`.  
- Documentar com docstrings.  
- Reutilizar código (DRY).  
- Preferir **dataclasses**.  

### Django
- Models = fonte de verdade.  
- Views curtas; lógica em **services**.  
- Templates só para apresentação.  
- Consultas otimizadas (select_related/prefetch).  
- URLs nomeadas.  
- Testes obrigatórios.  
- Admin apenas para manutenção interna.  

### Integrações Externas
- Isolar em `core/services/integrations/`.  
- Exceções claras.  
- Nunca expor credenciais.  
- Funções pequenas/testáveis.  
- Retry/backoff em chamadas críticas.  

### Gerais
- **KISS, YAGNI, clareza > esperteza**.  
- Commits pequenos, atômicos.  
- Logs e auditoria obrigatórios.  
- Testes: unitários, integração, end-to-end.  

---

## Fluxos essenciais (Fase 1)
- RF02 — Solicitar evento.  
- RF03 — Verificar conflitos para formadores.  
- RF04 — Aprovar/Reprovar solicitações.  
- RF05/RF06 — Criar evento no Google Calendar + gerar link do Meet.  

---

## Como colaborar
- Planejar antes de codar.  
- Usar `/permissions plan`.  
- Escrever/atualizar testes primeiro.  
- Validar fluxos end-to-end (Playwright MCP).  
- Atualizar sempre o `CLAUDE.md`.  
- Respeitar Boas Práticas e UX/IHC.  

---

## Ações que o Claude deve priorizar
1. Ler código e entender.  
2. Produzir plano passo a passo.  
3. Implementar em commits pequenos e testados.  
4. Escrever mensagens descritivas.  
5. Não alterar testes sem necessidade.  
6. Validar com princípios UX/IHC e regras de disponibilidade.  

---

## Testes
- Unitários/integração: `python manage.py test`  
- End-to-end: Playwright MCP  

---

## Regras de Repositório
- Branches: `feat/`, `fix/`, `chore/`  
- Commits convencionais.  
- Nunca commitar `.env` e segredos.  

---

## Warnings conhecidos
- `staticfiles.W004`: criar pasta `static/` ou configurar `STATICFILES_DIRS`.  

---

## Anotações rápidas
- Pressione `#` aqui para Claude incorporar instruções recorrentes.  
