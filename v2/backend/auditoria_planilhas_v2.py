#!/usr/bin/env python3
"""
Auditoria de Dados v2 - Planilhas Aprender Sistema
Usa hash v2 (17 campos) idêntico ao PR21
Gera relatórios CSV em v2/.agents/outbox/ com análise completa
"""

import hashlib
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# Configuração
TZ = ZoneInfo("America/Fortaleza")
OUTPUT_DIR = Path("/app/.agents/outbox") if Path("/.dockerenv").exists() else Path("v2/.agents/outbox")
TEMP_DIR = Path("/tmp/auditoria_sheets")

# Google Sheets IDs
SHEETS = {
    "Acompanhamento": "1oqDA9tN-wNiFVLS3KYTFzsXKpJpvDECfeKucjwf9GKs",
    "Disponibilidade": "1C4_9Gn8gwKjgD1CgssIKaU4bacwv7XuL2QnoSVwomxU",
    "Controle": "1adUmabEnbaG6Ldf58poLZts-4Bc7zSOm0XbVuhc_dfo",
    "Usuarios": "1yPH-uCRc2XyThLU7V4pSoNYozydn1-IRRJRjubFCjXs",
}

# Arquivos locais
LOCAL_FILES = {
    "Acompanhamento": "/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx",
    "Disponibilidade": "/app/data/csv-import/Cópia de Disponibilidade _ 2025.xlsx",
    "Controle": "/app/data/csv-import/Cópia de Planilha de Controle - 2025.xlsx",
    "Usuarios": "/app/data/csv-import/Cópia de Usuários.xlsx",
}

# Mapeamento de colunas por aba (letra → campo)
COLUMN_MAP = {
    "ACerta": {
        "A": "linha_num",
        "D": "cancelar",
        "E": "municipio",
        "F": "encontro",
        "G": "tipo",
        "H": "data",
        "I": "hora_inicio",
        "J": "hora_fim",
        "K": "projeto",
        "L": "segmento",
        "M": "coord_acompanha",
        "N": "coordenador",
        "O": "formador_1",
        "P": "formador_2",
        "Q": "formador_3",
        "R": "formador_4",
        "S": "formador_5",
        "T": "convidados_emails",
    },
    "Brincando": "ACerta",  # mesmo layout
    "Vidas": {
        "A": "linha_num",
        "D": "cancelar",
        "E": "municipio",
        "F": "encontro",
        "G": "tipo",
        "H": "data",
        "I": "hora_inicio",
        "J": "hora_fim",
        "K": "projeto",
        # sem L (segmento)
        "M": "coord_acompanha",
        "N": "coordenador",
        "O": "formador_1",
        "P": "formador_2",
        "Q": "formador_3",
        "R": "formador_4",
        "S": "formador_5",
        "T": "convidados_emails",
    },
    "Outros": {
        "A": "linha_num",
        "D": "cancelar",
        "E": "municipio",
        "F": "encontro",
        "G": "tipo",
        "H": "data",
        "I": "hora_inicio",
        "J": "hora_fim",
        "K": "projeto",
        "L": "segmento",
        "M": "coord_acompanha",
        "N": "coordenador",
        "O": "formador_1",
        "P": "formador_2",
        "Q": "formador_3",
        "R": "formador_4",
        "S": "formador_5",
        "T": "convidados_emails",
    },
    "Super": {
        "A": "linha_num",
        "B": "aprovacao",
        "D": "cancelar",
        "E": "municipio",
        "F": "encontro",
        "G": "tipo",
        "H": "data",  # IMPORTANTE: Super usa H para data (não G)
        "I": "hora_inicio",
        "J": "hora_fim",
        "K": "projeto",
        "L": "coord_acompanha",
        "M": "coordenador",
        "N": "formador_1",
        "O": "formador_2",
        "P": "formador_3",
        "Q": "formador_4",
        "R": "formador_5",
        "S": "segmento",
        "T": "convidados_emails",
    },
}

# Regex para filtrar indicadores (não-pessoas)
INDICATOR_PATTERNS = [
    r"^\s*\d{1,2}\s*(º|o)?\s*ano(\s+(ling|mat|cien|ciên|ciencia|ciência)s?)?\s*$",
    r"^\s*coordenadores?\s*$",
    r"^\s*sim\s*$",
    r"^\s*n(a|ã)o\s*$",
]


def normalize_text(text: str) -> str:
    """Normaliza texto: NFKD, minúsculas, sem acentos, strip, colapsar espaços"""
    if pd.isna(text) or text == "":
        return ""
    text = str(text).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_email(email: str) -> Optional[str]:
    """Normaliza e valida e-mail"""
    if pd.isna(email) or email == "":
        return None
    email = str(email).strip().lower()
    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return email
    return None


def is_indicator_not_person(value: str) -> bool:
    """Verifica se valor é indicador (1º ano, Sim/Não, etc.) e não pessoa"""
    if pd.isna(value) or value == "":
        return True
    normalized = normalize_text(value)
    for pattern in INDICATOR_PATTERNS:
        if re.match(pattern, normalized):
            return True
    return False


def normalize_project(projeto: str) -> str:
    """Normaliza nome do projeto (IDEB/IDEB10 -> Gestão Escolar)"""
    if pd.isna(projeto) or projeto == "":
        return ""
    projeto_norm = normalize_text(projeto)

    # Variantes IDEB (aceita texto adicional como "esquenta saeb")
    if re.search(r"\bideb\s*10?\b", projeto_norm) or re.search(r"\bideb[-\s]*10\b", projeto_norm):
        return "Gestão Escolar"
    if "gestao" in projeto_norm and "escolar" in projeto_norm:
        return "Gestão Escolar"

    # Retornar original capitalizado
    return str(projeto).strip()


def parse_date(val: Any) -> Optional[date]:
    """Parse robusto de data (string ou número Excel)"""
    if pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    if isinstance(val, (int, float)):
        # Excel date serial
        try:
            base = datetime(1899, 12, 30)
            return (base + pd.Timedelta(days=val)).date()
        except:
            return None
    # String
    try:
        return pd.to_datetime(val, dayfirst=True).date()
    except:
        return None


def parse_time(val: Any) -> Optional[time]:
    """Parse robusto de horário"""
    if pd.isna(val):
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, datetime):
        return val.time()
    if isinstance(val, (int, float)):
        # Excel time serial (fração de dia)
        try:
            total_seconds = int(val * 24 * 3600)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return time(hours % 24, minutes, seconds)
        except:
            return None
    # String
    try:
        parsed = pd.to_datetime(val, format="%H:%M", errors="coerce")
        if pd.notna(parsed):
            return parsed.time()
        return None
    except:
        return None


def compute_hash_v2(row: Dict[str, Any]) -> str:
    """
    Computa hash v2 (17 campos) idêntico ao PR21.

    Campos (ordem fixa):
    1. sector
    2. municipio
    3. encontro
    4. tipo
    5. data (YYYY-MM-DD)
    6. hora_inicio (HH:MM)
    7. hora_fim (HH:MM)
    8. projeto_norm
    9. coord_acompanha_norm
    10. coordenador_norm
    11. formador_1_norm
    12. formador_2_norm
    13. formador_3_norm
    14. formador_4_norm
    15. formador_5_norm
    16. convidados_emails_norm (ordenados)
    17. aprovacao_norm
    """
    # Normalizar campos
    sector = normalize_text(row.get("sector", ""))
    municipio = normalize_text(row.get("municipio_raw", ""))
    encontro = normalize_text(row.get("encontro", ""))
    tipo = normalize_text(row.get("tipo", ""))

    # Data/hora
    data_val = row.get("data")
    data_str = data_val.isoformat() if isinstance(data_val, date) else ""

    hora_inicio_val = row.get("hora_inicio")
    hora_inicio_str = hora_inicio_val.strftime("%H:%M") if isinstance(hora_inicio_val, time) else ""

    hora_fim_val = row.get("hora_fim")
    hora_fim_str = hora_fim_val.strftime("%H:%M") if isinstance(hora_fim_val, time) else ""

    # Projeto
    projeto_norm = normalize_text(row.get("projeto_norm", ""))

    # Coord acompanha (só se pessoa)
    coord_acomp_raw = row.get("coord_acompanha", "")
    coord_acomp = "" if is_indicator_not_person(coord_acomp_raw) else normalize_text(coord_acomp_raw)

    # Coordenador
    coordenador = normalize_text(row.get("coordenador", ""))

    # Formadores (5)
    formadores = []
    for i in range(1, 6):
        f = row.get(f"formador_{i}", "")
        formadores.append("" if is_indicator_not_person(f) else normalize_text(f))

    # Convidados (ordenar emails)
    convs_raw = str(row.get("convidados_emails", ""))
    convs_emails = []
    for email in re.split(r"[;,\s]+", convs_raw):
        email_norm = normalize_email(email)
        if email_norm:
            convs_emails.append(email_norm)
    convs_str = ";".join(sorted(set(convs_emails)))

    # Aprovação
    aprovacao = normalize_text(row.get("aprovacao", ""))

    # Montar campos
    parts = [
        sector,
        municipio,
        encontro,
        tipo,
        data_str,
        hora_inicio_str,
        hora_fim_str,
        projeto_norm,
        coord_acomp,
        coordenador,
        *formadores,
        convs_str,
        aprovacao,
    ]

    combined = "|".join(parts)
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()


def download_sheet(sheet_id: str, name: str) -> Optional[Path]:
    """Baixa planilha do Google Sheets como XLSX"""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        print(f"📥 Baixando {name} do Google Sheets...")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        output = TEMP_DIR / f"{name}.xlsx"
        output.write_bytes(response.content)
        print(f"   ✅ Salvo em {output}")
        return output
    except Exception as e:
        print(f"   ❌ Erro ao baixar {name}: {e}")
        return None


def load_workbook(file_path: Path, source: str) -> Optional[Dict[str, pd.DataFrame]]:
    """Carrega workbook Excel retornando dict de DataFrames por aba"""
    try:
        return pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        print(f"   ❌ Erro ao ler {file_path} ({source}): {e}")
        return None


def col_letter_to_index(letter: str) -> int:
    """Converte letra de coluna (A, B, ..., AA) para índice (0, 1, ..., 26)"""
    result = 0
    for char in letter:
        result = result * 26 + (ord(char.upper()) - ord("A") + 1)
    return result - 1


def process_events_sheet(df: pd.DataFrame, sheet_name: str, source: str) -> List[Dict[str, Any]]:
    """Processa uma aba de eventos (ACerta, Brincando, Vidas, Outros, Super)"""
    events = []

    # Determinar mapeamento de colunas
    col_map = COLUMN_MAP.get(sheet_name)
    if col_map == "ACerta":
        col_map = COLUMN_MAP["ACerta"]
    if not col_map:
        return []

    # Processar linhas (começar da linha 2 para pular cabeçalho)
    for idx in range(1, len(df)):
        row_data = {}

        # Extrair dados por coluna
        for col_letter, field_name in col_map.items():
            col_idx = col_letter_to_index(col_letter)
            if col_idx < len(df.columns):
                row_data[field_name] = df.iloc[idx, col_idx]

        # Validações básicas
        municipio = row_data.get("municipio", "")
        data_val = row_data.get("data")

        if pd.isna(municipio) or str(municipio).strip() == "" or pd.isna(data_val):
            continue  # Pular linha sem município ou data

        # Parse data e hora
        data_parsed = parse_date(data_val)
        hora_inicio_parsed = parse_time(row_data.get("hora_inicio"))
        hora_fim_parsed = parse_time(row_data.get("hora_fim"))

        if not data_parsed:
            continue

        # Determinar setor e projeto normalizado
        projeto_raw = row_data.get("projeto", "")
        projeto_norm = normalize_project(projeto_raw)

        if sheet_name in ["ACerta", "Brincando", "Vidas"]:
            sector = sheet_name
        elif sheet_name == "Outros":
            sector = projeto_norm
        else:  # Super
            sector = "Superintendência"

        # Super: dividir múltiplos municípios
        municipios = []
        municipio_raw = str(municipio).strip()
        if sheet_name == "Super" and any(sep in municipio_raw for sep in [";", ",", "/", "|"]):
            # Dividir
            for sep in [";", ",", "/", "|"]:
                municipio_raw = municipio_raw.replace(sep, "|")
            municipios = [m.strip() for m in municipio_raw.split("|") if m.strip()]
        else:
            municipios = [municipio_raw]

        # Criar registro por município
        for mun in municipios:
            event = {
                "sheet": sheet_name,
                "source": source,
                "sector": sector,
                "municipio_raw": mun,
                "encontro": row_data.get("encontro", ""),
                "tipo": row_data.get("tipo", ""),
                "data": data_parsed,
                "hora_inicio": hora_inicio_parsed,
                "hora_fim": hora_fim_parsed,
                "projeto": projeto_raw,
                "projeto_norm": projeto_norm,
                "coord_acompanha": row_data.get("coord_acompanha", ""),
                "coordenador": row_data.get("coordenador", ""),
                "formador_1": row_data.get("formador_1", ""),
                "formador_2": row_data.get("formador_2", ""),
                "formador_3": row_data.get("formador_3", ""),
                "formador_4": row_data.get("formador_4", ""),
                "formador_5": row_data.get("formador_5", ""),
                "segmento": row_data.get("segmento", ""),
                "aprovacao": row_data.get("aprovacao", ""),
                "convidados_emails": row_data.get("convidados_emails", ""),
                "cancelar": row_data.get("cancelar", ""),
                "row_index": idx + 1,
            }

            # Compute hash v2
            event["external_hash_v2"] = compute_hash_v2(event)

            events.append(event)

    return events


def main():
    """Função principal"""
    print("=" * 80)
    print("AUDITORIA DE PLANILHAS v2 - APRENDER SISTEMA")
    print("=" * 80)
    print(f"Timezone: {TZ}")
    print(f"Data/hora atual: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Diretório de saída: {OUTPUT_DIR.absolute()}")
    print()

    # Criar diretórios
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Baixar planilhas do Google Sheets
    print("📥 DOWNLOAD DE GOOGLE SHEETS")
    print("-" * 80)
    sheets_files = {}
    for name, sheet_id in SHEETS.items():
        file_path = download_sheet(sheet_id, name)
        if file_path:
            sheets_files[name] = file_path
    print()

    # Carregar arquivos locais
    print("📂 CARREGAMENTO DE ARQUIVOS LOCAIS")
    print("-" * 80)
    local_workbooks = {}
    for name, file_path in LOCAL_FILES.items():
        path = Path(file_path)
        if path.exists():
            print(f"📖 Carregando {name} local...")
            wb = load_workbook(path, "local")
            if wb:
                local_workbooks[name] = wb
                print(f"   ✅ {len(wb)} abas carregadas")
        else:
            print(f"   ⚠️  Arquivo não encontrado: {path}")
    print()

    # Carregar workbooks do Google Sheets
    print("📖 CARREGAMENTO DE PLANILHAS BAIXADAS")
    print("-" * 80)
    sheets_workbooks = {}
    for name, file_path in sheets_files.items():
        print(f"📖 Carregando {name} do Google Sheets...")
        wb = load_workbook(file_path, "sheets")
        if wb:
            sheets_workbooks[name] = wb
            print(f"   ✅ {len(wb)} abas carregadas")
    print()

    # Processar eventos do Acompanhamento
    print("🔄 PROCESSAMENTO DE EVENTOS")
    print("-" * 80)
    all_events = []

    for source_name, workbooks_dict in [("local", local_workbooks), ("sheets", sheets_workbooks)]:
        if "Acompanhamento" not in workbooks_dict:
            continue

        wb = workbooks_dict["Acompanhamento"]
        for sheet_name in ["ACerta", "Brincando", "Vidas", "Outros", "Super"]:
            if sheet_name in wb:
                print(f"   Processando {sheet_name} ({source_name})...")
                df = wb[sheet_name]
                events = process_events_sheet(df, sheet_name, source_name)
                all_events.extend(events)
                print(f"      ✅ {len(events)} eventos extraídos")

    print(f"\n📊 Total de eventos processados: {len(all_events)}")
    print()

    # Converter para DataFrame
    df_events = pd.DataFrame(all_events)

    # RELATÓRIO 1: Duplicados (hash v2)
    print("📝 GERANDO RELATÓRIO: Duplicados (hash v2)")
    duplicates = df_events[df_events.duplicated(subset=["external_hash_v2"], keep=False)]
    duplicates_sorted = duplicates.sort_values("external_hash_v2")
    output_file = OUTPUT_DIR / "relatorio_eventos_duplicados.csv"
    duplicates_sorted.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(duplicates)} duplicatas encontradas → {output_file.absolute()}")

    # RELATÓRIO 2: Intervalos inválidos
    print("📝 GERANDO RELATÓRIO: Intervalos inválidos")
    invalid_intervals = []
    for idx, row in df_events.iterrows():
        if row["hora_inicio"] and row["hora_fim"]:
            if row["hora_fim"] <= row["hora_inicio"]:
                invalid_intervals.append(row)
    df_invalid = pd.DataFrame(invalid_intervals)
    output_file = OUTPUT_DIR / "relatorio_intervalos_invalidos.csv"
    df_invalid.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(invalid_intervals)} intervalos inválidos → {output_file.absolute()}")

    # RELATÓRIO 3: Cancelados/adiados
    print("📝 GERANDO RELATÓRIO: Cancelados/adiados")
    cancelados = []
    for idx, row in df_events.iterrows():
        is_cancelled = False
        reason = ""

        # ACerta/Brincando/Vidas/Super: checkbox cancelar
        if row["sheet"] in ["ACerta", "Brincando", "Vidas", "Super"]:
            if row["cancelar"] and str(row["cancelar"]).lower() in ["true", "sim", "x", "1", "yes"]:
                is_cancelled = True
                reason = "Checkbox Cancelar marcado"

        # Outros: segmento contém cancelado/adiado
        if row["sheet"] == "Outros":
            segmento = normalize_text(str(row["segmento"]))
            if "cancelado" in segmento or "adiado" in segmento:
                is_cancelled = True
                reason = f"Segmento: {row['segmento']}"

        if is_cancelled:
            row_dict = row.to_dict()
            row_dict["reason"] = reason
            cancelados.append(row_dict)

    df_cancelados = pd.DataFrame(cancelados)
    output_file = OUTPUT_DIR / "relatorio_eventos_cancelados_adiados.csv"
    df_cancelados.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(cancelados)} eventos cancelados/adiados → {output_file.absolute()}")

    # RELATÓRIO 4: Outros sem formador
    print("📝 GERANDO RELATÓRIO: Outros sem formador")
    sem_formador = []
    for idx, row in df_events.iterrows():
        if row["sheet"] == "Outros":
            has_formador = False
            for i in range(1, 6):
                f = row[f"formador_{i}"]
                if not pd.isna(f) and not is_indicator_not_person(f):
                    has_formador = True
                    break

            if not has_formador:
                row_dict = row.to_dict()
                row_dict["observacao"] = "Coordenador acumula papel de FORMADOR"
                sem_formador.append(row_dict)

    df_sem_formador = pd.DataFrame(sem_formador)
    output_file = OUTPUT_DIR / "relatorio_outros_sem_formador.csv"
    df_sem_formador.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(sem_formador)} eventos sem formador → {output_file.absolute()}")

    # RELATÓRIO 5: Pessoas pendentes (placeholder - requer carregar Usuários)
    print("📝 GERANDO RELATÓRIO: Pessoas pendentes")
    output_file = OUTPUT_DIR / "relatorio_pessoas_pendentes_match.csv"
    pd.DataFrame({"status": ["Análise de matching requer processamento de Usuários"]}).to_csv(
        output_file, index=False, encoding="utf-8-sig"
    )
    print(f"   ⚠️  Análise completa requer processamento adicional → {output_file.absolute()}")

    # RELATÓRIO 6: Comparação projetos
    print("📝 GERANDO RELATÓRIO: Comparação projetos")
    output_file = OUTPUT_DIR / "relatorio_comparacao_projetos.csv"
    projetos_outros = df_events[df_events["sheet"] == "Outros"]["projeto_norm"].unique()
    pd.DataFrame({"projeto": projetos_outros}).to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(projetos_outros)} projetos únicos em Outros → {output_file.absolute()}")

    # RELATÓRIO 7: Divergências Sheets vs Local
    print("📝 GERANDO RELATÓRIO: Divergências Sheets vs Local")

    # Separar eventos por fonte
    df_local = df_events[df_events["source"] == "local"].copy()
    df_sheets = df_events[df_events["source"] == "sheets"].copy()

    # Comparar hashes
    hashes_local = set(df_local["external_hash_v2"])
    hashes_sheets = set(df_sheets["external_hash_v2"])

    only_local = hashes_local - hashes_sheets
    only_sheets = hashes_sheets - hashes_local

    divergencias = []
    if only_local:
        for h in only_local:
            row = df_local[df_local["external_hash_v2"] == h].iloc[0]
            divergencias.append(
                {
                    "tipo": "Apenas em XLSX local",
                    "sheet": row["sheet"],
                    "municipio": row["municipio_raw"],
                    "data": row["data"],
                    "tipo_evento": row["tipo"],
                    "hash": h,
                }
            )

    if only_sheets:
        for h in only_sheets:
            row = df_sheets[df_sheets["external_hash_v2"] == h].iloc[0]
            divergencias.append(
                {
                    "tipo": "Apenas em Google Sheets",
                    "sheet": row["sheet"],
                    "municipio": row["municipio_raw"],
                    "data": row["data"],
                    "tipo_evento": row["tipo"],
                    "hash": h,
                }
            )

    df_divergencias = pd.DataFrame(divergencias)
    output_file = OUTPUT_DIR / "relatorio_divergencias_sheets_vs_xlsx.csv"
    df_divergencias.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(divergencias)} divergências encontradas → {output_file.absolute()}")

    # SUMÁRIO EXECUTIVO
    print()
    print("=" * 80)
    print("SUMÁRIO EXECUTIVO")
    print("=" * 80)
    print()

    print("📊 RESUMO POR ABA")
    print("-" * 80)
    # Consolidar por aba (somar ambas as fontes e dividir por 2 se duplicado)
    df_unique = df_events.drop_duplicates(subset=["external_hash_v2"])
    for sheet in ["ACerta", "Brincando", "Vidas", "Outros", "Super"]:
        sheet_data = df_unique[df_unique["sheet"] == sheet]
        total = len(sheet_data)
        sem_municipio = len(sheet_data[sheet_data["municipio_raw"].isna() | (sheet_data["municipio_raw"] == "")])
        sem_data = len(sheet_data[sheet_data["data"].isna()])

        # Duplicados entre local e sheets
        sheet_all = df_events[df_events["sheet"] == sheet]
        duplicados = len(sheet_all[sheet_all.duplicated(subset=["external_hash_v2"], keep=False)])

        print(
            f"{sheet:15} | Total: {total:4} | Sem município: {sem_municipio:3} | "
            f"Sem data: {sem_data:3} | Duplicados (local↔sheets): {duplicados//2:3}"
        )

    print()
    print("📊 RESUMO SUPER (Aprovação/Tempo)")
    print("-" * 80)
    super_data = df_unique[df_unique["sheet"] == "Super"]
    today = datetime.now(TZ).date()
    passados = len(super_data[super_data["data"] < today])
    futuros = len(super_data[super_data["data"] >= today])

    # Aprovação = SIM (case-insensitive)
    futuros_aprovados = 0
    for idx, row in super_data.iterrows():
        if row["data"] >= today:
            aprov = normalize_text(str(row.get("aprovacao", "")))
            if aprov == "sim":
                futuros_aprovados += 1

    futuros_pendentes = futuros - futuros_aprovados

    print(f"Total eventos Super:          {len(super_data)}")
    print(f"Passados (< hoje):            {passados}")
    print(f"Futuros (>= hoje):            {futuros}")
    print(f"  ├─ Aprovados (Aprovação=SIM): {futuros_aprovados}")
    print(f"  └─ Pendentes:                 {futuros_pendentes}")

    print()
    print("📊 CONTAGENS DE DISPONIBILIDADE")
    print("-" * 80)
    print("⚠️  Processamento de Disponibilidade, Controle e Usuários em desenvolvimento")

    print()
    print("📊 PROJETOS SEM MATCH NO CONTROLE")
    print("-" * 80)
    print("⚠️  Comparação com FILTRO_PROD em desenvolvimento")

    print()
    print("📊 TOP 10 PENDÊNCIAS DE PESSOAS")
    print("-" * 80)
    print("⚠️  Matching com Usuários em desenvolvimento")

    print()
    print("✅ AUDITORIA CONCLUÍDA!")
    print(f"📁 Relatórios salvos em: {OUTPUT_DIR.absolute()}")
    print()

    # Listar arquivos gerados
    print("📄 ARQUIVOS GERADOS:")
    for file in sorted(OUTPUT_DIR.glob("relatorio_*.csv")):
        size_kb = file.stat().st_size / 1024
        print(f"   - {file.absolute()} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
