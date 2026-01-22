# API Status Badges

Definições de badges de status para endpoints da API.

---

## Definições

| Badge | Significado | Uso |
|-------|-------------|-----|
| ![Stable](https://img.shields.io/badge/status-stable-green) | Endpoint estável, sem mudanças planejadas | Maioria dos endpoints |
| ![Beta](https://img.shields.io/badge/status-beta-yellow) | Pode mudar sem aviso prévio | Features novas |
| ![Deprecated](https://img.shields.io/badge/status-deprecated-red) | Será removido na próxima versão | Endpoints antigos |
| ![Internal](https://img.shields.io/badge/status-internal-gray) | Uso interno, não documentado publicamente | Admin tools |

---

## Formato de Uso

### Em Tabelas (Recomendado)

```markdown
| Método | Endpoint | Status | Descrição |
|--------|----------|--------|-----------|
| GET | `/api/v1/solicitacoes/` | ![Stable](https://img.shields.io/badge/-stable-green) | Listar |
| GET | `/api/v1/insights/` | ![Beta](https://img.shields.io/badge/-beta-yellow) | Insights |
```

### Em Headers

```markdown
### POST /api/v1/solicitacoes/ ![Stable](https://img.shields.io/badge/-stable-green)
```

---

## URLs dos Badges

Para facilitar cópia:

```markdown
![Stable](https://img.shields.io/badge/-stable-green)
![Beta](https://img.shields.io/badge/-beta-yellow)
![Deprecated](https://img.shields.io/badge/-deprecated-red)
![Internal](https://img.shields.io/badge/-internal-gray)
```

---

## Critérios para Classificação

### Stable
- Endpoint em produção há mais de 30 dias
- Contrato de API não mudou nas últimas 3 releases
- Cobertura de testes > 80%

### Beta
- Feature nova ou experimental
- Pode ter breaking changes sem deprecation period
- Feedback de usuários ainda sendo coletado

### Deprecated
- Será removido em versão futura
- Alternativa documentada disponível
- Período de deprecation: mínimo 1 release

### Internal
- Uso apenas por ferramentas internas
- Não coberto por garantias de estabilidade
- Pode mudar a qualquer momento

---

**Referência**: [shields.io](https://shields.io/)
