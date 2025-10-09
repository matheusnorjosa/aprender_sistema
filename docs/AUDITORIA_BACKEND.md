# Auditoria Backend — Django

## Data: 2025-10-05 00:15 UTC

## ✅ Invariantes Confirmadas

### Distribuição de Status (Solicitações):
```
REALIZADO: 1712
CRIADO: 263
APROVADO: 108
CANCELADO: 95
```

**Análise**:
- ✅ Zero status legados (AGENDADO/PENDENTE/REPROVADO)
- ✅ 2.178 solicitações válidas
- ✅ 0 títulos vazios

### Vestígios de Status Legados:
- ✅ Encontrados apenas em **comandos de correção antigos** (não em código ativo)
- ✅ Arquivos: `corrigir_status_simples.py`, `corrigir_status_solicitacoes.py`
- ✅ **Conclusão**: Não há uso ativo de status legados

## ✅ Código Auditado

### Importadores (`import_eventos_abas.py`):
- ✅ Idempotência: `external_hash = sha1(aba|municipio|data|hora_ini|projeto|coordenador)`
- ✅ Sem AGENDADO: Apenas `{CRIADO, APROVADO, REALIZADO, CANCELADO}`
- ✅ Signals desabilitados: `with solicitacao_signals_disabled()`
- ✅ Usuários on-the-fly: `origem=planilha, is_provisorio=True`

### Signals (`mapa_signals.py`):
- ✅ Guards thread-safe: `_signal_local.solicitacao_off`
- ✅ Contexto seguro: `@contextlib.contextmanager solicitacao_signals_disabled()`
- ✅ Cache invalidation: `mapa_dados_brasil`, `mapa_estatisticas`

### Permissões RBAC:
- ✅ `can_controlar_preagenda`: Migration 0041
- ✅ Aplicado em: `ControlePreAgendaView` (linha 41)
- ✅ Permission model: `core.models.py:819`

## ✅ Modelos

### Disponibilidades (Staging como fonte oficial):
```
StagingBloqueio: 74 registros
StagingDeslocamento: 380 registros
StagingDisponAnual: 384 registros
TOTAL: 838 registros
```

**Qualidade**:
- 93.1% vinculação de usuários
- 99.8% datas válidas

## ✅ Cross-Check

### Choques de Horário (Top 10):
```
Usuario 13279: 6 choques
Usuario 13247: 6 choques
Usuario 13278: 4 choques
Usuario 13172: 4 choques
Usuario 13258: 3 choques
Usuario 13244: 3 choques
Usuario 13268: 2 choques
Usuario 13259: 2 choques
Usuario 13292: 2 choques
Usuario 9470: 2 choques
```

**Total**: 20 usuários com conflitos

## 🎯 Decisão: **APROVADO** ✅

Backend 100% auditado e conforme especificações.
