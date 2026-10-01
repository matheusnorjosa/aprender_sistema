---
title: Princípios de UX
status: canonical
last_verified: 2026-09-30
verified_at_commit: 2a79cf5c6bafdddb8d2072036f2b0527c3426f3f
sources_of_truth:
  - v2/frontend/e2e/checklist/accessibility.spec.ts
  - v2/frontend/e2e/checklist/performance.spec.ts
  - v2/frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts
  - v2/frontend/src/components/ResponsiveTable.tsx
  - v2/frontend/src/components/AcoesLinha.tsx
---

# Princípios de UX

Regra do dono (30/09/2026) para toda tela nova ou alterada. O **padrão técnico** das telas (lista enxuta, linha
expandida, detalhe, sidebar por largura) está em [pages.spec.md](./pages.spec.md), seção "Padrão responsivo"; esta spec
diz **o que buscar, o que evitar e como provar**.

## Para quem é

Sistema interno, usado todo dia por quem conhece o domínio (coordenação, DAT, Controle, aprovadoras). Simplicidade ×
flexibilidade é um trade-off real: telas de operação frequente pedem **densidade** (densidade média, decisão do dono
no C1) e poucos cliques; tarefas raras ou de quem está começando pedem guia (ex.: o wizard de solicitação).

## O que buscar

- **Clareza.** Hierarquia visual, ação principal óbvia, rótulos com as palavras do domínio (setor, gerência,
  formador), nunca a chave técnica (id, username). Estados de **carregando, vazio e erro** desenhados: o vazio diz o
  que fazer; o erro mostra a mensagem real do backend, não um texto genérico.
- **Fluidez.** Só os campos e cliques essenciais; defaults inteligentes (ex.: a gerência da lotação, a data de hoje);
  **complexidade só quando for relevante** — lista enxuta, e o resto a um clique (linha expandida ou detalhe por assunto).
- **Acessibilidade é baseline, não extra.** Contraste AA, tudo operável por teclado com foco visível, nome acessível em
  todo controle, leitor de tela anuncia estado (aberto/fechado, ordenação, erro).
- **Feedback.** Toda ação responde: botão em loading enquanto a API trabalha, mensagem de sucesso ou erro ao terminar.
  Nada de clique mudo.

## O que evitar

- **Paternalismo.** Não esconder informação que a tarefa precisa porque "pode confundir". O que sai da grade continua
  a um clique (linha expandida/detalhe). Restringir por **permissão** é outra coisa, e é regra de RBAC.
- **Dark patterns.** Desfazer, cancelar, excluir e sair são tão fáceis de achar quanto o contrário. Ação destrutiva
  começa no **Cancelar** e cita o nome do registro: é segurança, não obstáculo.
- **Polish que não serve à tarefa.** Animação e microinteração só quando ajudam a entender o que aconteceu; nada de
  biblioteca nova de animação nem efeito que custe desempenho ou manutenção.

## Limites duros (negociáveis só para cima)

| Limite | Onde é cobrado hoje |
|---|---|
| WCAG 2.1 AA (axe `wcag2a`, `wcag2aa`, `wcag21aa`) | [`accessibility.spec.ts`](../../../frontend/e2e/checklist/accessibility.spec.ts), job `[required] checklist tests`. Cobre o login, `/perfil`, `/dat/admin/usuarios` (C1) e as 7 rotas do C2 (`/dat/admin/grupos`, `/setores`, `/funcoes`, `/gerencias`, `/municipios`, `/produtos`, `/projetos-gerais`) a 360 e 1280 px, mais o erro de carga das opções em Gerências e Produtos e o vazio com filtro de Produtos: **cada PR de tela acrescenta suas telas** |
| Teclado e leitor de tela nos componentes do padrão | E2E `menu-lateral-teclado` e `mais-acoes-teclado` no mesmo job |
| Core Web Vitals: LCP < 2,5 s, CLS < 0,1, JS inicial < 200 KB | [`performance.spec.ts`](../../../frontend/e2e/checklist/performance.spec.ts), mesmo job (mede a página inicial) |
| Sem rolagem horizontal em 360/768/1024/1280 | [`sem-rolagem-horizontal.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts) com ratchet de `PENDENTES` |

O Lighthouse (relatório no PR e série mensal na #2066) acompanha, mas não bloqueia merge (decisão do dono, 28/09).

## Provar que a tarefa melhorou

"Ficou mais bonito" não é critério. Para as tarefas principais de cada perfil (ex.: criar solicitação, aprovar
pendentes, cadastrar usuário), comparar antes e depois: **taxa de sucesso, tempo de conclusão e taxa de erro**. Antes
da liberação e depois de mudança grande de tela, **teste com 5 pessoas por perfil** (Nielsen: ~85% dos problemas
aparecem); mais que isso tem retorno decrescente.

## Checklist do PR de tela

1. Estados de carregando, vazio e erro presentes e com texto útil.
2. Nenhuma informação da tarefa sumiu; o que saiu da grade está a um clique.
3. Ação destrutiva começa no Cancelar e cita o nome; ação principal com loading e mensagem.
4. Teclado de ponta a ponta, foco visível, nomes acessíveis; a tela entra no axe do `checklist`.
5. Sem rolagem horizontal nas 4 larguras; combinações tiradas de `PENDENTES`.
6. Nenhuma animação ou dependência nova sem ganho na tarefa.
