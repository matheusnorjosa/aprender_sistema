"""
Comando de importação de disponibilidades para STAGING.
Importa ANUAL, DESLOCAMENTO e Bloqueios direto do Google Sheets.
Ignora MENSAL.
"""

import csv
import datetime
import io
import re
import unicodedata
import urllib.request
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from backend.config.sheets_config import (
    ABAS_DISPONIBILIDADE,
    DISPONIBILIDADE_2025_ID,
    csv_url,
)


def _norm_key(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", "", s.strip().lower())
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


MESES = {
    "jan": "1",
    "janeiro": "1",
    "fev": "2",
    "fevereiro": "2",
    "mar": "3",
    "marco": "3",
    "abr": "4",
    "abril": "4",
    "mai": "5",
    "maio": "5",
    "jun": "6",
    "junho": "6",
    "jul": "7",
    "julho": "7",
    "ago": "8",
    "agosto": "8",
    "set": "9",
    "setembro": "9",
    "out": "10",
    "outubro": "10",
    "nov": "11",
    "novembro": "11",
    "dez": "12",
    "dezembro": "12",
}


def _preprocess_csv(raw: bytes) -> str:
    """Pula banners até achar cabeçalho plausível."""
    txt = None
    for enc in ("utf-8", "latin1", "ascii"):
        try:
            txt = raw.decode(enc, "ignore")
            break
        except:
            pass
    if txt is None:
        txt = raw.decode("utf-8", "ignore")
    buf = io.StringIO(txt)
    for _ in range(200):
        line = buf.readline()
        if not line:
            break
        try:
            cols = next(csv.reader([line]))
            cols_norm = [_norm_key(c) for c in cols]
            if len(cols_norm) >= 3:
                # heurísticas para 3 tipos
                meses_set = set(MESES.keys())
                if ({"formador", "nome"} & set(cols_norm)) and (
                    meses_set & set(cols_norm)
                ):
                    return line + buf.read()  # ANUAL - retorna header + resto
                if ("origem" in cols_norm or "destino" in cols_norm) and (
                    "data" in cols_norm or "datai" in cols_norm or "datav" in cols_norm
                ):
                    return line + buf.read()  # DESLOC
                if ({"inicio", "dataini", "ini"} & set(cols_norm)) and (
                    {"fim", "datafim"} & set(cols_norm)
                ):
                    return line + buf.read()  # BLOQ
            # se 1 coluna e parece banner, ignora
            if len(cols_norm) == 1 and cols_norm[0] in {
                "emmanutencao",
                "manutencao",
                "legenda",
                "cabecalho",
            }:
                continue
        except:
            pass
    return txt  # se não achar header, retorna tudo


def _fetch(gid: str) -> list[dict]:
    """Baixa CSV do Google Sheets e retorna lista de dicionários."""
    u = csv_url(DISPONIBILIDADE_2025_ID, gid)
    raw = urllib.request.urlopen(u).read()
    cleaned = _preprocess_csv(raw)
    reader = csv.DictReader(io.StringIO(cleaned))
    return list(reader)


def _tokenize_nome(nome: str):
    import re

    tokens = [t for t in re.split(r"[\s,;]+", (nome or "").strip()) if len(t) >= 2]
    return [t.lower() for t in tokens]


def _find_usuario(nome: str, email: str | None = None):
    """Busca usuário por email ou nome."""
    from django.db.models import Q

    U = apps.get_model("core", "Usuario")
    # 1) e-mail exato
    if email:
        u = U.objects.filter(email__iexact=email.strip()).first()
        if u:
            return u
    # 2) nome exato (campo nome/first_name)
    if nome:
        n = re.sub(r"\s+", " ", nome).strip()
        u = U.objects.filter(first_name__iexact=n).first()
        if u:
            return u
        # 3) fuzzy simples: até 3 tokens mais longos e interseção
        toks = sorted(_tokenize_nome(n), key=len, reverse=True)[:3]
        if toks:
            q = Q()
            for t in toks[:2]:
                q &= Q(first_name__icontains=t) | Q(last_name__icontains=t)
            cands = list(U.objects.filter(q)[:10])

            def score(u):
                base = getattr(u, "first_name", "") + " " + getattr(u, "last_name", "")
                utoks = set(_tokenize_nome(base))
                return len(utoks & set(toks)) / max(1, len(toks))

            if cands:
                best = max(cands, key=score)
                if score(best) >= 0.5:
                    return best
    return None


def _parse_date_pt(s):
    """Parse data PT (dd/mm/yyyy ou yyyy-mm-dd)."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    # tentar serial do Sheets/Excel
    try:
        if re.fullmatch(r"\d{4,6}(\.\d+)?", s):
            serial_base = datetime.date(1899, 12, 30)  # Excel/Sheets base
            days = int(float(s))
            return serial_base + datetime.timedelta(days=days)
    except:
        pass
    # formatos comuns
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except:
            pass
    # formato curto dd/mm (assume ano corrente 2025)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", s)
    if m:
        try:
            dia, mes = int(m.group(1)), int(m.group(2))
            return datetime.date(2025, mes, dia)
        except:
            pass
    # pegar dd/mm/yyyy perdido dentro de strings longas
    m = re.search(r"(\d{2}/\d{2}/\d{4})", s)
    if m:
        try:
            return datetime.datetime.strptime(m.group(1), "%d/%m/%Y").date()
        except:
            pass
    return None


def _parse_dt_pt(data_s, hora_s):
    """Parse datetime PT combinando data + hora."""
    d = _parse_date_pt(data_s)
    if not d:
        return None
    t = None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.datetime.strptime((hora_s or "00:00"), fmt).time()
            break
        except:
            pass
    dt = datetime.datetime.combine(d, t or datetime.time(0, 0))
    return timezone.make_aware(dt)


class Command(BaseCommand):
    help = "Importa Disponibilidades (ANUAL/DESLOCAMENTO/Bloqueios) direto do Google Sheets para tabelas de STAGING. Ignora MENSAL."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="source", default="sheets")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **opts):
        dry = opts.get("dry_run", False)
        verbose = opts.get("verbose", False)

        # modelos
        StgAnual = apps.get_model("core", "StagingDisponAnual")
        StgDesl = apps.get_model("core", "StagingDeslocamento")
        StgBloq = apps.get_model("core", "StagingBloqueio")

        # 1) ANUAL
        rows = _fetch(ABAS_DISPONIBILIDADE["ANUAL"])
        created_a = 0
        bulk_a = []
        for r in rows:
            rn = {_norm_key(k): (v or "").strip() for k, v in r.items()}
            nome = rn.get("formador") or rn.get("nome") or ""
            email = rn.get("email") or rn.get("email") or None
            ano = rn.get("ano") or "2025"
            try:
                ano = int(str(ano).strip() or "2025")
            except:
                ano = 2025
            usuario = _find_usuario(nome, email)
            for k, v in rn.items():
                mk = k
                if mk in MESES:
                    mes = int(MESES[mk])
                    try:
                        horas = Decimal(str(v).replace(",", ".").strip() or "0")
                    except:
                        horas = Decimal(0)
                    obj = StgAnual(
                        usuario=usuario,
                        nome_formador=nome,
                        ano=ano,
                        mes=mes,
                        horas=horas,
                    )
                    bulk_a.append(obj)
        if dry:
            created_a = len(bulk_a)
        else:
            with transaction.atomic():
                created_a = len(
                    StgAnual.objects.bulk_create(bulk_a, ignore_conflicts=True)
                )
        if verbose:
            self.stdout.write(f"[ANUAL] staged: {created_a}")

        # 2) DESLOCAMENTO
        rows = _fetch(ABAS_DISPONIBILIDADE["DESLOCAMENTO"])
        bulk_d = []
        for r in rows:
            rn = {_norm_key(k): (v or "").strip() for k, v in r.items()}
            # buscar nome em múltiplas pessoas (Pessoa 1..6)
            nome = rn.get("formador") or rn.get("nome") or rn.get("pessoa1") or ""
            email = rn.get("email") or None
            usuario = _find_usuario(nome, email)
            origem = rn.get("origem") or rn.get("cidadeorigem") or ""
            destino = rn.get("destino") or rn.get("cidadedestino") or ""
            cand_keys = [
                k
                for k in rn.keys()
                if re.search(r"(^|_)data($|_|)|dia|data_?(ida|volta)", k)
            ]
            vals = [rn.get(k) for k in cand_keys if rn.get(k)]
            data = None
            for v in vals:
                data = _parse_date_pt(v)
                if data:
                    break
            obs = rn.get("observacao") or rn.get("obs") or ""
            if nome or origem or destino:  # só adiciona se tiver algo
                bulk_d.append(
                    StgDesl(
                        usuario=usuario,
                        nome_formador=nome,
                        data=data,
                        origem=origem,
                        destino=destino,
                        observacao=obs,
                    )
                )
        if dry:
            created_d = len(bulk_d)
        else:
            with transaction.atomic():
                created_d = len(
                    StgDesl.objects.bulk_create(bulk_d, ignore_conflicts=True)
                )
        if verbose:
            self.stdout.write(f"[DESLOCAMENTO] staged: {created_d}")

        # 3) BLOQUEIOS
        rows = _fetch(ABAS_DISPONIBILIDADE["Bloqueios"])
        bulk_b = []
        for r in rows:
            rn = {_norm_key(k): (v or "").strip() for k, v in r.items()}
            nome = rn.get("formador") or rn.get("nome") or rn.get("usuario") or ""
            email = rn.get("email") or None
            usuario = _find_usuario(nome, email)
            ini = _parse_dt_pt(
                rn.get("inicio")
                or rn.get("dataini")
                or rn.get("ini")
                or rn.get("inicioem"),
                rn.get("horaini")
                or rn.get("horai")
                or rn.get("iniciohora")
                or rn.get("hora")
                or None,
            )
            fim = _parse_dt_pt(
                rn.get("fim") or rn.get("datafim") or rn.get("final"),
                rn.get("horafim") or rn.get("fimhora") or rn.get("hora") or None,
            )
            motivo = rn.get("motivo") or rn.get("justificativa") or rn.get("tipo") or ""
            if nome:  # só adiciona se tiver nome
                bulk_b.append(
                    StgBloq(
                        usuario=usuario,
                        nome_formador=nome,
                        inicio=ini,
                        fim=fim,
                        motivo=motivo,
                    )
                )
        if dry:
            created_b = len(bulk_b)
        else:
            with transaction.atomic():
                created_b = len(
                    StgBloq.objects.bulk_create(bulk_b, ignore_conflicts=True)
                )
        if verbose:
            self.stdout.write(f"[BLOQUEIOS] staged: {created_b}")

        total = (
            (created_a if not dry else len(bulk_a))
            + (created_d if not dry else len(bulk_d))
            + (created_b if not dry else len(bulk_b))
        )
        self.stdout.write(
            self.style.SUCCESS(f"[TOTAL] {'dry-run' if dry else 'created'}: {total}")
        )
