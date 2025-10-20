# SSOT Daily Automation — PowerShell + Docker + Windows Task Scheduler

## Data: 2025-10-05 12:15 UTC

## 🎯 Objetivo

Automatizar a validação diária SSOT (Single Source of Truth) executando:
1. Download de espelhos das 5 abas do Google Sheets
2. Comparação entre fonte live (sheets) e espelhos (CSV local)
3. Commit automático do relatório de validação

---

## 📁 Arquivos Criados

### 1. `scripts/ssot_daily.ps1`

**Script PowerShell** que executa o pipeline completo via Docker.

**Funcionalidades:**
- Download de 5 abas (ACerta, Brincando, Vidas, Super, Outros)
- Execução do comparador de fontes
- Commit automático com timestamp UTC
- Tratamento de erros com mensagens coloridas
- Idempotente (não comita se não houver mudanças)

**Uso manual:**
```powershell
cd "C:\Users\datsu\OneDrive\Documentos\Aprender Sistema"
powershell.exe -ExecutionPolicy Bypass -File scripts\ssot_daily.ps1 -GitUserName "ssot-bot" -GitUserEmail "ssot-bot@aprender.local"
```

**Parâmetros:**
- `-GitUserName`: Nome do usuário para commits (padrão: "ssot-bot")
- `-GitUserEmail`: Email do usuário para commits (padrão: "ssot-bot@example.com")

---

## ⏰ Windows Task Scheduler - Configuração

### Criar Tarefa Agendada

1. **Abrir Task Scheduler:**
   - Pressione `Win + R`
   - Digite: `taskschd.msc`
   - Pressione Enter

2. **Criar Tarefa Básica:**
   - Clique em **"Create Basic Task..."** no painel direito
   - Nome: `SSOT Daily Validation`
   - Descrição: `Validação diária SSOT - compara Google Sheets com espelhos locais`

3. **Trigger (Gatilho):**
   - Selecione: **Daily**
   - Start: Data atual
   - Time: **07:30:00** (7h30 da manhã)
   - Recur every: **1 days**

4. **Action (Ação):**
   - Selecione: **Start a program**
   - **Program/script:**
     ```
     powershell.exe
     ```
   - **Add arguments:**
     ```
     -NoLogo -NoProfile -ExecutionPolicy Bypass -File "scripts\ssot_daily.ps1" -GitUserName "ssot-bot" -GitUserEmail "ssot-bot@aprender.local"
     ```
   - **Start in (optional):**
     ```
     C:\Users\datsu\OneDrive\Documentos\Aprender Sistema
     ```

5. **Finish:**
   - Marque: ✅ **"Open the Properties dialog for this task when I click Finish"**

6. **Configurações Avançadas (Properties Dialog):**
   - **General Tab:**
     - ✅ Run whether user is logged on or not
     - ✅ Run with highest privileges
     - Configure for: **Windows 10**

   - **Conditions Tab:**
     - ⬜ Start the task only if the computer is on AC power (desmarcar)
     - ✅ Wake the computer to run this task

   - **Settings Tab:**
     - ✅ Allow task to be run on demand
     - ✅ Run task as soon as possible after a scheduled start is missed
     - ✅ If the task fails, restart every: **10 minutes** (até 3 tentativas)

7. **Salvar:**
   - Clique **OK**
   - Digite sua senha do Windows quando solicitado

---

## 🧪 Teste Manual

**Executar manualmente para testar:**

### Via PowerShell:
```powershell
cd "C:\Users\datsu\OneDrive\Documentos\Aprender Sistema"
powershell.exe -ExecutionPolicy Bypass -File scripts\ssot_daily.ps1 -GitUserName "ssot-bot" -GitUserEmail "ssot-bot@aprender.local"
```

### Via Task Scheduler:
1. Abra Task Scheduler (`taskschd.msc`)
2. Localize a tarefa: **SSOT Daily Validation**
3. Clique com botão direito → **Run**
4. Verifique a última execução em **Last Run Result**

---

## 📊 Resultado Esperado

**Saída de sucesso:**
```
=== SSOT Daily Job - Iniciando ===

=== 1/3: Baixando espelhos do Google Sheets ===
[Django banner output]

=== 2/3: Executando comparador de fontes ===
📋 Comparando aba: ACerta
   Fonte A: 490 registros
   Fonte B: 490 registros
   ✅ Contagens iguais

[... outras abas ...]

✅ Relatório salvo em: docs/VALIDACAO_FONTE_DUPLA.md

=== 3/3: Commitando relatório (via host) ===
   Commit criado: chore: SSOT diário 2025-10-05T12:15:43Z

✅ SSOT Daily Job - Concluído com sucesso!
   Timestamp: 2025-10-05T12:15:43Z
```

**Commits gerados:**
```bash
git log --oneline --author="ssot-bot" --since="1 week ago"
# Exemplo:
# 1a2b3c4 chore: SSOT diário 2025-10-05T12:15:43Z
# 5d6e7f8 chore: SSOT diário 2025-10-04T12:15:21Z
```

---

## 🔍 Monitoramento

### Verificar Logs do Task Scheduler:
1. Abra Event Viewer (`eventvwr.msc`)
2. Navegue: **Applications and Services Logs → Microsoft → Windows → TaskScheduler → Operational**
3. Filtre por **Task Name**: "SSOT Daily Validation"

### Verificar Commits:
```bash
git log --oneline --author="ssot-bot" --since="7 days ago"
```

### Verificar Relatório Atualizado:
```bash
cat docs/VALIDACAO_FONTE_DUPLA.md
```

---

## ⚠️ Troubleshooting

### Problema: Tarefa não executa
**Soluções:**
1. Verificar se Docker está rodando (`docker compose ps`)
2. Verificar se o caminho do script está correto no Task Scheduler
3. Verificar logs no Event Viewer
4. Executar manualmente para ver erros detalhados

### Problema: Commit falha
**Soluções:**
1. Verificar se git está configurado no PATH do Windows
2. Verificar se repo não está em estado de merge/rebase
3. Executar `git status` para ver se há conflitos

### Problema: Docker não responde
**Soluções:**
1. Verificar se Docker Desktop está rodando
2. Reiniciar Docker Desktop
3. Verificar se containers estão up: `docker compose ps`

---

## 📋 Checklist de Setup

- [x] Script `scripts/ssot_daily.ps1` criado
- [x] Teste manual executado com sucesso
- [ ] Tarefa agendada criada no Windows Task Scheduler
- [ ] Tarefa testada via "Run" no Task Scheduler
- [ ] Monitoramento configurado (Event Viewer)
- [ ] Documentação lida e entendida

---

## 🔧 Manutenção

### Desabilitar temporariamente:
```powershell
Disable-ScheduledTask -TaskName "SSOT Daily Validation"
```

### Reabilitar:
```powershell
Enable-ScheduledTask -TaskName "SSOT Daily Validation"
```

### Alterar horário:
1. Abra Task Scheduler
2. Localize a tarefa
3. Clique com botão direito → **Properties**
4. Aba **Triggers** → Edit
5. Altere horário → OK

### Remover:
```powershell
Unregister-ScheduledTask -TaskName "SSOT Daily Validation" -Confirm:$false
```

---

## 🎯 Benefícios

1. ✅ **Validação automática diária** - detecção precoce de divergências
2. ✅ **Histórico auditável** - commits com timestamp UTC
3. ✅ **Zero intervenção manual** - executa silenciosamente em background
4. ✅ **Alertas via Event Viewer** - notificação de falhas
5. ✅ **Idempotente** - não cria commits desnecessários se dados idênticos

---

## 📅 Próximos Passos (Opcional)

1. **Alertas por Email**: Configurar Task Scheduler para enviar email em caso de falha
2. **Dashboard**: Criar endpoint `/api/ssot/status` mostrando última validação
3. **Slack Integration**: Notificar canal #tech em caso de divergências
4. **Auto-remediation**: Se divergência < 1%, auto-merge; senão, criar issue no GitHub

---

**Data de Criação**: 2025-10-05 12:15 UTC
**Autor**: SSOT Automation Setup
**Versão**: 1.0
