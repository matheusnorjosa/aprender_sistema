"""
Funções de normalização para ETL de Acompanhamento.

Normaliza textos, setores, municípios, datas e horas vindos de CSVs.
"""

import re
import unicodedata
from datetime import date, time
from typing import List, Optional


def norm_text(s: str) -> str:
    """
    Normaliza texto: trim, collapse espaços, remover acentos (NFKD).

    Args:
        s: String para normalizar

    Returns:
        String normalizada (minúsculas, sem acentos, espaços colapsados)
    """
    if not s:
        return ""

    # Trim
    s = s.strip()

    # Collapse espaços múltiplos
    s = re.sub(r"\s+", " ", s)

    # Remover acentos (NFKD decomposition)
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    s = s.lower()

    return s


def normalize_sector(sheet_name: str, projeto_value: str) -> str:
    """
    Mapeia setor a partir da aba e valor do Projeto.

    Regras:
    - ACerta → "ACerta"
    - Brincando → "Brincando"
    - Vidas → "Vidas"
    - Outros:
      - IDEB/IDEB10 → "Gestão Escolar"
      - Vidas L → "Vida & Linguagem"
      - Vidas M → "Vida & Matemática"
      - Vidas C → "Vida & Ciências"
      - Outros → "Outros"
    - Super → "Super"

    Args:
        sheet_name: Nome da aba (ACerta, Brincando, Vidas, Outros, Super)
        projeto_value: Valor do campo Projeto

    Returns:
        Setor normalizado
    """
    sheet_norm = norm_text(sheet_name)
    projeto_norm = norm_text(projeto_value) if projeto_value else ""

    if sheet_norm == "acerta":
        return "ACerta"
    elif sheet_norm == "brincando":
        return "Brincando"
    elif sheet_norm == "vidas":
        return "Vidas"
    elif sheet_norm == "super":
        return "Super"
    elif sheet_norm == "outros":
        # Map por Projeto
        if "ideb" in projeto_norm:
            return "Gestão Escolar"
        elif "vidas l" in projeto_norm or "linguagem" in projeto_norm:
            return "Vida & Linguagem"
        elif "vidas m" in projeto_norm or "matematica" in projeto_norm:
            return "Vida & Matemática"
        elif "vidas c" in projeto_norm or "ciencias" in projeto_norm:
            return "Vida & Ciências"
        else:
            return "Outros"
    else:
        return "Outros"


def split_municipios_super(value: str) -> List[str]:
    """
    Split múltiplos municípios separados por ; , / |

    Args:
        value: String com municípios (ex: "Fortaleza; Caucaia")

    Returns:
        Lista de municípios normalizados
    """
    if not value:
        return []

    # Split por delimitadores
    municipios = re.split(r"[;,/|]", value)

    # Trim e filtrar vazios
    municipios = [m.strip() for m in municipios if m.strip()]

    return municipios


def parse_date_iso(s: str) -> Optional[date]:
    """
    Parse data no formato YYYY-MM-DD.

    Args:
        s: String de data

    Returns:
        objeto date ou None se inválido
    """
    if not s:
        return None

    try:
        parts = s.split("-")
        if len(parts) != 3:
            return None

        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_time_iso(s: str) -> Optional[time]:
    """
    Parse hora no formato HH:MM ou HH:MM:SS.

    Args:
        s: String de hora

    Returns:
        objeto time ou None se inválido
    """
    if not s:
        return None

    try:
        parts = s.split(":")
        if len(parts) < 2:
            return None

        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) > 2 else 0

        return time(hour, minute, second)
    except (ValueError, IndexError):
        return None
