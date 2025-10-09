# Verificação Contexto Supremo
**Data:** 2025-10-08T20:47:26.998884
**Status:** FAIL

## Itens Verificados

- **TIME_ZONE**: ✅ PASS
- **DOCS_ROOT**: ✅ PASS
- **Grupos minimos**: ❌ FAIL
  - Erro: Grupos faltando: {'gerente'}
- **Papeis permitidos**: ✅ PASS
- **AGENDADO por ingestao**: ✅ PASS
- **Solicitante conformidade**: ❌ FAIL
  - Erro: Apenas 0.0% conforme (esperado >= 95%)
- **Views disponibilidades**: ✅ PASS
- **MarcadorPlanilha UNIQUE**: ✅ PASS

## Métricas

- **vinculos_por_papel**: {'FORMADOR': 15, 'GERENTE': 1, 'COORDENADOR': 1}
- **vinculos_por_setor**: {'Superintendência': 1, 'ACerta': 5, 'Setor Teste': 5, 'Vidas': 1, 'Setor Test Dia 2': 5}
- **total_eventos**: 2178
- **eventos_por_status**: {'REALIZADO': 1712, 'CRIADO': 263, 'CANCELADO': 95, 'APROVADO': 108}
- **solicitante_conformidade_pct**: 0.0
- **vw_disp_normalizada_count**: 780
- **vw_disp_anual_agregada_count**: 336
- **vw_disp_desloc_agregada_count**: 376
- **vw_disp_bloq_agregada_count**: 68
- **total_marcadores**: 120
- **total_usuarios**: 229
- **total_vinculos**: 17
- **total_setores**: 5

## Erros

- Grupos minimos: Grupos faltando: {'gerente'}
- Solicitante conformidade: Apenas 0.0% conforme (esperado >= 95%)
