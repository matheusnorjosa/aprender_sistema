# aprender_sistema/core/scripts/import_formadores.py
import csv
import os
from django.conf import settings
from core.models import Formador

def run():
    # Caminho para o arquivo CSV baseado no BASE_DIR do projeto
    csv_file_path = os.path.join(settings.BASE_DIR, 'aprender_sistema', 'data', 'Formadores.csv')

    if not os.path.exists(csv_file_path):
        print(f"❌ Arquivo não encontrado: {csv_file_path}")
        return

    criados = 0
    existentes = 0

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        # Pular cabeçalho
        next(reader)

        for row in reader:
            if not row or len(row) < 3:
                print("⚠️ Linha ignorada (incompleta):", row)
                continue

            nome, email, area_atuacao = row[0], row[1], row[2]

            formador, created = Formador.objects.get_or_create(
                email=email,
                defaults={'nome': nome, 'area_atuacao': area_atuacao}
            )

            if created:
                criados += 1
                print(f"✅ Formador {nome} criado com sucesso.")
            else:
                existentes += 1
                print(f"ℹ️ Formador {nome} já existe.")

    print("\n📊 Resumo da importação:")
    print(f"   Criados: {criados}")
    print(f"   Já existentes: {existentes}")
