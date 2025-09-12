-- ======================================
-- 🛠️ DATABASE INITIALIZATION - DEVELOPMENT
-- Sistema Aprender
-- ======================================

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create development-specific configurations
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 0;

-- Reload configuration
SELECT pg_reload_conf();

-- Create test database for running tests
CREATE DATABASE aprender_sistema_test WITH OWNER postgres;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE aprender_sistema_dev TO postgres;
GRANT ALL PRIVILEGES ON DATABASE aprender_sistema_test TO postgres;

-- Insert development notice
DO $$
BEGIN
    RAISE NOTICE '🛠️  Development database initialized successfully!';
    RAISE NOTICE '📊 Database: aprender_sistema_dev';
    RAISE NOTICE '🧪 Test database: aprender_sistema_test';
    RAISE NOTICE '👤 User: postgres';
END $$;