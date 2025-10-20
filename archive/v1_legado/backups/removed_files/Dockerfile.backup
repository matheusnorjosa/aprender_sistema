# Use a imagem oficial do Python 3.13.5 como base
FROM python:3.13.5

# Variáveis úteis para containers Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Diretório de trabalho
WORKDIR /app

# System deps (netcat) + limpeza de cache do apt
RUN apt-get update \
    && apt-get install -y --no-install-recommends netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copie e instale as dependências Python primeiro (melhor cache)
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Agora copie o restante do código
COPY . .

# Expõe a porta do Django
EXPOSE 8000

# Permissão de execução ao entrypoint
RUN chmod +x /app/entrypoint.sh

# ENTRYPOINT + CMD
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
