# 🚀 ABRIR PR AGORA — Instruções Imediatas

## ✅ Quick Action

**1. Acessar URL:**
```
https://github.com/matheusnorjosa/aprender_sistema/compare/main-v1...rebuild/2025-contexto-supremo
```

**2. Configurar PR:**
- **Base:** `main-v1`
- **Compare:** `rebuild/2025-contexto-supremo`
- **Title:** `v2: bootstrap skeleton (sem impactar v1)`

**3. Copiar descrição de:** `PR_INSTRUCTIONS_V2_BOOTSTRAP.md`

**4. Criar PR** → Clicar "Create Pull Request"

---

## 🔒 Proteção de Branches (Após PR Aberto)

### No GitHub:
1. Ir em **Settings** → **Branches** → **Add branch protection rule**

2. **Branch name pattern:** `main-v1`

3. **Configurar:**
   - [x] Require a pull request before merging
   - [x] Require approvals (mínimo: 1)
   - [x] Require status checks to pass before merging
     - [x] Require branches to be up to date before merging
     - Status checks: `CI`, `lint`, `tests` (adicionar após workflow criado)
   - [x] Do not allow bypassing the above settings

4. **Salvar**

5. **Repetir para:** `rebuild/2025-contexto-supremo`

---

## ✅ Checklist Pós-PR

- [ ] PR aberto
- [ ] Proteção de branch `main-v1` configurada
- [ ] Proteção de branch `rebuild/2025-contexto-supremo` configurada
- [ ] CI rodando (após merge do workflow)
- [ ] Review solicitado

---

**Status:** ⏳ Aguardando abertura manual do PR
**Link direto:** https://github.com/matheusnorjosa/aprender_sistema/compare/main-v1...rebuild/2025-contexto-supremo
