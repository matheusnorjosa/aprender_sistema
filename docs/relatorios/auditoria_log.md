# 🔍 AUDITORIA FUNCIONAL - SISTEMA APRENDER
**Data:** 2025-08-29  
**Ambiente:** Local Django (Docker indisponível)  
**Objetivo:** Validar fluxo crítico Solicitação → Aprovação → Google Calendar

---

## 📊 LOG DE EXECUÇÃO

### ✅ AMBIENTE - DOCKER ATIVO
- **Status:** Docker Desktop iniciado com sucesso
- **Stack:** PostgreSQL + Django rodando em containers
- **URL:** http://localhost:8000 (302 → /login/ ✅)
- **Containers:** aprender_db (healthy) + aprender_web (up)

### ✅ GRUPOS E USUÁRIOS - CONFIGURADOS
- **6 grupos criados:** admin, controle, coordenador, formador, superintendencia, diretoria
- **6 usuários de teste:** admin_teste, controle_teste, coordenador_teste, formador_teste, super_teste, diretoria_teste
- **Arquivo:** `out/grupos_permissoes.txt` e `out/usuarios_grupos.json`

### ✅ DADOS DE APOIO - CRIADOS
- **Município:** Aurora do Norte/AN (ID: 2f276ac2...)
- **Projeto:** Projeto Piloto 2025 (ID: 6a42b433...)
- **Formador:** João Silva (ID: d0680a28...)
- **4 Tipos de Evento:** Formação Online, Formação Presencial, Workshop, Capacitação
- **Arquivo:** `out/ids_base.json`
