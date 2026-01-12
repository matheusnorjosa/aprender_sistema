# Plano: Disponibilidade Multi-Setor (Cenário A)

**Data**: 2026-01-09
**Status**: Planejado
**Meta**: Permitir visualização de grade mensal e bloqueios por setor (NAO_SUPER)

---

## 1. Contexto

### Situação Atual

Atualmente, a funcionalidade de disponibilidade (/disponibilidade) está restrita ao fluxo SUPER (Superintendência):

- **monthly_grid_service.py:101** - Filtro hardcoded: `solicitacao__projeto__fluxo='SUPER'`
- **views_availability_monthly.py:38** - Privileged check hardcoded: `Superintendência, Controle`
- **views/availability.py:45** - Block visibility hardcoded: `Superintendência ou superuser`

### Objetivo (Cenário A)

Permitir que coordenadores e gerentes de **outros setores** (Vidas, Fluir, ACerta, etc.) possam:

1. **Visualizar a grade mensal** de formadores do seu setor
2. **Verificar conflitos** antes de agendar eventos NAO_SUPER
3. **Visualizar bloqueios** de formadores do seu setor

**Importante**: Não inclui gerenciar bloqueios de terceiros (apenas visualização).

---

## 2. Modelo de Dados Existente

```
Usuario ─── EquipeGerencia ─── Gerencia ─── Projeto
              │                   │
              └─ papel            └─ fluxo (SUPER/NAO_SUPER)
              (FORMADOR, COORDENADOR,
               APOIO_COORDENACAO, GERENTE)
```

### Gerências e Setores

| Gerencia | Setor | Fluxo | Projetos |
|----------|-------|-------|----------|
| SUPERINTENDENCIA | Super | SUPER | CIRANDAR, LENDO E ESCREVENDO, etc. (10) |
| GERENCIA 2 | Vidas | NAO_SUPER | VIDA E CIÊNCIAS, VIDA E LINGUAGEM, VIDA E MATEMÁTICA (3) |
| GERENCIA 3 | Fluir | NAO_SUPER | FLUIR DAS EMOÇÕES, etc. (4) |
| GERENCIA 4 | ACerta | NAO_SUPER | ACERTA MATEMÁTICA, ACERTA PORTUGUÊS, etc. (6) |
| GERENCIA 5 | Brincando | NAO_SUPER | BRINCANDO E APRENDENDO (1) |
| GERENCIA 6 | Sou da Paz | NAO_SUPER | SOU DA PAZ (1) |
| GERENCIA INDIVIDUAL | Individual | NAO_SUPER | A COR DA GENTE, ED FINANCEIRA, etc. (6) |

---

## 3. Arquitetura Proposta

### 3.1 Camada de Dados

**Sem alterações em models** - usar relacionamentos existentes:
- `EquipeGerencia.gerencia` - vincula usuário a setor
- `Projeto.gerencia` - vincula projeto a setor

### 3.2 Camada de Serviço

**monthly_grid_service.py** - Parametrizar filtro:

```python
def build_monthly_grid(
    *,
    year: int,
    month: int,
    role: str,
    gerencia_id: int | None = None,  # NOVO: filtrar por gerência
    sector: str | None = None,
    q: str | None = None,
    allowed_user_ids: list[UserId] | None = None,
) -> dict[str, Any]:
    ...
    # ANTES (linha 101):
    # solicitacao__projeto__fluxo='SUPER'

    # DEPOIS:
    if gerencia_id is not None:
        participations_qs = participations_qs.filter(
            solicitacao__projeto__gerencia_id=gerencia_id
        )
    else:
        # Fallback para comportamento atual (SUPER)
        participations_qs = participations_qs.filter(
            solicitacao__projeto__fluxo='SUPER'
        )
```

### 3.3 Camada de Permissões

**permissions.py** - Nova classe para acesso por setor:

```python
class HasSectorAccess(permissions.BasePermission):
    """
    Permissão: usuário deve pertencer ao setor solicitado.

    Regras:
    - Superusers têm acesso a todos os setores
    - Controle NÃO tem acesso à grade mensal
    - Demais usuários só acessam setores em que estão vinculados via EquipeGerencia
    - Superintendência é tratada como setor normal (não privilegiado)
    """

    message = "Você não tem acesso a este setor."

    def has_permission(self, request: Request, view: APIView) -> bool:
        # Apenas superuser vê tudo
        if request.user.is_superuser:
            return True

        # Controle não tem acesso à grade mensal
        if request.user.groups.filter(name="Controle").exists():
            return False

        # Extrair gerencia_id do request
        gerencia_id = request.query_params.get("gerencia_id")
        if not gerencia_id:
            return False

        # Verificar se usuário pertence à gerência
        return EquipeGerencia.objects.filter(
            usuario=request.user,
            gerencia_id=gerencia_id
        ).exists()
```

### 3.4 Camada de API

**views_availability_monthly.py** - Adicionar parâmetro `gerencia_id`:

```python
class MonthlyAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, HasSectorAccess]

    def get(self, request: Request, ...) -> Response:
        # Extrair gerencia_id (novo parâmetro)
        gerencia_id = request.GET.get("gerencia_id")

        if gerencia_id:
            try:
                gerencia_id = int(gerencia_id)
            except ValueError:
                return Response({"error": "gerencia_id inválido"}, ...)

        # Chamar service com novo parâmetro
        data = build_monthly_grid(
            year=year,
            month=month,
            role=role,
            gerencia_id=gerencia_id,  # NOVO
            sector=sector,
            q=q,
            allowed_user_ids=allowed_user_ids
        )
```

**views/availability.py** - Expandir visibilidade de bloqueios:

```python
class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    def get_queryset(self) -> QuerySet:
        # Superusers e Superintendência veem todos
        if is_privileged_user(self.request.user):
            return AvailabilityBlock.objects.all()

        # Outros usuários veem bloqueios de membros da mesma gerência
        user_gerencia_ids = EquipeGerencia.objects.filter(
            usuario=self.request.user
        ).values_list("gerencia_id", flat=True)

        # IDs de usuários nas mesmas gerências
        same_sector_user_ids = EquipeGerencia.objects.filter(
            gerencia_id__in=user_gerencia_ids
        ).values_list("usuario_id", flat=True)

        return AvailabilityBlock.objects.filter(
            usuario_id__in=same_sector_user_ids
        )
```

---

## 4. Plano de Execução

### Fase 1: Backend Core (12h)

| PR | Arquivo | Mudança | Esforço |
|----|---------|---------|---------|
| #379 | `monthly_grid_service.py` | Adicionar parâmetro `gerencia_id`, refatorar filtro | 4h |
| #380 | `permissions.py` | Adicionar `HasSectorAccess` permission | 2h |
| #381 | `views_availability_monthly.py` | Aceitar `gerencia_id`, aplicar nova permission | 3h |
| #382 | `views/availability.py` | Expandir queryset por gerência | 3h |

### Fase 2: Testes (8h)

| PR | Escopo | Esforço |
|----|--------|---------|
| #383 | `test_monthly_grid_service.py` - Testes para `gerencia_id` | 4h |
| #384 | `test_permissions.py` - Testes para `HasSectorAccess` | 2h |
| #385 | `test_views_availability.py` - Testes E2E | 2h |

### Fase 3: Documentação (2h)

| PR | Escopo | Esforço |
|----|--------|---------|
| #386 | Atualizar `GUIDE_AVAILABILITY.md` com multi-setor | 1h |
| #386 | Documentar query params no endpoint | 1h |

**Total**: ~22h | 8 PRs

---

## 5. API Final

### GET /api/availability/monthly

Query params:
- `year` (obrigatório): int
- `month` (obrigatório): int (1-12)
- `role` (obrigatório): "FORMADOR" | "COORDENADOR"
- `gerencia_id` (opcional): int - Se omitido, assume SUPERINTENDENCIA (SUPER)
- `sector` (opcional): str - Filtro por nome do projeto
- `q` (opcional): str - Filtro por nome/email

Exemplos:
```
# Grade da Superintendência (comportamento atual)
GET /api/availability/monthly?year=2026&month=1&role=FORMADOR

# Grade do setor Vidas
GET /api/availability/monthly?year=2026&month=1&role=FORMADOR&gerencia_id=2
```

### GET /api/availability/blocks

Sem mudança na API, apenas na lógica de queryset:
- Privileged users: veem todos os bloqueios
- Outros: veem bloqueios de usuários das mesmas gerências

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Performance com muitas gerências | Baixa | Médio | Cache por gerência (já existente) |
| Vazamento de dados entre setores | Média | Alto | Permission class + testes unitários |
| Backward compatibility | Baixa | Médio | `gerencia_id=None` mantém comportamento atual |
| Cache key collision | Baixa | Baixo | Incluir `gerencia_id` na cache key |

---

## 7. Decisões de Design

### 7.1 Por que `gerencia_id` e não `fluxo`?

- `fluxo` é binário (SUPER/NAO_SUPER) - não distingue entre setores NAO_SUPER
- `gerencia_id` é granular - permite filtrar por setor específico
- Futuro: permite SUPER ser tratado como gerência normal

### 7.2 Por que não criar endpoints separados?

- Evita duplicação de código
- Mantém consistência de API
- Permite evolução gradual

### 7.3 Escopo de visualização

- **Bloqueios**: Ver todos os bloqueios de usuários do mesmo setor
- **Grid**: Ver grade de formadores/coordenadores do projeto da gerência
- **Conflitos**: Check de conflitos já é genérico (não muda)

---

## 8. Checklist de Implementação

### Backend

- [ ] Adicionar parâmetro `gerencia_id` em `build_monthly_grid()`
- [ ] Refatorar filtro `fluxo='SUPER'` para usar `gerencia_id`
- [ ] Criar permission `HasSectorAccess`
- [ ] Atualizar `MonthlyAvailabilityView` para aceitar `gerencia_id`
- [ ] Atualizar `AvailabilityBlockViewSet.get_queryset()` para filtrar por gerência
- [ ] Atualizar cache key para incluir `gerencia_id`

### Testes

- [ ] Testar grid com `gerencia_id=None` (backward compatible)
- [ ] Testar grid com `gerencia_id=2` (Vidas)
- [ ] Testar permission negada para usuário de outra gerência
- [ ] Testar superuser/Superintendência vê todas as gerências
- [ ] Testar bloqueios visíveis apenas do mesmo setor

### Documentação

- [ ] Documentar novo parâmetro `gerencia_id`
- [ ] Atualizar exemplos de API

---

## 9. Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Cobertura de testes novos | 100% |
| Performance (latência p95) | < 500ms |
| Backward compatibility | 100% (comportamento sem `gerencia_id` = atual) |

---

## 10. Próximos Passos (Fora do Escopo)

Se aprovado, futuramente pode-se implementar:

- **Cenário B**: Gerenciar bloqueios de terceiros (criar/editar bloqueios para formadores do setor)
- **Cenário C**: Aprovar solicitações NAO_SUPER (atualmente auto-aprovadas)
- **Frontend**: Selector de gerência no UI de disponibilidade

---

## Aprovação

- [ ] Aprovar plano técnico
- [ ] Criar Epic e Issues no GitHub
- [ ] Iniciar implementação

**Recomendação**: Implementar Fase 1 + Fase 2 em sprint único (~20h).
