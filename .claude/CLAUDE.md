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

## Diretrizes de UX/IHC — ISO 9241-110
Todo o sistema deve seguir os princípios ergonômicos para design de sistemas interativos:
1. **Adequação à tarefa**  
   - Mostrar apenas informações e ações necessárias para a tarefa atual.  
   - Evitar sobrecarga de opções irrelevantes.

2. **Auto-descritividade**  
   - Elementos da interface (botões, campos, mensagens) devem indicar claramente sua função.  
   - Fornecer feedback imediato após cada ação.

3. **Conformidade com expectativas do usuário**  
   - Usar termos, ícones e fluxos que sigam convenções amplamente conhecidas.  
   - Manter consistência de comportamento entre telas.

4. **Tolerância a erros**  
   - Prevenir erros sempre que possível.  
   - Fornecer mensagens claras e opções para corrigir ou desfazer ações críticas.

5. **Controle explícito**  
   - Executar ações apenas quando o usuário confirmar.  
   - Evitar execuções automáticas sem consentimento.

6. **Adequação à individualização**  
   - Permitir ajustes não-críticos de preferência (ex.: filtros, visualização).  
   - Manter consistência geral.

7. **Adequação à aprendizagem**  
   - Interfaces intuitivas para novos usuários, com padrões repetidos.  
   - Usar tooltips ou dicas contextuais quando necessário.

### Diretrizes visuais complementares
- Uso consistente de **Bootstrap 5.3** para responsividade.
- Paleta de cores e tipografia padronizadas.
- Destaque visual para ações primárias.
- Layouts limpos, com hierarquia visual clara.

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
- Garanta que toda implementação siga as diretrizes de UX/IHC descritas acima.

## Ações que o Claude **deve priorizar**
1. Ler código e **entender** onde alterar (sem editar ainda).
2. Produzir um **plano passo a passo** (com justificativas) — *think harder*.
3. Implementar em pequenos commits verificados por testes.
4. Escrever mensagens de commit descritivas.
5. Evitar mudanças não solicitadas em testes (exceto quando o plano exigir).
6. Validar se a interface gerada cumpre todos os princípios de UX/IHC.

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
