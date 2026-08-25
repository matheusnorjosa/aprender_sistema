"""
Importer dedicado do export-contract (skeleton seguro).

Princípios de segurança:
- **dry-run por padrão** (`apply=False`): só classifica, nunca escreve.
- **`apply=True` exige allowlist** (`allow=(...)`); sem allowlist → `apply_blocked`, nada escrito.
- **modo `create-only`**: na escrita, só insere `would_create`; nunca faz update.
- **never-overwrite de campos protegidos**: se um registro existe e diverge num campo protegido
  (`Solicitacao.status`, `Formacao.data_formacao`, `Acompanhamento.data_acompanhamento/realizado`),
  classifica como `protected_diff` e deixa para decisão humana (nunca sobrescreve).

Primeira fatia implementada (master, baixo risco): `dat_area`, `municipio`, `projeto_geral`.
Demais entidades → `not_implemented` (contagem reportada, sem processamento).

NÃO importa dados reais por padrão. Sem PII no relatório (só counts/nomes de entidade).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.constants import ALLOWED_USER_GROUPS
from apps.core.imports.normalization import normalize_cpf_digits
from apps.core.models import (
    DATAcao,
    DATArea,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    DATRegistro,
    Gerencia,
    Municipio,
    PlanoFormacoes,
    Produto,
    Projeto,
    ProjetoGeral,
    TipoEvento,
    Usuario,
)
from apps.core.services.dat_codigos import recompute_all
from apps.core.services.equipe_gerencia_import import PAPEL_MAPPING
from apps.core.services.export_contract_projeto_resolver import build_projeto_index, resolve_projeto_export
from apps.core.validators import CPF_ABSENT, CPF_INVALID, classify_cpf, is_valid_cpf

# Campos protegidos por entidade — NUNCA sobrescrever em update (decisão humana).
PROTECTED_FIELDS: dict[str, set[str]] = {
    "solicitacao": {"status"},
    "formacao": {"data_formacao"},
    "acompanhamento": {"data_acompanhamento", "realizado"},
}

# Ordem canônica (master → operacional). IMPLEMENTED = fatia atual.
ENTITY_ORDER = [
    "municipio",
    "projeto_geral",
    "projeto",
    "produto",
    "colecao",
    "usuario",
    "gerencia",
    "equipe_gerencia",
    "tipo_evento",
    "dat_area",
    "dat_coordenador",
    "solicitacao",
    "participation",
    "availability_block",
    "deslocamento",
    "dat_registro",
    "dat_cadastro",
    "dat_acao",
    "dat_compra",
    "plano_formacao",
    "formacao",
    "acompanhamento",
    "prova",
]
IMPLEMENTED = {
    "dat_area",
    "municipio",
    "projeto_geral",
    "projeto",
    "produto",
    "usuario",
    "tipo_evento",
    "gerencia",
    "dat_coordenador",
    "dat_acao",
    "plano_formacao",
    "dat_registro",
    "dat_cadastro",
    "dat_compra",
}
# Escrivíveis = subconjunto de IMPLEMENTED com apply REAL. `produto`/`gerencia` classificam mas não
# têm handler (silent-0) → `--allow-entity` neles é erro (CR-03), não "applied=0" calado.
APPLIABLE = IMPLEMENTED - {"produto", "gerencia"}

# Papel canonico (PAPEL_MAPPING) -> nome do Django Group (FUNCAO_GROUPS). Fonte do papel no
# import de usuario: equipe_gerencia.papel (primaria, por CPF) -> usuario.cargo (fallback).
# NUNCA default Coordenador — conceder poder de criar solicitacao exige papel explicito.
_PAPEL_TO_GROUP: dict[str, str] = {
    "GERENTE": "Gerente",
    "COORDENADOR": "Coordenador",
    "APOIO": "Apoio de Coordenação",
    "FORMADOR": "Formador",
}


def _resolve_papel(raw: str | None) -> str:
    """Nome de papel bruto -> canonico (GERENTE/COORDENADOR/APOIO/FORMADOR) via PAPEL_MAPPING."""
    s = (raw or "").strip()
    return PAPEL_MAPPING.get(s) or PAPEL_MAPPING.get(s.upper()) or ""


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).upper()


def _cmp(v: Any) -> str:
    """Forma comparável canônica (bool/None/str) para detectar diferença de campo."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v).strip().casefold()


def _to_bool(v: Any) -> bool:
    return str(v).strip().casefold() in {"true", "1", "yes", "sim", "t"}


def _parse_iso_date(v: Any) -> date | None:
    """Parseia data ISO YYYY-MM-DD do export-contract (v3). Vazio/inválido → None."""
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_int(v: Any) -> int | None:
    """Parseia inteiro de string (o v3 emite quantidades como string). Vazio/inválido → None."""
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_decimal(v: Any) -> Decimal:
    """Parseia decimal (carga horária). Vazio/inválido → 0.00."""
    s = str(v or "").strip()
    if not s:
        return Decimal("0.00")
    try:
        return Decimal(s)
    except (ArithmeticError, ValueError):
        return Decimal("0.00")


def _parse_json_list(v: Any) -> list[Any]:
    """Parseia array JSON de datas (ex.: '[\"2026-03-27\"]'). Vazio/inválido → []."""
    s = str(v or "").strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
    except (ValueError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


# projeto_geral: config de cálculo do contrato v5 → choices do Django.
_TIPO_CALCULO_MAP = {
    "aluno_div_divisor": "por_aluno",
    "professor_x_multiplicador": "por_professor",
}
# Nomes de projeto_geral ambíguos (aliases de outro PG com regra DIFERENTE): NUNCA criar
# via import — decisão humana (CONTRATO-v4 §2). Criar com o default por_professor daria
# nr_codigos errado onde a planilha usa aluno÷20 (ex.: ECS, ED FINANCEIRA).
_AMBIGUOUS_PG_NAMES = {_norm("ESCREVER COMUNICAR E SER"), _norm("EDUCAÇÃO FINANCEIRA")}
# projeto.fluxo autoritativo (SUPER exige aprovação — PA-01). Vazio/inválido → would_reject
# (default NAO_SUPER faria um projeto SUPER auto-aprovar solicitações).
_PROJETO_FLUXOS = {"SUPER", "NAO_SUPER"}


def _pg_calc_fields(r: dict[str, str]) -> dict[str, Any]:
    """Config de cálculo do projeto_geral (v5 → Django); ausentes usam o default do model."""
    fields: dict[str, Any] = {}
    tc = _TIPO_CALCULO_MAP.get((r.get("tipo_calculo_codigos") or "").strip())
    if tc:
        fields["tipo_calculo_codigos"] = tc
    divisor = _parse_int(r.get("divisor_aluno"))
    if divisor:
        fields["divisor_aluno"] = divisor
    mult = (r.get("multiplicador_professor") or "").strip()
    if mult:
        try:
            fields["multiplicador_professor"] = Decimal(mult)
        except (ArithmeticError, ValueError):
            pass
    return fields


# dat_cadastro: etapaN da planilha → (campo status, campo data) do DATCadastro, por plataforma.
# FORMAR tem 4 etapas; AVALIAR tem 3 (a etapa4 do CSV sai como 'na' e não tem campo no model).
_CAD_ETAPAS: dict[str, list[tuple[str, str, str]]] = {
    "FORMAR": [
        ("etapa1", "status_criacao_curso", "data_criacao_curso"),
        ("etapa2", "status_chaves", "data_chaves"),
        ("etapa3", "status_instrucoes", "data_instrucoes"),
        ("etapa4", "status_envio", "data_envio"),
    ],
    "AVALIAR": [
        ("etapa1", "status_recebidos", "data_recebidos"),
        ("etapa2", "status_validados", "data_validados"),
        ("etapa3", "status_importados", "data_importados"),
    ],
}


def _dat_acao_ano(r: dict[str, str]) -> int | None:
    """Ano-cohort da ação DAT (decisão B) = ano da data da reunião (âncora do ciclo), com fallback
    reuniao → entrega → carta → contato. CSV usa `contato_inicial` (= data_contato). None = pendente."""
    for col in ("data_reuniao", "data_entrega", "data_carta", "contato_inicial"):
        d = _parse_iso_date(r.get(col))
        if d:
            return d.year
    return None


def _dat_cadastro_ano(r: dict[str, str]) -> int | None:
    """Ano-cohort do cadastro = ano da 1ª etapa com data (início do ciclo FORMAR/AVALIAR), fallback
    pelas etapas seguintes. Nenhuma data → None (pendente)."""
    for col in ("etapa1_data", "etapa2_data", "etapa3_data", "etapa4_data"):
        d = _parse_iso_date(r.get(col))
        if d:
            return d.year
    return None


def diff_and_classify(
    existing: dict[str, Any] | None, export: dict[str, Any], protected: set[str]
) -> tuple[str, list[str]]:
    """
    Classifica um registro comparando o estado existente (ou None) com o do export.

    Returns (status, campos):
      - would_create   : não existe.
      - would_skip_same: existe e idêntico nos campos comparados.
      - protected_diff : existe e diverge em campo protegido (NUNCA sobrescrever).
      - would_update   : existe e diverge só em campos não-protegidos.
    """
    if existing is None:
        return "would_create", []
    diffs = [k for k in export if _cmp(existing.get(k)) != _cmp(export.get(k))]
    if not diffs:
        return "would_skip_same", []
    prot = sorted(k for k in diffs if k in protected)
    if prot:
        return "protected_diff", prot
    return "would_update", sorted(diffs)


class ExportContractImporter:
    """Importer dry-run-first do export-contract. Veja docstring do módulo."""

    def __init__(
        self,
        path: str,
        *,
        mode: str = "create-only",
        apply: bool = False,
        allow: tuple[str, ...] = (),
        actor: Usuario | None = None,
    ) -> None:
        self.path = path
        self.mode = mode
        self.apply = apply
        self.allow = tuple(allow)
        self.actor = actor  # created_by no apply de entidades com auditoria (dat_cadastro/dat_registro)
        self._pidx = None

    # ── resolver de Projeto (delegação ao módulo mergeado na #1372) ──
    def resolve_projeto(self, raw_name: str) -> int | None:
        if self._pidx is None:
            self._pidx = build_projeto_index()
        res = resolve_projeto_export(raw_name, index=self._pidx)
        return res.projeto.id if res.status == "matched" and res.projeto else None

    def _load(self, name: str) -> list[dict[str, str]]:
        fp = os.path.join(self.path, f"{name}.csv")
        if not os.path.exists(fp):
            return []
        with open(fp, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _read_manifest(self) -> dict[str, Any]:
        fp = os.path.join(self.path, "manifest.json")
        if not os.path.exists(fp):
            return {}
        with open(fp, encoding="utf-8") as f:
            return json.load(f)

    def _municipio_index(self) -> dict[tuple[str, str], int]:
        """Índice (norm(nome), uf.upper()) → municipio_id, para resolver FK por nome+uf."""
        return {(_norm(n), (u or "").upper()): mid for mid, n, u in Municipio.objects.values_list("id", "nome", "uf")}

    def _projeto_geral_index(self) -> dict[str, int]:
        """Índice norm(nome) → projeto_geral_id (ProjetoGeral.nome é unique)."""
        return {_norm(n): pid for pid, n in ProjetoGeral.objects.values_list("id", "nome")}

    # ── handlers da fatia implementada ──
    def _classify_master(self, name: str) -> dict[str, Any]:
        rows = self._load(name)
        tally: dict[str, Any] = {
            k: 0 for k in ("would_create", "would_update", "would_skip_same", "protected_diff", "would_reject")
        }
        protected = PROTECTED_FIELDS.get(name, set())

        if name == "dat_area":
            # DATArea não tem campo comparável vindo do export (export traz só nome/descricao;
            # 'descricao' não existe no model). → existência decide create vs skip.
            idx = {_norm(n) for n in DATArea.objects.values_list("nome", flat=True)}
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                existing = {} if _norm(nome) in idx else None
                st, _ = diff_and_classify(existing, {}, protected)
                tally[st] += 1

        elif name == "municipio":
            idx = {
                (_norm(n), (u or "").upper()): {"ativo": a}
                for n, u, a in Municipio.objects.values_list("nome", "uf", "ativo")
            }
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                key = (_norm(nome), (r.get("uf") or "").upper())
                st, _ = diff_and_classify(idx.get(key), {"ativo": _to_bool(r.get("ativo"))}, protected)
                tally[st] += 1

        elif name == "projeto_geral":
            idx = {_norm(n): {"usa_avaliar": a} for n, a in ProjetoGeral.objects.values_list("nome", "usa_avaliar")}
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                if _norm(nome) not in idx and _norm(nome) in _AMBIGUOUS_PG_NAMES:
                    tally["would_reject"] += 1  # alias ambíguo → decisão humana, não criar
                    continue
                st, _ = diff_and_classify(
                    idx.get(_norm(nome)), {"usa_avaliar": _to_bool(r.get("usa_avaliar"))}, protected
                )
                tally[st] += 1

        elif name == "projeto":
            # Master do catálogo de variantes (Onda A). Matching via resolver #1372 (canon-key,
            # detecta ambiguidade); NUNCA nome__iexact (o resolver canoniza & vs E / hífen /
            # prefixo PROJETO). Criar exige PG resolvível (coluna projeto_geral) + fluxo
            # autoritativo (PA-01) → PG/fluxo ausente = would_reject rotulado, nunca órfã NULL.
            if self._pidx is None:
                self._pidx = build_projeto_index()
            pg_idx = self._projeto_geral_index()
            reasons = {"nome_vazio": 0, "ambiguous": 0, "pg_desconhecido": 0, "fluxo_ausente": 0}
            for r in rows:
                nome = (r.get("projeto") or r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    reasons["nome_vazio"] += 1
                    continue
                res = resolve_projeto_export(nome, index=self._pidx)
                if res.status == "matched":
                    tally["would_skip_same"] += 1  # já existe (canon-key) → create-only não toca
                    continue
                if res.status == "ambiguous":
                    tally["would_reject"] += 1
                    reasons["ambiguous"] += 1
                    continue
                # unmatched → candidato a create; exige PG resolvível + fluxo válido.
                # projeto_geral vazio (base MATCH_CANONICO) → deriva do próprio nome (PG homônimo).
                pg_name = (r.get("projeto_geral") or "").strip() or nome
                if pg_idx.get(_norm(pg_name)) is None:
                    tally["would_reject"] += 1
                    reasons["pg_desconhecido"] += 1
                    continue
                if (r.get("fluxo") or "").strip().upper() not in _PROJETO_FLUXOS:
                    tally["would_reject"] += 1
                    reasons["fluxo_ausente"] += 1
                    continue
                tally["would_create"] += 1
            tally["reject_reasons"] = reasons

        elif name == "produto":
            # NK = codigo (unique). Compara nome (não-protegido).
            idx = {
                (c or "").strip().upper(): {"nome": n or ""} for c, n in Produto.objects.values_list("codigo", "nome")
            }
            for r in rows:
                codigo = (r.get("codigo") or "").strip()
                if not codigo:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify(idx.get(codigo.upper()), {"nome": r.get("nome") or ""}, protected)
                tally[st] += 1

        elif name == "usuario":
            # NK = CPF válido (mod-11), fallback email para dedup. CPF estruturalmente
            # inválido ou placeholder NÃO é NK: rejeita com motivo explícito (não infla
            # would_create). Os três skips ficam distinguíveis em `reject_reasons`:
            #   sem_nk       -> sem CPF e sem email (nada para identificar);
            #   cpf_invalido -> tem CPF, não-placeholder, mas DV/comprimento inválido;
            #   sem_cpf      -> tem email mas CPF ausente/placeholder (username=cpf exige CPF).
            # ("já existe" já aparece como would_skip_same.) PII: só conta, nunca imprime.
            cpfs = {
                normalize_cpf_digits(c)
                for c in Usuario.objects.values_list("cpf", flat=True)
                if normalize_cpf_digits(c)
            }
            emails = {(e or "").lower() for e in Usuario.objects.values_list("email", flat=True) if e}
            reasons = {"sem_nk": 0, "cpf_invalido": 0, "sem_cpf": 0}
            for r in rows:
                cpf = normalize_cpf_digits(r.get("cpf") or "")
                email = (r.get("email") or "").lower().strip()
                cpf_status = classify_cpf(r.get("cpf") or "")
                if cpf_status == CPF_INVALID:
                    tally["would_reject"] += 1
                    reasons["cpf_invalido"] += 1
                    continue
                if cpf_status == CPF_ABSENT:
                    tally["would_reject"] += 1
                    reasons["sem_cpf" if email else "sem_nk"] += 1
                    continue
                existe = (cpf in cpfs) or (email in emails)
                # sem comparação de campo (evita PII); existência decide skip vs create.
                st, _ = diff_and_classify({} if existe else None, {}, protected)
                tally[st] += 1
            tally["reject_reasons"] = reasons

        elif name == "tipo_evento":
            idx = {_norm(n): {"cor": (c or "")} for n, c in TipoEvento.objects.values_list("nome", "cor")}
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify(idx.get(_norm(nome)), {"cor": r.get("cor") or ""}, protected)
                tally[st] += 1

        elif name == "gerencia":
            # Export `nome` é o SETOR ("Vidas"); casa DB.nome_setor (não DB.nome="GERENCIA N").
            # Create é complexo (falta o `nome` canônico) → classifica, mas apply de create não suportado.
            idx = {_norm(s) for s in Gerencia.objects.values_list("nome_setor", flat=True)}
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome or nome == "-":
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if _norm(nome) in idx else None, {}, protected)
                tally[st] += 1

        elif name == "dat_coordenador":
            # Existence-based UNION (cpf ∪ email/alt ∪ norm(nome)) — ESPELHA a NK do apply, senão o
            # dry-run diverge do apply e fura o gate "dry-run verde". PII: coordenador é pessoa → o
            # `usuario_cpf` só entra na contagem de existência, nunca no relatório.
            emails = {(e or "").lower() for e in DATCoordenador.objects.values_list("email", flat=True) if e} | {
                (e or "").lower() for e in DATCoordenador.objects.values_list("email_alternativo", flat=True) if e
            }
            nomes = {_norm(n) for n in DATCoordenador.objects.values_list("nome", flat=True) if n}
            cpfs = {c for c in DATCoordenador.objects.values_list("cpf", flat=True) if c}
            for r in rows:
                val = (r.get("usuario") or "").strip()
                if not val:
                    tally["would_reject"] += 1
                    continue
                cpf_raw = r.get("usuario_cpf") or r.get("cpf") or ""
                cpf = normalize_cpf_digits(cpf_raw) if is_valid_cpf(cpf_raw) else None
                existe = (
                    (cpf is not None and cpf in cpfs) or ("@" in val and val.lower() in emails) or (_norm(val) in nomes)
                )
                st, _ = diff_and_classify({} if existe else None, {}, protected)
                tally[st] += 1

        elif name == "plano_formacao":
            # NK = (municipio_id, projeto_id, ano); `ano` DECLARADO do workbook (coluna `ano`, nullable=pendente).
            # `sem_plano` (TOTAL 0 + sem data) = linha reservada → reject VISÍVEL (não é plano; mantém a
            # reconciliação, não some calado). FK não-resolvido → would_reject. Não lê coordenador (PII).
            mun_idx = self._municipio_index()
            existing = set(PlanoFormacoes.objects.values_list("municipio_id", "projeto_id", "ano"))
            for r in rows:
                if _to_bool(r.get("sem_plano")):
                    tally["would_reject"] += 1
                    continue
                mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
                proj_id = self.resolve_projeto(r.get("projeto") or "")
                if mun_id is None or proj_id is None:
                    tally["would_reject"] += 1
                    continue
                nk = (mun_id, proj_id, _parse_int(r.get("ano")))
                st, _ = diff_and_classify({} if nk in existing else None, {}, protected)
                tally[st] += 1

        elif name == "dat_acao":
            # NK = (municipio_id, projeto_id, ano) — decisão B (anual). ano = cohort derivado da data
            # da reunião (fallback entrega→carta→contato; None = pendente). Existence-based (não lê coordenador).
            mun_idx = self._municipio_index()
            existing = set(DATAcao.objects.values_list("municipio_id", "projeto_id", "ano"))
            for r in rows:
                mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
                proj_id = self.resolve_projeto(r.get("projeto") or "")
                if mun_id is None or proj_id is None:
                    tally["would_reject"] += 1
                    continue
                nk = (mun_id, proj_id, _dat_acao_ano(r))
                st, _ = diff_and_classify({} if nk in existing else None, {}, protected)
                tally[st] += 1

        elif name == "dat_registro":
            # NK = (municipio_id, projeto_geral_id, projeto_id). Município por (norm(nome), uf);
            # projeto_geral por norm(nome); projeto via resolver (#1372). FK não-resolvida → would_reject.
            # Existence-based (não compara campos operacionais; status/nr_codigos ficam para o apply).
            mun_idx = self._municipio_index()
            pg_idx = self._projeto_geral_index()
            existing = set(DATRegistro.objects.values_list("municipio_id", "projeto_geral_id", "projeto_id"))
            for r in rows:
                mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
                pg_id = pg_idx.get(_norm(r.get("projeto_geral") or ""))
                proj_id = self.resolve_projeto(r.get("projeto") or "")
                if mun_id is None or pg_id is None or proj_id is None:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if (mun_id, pg_id, proj_id) in existing else None, {}, protected)
                tally[st] += 1

        elif name == "dat_cadastro":
            # NK = (municipio_id, projeto_geral_id, plataforma). plataforma faz parte da chave
            # (FORMAR|AVALIAR); valor fora do domínio → would_reject. Existence-based.
            mun_idx = self._municipio_index()
            pg_idx = self._projeto_geral_index()
            existing = set(DATCadastro.objects.values_list("municipio_id", "projeto_geral_id", "plataforma", "ano"))
            for r in rows:
                mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
                pg_id = pg_idx.get(_norm(r.get("projeto_geral") or ""))
                plataforma = (r.get("plataforma") or "").strip().upper()
                if mun_id is None or pg_id is None or plataforma not in ("FORMAR", "AVALIAR"):
                    tally["would_reject"] += 1
                    continue
                nk = (mun_id, pg_id, plataforma, _dat_cadastro_ano(r))
                st, _ = diff_and_classify({} if nk in existing else None, {}, protected)
                tally[st] += 1

        elif name == "dat_compra":
            # NK existence-based por tupla (idioma dos handlers DAT). Município por (norm, uf);
            # Projeto via resolver (#1372). FK não-resolvida → would_reject; ano_uso vazio
            # (NÃO_CLASSIFICADO) grava com ano_uso=NULL (pendente de ano — decisão A).
            mun_idx = self._municipio_index()
            existing = set(
                DATCompra.objects.values_list(
                    "municipio_id", "projeto_id", "descricao_produto", "tipo", "quantidade", "ano_uso", "data_compra"
                )
            )
            for r in rows:
                mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
                proj_id = self.resolve_projeto(r.get("projeto") or "")
                nk = self._dat_compra_nk(r, mun_id, proj_id)
                if mun_id is None or proj_id is None:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if nk in existing else None, {}, protected)
                tally[st] += 1

        tally["export_rows"] = len(rows)
        return tally

    @staticmethod
    def _dat_compra_nk(r: dict[str, str], mun_id: int | None, proj_id: int | None) -> tuple[Any, ...]:
        """NK existence-based da compra: (mun, proj, descricao, tipo, quantidade, ano_uso, data_compra).

        `data_compra` faz parte da NK (alinhado ao dedupe_key do contrato): duas compras iguais em
        tudo menos a data (ex.: mesmo kit de professor comprado em 15/05 e 25/05) sao DISTINTAS —
        sem a data elas colidiam e a 2a era descartada, causando under-count de nr_codigos.
        """
        return (
            mun_id,
            proj_id,
            (r.get("descricao_produto") or "").strip(),
            (r.get("tipo") or "").strip() or None,
            _parse_int(r.get("quantidade")),
            # Contrato v12 renomeou `ano_uso` -> `ano_uso_colecao` (ano de USO da coleção,
            # distinto de `ano_compra`). Prefere o nome novo; cai no antigo p/ contratos <=v11.
            _parse_int(r.get("ano_uso_colecao") or r.get("ano_uso")),
            _parse_iso_date(r.get("data_compra")),
        )

    def run(self) -> dict[str, Any]:
        manifest = self._read_manifest()
        apply_blocked = bool(self.apply) and not self.allow

        por_entidade: dict[str, Any] = {}
        for name in ENTITY_ORDER:
            fp = os.path.join(self.path, f"{name}.csv")
            if not os.path.exists(fp):
                continue
            if name in IMPLEMENTED:
                por_entidade[name] = self._classify_master(name)
            else:
                por_entidade[name] = {"status": "not_implemented", "export_rows": len(self._load(name))}

        # ── escrita (create-only) — só se apply + allowlist; NÃO exercida no skeleton ──
        applied: dict[str, int] = {}
        if self.apply and self.allow and self.mode == "create-only":
            applied = self._apply_create_only()

        return {
            "phase": "EXPORT_CONTRACT_IMPORTER",
            "mode": self.mode,
            "apply": self.apply,
            "apply_blocked": apply_blocked,
            "allow": list(self.allow),
            "manifest": manifest,
            "por_entidade": por_entidade,
            "applied": applied,
            "protected_fields": {k: sorted(v) for k, v in PROTECTED_FIELDS.items()},
        }

    def _apply_create_only(self) -> dict[str, int]:
        """Cria SOMENTE would_create das entidades em allow (create-only). Transacional."""
        applied: dict[str, int] = {}
        with transaction.atomic():
            # Ordena por ENTITY_ORDER (master → operacional): o apply itera `self.allow`, que preserva a
            # ordem de CLI — sem isto, `--allow-entity plano_formacao dat_coordenador` resolveria planos
            # ANTES de criar coordenadores (índice vazio → coordenador_id NULL), sem reparo (create-only).
            for name in sorted(
                self.allow, key=lambda n: ENTITY_ORDER.index(n) if n in ENTITY_ORDER else len(ENTITY_ORDER)
            ):
                if name not in IMPLEMENTED:
                    continue
                if name == "usuario":
                    # NK = CPF (nao `nome`); atribui Group -> handler dedicado.
                    applied[name] = self._apply_usuario(self._load(name))
                    continue
                if name == "dat_cadastro":
                    applied[name] = self._apply_dat_cadastro(self._load(name))
                    continue
                if name == "dat_registro":
                    applied[name] = self._apply_dat_registro(self._load(name))
                    continue
                if name == "dat_compra":
                    applied[name] = self._apply_dat_compra(self._load(name))
                    continue
                if name == "dat_coordenador":
                    # Handler dedicado (fecha silent-gap M18-09: CSV usa `usuario`, não `nome` → o loop
                    # genérico gravaria 0). Cria com CPF do master (`usuario_cpf`).
                    applied[name] = self._apply_dat_coordenador(self._load(name))
                    continue
                if name == "projeto":
                    # Handler dedicado (resolver + PG + fluxo); NÃO o loop genérico (nome__iexact).
                    applied[name] = self._apply_projeto(self._load(name))
                    continue
                if name == "dat_acao":
                    # Handler dedicado (NK com ano; CSV sem coluna `nome` → o loop genérico gravaria 0).
                    applied[name] = self._apply_dat_acao(self._load(name))
                    continue
                if name == "plano_formacao":
                    # Handler dedicado (NK com ano; CSV sem coluna `nome` → o loop genérico gravaria 0 = silent-gap).
                    applied[name] = self._apply_plano_formacao(self._load(name))
                    continue
                created = 0
                for r in self._load(name):
                    nome = (r.get("nome") or "").strip()
                    if not nome:
                        continue
                    if name == "dat_area" and not DATArea.objects.filter(nome__iexact=nome).exists():
                        DATArea.objects.create(nome=nome)
                        created += 1
                    elif name == "municipio":
                        uf = (r.get("uf") or "").upper()
                        if not Municipio.objects.filter(nome__iexact=nome, uf=uf).exists():
                            Municipio.objects.create(nome=nome, uf=uf, ativo=_to_bool(r.get("ativo")))
                            created += 1
                    elif name == "projeto_geral" and not ProjetoGeral.objects.filter(nome__iexact=nome).exists():
                        if _norm(nome) in _AMBIGUOUS_PG_NAMES:
                            continue  # alias ambíguo (regra divergente) → decisão humana, não criar
                        ProjetoGeral.objects.create(
                            nome=nome, usa_avaliar=_to_bool(r.get("usa_avaliar")), **_pg_calc_fields(r)
                        )
                        created += 1
                    elif name == "tipo_evento" and not TipoEvento.objects.filter(nome__iexact=nome).exists():
                        TipoEvento.objects.create(
                            nome=nome,
                            descricao=(r.get("descricao") or ""),
                            cor=(r.get("cor") or ""),
                        )
                        created += 1
                applied[name] = created
            if {"dat_compra", "dat_registro"} & set(self.allow):
                # nr_codigos vem das compras: recomputa após aplicar (ordem-independente).
                recompute_all()
        return applied

    def _require_actor(self, entity: str) -> Usuario:
        if self.actor is None:
            raise ValueError(f"apply de {entity} exige um ator (created_by): rode com --as-user <cpf>.")
        return self.actor

    def _apply_dat_cadastro(self, rows: list[dict[str, str]]) -> int:
        """Create-only de DATCadastro. NK (municipio, projeto_geral, plataforma).
        Status/data já chegam normalizados (enum/ISO) do export-contract v3."""
        actor = self._require_actor("dat_cadastro")
        mun_idx = self._municipio_index()
        pg_idx = self._projeto_geral_index()
        created = 0
        for r in rows:
            mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
            pg_id = pg_idx.get(_norm(r.get("projeto_geral") or ""))
            plataforma = (r.get("plataforma") or "").strip().upper()
            if mun_id is None or pg_id is None or plataforma not in _CAD_ETAPAS:
                continue
            ano = _dat_cadastro_ano(r)
            if DATCadastro.objects.filter(
                municipio_id=mun_id, projeto_geral_id=pg_id, plataforma=plataforma, ano=ano
            ).exists():
                continue
            campos: dict[str, Any] = {}
            for prefix, status_field, data_field in _CAD_ETAPAS[plataforma]:
                campos[status_field] = (r.get(f"{prefix}_status") or "pendente").strip() or "pendente"
                campos[data_field] = _parse_iso_date(r.get(f"{prefix}_data"))
            DATCadastro.objects.create(
                municipio_id=mun_id,
                projeto_geral_id=pg_id,
                plataforma=plataforma,
                ano=ano,
                created_by=actor,
                **campos,
            )
            created += 1
        return created

    def _apply_dat_acao(self, rows: list[dict[str, str]]) -> int:
        """Create-only de DATAcao. NK (municipio, projeto, ano); ano = cohort anual derivado da data
        da reunião (fallback entrega→carta→contato). CSV `contato_inicial` = data_contato; o status de
        cada etapa é derivado da presença da data (tem data → concluido, senão pendente)."""
        actor = self._require_actor("dat_acao")
        mun_idx = self._municipio_index()
        created = 0
        for r in rows:
            mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
            proj_id = self.resolve_projeto(r.get("projeto") or "")
            if mun_id is None or proj_id is None:
                continue  # FK não-resolvida (municipio/projeto)
            ano = _dat_acao_ano(r)
            if DATAcao.objects.filter(municipio_id=mun_id, projeto_id=proj_id, ano=ano).exists():
                continue
            dc = _parse_iso_date(r.get("data_carta"))
            dco = _parse_iso_date(r.get("contato_inicial"))  # CSV `contato_inicial` → model data_contato
            dr = _parse_iso_date(r.get("data_reuniao"))
            de = _parse_iso_date(r.get("data_entrega"))
            DATAcao.objects.create(
                municipio_id=mun_id,
                projeto_id=proj_id,
                ano=ano,
                created_by=actor,
                data_carta=dc,
                status_carta="concluido" if dc else "pendente",
                data_contato=dco,
                status_contato="concluido" if dco else "pendente",
                data_reuniao=dr,
                status_reuniao="concluido" if dr else "pendente",
                data_entrega=de,
                status_entrega="concluido" if de else "pendente",
                observacao_carta=(r.get("observacao") or "")[:500],
            )
            created += 1
        return created

    def _usuario_cpf_index(self) -> dict[str, int]:
        """cpf(11 díg) → Usuario.id. O coordenador do plano é a PESSOA que coordenou (#1849), e
        `Usuario.cpf` é unique no banco → chave inequívoca. Guard falsy OBRIGATÓRIO: só `len==11` (senão
        um cpf vazio/legado mapearia `""→id` e prenderia toda linha de CPF vazio na pessoa errada)."""
        idx: dict[str, int] = {}
        for uid, cpf in Usuario.objects.values_list("id", "cpf"):
            digits = normalize_cpf_digits(cpf)
            if len(digits) == 11:
                idx[digits] = uid
        return idx

    def _apply_dat_coordenador(self, rows: list[dict[str, str]]) -> int:
        """Create-only de DATCoordenador (fecha o silent-gap M18-09). Master v14 =
        `usuario`(NOME, sem email), `usuario_cpf`(raw), `area`. NK existence-based **UNION**
        (cpf OU email OU norm(nome)) — priority-first (cpf) duplicaria a pessoa cuja linha DB
        nasceu no CRUD sem cpf. `cpf` só se `is_valid_cpf`; linha sem nome é rejeitada (create-only
        não conserta nome vazio). Índices atualizados in-memory p/ dedupe intra-CSV."""
        actor = self._require_actor("dat_coordenador")
        existing_cpfs = {c for c in DATCoordenador.objects.values_list("cpf", flat=True) if c}
        existing_names = {_norm(n) for n in DATCoordenador.objects.values_list("nome", flat=True) if n}
        existing_emails = {(e or "").lower() for e in DATCoordenador.objects.values_list("email", flat=True) if e} | {
            (e or "").lower() for e in DATCoordenador.objects.values_list("email_alternativo", flat=True) if e
        }
        created = 0
        for r in rows:
            usuario = (r.get("usuario") or "").strip()
            if not usuario:
                continue  # sem nome → não cria (row inutilizável sob create-only)
            cpf_raw = r.get("usuario_cpf") or r.get("cpf") or ""
            cpf = normalize_cpf_digits(cpf_raw) if is_valid_cpf(cpf_raw) else None
            is_email = "@" in usuario
            exists = (
                (cpf is not None and cpf in existing_cpfs)
                or (is_email and usuario.lower() in existing_emails)
                or (_norm(usuario) in existing_names)
            )
            if exists:
                continue
            DATCoordenador.objects.create(
                nome=usuario[:200],
                email=(usuario.lower()[:254] if is_email else ""),
                area=(r.get("area") or "").strip()[:100],
                cpf=cpf,
                created_by=actor,
            )
            if cpf is not None:
                existing_cpfs.add(cpf)
            existing_names.add(_norm(usuario))
            if is_email:
                existing_emails.add(usuario.lower())
            created += 1
        return created

    def _apply_plano_formacao(self, rows: list[dict[str, str]]) -> int:
        """Create-only de PlanoFormacoes. NK (municipio, projeto, ano); `ano` DECLARADO do workbook.
        `sem_plano` (reserva: TOTAL 0 + sem data) é pulado (não é plano). Coordenador = a PESSOA que
        coordenou (coluna Coordenador da Agenda), resolvido por CPF → `Usuario` (cpf unique no banco);
        CPF ausente/inválido ou sem match → NULL, sem fallback email/nome (a pessoa é chave de CPF, #1849).
        `ch_estudo` importado; `ch_total`/`ch_anual` semeados dos totais da planilha (recalcular_ch
        sobrescreve quando/se as formações-filhas forem importadas)."""
        actor = self._require_actor("plano_formacao")
        mun_idx = self._municipio_index()
        usuario_idx = self._usuario_cpf_index()
        created = 0
        for r in rows:
            if _to_bool(r.get("sem_plano")):
                continue  # linha reservada, não é plano
            mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
            proj_id = self.resolve_projeto(r.get("projeto") or "")
            if mun_id is None or proj_id is None:
                continue  # FK não-resolvida (municipio/projeto)
            ano = _parse_int(r.get("ano"))
            if PlanoFormacoes.objects.filter(municipio_id=mun_id, projeto_id=proj_id, ano=ano).exists():
                continue
            # Coordenador = a PESSOA (Usuario) por CPF (#1849). CPF inválido/ausente/sem match → NULL,
            # sem chute por email/nome de cargo (a resolução por email atrelaria ao ocupante atual da caixa).
            cpf_raw = r.get("coordenador_cpf") or ""
            cpf = normalize_cpf_digits(cpf_raw) if is_valid_cpf(cpf_raw) else None
            coord_id = usuario_idx.get(cpf) if cpf else None
            PlanoFormacoes.objects.create(
                municipio_id=mun_id,
                projeto_id=proj_id,
                ano=ano,
                coordenador_id=coord_id,
                ch_estudo=_parse_decimal(r.get("ch_estudo")),
                ch_total=_parse_decimal(r.get("ch_total_planilha")),
                ch_anual=_parse_decimal(r.get("ch_anual_planilha")),
                created_by=actor,
            )
            created += 1
        return created

    def _apply_dat_registro(self, rows: list[dict[str, str]]) -> int:
        """Create-only de DATRegistro. NK (municipio, projeto_geral, projeto).
        aluno_qtde é obrigatório → linha sem ele é pulada. DATRegistro.save()
        recalcula nr_codigos + espelha usa_avaliar; nr_codigos_planilha guarda o
        valor cru da planilha para reconciliação."""
        actor = self._require_actor("dat_registro")
        mun_idx = self._municipio_index()
        pg_idx = self._projeto_geral_index()
        created = 0
        for r in rows:
            mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
            pg_id = pg_idx.get(_norm(r.get("projeto_geral") or ""))
            proj_id = self.resolve_projeto(r.get("projeto") or "")
            aluno_qtde = _parse_int(r.get("aluno_qtde"))
            if mun_id is None or pg_id is None or proj_id is None:
                continue  # FK não-resolvida (aluno_qtde é opcional: registros professor-only)
            if DATRegistro.objects.filter(municipio_id=mun_id, projeto_geral_id=pg_id, projeto_id=proj_id).exists():
                continue
            reg = DATRegistro(
                municipio_id=mun_id,
                projeto_geral_id=pg_id,
                projeto_id=proj_id,
                created_by=actor,
                aluno_qtde=aluno_qtde,
                professor_qtde=_parse_int(r.get("professor_qtde")),
                nr_codigos_planilha=_parse_int(r.get("nr_codigos_planilha")),
                reuniao_dat=_parse_iso_date(r.get("reuniao_dat")),
                turma_formar_id=_parse_int(r.get("turma_formar_id")),
                turma_formar_status=(r.get("turma_formar_status") or "pendente").strip() or "pendente",
                chaves_inscricao_status=(r.get("chaves_inscricao_status") or "pendente").strip() or "pendente",
                chaves_inscricao_data=_parse_iso_date(r.get("chaves_inscricao_data")),
                instrucoes_status=(r.get("instrucoes_status") or "pendente").strip() or "pendente",
                instrucoes_data=_parse_iso_date(r.get("instrucoes_data")),
                envio_codigos_status=(r.get("envio_codigos_status") or "pendente").strip() or "pendente",
                envio_codigos_data=_parse_iso_date(r.get("envio_codigos_data")),
                obs_formar=(r.get("obs_formar") or "")[:1000],
                alunos_recebidos_status=(r.get("alunos_recebidos_status") or "nao_aplicavel").strip()
                or "nao_aplicavel",
                alunos_recebidos_datas=_parse_json_list(r.get("alunos_recebidos_datas")),
                alunos_validados_status=(r.get("alunos_validados_status") or "nao_aplicavel").strip()
                or "nao_aplicavel",
                alunos_validados_datas=_parse_json_list(r.get("alunos_validados_datas")),
                alunos_importados_status=(r.get("alunos_importados_status") or "nao_aplicavel").strip()
                or "nao_aplicavel",
                alunos_importados_datas=_parse_json_list(r.get("alunos_importados_datas")),
                obs_avaliar=(r.get("obs_avaliar") or "")[:1000],
            )
            reg.save()  # calcula nr_codigos + espelha usa_avaliar do projeto_geral
            created += 1
        return created

    def _apply_dat_compra(self, rows: list[dict[str, str]]) -> int:
        """Create-only de DATCompra. NK existence-based por tupla; `tipo`/`conta_para_codigos`
        alimentam o cálculo de nr_codigos (recomputado ao fim do apply). Produto resolvido por
        codigo (opcional; fallback descricao_produto). status_uso é derivado no save()."""
        actor = self._require_actor("dat_compra")
        mun_idx = self._municipio_index()
        prod_idx = {(c or "").strip().upper(): pid for pid, c in Produto.objects.values_list("id", "codigo")}
        existing = set(
            DATCompra.objects.values_list(
                "municipio_id", "projeto_id", "descricao_produto", "tipo", "quantidade", "ano_uso", "data_compra"
            )
        )
        created = 0
        for r in rows:
            mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
            proj_id = self.resolve_projeto(r.get("projeto") or "")
            nk = self._dat_compra_nk(r, mun_id, proj_id)
            if mun_id is None or proj_id is None:
                continue  # FK não-resolvida (ano_uso vazio grava como pendente, ano_uso=NULL)
            if nk in existing:
                continue
            DATCompra.objects.create(
                municipio_id=mun_id,
                projeto_id=proj_id,
                produto_id=prod_idx.get((r.get("produto_codigo") or "").strip().upper()),
                descricao_produto=nk[2],
                tipo=nk[3],
                conta_para_codigos=_to_bool(r.get("conta_para_codigos")),
                quantidade=nk[4] or 0,
                ano_uso=nk[5],
                data_compra=nk[6],
                created_by=actor,
            )
            existing.add(nk)
            created += 1
        return created

    def _apply_projeto(self, rows: list[dict[str, str]]) -> int:
        """Create-only do master `projeto` (catálogo de variantes — Onda A). Matching via
        resolver #1372 (canon-key): cria SÓ unmatched, COM projeto_geral resolvível + fluxo
        válido (PA-01). NÃO usa actor (Projeto não tem created_by). PG/fluxo ausente → pula
        (would_reject no dry-run). Dedup intra-CSV por canon-key: o índice do resolver é cacheado
        antes do loop, então sem dedup 2 grafias da mesma variante quebrariam o unique de `nome`.
        Invalida o índice ao fim para que resolves posteriores (na mesma instância) vejam os novos."""
        if self._pidx is None:
            self._pidx = build_projeto_index()
        pg_idx = self._projeto_geral_index()
        seen: set[str] = set()
        seen_codigos: set[str] = set()
        created = 0
        for r in rows:
            nome = (r.get("projeto") or r.get("nome") or "").strip()
            if not nome:
                continue
            res = resolve_projeto_export(nome, index=self._pidx)
            if res.status != "unmatched":
                continue  # matched (já existe) ou ambiguous (decisão humana) → não cria
            if res.canonical_key in seen:
                continue  # mesma variante canônica repetida na run
            pg_name = (r.get("projeto_geral") or "").strip() or nome  # base sem PG → deriva do nome
            pg_id = pg_idx.get(_norm(pg_name))
            fluxo = (r.get("fluxo") or "").strip().upper()
            if pg_id is None or fluxo not in _PROJETO_FLUXOS:
                continue  # PG desconhecido / fluxo ausente → não cria (órfã/PA-01)
            codigo = (r.get("codigo") or "").strip()[:50]
            if codigo and codigo in seen_codigos:
                codigo = ""  # codigo repetido na run quebraria o unique parcial → grava vazio
            Projeto.objects.create(
                nome=nome,
                codigo=codigo,
                fluxo=fluxo,
                descricao=(r.get("descricao") or ""),
                ativo=(_to_bool(r.get("ativo")) if (r.get("ativo") or "").strip() else True),
                projeto_geral_id=pg_id,
            )
            seen.add(res.canonical_key)
            if codigo:
                seen_codigos.add(codigo)
            created += 1
        if created:
            self._pidx = None  # invalida cache: resolves posteriores veem os recém-criados
        return created

    def _papel_index_from_equipe(self) -> dict[str, str]:
        """Mapa cpf(11 dig) -> papel canonico, de equipe_gerencia.csv (fonte primaria do papel)."""
        idx: dict[str, str] = {}
        for r in self._load("equipe_gerencia"):
            cpf = normalize_cpf_digits(r.get("usuario_cpf") or "")
            papel = _resolve_papel(r.get("papel"))
            if len(cpf) == 11 and papel:
                idx.setdefault(cpf, papel)
        return idx

    def _apply_usuario(self, rows: list[dict[str, Any]]) -> int:
        """Cria usuarios (create-only) + atribui Django Group por papel. NK = CPF (fallback email).

        Papel: equipe_gerencia.papel (primario, por CPF) -> usuario.cargo (fallback). NUNCA
        default Coordenador. Sem papel ou grupo inexistente -> cria sem grupo. Senha
        inutilizavel (login real via OAuth Google). NK exige CPF valido por mod-11
        (is_valid_cpf): placeholder/DV-invalido NAO cria — o dry-run reporta o motivo.
        """
        papel_by_cpf = self._papel_index_from_equipe()
        existing_cpfs = {
            normalize_cpf_digits(c) for c in Usuario.objects.values_list("cpf", flat=True) if normalize_cpf_digits(c)
        }
        existing_emails = {(e or "").lower() for e in Usuario.objects.values_list("email", flat=True) if e}
        created = 0
        for r in rows:
            cpf = normalize_cpf_digits(r.get("cpf") or "")
            email = (r.get("email") or "").strip().lower()
            # NK exige CPF estruturalmente valido (mod-11). Placeholder/DV-invalido NAO
            # cria (username=cpf); nunca escreve CPF bogus (evita usuario fantasma e
            # colisao de unique). O dry-run ja reporta sem_nk/cpf_invalido/sem_cpf.
            if not is_valid_cpf(r.get("cpf") or ""):
                continue
            if (cpf in existing_cpfs) or (email and email in existing_emails):
                continue  # ja existe -> skip (create-only)
            nome = (r.get("nome_completo") or "").strip()
            first, _, last = nome.partition(" ")
            usuario = Usuario(
                username=cpf,
                cpf=cpf,
                email=email,
                first_name=first[:150],
                last_name=last[:150],
                telefone=(r.get("telefone") or "").strip()[:20],
                cargo=(r.get("cargo") or "").strip()[:100],
                is_active=True,
            )
            usuario.set_unusable_password()
            usuario.save()
            existing_cpfs.add(cpf)
            if email:
                existing_emails.add(email)
            papel = papel_by_cpf.get(cpf) or _resolve_papel(r.get("cargo"))
            group_name = _PAPEL_TO_GROUP.get(papel)
            if group_name and group_name in ALLOWED_USER_GROUPS:
                grupo = Group.objects.filter(name__iexact=group_name).first()
                if grupo:
                    usuario.groups.add(grupo)
            created += 1
        return created
