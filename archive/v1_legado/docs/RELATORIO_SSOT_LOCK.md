# SSOT Lock — Gestão x Ingestão

## Data: 2025-10-05 11:50 UTC

## 🔒 SSOT Lock Completo

Este relatório documenta a execução do pipeline de lock SSOT (Single Source of Truth) + gates + legacy cleanup de forma idempotente.

---

## ✅ 0) Sanity Check

```
System check identified no issues (0 silenced).
HTTP 200
```

**Status**: Sistema operacional sem erros.

---

## ✅ 1) SSOT Confirmado

**Admin Models (16 modelos):**
```
- ('auth', 'Group', 'auth_group')
- ('authtoken', 'TokenProxy', 'authtoken_token')
- ('core', 'Aprovacao', 'core_aprovacao')
- ('core', 'AprovacaoHistorico', 'core_aprovacaohistorico')
- ('core', 'Deslocamento', 'core_deslocamento')
- ('core', 'DisponibilidadeFormadores', 'core_disponibilidadeformadores')
- ('core', 'EventoGoogleCalendar', 'core_eventogooglecalendar')
- ('core', 'LogAuditoria', 'core_logauditoria')
- ('core', 'MarcadorPlanilha', 'core_marcadorplanilha')
- ('core', 'Municipio', 'core_municipio')
- ('core', 'Participante', 'core_participante')
- ('core', 'Projeto', 'core_projeto')
- ('core', 'Solicitacao', 'core_solicitacao')
- ('core', 'TipoEvento', 'core_tipoevento')
- ('core', 'Usuario', 'core_usuario')
- ('core', 'VinculoUsuarioSetor', 'core_vinculousuariosetor')
```

**Conclusão**: Admin/Views apontam para models/tabelas **core** (e staging para disponibilidades). SSOT confirmado.

---

## ✅ 2) Gates Ativos

### Gate anti-MENSAL:
**Encontrado em comandos de import** (comportamento correto):
```
ingestao/management/commands/import_disponibilidades_sheets.py:
  - "Não usar MENSAL; priorizar ANUAL, DESLOCAMENTO, Bloqueios"
  - if tipo.upper() == "MENSAL": [SKIP]

ingestao/management/commands/import_disponibilidades_stage.py:
  - "Ignora MENSAL."
```

**Status**: ✅ Gate anti-MENSAL ativo e funcionando.

### Gate Status Legados (código ativo):
**Encontrados em código ativo** (uso legítimo):
```
- core/models.py: AGENDADO (status válido para Google Calendar sync)
- core/models.py: SincronizacaoStatus.PENDENTE (para sincronização)
- core/models.py: NotificacaoStatus "pendente" (para notificações)
- core/services/*: Uso de AGENDADO em conflict detection (correto)
```

**NÃO encontrados** (removidos corretamente):
- SolicitacaoStatus.PENDENTE → normalizado para CRIADO (migration 0036)
- SolicitacaoStatus.REPROVADO → normalizado para CRIADO (migration 0036)

**Status**: ✅ Nada de status legados **PENDENTE/REPROVADO** em SolicitacaoStatus (código ativo limpo).

---

## ✅ 3) SSOT Job (Espelho + Comparador)

**Espelhos baixados:**
```
OK /app/data/ingest/daily/abas/acerta.csv
OK /app/data/ingest/daily/abas/brincando.csv
OK /app/data/ingest/daily/abas/vidas.csv
OK /app/data/ingest/daily/abas/super.csv
OK /app/data/ingest/daily/abas/outros.csv
```

**Comparador executado:**
```
Aba ACerta:     490 registros (Fonte A = Fonte B) ✅
Aba Brincando:  191 registros (Fonte A = Fonte B) ✅
Aba Vidas:      285 registros (Fonte A = Fonte B) ✅
Aba Super:     1245 registros (Fonte A = Fonte B) ✅
Aba Outros:      79 registros (Fonte A = Fonte B) ✅

TOTAL: 2290 registros
Resultado: Fontes idênticas ✅
```

**Relatório salvo**: `docs/VALIDACAO_FONTE_DUPLA.md`

**Status**: ✅ SSOT job executado com sucesso (manual run).

---

## ✅ 4) RBAC Aplicado

**Mapeamento cargo → grupos:**
```python
{
  "Formador":     ["formador"],
  "Coordenador":  ["coordenador"],
  "Gerente":      ["superintendencia", "controle"]
}
```

**Resultado**: `[OK] RBAC aplicado para 0 usuários com cargo.`

**Observação**: Nenhum usuário atual possui campo `cargo` preenchido. RBAC será aplicado automaticamente quando usuários forem criados/atualizados com cargo.

**Status**: ✅ Lógica RBAC pronta (idempotente).

---

## ⚠️ 5) Legacy Check: ingestao_disp_staging

**Verificação:**
```
Tabela: ingestao_disp_staging
Linhas: 452
Uso por Model Django: UNUSED
```

**Análise**:
- Tabela **existe** com 452 linhas
- **NÃO** é usada por nenhum Model Django ativo
- Possivelmente legacy de experimentos anteriores

**Ação Tomada**: ⏸️ **NÃO alterada** (tem dados, sem uso ativo)

**Recomendação**: Criar migration para renomear → `ingestao_disp_staging_legacy_YYYYMMDD` se confirmado que não é necessária.

**Status**: ⚠️ Identificada como legacy, mas mantida intacta (segurança).

---

## 🎯 Resumo Executivo

| Item | Status | Detalhes |
|------|--------|----------|
| Sanity Check | ✅ | Sistema operacional (HTTP 200, zero erros) |
| SSOT Confirmado | ✅ | Admin/Views → core models |
| Gate anti-MENSAL | ✅ | Ativo em comandos de import |
| Gate Status Legados | ✅ | PENDENTE/REPROVADO removidos de SolicitacaoStatus |
| SSOT Job | ✅ | 2290 registros validados (fontes idênticas) |
| RBAC | ✅ | Lógica pronta (0 usuários com cargo atualmente) |
| Legacy Table | ⚠️ | ingestao_disp_staging (452 linhas, UNUSED) |

---

## 📋 Próximos Passos (Opcional)

1. **Migration para tabela legacy**: Renomear `ingestao_disp_staging` → `ingestao_disp_staging_legacy_20251005` (se confirmado não uso)
2. **Popular campo cargo**: Atribuir cargo aos 111 usuários para ativar RBAC automático
3. **Automatizar SSOT job**: Agendar comparador diário via cron/Celery

---

## 🔐 Decisão: **LOCKED** ✅

**SSOT validado e locked:**
- Gestão e Ingestão usam as **mesmas tabelas core**
- Gates anti-regressão ativos
- Espelhos validados (2290 registros idênticos)
- Sistema pronto para operação contínua

**Data do Lock**: 2025-10-05 11:50 UTC
**Branch**: fix/limpa-diff-20251003-191daf4
**Commit**: 1e5215b (comparador diário manual run)
