# Armadilhas que produzem número errado

A calibragem depende de uma medição. Se a medição está quebrada, o gate nasce
errado — e todas as armadilhas abaixo produzem um número **plausível**, que é o
que as torna perigosas.

Todas foram cometidas em 2026-08, e cada uma custou uma rodada.

## 1. Um texto que NEGA a mentira contém as mesmas palavras

A mais recorrente — cometida **três vezes** numa única auditoria.

Contar a ocorrência de `"restore quebrado"` não distingue:

- a spec que **afirma** que o restore está quebrado (drift real)
- a nota que **corrige** dizendo «não está mais quebrado» (correta)
- o teste que **prova** que não está quebrado (correto)

Filtro por palavra-chave não resolve isso, nunca. Duas saídas que funcionaram:

- **perguntar a um fato**, não ao texto: `git log --diff-filter=D` sabe se o
  caminho existiu; `gh issue view` sabe se a issue fechou. Precisão de 17% → 83%.
- **exigir marcador de estado E ausência de marcador de correção na mesma linha**
  — e ainda assim chamar o resultado de «suspeita», não de veredito.

## 2. Contar palavra-chave em vez de ler a afirmação

Variante da anterior, do lado do teste:

```python
assert "EM DRIFT" not in r.stdout   # ← a linha de resumo diz "0 em drift"
```

A asserção reprovava com a saída **correta**. O que se verifica é a contagem, não
a presença da palavra: `assert "0 em drift" in r.stdout`.

## 3. Teste que passa por vacuidade

Asserção negativa é satisfeita por saída vazia. Cinco testes passaram **antes da
implementação existir**, porque o script ausente produz stdout vazio.

Antes de toda asserção negativa, prove que a coisa foi medida:

```python
assert "pagamento.spec.md" in r.stdout, "a spec nem foi medida"
assert "0 em drift" in r.stdout
```

Mesmo princípio no harness: um **piso mínimo de casos**, senão 2 testes somem em
silêncio e o conjunto fica verde por não ter rodado.

## 4. `exit != 0` não diz POR QUE

Um teste de âncora quebrada deu `EXIT=1` e foi dado como prova. Ao ler a
mensagem, o motivo era **link não-encontrado**, não âncora — o alvo relativo não
existia. O teste não exercitava o que dizia exercitar.

Quando o gate reprova, **leia a mensagem**, não só o código de saída.

## 5. Teste que passa por acidente do ambiente

Um teste do caminho «sem API» assumia que `gh` não existe. No runner ele existe e
está autenticado — o teste passou por sorte, e viraria flake.

Force a condição (`PATH` sem o binário), não torça por ela. Mesma família:
`powershell` só existe com esse nome no Windows; o `ubuntu-latest` tem `pwsh`.

## 6. Glob e regex que perdem o arquivo mais importante

Duas medições erradas seguidas, ambas plausíveis:

- `*.yml*` **não casa `ci.yaml`** — o arquivo com mais jobs do repositório. Deu
  «4 divergências» quando eram 9, e me levou a afirmar que o plano estava
  desatualizado. O plano estava certo.
- `(?:ts|tsx)` — a alternância do `re` é **ordenada**: `Componente.tsx` casa como
  `Componente.ts`, um arquivo que não existe, e o achado nasce falso. Ordene do
  mais longo para o mais curto.

Para estrutura (YAML, JSON), **parseie**; não faça grep.

## 7. `lstrip` não remove prefixo

```python
".claude/x".lstrip("./")   # → "claude/x"
```

`lstrip` remove um **conjunto de caracteres**, não um prefixo. Comeu o ponto de
`.claude` e o allowlist nunca casava.

## 8. `text=True` sem `encoding` em subprocess

No Windows o default é cp1252. Saída com acento estoura `UnicodeDecodeError`
dentro da thread leitora e `r.stdout` vira `None` — que é falsy, então o detector
desliga em silêncio. Sempre `encoding="utf-8", errors="replace"`, e nunca deixe
a função devolver `None` quando a assinatura diz `str`.

O mesmo vale para **imprimir**: o console cp1252 derruba o script ao escrever
`→` ou acento. `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` no
topo. Um relatório que só roda no CI não serve para quem precisa dele antes do PR.

## 9. Relatório de agente não é evidência

Agentes fabricam achado com confiança — inclusive um endpoint inexistente citado
9 vezes em 6 arquivos. E o inverso também ocorre: uma sessão paralela mostrou que
três «códigos mortos» que eu havia confirmado eram **load-bearing**, presos por
invariante forçada em teste (`assert not orphans`, `len(__all__) >= 54`) ou
documentados de propósito.

Regra: **«0 usos» não é «morto»** quando há invariante forçada por teste ou
decisão de design registrada. Verifique com as próprias mãos, `file:line`,
imediatamente antes de agir — nunca na palavra do agente, nem na sua própria
memória de três passos atrás.
