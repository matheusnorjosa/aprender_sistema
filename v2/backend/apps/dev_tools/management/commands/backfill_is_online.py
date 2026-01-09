"""
Management command to backfill tipo (CharField) from original spreadsheet
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false
from __future__ import annotations

from typing import Any

import pandas as pd
from django.core.management.base import BaseCommand

from apps.core.models import Solicitacao, TipoEvento


class Command(BaseCommand):
    help = "Backfill tipo (CharField) from original spreadsheet column G"

    def handle(self, *args: Any, **options: Any) -> None:
        file_path = '/app/data/csv-import/Cópia de Acompanhamento de Agenda _ 2025.xlsx'
        abas = ['ACerta', 'Outros', 'Super', 'Brincando', 'Vidas']

        tipo_evento_acomp = TipoEvento.objects.get(nome='Acompanhamento')
        tipo_evento_formacao = TipoEvento.objects.get(nome='Formação')

        stats = {'online': 0, 'presencial': 0, 'acompanhamento': 0, 'nao_encontrado': 0}

        self.stdout.write('=== Processando abas ===')

        for aba in abas:
            self.stdout.write(f'\nAba: {aba}')
            try:
                df = pd.read_excel(file_path, sheet_name=aba)

                # Filtrar linhas com dados válidos
                df_valido = df[df['município'].notna() & df['data'].notna()].copy()

                self.stdout.write(f'  Total de linhas: {len(df_valido)}')

                for idx, row in df_valido.iterrows():
                    municipio = str(row.get('município', '')).strip()
                    data = row.get('data')
                    tipo = str(row.get('tipo', '')).strip().lower()

                    # Skip if municipio is empty or data is null/NaT
                    if not municipio:
                        continue
                    if data is None or (hasattr(data, '__class__') and pd.isna(data)):
                        continue

                    # Converter data para buscar no banco
                    try:
                        data_str = pd.to_datetime(data).strftime('%Y-%m-%d')
                    except:
                        continue

                    # Buscar solicitação correspondente
                    municipio_nome = municipio.split('-')[0].strip()
                    sols = Solicitacao.objects.filter(
                        municipio__nome__icontains=municipio_nome,
                        inicio__date=data_str
                    )

                    if sols.count() == 0:
                        stats['nao_encontrado'] += 1
                        continue

                    # Mapear tipo → tipo (CharField), is_online, tipo_evento
                    tipo_original = row.get('tipo', '').strip()  # Valor original da planilha

                    if 'online' in tipo.lower():
                        is_online = True
                        tipo_evt = tipo_evento_formacao
                        stats['online'] += 1
                    elif 'acompanhamento' in tipo.lower():
                        is_online = False
                        tipo_evt = tipo_evento_acomp
                        stats['acompanhamento'] += 1
                    elif 'presencial' in tipo.lower():
                        is_online = False
                        tipo_evt = tipo_evento_formacao
                        stats['presencial'] += 1
                    else:
                        continue

                    # Atualizar: tipo (CharField com valor original), is_online, tipo_evento
                    sols.update(tipo=tipo_original, is_online=is_online, tipo_evento=tipo_evt)

            except Exception as e:
                self.stdout.write(f'  Erro: {e}')

        self.stdout.write(f'\n=== Estatísticas ===')
        self.stdout.write(f'Online: {stats["online"]}')
        self.stdout.write(f'Presencial: {stats["presencial"]}')
        self.stdout.write(f'Acompanhamento: {stats["acompanhamento"]}')
        self.stdout.write(f'Não encontrado: {stats["nao_encontrado"]}')

        # Verificar resultado
        self.stdout.write(f'\n=== Resultado Final ===')
        total = Solicitacao.objects.count()
        online = Solicitacao.objects.filter(is_online=True).count()
        presencial = Solicitacao.objects.filter(is_online=False).count()
        acomp = Solicitacao.objects.filter(tipo_evento=tipo_evento_acomp).count()
        form = Solicitacao.objects.filter(tipo_evento=tipo_evento_formacao).count()

        self.stdout.write(f'Total de eventos: {total}')
        self.stdout.write(f'  is_online=True: {online}')
        self.stdout.write(f'  is_online=False: {presencial}')
        self.stdout.write(f'  tipo_evento=Acompanhamento: {acomp}')
        self.stdout.write(f'  tipo_evento=Formação: {form}')
