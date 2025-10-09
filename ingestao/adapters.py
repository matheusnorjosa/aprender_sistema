# ingestao/adapters.py
import csv
import datetime
import hashlib
import io
import re
import unicodedata
import urllib.request
from typing import Dict, Iterable, List, Optional

from backend.config.sheets_config import csv_url


def _norm_key(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", "_", s.strip().lower())
    return re.sub(r"[^a-z0-9_]", "", s)


def _pick(row_norm: Dict[str, str], *cands: str) -> Optional[str]:
    for c in cands:
        k = _norm_key(c)
        v = row_norm.get(k, "")
        if str(v).strip():
            return str(v).strip()
    return None


def _boolish(v: Optional[str]) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() in {
        "1",
        "true",
        "t",
        "yes",
        "y",
        "sim",
        "x",
        "ok",
        "checked",
        "marcado",
    }


def _parse_date_pt(s: Optional[str]) -> Optional[datetime.date]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except:
            pass
    return None


def _parse_time_pt(s: Optional[str]) -> Optional[datetime.time]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt).time()
        except:
            pass
    return None


def normalize_row_generic(row: Dict[str, str]) -> Dict[str, str]:
    return {_norm_key(k): (v if v is not None else "") for k, v in row.items()}


def collect_formadores(row_norm: Dict[str, str]) -> List[str]:
    formadores = []
    for k, v in row_norm.items():
        if re.match(r"^formador_?\d+$", k) and str(v).strip():
            formadores.append(str(v).strip())
    if not formadores:
        coord = _pick(row_norm, "Coordenador")
        if coord:
            formadores.append(coord)
    seen, out = set(), []
    for f in formadores:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


class ParsedEvento:
    def __init__(
        self,
        origem_aba: str,
        municipio: str,
        data: Optional[datetime.date],
        hora_ini: Optional[datetime.time],
        hora_fim: Optional[datetime.time],
        projeto: Optional[str],
        tipo: Optional[str],
        coordenador: Optional[str],
        formadores: List[str],
        aprovado: bool,
        cancelado: bool,
        encontro: Optional[str],
    ):
        self.origem_aba = origem_aba
        self.municipio = municipio or ""
        self.data = data
        self.hora_ini = hora_ini
        self.hora_fim = hora_fim
        self.projeto = projeto or ""
        self.tipo = tipo or ""
        self.coordenador = coordenador or ""
        self.formadores = formadores
        self.aprovado = aprovado
        self.cancelado = cancelado
        self.encontro = encontro


def parse_row_por_aba(origem_aba: str, row: Dict[str, str]) -> Optional[ParsedEvento]:
    rn = normalize_row_generic(row)
    municipio = _pick(rn, "Município", "Municípios")
    data = _parse_date_pt(_pick(rn, "Data"))
    hora_ini = _parse_time_pt(
        _pick(rn, "Hora Início", "Hora Inicio", "Ini", "Hora Ini")
    )
    hora_fim = _parse_time_pt(
        _pick(rn, "Hora Fim", "Fim", "Hora Término", "Hora Termino")
    )
    projeto = _pick(rn, "Projeto")
    tipo = _pick(rn, "Tipo", "Tipo do Evento", "Tipo Evento")
    encontro = _pick(rn, "Encontro")
    coord = _pick(rn, "Coordenador")

    cancel_flag = _pick(rn, "Cancelar", "C ancelar", "Cancelado")
    seg = _pick(rn, "Segmento")
    if not cancel_flag and seg and any(x in seg.lower() for x in ["cancel", "adiad"]):
        cancel_flag = "1"
    cancelado = _boolish(cancel_flag)

    aprovado = False
    if origem_aba.lower() == "super":
        aprov = _pick(rn, "Aprovação", "Aprovacao")
        aprovado = str(aprov).strip().lower() == "sim"

    formadores = collect_formadores(rn)
    if not municipio or not data:
        return None
    return ParsedEvento(
        origem_aba,
        municipio,
        data,
        hora_ini,
        hora_fim,
        projeto,
        tipo,
        coord,
        formadores,
        aprovado,
        cancelado,
        encontro,
    )


class SheetsAdapter:
    """Lê direto do Google Sheets (export?format=csv&gid=...), via GET com redirects."""

    def rows(
        self, sheet_id: str, gid: str, encoding: str = "utf-8"
    ) -> Iterable[Dict[str, str]]:
        if not sheet_id or not gid:
            return []
        url = csv_url(sheet_id, gid)
        with urllib.request.urlopen(url) as r:
            raw_bytes = r.read()
        # HOTFIX: pular banners e detectar cabeçalho real
        cleaned_bytes = _preprocess_csv_text_for_disp(raw_bytes)
        data = cleaned_bytes.decode(encoding, errors="replace")
        reader = csv.DictReader(io.StringIO(data))
        for row in reader:
            yield row


class CsvFolderAdapter:
    """Lê de um arquivo CSV local."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

    def rows(
        self, csv_filename: str, encoding: str = "utf-8"
    ) -> Iterable[Dict[str, str]]:
        import os

        csv_path = os.path.join(self.base_dir, csv_filename)
        with open(csv_path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row


def _looks_like_disp_header(cols_norm):
    c = set(cols_norm)
    # ANUAL: formador + meses ou CH
    meses = {
        "jan",
        "fev",
        "mar",
        "abr",
        "mai",
        "jun",
        "jul",
        "ago",
        "set",
        "out",
        "nov",
        "dez",
    }
    if "formador" in c and (
        c & meses or {"ch", "chanual", "cargahoraria", "horas"} & c
    ):
        return "ANUAL"
    if ({"ano", "carga_horaria", "ch", "horas"} & c) and (
        "formador" in c or "nome" in c
    ):
        return "ANUAL"
    if ({"origem", "destino"} & c) and (
        "data" in c or "data_ida" in c or "data_volta" in c
    ):
        return "DESLOCAMENTO"
    if ({"inicio", "data_inicio", "ini"} & c) and ({"fim", "data_fim"} & c):
        return "BLOQUEIOS"
    if "tipo" in c and ("formador" in c or "nome" in c or "usuario" in c):
        return "DESCONHECIDO_OK"
    return None


def _skip_to_header(csv_text):
    buf = io.StringIO(csv_text)
    peek_lines = []
    for _ in range(200):
        line = buf.readline()
        if line == "":
            break
        peek_lines.append(line)
        try:
            parts = next(csv.reader([line], delimiter=","))
            cols_norm = [_norm_key(x) for x in parts]
            hdr_kind = _looks_like_disp_header(cols_norm)
            if hdr_kind and len([x for x in cols_norm if x]) >= 3:
                start = "".join(peek_lines[-1:])
                rest = buf.read()
                return hdr_kind, start + rest
            if len(parts) == 1 and _norm_key(parts[0]) in {
                "emmanutencao",
                "manutencao",
                "legenda",
                "cabecalho",
                "aguarde",
            }:
                continue
        except:
            pass
    return None, "".join(peek_lines) + buf.read()


# --- SKIP_TO_HEADER_APPLIED (hook de pré-processamento CSV) ---
def _preprocess_csv_text_for_disp(raw_bytes):
    try:
        txt = raw_bytes.decode("utf-8", "ignore")
    except Exception:
        try:
            txt = raw_bytes.decode("latin1", "ignore")
        except Exception:
            txt = raw_bytes.decode("ascii", "ignore")
    _, cleaned = _skip_to_header(txt)
    return cleaned.encode("utf-8")
