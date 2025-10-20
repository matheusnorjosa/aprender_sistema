# ✅ PR 8/N - Checklist Manual de Validação

**Data:** 2025-10-14
**Status:** 🟡 Pendente validação manual pelo usuário

---

## 📋 Checklist Rápido

### 1️⃣ RBAC - Rota `/solicitar`

**O que validar:**
- [ ] Usuário **Coordenador** vê a página `/solicitar`
- [ ] Usuário **DAT** vê a página `/solicitar`
- [ ] Usuário **Formador** NÃO vê a página (ou vê erro 403)
- [ ] Usuário **Superintendência** NÃO vê a página (não faz parte do grupo permitido)
- [ ] Superuser vê a página (bypass)

**Como testar:**
1. Login como Coordenador → http://localhost:5173/solicitar → ✅ deve carregar
2. Login como Formador → http://localhost:5173/solicitar → ❌ deve dar erro 403 no POST

**Implementação confirmada:**
```python
# v2/backend/apps/core/views.py:127-129
def get_permissions(self):
    if self.action == "create":
        return [IsCoordenadorOrDAT()]
    return [IsAuthenticated()]
```

**Status backend:** ✅ Implementado
**Status frontend:** ⚠️ **FALTA** - Menu visível para todos (UX issue)

---

### 2️⃣ Remote Selects

#### a) Municípios
**O que validar:**
- [ ] Search funciona (digitar "cau" → filtra Caucaia)
- [ ] Campo UF visível no label

**Endpoint:** `GET /api/options/municipios/?search=cau`

**Implementação:**
```python
# views.py:855-856
filter_backends = [SearchFilter]
search_fields = ["nome", "uf"]
```

**Status:** ✅ Implementado

---

#### b) Projetos (dependente de Município)
**O que validar:**
- [ ] Campo **desabilitado** até selecionar município
- [ ] Após selecionar município, campo habilita
- [ ] Lista carrega apenas projetos do município (se houver filtro futuro)
- [ ] Search funciona

**Implementação:**
```jsx
// NovaSolicitacao.jsx:311
disabled={!municipioSelecionado}
```

**Status:** ✅ Implementado

---

#### c) Coordenadores
**O que validar:**
- [ ] Lista apenas usuários do grupo **Coordenador**
- [ ] Search funciona (nome, username, email)
- [ ] Aparece apenas se checkbox "Coordenador acompanha" marcado

**Endpoint:** `GET /api/options/coordenadores/?search=maria`

**Status:** ✅ Implementado

---

#### d) Formadores
**O que validar:**
- [ ] Lista apenas usuários do grupo **Formador**
- [ ] Permite seleção múltipla
- [ ] Search funciona

**Endpoint:** `GET /api/options/formadores/?search=joão`

**Status:** ✅ Implementado

---

### 3️⃣ Campo "Tipo de Evento" (NOVO!)

**O que validar:**
- [x] Campo presente no formulário
- [x] Marcado como obrigatório (*)
- [ ] RemoteSelect com busca funciona
- [ ] Criar sem tipo_evento → **400 Bad Request**
- [ ] Criar com tipo_evento → **201 Created**

**Endpoint:** `GET /api/options/tipos-evento/?search=form`

**Dados no banco:**
- ✅ 6 tipos criados:
  - ID 1: Formação
  - ID 2: Formação Inicial
  - ID 3: Formação Continuada
  - ID 4: Reunião Pedagógica
  - ID 5: Workshop
  - ID 6: Seminário

**Status:** ✅ Implementado e validado visualmente

**Teste backend:**
```bash
# Sem tipo_evento (deve falhar):
curl -X POST http://localhost:8002/api/solicitacoes/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -d '{"municipio": 1, "projeto": 1, "tipo": "evento", "inicio": "...", "fim": "..."}'
# Esperado: 400 {"tipo_evento": ["Este campo é obrigatório."]}

# Com tipo_evento (deve passar):
curl -X POST ... -d '{"tipo_evento": 1, ...}'
# Esperado: 201 Created
```

---

### 4️⃣ Data/Hora → ISO UTC

**O que validar:**
- [ ] Frontend envia `inicio` e `fim` em formato ISO 8601 UTC
- [ ] Backend valida `fim > inicio`
- [ ] Backend grava em UTC
- [ ] GET retorna em UTC (frontend converte de volta para America/Fortaleza)

**Conversão esperada:**
```javascript
// Frontend (America/Fortaleza → UTC):
const inicioLocal = dayjs(data).hour(8).minute(0);  // 08:00 BRT
const inicio = inicioLocal.tz('America/Fortaleza', true).utc().toISOString();
// Resultado: "2025-10-15T11:00:00Z" (08:00 BRT = 11:00 UTC)
```

**Teste:**
```bash
# Criar solicitação para 15/10/2025 08:00-12:00 (horário local)
# Backend deve gravar: 11:00-15:00 UTC
```

**Status:** ✅ Implementado (NovaSolicitacao.jsx:126-131, 168-174)

---

### 5️⃣ Pré-checagem em Lote (Consultiva)

**O que validar:**
- [ ] Botão "Checar Disponibilidade" desabilitado até preencher data/hora + pelo menos 1 usuário
- [ ] Checagem inclui coordenador (se "acompanha" = true)
- [ ] Checagem inclui todos os formadores selecionados
- [ ] Resultado mostra status por usuário:
  - ✅ **OK** (disponível)
  - ⚠️ **Conflitos** com códigos X/T/P/D/M
- [ ] Checagem é **consultiva** (não bloqueia criação)

**Endpoint:** `POST /api/availability/check-many/`

**Payload exemplo:**
```json
{
  "usuarios_ids": [1, 2, 3],
  "inicio": "2025-10-15T11:00:00Z",
  "fim": "2025-10-15T15:00:00Z",
  "municipio_id": 1
}
```

**Response esperada:**
```json
{
  "ok": false,
  "results": [
    {
      "usuario_id": 1,
      "ok": true,
      "conflicts": []
    },
    {
      "usuario_id": 2,
      "ok": false,
      "conflicts": [
        {
          "code": "X",
          "title": "Conflito de Agenda",
          "detail": "Evento já agendado para 15/10 08:00-12:00"
        }
      ]
    }
  ]
}
```

**Códigos de conflito (RD-01 a RD-08):**
- **X** = Conflito de sobreposição
- **T** = Bloqueio total
- **P** = Bloqueio parcial
- **D** = Buffer de deslocamento
- **M** = Capacidade diária excedida

**Status:** ✅ Implementado (views.py:435-565)

---

### 6️⃣ Create - POST /api/solicitacoes/

**O que validar:**
- [ ] POST retorna **201 Created**
- [ ] Solicitação criada com `status = "pendente"`
- [ ] Campo `usuario` preenchido automaticamente (request.user)
- [ ] Solicitação aparece em `GET /api/solicitacoes/?status=pendente`
- [ ] Frontend redireciona para `/solicitacoes?status=pendente`

**Payload mínimo:**
```json
{
  "municipio": 1,
  "projeto": 1,
  "tipo": "evento",
  "tipo_evento": 1,
  "inicio": "2025-10-15T11:00:00Z",
  "fim": "2025-10-15T15:00:00Z",
  "coordenador_acompanha": false,
  "formadores": []
}
```

**Campos opcionais:**
- `encontro`, `segmento`, `observacoes`
- `coordenador` (obrigatório se `coordenador_acompanha = true`)

**Status:** ✅ Implementado (views.py:143-148)

---

### 7️⃣ CSRF/Sessão

**O que validar:**
- [ ] Todos os POST/PATCH incluem `credentials: 'include'`
- [ ] Cookie `csrftoken` extraído e enviado no header `X-CSRFToken`
- [ ] Sem CSRF → 403 Forbidden
- [ ] Sem sessão → 401 Unauthorized

**Implementação:**
```javascript
// solicitacoes.js:58-62
const response = await fetch(fullUrl, {
  ...options,
  headers,
  credentials: 'include', // ✅ Incluir cookies
});
```

**Status:** ✅ Implementado (solicitacoes.js:42-70)

---

### 8️⃣ Erros UX

**O que validar:**
- [ ] Erro de campo obrigatório → mensagem do DRF aparece no form
- [ ] Erro de validação → mensagem específica por campo
- [ ] Erro de rede → toast de erro genérico
- [ ] Sucesso → toast + redirect

**Implementação:**
```javascript
// NovaSolicitacao.jsx:186-196
catch (error) {
  if (error.message && typeof error.message === 'object') {
    Object.entries(error.message).forEach(([field, errors]) => {
      message.error(`${field}: ${errors.join(', ')}`);
    });
  }
}
```

**Status:** ✅ Implementado

---

## 🎯 Confirmações Finais

### ✅ Rota Protegida (RBAC)
- Backend: `IsCoordenadorOrDAT` permission aplicada
- Frontend: **⚠️ Menu visível para todos** (issue de UX, não bloqueia funcionalidade)

### ✅ Dependência Projeto → Município
- Campo projeto desabilitado até selecionar município
- Reset de projeto quando município muda

### ✅ Payload Correto
- Todos os campos obrigatórios presentes no form
- `tipo_evento` adicionado e obrigatório
- `usuario` auto-filled no backend (read_only)

### ✅ Check-many com Códigos X/T/P/D/M
- Endpoint implementado com lógica RD-01 a RD-08
- Response estruturada por usuário com lista de conflitos
- Códigos documentados no backend

---

## 📝 Issues Conhecidas (Não Bloqueantes)

### 1. Menu "Nova Solicitação" Visível Para Todos
**Impacto:** 🟡 UX - Usuários sem permissão veem o menu mas recebem 403 ao tentar criar

**Recomendação:** Adicionar verificação de grupo no frontend:
```jsx
// App.jsx - condicional no menu
{(user.groups.includes('Coordenador') || user.groups.includes('DAT')) && (
  <Menu.Item key="solicitar" icon={<PlusOutlined />}>
    <Link to="/solicitar">Nova Solicitação</Link>
  </Menu.Item>
)}
```

### 2. Rate Limiting Observado Durante Testes
**Impacto:** 🟢 Nenhum - Comportamento esperado

**Status:** Expira em ~1 hora após testes intensivos

---

## 🧪 Roteiro de Teste Manual

### Teste 1: Criação Básica (Happy Path)
1. Login como Coordenador
2. Navegar para http://localhost:5173/solicitar
3. Preencher:
   - Município: Caucaia
   - Projeto: (selecionar um)
   - Tipo: Evento
   - **Tipo de Evento: Formação Inicial** ⭐ NOVO
   - Data: 15/10/2025
   - Hora início: 08:00
   - Hora fim: 12:00
4. Clicar "Criar Solicitação"
5. Verificar:
   - ✅ Toast "Solicitação criada com sucesso!"
   - ✅ Redirect para `/solicitacoes?status=pendente`
   - ✅ Solicitação aparece na lista

### Teste 2: Validação - Tipo Evento Obrigatório
1. Preencher formulário sem selecionar Tipo de Evento
2. Tentar criar
3. Verificar:
   - ❌ Erro de validação do form
   - 🔴 Campo "Tipo de Evento" marcado em vermelho
   - 📝 Mensagem "Tipo de Evento é obrigatório"

### Teste 3: Pré-checagem com Conflito
1. Preencher formulário completo
2. Selecionar 2 formadores
3. Marcar "Coordenador acompanha" + selecionar coordenador
4. Clicar "Checar Disponibilidade"
5. Verificar:
   - ✅ Card com resultado por usuário (3 no total)
   - ✅ Se houver conflito, código e detalhes aparecem
   - ✅ Botão "Criar Solicitação" continua habilitado (consultivo)

### Teste 4: RBAC - Formador Negado
1. Login como Formador (ou criar um)
2. Navegar para http://localhost:5173/solicitar
3. Preencher formulário
4. Tentar criar
5. Verificar:
   - ❌ 403 Forbidden no POST
   - 🔴 Toast de erro

### Teste 5: Timezone UTC
1. Criar solicitação para 15/10 08:00-12:00 (horário local)
2. Fazer GET da solicitação criada
3. Verificar JSON:
   ```json
   {
     "inicio": "2025-10-15T11:00:00Z",  // 08:00 BRT = 11:00 UTC ✅
     "fim": "2025-10-15T15:00:00Z"      // 12:00 BRT = 15:00 UTC ✅
   }
   ```

---

## ✅ Checklist Final de Aprovação

- [ ] **Teste 1** (Happy Path) → ✅ Passou
- [ ] **Teste 2** (Validação) → ✅ Passou
- [ ] **Teste 3** (Pré-checagem) → ✅ Passou
- [ ] **Teste 4** (RBAC) → ✅ Passou
- [ ] **Teste 5** (Timezone) → ✅ Passou
- [ ] Nenhum console.error crítico no browser
- [ ] Nenhum erro 500 no backend
- [ ] PR8-validation.json atualizado

---

## 🚀 Comandos Úteis

### Backend - Verificar Solicitação Criada
```bash
docker-compose exec web python manage.py shell
>>> from apps.core.models import Solicitacao
>>> sol = Solicitacao.objects.last()
>>> print(f"Status: {sol.status}")
>>> print(f"Tipo Evento: {sol.tipo_evento.nome}")
>>> print(f"Início: {sol.inicio}")
>>> print(f"Fim: {sol.fim}")
```

### Frontend - Limpar Rate Limit (se necessário)
```bash
# Esperar 1 hora OU resetar Redis cache:
docker-compose restart redis
```

### Teste API Direto (via curl)
```bash
# Login no Django Admin primeiro, copiar sessionid do cookie

# Testar Options Tipos Evento
curl -H "Cookie: sessionid=XXX" \
  http://localhost:8002/api/options/tipos-evento/

# Testar Search
curl -H "Cookie: sessionid=XXX" \
  "http://localhost:8002/api/options/tipos-evento/?search=form"
```

---

**Gerado em:** 2025-10-14 17:40 BRT
**Por:** Claude Code
**Versão:** PR 8/N Final Checklist
