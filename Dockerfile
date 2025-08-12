# Use a imagem oficial do Python 3.13.5 como base
FROM python:3.13.5

# Defina o diretório de trabalho dentro do container
WORKDIR /app

# Copie o arquivo de dependências e instale-as
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instale o netcat para que o entrypoint.sh possa usá-lo
RUN apt-get update && apt-get install -y netcat-traditional

# Copie todo o código do seu projeto para o container
COPY . .

# Expõe a porta que o Django usará (padrão 8000)
EXPOSE 8000

# Adicione permissão de execução ao script de entrada
RUN chmod +x /app/entrypoint.sh

# O ENTRYPOINT executa nosso script de espera, e o CMD são os argumentos
ENTRYPOINT ["/app/entrypoint.sh"]

# O CMD é a parte do comando que nosso script irá executar depois de esperar
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
