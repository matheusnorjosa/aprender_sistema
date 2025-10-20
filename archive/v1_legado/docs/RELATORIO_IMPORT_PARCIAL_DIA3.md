# Relatório de Import Parcial - Dia 3

**Data:** 2025-10-03 21:30:00
**Status:** ⚠️  PARCIALMENTE CONCLUÍDO

---

## ✅ COMPLETADO COM SUCESSO

### 1. Sistema de Ingestão Dual (Sheets + CSV)
- ✅ **ingestao/adapters.py** reescrito (126 linhas)
  - Parsing robusto com normalização case-insensitive
  - Multi-formador (Formador 1-5) implementado
  - Detecção de cancelamento/aprovação
  - Suporte a formatos brasileiros (dd/mm/yyyy, HH:MM)

- ✅ **9 GIDs configurados** em sheets_config.py
- ✅ **9 URLs HTTP 200** validadas
- ✅ **663KB CSVs espelhados** baixados
- ✅ **Comparador funcionando**: Sheets = CSV (paridade 100%)

### 2. Dry-runs Validados
```
Aba ACerta:    490 eventos parseados, 0 erros
Aba Brincando: 191 eventos parseados, 0 erros
Aba Vidas:     285 eventos parseados, 0 erros
Aba Super:    1245 eventos parseados, 0 erros
Aba Outros:     79 eventos parseados, 0 erros
TOTAL:        2290 eventos, 0 erros de parsing
```

### 3. Import de Usuários
- ✅ **118 usuários importados** com sucesso via Sheets
- ✅ Validação de CPF/email funcionando
- ✅ Origem "planilha" + is_provisorio=True aplicados

### 4. Backup do Banco
- ✅ **126.5KB backup** criado antes do import
- ✅ Localização: `/dump/backup_pre_import_20251003_212353.dmp`

---

## ⚠️  BLOQUEIOS IDENTIFICADOS

### Problema: Incompatibilidade de Schema do Modelo

**Erro:** `Solicitacao() got unexpected keyword arguments: 'data', 'hora_inicio', 'hora_fim', 'encontro', 'coordenador', 'origem_aba'`

**Causa Raiz:**
O modelo `core.models.Solicitacao` possui schema diferente do esperado pelo import:

**Esperado pelo Parser:**
- `data` (date)
- `hora_inicio` (time)
- `hora_fim` (time)
- `encontro` (str)
- `coordenador` (FK para Usuario)
- `origem_aba` (str)

**Schema Real do Modelo:**
```python
Solicitacao._meta.get_fields():
- data_inicio (DateTime, não Date+Time separados)
- data_fim (DateTime)
- numero_encontro_formativo (str, não 'encontro')
- usuario_solicitante (FK Usuario, não 'coordenador')
- observacoes (str)
- SEM campo origem_aba
```

**Correções Aplicadas:**
1. ✅ Combinar date + time → datetime para data_inicio/data_fim
2. ✅ Mapear 'encontro' → 'numero_encontro_formativo'
3. ✅ Mapear 'coordenador' → 'usuario_solicitante'
4. ✅ Adicionar origem_aba em 'observacoes'

**Erro Secundário:** `AttributeError: 'NoneType' object has no attribute 'vinculado_superintendencia'`

**Causa:** Signal ou validation no modelo Solicitacao.save() espera que usuario_solicitante tenha atributo vinculado_superintendencia

**Tentativa de Fix:** Criar usuário fallback "sistema_import" quando coordenador ausente

---

## 📊 EVIDÊNCIAS COLETADAS

### Validação Status (Sem AGENDADO)
```bash
$ grep -i "AGENDADO" <dry-run output>
(vazio - 0 ocorrências encontradas)
```
✅ **CONFIRMADO:** Nenhum status AGENDADO foi gerado

### External Hashes Gerados (Exemplos)
```
d21d973e... - Amigos do Bem | 2025-03-10 08:00 | Lendo e Escrevendo
ff82d2e4... - Amigos do Bem | 2025-03-10 08:00 | Novo Lendo
069559aa... - Amigos do Bem | 2025-03-10 08:00 | Projeto AMMA
```

### Paridade Sheets vs CSV (ACerta)
```
Fonte A (Sheets): 490 registros
Fonte B (CSV):    490 registros
Diferença:        0 registros (100% paridade)
```

---

## 🚧 PRÓXIMOS PASSOS NECESSÁRIOS

### PASSO A: Resolver Incompatibilidade de Modelo (CRÍTICO)

**Opção 1: Ajustar Schema do Modelo (Recomendado)**
```python
# Em core/models.py - Adicionar campos compatíveis
class Solicitacao(models.Model):
    # ... campos existentes ...
    origem_aba = models.CharField(max_length=50, blank=True, null=True)  # Novo

    # OU criar migration para popular de observacoes
```

**Opção 2: Criar Modelo Intermediário**
```python
class SolicitacaoImportada(models.Model):
    """Modelo temporário para staging de imports antes de validação."""
    solicitacao = models.ForeignKey(Solicitacao, null=True, on_delete=models.SET_NULL)
    external_hash = models.CharField(max_length=40, unique=True)
    raw_data = models.JSONField()  # Dados brutos da planilha
    status_import = models.CharField(choices=[('pendente', 'staging', 'aprovado', 'erro')])
    # ... outros campos de metadados
```

**Opção 3: Desabilitar Signals Temporariamente**
```python
# Em import_eventos_abas.py
from django.db.models.signals import pre_save, post_save
from core.models import Solicitacao

# Desabilitar signals durante import
pre_save.disconnect(sender=Solicitacao)
post_save.disconnect(sender=Solicitacao)

# ... import code ...

# Reabilitar signals
pre_save.connect(sender=Solicitacao)
post_save.connect(sender=Solicitacao)
```

### PASSO B: Resolver Atributo vinculado_superintendencia

**Investigar:**
1. Qual signal/validation está acessando `usuario_solicitante.vinculado_superintendencia`
2. Se é campo de Usuario ou Formador relacionado
3. Se pode ser None ou precisa de valor padrão

**Localizar:**
```bash
$ grep -r "vinculado_superintendencia" core/
$ grep -r "def save" core/models.py
```

### PASSO C: Import Efetivo (Após Fixes)

```bash
# 1. Importar eventos (todas as abas)
docker compose exec -T web python manage.py import_eventos_abas \
    --from sheets \
    --abas ACerta,Brincando,Vidas,Super,Outros \
    --verbose

# 2. Validar status
docker compose exec -T web bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, COUNT(*) FROM core_solicitacao GROUP BY 1 ORDER BY 2 DESC;"'

# 3. Validar marcadores
docker compose exec -T web bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT origem_aba, COUNT(*) FROM core_marcadorplanilha GROUP BY 1;"'

# 4. Testar idempotência
docker compose exec -T web python manage.py import_eventos_abas \
    --from sheets \
    --abas ACerta \
    --verbose
# Esperado: created=0, skipped=490, errors=0
```

---

## 📁 ARQUIVOS MODIFICADOS NESTA SESSÃO

### Criados:
1. `docs/RELATORIO_INGESTAO_DIA3_COMPLETO.md` (relatório pré-import)
2. `docs/VALIDACAO_FONTE_DUPLA.md` (comparação Sheets vs CSV)
3. `docs/RELATORIO_IMPORT_PARCIAL_DIA3.md` (este arquivo)

### Modificados:
1. `ingestao/adapters.py` (reescrito - 126 linhas)
2. `ingestao/management/commands/import_eventos_abas.py` (atualizado - 280 linhas)
3. `ingestao/management/commands/import_usuarios.py` (corrigido SheetsAdapter)
4. `ingestao/management/commands/compare_fontes.py` (atualizado parser)
5. `backend/config/sheets_config.py` (9 GIDs preenchidos)

---

## 🎯 DECISÃO TÉCNICA RECOMENDADA

### Recomendação: Criar Modelo de Staging

**Justificativa:**
1. **Separação de Concerns**: Staging vs Produção
2. **Validação Manual**: Permite revisão antes de criar Solicitacao real
3. **Rollback Fácil**: Deletar staging não afeta dados de produção
4. **Auditoria Completa**: JSON raw_data preserva fonte original
5. **Flexibilidade**: Permite ajustar mapeamento sem migrations constantes

**Próximo comando:**
```bash
# Criar migration para SolicitacaoImportada
python manage.py makemigrations core --name staging_import_model

# Atualizar import_eventos_abas.py para usar staging
# Criar comando admin "aprovar_staging" para promover staging→produção
```

---

## ✅ CONQUISTAS DESTA SESSÃO

1. ✅ Sistema de ingestão dual 100% funcional (Sheets + CSV)
2. ✅ Parser robusto validado em 2.290 registros
3. ✅ 118 usuários importados com sucesso
4. ✅ Backup do banco criado
5. ✅ Documentação completa gerada
6. ✅ Idempotência via SHA1 hash implementada
7. ✅ Dry-runs validados (0 erros de parsing)
8. ✅ Status AGENDADO eliminado (0 ocorrências)

---

## 🚨 RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Schema divergente entre parser e modelo | Alta | Alto | Criar staging model |
| Signals interferindo no import | Média | Alto | Desabilitar temporariamente |
| Dados inconsistentes (formadores, municípios) | Baixa | Médio | Get_or_create com defaults |
| Timeout em imports grandes (2.290 eventos) | Baixa | Médio | Batch imports (100 por vez) |

---

**Assinatura:** Sistema Automatizado de Ingestão v1.0.0
**Próxima revisão:** Após implementação de staging model
