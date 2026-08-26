# Passe adversarial: provar que o gate não pode ser contornado

**Provar que um gate morde não prova que ele não pode ser evitado.** São duas
coisas, e a segunda quase nunca é feita — inclusive por quem acabou de escrever
dez testes verdes.

Em 2026-08-26, uma hora tentando *explorar* os próprios gates achou duas coisas
que 46 testes unitários não pegaram.

## A pergunta que abre o passe

> Existe uma edição pequena que faz este arquivo **sair do escopo** do gate, em
> vez de satisfazê-lo?

Todo gate tem um `continue`, um `skip`, um filtro. Cada um é uma porta.

## Achado 1 — evasão por rebaixamento de status

Três gates pulavam um doc quando `status` estava em `{historical, stale,
superseded, deprecated}`. Trocar **uma palavra** — `canonical → historical` —
fazia a spec sumir dos três.

```
antes:   check_issue_drift acusa: 1   |  doc_drift_report vê a spec: 2
depois:  check_issue_drift acusa: 0   |  doc_drift_report vê a spec: 1
         OK 53 suspeita(s), nenhuma raiz acima do piso medido.
```

O que torna esse pior que os outros: **a contagem CAI.** O ratchet não só
aprovou — ele *sugeriu apertar o piso*. A evasão foi lida como progresso.

Compare com o caso irmão (`sources_of_truth` encolhendo): lá a contagem ficava
igual. Aqui ela melhora. **Quando a evasão melhora a métrica, o gate está
premiando quem o burla.**

Conserto: detector que compara o campo contra a versão da base e bloqueia o
rebaixamento sem justificativa. Roda **antes** do skip, porque é o skip que ele
protege.

## Achado 2 — o detector cego por plataforma

O mais incômodo: **o exploit passou localmente, com os testes verdes.**

```python
subprocess.run([...], text=True)          # ← sem encoding
```

`text=True` sem `encoding` usa o default da plataforma: cp1252 no Windows.
`git show` de uma spec com acento estoura `UnicodeDecodeError` **dentro da thread
leitora** do subprocess, e `r.stdout` volta `None`. Como todo chamador faz
`if not antes:`, `None` é falsy e o detector **desliga em silêncio** — com o gate
reportando OK.

Consequência: um detector esteve cego no Windows desde que subiu. Só o CI
(Linux/UTF-8) o exercitava. Verde nos dois lugares, funcionando em um.

Regra: **em subprocess que lê texto, sempre `encoding="utf-8", errors="replace"`,
e nunca deixe a função devolver `None`** quando a assinatura diz `str`.

## O checklist do passe

Para cada gate, tente:

1. **Sair do escopo por campo** — mudar `status`, `type`, qualquer chave que o
   gate usa para pular. → detector de rebaixamento
2. **Sair do escopo por caminho** — mover para `_archive/`, renomear a extensão.
   Cuidado: mover para arquivo pode ser a ação *legítima*; calibre com isso em
   mente antes de bloquear.
3. **Esvaziar a declaração** — apagar linhas de `sources_of_truth`, esvaziar a
   lista que o gate lê. → detector de encolhimento
4. **Esconder em comentário** — waiver dentro de `<!-- -->`, que não é revisável.
5. **Fazer o gate não medir** — repo raso, API indisponível, dependência
   ausente. Cada um precisa de resposta explícita e diferente.
6. **Rodar na outra plataforma** — encoding, separador de caminho, binário com
   nome diferente (`powershell` vs `pwsh`).

## Como testar sem se machucar

O exploit exige mexer no repositório real. Duas regras aprendidas do jeito
difícil, no mesmo dia:

- **Commite o trabalho ANTES de testar exploit.** Duas vezes um `git reset
  --hard` / `reset --soft` + `stash drop` apagou a implementação inteira, que não
  estava commitada. Na primeira vez o reflog não ajudou (nunca houve commit).
- **Restaure com `git checkout <arquivo>`**, não com reset destrutivo na árvore
  toda. Ou teste num clone descartável.

## E registre o limite que você NÃO resolveu

Todo discriminador tem um caso que ele erra. Fixe-o como teste que documenta o
erro, com a saída de escape:

```python
def test_declaracao_historica_correta_precisa_de_allowlist(tmp_path):
    """Este teste não finge que o gate acerta: fixa que ele ERRA aqui.

    Se algum dia surgir um discriminador melhor, este teste é o que vai
    reprovar e cobrar a atualização.
    """
```

Caso real: `src/api.ts` **foi** apagado, e a skill que o cita está **certa** — a
frase é «There is no `src/api.ts` anymore». Declaração histórica correta sobre
arquivo realmente apagado é, por histórico, indistinguível de instrução que ficou
para trás. O allowlist é a saída, e o teste diz isso em voz alta.
