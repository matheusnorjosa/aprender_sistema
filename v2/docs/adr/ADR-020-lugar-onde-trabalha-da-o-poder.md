# ADR-020 — Lugar onde a pessoa trabalha dá o poder

| Campo         | Valor                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------- |
| **Status**    | Aceito                                                                                    |
| **Data**      | 2026-10-06                                                                                |
| **Decisor**   | Dono do sistema (meio-termo aprovado em 06/10/2026)                                        |
| **Relacionado** | [rbac.spec.md](../specs/backend/rbac.spec.md), [ADR-019](ADR-019-metrics-composition-or.md) |

## Contexto

Hoje o poder de uma pessoa vem de sete fontes que não se conversam. As que pesam: o grupo de
setor (13), o grupo de função (5), a matriz Grupo×Capacidade editável pela tela e pelo admin
(`PermissaoFuncional.groups`), os pares Setor×Função que aprovam (`APPROVER_COMPOSITES`), o
vínculo `EquipeGerencia` (GERENTE na Superintendência aprova; os vínculos dão escopo), o texto
`Projeto.setor == Gerencia.setor_canonico` no escopo das listas e o superusuário.

Consequência: cadastrar alguém do DAT como "Equipe administrativa" na gerência DAT não dá
nenhum poder do DAT. O poder só chega quando alguém põe a pessoa no grupo "DAT", em outra tela,
e some só quando alguém lembra de tirá-la. O seed e a produção já divergem na matriz.

## Decisão

1. **Perfil da gerência → pacote em código.** Cada gerência ganha um perfil de valores fixos
   (`PADRAO`, `ADMIN_OPERACIONAL`, `CONTROLE`, `APROVACAO`, `DIRETORIA`). Cada perfil tem um
   pacote de capacidades escrito em código, versionado e testado. Gerência pedagógica fica em
   `PADRAO`, de pacote vazio.
2. **Papel só dá direitos de evento, e só na própria gerência.** FORMADOR, COORDENADOR, APOIO,
   GERENTE e EQUIPE nunca dão poder administrativo nem alcance sobre outra gerência.
3. **Só EQUIPE e GERENTE recebem o pacote** de uma gerência com perfil.
4. **Só o superusuário lota alguém em gerência com perfil** (ou como GERENTE na
   Superintendência), porque esse cadastro passa a dar poder.

Decisões do dono que entram no modelo:

- **D1** — Todo o Controle aprova eventos (a aprovação fica no pacote do Controle).
- **D2** — Segregação por histórico: quem alterou a conta do autor (senha, e-mail, vínculos)
  nos últimos 30 dias não aprova as solicitações dele, e isso fica auditado.
- **D3** — Só EQUIPE e GERENTE dão o pacote. Formador que aparecer na gerência DAT por
  planilha não vira administrador.
- **D4** — Mudar o que um setor pode fazer só por PR revisado (uma linha no pacote), não por
  clique na tela.
- **D5** — Escopo só pela própria gerência. Quem precisa de outra ganha um vínculo nela.

## Sequência (13 PRs, meio-termo)

Os PRs 1 a 11 entram antes da liberação; o 12 e o 13, depois.

1. Simulador `rbac_diff` + este ADR (somente leitura).
2. Papel EQUIPE ("Equipe administrativa") no vínculo — mergeado no #2094.
3. Fechar as portas de escrita e criar `Gerencia.perfil` sem leitura.
4. Congelar a matriz: pacotes = matriz real de produção; tela e admin só leitura; auditor no promote.
5. Dados: perfis das gerências, gerências CONTROLE e DIRETORIA, vínculos EQUIPE de quem só tem grupo.
6. Fórmula em modo união (grupos ∪ pacote).
7. Frontend com uma fonte só (`useCapabilities`).
8. Função deixa de dar poder; entram os direitos de papel.
9. Escopo por gerência, fail-closed.
10. DAT = administrador operacional (antes, atualizar PA-02/CP-02).
11. Aprovação com uma fonte só.
12. Corte: o poder deixa de ler grupos.
13. Limpeza do M2M, dos símbolos e dos grupos, 2 a 4 semanas depois do 12.

## Regra para todo PR que muda poder

Antes do merge, roda-se `python manage.py rbac_diff` em produção (somente leitura) e o dono vê,
por pessoa, quem ganha e quem perde. A mudança só segue com o OK dele. O comando lê o banco real,
não grava nada e não mostra dado pessoal (a pessoa aparece como `u<id>`).

## Consequências

- O poder passa a ter uma resposta por pergunta: onde trabalha (vínculo), o que o lugar permite
  (pacote), o que o papel acrescenta (direitos de evento na própria gerência).
- Encerrar o vínculo retira o poder sem passo manual.
- Setor administrativo novo exige PR; setor pedagógico novo continua sendo uma gerência `PADRAO`.
- Detalhe, riscos e travas: relatório de arquitetura de permissões de 06/10/2026 (seções 2, 4 e 5).
