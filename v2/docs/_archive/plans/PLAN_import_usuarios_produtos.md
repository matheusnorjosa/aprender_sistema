# PLAN: APIs de Importação para Usuários e Produtos

**Epic**: #601
**Data**: 2026-02-05
**Status**: Em Planejamento

## Objetivo

Criar APIs de importação web para **Usuários** e **Produtos**, seguindo os padrões estabelecidos das outras 6 importações existentes (Bloqueios, Deslocamentos, Eventos, Compras, Ações, Cadastros DAT).

## Contexto

### Dados Disponíveis

| Arquivo | Registros | Campos Principais |
|---------|-----------|-------------------|
| `todososusuarios.xlsx` | 116 | Nome, CPF, Email, Cargo, Gerência |
| `Usuários.xlsx` | 157 | Status (Ativos/Inativos/Pendentes) |
| `produtos.xlsx` | 138 | Código, Nome, Projeto, Tipo |

### Modelos Target

**Usuario** (`apps/core/models/usuario.py`):
```python
class Usuario(AbstractUser):
    cpf: str (unique, 11 digits, required)
    telefone: str (optional)
    cargo: str (optional)
    # + AbstractUser: username, email, first_name, last_name, is_active
```

**Produto** (`apps/core/models/organizacao.py`):
```python
class Produto(models.Model):
    codigo: str (unique, required)
    nome: str (required)
    descricao: str (optional)
    projeto: FK[Projeto] (required)
    ativo: bool (default=True)
```

## Arquitetura

### Padrões Existentes (seguir rigorosamente)

| Componente | Padrão | Exemplo |
|------------|--------|---------|
| **View** | `views_import_*.py` com APIView | `views_import_deslocamentos.py` |
| **Service** | `*_import.py` com dry_run + idempotência | `deslocamentos_import.py` |
| **URL** | `/api/{recurso}/import/` | `/api/deslocamentos/import/` |
| **Frontend** | `ImportUploader.tsx` reutilizável | `Import*.tsx` pages |
| **Tests** | `test_import_*.py` completo | `test_import_deslocamentos.py` |

### Permissões

- **Usuarios**: `IsAuthenticated + (IsDAT | IsSuperuser)` - Apenas DAT/superuser pode criar usuários
- **Produtos**: `IsAuthenticated + IsControleOrSuper` - Controle pode gerenciar produtos

---

## Issues e Implementação

### Issue #602: Backend - Serviço de Importação de Usuários

**Arquivo**: `v2/backend/apps/core/services/usuarios_import.py`

#### Funcionalidades

1. **Idempotência por CPF** (campo único)
2. **Campos obrigatórios**: cpf, nome (first_name + last_name)
3. **Campos opcionais**: email, telefone, cargo, is_active
4. **Username**: gerado automaticamente do CPF se não fornecido
5. **Senha**: gerada aleatória (usuário deve resetar)
6. **Grupos/RBAC**: opcional via coluna "grupos" (comma-separated)

#### Mapeamento de Colunas

```python
COLUMN_ALIASES = {
    "cpf": ["cpf", "documento", "cpf_usuario"],
    "nome": ["nome", "nome_completo", "name", "full_name"],
    "email": ["email", "e-mail", "mail", "correio"],
    "telefone": ["telefone", "tel", "celular", "phone"],
    "cargo": ["cargo", "funcao", "function", "role"],
    "is_active": ["ativo", "is_active", "active", "status"],
    "grupos": ["grupos", "groups", "perfis", "profiles"],
}
```

#### Código do Serviço

```python
"""
AS v2 — Usuarios Import Service

Importa usuários de CSV/XLSX com idempotência por CPF.
Segue padrão estabelecido em deslocamentos_import.py.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pandas as pd
from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.models import Usuario


def import_usuarios_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa usuários de arquivo CSV/XLSX.

    Args:
        path: Caminho do arquivo
        dry_run: Se True, não persiste (apenas valida)

    Returns:
        Dict com stats e pendências
    """
    stats = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"cpf_invalid": 0, "nome_missing": 0, "duplicate": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "cpf_invalid": [],
        "nome_missing": [],
        "duplicates": [],
        "outros": [],
    }

    df = _load_file(path)

    with transaction.atomic():
        for idx, row in df.iterrows():
            try:
                _process_row(row, int(idx) + 2, stats, pendencias)  # +2 for Excel row
            except Exception as e:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append({"linha": int(idx) + 2, "erro": str(e)})

        if dry_run:
            transaction.set_rollback(True)

    return {
        "stats": stats,
        "pendencias": pendencias,
        "dry_run": dry_run,
        "file": path,
    }


def _load_file(path: str) -> pd.DataFrame:
    """Carrega CSV ou XLSX."""
    if path.endswith(".csv"):
        return pd.read_csv(path, dtype=str).fillna("")
    return pd.read_excel(path, dtype=str).fillna("")


def _normalize_row(row: pd.Series) -> dict[str, str]:
    """Normaliza nomes de colunas com aliases."""
    lower_map = {str(k).strip().lower(): str(v).strip() for k, v in row.items()}

    result = {}
    aliases = {
        "cpf": ["cpf", "documento", "cpf_usuario"],
        "nome": ["nome", "nome_completo", "name"],
        "email": ["email", "e-mail", "mail"],
        "telefone": ["telefone", "tel", "celular"],
        "cargo": ["cargo", "funcao", "function"],
        "is_active": ["ativo", "is_active", "active"],
        "grupos": ["grupos", "groups", "perfis"],
    }

    for field, keys in aliases.items():
        for key in keys:
            if key in lower_map and lower_map[key]:
                result[field] = lower_map[key]
                break
        else:
            result[field] = ""

    return result


def _clean_cpf(cpf: str) -> str:
    """Remove formatação do CPF."""
    return re.sub(r"[^\d]", "", cpf)


def _parse_name(nome: str) -> tuple[str, str]:
    """Divide nome em first_name e last_name."""
    parts = nome.strip().split(maxsplit=1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    return first_name, last_name


def _process_row(
    row: pd.Series,
    linha: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]]
) -> None:
    """Processa uma linha do arquivo."""
    data = _normalize_row(row)

    # Validar CPF
    cpf = _clean_cpf(data["cpf"])
    if not cpf or len(cpf) != 11 or not cpf.isdigit():
        stats["skipped"]["cpf_invalid"] += 1
        pendencias["cpf_invalid"].append({"linha": linha, "cpf": data["cpf"]})
        return

    # Validar nome
    if not data["nome"]:
        stats["skipped"]["nome_missing"] += 1
        pendencias["nome_missing"].append({"linha": linha, "cpf": cpf})
        return

    first_name, last_name = _parse_name(data["nome"])

    # Verificar existente
    existing = Usuario.objects.filter(cpf=cpf).first()

    if existing:
        # Atualizar se houver mudanças
        updated = False
        if data["telefone"] and existing.telefone != data["telefone"]:
            existing.telefone = data["telefone"]
            updated = True
        if data["cargo"] and existing.cargo != data["cargo"]:
            existing.cargo = data["cargo"]
            updated = True
        if data["email"] and existing.email != data["email"]:
            existing.email = data["email"]
            updated = True

        if updated:
            existing.save()
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        # Criar novo usuário
        username = data["email"].split("@")[0] if data["email"] else f"user_{cpf}"

        usuario = Usuario.objects.create(
            cpf=cpf,
            username=username,
            email=data["email"] or f"{cpf}@placeholder.local",
            first_name=first_name,
            last_name=last_name,
            telefone=data["telefone"],
            cargo=data["cargo"],
            is_active=data["is_active"].lower() not in ("nao", "não", "false", "0", "inativo"),
        )
        usuario.set_password(Usuario.objects.make_random_password())
        usuario.save()

        # Adicionar grupos se especificado
        if data["grupos"]:
            grupos = [g.strip() for g in data["grupos"].split(",")]
            for nome_grupo in grupos:
                grupo = Group.objects.filter(name__iexact=nome_grupo).first()
                if grupo:
                    usuario.groups.add(grupo)

        stats["created"] += 1
```

#### Testes Obrigatórios

```python
# test_import_usuarios.py
- test_import_requires_authentication
- test_import_requires_dat_permission
- test_import_dry_run_no_changes
- test_import_creates_new_usuario
- test_import_updates_existing_usuario
- test_import_idempotent_by_cpf
- test_import_invalid_cpf_skipped
- test_import_missing_nome_skipped
- test_import_header_flexibility
- test_import_assigns_groups
```

---

### Issue #603: Backend - View de Importação de Usuários

**Arquivo**: `v2/backend/apps/core/views_import_usuarios.py`

#### Código

```python
"""
AS v2 — Import Usuarios View

POST /api/usuarios/import/?dry_run=true|false
Accepts: CSV, XLSX (max 10MB)
Permission: IsDAT or IsSuperuser
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDATOrSuperuser
from apps.core.services.usuarios_import import import_usuarios_from_file

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ImportUsuariosView(APIView):
    """View para importação de usuários via CSV/XLSX."""

    permission_classes = [IsAuthenticated, IsDATOrSuperuser]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        dry_run = request.query_params.get("dry_run", "true").lower() in {"1", "true", "t", "yes", "y"}

        if "file" not in request.FILES:
            return Response({"error": "Campo 'file' obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES["file"]

        # Validar tamanho
        if uploaded_file.size and uploaded_file.size > MAX_UPLOAD_SIZE:
            return Response({"error": "Arquivo excede 10MB"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        # Validar tipo
        content_type = uploaded_file.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            return Response({"error": f"Tipo não suportado: {content_type}"}, status=status.HTTP_400_BAD_REQUEST)

        # Determinar extensão
        suffix = ".xlsx" if "spreadsheet" in content_type or "excel" in content_type else ".csv"

        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file.close()

            report = import_usuarios_from_file(path=temp_file.name, dry_run=dry_run)
            return Response(report, status=status.HTTP_200_OK)

        finally:
            if temp_file:
                Path(temp_file.name).unlink(missing_ok=True)
```

#### URL Registration

```python
# Em urls.py, adicionar:
path("usuarios/import/", ImportUsuariosView.as_view(), name="import-usuarios"),
```

---

### Issue #604: Backend - Serviço de Importação de Produtos

**Arquivo**: `v2/backend/apps/core/services/produtos_import.py`

#### Funcionalidades

1. **Idempotência por código** (campo único)
2. **Campos obrigatórios**: codigo, nome, projeto
3. **Campos opcionais**: descricao, ativo
4. **Projeto**: resolvido por nome (fuzzy) ou código

#### Mapeamento de Colunas

```python
COLUMN_ALIASES = {
    "codigo": ["codigo", "code", "cod", "sku"],
    "nome": ["nome", "name", "produto", "descricao_produto"],
    "descricao": ["descricao", "description", "obs", "observacao"],
    "projeto": ["projeto", "project", "projeto_nome"],
    "ativo": ["ativo", "active", "is_active", "status"],
}
```

#### Código do Serviço

```python
"""
AS v2 — Produtos Import Service

Importa produtos de CSV/XLSX com idempotência por código.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from django.db import transaction

from apps.core.models import Produto, Projeto
from apps.dat_ingest.services.resolvers import norm_text


def import_produtos_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """Importa produtos de arquivo CSV/XLSX."""
    stats = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"codigo_missing": 0, "nome_missing": 0, "projeto_not_found": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "codigo_missing": [],
        "nome_missing": [],
        "projeto_not_found": [],
        "outros": [],
    }

    df = _load_file(path)
    projeto_cache = _build_projeto_cache()

    with transaction.atomic():
        for idx, row in df.iterrows():
            try:
                _process_row(row, int(idx) + 2, stats, pendencias, projeto_cache)
            except Exception as e:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append({"linha": int(idx) + 2, "erro": str(e)})

        if dry_run:
            transaction.set_rollback(True)

    return {
        "stats": stats,
        "pendencias": pendencias,
        "dry_run": dry_run,
        "file": path,
    }


def _load_file(path: str) -> pd.DataFrame:
    if path.endswith(".csv"):
        return pd.read_csv(path, dtype=str).fillna("")
    return pd.read_excel(path, dtype=str).fillna("")


def _build_projeto_cache() -> dict[str, Projeto]:
    """Cria cache de projetos por nome normalizado."""
    cache: dict[str, Projeto] = {}
    for p in Projeto.objects.filter(ativo=True):
        cache[norm_text(p.nome)] = p
        if p.codigo:
            cache[norm_text(p.codigo)] = p
    return cache


def _normalize_row(row: pd.Series) -> dict[str, str]:
    lower_map = {str(k).strip().lower(): str(v).strip() for k, v in row.items()}

    result = {}
    aliases = {
        "codigo": ["codigo", "code", "cod", "sku"],
        "nome": ["nome", "name", "produto"],
        "descricao": ["descricao", "description", "obs"],
        "projeto": ["projeto", "project", "projeto_nome"],
        "ativo": ["ativo", "active", "is_active"],
    }

    for field, keys in aliases.items():
        for key in keys:
            if key in lower_map and lower_map[key]:
                result[field] = lower_map[key]
                break
        else:
            result[field] = ""

    return result


def _resolve_projeto(nome: str, cache: dict[str, Projeto]) -> Projeto | None:
    """Resolve projeto por nome ou código."""
    normalized = norm_text(nome)
    return cache.get(normalized)


def _process_row(
    row: pd.Series,
    linha: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    projeto_cache: dict[str, Projeto],
) -> None:
    data = _normalize_row(row)

    # Validar código
    if not data["codigo"]:
        stats["skipped"]["codigo_missing"] += 1
        pendencias["codigo_missing"].append({"linha": linha})
        return

    # Validar nome
    if not data["nome"]:
        stats["skipped"]["nome_missing"] += 1
        pendencias["nome_missing"].append({"linha": linha, "codigo": data["codigo"]})
        return

    # Resolver projeto
    projeto = _resolve_projeto(data["projeto"], projeto_cache)
    if not projeto:
        stats["skipped"]["projeto_not_found"] += 1
        pendencias["projeto_not_found"].append({
            "linha": linha,
            "codigo": data["codigo"],
            "projeto": data["projeto"],
        })
        return

    # Verificar existente
    existing = Produto.objects.filter(codigo=data["codigo"]).first()

    if existing:
        updated = False
        if existing.nome != data["nome"]:
            existing.nome = data["nome"]
            updated = True
        if data["descricao"] and existing.descricao != data["descricao"]:
            existing.descricao = data["descricao"]
            updated = True
        if existing.projeto_id != projeto.id:
            existing.projeto = projeto
            updated = True

        if updated:
            existing.save()
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        Produto.objects.create(
            codigo=data["codigo"],
            nome=data["nome"],
            descricao=data["descricao"],
            projeto=projeto,
            ativo=data["ativo"].lower() not in ("nao", "não", "false", "0", "inativo"),
        )
        stats["created"] += 1
```

---

### Issue #605: Backend - View de Importação de Produtos

**Arquivo**: `v2/backend/apps/core/views_import_produtos.py`

```python
"""
AS v2 — Import Produtos View

POST /api/produtos/import/?dry_run=true|false
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsControleOrSuper
from apps.core.services.produtos_import import import_produtos_from_file

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ImportProdutosView(APIView):
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        dry_run = request.query_params.get("dry_run", "true").lower() in {"1", "true", "t", "yes", "y"}

        if "file" not in request.FILES:
            return Response({"error": "Campo 'file' obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES["file"]

        if uploaded_file.size and uploaded_file.size > MAX_UPLOAD_SIZE:
            return Response({"error": "Arquivo excede 10MB"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        content_type = uploaded_file.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            return Response({"error": f"Tipo não suportado: {content_type}"}, status=status.HTTP_400_BAD_REQUEST)

        suffix = ".xlsx" if "spreadsheet" in content_type or "excel" in content_type else ".csv"

        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file.close()

            report = import_produtos_from_file(path=temp_file.name, dry_run=dry_run)
            return Response(report, status=status.HTTP_200_OK)

        finally:
            if temp_file:
                Path(temp_file.name).unlink(missing_ok=True)
```

#### URL Registration

```python
path("produtos/import/", ImportProdutosView.as_view(), name="import-produtos"),
```

---

### Issue #606: Frontend - Páginas de Importação

#### 1. API Client (`src/api/imports.ts`)

```typescript
// Adicionar aos imports existentes
export const importUsuarios = async (file: File, dryRun: boolean = true) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/usuarios/import/?dry_run=${dryRun}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const importProdutos = async (file: File, dryRun: boolean = true) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/produtos/import/?dry_run=${dryRun}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};
```

#### 2. Página ImportUsuarios (`src/pages/Importacoes/ImportUsuarios.tsx`)

```tsx
import React from 'react';
import { Card, Typography } from 'antd';
import ImportUploader from '../../components/ImportUploader';
import { importUsuarios } from '../../api/imports';

const { Title, Paragraph } = Typography;

const ImportUsuarios: React.FC = () => {
  return (
    <Card>
      <Title level={3}>Importar Usuários</Title>
      <Paragraph type="secondary">
        Importe usuários de arquivo CSV ou XLSX. Campos obrigatórios: CPF, Nome.
        Campos opcionais: Email, Telefone, Cargo, Grupos.
      </Paragraph>

      <ImportUploader
        label="Selecione o arquivo de usuários"
        onDryRun={(file) => importUsuarios(file, true)}
        onApply={(file) => importUsuarios(file, false)}
        description="Aceita CSV e XLSX até 10MB. CPF é a chave de idempotência."
      />
    </Card>
  );
};

export default ImportUsuarios;
```

#### 3. Página ImportProdutos (`src/pages/Importacoes/ImportProdutos.tsx`)

```tsx
import React from 'react';
import { Card, Typography } from 'antd';
import ImportUploader from '../../components/ImportUploader';
import { importProdutos } from '../../api/imports';

const { Title, Paragraph } = Typography;

const ImportProdutos: React.FC = () => {
  return (
    <Card>
      <Title level={3}>Importar Produtos</Title>
      <Paragraph type="secondary">
        Importe produtos de arquivo CSV ou XLSX. Campos obrigatórios: Código, Nome, Projeto.
        O projeto deve existir previamente no sistema.
      </Paragraph>

      <ImportUploader
        label="Selecione o arquivo de produtos"
        onDryRun={(file) => importProdutos(file, true)}
        onApply={(file) => importProdutos(file, false)}
        description="Aceita CSV e XLSX até 10MB. Código é a chave de idempotência."
      />
    </Card>
  );
};

export default ImportProdutos;
```

#### 4. Rotas (`src/routes/index.tsx`)

```tsx
// Adicionar lazy imports
const ImportUsuarios = lazy(() => import('../pages/Importacoes/ImportUsuarios'));
const ImportProdutos = lazy(() => import('../pages/Importacoes/ImportProdutos'));

// Adicionar rotas
{ path: '/importacoes/usuarios', element: <ImportUsuarios /> },
{ path: '/importacoes/produtos', element: <ImportProdutos /> },
```

#### 5. Menu de Navegação

Adicionar no menu de Importações:
- Usuários → `/importacoes/usuarios`
- Produtos → `/importacoes/produtos`

---

## Ordem de Execução

```
#602 (Service Usuarios)  ─┬─→ #603 (View Usuarios)  ─┐
                          │                           │
#604 (Service Produtos) ─┴─→ #605 (View Produtos) ─┴─→ #606 (Frontend)
```

**Paralelização possível**:
- Issues #602 e #604 podem ser feitas em paralelo
- Issues #603 e #605 podem ser feitas em paralelo (após services)
- Issue #606 depende de #603 e #605

---

## Verificação Final

```bash
# Backend
cd v2/backend
pyright apps/core/services/usuarios_import.py apps/core/services/produtos_import.py
pytest apps/core/tests/test_import_usuarios.py apps/core/tests/test_import_produtos.py -v

# Frontend
cd v2/frontend
npm run typecheck
npm run build
```

---

## Estimativa

| Issue | Tempo | Prioridade |
|-------|-------|------------|
| #602 Service Usuarios | 2h | Alta |
| #603 View Usuarios | 1h | Alta |
| #604 Service Produtos | 1.5h | Alta |
| #605 View Produtos | 0.5h | Alta |
| #606 Frontend | 2h | Alta |
| **Total** | **7h** | - |
