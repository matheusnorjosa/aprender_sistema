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

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false

from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from apps.core.constants import ALLOWED_USER_GROUPS
from apps.core.imports.hashing import stable_import_hash
from apps.core.imports.normalization import normalize_cpf_digits
from apps.core.models import (
    Acompanhamento,
    AvailabilityBlock,
    DATAcao,
    DATArea,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    DATRegistro,
    Deslocamento,
    EquipeGerencia,
    Formacao,
    Gerencia,
    Municipio,
    Participation,
    PlanoFormacoes,
    Produto,
    Projeto,
    ProjetoGeral,
    Prova,
    Solicitacao,
    TipoEvento,
    Usuario,
)
from apps.core.services.dat_codigos import recompute_all
from apps.core.services.equipe_gerencia_import import (
    PAPEL_MAPPING,
    SETOR_MAPPING,
    _generate_gerencia_nome,
    _get_or_create_gerencia,
    _resolve_usuario,
)
from apps.core.services.eventos_import import _compute_external_hash
from apps.core.services.export_contract_projeto_resolver import build_projeto_index, resolve_projeto_export
from apps.core.services.resolvers import resolve_user_by_email, resolve_user_by_name
from apps.core.services.solicitacao_create import resolve_initial_status
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
    "equipe_gerencia",
    "dat_coordenador",
    "dat_acao",
    "plano_formacao",
    "dat_registro",
    "dat_cadastro",
    "dat_compra",
    "solicitacao",
    "participation",
    "formacao",
    "acompanhamento",
    "prova",
    "availability_block",
    "deslocamento",
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
# Papéis canônicos válidos de EquipeGerencia (NK inclui o papel; fora disto = would_reject).
_EQUIPE_PAPEIS = frozenset(_PAPEL_TO_GROUP)

# Tipos válidos de Acompanhamento (choices do model, sem CheckConstraint no BD → guard no importer).
_ACOMPANHAMENTO_TIPOS = frozenset({"primeiro", "segundo"})

# Guardrail: colunas do CSV que cada handler DE FATO consome. O classify reporta em `ignored_fields`
# o que chega no contrato mas não é lido — pra nenhum dado cair calado (sugestão do sheets.banco).
# Inclui os aliases aceitos na leitura. Entidade sem entrada aqui não reporta ignorados (ainda).
_CONSUMED_FIELDS: dict[str, frozenset[str]] = {
    "equipe_gerencia": frozenset(
        {
            "gerencia",
            "setor",
            "usuario_cpf",
            "cpf",
            "usuario_email",
            "email",
            "usuario_nome",
            "nome",
            "papel",
            "setor_canonico",
        }
    ),
    "solicitacao": frozenset(
        {
            "municipio",
            "uf",
            "projeto",
            "tipo_evento",
            "data",
            "hora_inicio",
            "hora_fim",
            "segmento",
            "encontro",
            "coord_acompanha",
            "coordenador",
            "coordenador_cpf",
            "solicitante_cpf",
            "solicitante_email",
            "solicitante_procedencia",
            "linha_completa",
            "is_online",
            "evento_id",
            "evento_id_origem",
            "evento_hash_natural",
        }
    ),
    "participation": frozenset(
        {
            "evento_id",
            "evento_hash_natural",
            "usuario",
            "usuario_cpf",
            "usuario_email",
            "email",
            "convidados_emails",
            "match_procedencia",
            "role",
        }
    ),
    "formacao": frozenset(
        {"municipio", "uf", "projeto", "ano", "numero_formacao", "data_formacao", "carga_horaria", "modalidade"}
    ),
    "acompanhamento": frozenset({"municipio", "uf", "projeto", "ano", "tipo", "data_acompanhamento"}),
    "prova": frozenset({"municipio", "uf", "projeto", "ano", "numero_prova", "data_prova", "marcado"}),
    "availability_block": frozenset({"usuario_cpf", "inicio", "fim", "tipo", "motivo"}),
    "deslocamento": frozenset({"usuario_cpf", "origem", "destino", "start_date", "end_date", "observacao"}),
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


_FORTALEZA_TZ = ZoneInfo("America/Fortaleza")


def _parse_local_datetime(v: Any) -> datetime | None:
    """Parseia datetime ISO (YYYY-MM-DDTHH:MM:SS) LOCAL de Fortaleza → aware em UTC (RD-06).
    Vazio/inválido → None. Ignora offset já embutido (a fonte emite naive + timezone=Fortaleza)."""
    s = str(v or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt, _FORTALEZA_TZ)
    return dt


def _parse_hora(v: Any) -> time | None:
    """Parseia hora HH:MM (ou HH:MM:SS) do export-contract. Vazio/inválido → None."""
    s = str(v or "").strip()
    if not s:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _map_participation_role(raw: Any) -> str | None:
    """Papel do participante vindo do CSV (derivado de POSIÇÃO pela planilha), NUNCA do cargo do
    usuário. Tolera rótulos de posição ('Formador 1'..'Formador 5' → FORMADOR). Fora do domínio → None."""
    s = str(raw or "").strip().upper()
    if not s:
        return None
    if s.startswith("COORD") and "ACOMPANH" in s:
        return Participation.Role.COORD_ACOMPANHA
    if s.startswith("COORDENADOR"):
        return Participation.Role.COORDENADOR
    if s.startswith("FORMADOR"):
        return Participation.Role.FORMADOR
    if s.startswith("CONVIDADO"):
        return Participation.Role.CONVIDADO
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
        self._dat_uso_projetos: set[str] | None = None

    def _projetos_com_dat_uso(self) -> set[str]:
        """norm(nome) dos projetos que aparecem em dat_registro.csv/dat_compra.csv (coluna `projeto`).
        Guard do #1897: um rótulo família-vazia (projeto_geral NULL) é OK, MAS se tem uso DAT a família
        importa para `nr_codigos` → não pode ficar sem — o import barra a criação (would_reject)."""
        if self._dat_uso_projetos is None:
            s: set[str] = set()
            for ent in ("dat_registro", "dat_compra"):
                for r in self._load(ent):
                    nome = (r.get("projeto") or "").strip()
                    if nome:
                        s.add(_norm(nome))
            self._dat_uso_projetos = s
        return self._dat_uso_projetos

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

    def _tipo_evento_index(self) -> dict[str, int]:
        """Índice norm(nome) → tipo_evento_id (resolver FK de solicitacao por nome do tipo)."""
        return {_norm(n): tid for tid, n in TipoEvento.objects.values_list("id", "nome")}

    def _resolve_solicitante(self, r: dict[str, str], cpf_idx: dict[str, int]) -> int | None:
        """Pessoa dona do evento (v16.4, RELAY 57), já resolvida pelo sheets em `solicitante_cpf` (cascata
        coluna_n + escada-2-tokens + inferência). Fallback: `solicitante_email` (mesma pessoa) e, por fim,
        `coordenador_cpf` cru (fixtures/legado). Retorna o Usuario.id ou None. É gravada em `usuario` E
        `coordenador` (decisão a). NÃO gateia por cargo/papel."""
        cpf = normalize_cpf_digits(r.get("solicitante_cpf") or "")
        if len(cpf) == 11:
            uid = cpf_idx.get(cpf)
            if uid is not None:
                return uid
        email = (r.get("solicitante_email") or "").strip()
        if email:
            u = resolve_user_by_email(email)
            if u is not None:
                return u.id
        fb = normalize_cpf_digits(r.get("coordenador_cpf") or "")
        if len(fb) == 11:
            return cpf_idx.get(fb)
        return None

    def _resolve_solicitacao_key(
        self,
        r: dict[str, str],
        mun_idx: dict[tuple[str, str], int],
        tipo_idx: dict[str, int],
        cpf_idx: dict[str, int],
    ) -> tuple[int, int, int, date, time, time, str, int, str] | None:
        """Resolve os campos-chave de uma linha de solicitacao (FKs + hora + solicitante).
        Retorna (mun_id, proj_id, tipo_id, data, hora_ini, hora_fim, segmento, coord_id, ext_hash) ou
        None se algum essencial não resolve (would_reject: `linha_completa=false`, FK ausente, hora
        inválida, ou solicitante — `usuario` NOT NULL — não resolvido). Identidade (external_hash) = o
        `evento_id` estável do CSV; fallback `evento_hash_natural` (join intra-entrega) e
        `_compute_external_hash` (ADR-012) quando ausentes. Solicitante (dono) via `_resolve_solicitante`
        (`solicitante_cpf`→`solicitante_email`→`coordenador_cpf`)."""
        # v16.2: linha incompleta (sem hora/dados essenciais, `linha_completa=false`) = fora de escopo do
        # import — NÃO inventa hora (RELAY 54). Coluna ausente (fixtures/CSV antigo) → trata como completa.
        lc = r.get("linha_completa")
        if lc is not None and not _to_bool(lc):
            return None
        mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
        proj_id = self.resolve_projeto(r.get("projeto") or "")
        tipo_id = tipo_idx.get(_norm(r.get("tipo_evento") or ""))
        data_ev = _parse_iso_date(r.get("data"))
        hora_ini = _parse_hora(r.get("hora_inicio"))
        hora_fim = _parse_hora(r.get("hora_fim"))
        coord_id = self._resolve_solicitante(r, cpf_idx)
        if mun_id is None or proj_id is None or tipo_id is None or coord_id is None:
            return None
        if data_ev is None or hora_ini is None or hora_fim is None:
            return None
        segmento = (r.get("segmento") or "").strip()
        # Identidade ESTÁVEL = `evento_id` (ledger do sheets.banco, sobrevive a edição da linha). RELAY 52
        # mediu que o `evento_hash_natural` (hash de CONTEÚDO) deriva ~2%/10 dias (44/3.322 mudam de hash),
        # logo NÃO serve de identidade ao longo do tempo — armazená-lo recria o problema do RELAY 50 item 2
        # (a cada carga ~44 eventos viram "novo" + ~44 órfãos). O hash vira fallback (join dentro de UMA
        # entrega) e `_compute_external_hash` (ADR-012) o último fallback (fixtures / CSV sem as colunas).
        ext_hash = (
            (r.get("evento_id") or "").strip()
            or (r.get("evento_hash_natural") or "").strip()
            or _compute_external_hash(mun_id, proj_id, tipo_id, data_ev, hora_ini, hora_fim, segmento)
        )
        return (mun_id, proj_id, tipo_id, data_ev, hora_ini, hora_fim, segmento, coord_id, ext_hash)

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
            # prefixo PROJETO). Criar exige fluxo autoritativo (PA-01). projeto_geral resolvível OU,
            # se vazio, rótulo família-vazia sem uso DAT (#1897) → cria NULL; PG declarado-desconhecido
            # ou família-vazia-com-dat = would_reject rotulado.
            if self._pidx is None:
                self._pidx = build_projeto_index()
            pg_idx = self._projeto_geral_index()
            reasons = {
                "nome_vazio": 0,
                "ambiguous": 0,
                "pg_desconhecido": 0,
                "fluxo_ausente": 0,
                "familia_vazia_com_dat": 0,
            }
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
                # unmatched → candidato a create.
                pg_raw = (r.get("projeto_geral") or "").strip()
                if pg_idx.get(_norm(pg_raw or nome)) is None:  # nem declarado nem homônimo resolve
                    if pg_raw:
                        tally["would_reject"] += 1  # PG DECLARADO mas desconhecido
                        reasons["pg_desconhecido"] += 1
                        continue
                    if _norm(nome) in self._projetos_com_dat_uso():  # #1897: família vazia + uso DAT
                        tally["would_reject"] += 1
                        reasons["familia_vazia_com_dat"] += 1
                        continue
                    # else: rótulo família-vazia sem uso DAT → OK criar NULL
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

        elif name == "equipe_gerencia":
            # NK = (gerencia, usuario, papel). Papel fora do domínio ou usuário não-resolvido →
            # would_reject. Gerência resolvida read-only (o apply cria se faltar via
            # _get_or_create_gerencia). PII: usuário (CPF) só entra na contagem de existência.
            existing = set(EquipeGerencia.objects.values_list("gerencia_id", "usuario_id", "papel"))
            for r in rows:
                setor = (r.get("gerencia") or r.get("setor") or "").strip()
                papel = _resolve_papel(r.get("papel"))
                if not setor or papel not in _EQUIPE_PAPEIS:
                    tally["would_reject"] += 1
                    continue
                usuario = _resolve_usuario(
                    r.get("usuario_cpf") or r.get("cpf") or "",
                    r.get("usuario_email") or r.get("email") or "",
                    r.get("usuario_nome") or r.get("nome") or "",
                )
                if usuario is None:
                    tally["would_reject"] += 1
                    continue
                ger = self._resolve_gerencia_readonly(setor)
                exists = ger is not None and (ger.id, usuario.id, papel) in existing
                st, _ = diff_and_classify({} if exists else None, {}, protected)
                tally[st] += 1

        elif name == "solicitacao":
            # NK = external_hash (= evento_id estável do CSV; fallback hash/recompute). FK/hora/coordenador não resolvidos →
            # would_reject. Existence-based (status/participations ficam para o apply).
            mun_idx = self._municipio_index()
            tipo_idx = self._tipo_evento_index()
            cpf_idx = self._usuario_cpf_index()
            existing = set(
                Solicitacao.objects.exclude(external_hash__isnull=True).values_list("external_hash", flat=True)
            )
            for r in rows:
                key = self._resolve_solicitacao_key(r, mun_idx, tipo_idx, cpf_idx)
                if key is None:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if key[-1] in existing else None, {}, protected)
                tally[st] += 1

        elif name == "participation":
            # Liga por evento_id (fallback evento_hash_natural) → solicitacao.external_hash. Papel do CSV (posição), não cargo.
            # No dry-run a solicitacao pode ainda não existir no DB → would_reject inflado (esperado; o apply
            # ordenado cria a solicitacao antes). Resolução de usuário/existência fica para o apply.
            sol_hashes = set(
                Solicitacao.objects.exclude(external_hash__isnull=True).values_list("external_hash", flat=True)
            )
            for r in rows:
                ehash = (r.get("evento_id") or r.get("evento_hash_natural") or "").strip()
                role = _map_participation_role(r.get("role"))
                if not ehash or ehash not in sol_hashes or role is None:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify(None, {}, protected)  # would_create (dedup por-usuário no apply)
                tally[st] += 1

        elif name == "formacao":
            # Filha de PlanoFormacoes. NK (plano_id, numero_formacao); plano pai resolvido por
            # (municipio, projeto[, ano derivado de data_formacao.year]). Plano/FK ausente ou numero
            # fora de 1..15 (CheckConstraint) → would_reject. Existence-based.
            mun_idx = self._municipio_index()
            existing = set(Formacao.objects.values_list("plano_id", "numero_formacao"))
            for r in rows:
                plano_id = self._resolve_plano_id(r, mun_idx, "data_formacao")
                numero = _parse_int(r.get("numero_formacao"))
                if plano_id is None or numero is None or not (1 <= numero <= 15):
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if (plano_id, numero) in existing else None, {}, protected)
                tally[st] += 1

        elif name == "acompanhamento":
            # Filha de PlanoFormacoes. NK (plano_id, tipo); tipo ∈ {primeiro, segundo} (choices, sem
            # CheckConstraint no BD → guard aqui p/ não gravar valor fora do domínio). Existence-based.
            mun_idx = self._municipio_index()
            existing = set(Acompanhamento.objects.values_list("plano_id", "tipo"))
            for r in rows:
                plano_id = self._resolve_plano_id(r, mun_idx, "data_acompanhamento")
                tipo = (r.get("tipo") or "").strip().lower()
                if plano_id is None or tipo not in _ACOMPANHAMENTO_TIPOS:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if (plano_id, tipo) in existing else None, {}, protected)
                tally[st] += 1

        elif name == "prova":
            # Filha de PlanoFormacoes. NK (plano_id, numero_prova); numero ∈ 1..3 (CheckConstraint).
            # Existence-based.
            mun_idx = self._municipio_index()
            existing = set(Prova.objects.values_list("plano_id", "numero_prova"))
            for r in rows:
                plano_id = self._resolve_plano_id(r, mun_idx, "data_prova")
                numero = _parse_int(r.get("numero_prova"))
                if plano_id is None or numero is None or not (1 <= numero <= 3):
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if (plano_id, numero) in existing else None, {}, protected)
                tally[st] += 1

        elif name == "availability_block":
            # Bloco de disponibilidade de formador. usuario por CPF (FK PROTECT NOT NULL → sem match
            # = reject). tipo ∈ {T, P} (CheckConstraint). inicio/fim datetime local → UTC; fim ≤ inicio
            # viola a constraint → reject. NK (usuario, inicio, fim, tipo). Existence-based.
            cpf_idx = self._usuario_cpf_index()
            existing = set(AvailabilityBlock.objects.values_list("usuario_id", "inicio", "fim", "tipo"))
            for r in rows:
                usr_id = cpf_idx.get(normalize_cpf_digits(r.get("usuario_cpf") or ""))
                tipo = (r.get("tipo") or "").strip().upper()
                inicio = _parse_local_datetime(r.get("inicio"))
                fim = _parse_local_datetime(r.get("fim"))
                if usr_id is None or tipo not in ("T", "P") or inicio is None or fim is None or fim <= inicio:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if (usr_id, inicio, fim, tipo) in existing else None, {}, protected)
                tally[st] += 1

        elif name == "deslocamento":
            # Deslocamento de formador (origem/destino TEXTO, não FK). usuario por CPF (PROTECT NOT
            # NULL → sem match = reject); start/end obrigatórios. NK = external_hash (SHA1 ADR-012)
            # sobre (usuario, start, end, origem, destino, observacao) — observacao ENTRA (RELAY 31:
            # senão ida/volta colapsam). Existence-based por hash.
            cpf_idx = self._usuario_cpf_index()
            existing = set(
                Deslocamento.objects.exclude(external_hash__isnull=True).values_list("external_hash", flat=True)
            )
            for r in rows:
                fields = self._deslocamento_fields(r, cpf_idx)
                if fields is None:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify({} if fields[-1] in existing else None, {}, protected)
                tally[st] += 1

        if name in _CONSUMED_FIELDS and rows:
            # Guardrail: colunas presentes no CSV que o handler não lê (aliases já contam como consumidos).
            tally["ignored_fields"] = sorted(set(rows[0].keys()) - _CONSUMED_FIELDS[name])

        tally["export_rows"] = len(rows)
        return tally

    def _resolve_plano_id(self, r: dict[str, str], mun_idx: dict[tuple[str, str], int], date_field: str) -> int | None:
        """Resolve o PlanoFormacoes pai de uma filha (formacao/acompanhamento/prova) por
        (municipio, projeto, ano).

        `ano` vem da coluna `ano` do CSV da filha — o MESMO dado do pai (contrato v16.7/RELAY 31),
        não derivado. Fallback p/ contratos antigos/fixtures: ano derivado de `date_field.year` (as
        datas da fonte vêm DD/MM sem ano → derivação NÃO é confiável para planos de outros anos, por
        isso a coluna explícita); depois o ÚNICO plano do par (golden 1:1).

        Fail-safe: par (mun, proj) com planos em anos distintos e `ano` desconhecido → ambíguo →
        None (rejeita a filha, não chuta um plano arbitrário). Co-liderança no MESMO (mun, proj,
        ano) = 1 plano com N coordenadores (M2M, #1957): a UniqueConstraint garante 1 plano por
        (mun, proj, ano), então o resolver casa esse plano único e as filhas co-lideradas anexam a ele."""
        mun_id = mun_idx.get((_norm(r.get("municipio") or ""), (r.get("uf") or "").upper()))
        proj_id = self.resolve_projeto(r.get("projeto") or "")
        if mun_id is None or proj_id is None:
            return None
        qs = PlanoFormacoes.objects.filter(municipio_id=mun_id, projeto_id=proj_id)
        ano = _parse_int(r.get("ano"))
        if ano is None:
            d = _parse_iso_date(r.get(date_field))
            ano = d.year if d is not None else None
        if ano is not None:
            matched = qs.filter(ano=ano).values_list("id", flat=True).first()  # UniqueConstraint → ≤1
            if matched is not None:
                return matched
        ids = list(qs.values_list("id", flat=True)[:2])
        return ids[0] if len(ids) == 1 else None

    def _deslocamento_fields(
        self, r: dict[str, str], cpf_idx: dict[str, int]
    ) -> tuple[int, str, str, date, date, str, str] | None:
        """Resolve os campos de um deslocamento + o external_hash (ponto único, classify e apply).
        None se usuario (por CPF) ou datas (start/end) não resolvem. origem/destino são texto (não
        FK); observacao ENTRA no hash (RELAY 31: senão ida/volta colapsam)."""
        usr_id = cpf_idx.get(normalize_cpf_digits(r.get("usuario_cpf") or ""))
        start = _parse_iso_date(r.get("start_date"))
        end = _parse_iso_date(r.get("end_date"))
        if usr_id is None or start is None or end is None:
            return None
        origem = (r.get("origem") or "").strip()[:200]
        destino = (r.get("destino") or "").strip()[:200]
        obs = (r.get("observacao") or "").strip()
        h = stable_import_hash(str(usr_id), start.isoformat(), end.isoformat(), origem, destino, obs)
        return (usr_id, origem, destino, start, end, obs, h)

    def _resolve_gerencia_readonly(self, setor_raw: str) -> Gerencia | None:
        """Resolve Gerencia por setor SEM criar (espelha a precedência de _get_or_create_gerencia,
        p/ o classify dry-run): nome_setor → nome → nome canônico gerado."""
        setor = SETOR_MAPPING.get(setor_raw, setor_raw)
        return (
            Gerencia.objects.filter(nome_setor__iexact=setor).first()
            or Gerencia.objects.filter(nome__iexact=setor).first()
            or Gerencia.objects.filter(nome__iexact=_generate_gerencia_nome(setor)).first()
        )

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
                if name == "equipe_gerencia":
                    # NK = (gerencia, usuario, papel); CSV usa `usuario_cpf`/`gerencia` (setor), não
                    # `nome` → handler dedicado (o loop genérico gravaria 0 = silent-gap).
                    applied[name] = self._apply_equipe_gerencia(self._load(name))
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
                if name == "solicitacao":
                    applied[name] = self._apply_solicitacao(self._load(name))
                    continue
                if name == "participation":
                    # DEPOIS de solicitacao (ENTITY_ORDER garante): liga por external_hash já criado.
                    applied[name] = self._apply_participation(self._load(name))
                    continue
                if name == "formacao":
                    # Filha de PlanoFormacoes (DEPOIS de plano_formacao por ENTITY_ORDER). CSV sem `nome`.
                    applied[name] = self._apply_formacao(self._load(name))
                    continue
                if name == "acompanhamento":
                    applied[name] = self._apply_acompanhamento(self._load(name))
                    continue
                if name == "prova":
                    applied[name] = self._apply_prova(self._load(name))
                    continue
                if name == "availability_block":
                    applied[name] = self._apply_availability_block(self._load(name))
                    continue
                if name == "deslocamento":
                    applied[name] = self._apply_deslocamento(self._load(name))
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

    def _apply_equipe_gerencia(self, rows: list[dict[str, str]]) -> int:
        """Create-only de EquipeGerencia. NK (gerencia, usuario, papel); vigência aberta
        (valid_from=hoje, valid_to=None). Reusa os resolvers do serviço de upload
        (_get_or_create_gerencia / _resolve_usuario). Popula Gerencia.setor_canonico do row
        (vocabulário de produto, de-para) — o fio de leitura do #1893. EquipeGerencia não audita
        (sem created_by) → NÃO exige actor. CPF por string (não valida dígito: a linha de dígito
        inválido casa por igualdade); papel/usuário não-resolvido → pula (nunca o substring do #1643)."""
        hoje = timezone.localdate()
        ger_stats: dict[str, Any] = {"gerencias_created": 0, "gerencias_existing": 0}
        created = 0
        for r in rows:
            setor_raw = (r.get("gerencia") or r.get("setor") or "").strip()
            papel = _resolve_papel(r.get("papel"))
            if not setor_raw or papel not in _EQUIPE_PAPEIS:
                continue
            usuario = _resolve_usuario(
                r.get("usuario_cpf") or r.get("cpf") or "",
                r.get("usuario_email") or r.get("email") or "",
                r.get("usuario_nome") or r.get("nome") or "",
            )
            if usuario is None:
                continue
            gerencia = _get_or_create_gerencia(setor_raw, ger_stats)
            if gerencia is None:
                continue
            setor_canon = (r.get("setor_canonico") or "").strip()
            if setor_canon and gerencia.setor_canonico != setor_canon:
                gerencia.setor_canonico = setor_canon
                gerencia.save(update_fields=["setor_canonico"])
            if EquipeGerencia.objects.filter(gerencia=gerencia, usuario=usuario, papel=papel).exists():
                continue
            EquipeGerencia.objects.create(
                gerencia=gerencia,
                usuario=usuario,
                papel=papel,
                ativo=True,
                valid_from=hoje,
                valid_to=None,
            )
            created += 1
        return created

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

    def _resolve_coordenador_ids(self, r: dict[str, str], usuario_idx: dict[str, int]) -> list[int]:
        """CPFs dos coordenadores → ids de `Usuario`, em ordem e sem duplicar. Co-liderança N:N (RELAY
        32/34): prefere o array `coordenadores_cpf`; cai para a coluna única `coordenador_cpf` (CSV
        antigo). CPF inválido (mod-11), ausente ou sem match no cadastro é descartado — sem fallback por
        email/nome de cargo (isso atrelaria ao ocupante atual da caixa; a pessoa é chave de CPF, #1849)."""
        raw = _parse_json_list(r.get("coordenadores_cpf"))
        if not raw:
            single = r.get("coordenador_cpf") or ""
            raw = [single] if single else []
        ids: list[int] = []
        for item in raw:
            s = str(item or "")
            cpf = normalize_cpf_digits(s) if is_valid_cpf(s) else None
            uid = usuario_idx.get(cpf) if cpf else None
            if uid is not None and uid not in ids:
                ids.append(uid)
        return ids

    def _apply_plano_formacao(self, rows: list[dict[str, str]]) -> int:
        """Create-only de PlanoFormacoes. NK (municipio, projeto, ano); `ano` DECLARADO do workbook.
        `sem_plano` (reserva: TOTAL 0 + sem data) é pulado (não é plano). Coordenadores = as PESSOAS que
        coordenaram (coluna Coordenador da Agenda), N:N por co-liderança (RELAY 32/34): `coordenadores_cpf`
        (array) com fallback `coordenador_cpf`, cada CPF → `Usuario` (sem fallback email/nome; ausente/
        inválido/sem match é descartado, #1849). `ch_estudo` importado; `ch_total`/`ch_anual` semeados dos
        totais da planilha (recalcular_ch sobrescreve quando/se as formações-filhas forem importadas)."""
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
            coord_ids = self._resolve_coordenador_ids(r, usuario_idx)
            plano = PlanoFormacoes.objects.create(
                municipio_id=mun_id,
                projeto_id=proj_id,
                ano=ano,
                ch_estudo=_parse_decimal(r.get("ch_estudo")),
                ch_total=_parse_decimal(r.get("ch_total_planilha")),
                ch_anual=_parse_decimal(r.get("ch_anual_planilha")),
                created_by=actor,
            )
            if coord_ids:
                plano.coordenadores.set(coord_ids)
            created += 1
        return created

    def _apply_solicitacao(self, rows: list[dict[str, str]]) -> int:
        """Create-only de Solicitacao. NK = external_hash = `evento_id` estável do CSV (fallback
        `evento_hash_natural`, depois `_compute_external_hash`/ADR-012 — ver `_resolve_solicitacao_key`). Solicitante
        (dono) via `_resolve_solicitante` (solicitante_cpf→email→coordenador_cpf, v16.4); grava `usuario` E a FK
        `coordenador` (decisão a — a tela lê a FK) + uma Participation(COORDENADOR) e carimba
        `solicitante_procedencia`. Status via `resolve_initial_status` (PA-01: SUPER/desconhecido →
        pendente). `coord_acompanha` (Sim/Não) → BooleanField `coordenador_acompanha` (RELAY 50: visual,
        vazio→False). inicio/fim montados de data+hora LOCAL (America/Fortaleza), armazenados em UTC. Sem
        `created_by` no model → não exige actor."""
        mun_idx = self._municipio_index()
        tipo_idx = self._tipo_evento_index()
        cpf_idx = self._usuario_cpf_index()
        proj_by_id = {p.id: p for p in Projeto.objects.all()}
        existing = set(Solicitacao.objects.exclude(external_hash__isnull=True).values_list("external_hash", flat=True))
        created = 0
        for r in rows:
            key = self._resolve_solicitacao_key(r, mun_idx, tipo_idx, cpf_idx)
            if key is None:
                continue  # would_reject (FK/hora/coordenador não resolvido)
            mun_id, proj_id, tipo_id, data_ev, hora_ini, hora_fim, segmento, coord_id, ext_hash = key
            if ext_hash in existing:
                continue
            inicio = timezone.make_aware(datetime.combine(data_ev, hora_ini), _FORTALEZA_TZ)
            fim = timezone.make_aware(datetime.combine(data_ev, hora_fim), _FORTALEZA_TZ)
            if fim <= inicio:
                continue  # constraint solicitacao_fim_gt_inicio: linha inconsistente
            status = resolve_initial_status(projeto=proj_by_id.get(proj_id)).status
            sol = Solicitacao.objects.create(
                usuario_id=coord_id,  # solicitante = coordenador (D3)
                municipio_id=mun_id,
                projeto_id=proj_id,
                tipo_evento_id=tipo_id,
                coordenador_id=coord_id,  # grava nos DOIS (decisão a)
                inicio=inicio,
                fim=fim,
                segmento=segmento,
                encontro=(r.get("encontro") or "").strip() or None,
                coordenador_acompanha=_to_bool(r.get("coord_acompanha")),
                is_online=_to_bool(r.get("is_online")),
                status=status,
                external_hash=ext_hash,
                solicitante_procedencia=(r.get("solicitante_procedencia") or "").strip()[:30],
            )
            Participation.objects.get_or_create(
                solicitacao=sol, usuario_id=coord_id, role=Participation.Role.COORDENADOR
            )
            existing.add(ext_hash)
            created += 1
        return created

    def _resolve_participante(self, r: dict[str, str], cpf_idx: dict[str, int]) -> Usuario | None:
        """EMAIL-first (`resolve_user_by_email`, exato, sem filtro is_active — inclui inativos, RELAY 50)
        → CPF (`usuario_cpf`) → nome (escada determinística #1643). Papel/cargo NUNCA gateiam a resolução.

        Guarda de relay (v16.4/RELAY 57): se o sheets emite `match_procedencia` e ele vem VAZIO, a fonte
        JÁ tentou CPF/e-mail + escada-2-tokens e se absteve — o resolver-por-nome (Degrau 2, token-subset)
        é sinal mais fraco e casaria a pessoa que SAIU a um homônimo de nome mais longo. Então NÃO resolve
        por nome nesse caso → vira `guest_nome` (preserva quem saiu). Coluna ausente (fixtures/CSV antigo) =
        sem sinal → mantém o fallback por nome."""
        email = (r.get("usuario_email") or r.get("email") or r.get("convidados_emails") or "").strip()
        if email:
            first = email.replace(";", ",").split(",")[0].strip()
            u = resolve_user_by_email(first)
            if u is not None:
                return u
        cpf = normalize_cpf_digits(r.get("usuario_cpf") or "")
        if len(cpf) == 11:
            uid = cpf_idx.get(cpf)
            if uid is not None:
                return Usuario.objects.filter(id=uid).first()
        match_proc = r.get("match_procedencia")
        if match_proc is not None and not match_proc.strip():
            return None  # fonte abstém-se → não fuzzy-match por nome → guest_nome
        nome = (r.get("usuario") or "").strip()
        if nome and "@" not in nome:
            return resolve_user_by_name(nome)
        return None

    def _apply_participation(self, rows: list[dict[str, str]]) -> int:
        """Create-only de Participation. Liga por `evento_id` (fallback `evento_hash_natural`) →
        `solicitacao.external_hash`.
        Papel vem do CSV (POSIÇÃO), NUNCA do cargo. Usuário resolvido EMAIL-first → CPF → nome; sem match
        mas com nome → `guest_nome` (preserva quem saiu, MARCA não descarta). Sem solicitacao ou papel
        inválido → pula. Dedup existence-based (por-usuário e nome-only), índices atualizados in-memory."""
        sol_idx = dict(Solicitacao.objects.exclude(external_hash__isnull=True).values_list("external_hash", "id"))
        cpf_idx = self._usuario_cpf_index()
        existing_user = set(
            Participation.objects.exclude(usuario__isnull=True).values_list("solicitacao_id", "usuario_id", "role")
        )
        existing_nome = set(
            Participation.objects.exclude(guest_nome="").values_list("solicitacao_id", "guest_nome", "role")
        )
        created = 0
        for r in rows:
            ehash = (r.get("evento_id") or r.get("evento_hash_natural") or "").strip()
            sol_id = sol_idx.get(ehash)
            role = _map_participation_role(r.get("role"))
            if sol_id is None or role is None:
                continue  # solicitacao inexistente (órfã) ou papel fora do domínio
            usuario = self._resolve_participante(r, cpf_idx)
            if usuario is not None:
                ukey = (sol_id, usuario.id, role)
                if ukey in existing_user:
                    continue
                Participation.objects.create(solicitacao_id=sol_id, usuario=usuario, role=role)
                existing_user.add(ukey)
                created += 1
                continue
            nome = (r.get("usuario") or "").strip()[:200]
            if not nome:
                continue  # sem identidade alguma (nem usuário nem nome) → não cria
            nkey = (sol_id, nome, role)
            if nkey in existing_nome:
                continue
            Participation.objects.create(solicitacao_id=sol_id, guest_nome=nome, role=role)
            existing_nome.add(nkey)
            created += 1
        return created

    def _apply_formacao(self, rows: list[dict[str, str]]) -> int:
        """Create-only de Formacao (filha de PlanoFormacoes). Plano pai via `_resolve_plano_id`
        (municipio, projeto[, ano de data_formacao]). NK (plano_id, numero_formacao); numero fora de
        1..15 (CheckConstraint) → skip (não estoura IntegrityError na transação). modalidade fora do
        domínio → default presencial; carga_horaria vazia → default do model. Sem created_by no
        model → não exige actor."""
        mun_idx = self._municipio_index()
        existing = set(Formacao.objects.values_list("plano_id", "numero_formacao"))
        created = 0
        for r in rows:
            plano_id = self._resolve_plano_id(r, mun_idx, "data_formacao")
            numero = _parse_int(r.get("numero_formacao"))
            if plano_id is None or numero is None or not (1 <= numero <= 15):
                continue
            if (plano_id, numero) in existing:
                continue
            modalidade = (r.get("modalidade") or "").strip().lower()
            if modalidade not in ("presencial", "online"):
                modalidade = "presencial"
            ch = _parse_decimal(r.get("carga_horaria"))
            Formacao.objects.create(
                plano_id=plano_id,
                numero_formacao=numero,
                data_formacao=_parse_iso_date(r.get("data_formacao")),
                carga_horaria=ch if ch is not None else Decimal("4.00"),
                modalidade=modalidade,
            )
            existing.add((plano_id, numero))
            created += 1
        return created

    def _apply_acompanhamento(self, rows: list[dict[str, str]]) -> int:
        """Create-only de Acompanhamento (filha de PlanoFormacoes). Plano pai via `_resolve_plano_id`
        (municipio, projeto[, ano de data_acompanhamento]). NK (plano_id, tipo); tipo fora de
        {primeiro, segundo} → skip (choices, sem CheckConstraint no BD). `realizado` = default False
        (o contrato não traz sinal de realizado). Sem created_by no model → não exige actor."""
        mun_idx = self._municipio_index()
        existing = set(Acompanhamento.objects.values_list("plano_id", "tipo"))
        created = 0
        for r in rows:
            plano_id = self._resolve_plano_id(r, mun_idx, "data_acompanhamento")
            tipo = (r.get("tipo") or "").strip().lower()
            if plano_id is None or tipo not in _ACOMPANHAMENTO_TIPOS:
                continue
            if (plano_id, tipo) in existing:
                continue
            Acompanhamento.objects.create(
                plano_id=plano_id,
                tipo=tipo,
                data_acompanhamento=_parse_iso_date(r.get("data_acompanhamento")),
            )
            existing.add((plano_id, tipo))
            created += 1
        return created

    def _apply_prova(self, rows: list[dict[str, str]]) -> int:
        """Create-only de Prova (filha de PlanoFormacoes). Plano pai via `_resolve_plano_id`
        (municipio, projeto[, ano de data_prova]). NK (plano_id, numero_prova); numero fora de 1..3
        (CheckConstraint) → skip. `marcado` (sempre 'true' na fonte) → `realizada`. data_prova vazia
        é comum (nullable). Sem created_by no model → não exige actor."""
        mun_idx = self._municipio_index()
        existing = set(Prova.objects.values_list("plano_id", "numero_prova"))
        created = 0
        for r in rows:
            plano_id = self._resolve_plano_id(r, mun_idx, "data_prova")
            numero = _parse_int(r.get("numero_prova"))
            if plano_id is None or numero is None or not (1 <= numero <= 3):
                continue
            if (plano_id, numero) in existing:
                continue
            Prova.objects.create(
                plano_id=plano_id,
                numero_prova=numero,
                data_prova=_parse_iso_date(r.get("data_prova")),
                realizada=_to_bool(r.get("marcado")),
            )
            existing.add((plano_id, numero))
            created += 1
        return created

    def _apply_availability_block(self, rows: list[dict[str, str]]) -> int:
        """Create-only de AvailabilityBlock (bloco de disponibilidade de formador). usuario por CPF
        (FK PROTECT NOT NULL → sem match = skip). inicio/fim datetime LOCAL Fortaleza → UTC (RD-06);
        fim ≤ inicio viola a CheckConstraint → skip. tipo ∈ {T, P} → skip fora disso. `motivo` sem
        origem na planilha → ''. status default 'aprovado' (save auto-aprova). created_by = actor.
        NK existence-based (usuario, inicio, fim, tipo)."""
        actor = self._require_actor("availability_block")
        cpf_idx = self._usuario_cpf_index()
        existing = set(AvailabilityBlock.objects.values_list("usuario_id", "inicio", "fim", "tipo"))
        created = 0
        for r in rows:
            usr_id = cpf_idx.get(normalize_cpf_digits(r.get("usuario_cpf") or ""))
            tipo = (r.get("tipo") or "").strip().upper()
            inicio = _parse_local_datetime(r.get("inicio"))
            fim = _parse_local_datetime(r.get("fim"))
            if usr_id is None or tipo not in ("T", "P") or inicio is None or fim is None or fim <= inicio:
                continue
            nk = (usr_id, inicio, fim, tipo)
            if nk in existing:
                continue
            AvailabilityBlock.objects.create(
                usuario_id=usr_id,
                inicio=inicio,
                fim=fim,
                tipo=tipo,
                motivo=(r.get("motivo") or "").strip()[:255],
                created_by=actor,
            )
            existing.add(nk)
            created += 1
        return created

    def _apply_deslocamento(self, rows: list[dict[str, str]]) -> int:
        """Create-only de Deslocamento (formador entre municípios, origem/destino TEXTO). usuario por
        CPF (FK PROTECT NOT NULL → sem match = skip); start/end obrigatórios. Idempotência por
        `external_hash` (SHA1 ADR-012) sobre (usuario, start, end, origem, destino, observacao) —
        observacao ENTRA (RELAY 31). Sem created_by no model → não exige actor."""
        cpf_idx = self._usuario_cpf_index()
        existing = set(Deslocamento.objects.exclude(external_hash__isnull=True).values_list("external_hash", flat=True))
        created = 0
        for r in rows:
            fields = self._deslocamento_fields(r, cpf_idx)
            if fields is None:
                continue
            usr_id, origem, destino, start, end, obs, h = fields
            if h in existing:
                continue
            Deslocamento.objects.create(
                usuario_id=usr_id,
                origem=origem,
                destino=destino,
                start_date=start,
                end_date=end,
                observacao=obs,
                external_hash=h,
            )
            existing.add(h)
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
            fluxo = (r.get("fluxo") or "").strip().upper()
            if fluxo not in _PROJETO_FLUXOS:
                continue  # fluxo ausente → não cria (PA-01: default NAO_SUPER faria SUPER auto-aprovar)
            pg_raw = (r.get("projeto_geral") or "").strip()
            pg_id = pg_idx.get(_norm(pg_raw or nome))  # declarado, ou homônimo se vazio
            if pg_id is None:
                if pg_raw:
                    continue  # PG DECLARADO mas desconhecido → não cria (nunca família errada)
                # #1897: projeto_geral vazio = rótulo família-vazia intencional → cria NULL, SALVO se
                # o projeto tem dat_registro/dat_compra (aí a família importa p/ nr_codigos → barra).
                if _norm(nome) in self._projetos_com_dat_uso():
                    continue  # would_reject (familia_vazia_com_dat)
                # pg_id fica None → Projeto.projeto_geral NULL (rótulo)
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
