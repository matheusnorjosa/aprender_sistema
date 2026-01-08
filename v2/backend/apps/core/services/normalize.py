"""
Funções de normalização de texto, datas e horas.

Funções utilitárias para normalização de strings vindas de planilhas/CSVs,
usadas tanto pelo ETL quanto por validações em runtime.

Movido de dat_ingest/services/acompanhamento_normalize.py para desacoplar
ETL do sistema principal (Issue: decouple-etl).
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

import hashlib
import re
import unicodedata
from datetime import date, time
from typing import Dict, List, Optional


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
        if "ideb" in projeto_norm or ("gestao" in projeto_norm and "escolar" in projeto_norm):
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


def normalize_project_alias(projeto: str) -> str:
    """
    Normaliza nome do projeto aplicando aliases (IDEB/IDEB10 → Gestão Escolar).

    Args:
        projeto: Nome do projeto

    Returns:
        Nome normalizado com aliases aplicados
    """
    projeto_norm = norm_text(projeto) if projeto else ""

    # Aplicar aliases IDEB
    if "ideb" in projeto_norm or ("gestao" in projeto_norm and "escolar" in projeto_norm):
        return "Gestão Escolar"

    # Retornar original se não houver alias
    return projeto.strip() if projeto else ""


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


def normalize_email(s: str) -> str:
    """
    Normaliza email para lowercase (sem acentos removidos).

    Args:
        s: Email string

    Returns:
        Email em lowercase, trimmed
    """
    if not s:
        return ""

    return s.strip().lower()


def normalize_date_field(s: str) -> str:
    """
    Normaliza campo de data para formato YYYY-MM-DD.

    Args:
        s: String de data (pode ser YYYY-MM-DD ou DD/MM/YYYY)

    Returns:
        Data em formato YYYY-MM-DD ou string vazia se inválido
    """
    if not s:
        return ""

    s = s.strip()

    # Já está em formato ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # Converter DD/MM/YYYY para YYYY-MM-DD
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    return ""


def normalize_time_field(s: str) -> str:
    """
    Normaliza campo de hora para formato HH:MM.

    Args:
        s: String de hora (pode incluir segundos)

    Returns:
        Hora em formato HH:MM ou string vazia se inválido
    """
    if not s:
        return ""

    s = s.strip()

    # Remove segundos se presente
    parts = s.split(":")
    if len(parts) >= 2:
        hour = parts[0].zfill(2)
        minute = parts[1].zfill(2)
        return f"{hour}:{minute}"

    return ""


def hash_event_v2(row: Dict[str, str]) -> str:
    """
    Gera external_hash v2 (SHA1) a partir de 17 campos normalizados.

    Esta função implementa o critério de "duplicata real" usado na auditoria,
    com normalização completa de todos os campos.

    Campos (todos normalizados):
    1. sector (aba ou mapeado em "Outros" via Projeto com alias IDEB→Gestão Escolar)
    2. municipio
    3. encontro
    4. tipo_evento
    5. data (formato YYYY-MM-DD)
    6. hora_inicio (formato HH:MM)
    7. hora_fim (formato HH:MM)
    8. projeto
    9. segmento
    10. coord_acompanha
    11. coordenador
    12. formador1
    13. formador2
    14. formador3
    15. formador4
    16. formador5
    17. aprovacao (apenas para "Super"; vazio nos demais)

    Normalização aplicada:
    - Textos: trim, collapse spaces, sem acentos, casefold
    - Emails: lowercase (sem remoção de acentos)
    - Datas: YYYY-MM-DD
    - Horas: HH:MM

    Args:
        row: Dicionário com campos normalizados do evento

    Returns:
        Hash SHA1 (40 caracteres hex)

    Examples:
        >>> row = {
        ...     "source_sheet": "ACerta",
        ...     "projeto": "ACerta",
        ...     "municipio": "Fortaleza",
        ...     "encontro": "1",
        ...     "tipo": "Presencial",
        ...     "data": "2025-01-15",
        ...     "hora_inicio": "08:00",
        ...     "hora_fim": "12:00",
        ...     "segmento": "EI",
        ...     "coord_acompanha": "sim",
        ...     "coordenador": "coord@example.com",
        ...     "formador1": "form1@example.com",
        ...     "formador2": "",
        ...     "formador3": "",
        ...     "formador4": "",
        ...     "formador5": "",
        ...     "aprovacao": "",
        ... }
        >>> hash_event_v2(row)
        'a1b2c3...'  # SHA1 hash
    """
    # 1. sector - mapear de aba + projeto (com alias IDEB)
    sector = normalize_sector(
        row.get("source_sheet", ""),
        row.get("projeto", "")
    )
    sector_norm = norm_text(sector)

    # 2. municipio
    municipio_norm = norm_text(row.get("municipio", ""))

    # 3. encontro
    encontro_norm = norm_text(row.get("encontro", ""))

    # 4. tipo_evento
    tipo_norm = norm_text(row.get("tipo", ""))

    # 5. data (YYYY-MM-DD)
    data_norm = normalize_date_field(row.get("data", ""))

    # 6. hora_inicio (HH:MM)
    hora_inicio_norm = normalize_time_field(row.get("hora_inicio", ""))

    # 7. hora_fim (HH:MM)
    hora_fim_norm = normalize_time_field(row.get("hora_fim", ""))

    # 8. projeto - aplicar aliases IDEB→Gestão Escolar para consistência
    projeto_raw = row.get("projeto", "")
    projeto_lower = norm_text(projeto_raw)
    # Aplicar mesmo mapeamento de aliases que normalize_sector
    if "ideb" in projeto_lower or ("gestao" in projeto_lower and "escolar" in projeto_lower):
        projeto_norm = norm_text("Gestão Escolar")
    else:
        projeto_norm = projeto_lower

    # 9. segmento
    segmento_norm = norm_text(row.get("segmento", ""))

    # 10. coord_acompanha
    coord_acompanha_norm = norm_text(row.get("coord_acompanha", ""))

    # 11. coordenador (email ou nome)
    coordenador = row.get("coordenador", "")
    if "@" in coordenador:
        coordenador_norm = normalize_email(coordenador)
    else:
        coordenador_norm = norm_text(coordenador)

    # 12-16. formadores (emails ou nomes)
    formadores_norm = []
    for i in range(1, 6):
        formador = row.get(f"formador{i}", "")
        if "@" in formador:
            formadores_norm.append(normalize_email(formador))
        else:
            formadores_norm.append(norm_text(formador))

    # 17. aprovacao (apenas para Super; vazio nos demais)
    aprovacao = row.get("aprovacao", "")
    if sector_norm == "super":
        aprovacao_norm = norm_text(aprovacao)
    else:
        aprovacao_norm = ""

    # Construir string canônica
    parts = [
        sector_norm,           # 1
        municipio_norm,        # 2
        encontro_norm,         # 3
        tipo_norm,             # 4
        data_norm,             # 5
        hora_inicio_norm,      # 6
        hora_fim_norm,         # 7
        projeto_norm,          # 8
        segmento_norm,         # 9
        coord_acompanha_norm,  # 10
        coordenador_norm,      # 11
        formadores_norm[0],    # 12 (formador1)
        formadores_norm[1],    # 13 (formador2)
        formadores_norm[2],    # 14 (formador3)
        formadores_norm[3],    # 15 (formador4)
        formadores_norm[4],    # 16 (formador5)
        aprovacao_norm,        # 17
    ]

    # Join com pipe delimiter
    content = "|".join(parts)

    # SHA1 hash
    hash_obj = hashlib.sha1(content.encode("utf-8"))
    return hash_obj.hexdigest()
