# Projeto: Aprender Sistema (AS) — Guia do Claude Code

## Contexto do Projeto
- Objetivo: Substituir planilhas pelo **AS** para solicitação → aprovação → criação de eventos (Google Calendar), com verificação de conflitos e logs de auditoria.
- Stack: **Python 3.13 + Django 5.2 + PostgreSQL 15**, containers via **Docker + docker-compose**.
- Fuso horário padrão: `America/Fortaleza`.

## Papéis e Perfis
- Coordenador, Superintendência, Controle, Formador, Admin do Sistema e Diretoria.

## Comandos úteis (Docker/Django)
- Subir ambiente: `docker compose up -d --build`
- Logs da app: `docker compose logs -f web`
- Executar comandos Django: `docker exec -it aprender_web python manage.py <comando>`
  - Exemplos: `migrate`, `makemigrations`, `createsuperuser`, `check`, `test`
- Importar formadores: `docker exec -it aprender_web python manage.py runscript core.scripts.import_formadores`
- Abrir Django Admin: `http://localhost:8000/admin/`
- App local: `http://localhost:8000/`

## Estilo de Código
- **PEP8** para Python. Prefira funções puras e views pequenas.
- Separar responsabilidades por app: `core`, `relatorios`, `api`.
- Templates Django sem SPA nesta fase.

## Fluxos essenciais (Fase 1)
- RF02 — Solicitar evento.
- RF03 — Verificar conflitos para formadores.
- RF04 — Aprovar/Reprovar solicitações.
- RF05/RF06 — Criar evento no Google Calendar + gerar link do Meet.

## Como colaborar (IMPORTANTE)
- Sempre **planeje antes de codar**. Use `/permissions plan` ou inicie com `--permission-mode plan`.
- Escreva/atualize **testes primeiro** quando possível (TDD). Só depois implemente.
- Use **Playwright MCP** para validar fluxos end-to-end quando apropriado.
- Ao finalizar, atualize este `CLAUDE.md` com decisões, comandos e avisos.

## Ações que o Claude **deve priorizar**
1. Ler código e **entender** onde alterar (sem editar ainda).
2. Produzir um **plano passo a passo** (com justificativas) — *think harder*.
3. Implementar em pequenos commits verificados por testes.
4. Escrever mensagens de commit descritivas.
5. Evitar mudanças não solicitadas em testes (exceto quando o plano exigir).

## Testes
- Unitários/integração: `python manage.py test`
- End-to-end: via **Playwright MCP** (opcional nesta fase). Registrar smoke tests dos fluxos RF02→RF04→RF05.

## Regras e Etiqueta de Repositório
- Nomes de branch: `feat/<escopo>`, `fix/<escopo>`, `chore/<escopo>`
- Commits: prefixos convencionais (`feat:`, `fix:`, `chore:`…).
- Não commitar `.env` e segredos.

## Warnings conhecidos
- `staticfiles.W004`: garantir pasta `static/` ou ajustar `STATICFILES_DIRS`.

## Anotações rápidas
- Pressione `#` aqui para o Claude incorporar instruções recorrentes (atalhos, comandos, padrões de view/form/model).
