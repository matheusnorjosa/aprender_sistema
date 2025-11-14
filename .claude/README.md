# Configuração .claude — Aprender Sistema v2

**Versão**: 1.0
**Data**: 04/11/2025
**Baseado em**: Configuração Premium Claude Code adaptada para Python/Django

---

## 🚀 Quick Start

### Documentação Principal

📖 **[GUIA_USO.md](GUIA_USO.md)** - Guia completo com exemplos e workflows

### Comandos Essenciais

```bash
/new-feat <descrição>        # Implementar nova feature
/review <arquivo>            # Revisar código (compliance)
/check-conflicts             # Testar RF03 (RD-01 a RD-08)
/approve-flow                # Testar PA-01 a PA-07
/migrate [app]               # Criar/aplicar migrations
/test-coverage [path]        # Coverage 90%+
/deploy-staging [type]       # Checklist pré-deploy
```

---

## 📂 Estrutura

```
.claude/
├── CLAUDE.md                    # Regras de negócio AS v2 (1.432 linhas)
├── CLAUDE-principles.md         # Qualidade de código (463 linhas)
├── GUIA_USO.md                  # Guia completo de uso ⭐
├── README.md                    # Este arquivo
├── settings.json                # Configurações Claude Code
├── commands/                    # 9 comandos slash
└── skills/                      # 3 skills completas
    ├── aprender-domain/         # CP, RD, PA, RF
    ├── django-patterns/         # Models, serializers, views
    └── etl-guidelines/          # Idempotência, quality gates
```

---

## 🎯 Filosofia

### Complementaridade, não duplicação

- **CLAUDE.md** → Regras de negócio, histórico, infraestrutura
- **CLAUDE-principles.md** → Qualidade de código universal
- **Skills** → Detalhamento técnico específico
- **Commands** → Workflows que integram tudo

---

## 📚 Documentação por Contexto

### Preciso implementar feature
1. Ler: `CLAUDE.md` (regras de negócio)
2. Ler: `CLAUDE-principles.md` (qualidade)
3. Usar: `/new-feat <descrição>`
4. Consultar: Skills relevantes

### Preciso revisar código
1. Usar: `/review <arquivo>`
2. Validar: `/check-conflicts` ou `/approve-flow` (se aplicável)
3. Verificar: `/test-coverage`

### Preciso importar dados
1. Consultar: `skills/etl-guidelines/SKILL.md`
2. Usar: `/etl-dry <comando>`
3. Validar: Relatório em `out_etl/`
4. Usar: `/etl-apply <comando>`

### Preciso fazer deploy
1. Usar: `/test-coverage` (garantir 90%+)
2. Usar: `/migrate` (se há migrations)
3. Usar: `/deploy-staging full`
4. Seguir checklist completo

---

## ✅ Validações Importantes

### Antes de Commitar
- [ ] Testes passando (`pytest -v`)
- [ ] Coverage >= 90% (`/test-coverage`)
- [ ] Code review (`/review <arquivo>`)
- [ ] Conventional commit (`feat/fix/chore: message`)

### Antes de PR
- [ ] Branch atualizada com main
- [ ] Todos os testes passando
- [ ] Coverage threshold met
- [ ] Documentação atualizada (se necessário)

### Antes de Deploy
- [ ] PR aprovada e merged
- [ ] Tests passando em staging
- [ ] Database backup criado
- [ ] Rollback plan ready

---

## 🔗 Referências Rápidas

| Preciso de... | Arquivo/Comando |
|---------------|-----------------|
| Regras CP/RD/PA/RF | `CLAUDE.md` ou `aprender-domain` skill |
| Qualidade de código | `CLAUDE-principles.md` |
| Implementar model | `django-patterns` skill |
| Criar ETL | `etl-guidelines` skill |
| Fazer migration | `/migrate` |
| Testar coverage | `/test-coverage` |
| Deploy staging | `/deploy-staging` |

---

## 📊 Estatísticas

- **Documentação**: 3 arquivos principais (3.100+ linhas)
- **Skills**: 3 completas (2.000+ linhas)
- **Comandos**: 9 workflows completos
- **Testes cobertos**: RF03 (17 testes), PA-01 a PA-07 (5 testes)
- **Coverage target**: 90%+ overall, 100% critical

---

## 🤝 Contribuindo

### Adicionar novo comando

1. Criar `.claude/commands/meu-comando.md`
2. Seguir template dos comandos existentes
3. Adicionar descrição ao `GUIA_USO.md`
4. Testar comando

### Adicionar nova skill

1. Criar `.claude/skills/minha-skill/SKILL.md`
2. Adicionar frontmatter:
   ```yaml
   ---
   name: minha-skill
   description: Descrição breve
   ---
   ```
3. Adicionar ao `GUIA_USO.md`

### Atualizar documentação

- **CLAUDE.md**: Ao adicionar PR, feature, ou regra de negócio
- **CLAUDE-principles.md**: Ao definir novo padrão de qualidade
- **GUIA_USO.md**: Ao adicionar comando/skill ou exemplos

---

## 🔧 Configurações

### settings.json

```json
{
  "permissions": {
    "allow": ["Read", "Edit", "Write", "Bash(git *)", "Bash(docker compose *)", "Bash(python manage.py *)"]
  },
  "includeCoAuthoredBy": false
}
```

**Importante**: `includeCoAuthoredBy=false` preservado conforme especificação.

---

## 📝 Changelog

### v1.0 (04/11/2025)
- ✅ Estrutura base criada
- ✅ CLAUDE.md preservado (1.432 linhas)
- ✅ CLAUDE-principles.md criado (463 linhas)
- ✅ 9 comandos slash implementados
- ✅ 3 skills completas (aprender-domain, django-patterns, etl-guidelines)
- ✅ GUIA_USO.md completo com exemplos

---

## 📞 Suporte

**Dúvidas sobre**:
- Uso da configuração → Consulte `GUIA_USO.md`
- Regras de negócio → Consulte `CLAUDE.md`
- Qualidade de código → Consulte `CLAUDE-principles.md`
- Implementação específica → Consulte skills relevantes

**Problemas**:
- Comando não funciona → Verifique sintaxe no `GUIA_USO.md`
- Skill não ativa → Referência explícita no prompt
- Coverage falha → Use `/test-coverage` para detalhes

---

**Última Atualização**: 04/11/2025
**Versão**: 1.0
**Licença**: Proprietário (Aprender Sistema v2)
