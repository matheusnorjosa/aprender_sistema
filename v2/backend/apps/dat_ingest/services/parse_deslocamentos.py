"""
Parser para aba DESLOCAMENTO da planilha Disponibilidade
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
from openpyxl import load_workbook

from .normalizers import normalize_str


def parse_deslocamentos(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse aba DESLOCAMENTO

    Estrutura:
    A: Formador
    B: Origem (Município - UF)
    C: Destino (Município - UF)
    D: Data Saída
    E: Hora Saída
    F: Data Chegada
    G: Hora Chegada
    H: Duração (min)
    I: Meio de Transporte
    J: Observações

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com deslocamentos
    """
    wb = load_workbook(filepath, data_only=True)

    # Procurar aba (pode ter nome com maiúsculas/minúsculas)
    aba_name = None
    for nome in wb.sheetnames:
        if 'DESLOCAMENTO' in nome.upper():
            aba_name = nome
            break

    if not aba_name:
        return []

    ws = wb[aba_name]
    deslocamentos = []
    tz = pytz.timezone('America/Fortaleza')

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 7:
            continue

        formador_nome = normalize_str(row[0]) if len(row) > 0 else ""
        origem_uf = normalize_str(row[1]) if len(row) > 1 else ""
        destino_uf = normalize_str(row[2]) if len(row) > 2 else ""
        data_saida = row[3] if len(row) > 3 else None
        hora_saida = row[4] if len(row) > 4 else None
        data_chegada = row[5] if len(row) > 5 else None
        hora_chegada = row[6] if len(row) > 6 else None
        duracao_min = row[7] if len(row) > 7 else None
        meio_transporte = normalize_str(row[8]) if len(row) > 8 else ""
        observacoes = normalize_str(row[9]) if len(row) > 9 else ""

        # Validar dados obrigatórios
        if not formador_nome or not origem_uf or not destino_uf:
            continue

        if not data_saida or not hora_saida or not data_chegada or not hora_chegada:
            continue

        # Combinar data + hora
        try:
            if isinstance(hora_saida, str):
                hora_saida = datetime.strptime(hora_saida, '%H:%M').time()
            if isinstance(hora_chegada, str):
                hora_chegada = datetime.strptime(hora_chegada, '%H:%M').time()

            saida = tz.localize(datetime.combine(data_saida, hora_saida))
            chegada = tz.localize(datetime.combine(data_chegada, hora_chegada))
        except Exception as e:
            continue

        # Calcular duração se não fornecida
        if not duracao_min or duracao_min <= 0:
            duracao_min = int((chegada - saida).total_seconds() / 60)

        # Converter para int
        try:
            duracao_min = int(duracao_min)
        except:
            duracao_min = 0

        deslocamentos.append({
            'formador_nome': formador_nome,
            'origem_nome_uf': origem_uf,
            'destino_nome_uf': destino_uf,
            'saida': saida,
            'chegada': chegada,
            'duracao_minutos': duracao_min,
            'meio_transporte': meio_transporte,
            'observacoes': observacoes,
            'src': f"{filepath.name}/{aba_name}",
            'rownum': i,
        })

    return deslocamentos
