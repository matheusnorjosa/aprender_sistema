# Plano: Paginas de Importacao Web

**Data**: 2026-02-04
**Objetivo**: Criar paginas de importacao web para Bloqueios, Deslocamentos e Eventos

---

## Decisoes do Usuario

- **Bloqueios**: Adicionar na pagina `/bloqueios` (Disponibilidade.tsx)
- **Prioridade**: Bloqueios primeiro
- **Eventos**: Versao completa (todos os campos, ate 5 formadores)

---

## Ordem de Implementacao

1. **Bloqueios** (mais simples, valida o padrao)
2. **Deslocamentos** (complexidade similar)
3. **Eventos** (mais complexo, com Participations)

---

## 1. Import de Bloqueios

### Colunas Esperadas

| Coluna | Obrigatorio | Aliases | Validacao |
|--------|-------------|---------|-----------|
| usuario | Sim | nome, formador | Resolver por nome |
| inicio | Sim | data_inicio, start | Datetime flexivel |
| fim | Sim | data_fim, end | Deve ser > inicio |
| tipo | Sim | type | T=Total, P=Parcial |
| motivo | Nao | obs, observacao | Texto livre |

### Hash de Idempotencia
```
SHA1(usuario_id|inicio_iso|fim_iso|tipo)
```

### Backend

**Novo arquivo**: `apps/core/views_import_bloqueios.py`
```python
class ImportBloqueiosView(APIView):
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request):
        dry_run = request.query_params.get("dry_run", "true").lower() in ("1", "true")
        # ... validar arquivo, chamar service
```

**Novo arquivo**: `apps/core/services/bloqueios_import.py`
```python
def import_bloqueios_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    # Reaproveitar logica de etl_import_bloqueios.py
    # transaction.atomic() + set_rollback(True) para dry_run
```

**Modificar**: `apps/core/urls.py`
```python
path("disponibilidade/import-bloqueios/", ImportBloqueiosView.as_view(), name="import-bloqueios"),
```

### Frontend

**Modificar**: `src/api/ops.ts`
```typescript
export async function importBloqueios(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/disponibilidade/import-bloqueios/', file, dryRun);
}
```

**Modificar**: `src/pages/Disponibilidade.tsx`
- Adicionar terceiro Card com ImportUploader
- Layout: 3 colunas (Criar | Listar | Importar)

```tsx
<Col xs={24} lg={8}>
  <Card title="Importar Bloqueios" bordered={false}>
    <ImportUploader
      label="Importar em Massa"
      description="CSV/XLSX: usuario, inicio, fim, tipo (T/P), motivo"
      onDryRun={async (file) => toValidationResult(await importBloqueios(file, true))}
      onApply={async (file) => {
        const result = await importBloqueios(file, false);
        fetchBlocks();
        return toApplyResult(result);
      }}
    />
  </Card>
</Col>
```

### Testes

**Novo arquivo**: `apps/core/tests/test_import_bloqueios.py`
- test_dry_run_returns_stats
- test_apply_creates_records
- test_idempotency_no_duplicates
- test_permission_denied_for_formador
- test_invalid_file_returns_400

---

## 2. Import de Deslocamentos

### Colunas Esperadas

| Coluna | Obrigatorio | Aliases | Validacao |
|--------|-------------|---------|-----------|
| usuario | Sim | email, nome | Email ou nome |
| origem | Sim | de, from | Texto |
| destino | Sim | para, to | Texto |
| data_inicio | Sim | start, inicio | Date |
| data_fim | Sim | end, fim | >= data_inicio |
| observacao | Nao | obs, notes | Texto |

### Hash de Idempotencia
```
SHA1(usuario_id|origem|destino|data_inicio|data_fim)
```

### Backend

**Novo arquivo**: `apps/core/views_import_deslocamentos.py`

**Novo arquivo**: `apps/core/services/deslocamentos_import.py`

**Modificar**: `apps/core/urls.py`
```python
path("deslocamentos/import/", ImportDeslocamentosView.as_view(), name="import-deslocamentos"),
```

### Frontend

**Modificar**: `src/api/ops.ts` - adicionar `importDeslocamentos()`

**Modificar**: `src/pages/Deslocamentos/DeslocamentosPage.tsx` - adicionar ImportUploader

---

## 3. Import de Eventos (Versao Completa)

### Colunas Esperadas

| Coluna | Obrigatorio | Aliases | Validacao |
|--------|-------------|---------|-----------|
| municipio | Sim | cidade | Resolver por nome |
| projeto | Sim | project | Resolver por nome |
| tipo_evento | Sim | tipo | Resolver ou criar |
| data | Sim | date | Date |
| hora_inicio | Sim | inicio, start_time | Time |
| hora_fim | Sim | fim, end_time | > hora_inicio |
| coordenador | Sim | coord, coord_email | Resolver usuario |
| formador1 | Nao | | Criar Participation |
| formador2 | Nao | | Criar Participation |
| formador3 | Nao | | Criar Participation |
| formador4 | Nao | | Criar Participation |
| formador5 | Nao | | Criar Participation |
| encontro | Nao | ef | Numero do encontro |
| segmento | Nao | | Texto |
| local | Nao | location | Texto |

### Hash de Idempotencia
```
SHA1(municipio_id|projeto_id|tipo_id|data|hora_inicio|hora_fim)
```

### Regras de Negocio (PA)

- Se projeto.fluxo == 'SUPER' e nao passou da data: status = 'pendente'
- Se projeto.fluxo == 'NAO_SUPER' ou data < hoje: status = 'aprovado'
- Criar Participation para coordenador (role='COORDENADOR')
- Criar Participation para cada formador1-5 (role='FORMADOR')

### Backend

**Novo arquivo**: `apps/core/views_import_eventos.py`

**Novo arquivo**: `apps/core/services/eventos_import.py`

**Modificar**: `apps/core/urls.py`
```python
path("solicitacoes/import/", ImportEventosView.as_view(), name="import-eventos"),
```

### Frontend

**Modificar**: `src/api/ops.ts` - adicionar `importEventos()`

**Modificar**: `src/pages/Controle/ControlePage.tsx` - adicionar terceiro ImportUploader

---

## Arquivos Criticos (Referencia)

### Padroes Existentes

| Arquivo | Uso |
|---------|-----|
| `apps/core/views_imports.py` | Padrao de View para upload |
| `apps/core/services/controle_acoes_import.py` | Padrao de Service |
| `apps/dat_ingest/management/commands/etl_import_bloqueios.py` | Logica a extrair |
| `apps/dat_ingest/management/commands/etl_upsert_deslocamento.py` | Logica a extrair |
| `apps/dat_ingest/management/commands/etl_upsert_acompanhamento.py` | Logica a extrair |
| `src/components/ImportUploader.tsx` | Componente frontend |
| `src/api/ops.ts` | Helper postMultipart |
| `src/pages/Disponibilidade.tsx` | Pagina a modificar |
| `src/pages/Deslocamentos/DeslocamentosPage.tsx` | Pagina a modificar |
| `src/pages/Controle/ControlePage.tsx` | Pagina a modificar |

---

## Verificacao

### Apos cada import implementado:

```bash
# 1. Testes backend
docker exec aprender_v2-web-1 pytest apps/core/tests/test_import_bloqueios.py -v

# 2. Type check
cd v2/backend && pyright apps/core/views_import_bloqueios.py apps/core/services/bloqueios_import.py

# 3. Build frontend
cd v2/frontend && npm run build

# 4. Teste manual
# - Acessar /bloqueios
# - Upload arquivo CSV/XLSX de teste
# - Verificar dry-run mostra stats corretos
# - Aplicar e verificar dados no banco
```

### Arquivo de Teste (bloqueios_teste.csv)
```csv
usuario,inicio,fim,tipo,motivo
Joao Silva,2026-02-10 08:00,2026-02-10 12:00,P,Consulta medica
Maria Santos,2026-02-15 00:00,2026-02-15 23:59,T,Ferias
```

---

## Estimativa

| Fase | Componente | Tempo |
|------|------------|-------|
| 1 | Bloqueios backend | 2h |
| 1 | Bloqueios frontend | 1h |
| 1 | Bloqueios testes | 1h |
| 2 | Deslocamentos backend | 2h |
| 2 | Deslocamentos frontend | 1h |
| 2 | Deslocamentos testes | 1h |
| 3 | Eventos backend | 4h |
| 3 | Eventos frontend | 1h |
| 3 | Eventos testes | 2h |
| **Total** | | **15h** |
