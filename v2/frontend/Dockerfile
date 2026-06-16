# Frontend Dockerfile - Vite + React
# Usado para desenvolvimento local via Docker

FROM node:26-alpine

WORKDIR /app

# Instalar dependências primeiro (cache layer)
COPY package*.json ./
RUN npm ci

# Copiar código fonte
COPY . .

# Expor porta do Vite
EXPOSE 5173

# Comando para desenvolvimento com HMR
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
