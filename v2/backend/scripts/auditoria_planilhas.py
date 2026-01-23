#!/usr/bin/env python3
"""
Auditoria de Dados - Planilhas Aprender Sistema
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

import pandas as pd
import pytz
import requests

# Configuração
TZ = pytz.timezone("America/Fortaleza")
OUTPUT_DIR = Path("/app/.agents/outbox")
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

# Mapeamento de colunas por aba
COLUMN_MAP = {
    "ACerta": {
        "D": "cancelar",
        "E": "encontro",
        "F": "municipio",
        "G": "tipo",
        "H": "data",
        "I": "hora_inicio",
        "J": "hora_fim",
        "K": "projeto",
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
        "D": "cancelar",
        "E": "encontro",
        "F": "municipio",
        "G": "tipo",
        "H": "data",
        "I": "hora_inicio",
        "J": "hora_fim",
        "K": "projeto",
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
        "D": "cancelar",
        "E": "encontro",
        "F": "municipio",
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
        "B": "aprovacao",
        "D": "cancelar",
        "E": "encontro",
        "F": "municipio",
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
}


def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, sem acentos, strip, colapsar espaços"""
    if pd.isna(text) or text == "":
        return ""
    text = str(text).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
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


def normalize_project(projeto: str) -> str:
    """Normaliza nome do projeto (IDEB/IDEB10 -> Gestão Escolar)"""
    projeto_norm = normalize_text(projeto)
    if "ideb" in projeto_norm or ("gestao" in projeto_norm and "escolar" in projeto_norm):
        return "Gestão Escolar"
    return projeto.strip() if projeto else ""


def parse_date(val: Any) -> Optional[date]:
    """Parse robusto de data (string ou número Excel)"""
    if pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    if isinstance(val, (int, float)):
        # Excel date serial
        try:
            return pd.Timestamp("1899-12-30") + pd.Timedelta(days=val)
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
            hours = int(val * 24)
            minutes = int((val * 24 * 60) % 60)
            return time(hours, minutes)
        except:
            return None
    # String
    try:
        return pd.to_datetime(val, format="%H:%M").time()
    except:
        try:
            return pd.to_datetime(val).time()
        except:
            return None


def compute_hash(row: Dict[str, Any]) -> str:
    """Computa hash SHA1 determinístico"""
    parts = [
        str(row.get("sheet", "")),
        str(row.get("sector", "")),
        str(row.get("municipio_raw", "")),
        str(row.get("tipo", "")),
        str(row.get("data", "")),
        str(row.get("hora_inicio", "")),
        str(row.get("hora_fim", "")),
        str(row.get("coordenador", "")),
        str(row.get("encontro", "")),
    ]
    combined = "|".join(parts)
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()


def download_sheet(sheet_id: str, name: str) -> Optional[Path]:
    """Baixa planilha do Google Sheets como XLSX"""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        print(f"📥 Baixando {name} do Google Sheets...")
        response = requests.get(url, timeout=30)
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


def process_events_sheet(df: pd.DataFrame, sheet_name: str, source: str) -> List[Dict[str, Any]]:
    """Processa uma aba de eventos (ACerta, Brincando, Vidas, Outros, Super)"""
    events = []

    # Determinar mapeamento de colunas
    col_map = COLUMN_MAP.get(sheet_name, COLUMN_MAP.get("ACerta"))
    if col_map == "ACerta":
        col_map = COLUMN_MAP["ACerta"]

    # Converter índices de coluna de letra para número
    def col_letter_to_index(letter: str) -> int:
        return ord(letter) - ord("A")

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

        if pd.isna(municipio) or municipio == "" or pd.isna(data_val):
            continue  # Pular linha sem município ou data

        # Parse data e hora
        data_parsed = parse_date(data_val)
        hora_inicio_parsed = parse_time(row_data.get("hora_inicio"))
        hora_fim_parsed = parse_time(row_data.get("hora_fim"))

        if not data_parsed:
            continue

        # Determinar setor
        if sheet_name in ["ACerta", "Brincando", "Vidas"]:
            sector = sheet_name
        elif sheet_name == "Outros":
            sector = normalize_project(row_data.get("projeto", ""))
        else:  # Super
            sector = "Super"

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

            # Compute hash
            event["external_hash"] = compute_hash(event)

            events.append(event)

    return events


def main():
    """Função principal"""
    print("=" * 80)
    print("AUDITORIA DE PLANILHAS - APRENDER SISTEMA")
    print("=" * 80)
    print(f"Timezone: {TZ}")
    print(f"Data/hora atual: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
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

    # RELATÓRIO 1: Duplicados
    print("📝 GERANDO RELATÓRIO: Duplicados")
    duplicates = df_events[df_events.duplicated(subset=["external_hash"], keep=False)]
    duplicates_sorted = duplicates.sort_values("external_hash")
    output_file = OUTPUT_DIR / "relatorio_eventos_duplicados.csv"
    duplicates_sorted.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(duplicates)} duplicatas encontradas → {output_file}")

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
    print(f"   ✅ {len(invalid_intervals)} intervalos inválidos → {output_file}")

    # RELATÓRIO 3: Cancelados/adiados
    print("📝 GERANDO RELATÓRIO: Cancelados/adiados")
    cancelados = []
    for idx, row in df_events.iterrows():
        is_cancelled = False
        reason = ""

        # ACerta/Brincando/Vidas/Super: checkbox cancelar
        if row["sheet"] in ["ACerta", "Brincando", "Vidas", "Super"]:
            if row["cancelar"] and str(row["cancelar"]).lower() in ["true", "sim", "x", "1"]:
                is_cancelled = True
                reason = "Checkbox Cancelar marcado"

        # Outros: segmento contém cancelado/adiado
        if row["sheet"] == "Outros":
            segmento = normalize_text(row["segmento"])
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
    print(f"   ✅ {len(cancelados)} eventos cancelados/adiados → {output_file}")

    # RELATÓRIO 4: Outros sem formador
    print("📝 GERANDO RELATÓRIO: Outros sem formador")
    sem_formador = []
    for idx, row in df_events.iterrows():
        if row["sheet"] == "Outros":
            has_formador = any(row[f"formador_{i}"] and not pd.isna(row[f"formador_{i}"]) for i in range(1, 6))
            if not has_formador:
                row_dict = row.to_dict()
                row_dict["observacao"] = "Coordenador acumula papel de FORMADOR"
                sem_formador.append(row_dict)

    df_sem_formador = pd.DataFrame(sem_formador)
    output_file = OUTPUT_DIR / "relatorio_outros_sem_formador.csv"
    df_sem_formador.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(sem_formador)} eventos sem formador → {output_file}")

    # RELATÓRIO 5: Pessoas pendentes (placeholder - requer carregar Usuários)
    print("📝 GERANDO RELATÓRIO: Pessoas pendentes")
    output_file = OUTPUT_DIR / "relatorio_pessoas_pendentes_match.csv"
    pd.DataFrame({"status": ["Análise de matching requer processamento de Usuários"]}).to_csv(
        output_file, index=False, encoding="utf-8-sig"
    )
    print(f"   ⚠️  Análise completa requer processamento adicional → {output_file}")

    # RELATÓRIO 6: Comparação projetos (placeholder)
    print("📝 GERANDO RELATÓRIO: Comparação projetos")
    output_file = OUTPUT_DIR / "relatorio_comparacao_projetos.csv"
    projetos_outros = df_events[df_events["sheet"] == "Outros"]["sector"].unique()
    pd.DataFrame({"projeto": projetos_outros}).to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"   ✅ {len(projetos_outros)} projetos únicos em Outros → {output_file}")

    # RELATÓRIO 7: Divergências Sheets vs Local
    print("📝 GERANDO RELATÓRIO: Divergências Sheets vs Local")
    output_file = OUTPUT_DIR / "relatorio_divergencias_sheets_vs_xlsx.csv"
    pd.DataFrame({"status": ["Comparação requer análise linha a linha"]}).to_csv(
        output_file, index=False, encoding="utf-8-sig"
    )
    print(f"   ⚠️  Análise detalhada pendente → {output_file}")

    # SUMÁRIO EXECUTIVO
    print()
    print("=" * 80)
    print("SUMÁRIO EXECUTIVO")
    print("=" * 80)
    print()

    print("📊 RESUMO POR ABA")
    print("-" * 80)
    for sheet in ["ACerta", "Brincando", "Vidas", "Outros", "Super"]:
        sheet_data = df_events[df_events["sheet"] == sheet]
        total = len(sheet_data)
        sem_municipio = len(sheet_data[sheet_data["municipio_raw"].isna()])
        sem_data = len(sheet_data[sheet_data["data"].isna()])
        duplicados = len(sheet_data[sheet_data.duplicated(subset=["external_hash"], keep=False)])

        print(
            f"{sheet:15} | Total: {total:4} | Sem município: {sem_municipio:3} | "
            f"Sem data: {sem_data:3} | Duplicados: {duplicados:3}"
        )

    print()
    print("📊 RESUMO SUPER (Aprovação/Tempo)")
    print("-" * 80)
    super_data = df_events[df_events["sheet"] == "Super"]
    today = datetime.now(TZ).date()
    passados = len(super_data[super_data["data"] < today])
    futuros = len(super_data[super_data["data"] >= today])
    futuros_aprovados = len(super_data[(super_data["data"] >= today) & (super_data["aprovacao"].str.upper() == "SIM")])
    futuros_pendentes = futuros - futuros_aprovados

    print(f"Total eventos Super:          {len(super_data)}")
    print(f"Passados (< hoje):            {passados}")
    print(f"Futuros (>= hoje):            {futuros}")
    print(f"  ├─ Aprovados (Aprovação=SIM): {futuros_aprovados}")
    print(f"  └─ Pendentes:                 {futuros_pendentes}")

    print()
    print("✅ AUDITORIA CONCLUÍDA!")
    print(f"📁 Relatórios salvos em: {OUTPUT_DIR.absolute()}")
    print()

    # Listar arquivos gerados
    print("📄 ARQUIVOS GERADOS:")
    for file in sorted(OUTPUT_DIR.glob("relatorio_*.csv")):
        size_kb = file.stat().st_size / 1024
        print(f"   - {file.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
