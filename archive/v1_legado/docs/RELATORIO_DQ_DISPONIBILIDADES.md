# Relatório DQ — Disponibilidades (Staging)

## Data: 2025-10-05 00:20 UTC

## 📊 Métricas de Qualidade

### Dados Consolidados:
```json
{
  "staging": {
    "StagingDisponAnual": {
      "total": 384,
      "sem_usuario": 48,
      "datas_ausentes": 0
    },
    "StagingDeslocamento": {
      "total": 380,
      "sem_usuario": 4,
      "datas_ausentes": 1
    },
    "StagingBloqueio": {
      "total": 74,
      "sem_usuario": 6,
      "datas_ausentes": 0
    }
  }
}
```

## ✅ Análise de Qualidade

### StagingDisponAnual (384 registros):
- **Vinculação**: 87.5% (336/384) ✅
- **Datas**: 100% (0 ausentes) ✅
- **Campos**: usuario_id, nome_formador, ano, mes, horas

### StagingDeslocamento (380 registros):
- **Vinculação**: 98.9% (376/380) ✅
- **Datas**: 99.7% (379/380) ✅
- **Campos**: usuario_id, nome_formador, data, origem, destino, observacao

### StagingBloqueio (74 registros):
- **Vinculação**: 91.9% (68/74) ✅
- **Datas**: 100% (0 ausentes) ✅
- **Campos**: usuario_id, nome_formador, inicio, fim, motivo

## 🔍 Índices Criados

```sql
-- Usuario lookups
CREATE INDEX core_stagingdisponanual_uid_idx ON core_stagingdisponanual (usuario_id);
CREATE INDEX core_stagingdeslocamento_uid_idx ON core_stagingdeslocamento (usuario_id);
CREATE INDEX core_stagingbloqueio_uid_idx ON core_stagingbloqueio (usuario_id);

-- Date ranges
CREATE INDEX core_stagingdisponanual_mes_idx ON core_stagingdisponanual (mes);
CREATE INDEX core_stagingdisponanual_ano_idx ON core_stagingdisponanual (ano);
CREATE INDEX core_stagingdeslocamento_data_idx ON core_stagingdeslocamento (data);
CREATE INDEX core_stagingbloqueio_inicio_idx ON core_stagingbloqueio (inicio);
CREATE INDEX core_stagingbloqueio_fim_idx ON core_stagingbloqueio (fim);
```

## 🎯 Decisão: **APROVADO** ✅

**Qualidade Geral**: 93.1% vinculação média, 99.8% datas válidas

**Staging congelado** como fonte oficial para disponibilidades.
