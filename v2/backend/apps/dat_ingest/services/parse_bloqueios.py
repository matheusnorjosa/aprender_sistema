"""
Parser para aba Bloqueios da planilha Disponibilidade
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from datetime import datetime, time
from pathlib import Path
from typing import Any

import pytz
from openpyxl import load_workbook

from .normalizers import normalize_str


def parse_bloqueios(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse aba Bloqueios

    Estrutura:
    A: Formador
    B: Tipo (T=Total, P=Parcial)
    C: Data Início
    D: Hora Início (apenas para P)
    E: Data Fim
    F: Hora Fim (apenas para P)
    G: Motivo

    Args:
        filepath: Caminho do arquivo Excel

    Returns:
        Lista de dicts com bloqueios
    """
    wb = load_workbook(filepath, data_only=True)

    if 'Bloqueios' not in wb.sheetnames:
        return []

    ws = wb['Bloqueios']
    bloqueios = []
    tz = pytz.timezone('America/Fortaleza')

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or len(row) < 3:
            continue

        formador_nome = normalize_str(row[0]) if len(row) > 0 else ""
        tipo = normalize_str(row[1]).upper() if len(row) > 1 else ""
        data_inicio = row[2] if len(row) > 2 else None
        hora_inicio = row[3] if len(row) > 3 else None
        data_fim = row[4] if len(row) > 4 else None
        hora_fim = row[5] if len(row) > 5 else None
        motivo = normalize_str(row[6]) if len(row) > 6 else ""

        # Validar tipo
        if tipo not in ['T', 'P', 'TOTAL', 'PARCIAL']:
            continue

        # Normalizar tipo
        if tipo in ['TOTAL', 'T']:
            tipo = 'T'
        else:
            tipo = 'P'

        # Validar datas
        if not data_inicio or not data_fim:
            continue

        # Montar datetime
        try:
            if tipo == 'T':
                # Bloqueio total: dia inteiro
                inicio = tz.localize(datetime.combine(data_inicio, time(0, 0)))
                fim = tz.localize(datetime.combine(data_fim, time(23, 59)))
            else:
                # Bloqueio parcial: usar horas fornecidas
                if not hora_inicio or not hora_fim:
                    # Se faltar hora, assumir dia inteiro
                    inicio = tz.localize(datetime.combine(data_inicio, time(0, 0)))
                    fim = tz.localize(datetime.combine(data_fim, time(23, 59)))
                else:
                    # Converter hora para time se necessário
                    if isinstance(hora_inicio, str):
                        hora_inicio = datetime.strptime(hora_inicio, '%H:%M').time()
                    elif not isinstance(hora_inicio, time):
                        hora_inicio = time(0, 0)

                    if isinstance(hora_fim, str):
                        hora_fim = datetime.strptime(hora_fim, '%H:%M').time()
                    elif not isinstance(hora_fim, time):
                        hora_fim = time(23, 59)

                    inicio = tz.localize(datetime.combine(data_inicio, hora_inicio))
                    fim = tz.localize(datetime.combine(data_fim, hora_fim))
        except Exception as e:
            # Erro ao processar datas, pular linha
            continue

        bloqueios.append({
            'formador_nome': formador_nome,
            'tipo': tipo,
            'inicio': inicio,
            'fim': fim,
            'motivo': motivo,
            'src': f"{filepath.name}/Bloqueios",
            'rownum': i,
        })

    return bloqueios
