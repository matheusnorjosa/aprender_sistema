# aprender_sistema/core/scripts/import_projetos.py
import csv
import os
from core.models import Projeto

def run():
    csv_file_path = os.path.join('/app', 'data', 'Projetos.csv')

    if not os.path.exists(csv_file_path):
        print(f"❌ Arquivo não encontrado: {csv_file_path}")
        return

    criados = 0
    existentes = 0

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pular o cabeçalho

        for row in reader:
            if not row or len(row) < 3:
                print("⚠️ Linha ignorada (incompleta):", row)
                continue

            nome, descricao, ativo = row[0], row[1], row[2]

            projeto, created = Projeto.objects.get_or_create(
                nome=nome,
                defaults={'descricao': descricao, 'ativo': ativo.lower() == 'true'}
            )

            if created:
                criados += 1
                print(f"✅ Projeto '{nome}' criado com sucesso.")
            else:
                existentes += 1
                print(f"ℹ️ Projeto '{nome}' já existe.")

    print("\n📊 Resumo da importação:")
    print(f"   Criados: {criados}")
    print(f"   Já existentes: {existentes}")

