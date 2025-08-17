# aprender_sistema/core/scripts/import_municipios.py
import csv
import os
from core.models import Municipio

def run():
    # Caminho corrigido para o arquivo CSV dentro do container Docker
    csv_file_path = os.path.join('/app', 'aprender_sistema', 'data', 'Municipios.csv')

    if not os.path.exists(csv_file_path):
        print(f"❌ Arquivo não encontrado: {csv_file_path}")
        return

    criados = 0
    existentes = 0

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pular o cabeçalho

        for row in reader:
            if not row or len(row) < 1:
                print("⚠️ Linha ignorada (incompleta):", row)
                continue

            nome = row[0]

            municipio, created = Municipio.objects.get_or_create(
                nome=nome,
            )

            if created:
                criados += 1
                print(f"✅ Município '{nome}' criado com sucesso.")
            else:
                existentes += 1
                print(f"ℹ️ Município '{nome}' já existe.")

    print("\n📊 Resumo da importação:")
    print(f"   Criados: {criados}")
    print(f"   Já existentes: {existentes}")
