"""
ETL Loaders - Funções puras para carregar dados de planilhas Excel
"""

import hashlib
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .normalizers import (
    normalize_cpf,
    normalize_email,
    normalize_str,
    normalize_telefone,
    normalize_uf,
    parse_bool,
    titlecase,
)


def compute_file_hash(filepath: Path) -> str:
    """
    Calcula SHA256 de um arquivo

    Args:
        filepath: Caminho do arquivo

    Returns:
        Hash SHA256 em hexadecimal
    """
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def load_workbook_index(directory: Path) -> list[Path]:
    """
    Retorna lista de arquivos .xlsx no diretório

    Args:
        directory: Diretório a escanear

    Returns:
        Lista de Paths para arquivos .xlsx ordenados por nome
    """
    if not directory.exists():
        return []

    return sorted(directory.glob("*.xlsx"))


def parse_usuarios(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse planilha de usuários

    Estrutura esperada (aba "Ativos"):
    | Nome | CPF | Telefone | Email | Perfil | Superintendência | Ativo |

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com dados normalizados
    """
    wb = load_workbook(filepath, data_only=True)

    # Tenta várias abas possíveis
    sheet_names = ["Ativos", "Usuários", "Users", "Sheet1"]
    ws = None
    for name in sheet_names:
        if name in wb.sheetnames:
            ws = wb[name]
            break

    if ws is None:
        return []

    usuarios = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 4:
            continue

        nome = normalize_str(row[0]) if len(row) > 0 else ""
        cpf = normalize_cpf(row[1]) if len(row) > 1 else ""
        telefone = normalize_telefone(row[2]) if len(row) > 2 else ""
        email = normalize_email(row[3]) if len(row) > 3 else ""
        perfil = normalize_str(row[4]) if len(row) > 4 else "Formador"
        superintendencia = normalize_str(row[5]) if len(row) > 5 else ""
        ativo = parse_bool(row[6], default=True) if len(row) > 6 else True

        # Detecta se é superintendência pelo campo ou pelo perfil
        if "superintend" in perfil.lower() or "superintend" in superintendencia.lower():
            perfil = "Superintendência"

        # Validação mínima: precisa ter nome e email
        if not nome or not email:
            continue

        usuarios.append(
            {
                "nome": titlecase(nome),
                "email": email,
                "cpf": cpf,
                "telefone": telefone,
                "perfil": perfil,
                "ativo": ativo,
                "src": f"{filepath.name}/Ativos",
                "rownum": i,
            }
        )

    return usuarios


def parse_municipios(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse planilha de municípios

    Estrutura esperada:
    | Nome | UF | Ativo |

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com dados normalizados
    """
    wb = load_workbook(filepath, data_only=True)

    # Tenta várias abas possíveis
    sheet_names = ["Municípios", "Municipios", "Cidades", "Sheet1"]
    ws = None
    for name in sheet_names:
        if name in wb.sheetnames:
            ws = wb[name]
            break

    if ws is None:
        return []

    municipios = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 2:
            continue

        nome = normalize_str(row[0]) if len(row) > 0 else ""
        uf = normalize_uf(row[1]) if len(row) > 1 else ""
        ativo = parse_bool(row[2], default=True) if len(row) > 2 else True

        # Validação mínima
        if not nome or not uf:
            continue

        municipios.append(
            {
                "nome": titlecase(nome),
                "uf": uf.upper(),
                "ativo": ativo,
                "src": f"{filepath.name}/Municipios",
                "rownum": i,
            }
        )

    return municipios


def parse_projetos(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse planilha de projetos

    Estrutura esperada:
    | Nome | Descrição | Ativo |

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com dados normalizados
    """
    wb = load_workbook(filepath, data_only=True)

    # Tenta várias abas possíveis
    sheet_names = ["Projetos", "Projects", "Sheet1"]
    ws = None
    for name in sheet_names:
        if name in wb.sheetnames:
            ws = wb[name]
            break

    if ws is None:
        return []

    projetos = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 1:
            continue

        nome = normalize_str(row[0]) if len(row) > 0 else ""
        descricao = normalize_str(row[1]) if len(row) > 1 else ""
        ativo = parse_bool(row[2], default=True) if len(row) > 2 else True

        # Validação mínima
        if not nome:
            continue

        projetos.append(
            {
                "nome": nome,
                "descricao": descricao,
                "ativo": ativo,
                "src": f"{filepath.name}/Projetos",
                "rownum": i,
            }
        )

    return projetos


def parse_tipos_evento(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse planilha de tipos de evento

    Estrutura esperada:
    | Nome | Descrição | Cor (hex) |

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com dados normalizados
    """
    wb = load_workbook(filepath, data_only=True)

    # Tenta várias abas possíveis
    sheet_names = ["Tipos Evento", "TiposEvento", "Tipos", "Sheet1"]
    ws = None
    for name in sheet_names:
        if name in wb.sheetnames:
            ws = wb[name]
            break

    if ws is None:
        return []

    tipos = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 1:
            continue

        nome = normalize_str(row[0]) if len(row) > 0 else ""
        descricao = normalize_str(row[1]) if len(row) > 1 else ""
        cor = normalize_str(row[2]) if len(row) > 2 else ""

        # Validação de cor hex (opcional)
        if cor and not cor.startswith("#"):
            cor = f"#{cor}"
        if cor and len(cor) != 7:
            cor = ""

        # Validação mínima
        if not nome:
            continue

        tipos.append(
            {
                "nome": nome,
                "descricao": descricao,
                "cor": cor,
                "src": f"{filepath.name}/TiposEvento",
                "rownum": i,
            }
        )

    return tipos
