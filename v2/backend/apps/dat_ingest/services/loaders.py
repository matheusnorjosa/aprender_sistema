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

        # Estrutura real: A=Nome curto, B=Nome Completo, C=CPF, D=Tel, E=Email, F=Cargo, G=Gerência
        nome_curto = normalize_str(row[0]) if len(row) > 0 else ""  # Ignorar
        nome = normalize_str(row[1]) if len(row) > 1 else ""  # Nome Completo
        cpf = normalize_cpf(row[2]) if len(row) > 2 else ""  # CPF (CORRIGIDO!)
        telefone = normalize_telefone(row[3]) if len(row) > 3 else ""
        email = normalize_email(row[4]) if len(row) > 4 else ""
        cargo = normalize_str(row[5]) if len(row) > 5 else "Formador"
        gerencia = normalize_str(row[6]) if len(row) > 6 else ""
        ativo = parse_bool(row[7], default=True) if len(row) > 7 else True

        # Mapear cargo para perfil
        perfil = cargo if cargo else "Formador"
        if "superintend" in perfil.lower() or "superintend" in gerencia.lower():
            perfil = "Superintendência"
        elif "coordenador" in perfil.lower():
            perfil = "Coordenador"
        elif "formador" in perfil.lower():
            perfil = "Formador"

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
    Parse municípios da aba FILTRO_PROD. da Planilha de Controle

    Estrutura real:
    Aba: ℹ️ FILTRO_PROD.
    Col A: Índice
    Col B: Município - UF ("SOBRAL - CE", "FORTALEZA - CE", "AMIGOS DO BEM")

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com dados normalizados
    """
    wb = load_workbook(filepath, data_only=True)

    # Procurar aba com nome fuzzy (pode ter emojis)
    aba_filtro = None
    for nome in wb.sheetnames:
        # Procurar por "FILTRO" e "PROD" no nome
        if 'FILTRO' in nome.upper() and 'PROD' in nome.upper():
            aba_filtro = nome
            break

    if not aba_filtro:
        return []

    ws = wb[aba_filtro]
    municipios = []
    municipios_vistos = set()  # Evitar duplicatas

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 2:
            continue

        municipio_uf = normalize_str(row[1]) if len(row) > 1 else ""  # Col B

        if not municipio_uf or municipio_uf in municipios_vistos:
            continue

        # Separar "SOBRAL - CE" → nome="SOBRAL", uf="CE"
        if " - " in municipio_uf:
            partes = municipio_uf.split(" - ", 1)
            nome = partes[0].strip()
            uf = partes[1].strip() if len(partes) > 1 else ""
        else:
            nome = municipio_uf.strip()
            uf = ""  # Ou "CE" como padrão se quiser

        # Normalizar UF
        uf_normalizado = normalize_uf(uf) if uf else ""

        # Validação mínima
        if not nome:
            continue

        municipios_vistos.add(municipio_uf)

        municipios.append(
            {
                "nome": titlecase(nome),
                "uf": uf_normalizado.upper() if uf_normalizado else "",
                "ativo": True,
                "src": f"{filepath.name}/FILTRO_PROD",
                "rownum": i,
            }
        )

    return municipios


def parse_projetos(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse projetos da aba FILTRO_PROD. da Planilha de Controle

    Estrutura real:
    Aba: ℹ️ FILTRO_PROD.
    Col E: Projeto ("ACERTA MATEMÁTICA", "LENDO E ESCREVENDO", ...)

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com dados normalizados
    """
    wb = load_workbook(filepath, data_only=True)

    # Procurar aba FILTRO_PROD.
    aba_filtro = None
    for nome in wb.sheetnames:
        if 'FILTRO' in nome.upper() and 'PROD' in nome.upper():
            aba_filtro = nome
            break

    if not aba_filtro:
        return []

    ws = wb[aba_filtro]
    projetos = []
    projetos_vistos = set()  # Evitar duplicatas

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 5:
            continue

        nome_projeto = normalize_str(row[4]) if len(row) > 4 else ""  # Col E (índice 4)

        if not nome_projeto or nome_projeto in projetos_vistos:
            continue

        # Normalizar nomes especiais
        if "IDEB" in nome_projeto.upper() or "IDEB10" in nome_projeto.upper():
            nome_projeto = "Gestão Escolar"

        projetos_vistos.add(nome_projeto)

        projetos.append(
            {
                "nome": nome_projeto,
                "descricao": "",
                "ativo": True,
                "src": f"{filepath.name}/FILTRO_PROD",
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
