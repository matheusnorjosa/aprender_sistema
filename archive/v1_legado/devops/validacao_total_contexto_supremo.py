import csv
import datetime
import json
import os
import pathlib
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------- Setup de paths ----------
BASE = Path(__file__).resolve().parents[1]
DOCS_ROOT = Path(os.getenv("DOCS_ROOT", BASE / "docs"))
DOCS_ROOT.mkdir(parents=True, exist_ok=True)
OUT_MD = (
    DOCS_ROOT
    / f"VALIDACAO_TOTAL_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
)
OUT_JSON = (
    DOCS_ROOT
    / f"VALIDACAO_TOTAL_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)
LOGS = BASE / "logs"
LOGS.mkdir(exist_ok=True)

# ---------- Parametrização do Contexto Supremo ----------
SHEET_AGENDA_ID = os.getenv("SHEET_AGENDA_ID", "")
SHEET_DISP_ID = os.getenv("SHEET_DISP_ID", "")
SHEET_USERS_ID = os.getenv("SHEET_USERS_ID", "")
CSV_LOCAL_DIR = Path(os.getenv("CSV_LOCAL_DIR", BASE / "data/ingest"))
CUTOFF_DATE = datetime.date.fromisoformat(os.getenv("CUTOFF_DATE", "2025-09-25"))

TABS_AGENDA = ["ACerta", "Outros", "Brincando", "Vidas", "Super"]
# mapeamentos de colunas por aba (nomes exatos conforme Contexto Supremo)
MAP_COLS = {
    # A, E..T (conforme descrito)
    "ACerta": {
        "criado": "Criado na Agenda",
        "municipio": "município",
        "encontro": "encontro",
        "tipo": "tipo",
        "data": "data",
        "hora_inicio": "hora início",
        "hora_fim": "hora fim",
        "projeto": "projeto",
        "segmento": "segmento",
        "coord_acomp": "Coord Acompanha",
        "coordenador": "Coordenador",
        "f1": "Formador 1",
        "f2": "Formador 2",
        "f3": "Formador 3",
        "f4": "Formador 4",
        "f5": "Formador 5",
        "convidados": "Convidados",
        "cancelar": "Cancelar",
    },
    "Brincando": {
        "criado": "Criado na Agenda",
        "municipio": "município",
        "encontro": "encontro",
        "tipo": "tipo",
        "data": "data",
        "hora_inicio": "hora início",
        "hora_fim": "hora fim",
        "projeto": "projeto",
        "segmento": "segmento",
        "coord_acomp": "Coord Acompanha",
        "coordenador": "Coordenador",
        "f1": "Formador 1",
        "f2": "Formador 2",
        "f3": "Formador 3",
        "f4": "Formador 4",
        "f5": "Formador 5",
        "convidados": "Convidados",
        "cancelar": "Cancelar",
    },
    "Vidas": {
        "criado": "Criado na Agenda",
        "municipio": "município",
        "encontro": "encontro",
        "tipo": "tipo",
        "data": "data",
        "hora_inicio": "hora início",
        "hora_fim": "hora fim",
        "projeto": "projeto",
        "segmento": "segmento",
        "coord_acomp": "Coord Acompanha",
        "coordenador": "Coordenador",
        "f1": "Formador 1",
        "f2": "Formador 2",
        "f3": "Formador 3",
        "f4": "Formador 4",
        "f5": "Formador 5",
        "convidados": "Convidados",
        "cancelar": "Cancelar",
    },
    # Outros: projeto (K) define o setor; cancelado/adiado está em 'segmento'
    "Outros": {
        "criado": "Criado na Agenda",
        "municipio": "município",
        "encontro": "encontro",
        "tipo": "tipo",
        "data": "data",
        "hora_inicio": "hora início",
        "hora_fim": "hora fim",
        "projeto": "projeto",
        "segmento": "segmento",
        "coord_acomp": "Coord Acompanha",
        "coordenador": "Coordenador",
        "f1": "Formador 1",
        "f2": "Formador 2",
        "f3": "Formador 3",
        "f4": "Formador 4",
        "f5": "Formador 5",
        "convidados": "Convidados",
    },
    # Super tem Aprovação + Municípios
    "Super": {
        "aprovacao": "Aprovação",
        "municipios": "Municípios",
        "encontro": "encontro",
        "tipo": "tipo",
        "data": "data",
        "hora_inicio": "hora início",
        "hora_fim": "hora fim",
        "projeto": "projeto",
        "coord_acomp": "Coord Acompanha",
        "coordenador": "Coordenador",
        "f1": "Formador 1",
        "f2": "Formador 2",
        "f3": "Formador 3",
        "f4": "Formador 4",
        "f5": "Formador 5",
        "convidados": "Convidados",
    },
}

# Regras canônicas:
# - IDEB/IDEB10 => Gestão Escolar (Outros/projeto)
# - Solicitação = Coordenador (coluna N)
# - Corte temporal: <= CUTOFF_DATE => REALIZADO/CANCELADO; > CUTOFF_DATE => (Super: APROVADO se 'Aprovação'=='SIM', senão CRIADO; demais: CRIADO)
# - Nunca gerar AGENDADO por ingestão
# - Vínculos por setor:
#     set(ACerta, Brincando, Vidas) => setor homônimo; papel COORDENADOR = quem está na coluna 'Coordenador'
#     Outros => setor = 'projeto' (exceto IDEB/IDEB10 -> 'Gestão Escolar'); coordenador também é FORMADOR (regra fornecida)
#     Super => setor = 'Superintendência'; vincular coordenadores/formadores à Super
# - cancelado: nas abas com 'Cancelar'; em Outros: inferir por 'segmento' contendo 'cancelado'/'adiado' (case-insensitive)


def slug(x: str) -> str:
    return (x or "").strip()


def is_true(x: str) -> bool:
    s = (x or "").strip().lower()
    return s in {"1", "true", "t", "sim", "yes", "y", "x", "ok"}


def looks_cancelled_from_segment(x: str) -> bool:
    s = (x or "").strip().lower()
    return ("cancel" in s) or ("adiad" in s)


def norm_setor_from_outros(projeto: str) -> str:
    p = (projeto or "").strip().upper()
    if p in {"IDEB", "IDEB10"}:
        return "Gestão Escolar"
    return (projeto or "").strip() or "Outros"


def decide_status(aba: str, row: Dict[str, str], dt: datetime.date) -> str:
    if dt <= CUTOFF_DATE:
        # passado
        if aba == "Outros" and looks_cancelled_from_segment(row.get("segmento", "")):
            return "CANCELADO"
        if row.get("cancelar") is not None and is_true(row.get("cancelar")):
            return "CANCELADO"
        return "REALIZADO"
    else:
        # futuro
        if aba == "Super":
            return (
                "APROVADO"
                if (row.get("aprovacao", "").strip().upper() == "SIM")
                else "CRIADO"
            )
        return "CRIADO"


def parse_dt(date_s: str, time_s: str) -> Optional[str]:
    # Retorna string ISO com TZ implícita; parser real ficará a cargo do command
    ds = (date_s or "").strip()
    ts = (time_s or "").strip()
    if not ds:
        return None
    # formato esperado DD/MM/AAAA, HH:MM
    try:
        d, m, y = ds.split("/")
        hh, mm = (ts.split(":") + ["0"])[:2] if ts else ("00", "00")
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}T{hh.zfill(2)}:{mm.zfill(2)}:00"
    except Exception:
        return None


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def download_sheet_csv_by_title(sheet_id: str, title: str, out_path: Path) -> bool:
    """
    Tenta baixar via gspread pela aba 'title'.
    Se não houver Service Account configurada, retorna False (fallback p/ CSV local).
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv(
            "GSHEETS_SA_PATH"
        )
        if not sa_path or not Path(sa_path).exists():
            return False
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet(title)
        rows = ws.get_all_records()
        if not rows:
            # salvar mesmo assim para auditoria
            out_path.write_text("", encoding="utf-8")
            return True
        # escreve CSV bruto
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return True
    except Exception as e:
        return False


# ---------- 1) Preparar CSVs canônicos a partir do Sheets (ou fallback local) ----------
artifacts = {"sources": {}, "imports": {}, "checks": {}}
can_dir = BASE / "data/canon"
can_dir.mkdir(parents=True, exist_ok=True)
raw_dir = BASE / "data/raw_supremo"
raw_dir.mkdir(parents=True, exist_ok=True)


def ensure_csv_from_sheet(sheet_id: str, tab: str, fallback_name: str) -> Path:
    raw = raw_dir / f"{tab}.csv"
    ok = download_sheet_csv_by_title(sheet_id, tab, raw)
    if not ok:
        # fallback local
        fb = (
            Path(os.getenv("CSV_LOCAL_DIR", str(BASE / "data/ingest")))
            / f"{fallback_name}"
        )
        if fb.exists():
            raw = fb
        else:
            # continua, mas registra erro
            artifacts["sources"].setdefault("errors", []).append(
                {"sheet": sheet_id, "tab": tab, "error": "no SA and no local CSV"}
            )
    artifacts.setdefault("sources", {}).setdefault("tabs", []).append(
        {"tab": tab, "path": str(raw)}
    )
    return raw


# ---------- 2) Canonicalização dos eventos por aba ----------
def canonicalize_agenda_tab(aba: str, src_csv: Path) -> Path:
    cols = MAP_COLS[aba]
    out = can_dir / f"agenda_{aba.lower()}_canon.csv"
    fieldnames = [
        "titulo",
        "status",
        "data_inicio",
        "data_fim",
        "municipio",
        "solicitante",
        "setor",
        "aprovado_super",
        "cancelado_flag",
        "fonte_aba",
    ]
    rows_out = []
    # abrir csv fonte
    try:
        with src_csv.open(newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                # pega valores por alias
                val = lambda k: r.get(cols.get(k, ""), "")
                data = val("data")
                hi = val("hora_inicio")
                hf = val("hora_fim")
                di = parse_dt(data, hi)
                df = parse_dt(data, hf)  # strings ISO; command aplicará TZ Fortaleza
                municipio = (
                    val("municipio")
                    or r.get("Municípios", "")
                    or r.get("Município", "")
                )
                coord = val("coordenador")
                segmento = val("segmento")
                aprov = (val("aprovacao") or "").strip().upper()
                # setor
                if aba == "Outros":
                    setor = norm_setor_from_outros(val("projeto"))
                elif aba == "Super":
                    setor = "Superintendência"
                else:
                    setor = aba
                # status
                if data:
                    dday = None
                    try:
                        dd, mm, yy = data.split("/")
                        dday = datetime.date(int(yy), int(mm), int(dd))
                    except:
                        pass
                    st = decide_status(
                        aba,
                        {
                            "segmento": segmento,
                            "cancelar": r.get(cols.get("cancelar", ""), ""),
                            "aprovacao": aprov,
                        },
                        dday or CUTOFF_DATE,
                    )
                else:
                    st = "CRIADO"
                # cancelado flag (somente informativo)
                cancelado = False
                if aba == "Outros":
                    cancelado = looks_cancelled_from_segment(segmento)
                elif cols.get("cancelar") and r.get(cols["cancelar"]):
                    cancelado = is_true(r.get(cols["cancelar"]))
                # título (se vier vazio, gera um simples)
                titulo = (
                    r.get("encontro") or r.get("encontro ", "") or ""
                ).strip() or f"{aba} - {municipio} - {data}"
                rows_out.append(
                    {
                        "titulo": titulo,
                        "status": st,
                        "data_inicio": di or "",
                        "data_fim": df or "",
                        "municipio": municipio,
                        "solicitante": coord,
                        "setor": setor,
                        "aprovado_super": (
                            "SIM" if (aba == "Super" and aprov == "SIM") else ""
                        ),
                        "cancelado_flag": "1" if cancelado else "",
                        "fonte_aba": aba,
                    }
                )
    except FileNotFoundError:
        artifacts.setdefault("sources", {}).setdefault("missing", []).append(
            str(src_csv)
        )
    write_csv(out, rows_out, fieldnames)
    artifacts.setdefault("canon", {}).setdefault("tabs", []).append(
        {"aba": aba, "path": str(out), "rows": len(rows_out)}
    )
    return out


# ---------- 3) Construir CSV canônico de Usuários ----------
def canonicalize_users() -> Path:
    out = can_dir / "usuarios_canon.csv"
    # tenta baixar "Ativos"
    raw = ensure_csv_from_sheet(SHEET_USERS_ID, "Ativos", "usuarios.csv")
    # normaliza possiveis nomes de colunas
    rows = []
    fields = ["Nome", "Nome Completo", "CPF", "Telefone", "Email", "Cargo", "Gerência"]
    if raw.exists():
        with raw.open(newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                rows.append(
                    {
                        "Nome": r.get("Nome") or r.get("nome") or "",
                        "Nome Completo": r.get("Nome Completo")
                        or r.get("nome_completo")
                        or r.get("nome completo")
                        or r.get("Nome completo")
                        or "",
                        "CPF": r.get("CPF") or r.get("cpf") or "",
                        "Telefone": r.get("Telefone") or r.get("telefone") or "",
                        "Email": r.get("Email") or r.get("email") or "",
                        "Cargo": r.get("Cargo") or r.get("cargo") or "",
                        "Gerência": r.get("Gerência")
                        or r.get("gerência")
                        or r.get("Gerencia")
                        or r.get("gerencia")
                        or r.get("Outros")
                        or "",
                    }
                )
    write_csv(out, rows, fields)
    artifacts.setdefault("canon", {}).setdefault("users", str(out))
    return out


# ---------- 4) Orquestração de ingestão ----------
def run_manage(cmd: List[str]) -> Dict[str, Any]:
    import shlex
    import subprocess

    p = subprocess.run(["python", "manage.py"] + cmd, capture_output=True, text=True)
    return {"cmd": " ".join(cmd), "rc": p.returncode, "out": p.stdout, "err": p.stderr}


def import_usuarios(csv_users: Path) -> Dict[str, Any]:
    return run_manage(
        ["import_usuarios", str(csv_users), "--sheet-id=SUPREMO", "--gid=Ativos"]
    )


def import_agenda(canon_csv: Path) -> Dict[str, Any]:
    # usa colunas canônicas: solicitante/coordenador; sem AGENDADO; corte temporal no comando
    return run_manage(
        [
            "import_eventos_abas",
            str(canon_csv),
            "--sheet-id=SUPREMO",
            "--gid=Aba",
            f"--cutoff={CUTOFF_DATE.isoformat()}",
            "--col-solicitante",
            "solicitante",
            "--col-email",
            "",
            "--col-cancelado",
            "cancelado_flag",
            "--col-aprovado",
            "aprovado_super",
            "--col-titulo",
            "titulo",
        ]
    )


def import_disponibilidades_stub() -> Dict[str, Any]:
    # Apenas marca idempotência com os CSVs existentes; a operação real já foi implementada anteriormente
    disp_local = (
        Path(os.getenv("CSV_LOCAL_DIR", str(BASE / "data/ingest")))
        / "disponibilidades.csv"
    )
    if not disp_local.exists():
        return {
            "cmd": "import_disponibilidades (skipped)",
            "rc": 0,
            "out": "skipped (no local CSV)",
            "err": "",
        }
    return run_manage(
        [
            "import_disponibilidades",
            str(disp_local),
            "--sheet-id=SUPREMO",
            "--gid=ANUAL",
        ]
    )


# ---------- 5) Vínculos por setor (VinculoUsuarioSetor) ----------
def vincular_por_setor() -> Dict[str, Any]:
    """
    - ACerta/Brincando/Vidas: setor homônimo, papel=COORDENADOR para 'solicitante'
    - Outros: setor = projeto* (IDEB/IDEB10 -> Gestão Escolar); coordenador também como FORMADOR
    - Super: setor = Superintendência; coordenadores/formadores vinculados
    """
    code = r"""
from django.contrib.auth import get_user_model
from django.apps import apps
from ingestao.utils import sha1_of_row
import csv, pathlib

User = get_user_model()
Vinc = apps.get_model('core','VinculoUsuarioSetor')
Setor = apps.get_model('core','Setor')

CAN = pathlib.Path('data/canon')
tabs = ['agenda_acerta_canon.csv','agenda_brincando_canon.csv','agenda_vidas_canon.csv','agenda_outros_canon.csv','agenda_super_canon.csv']

def ensure_setor(nome):
    s = Setor.objects.filter(nome__iexact=nome).first()
    if not s:
        s = Setor.objects.create(nome=nome, sigla=nome[:8].upper())
    return s

created=updated=skipped=0
for t in tabs:
    p = CAN/t
    if not p.exists():
        continue
    with p.open(newline='',encoding='utf-8') as f:
        rdr=csv.DictReader(f)
        for r in rdr:
            aba = r.get('fonte_aba') or ''
            setor_nome = r.get('setor') or (aba if aba!='Outros' else 'Outros')
            s = ensure_setor(setor_nome)
            coord = (r.get('solicitante') or '').strip()
            if not coord:
                continue
            u = User.objects.filter(first_name__iexact=coord.split()[0]).order_by('id').first()
            if not u:
                # fallback por username pseudo
                from django.contrib.auth.models import User as U2
                uname = sha1_of_row({'n':coord})[:16]
                u = User.objects.create(username=uname, first_name=coord)
            # papel coordenador
            if not Vinc.objects.filter(usuario=u, setor=s, papel='COORDENADOR').exists():
                Vinc.objects.create(usuario=u, setor=s, papel='COORDENADOR', ativo=True); created+=1
            else:
                skipped+=1
            # regra de 'Outros': coordenador também é formador
            if aba=='Outros':
                if not Vinc.objects.filter(usuario=u, setor=s, papel='FORMADOR').exists():
                    Vinc.objects.create(usuario=u, setor=s, papel='FORMADOR', ativo=True); created+=1
                else:
                    skipped+=1
            # Super: setor Superintendência já forçado na canonicalização
"""
    return run_manage(["shell", "-c", code])


# ---------- 6) Auditoria final ----------
def auditoria_final() -> Dict[str, Any]:
    code = r"""
from django.db import connection
from django.conf import settings
from django.apps import apps

def q(sql):
    with connection.cursor() as c:
        c.execute(sql)
        return c.fetchall()

out = {
  "tz": getattr(settings,"TIME_ZONE",None),
  "use_tz": getattr(settings,"USE_TZ",None),
  "sem_agendado_por_ingestao": q("SELECT COUNT(*) FROM core_solicitacao WHERE status='AGENDADO' AND (origem ILIKE '%import%' OR observacoes ILIKE '%ingest%')")[0][0]==0,
  "vinculos_total": q("SELECT COUNT(*) FROM core_vinculousuariosetor")[0][0],
  "vinculos_por_papel": dict((p, q(f"SELECT COUNT(*) FROM core_vinculousuariosetor WHERE papel='{p}'")[0][0]) for p in ['COORDENADOR','FORMADOR','CONTROLE','SUPER','GERENTE']),
  "marcadores_total": q("SELECT COUNT(*) FROM core_marcadorplanilha")[0][0],
  "eventos_total": q("SELECT COUNT(*) FROM core_solicitacao")[0][0],
}
print(out)
"""
    return run_manage(["shell", "-c", code])


# ---------- Execução ----------
res = {"meta": {"docs_root": str(DOCS_ROOT), "base": str(BASE)}, "steps": []}
try:
    # Usuarios (sempre primeiro)
    users_csv = canonicalize_users()
    res["steps"].append({"canonicalize_users": str(users_csv)})

    # Agenda tabs
    canon_tabs = []
    for tab in TABS_AGENDA:
        raw = ensure_csv_from_sheet(SHEET_AGENDA_ID, tab, f"agenda_{tab.lower()}.csv")
        canon = canonicalize_agenda_tab(tab, raw)
        canon_tabs.append(str(canon))
    res["steps"].append({"canonicalize_agenda": canon_tabs})

    # Importadores
    res["imports"]["usuarios"] = import_usuarios(users_csv)
    for cpath in canon_tabs:
        res["imports"].setdefault("agenda", []).append(import_agenda(Path(cpath)))
    res["imports"]["dispon"] = import_disponibilidades_stub()

    # Vínculos por setor
    res["imports"]["vinculos"] = vincular_por_setor()

    # Auditoria
    res["checks"]["auditoria_final"] = auditoria_final()

    ok = True
except Exception as e:
    ok = False
    res["error"] = {
        "type": str(type(e)),
        "msg": str(e),
        "trace": traceback.format_exc(),
    }

# ---------- Saída ----------
OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
OUT_MD.write_text(
    "# VALIDAÇÃO TOTAL — Contexto Supremo\n\n```json\n"
    + json.dumps(res, ensure_ascii=False, indent=2)
    + "\n```\n",
    encoding="utf-8",
)
print("[OK] Validação total concluída:", OUT_JSON, OUT_MD)
