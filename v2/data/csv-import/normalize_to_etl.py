#!/usr/bin/env python3
"""
Normaliza XLSX para CSV ETL usando regras PR21 (hash v2).
Lê: /app/data/csv-import/acompanhamento_2025.xlsx
Saída: /app/data/csv-import/etl_eventos_normalizados.csv
"""
import sys
import hashlib
import re
from pathlib import Path
from datetime import datetime
import unicodedata
import pandas as pd

def normalize_text(val):
    if pd.isna(val) or val == "":
        return ""
    s = str(val).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.casefold()
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def normalize_project_alias(projeto: str) -> str:
    if pd.isna(projeto) or projeto == "":
        return ""
    projeto_norm = normalize_text(projeto)
    if re.search(r"\bideb\s*10?\b", projeto_norm) or re.search(r"\bideb[-\s]*10\b", projeto_norm):
        return "Gestão Escolar"
    if "gestao" in projeto_norm and "escolar" in projeto_norm:
        return "Gestão Escolar"
    return str(projeto).strip()

def parse_date(val):
    if pd.isna(val):
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    m = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    return ""

def parse_time(val):
    if pd.isna(val):
        return ""
    if isinstance(val, datetime):
        return val.strftime("%H:%M")
    s = str(val).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", s)
    if m:
        h, mi = m.groups()
        return f"{h.zfill(2)}:{mi}"
    return ""

def explode_municipios(mun_raw: str) -> list:
    if pd.isna(mun_raw) or mun_raw == "":
        return [""]
    s = str(mun_raw).strip()
    s_norm = normalize_text(s)
    if s_norm in ["super", "seduc"]:
        return ["Super"]
    parts = re.split(r"[;,]+", s)
    result = []
    for p in parts:
        p = p.strip()
        if p:
            result.append(p)
    return result if result else [""]

def extract_formadores(row):
    formadores = []
    for i in range(1, 6):
        col = f"FORMADOR_{i}"
        if col in row.index:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                formadores.append(normalize_text(str(val).strip()))
    return formadores

def main():
    input_path = Path("/app/data/csv-import/acompanhamento_2025.xlsx")
    output_path = Path("/app/data/csv-import/etl_eventos_normalizados.csv")

    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}")
        import os
        print("   Arquivos disponíveis em /app/data/csv-import:")
        for f in os.listdir("/app/data/csv-import"):
            print(f"   - {f}")
        sys.exit(1)

    print(f"📖 Lendo {input_path}...")
    df = pd.read_excel(input_path, sheet_name=0)
    df.columns = [str(c).strip().upper() for c in df.columns]

    rename_map = {
        "SETOR": "SECTOR",
        "MUNICÍPIO": "MUNICIPIO",
        "HORA INÍCIO": "HORA_INICIO",
        "HORA FIM": "HORA_FIM",
        "COORD. ACOMPANHA": "COORD_ACOMPANHA",
        "APROVAÇÃO": "APROVACAO",
    }
    df.rename(columns=rename_map, inplace=True)
    print(f"   {len(df)} linhas, {len(df.columns)} colunas")

    print("\n🔄 Normalizando registros...")
    rows_out = []

    for idx, row in df.iterrows():
        sector = str(row.get("SECTOR", "")).strip()
        municipio_raw = str(row.get("MUNICIPIO", "")).strip()
        encontro = str(row.get("ENCONTRO", "")).strip()
        tipo = str(row.get("TIPO", "")).strip()
        data = parse_date(row.get("DATA"))
        hora_inicio = parse_time(row.get("HORA_INICIO"))
        hora_fim = parse_time(row.get("HORA_FIM"))
        projeto = str(row.get("PROJETO", "")).strip()
        coord_acompanha = str(row.get("COORD_ACOMPANHA", "")).strip()
        coordenador = str(row.get("COORDENADOR", "")).strip()
        convidados = str(row.get("CONVIDADOS", "")).strip()
        aprovacao = str(row.get("APROVACAO", "")).strip()

        sector_norm = normalize_text(sector)
        encontro_norm = normalize_text(encontro)
        tipo_norm = normalize_text(tipo)
        projeto_norm = normalize_project_alias(projeto)
        coord_acompanha_norm = normalize_text(coord_acompanha)
        coordenador_norm = normalize_text(coordenador)
        convidados_norm = normalize_text(convidados)
        aprovacao_norm = normalize_text(aprovacao)

        formadores_norm = extract_formadores(row)
        while len(formadores_norm) < 5:
            formadores_norm.append("")

        municipios_exploded = explode_municipios(municipio_raw)

        for mun in municipios_exploded:
            mun_norm = normalize_text(mun)

            conv_emails = sorted([e.strip().lower() for e in convidados_norm.split(",") if e.strip()])
            convs_str = ",".join(conv_emails) if conv_emails else ""

            parts = [
                sector_norm,
                mun_norm,
                encontro_norm,
                tipo_norm,
                data,
                hora_inicio,
                hora_fim,
                projeto_norm,
                coord_acompanha_norm,
                coordenador_norm,
                *formadores_norm,
                convs_str,
                aprovacao_norm,
            ]
            combined = "|".join(parts)
            external_hash = hashlib.sha1(combined.encode("utf-8")).hexdigest()

            rows_out.append({
                "sector": sector,
                "municipio_raw": mun,
                "municipio_norm": mun_norm,
                "encontro": encontro,
                "tipo": tipo,
                "data": data,
                "hora_inicio": hora_inicio,
                "hora_fim": hora_fim,
                "projeto": projeto,
                "projeto_norm": projeto_norm,
                "coord_acompanha": coord_acompanha,
                "coord_acompanha_norm": coord_acompanha_norm,
                "coordenador": coordenador,
                "coordenador_norm": coordenador_norm,
                "formador_1_norm": formadores_norm[0],
                "formador_2_norm": formadores_norm[1],
                "formador_3_norm": formadores_norm[2],
                "formador_4_norm": formadores_norm[3],
                "formador_5_norm": formadores_norm[4],
                "convidados": convidados,
                "convidados_norm": convs_str,
                "aprovacao": aprovacao,
                "aprovacao_norm": aprovacao_norm,
                "external_hash": external_hash,
            })

    df_out = pd.DataFrame(rows_out)
    print(f"   {len(df_out)} registros normalizados (após explosão de municípios)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\n✅ CSV gerado: {output_path} ({len(df_out)} linhas)")

if __name__ == "__main__":
    main()
