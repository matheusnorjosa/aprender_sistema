"""
Reconcile v16→v20 — corrige em prod o que o import create-only não conserta.

Contexto (RELAY-40/41 do sheets.banco): o pacote v20 traz `reconcile__v16_para_v20.csv`
com 121 correções em 5 classes. O create-only só ADICIONA; estas classes MUTAM linhas
existentes (reatribuir pessoa, deletar linha sem-origem, repontar/limpar família).

Disciplina (igual ao importer):
- **dry-run por padrão**; `--apply` só escreve as classes na allowlist (`allow`).
- **idempotente**: só escreve se o estado difere (senão `noop`).
- **nunca chuta**: lookup determinístico; ambíguo/não-encontrado → skip + report (nunca grava).
- roda tudo numa transação quando apply (all-or-nothing).

Chaves de lookup (confirmadas file:line, ver services/export_contract_importer.py):
- Projeto: resolver canon-key (`resolve_projeto_export`); ProjetoGeral: `_norm(nome)` (unique).
- Participation: `(solicitacao, usuario, role)`; Solicitacao: `external_hash`.

Handlers determinísticos de família implementados aqui; TROCA_DE_PESSOA/TROCA_DE_TITULAR/
LINHA_NAO_EMITIDA entram em incrementos seguintes (registrados como `pending` até lá).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportArgumentType=false, reportGeneralTypeIssues=false, reportPrivateUsage=false

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from django.db import transaction

from apps.core.imports.normalization import normalize_cpf_digits
from apps.core.models import Municipio, Participation, Projeto, ProjetoGeral, Solicitacao, Usuario
from apps.core.services.export_contract_projeto_resolver import (
    _norm,
    build_projeto_index,
    resolve_projeto_export,
)

# Classes do reconcile (coluna `classe` do CSV).
FAMILIA_CORRIGIDA = "FAMILIA_CORRIGIDA"
FAMILIA_INEXISTENTE = "FAMILIA_INEXISTENTE"
TROCA_DE_TITULAR = "TROCA_DE_TITULAR"
TROCA_DE_PESSOA = "TROCA_DE_PESSOA"
LINHA_NAO_EMITIDA = "LINHA_NAO_EMITIDA"

# Escrivíveis = subconjunto com handler REAL. As demais só reportam até serem implementadas.
IMPLEMENTED_CLASSES = frozenset({FAMILIA_CORRIGIDA, FAMILIA_INEXISTENTE, TROCA_DE_TITULAR, TROCA_DE_PESSOA})


def _parse_iso_date(s: str | None) -> date | None:
    try:
        return date.fromisoformat((s or "").strip())
    except ValueError:
        return None


_SEM_FAMILIA = {"(sem família)", "(sem familia)", ""}

# Ordem de processamento (dependências): repontar antes de deletar o fantasma órfão.
_CLASS_ORDER = [
    FAMILIA_CORRIGIDA,
    FAMILIA_INEXISTENTE,
    TROCA_DE_TITULAR,
    TROCA_DE_PESSOA,
    LINHA_NAO_EMITIDA,
]

_STATUSES = [
    "applied",
    "would_apply",
    "noop",
    "skipped_not_found",
    "skipped_ambiguous",
    "skipped_has_refs",
    "manual",
    "pending",
]

_RECONCILE_FILE = "reconcile__v16_para_v20.csv"


class ExportContractV20Reconciler:
    """Aplica reconcile__v16_para_v20.csv com dry-run-first + allowlist + guardas."""

    def __init__(
        self,
        path: str,
        *,
        apply: bool = False,
        allow: tuple[str, ...] = (),
        actor: Any = None,
    ) -> None:
        self.path = Path(path)
        self.apply = apply
        self.allow = set(allow)
        self.actor = actor
        self._report: dict[str, dict[str, int]] = {s: defaultdict(int) for s in _STATUSES}
        self._proj_index: Any = None
        self._pg_index: dict[str, int] | None = None
        self._cpf_cache: dict[str, Any] = {}
        self._mun_idx: dict[tuple[str, str], int] | None = None

    # ── infra ────────────────────────────────────────────────────────────────
    def _reconcile_path(self) -> Path:
        """Acha o reconcile CSV de maior versão em `path` (reconcile__v16_para_vNN.csv).
        Assim o mesmo comando serve v20 (nome/CPF) e v24 (evento_id/de_cpf/…) sem flag."""
        cands = list(self.path.glob("reconcile__v16_para_v*.csv"))
        if not cands:
            return self.path / _RECONCILE_FILE

        def _ver(p: Path) -> int:
            m = re.search(r"_v(\d+)\.csv$", p.name)
            return int(m.group(1)) if m else -1

        return max(cands, key=_ver)

    def _load(self) -> list[dict[str, str]]:
        with open(self._reconcile_path(), encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _get(r: dict[str, str], *keys: str) -> str:
        """Primeiro valor não-vazio entre `keys` (prefere coluna nova, cai na antiga)."""
        for k in keys:
            v = (r.get(k) or "").strip()
            if v:
                return v
        return ""

    def _sol_by_event(self, r: dict[str, str]) -> Any:
        """Solicitacao por evento_id (external_hash; fallback `chave`). None se ausente/sem match."""
        ehash = self._get(r, "evento_id", "chave")
        if not ehash:
            return None
        return Solicitacao.objects.filter(external_hash=ehash).first()

    def _rec(self, status: str, classe: str) -> None:
        self._report[status][classe] += 1

    def _should_write(self, classe: str) -> bool:
        return self.apply and classe in self.allow and classe in IMPLEMENTED_CLASSES

    def _projeto_geral_index(self) -> dict[str, int]:
        if self._pg_index is None:
            self._pg_index = {_norm(pg.nome): pg.id for pg in ProjetoGeral.objects.all()}
        return self._pg_index

    def _resolve_projeto(self, nome: str) -> Projeto | None:
        if self._proj_index is None:
            self._proj_index = build_projeto_index()
        res = resolve_projeto_export(nome, index=self._proj_index)
        return res.projeto if res.status == "matched" else None

    @staticmethod
    def _pg_has_refs(pg: ProjetoGeral) -> bool:
        """True se QUALQUER objeto aponta pra este ProjetoGeral (guard anti-deleção)."""
        for rel in pg._meta.related_objects:
            if getattr(rel, "one_to_one", False):
                continue
            try:
                if getattr(pg, rel.get_accessor_name()).exists():
                    return True
            except Exception:
                pass
        return False

    def _usuario_by_cpf(self, cpf_raw: str | None) -> Any:
        """Resolve Usuario por CPF (username=dígitos OU cpf=dígitos), com cache. None se ausente."""
        digits = normalize_cpf_digits(cpf_raw or "")
        if not digits:
            return None
        if digits not in self._cpf_cache:
            self._cpf_cache[digits] = (
                Usuario.objects.filter(username=digits).first() or Usuario.objects.filter(cpf=digits).first()
            )
        return self._cpf_cache[digits]

    @staticmethod
    def _usuario_by_email(email_raw: str | None) -> Any:
        """Resolve Usuario por e-mail (case-insensitive). Guarda 'nunca chuta': só resolve se
        EXATAMENTE 1 casar (e-mail compartilhado/posto → None → cai no CPF via `_resolve_para`)."""
        email = (email_raw or "").strip()
        if not email:
            return None
        qs = Usuario.objects.filter(email__iexact=email)
        return qs.first() if qs.count() == 1 else None

    def _resolve_para(self, r: dict[str, str]) -> Any:
        """Resolve o `para` (alvo do reassign) pela chave que casa com o prod (v25). O prod indexa
        coordenador por E-MAIL (CPF vazio/errado), então e-mail é a chave estável — EXCETO quando
        `email_desambigua == NAO_mesma_caixa` (o e-mail é um posto em sucessão, ex.: coordenacao21@
        Elienai→Diogo): aí o e-mail é ambíguo e usa-se o `para_cpf`. Fallback pro CPF sempre."""
        if (r.get("email_desambigua") or "").strip().upper() == "NAO_MESMA_CAIXA":
            return self._usuario_by_cpf(self._get(r, "para_cpf", "para"))
        return self._usuario_by_email(r.get("para_email")) or self._usuario_by_cpf(self._get(r, "para_cpf", "para"))

    @staticmethod
    def _map_role(papel: str | None) -> str | None:
        """Mapeia o `papel` do reconcile para Participation.Role (mesmo domínio do importer)."""
        p = (papel or "").strip().upper()
        if not p:
            return None
        if p.startswith("COORD") and "ACOMPANH" in p:
            return Participation.Role.COORD_ACOMPANHA
        if p.startswith("COORDENADOR"):
            return Participation.Role.COORDENADOR
        if p.startswith("FORMADOR"):
            return Participation.Role.FORMADOR
        if p.startswith("CONVIDADO"):
            return Participation.Role.CONVIDADO
        return None

    def _municipio_id(self, s: str | None) -> int | None:
        """Resolve município do formato 'NOME - UF' por (_norm(nome), uf). None se ausente/ambíguo."""
        raw = (s or "").strip()
        if not raw:
            return None
        if " - " in raw:
            nome, uf = raw.rsplit(" - ", 1)
        else:
            nome, uf = raw, ""
        if self._mun_idx is None:
            self._mun_idx = {(_norm(m.nome), (m.uf or "").upper()): m.id for m in Municipio.objects.all()}
        return self._mun_idx.get((_norm(nome), uf.strip().upper()))

    # ── handlers ───────────────────────────────────────────────────────────────
    def _h_familia_corrigida(self, r: dict[str, str]) -> None:
        classe = FAMILIA_CORRIGIDA
        proj = self._resolve_projeto((r.get("chave") or "").strip())
        if proj is None:
            return self._rec("skipped_not_found", classe)
        para = (r.get("para") or "").strip()
        if para in _SEM_FAMILIA:
            target_id: int | None = None
        else:
            target_id = self._projeto_geral_index().get(_norm(para))
            if target_id is None:
                return self._rec("skipped_not_found", classe)
        if proj.projeto_geral_id == target_id:
            return self._rec("noop", classe)
        if not self._should_write(classe):
            return self._rec("would_apply", classe)
        proj.projeto_geral_id = target_id
        proj.save(update_fields=["projeto_geral"])
        self._rec("applied", classe)

    def _h_familia_inexistente(self, r: dict[str, str]) -> None:
        classe = FAMILIA_INEXISTENTE
        pg_id = self._projeto_geral_index().get(_norm((r.get("chave") or "").strip()))
        if pg_id is None:
            return self._rec("noop", classe)  # já não existe (idempotente)
        pg = ProjetoGeral.objects.filter(id=pg_id).first()
        if pg is None:
            return self._rec("noop", classe)
        if self._pg_has_refs(pg):
            return self._rec("skipped_has_refs", classe)
        if not self._should_write(classe):
            return self._rec("would_apply", classe)
        pg.delete()
        self._pg_index = None  # invalida o cache após deletar
        self._rec("applied", classe)

    def _find_de_participation(self, sol: Any, role: str, r: dict[str, str]) -> Any:
        """Acha a participação do `de` no titular. A identidade gravada em prod pode ser
        o usuário (CPF), a caixa (e-mail em `de_usuario_origem`, como usuario OU guest_email),
        ou o nome livre (`de` = guest_nome). Tenta nessa ordem; None se nada casar."""
        de_user = self._usuario_by_cpf(self._get(r, "de_cpf", "de"))
        if de_user is not None:
            p = Participation.objects.filter(solicitacao=sol, usuario=de_user, role=role).first()
            if p is not None:
                return p
        email = (r.get("de_usuario_origem") or "").strip()
        if email:
            u = Usuario.objects.filter(email__iexact=email).first()
            if u is not None:
                p = Participation.objects.filter(solicitacao=sol, usuario=u, role=role).first()
                if p is not None:
                    return p
            p = Participation.objects.filter(solicitacao=sol, guest_email__iexact=email, role=role).first()
            if p is not None:
                return p
        nome = (r.get("de") or "").strip()
        if nome and not nome.replace(".", "").replace("-", "").isdigit():
            p = Participation.objects.filter(solicitacao=sol, guest_nome=nome, role=role).first()
            if p is not None:
                return p
        return None

    def _h_troca_de_titular(self, r: dict[str, str]) -> None:
        """Reatribui a Participation (caixa de coordenação) de `de`→`para`. Lookup por evento_id
        (external_hash; fallback `chave`) + identidade do `de` por CPF/e-mail-da-caixa/nome
        (`_find_de_participation`); `para` por `para_cpf` (fallback `para`)."""
        classe = TROCA_DE_TITULAR
        sol = self._sol_by_event(r)
        role = self._map_role(r.get("papel"))
        para_user = self._resolve_para(r)
        if sol is None or role is None or para_user is None:
            return self._rec("skipped_not_found", classe)
        # idempotência: se a participation do `para` já existe, nada a fazer.
        if Participation.objects.filter(solicitacao=sol, usuario=para_user, role=role).exists():
            return self._rec("noop", classe)
        p = self._find_de_participation(sol, role, r)
        if p is None:
            return self._rec("skipped_not_found", classe)
        if not self._should_write(classe):
            return self._rec("would_apply", classe)
        p.usuario = para_user
        p.guest_email = None
        p.guest_nome = ""
        p.save(update_fields=["usuario", "guest_email", "guest_nome"])
        self._rec("applied", classe)

    def _h_troca_de_pessoa(self, r: dict[str, str]) -> None:
        """Troca de pessoa num evento. Lookup PRIMÁRIO por evento_id (external_hash) →
        participação exata (sol, de, papel); FALLBACK v20 por (município nome+UF, data
        Fortaleza, papel, de-CPF) com **guarda estrita** (exatamente-1; senão skip+report,
        nunca chuta). Sub-ações (o_que_fazer): 'assumiu a coordenação' → reatribui de→para;
        'vaga de formador esvaziada' → remove; '+ saiu da vaga de formador' → reatribui +
        remove a de-formador do `para` no evento."""
        classe = TROCA_DE_PESSOA
        role = self._map_role(r.get("papel"))
        de_user = self._usuario_by_cpf(self._get(r, "de_cpf", "de"))
        if role is None or de_user is None:
            return self._rec("skipped_not_found", classe)

        sol = self._sol_by_event(r)
        if sol is not None:
            parts = list(Participation.objects.filter(solicitacao=sol, usuario=de_user, role=role))
        else:
            mun_id = self._municipio_id(r.get("municipio"))
            data = _parse_iso_date(r.get("data"))
            if mun_id is None or data is None:
                return self._rec("skipped_not_found", classe)
            parts = list(
                Participation.objects.filter(
                    solicitacao__municipio_id=mun_id,
                    solicitacao__inicio__date=data,
                    usuario=de_user,
                    role=role,
                )
            )
        if len(parts) == 0:
            return self._rec("skipped_not_found", classe)
        if len(parts) > 1:
            return self._rec("skipped_ambiguous", classe)  # guarda: não age no ambíguo
        p = parts[0]
        o_que = (r.get("o_que_fazer") or "").lower()

        # "vaga de formador esvaziada" → remove a participação (de, papel).
        if "vaga de formador esvaziada" in o_que:
            if not self._should_write(classe):
                return self._rec("would_apply", classe)
            p.delete()
            return self._rec("applied", classe)

        # "assumiu a coordenação" [+ saiu de formador] → reatribui de→para.
        para_user = self._resolve_para(r)
        if para_user is None:
            return self._rec("skipped_not_found", classe)
        if Participation.objects.filter(solicitacao=p.solicitacao, usuario=para_user, role=role).exists():
            return self._rec("noop", classe)  # para já ocupa o papel → idempotente/conflito
        if not self._should_write(classe):
            return self._rec("would_apply", classe)
        p.usuario = para_user
        p.save(update_fields=["usuario"])
        # secundário: "saiu da vaga de formador que já ocupava" → remove a formador do `para` no evento.
        if "saiu da vaga de formador" in o_que:
            Participation.objects.filter(
                solicitacao=p.solicitacao, usuario=para_user, role=Participation.Role.FORMADOR
            ).delete()
        self._rec("applied", classe)

    def _dispatch(self, r: dict[str, str]) -> None:
        classe = (r.get("classe") or "").strip()
        if classe == FAMILIA_CORRIGIDA:
            self._h_familia_corrigida(r)
        elif classe == FAMILIA_INEXISTENTE:
            self._h_familia_inexistente(r)
        elif classe == TROCA_DE_TITULAR:
            self._h_troca_de_titular(r)
        elif classe == TROCA_DE_PESSOA:
            self._h_troca_de_pessoa(r)
        elif classe == LINHA_NAO_EMITIDA:
            self._rec("manual", classe)  # deleção por contagem → relatório/decisão manual (não auto-deleta)
        else:
            self._rec("manual", classe or "(classe vazia)")

    # ── orquestração ────────────────────────────────────────────────────────────
    def run(self) -> dict[str, dict[str, int]]:
        rows = self._load()
        rows.sort(key=lambda r: _CLASS_ORDER.index(r["classe"]) if r.get("classe") in _CLASS_ORDER else 99)

        if self.apply:
            with transaction.atomic():
                for r in rows:
                    self._dispatch(r)
        else:
            for r in rows:
                self._dispatch(r)

        # Retorna os defaultdicts: status/classe ausente resolve para 0 (API amigável).
        return self._report
