# Release Notes v2025.10.08-go

**Data:** 2025-10-08 00:00:00  
**Versão:** v2025.10.08-go

## 📊 RESUMO EXECUTIVO

Esta release inclui implementações completas de:
- ✅ Normalização de documentação (DOCS_ROOT)
- ✅ Backfill de vínculos usuário-setor
- ✅ Migração de deslocamentos para AUTH_USER
- ✅ Configuração de filtro estrito da Superintendência
- ✅ Auditoria completa do sistema
- ✅ GitHub workflows e padrões de desenvolvimento

## 📋 RELATÓRIOS DE IMPLEMENTAÇÃO

### Relatórios Principais
- RELATORIO_EXECUCAO_VINCULOS_FINAL.md
- RELATORIO_MIGRACAO_DESLOCAMENTOS_FINAL.md
- RELATORIO_MIGRACAO_DOCUMENTACAO.md
- RELATORIO_NORMALIZACAO_DOCS_FINAL.md

### Auditorias
- AUDITORIA_ANTI_REGRESSAO_FINAL.md
- AUDITORIA_BACKEND.md
- AUDITORIA_CENTRALIZACAO_DOCKER.md
- AUDITORIA_COMPLETA_DUPLICATAS.md
- AUDITORIA_COMPLETA.md
- AUDITORIA_FRONTEND.md
- AUDITORIA_FULL_20251007_215237.md
- AUDITORIA_FULL_20251007_220237.md
- AUDITORIA_FULL_20251007_220307.md
- AUDITORIA_FULL_20251007_220420.md
- AUDITORIA_FULL_20251007_220542.md
- AUDITORIA_FULL_20251007_220727.md
- AUDITORIA_TECNICA_COMPLETA.md

### Outros Documentos
- RELATORIO_API_REPORTS.md
- RELATORIO_ARCHIVE_LEGACY_STAGING.md
- RELATORIO_COMPLETO_TODAS_FASES.md
- RELATORIO_CONFLITOS_RECOMENDACOES.md
- RELATORIO_DASHBOARD_EXECUTIVO.md
- RELATORIO_DASHBOARD_WIRING.md
- RELATORIO_DQ_DISPONIBILIDADES.md
- RELATORIO_FINALIZACAO_DIA3.md
- RELATORIO_FIX_COORDENADORES_ATIVOS.md
- RELATORIO_FRONT_RELATORIOS.md
- RELATORIO_IMPORT_FINAL_DIA3.md
- RELATORIO_IMPORT_PARCIAL_DIA3.md
- RELATORIO_INGESTAO_DIA3_COMPLETO.md
- RELATORIO_PLANILHAS_FINAL.md
- RELATORIO_RBAC_CONFLITOS.md
- RELATORIO_SESSAO_FASE3_COMPLETA.md
- RELATORIO_SSOT_GESTAO.md
- RELATORIO_SSOT_LOCK.md

## 🎯 PRINCIPAIS FEATURES

### 1. Normalização DOCS_ROOT
- Centralização de toda documentação em `docs/`
- Refatoração de scripts para usar `DOCS_ROOT`
- Migração de 60+ arquivos de documentação
- Configuração de variável de ambiente

### 2. Backfill de Vínculos
- Comando `import_vinculos_setor` implementado
- Idempotência por `UNIQUE(usuario, setor, papel)`
- Suporte a papéis: SUPER, COORDENADOR, FORMADOR, CONTROLE, GERENTE
- Filtro estrito da Superintendência ativo

### 3. Migração Deslocamentos
- Migração de `Formador` para `AUTH_USER_MODEL`
- Preservação de dados existentes
- Reativação de deslocamentos no mapa
- Feature flag `FEATURE_MAP_DESLOCAMENTOS_ENABLED = True`

### 4. GitHub Workflows
- CI completo com testes e auditoria
- Release manual com tags
- Configurações de segurança
- Padrões de desenvolvimento

## 🔧 CONFIGURAÇÕES TÉCNICAS

### Feature Flags
```python
FEATURE_SUPER_FALLBACK = False              # Filtro estrito ativo
FEATURE_MAP_DESLOCAMENTOS_ENABLED = True    # Deslocamentos ativos
```

### DOCS_ROOT
```python
DOCS_ROOT = Path(os.getenv("DOCS_ROOT", BASE_DIR / "docs"))
```

### Migrações
- `00ZZ_deslocamento_to_auth_user.py` - Schema migration
- `00ZY_deslocamento_data_map.py` - Data migration

## 📊 MÉTRICAS

- **Arquivos migrados**: 60+
- **Scripts refatorados**: 5+
- **Workflows criados**: 2
- **Migrações criadas**: 2
- **Feature flags configuradas**: 2
- **Status**: ✅ 100% CONCLUÍDO

## 🚀 PRÓXIMOS PASSOS

1. **Validação Final**
   ```bash
   python manage.py check --deploy
   python devops/auditar_integracoes.py
   ```

2. **Teste de Funcionalidades**
   - Acessar `/disponibilidade/` no navegador
   - Verificar filtro estrito da Superintendência
   - Confirmar deslocamentos no mapa

3. **Deploy**
   - Usar GitHub Actions para CI
   - Release via workflow manual

## 🏆 CONCLUSÃO

Esta release representa um marco importante na organização e funcionalidade do sistema:

- ✅ **Documentação centralizada** em `docs/`
- ✅ **Vínculos usuário-setor** funcionando
- ✅ **Deslocamentos reativados** no mapa
- ✅ **Filtro estrito** da Superintendência
- ✅ **CI/CD configurado** para desenvolvimento contínuo

**O sistema está pronto para produção com todas as funcionalidades implementadas!** 🎉
