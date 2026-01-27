# Plano: Migracao do Frontend para TypeScript

**Epic**: #477
**Status**: 🆕 Planejado
**Criado**: 2026-01-22
**Ultima Atualizacao**: 2026-01-22

---

## Objetivo

Migrar o frontend de JavaScript/JSX para TypeScript/TSX de forma gradual e segura, mantendo o sistema funcionando durante todo o processo.

---

## Metricas Atuais

| Categoria | Arquivos JS/JSX | Arquivos de Teste |
|-----------|-----------------|-------------------|
| API clients | 11 | 1 |
| Hooks | 9 | 4 |
| Components | 15 | 5 |
| Pages | 46 | 0 |
| Constants | 8 | 0 |
| Contexts | 1 | 0 |
| Services | 2 | 1 |
| Utils | 2 | 0 |
| Root (App, main) | 2 | 0 |
| **Total** | **96** | **11** |

---

## Fases e Issues

| Fase | Descricao | Issue | Status |
|------|-----------|-------|--------|
| 1 | Configuracao Inicial | [#478](https://github.com/matheusnorjosa/aprender_sistema/issues/478) | [ ] Pendente |
| 2 | Types e Interfaces | [#479](https://github.com/matheusnorjosa/aprender_sistema/issues/479) | [ ] Pendente |
| 3 | Constants | [#480](https://github.com/matheusnorjosa/aprender_sistema/issues/480) | [ ] Pendente |
| 4 | Utils e Services | [#481](https://github.com/matheusnorjosa/aprender_sistema/issues/481) | [ ] Pendente |
| 5 | API Clients | [#482](https://github.com/matheusnorjosa/aprender_sistema/issues/482) | [ ] Pendente |
| 6 | Hooks | [#483](https://github.com/matheusnorjosa/aprender_sistema/issues/483) | [ ] Pendente |
| 7 | Contexts | [#484](https://github.com/matheusnorjosa/aprender_sistema/issues/484) | [ ] Pendente |
| 8 | Components | [#485](https://github.com/matheusnorjosa/aprender_sistema/issues/485) | [ ] Pendente |
| 9 | Pages Admin/Auth | [#486](https://github.com/matheusnorjosa/aprender_sistema/issues/486) | [ ] Pendente |
| 10 | Pages DATModule | [#487](https://github.com/matheusnorjosa/aprender_sistema/issues/487) | [ ] Pendente |
| 11 | Pages Dashboards | [#488](https://github.com/matheusnorjosa/aprender_sistema/issues/488) | [ ] Pendente |
| 12 | Pages Restantes | [#489](https://github.com/matheusnorjosa/aprender_sistema/issues/489) | [ ] Pendente |
| 13 | Strict Mode | [#490](https://github.com/matheusnorjosa/aprender_sistema/issues/490) | [ ] Pendente |

---

## Estrategia de Migracao

### Principios

1. **Gradual**: Migrar arquivo por arquivo, nunca quebrar a build
2. **allowJs: true**: Permite JS e TS coexistirem durante migracao
3. **Bottom-up**: Comecar por arquivos sem dependencias (constants, utils)
4. **Testes primeiro**: Garantir que testes passam antes e depois de cada migracao
5. **PR por fase**: Cada fase = 1 PR para facilitar review

### Ordem de Dependencias

```
constants/  →  utils/  →  services/  →  api/
                                         ↓
                                      hooks/  →  contexts/
                                         ↓
                                    components/
                                         ↓
                                      pages/
```

### Convencoes de Tipos

```typescript
// Arquivos de tipos: src/types/*.ts
// Sufixo para interfaces de props: Props (ex: ButtonProps)
// Sufixo para interfaces de API: Response, Request (ex: SolicitacaoResponse)
// Usar type para unions, interface para objetos extensiveis
```

---

## Checklist de Validacao por Fase

Cada fase deve passar por:

- [ ] Lint passa (`npm run lint`)
- [ ] Build passa (`npm run build`)
- [ ] Testes passam (`npm run test`)
- [ ] Type check passa (`npx tsc --noEmit`)
- [ ] PR criado e aprovado
- [ ] CI passa (todos os checks verdes)
- [ ] Merge na main

---

## Estimativas

| Fase | Arquivos | Complexidade | Estimativa |
|------|----------|--------------|------------|
| 1. Config | 3 | Baixa | 1h |
| 2. Types | ~10 | Media | 2h |
| 3. Constants | 8 | Baixa | 1h |
| 4. Utils/Services | 4 | Baixa | 1h |
| 5. API | 11 | Media | 2h |
| 6. Hooks | 9 | Media | 2h |
| 7. Contexts | 1 | Baixa | 0.5h |
| 8. Components | 15 | Media | 3h |
| 9. Pages Admin | 7 | Media | 2h |
| 10. Pages DAT | 12 | Alta | 3h |
| 11. Pages Dash | 5 | Media | 1.5h |
| 12. Pages Rest | 22 | Alta | 4h |
| 13. Strict | - | Media | 2h |
| **Total** | **96+** | - | **~25h** |

---

## Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|-----------|
| Quebrar build durante migracao | allowJs: true, migrar arquivo por arquivo |
| Tipos incorretos de libs externas | Usar @types/* ou criar .d.ts local |
| Regressoes de funcionalidade | Rodar testes antes e depois de cada arquivo |
| Conflitos de merge | PRs pequenos, merge frequente |

---

## Dependencias Externas

| Pacote | @types necessario | Status |
|--------|-------------------|--------|
| react | @types/react | Ja instalado |
| react-dom | @types/react-dom | Ja instalado |
| antd | Tipos incluidos | OK |
| axios | Tipos incluidos | OK |
| dayjs | Tipos incluidos | OK |
| leaflet | @types/leaflet | Verificar |
| react-leaflet | @types/react-leaflet | Verificar |
| fuse.js | Tipos incluidos | OK |

---

## Referencias

- [TypeScript Handbook - Migrating from JavaScript](https://www.typescriptlang.org/docs/handbook/migrating-from-javascript.html)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Vite TypeScript Guide](https://vitejs.dev/guide/features.html#typescript)
