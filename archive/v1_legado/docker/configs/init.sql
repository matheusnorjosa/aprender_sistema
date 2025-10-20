-- Inicialização do banco de dados PostgreSQL
-- Sistema Aprender
-- Timezone: America/Fortaleza (única fonte de verdade)

-- Database já é criado pelo POSTGRES_DB
-- CREATE DATABASE aprender_sistema_db;

-- Habilitar extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Configurar timezone para America/Fortaleza (ÚNICO timezone do sistema)
SET timezone = 'America/Fortaleza';

-- Configurar timezone permanente no database (após criação)
-- Executado automaticamente ao conectar
ALTER DATABASE ${POSTGRES_DB} SET timezone TO 'America/Fortaleza';
