# ======================================
# DOCKERFILE - FRONTEND REACT
# Sistema Aprender - Interface React
# ======================================

# Stage 1: Development
FROM node:20-alpine AS development

WORKDIR /app

# Copiar arquivos de dependências
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar código fonte
COPY . .

# Expor porta de desenvolvimento
EXPOSE 3000

# Comando de desenvolvimento
CMD ["npm", "start"]


# Stage 2: Build para produção
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build


# Stage 3: Produção com Nginx
FROM nginx:alpine AS production

# Copiar build do React
COPY --from=build /app/build /usr/share/nginx/html

# Copiar configuração customizada do Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
