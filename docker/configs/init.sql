-- Inicialização do banco de dados PostgreSQL
-- Sistema Aprender

-- Database já é criado pelo POSTGRES_DB
-- CREATE DATABASE aprender_sistema_db;

-- Habilitar extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Configurar timezone
SET timezone = 'America/Sao_Paulo';
