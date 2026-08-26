---
name: gate-calibration
description: Projetar um gate de CI que sobreviva — decidir se bloqueia, avisa ou usa ratchet; medir a precisão antes de escolher; limpar antes de trancar; e provar que ele não pode ser contornado. Use ao criar ou recalibrar qualquer check automático, especialmente sobre dívida preexistente.
---

# Calibragem de gate

Um gate que reprova demais é desligado. Um que avisa demais vira decoração. A
diferença entre os dois não é opinião — é uma medição que se faz **antes** de
escrever o código.

Esta skill é o destilado de nove gates construídos no AS v2 em 2026-08 (PRs
#1847 → #1870). Cada regra abaixo tem um número medido atrás, e vários vieram de
erro cometido e corrigido no mesmo dia.

> Complementa, não substitui: `ci-github-actions` (operar o CI),
> `verification-gate` (verificar antes de afirmar), `test-driven-development`
> (o teste vermelho primeiro).

## O procedimento, em ordem

**1. Meça a precisão ANTES de escolher a calibragem.**
Rode o detector cru contra o repositório e conte: de N achados, quantos exigem
ação? Sem esse número você está chutando.

Medido aqui: «caminho citado que não existe» deu **12 achados, 2 reais — 17%**.
Um gate assim é revertido na primeira semana. Perguntar ao `git log
--diff-filter=D` se o repositório *já teve* aquele caminho levou a precisão para
**83%**, e aí ele podia bloquear.

**2. Escolha pelo par (precisão, quem consegue consertar).**

| | bloqueia | avisa | ratchet |
|---|---|---|---|
| precisão | alta | qualquer | qualquer |
| frequência | rara | ampla | qualquer |
| conserta no PR? | **sim** | não importa | não (é dívida de terceiros) |
| dívida preexistente | zero, ou allowlist | tanto faz | **é o caso de uso** |

O critério **«quem consegue consertar»** decide sozinho vários casos: rótulo
`[required]` que não está no ruleset só se corrige com ação de admin, então
bloquear o autor do PR por isso é a receita para desligarem o gate — vira aviso.
Já um context exigido que nenhum job produz trava merge para sempre e se
conserta dentro do PR (alguém renomeou um job) — bloqueia.

**3. Limpe antes de trancar.**
Se o repo já nasce sujo, o gate nasce vermelho e alguém o desliga antes que ele
pegue o primeiro caso novo. Duas saídas provadas aqui:

- **allowlist com motivo obrigatório** — entrada nua é o começo da erosão. Toda
  linha carrega `alvo — por quê`, e entradas temporárias dizem quando sair.
- **ratchet sobre piso medido** — quando a redução é trabalho de outra frente. A
  contagem por raiz não pode *crescer*; cair é livre e o gate sugere apertar.

**4. Não poder medir não é aprovar.**
Repositório raso, API fora do ar, dependência ausente, conjunto vazio: cada um
precisa de uma resposta explícita, e nunca a mesma.

- **fora do alcance e não-consertável** (API caiu) → avisa alto, sai 0. Fazer o
  CI depender da disponibilidade de terceiro é pior que a doença.
- **local e consertável** (falta PyYAML) → falha alto. Pular deixa o gate verde
  por não ter rodado.
- **resultado vazio suspeito** (ruleset devolveu zero contexts) → trate como
  falha de leitura, não como ausência de problema.

**5. Prove que morde — e que não dá para contornar.**
São duas coisas diferentes, e a segunda é a que ninguém faz. Ver
`reference/evasao.md`.

## Regras que valem sozinhas

**Piso anti-vacuidade.** Um harness que roda pouco passa por não testar. Se o
número de casos cair abaixo de um mínimo, reprove — foi assim que 2 testes
sumiram em silêncio e o gate ficou verde por vacuidade.

**Um SSOT por conceito.** Dois parsers respondendo diferente sobre o mesmo
arquivo são o gerador de drift que o gate combate.

**A saída é interface.** Ela é lida por gente e colada em PR. Nomeie o arquivo e
a linha, diga *por que* foi apontado, e ensine a saída de escape. Se houver
conserto óbvio (o próximo número livre, o commit que apagou o arquivo),
imprima — senão quem for consertar erra de novo.

**Cada gate reporta por si.** No CI, `if: ${{ !cancelled() }}` nos steps: sem
isso a falha de um pula os outros e o diagnóstico chega pela metade.

**Heurística assumida, não disfarçada.** Se o detector é heurístico, a saída diz
«suspeita», não «erro». O que o ratchet trava é o número de suspeitas.

## Anti-padrões, todos cometidos aqui

- **Escolher a calibragem por intuição.** Sempre meça antes.
- **Bloquear sobre dívida preexistente.** Vermelho no dia 1 = gate desligado.
- **Avisar sem ação associada.** Foi assim que o aviso de 180 dias virou
  decoração. Aviso precisa de um gesto barato que o resolva.
- **Contrabandear calibragem por outra porta.** Exigir um checkbox sempre que um
  detector *avisa* converte esse detector em bloqueio. Se você recusou bloquear
  no detector, não bloqueie no checkbox dele.
- **Deixar o allowlist aceitar entrada sem motivo.**
- **Confiar em `text=True` sem `encoding`** em subprocess — ver
  `reference/medicao.md`.

## Referências

- `reference/calibragem.md` — os nove gates, com o número medido de cada um
- `reference/evasao.md` — passe adversarial: como um gate é contornado
- `reference/medicao.md` — armadilhas que produzem número errado
