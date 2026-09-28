# Frontend Dockerfile - Vite + React
# Usado para desenvolvimento local via Docker

FROM node:22-alpine

WORKDIR /app

# Instalar dependências primeiro (cache layer). O .npmrc vem junto para o
# `npm ci` já ver o ignore-scripts=true.
COPY package*.json .npmrc ./
RUN npm ci

# Copiar código fonte
COPY . .

# Expor porta do Vite
EXPOSE 5173

# Comando para desenvolvimento com HMR
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
