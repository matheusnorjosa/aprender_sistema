# aprender_sistema/core/scripts/import_tiposdeevento.py
import csv
import os
from core.models import TipoEvento

def run():
    csv_file_path = os.path.join('/app', 'aprender_sistema', 'data', 'TiposDeEvento.csv')

    if not os.path.exists(csv_file_path):
        print(f"❌ Arquivo não encontrado: {csv_file_path}")
        return

    criados = 0
    existentes = 0

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        next(reader)  # Pular o cabeçalho

        for row in reader:
            if not row or len(row) < 1:
                print("⚠️ Linha ignorada (incompleta):", row)
                continue

            nome = row[0].strip()
            # Se não tiver coluna online, determinar pelo nome
            if len(row) > 1 and row[1].strip():
                online = row[1].strip().lower() == 'true'
            else:
                online = nome.lower() == 'online'

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
