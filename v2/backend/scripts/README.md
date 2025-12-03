# Scripts Utilitários

Scripts standalone para operações de manutenção e análise.

## Arquivos

### auditoria_planilhas.py

Auditoria de dados das planilhas Google Sheets vs arquivos locais.
Gera relatórios CSV em `/.agents/outbox/`.

**Uso (Docker):**
```bash
docker compose exec -T web python scripts/auditoria_planilhas.py
```

**Relatórios gerados:**
- `relatorio_eventos_duplicados.csv`
- `relatorio_intervalos_invalidos.csv`
- `relatorio_eventos_cancelados_adiados.csv`
- `relatorio_outros_sem_formador.csv`
- `relatorio_pessoas_pendentes_match.csv`
- `relatorio_comparacao_projetos.csv`
- `relatorio_divergencias_sheets_vs_xlsx.csv`

### validate_etl.py

Validação de dados após importação ETL.

**Uso:**
```bash
docker compose exec -T web python scripts/validate_etl.py
```
