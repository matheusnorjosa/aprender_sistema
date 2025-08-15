# aprender_sistema/core/scripts/import_tiposdeevento.py
import csv
import os
from core.models import TipoEvento

def run():
    csv_file_path = os.path.join('/app', 'data', 'TiposDeEvento.csv')

    if not os.path.exists(csv_file_path):
        print(f"❌ Arquivo não encontrado: {csv_file_path}")
        return

    criados = 0
    existentes = 0

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pular o cabeçalho

        for row in reader:
            if not row or len(row) < 2:
                print("⚠️ Linha ignorada (incompleta):", row)
                continue

            nome, online_str = row[0], row[1]
            online = online_str.lower() == 'true'

            tipoevento, created = TipoEvento.objects.get_or_create(
                nome=nome,
                defaults={'online': online}
            )

            if created:
                criados += 1
                print(f"✅ Tipo de Evento '{nome}' criado com sucesso.")
            else:
                existentes += 1
                print(f"ℹ️ Tipo de Evento '{nome}' já existe.")

    print("\n📊 Resumo da importação:")
    print(f"   Criados: {criados}")
    print(f"   Já existentes: {existentes}")
