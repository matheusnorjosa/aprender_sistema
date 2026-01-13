"""
Parser para planilha "Acompanhamento de Agenda _ Fluir (1).xlsx".

Diferenças vs. planilha principal:
- Estrutura de colunas diferente (A-I vs A-T)
- Formador único (coluna I) vs múltiplos (O-S)
- Campo "tema" específico do Fluir
- Campo "turma" adicional

Estrutura esperada (aba "Acompanhamento"):
- Coluna A: foi Configurado (bool)
- Coluna B: município (str + UF)
- Coluna C: turma (str)
- Coluna D: encontro (int)
- Coluna E: presencial (bool)
- Coluna F: data (date)
- Coluna G: hora início (time)
- Coluna H: tema (str)
- Coluna I: formador (str - nome)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportGeneralTypeIssues=false, reportArgumentType=false, reportOptionalMemberAccess=false


from __future__ import annotations
import hashlib
import logging
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

FORTALEZA_TZ = ZoneInfo("America/Fortaleza")


def parse_fluir_eventos(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse aba "Acompanhamento" da planilha Fluir.

    Args:
        filepath: Caminho para "Acompanhamento de Agenda _ Fluir (1).xlsx"

    Returns:
        Lista de dicts com campos:
        - municipio_nome_uf (str)
        - projeto_nome (str) - "FLUIR DAS EMOÇÕES"
        - tipo (str) - "evento"
        - encontro (str)
        - inicio (datetime - timezone aware)
        - fim (datetime - estimado inicio + 3h se não fornecido)
        - formadores (list[str]) - lista de 1 elemento
        - tema (str) - campo específico Fluir
        - turma (str) - campo específico Fluir
        - is_online (bool) - inverso de "presencial"
        - status (str) - "aprovado" se configurado, senão "pendente"
        - src (str) - "fluir/Acompanhamento"
        - external_hash (str) - SHA1 para idempotência
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Planilha Fluir não encontrada: {filepath}")

    # Ler aba "Acompanhamento"
    df = pd.read_excel(filepath, sheet_name="Acompanhamento")

    # Mapear colunas esperadas (nomes EXATOS da planilha)
    col_map = {
        "foi Configurado": "configurado",
        "município": "municipio",  # Com acento!
        "turma": "turma",
        "encontro": "encontro",
        "presencial": "presencial",
        "data": "data",
        "hora início": "hora_inicio",  # Com acento!
        "tema": "tema",
        "formador": "formador",
    }

    # Renomear colunas
    df_renamed = df.rename(columns=col_map)

    # Remover linhas vazias (usar nome normalizado 'municipio')
    df_clean = df_renamed.dropna(subset=["municipio", "data"], how="any")

    eventos = []

    for idx, row in df_clean.iterrows():
        try:
            # Parse básico
            municipio_raw = str(row.get("municipio", "")).strip()
            if not municipio_raw or municipio_raw == "nan":
                continue

            data_raw = row.get("data")
            if pd.isna(data_raw):
                continue

            formador_raw = str(row.get("formador", "")).strip()
            if not formador_raw or formador_raw == "nan":
                continue

            # Data
            if isinstance(data_raw, pd.Timestamp):
                data_dt = data_raw.to_pydatetime().date()
            elif isinstance(data_raw, datetime):
                data_dt = data_raw.date()
            else:
                # Tentar parse manual
                data_dt = pd.to_datetime(data_raw).date()

            # Hora início (default 14:00 se não fornecida)
            hora_inicio_raw = row.get("hora_inicio")
            if pd.isna(hora_inicio_raw):
                hora_inicio = dtime(14, 0)
            elif isinstance(hora_inicio_raw, dtime):
                hora_inicio = hora_inicio_raw
            elif isinstance(hora_inicio_raw, pd.Timestamp):
                hora_inicio = hora_inicio_raw.time()
            else:
                # Tentar parse string "HH:MM"
                try:
                    hora_inicio = pd.to_datetime(hora_inicio_raw).time()
                except Exception:
                    hora_inicio = dtime(14, 0)

            # Combinar data + hora em datetime timezone-aware
            inicio_dt = datetime.combine(data_dt, hora_inicio)
            inicio_aware = inicio_dt.replace(tzinfo=FORTALEZA_TZ)

            # Fim (estimado: início + 3h)
            fim_aware = inicio_aware + timedelta(hours=3)

            # Campos adicionais
            configurado = bool(row.get("configurado", False))
            presencial = bool(row.get("presencial", True))
            turma = str(row.get("turma", "")).strip()
            encontro = str(row.get("encontro", "1")).strip()
            tema = str(row.get("tema", "")).strip()

            # Montar objeto de evento
            evento = {
                "municipio_nome_uf": municipio_raw,
                "projeto_nome": "FLUIR DAS EMOÇÕES",
                "tipo": "evento",
                "encontro": encontro,
                "inicio": inicio_aware,
                "fim": fim_aware,
                "formadores": [formador_raw],
                "tema": tema,
                "turma": turma,
                "is_online": not presencial,
                "status": "aprovado" if configurado else "pendente",
                "src": "fluir/Acompanhamento",
            }

            # Gerar external_hash para idempotência
            hash_input = f"{municipio_raw}|{inicio_aware.isoformat()}|{formador_raw}|{turma}|{encontro}"
            evento["external_hash"] = hashlib.sha1(hash_input.encode()).hexdigest()

            eventos.append(evento)

        except Exception as e:
            # Log erro mas continua processando
            logger.warning(f"Erro ao processar linha {idx}: {e}")
            continue

    return eventos


def get_formadores_fluir() -> list[str]:
    """
    Retorna lista dos 9 formadores únicos do projeto Fluir.

    Baseado em análise manual da planilha.

    Returns:
        Lista de nomes completos dos formadores
    """
    return [
        "Adeliana Mówima Falcao Machado",
        "Fernanda Matthews Jucá",
        "Janaína Bezerra de Aquino Faria",
        "Jennifer Kerolly de Oliveira Barros Bathaus",
        "Juliana Cruz Maciel",
        "Jéssica Nunes Apolonio",
        "Natália de Araújo Loiola",
        "Priscilla Laysa Mota Pereira",
        "Talitha Lousada Teixeira",
    ]
