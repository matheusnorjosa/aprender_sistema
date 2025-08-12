# aprender_sistema/core/scripts/import_formadores.py
import csv
from core.models import Formador # Importa o modelo que você criou
import os

def run():
    # Caminho corrigido para o arquivo CSV dentro do container Docker
    csv_file_path = os.path.join('/app', 'data', 'Formadores.csv')

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        # Pule o cabeçalho
        next(reader) 
        
        for row in reader:
            nome = row[0]
            email = row[1]
            area_atuacao = row[2]

            # Cria um novo objeto Formador e o salva no banco de dados
            formador, created = Formador.objects.get_or_create(
                email=email,
                defaults={'nome': nome, 'area_atuacao': area_atuacao}
            )

            if created:
                print(f"Formador {nome} criado com sucesso.")
            else:
                print(f"Formador {nome} já existe.")

# Para executar este script, use o comando:
# python manage.py runscript core.scripts.import_formadores
