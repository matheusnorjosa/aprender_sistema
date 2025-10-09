# ⚡ QUICK START - INTEGRAÇÕES

Guia rápido para configurar e testar Google Sheets + Anthropic + MCP

---

## 🚀 1. INSTALAÇÃO (Executar uma vez)

```bash
# Entrar no container
docker compose exec web bash

# Instalar dependências
pip install gspread google-auth google-auth-oauthlib google-auth-httplib2 gspread-dataframe anthropic

# Criar pastas
mkdir -p creds docs/inventario_integracoes

# Sair do container
exit
```

---

## 🔑 2. CONFIGURAR CREDENCIAIS

### Google Sheets Service Account

1. Acesse: https://console.cloud.google.com/
2. Navegue: IAM & Admin → Service Accounts
3. Crie nova Service Account
4. Baixe chave JSON
5. Salve em: `creds/gsheet_sa.json`
6. Compartilhe suas planilhas com o email da SA

**OU** defina variável de ambiente:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/sa.json
```

### Anthropic API Key

1. Acesse: https://console.anthropic.com/
2. Navegue: API Keys
3. Crie nova chave
4. Configure:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**No Docker Compose:**
```yaml
# docker-compose.yml
services:
  web:
    environment:
      - ANTHROPIC_API_KEY=sk-ant-api03-...
      - GOOGLE_APPLICATION_CREDENTIALS=/app/creds/gsheet_sa.json
```

---

## ✅ 3. TESTAR CONECTIVIDADE

```bash
# Entrar no container
docker compose exec web bash

# Testar Google Sheets
python manage.py gsheets_healthcheck \
  --sheet-id=1AbC2DeF3GhI... \
  --gid=0

# Testar Anthropic
python aiops/anthropic_ping.py

# Testar MCP
echo "{}" | python mcp/mcp_server.py

# Auditoria completa
python devops/auditar_integracoes.py
```

**Resultado esperado:**
```
✓ gspread: 6.1.2
✓ anthropic: 0.34.2
✓ Service Account: /app/creds/gsheet_sa.json
✓ ANTHROPIC_API_KEY: configurada (48 chars)
```

---

## 📥 4. IMPORTAR COM CROSS-CHECK

### Usuários

```bash
python manage.py import_usuarios data/usuarios.csv \
  --sheet-id=1AbC2DeF3GhI... \
  --gid=0 \
  --fonte=Usuarios2025
```

**Relatório gerado:**
```
docs/GSHEETS_CROSSCHECK_import_usuarios_20251008_123456.json
```

### Eventos

```bash
python manage.py import_eventos_abas data/eventos.csv \
  --sheet-id=1AbC2DeF3GhI... \
  --gid=123456 \
  --fonte=EventosBahia \
  --col-solicitante="Solicitante" \
  --col-cancelado="Cancelado?" \
  --col-aprovado="Aprovado?"
```

**Relatório gerado:**
```
docs/GSHEETS_CROSSCHECK_import_eventos_20251008_123456.json
```

### Disponibilidades

```bash
python manage.py import_disponibilidades data/disp.csv \
  --sheet-id=1AbC2DeF3GhI... \
  --gid=789012 \
  --fonte=DispAno2025
```

**Relatório gerado:**
```
docs/GSHEETS_CROSSCHECK_import_disp_20251008_123456.json
```

---

## 📊 5. VER RELATÓRIOS DE CROSS-CHECK

```bash
# Listar todos os relatórios
ls -lh docs/GSHEETS_CROSSCHECK_*.json

# Ver último relatório (exemplo)
cat docs/GSHEETS_CROSSCHECK_import_usuarios_*.json | python -m json.tool
```

**Formato do relatório:**
```json
{
  "local_rows": 118,
  "sheet_rows": 120,
  "intersection": 115,
  "coverage_local_in_sheet_pct": 97.46,
  "coverage_sheet_in_local_pct": 95.83,
  "missing_in_sheet": 3,
  "missing_in_local": 5
}
```

---

## 🔍 6. INTERPRETAR RESULTADOS

### Cobertura Ideal: >95%

✅ **EXCELENTE:** `coverage_local_in_sheet_pct >= 95%`
- Dados locais consistentes com Google Sheets
- Seguro para produção

⚠️ **ATENÇÃO:** `90% <= coverage < 95%`
- Pequenas diferenças detectadas
- Revisar `missing_in_sheet` e `missing_in_local`

❌ **CRÍTICO:** `coverage < 90%`
- Drift significativo de dados
- NÃO usar em produção sem revisão

### Exemplo de Análise

```json
{
  "local_rows": 100,
  "sheet_rows": 105,
  "coverage_local_in_sheet_pct": 98.0,
  "missing_in_sheet": 2,
  "missing_in_local": 7
}
```

**Interpretação:**
- ✅ 98% das linhas locais existem no Sheets (EXCELENTE)
- 2 linhas só existem localmente (verificar)
- 7 linhas só existem no Sheets (podem ser novas)
- **Ação:** Revisar as 2 linhas locais antes de produção

---

## 🛠️ 7. TROUBLESHOOTING

### Erro: "Service Account ausente"

```bash
# Verificar se arquivo existe
ls -lh creds/gsheet_sa.json

# Se não existir, copiar do host
docker compose cp /caminho/local/sa.json web:/app/creds/gsheet_sa.json
```

### Erro: "Permission denied" (Google Sheets)

1. Abra a planilha no navegador
2. Clique em "Compartilhar"
3. Adicione o email da Service Account (em `creds/gsheet_sa.json`)
4. Dê permissão de "Leitor"

### Erro: "Invalid API key" (Anthropic)

```bash
# Verificar se está configurada
echo $ANTHROPIC_API_KEY

# Se não estiver, configurar
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Testar novamente
python aiops/anthropic_ping.py
```

### Erro: "Aba gid=XXX não encontrada"

1. Abra a planilha no navegador
2. Na URL, encontre: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=GID`
3. Use o GID correto (número após `gid=`)

---

## 📋 8. CHECKLIST DE PRODUÇÃO

Antes de usar em produção, verifique:

- [ ] Service Account configurada e testada
- [ ] Anthropic API Key configurada e testada
- [ ] Cross-check de usuários: coverage > 95%
- [ ] Cross-check de eventos: coverage > 95%
- [ ] Cross-check de disponibilidades: coverage > 95%
- [ ] Auditoria de integrações: todas ✓
- [ ] Budget alert configurado no Anthropic Console
- [ ] Planilhas compartilhadas com SA (read-only)
- [ ] Backups das planilhas originais
- [ ] Logs de cross-check arquivados

---

## 🔄 9. WORKFLOW RECOMENDADO

### Para cada importação:

1. **Exportar CSV da planilha**
   ```bash
   # Download manual ou via script
   ```

2. **Importar com cross-check**
   ```bash
   python manage.py import_usuarios data/usuarios.csv \
     --sheet-id=... --gid=... --dry-run
   ```

3. **Revisar relatório**
   ```bash
   cat docs/GSHEETS_CROSSCHECK_import_usuarios_*.json
   ```

4. **Se coverage > 95%, aplicar**
   ```bash
   python manage.py import_usuarios data/usuarios.csv \
     --sheet-id=... --gid=...
   ```

5. **Arquivar relatório**
   ```bash
   mkdir -p docs/crosschecks/$(date +%Y%m)
   mv docs/GSHEETS_CROSSCHECK_*.json docs/crosschecks/$(date +%Y%m)/
   ```

---

## 💡 10. DICAS AVANÇADAS

### Automatizar com cron

```bash
# Exemplo: import diário com cross-check
0 2 * * * cd /app && python manage.py import_usuarios \
  /backup/usuarios_$(date +\%Y\%m\%d).csv \
  --sheet-id=... --gid=... >> /logs/import.log 2>&1
```

### Alertas de drift

```python
# Script para alertar se coverage < 95%
import json
import sys

with open("docs/GSHEETS_CROSSCHECK_import_usuarios_latest.json") as f:
    data = json.load(f)
    coverage = data["coverage_local_in_sheet_pct"]
    if coverage < 95:
        print(f"ALERTA: Coverage {coverage}% < 95%", file=sys.stderr)
        sys.exit(1)
```

### Dashboard de cross-checks

```python
# Em dashboard/views.py
def crosscheck_dashboard(request):
    reports = list(Path("docs").glob("GSHEETS_CROSSCHECK_*.json"))
    data = [json.loads(r.read_text()) for r in reports]
    return render(request, "dashboard/crosscheck.html", {"reports": data})
```

---

## 📚 11. REFERÊNCIAS

- **Documentação completa:** `RELATORIO_INTEGRACOES_COMPLETO.md`
- **Auditoria:** `RELATORIO_AUDITORIA_FINAL_COMPLETA.md`
- **Inventário:** `docs/inventario_integracoes/INVENTARIO_FINAL.md`
- **Sumário:** `SUMARIO_EXECUTIVO_FINAL.md`

---

## 🆘 12. SUPORTE

### Logs de erro

```bash
# Ver logs do Django
docker compose logs web -f --tail=100

# Ver logs de import específico
grep "import_usuarios" /logs/*.log

# Ver logs de cross-check
ls -lh docs/GSHEETS_CROSSCHECK_*.json
```

### Comandos de debug

```bash
# Testar conexão PostgreSQL
docker compose exec web python manage.py dbshell

# Testar settings
docker compose exec web python manage.py shell -c \
  "from django.conf import settings; print(settings.GSHEETS_SA_PATH)"

# Ver versões instaladas
docker compose exec web pip list | grep -E "gspread|anthropic|django"
```

---

**Criado em:** 2025-10-08  
**Versão:** 1.0.0  
**Para:** Sistema Aprender - Integrações
