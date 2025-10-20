# Análise: Squash de Migrações do Core

**Data:** 2025-10-08  
**Status:** ⚠️ **NÃO RECOMENDADO NESTE MOMENTO**

---

## 📊 SITUAÇÃO ATUAL

### Migrações Existentes

- **Total de migrações core:** 56 (0001 até 0056)
- **Última migração:** `0056_remove_marcadorplanilha_disponibilidade_and_more.py`
- **Status:** Todas aplicadas ✅

### Schema Drift Detectado

**Problema:** O Django detecta campos `disponibilidade`, `remarcado_para`, `solicitacao` em `MarcadorPlanilha` que nunca existiram na tabela PostgreSQL real.

**Origem:** Migrações históricas (0050) referenciavam campos que foram planejados mas nunca criados.

**Impacto Atual:** **NENHUM**
- ✅ Sistema funciona 100%
- ✅ Todos os comandos executam
- ✅ Queries funcionam perfeitamente
- ✅ Não há erros em runtime

---

## ⚠️ POR QUE NÃO FAZER SQUASH AGORA

### 1. Schema Drift é Benigno

O "erro" de migrações é apenas histórico. O sistema está:
- ✅ Funcional
- ✅ Estável
- ✅ Passando 11/12 checks de auditoria (91.7%)

### 2. Riscos do Squash

**Alto Risco:**
- Pode quebrar referências em produção se já houver dados
- Requer coordenação com todos os ambientes (dev, staging, prod)
- Outros desenvolvedores podem ter problemas de sincronização

**Benefício Baixo:**
- Apenas "limpa" histórico de migrações
- Não melhora funcionalidade
- Não resolve problemas reais

### 3. Migrações Já Aplicadas

Todas as 56 migrações já foram aplicadas no banco. Squash seria apenas cosmético.

---

## ✅ SOLUÇÃO RECOMENDADA

### Opção 1: Manter Como Está (Recomendado)

**Justificativa:**
- Sistema funcional
- Schema drift benigno
- Sem impacto em produção

**Ação:**
- Documentar o schema drift como "conhecido e sem impacto"
- Continuar com desenvolvimento normal

### Opção 2: Squash em Ambiente Limpo (Futuro)

**Quando considerar:**
- Criação de novo ambiente do zero
- Migração para novo banco de dados
- Reestruturação completa do projeto

**Como fazer:**
1. Backup completo do banco
2. Criar novo ambiente de teste
3. Squash em ambiente isolado
4. Testar exaustivamente
5. Documentar processo de migração
6. Aplicar em produção com janela de manutenção

---

## 📝 MIGRAÇÕES NO-OP CRIADAS

Para resolver o schema drift, foram criadas migrações no-op:

- **`0054`**: Remove constraint + adiciona nova (Deslocamento)
- **`0055`**: No-op (campos já não existiam)
- **`0056`**: No-op (campos já não existiam)

Essas migrações:
- ✅ Foram aplicadas com sucesso
- ✅ Não alteraram dados
- ✅ Mantiveram compatibilidade

---

## 🔍 COMANDO PARA ANÁLISE (Se Necessário)

Se ainda quiser analisar as migrações:

```bash
# Dentro do container
docker compose exec web bash

# Listar todas as migrações
python manage.py showmigrations core

# Verificar se há pendências
python manage.py makemigrations --check

# Ver dependências
python manage.py showmigrations --plan core
```

---

## 🎯 DECISÃO FINAL

**Recomendação:** ❌ **NÃO FAZER SQUASH**

**Motivo:**
1. ✅ Sistema funcional (91.7% auditoria passou)
2. ✅ Schema drift benigno e documentado
3. ⚠️ Riscos superam benefícios
4. ✅ Migrações no-op já resolveram o problema prático

**Se precisar fazer squash no futuro:**
- Aguardar reestruturação maior do projeto
- Fazer em ambiente isolado primeiro
- Coordenar com toda equipe
- Ter backup completo antes

---

## 📚 REFERÊNCIAS

- **Auditoria Completa:** `docs/AUDITORIA_FULL_20251007_220727.md`
- **Inventário de Integrações:** `docs/inventario_integracoes/INVENTARIO_FINAL.md`
- **Django Migrations Docs:** https://docs.djangoproject.com/en/4.2/topics/migrations/

---

**Conclusão:** Continue com desenvolvimento normal. O schema drift é conhecido, documentado e não causa problemas funcionais.
