# Plano de Importação de Dados — Multi-Ano

**Data**: 2026-01-26
**Status**: Em planejamento

---

## 1. Mapeamento Planilhas → Modelos

### 1.1 Acompanhamento de Agenda (2025/2026)

| Planilha | Aba | Modelo Django | ETL Existente | Status |
|----------|-----|---------------|---------------|--------|
| Acompanhamento 2026.xlsx | Super, Vidas, ACerta, Brincando, Outros | `Solicitacao` + `Participation` | `etl_upsert_acompanhamento` | ✅ Importado |
| Acompanhamento 2025.xlsx | Super, Vidas, ACerta, Brincando, Outros | `Solicitacao` + `Participation` | `etl_upsert_acompanhamento` | 📋 Pendente |

**Campos mapeados**:
| Coluna Planilha | Campo Modelo | Observação |
|-----------------|--------------|------------|
| Projeto | `Solicitacao.projeto` | FK para Projeto |
| Município | `Solicitacao.municipio` | FK para Municipio |
| Tipo | `Solicitacao.tipo_evento` | FK para TipoEvento |
| Data + Hora Início | `Solicitacao.inicio` | DateTime UTC |
| Data + Hora Fim | `Solicitacao.fim` | DateTime UTC |
| Local | `Solicitacao.local` | String |
| Encontro | `Solicitacao.encontro` | String |
| Segmento | `Solicitacao.segmento` | String |
| Observação | `Solicitacao.observacoes` | Text |
| Formador 1, Formador 2 | `Participation` (role=FORMADOR) | FK para Usuario |
| Coordenador | `Participation` (role=COORDENADOR) | FK para Usuario |

---

### 1.2 Disponibilidade (2025/2026)

| Planilha | Aba | Modelo Django | ETL Existente | Status |
|----------|-----|---------------|---------------|--------|
| Disponibilidade 2026.xlsx | DESLOCAMENTO | `Deslocamento` | `etl_upsert_deslocamento` | 📋 Pendente (16 registros) |
| Disponibilidade 2025.xlsx | DESLOCAMENTO | `Deslocamento` | `etl_upsert_deslocamento` | 📋 Pendente (508 registros) |
| Disponibilidade 2026.xlsx | Bloqueios | `AvailabilityBlock` | `etl_import_bloqueios` | ⏸️ Vazio (0 registros) |
| Disponibilidade 2025.xlsx | Bloqueios | `AvailabilityBlock` | `etl_import_bloqueios` | 📋 Pendente (41 registros) |

**Campos DESLOCAMENTO**:
| Coluna Planilha | Campo Modelo | Observação |
|-----------------|--------------|------------|
| FORMADOR | `Deslocamento.usuario` | FK para Usuario |
| SAÍDA | `Deslocamento.origem` | String |
| DESTINO | `Deslocamento.destino` | String |
| DATA SAÍDA | `Deslocamento.start_date` | Date |
| DATA CHEGADA | `Deslocamento.end_date` | Date |
| OBS | `Deslocamento.observacao` | Text |

**Campos Bloqueios**:
| Coluna Planilha | Campo Modelo | Observação |
|-----------------|--------------|------------|
| FORMADOR | `AvailabilityBlock.usuario` | FK para Usuario |
| DATA INÍCIO | `AvailabilityBlock.inicio` | DateTime UTC |
| DATA FIM | `AvailabilityBlock.fim` | DateTime UTC |
| TIPO | `AvailabilityBlock.tipo` | T=Total, P=Parcial |
| MOTIVO | `AvailabilityBlock.motivo` | String |

---

### 1.3 Planilha de Controle (2025/2026)

| Planilha | Aba | Modelo Django | ETL Existente | Status |
|----------|-----|---------------|---------------|--------|
| Controle 2026.xlsx | AÇÕES | `AcaoControle` | `etl_import_acoes_controle` | 📋 Pendente (210 registros) |
| Controle 2025.xlsx | AÇÕES | `AcaoControle` | `etl_import_acoes_controle` | 📋 Pendente (688 registros) |
| Controle 2026.xlsx | COMPRAS | N/A (novo modelo?) | ❌ Não existe | 🆕 Criar modelo? |
| Controle 2025.xlsx | COMPRAS | N/A | ❌ Não existe | 🆕 Criar modelo? |
| Controle 2026.xlsx | CADASTROS | `AcaoDAT` (tipo_acao=cadastro) | `etl_import_dat_cadastros` | 📋 Pendente (252 registros) |
| Controle 2025.xlsx | CADASTROS | `AcaoDAT` (tipo_acao=cadastro) | `etl_import_dat_cadastros` | 📋 Pendente (1516 registros) |
| Controle 2026.xlsx | DAT | `AcaoDAT` | `etl_import_dat_cadastros` | 📋 Verificar |
| Controle 2025.xlsx | DAT | `AcaoDAT` | `etl_import_dat_cadastros` | 📋 Verificar |

**Campos AÇÕES (AcaoControle)**:
| Coluna Planilha | Campo Modelo | Observação |
|-----------------|--------------|------------|
| MUNICÍPIO | `AcaoControle.municipio` | FK para Municipio |
| PROJETO | `AcaoControle.projeto` | FK para Projeto |
| COORDENADOR | `AcaoControle.coordenador` | FK para Usuario |
| DATA ENTREGA | `AcaoControle.data_entrega` | Date |
| DATA CARTA | `AcaoControle.data_carta` | Date |
| CONTATO INICIAL | `AcaoControle.contato_inicial` | Date |
| DATA REUNIÃO | `AcaoControle.data_reuniao` | Date |
| OBS | `AcaoControle.observacao` | Text |

---

### 1.4 Usuários

| Planilha | Modelo Django | ETL Existente | Status |
|----------|---------------|---------------|--------|
| Usuários.xlsx | `Usuario` | `import_usuarios_from_csv` | ✅ Base importada |
| todososusuarios.xlsx | `Usuario` (complemento) | Manual | 📋 Verificar duplicados |
| formadores_fluir.xlsx | `Usuario` (setor Fluir) | `seed_formadores_fluir` | ✅ Importado |

---

## 2. Estratégia Multi-Ano

### 2.1 Problema

O sistema precisa:
1. Armazenar dados de 2025 (histórico)
2. Exibir dados de 2026 (ano atual) por padrão
3. Permitir acesso a dados de anos anteriores
4. Suportar anos futuros (2027+)

### 2.2 Solução: Filtro por Data

**Abordagem recomendada**: Usar `inicio` (DateTime) existente para filtrar por ano.

```python
# Filtrar solicitações do ano atual
from django.utils import timezone
ano_atual = timezone.now().year  # 2026

Solicitacao.objects.filter(inicio__year=ano_atual)
Deslocamento.objects.filter(start_date__year=ano_atual)
AcaoControle.objects.filter(data_entrega__year=ano_atual)
```

**Vantagens**:
- Não requer migração de schema
- Campo `inicio` já tem índice
- Funciona com qualquer ano futuro

**Frontend (API)**:
```python
# ViewSet com filtro de ano
class SolicitacaoViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        ano = self.request.query_params.get('ano')
        if ano:
            qs = qs.filter(inicio__year=int(ano))
        else:
            # Padrão: ano atual
            qs = qs.filter(inicio__year=timezone.now().year)
        return qs
```

### 2.3 Identificador de Ano na Importação

Para distinguir dados importados de diferentes anos:

**Opção A**: Usar nome do arquivo no `external_hash`
```python
# Hash inclui ano de origem
hash_input = f"2025|{projeto}|{municipio}|{inicio.isoformat()}"
```

**Opção B**: Campo `ano_referencia` (opcional)
```python
# Em Solicitacao (migration necessária)
ano_referencia = models.PositiveIntegerField(
    null=True,
    blank=True,
    help_text="Ano de referência dos dados importados"
)
```

### 2.4 Decisão Recomendada

**Usar Opção A (hash com ano)** + **filtro por `inicio__year`**:
- Zero migrações necessárias
- Funciona imediatamente
- Dados de 2025 e 2026 coexistem na mesma tabela
- UI pode filtrar por ano via query param `?ano=2025`

---

## 3. Ordem de Importação

### Fase 1: Dados de Referência (já feito)
1. ✅ Municípios (seed)
2. ✅ Projetos (seed)
3. ✅ TipoEvento (seed)
4. ✅ Usuários base

### Fase 2: Dados 2026 (Ano Atual)
1. ✅ Solicitações 2026 (92 registros)
2. ✅ Participações 2026 (232 registros)
3. 📋 Deslocamentos 2026 (16 registros)
4. ⏸️ Bloqueios 2026 (0 registros)
5. 📋 Ações Controle 2026 (210 registros)
6. 📋 Cadastros DAT 2026 (252 registros)

### Fase 3: Dados 2025 (Histórico)
1. 📋 Solicitações 2025 (~5000 registros)
2. 📋 Participações 2025 (estimativa ~12000)
3. 📋 Deslocamentos 2025 (508 registros)
4. 📋 Bloqueios 2025 (41 registros)
5. 📋 Ações Controle 2025 (688 registros)
6. 📋 Cadastros DAT 2025 (1516 registros)

---

## 4. Comandos ETL Necessários

### 4.1 DESLOCAMENTO (requer normalização prévia)

A planilha DESLOCAMENTO tem formato diferente (múltiplas pessoas por linha).
Usar comando de normalização primeiro:

```bash
# Passo 1: Normalizar 2026
docker exec aprender_v2-web-1 python manage.py normalize_deslocamento \
  --file "/app/data/csv-import/Disponibilidade _ 2026.xlsx" \
  --output "/app/out_etl/deslocamento_2026.csv"

# Passo 2: Importar CSV normalizado
docker exec aprender_v2-web-1 python manage.py etl_upsert_deslocamento \
  --file "/app/out_etl/deslocamento_2026.csv" --dry-run

# Passo 3: Aplicar (sem --dry-run)
docker exec aprender_v2-web-1 python manage.py etl_upsert_deslocamento \
  --file "/app/out_etl/deslocamento_2026.csv"

# Repetir para 2025
docker exec aprender_v2-web-1 python manage.py normalize_deslocamento \
  --file "/app/data/csv-import/Disponibilidade _ 2025.xlsx" \
  --output "/app/out_etl/deslocamento_2025.csv"

docker exec aprender_v2-web-1 python manage.py etl_upsert_deslocamento \
  --file "/app/out_etl/deslocamento_2025.csv"
```

### 4.2 BLOQUEIOS (novo comando criado)

```bash
# Dry-run 2025 (41 registros)
docker exec aprender_v2-web-1 python manage.py etl_import_bloqueios \
  --file "/app/data/csv-import/Disponibilidade _ 2025.xlsx" --dry-run

# Aplicar 2025
docker exec aprender_v2-web-1 python manage.py etl_import_bloqueios \
  --file "/app/data/csv-import/Disponibilidade _ 2025.xlsx"

# 2026 está vazio (0 registros) - não precisa importar
```

### 4.3 Ações Controle (existente)

```bash
# 2026 (210 registros)
docker exec aprender_v2-web-1 python manage.py etl_import_acoes_controle \
  --file "/app/data/csv-import/Planilha de Controle - 2026.xlsx" --dry-run

# 2025 (688 registros)
docker exec aprender_v2-web-1 python manage.py etl_import_acoes_controle \
  --file "/app/data/csv-import/Planilha de Controle - 2025.xlsx" --dry-run
```

### 4.4 Cadastros DAT (existente)

```bash
# 2026 (252 registros)
docker exec aprender_v2-web-1 python manage.py etl_import_dat_cadastros \
  --file "/app/data/csv-import/Planilha de Controle - 2026.xlsx" --dry-run

# 2025 (1516 registros)
docker exec aprender_v2-web-1 python manage.py etl_import_dat_cadastros \
  --file "/app/data/csv-import/Planilha de Controle - 2025.xlsx" --dry-run
```

### 4.5 Acompanhamento 2025 (histórico)

```bash
# Normalizar e importar (volume maior)
docker exec aprender_v2-web-1 python manage.py etl_upsert_acompanhamento \
  --source "/app/data/csv-import/Acompanhamento de Agenda _ 2025.xlsx" --dry-run
```

---

## 5. Dados COMPRAS

A aba COMPRAS nas planilhas de controle (923 registros em 2026, 1890 em 2025) não tem modelo Django correspondente.

**Opções**:
1. **Ignorar**: Se não for requisito do sistema
2. **Criar modelo `Compra`**: Se for necessário rastrear
3. **Usar `AcaoDAT` genérico**: Com `tipo_acao="COMPRA"`

**Decisão necessária**: Verificar com stakeholder se COMPRAS deve ser importado.

---

## 6. Próximos Passos

1. [ ] Executar ETL para DESLOCAMENTO 2026 (16 registros)
2. [ ] Executar ETL para Ações Controle 2026 (210 registros)
3. [ ] Verificar/criar ETL para Bloqueios
4. [ ] Testar filtro por ano na API
5. [ ] Implementar seletor de ano no frontend
6. [ ] Importar dados históricos de 2025

---

## 7. Resumo de Volumes

| Modelo | 2026 | 2025 | Total |
|--------|------|------|-------|
| Solicitacao | 92 | ~5000 | ~5092 |
| Participation | 232 | ~12000 | ~12232 |
| Deslocamento | 16 | 508 | 524 |
| AvailabilityBlock | 0 | 41 | 41 |
| AcaoControle | 210 | 688 | 898 |
| AcaoDAT (Cadastros) | 252 | 1516 | 1768 |
| Compra (?) | 923 | 1890 | 2813 |

**Total estimado**: ~23.368 registros
