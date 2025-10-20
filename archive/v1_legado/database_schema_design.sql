-- =====================================================
-- SCHEMA POSTGRESQL OTIMIZADO - SISTEMA APRENDER
-- Baseado no entendimento completo da estrutura
-- =====================================================

-- =====================================================
-- 1. EXTENSÕES E CONFIGURAÇÕES
-- =====================================================

-- Extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para busca de texto
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- Para normalização de texto

-- =====================================================
-- 2. TABELAS DE REFERÊNCIA (LOOKUP TABLES)
-- =====================================================

-- Estados brasileiros
CREATE TABLE estados (
    id SERIAL PRIMARY KEY,
    codigo_ibge INTEGER UNIQUE NOT NULL,
    sigla VARCHAR(2) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    regiao VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Municípios
CREATE TABLE municipios (
    id SERIAL PRIMARY KEY,
    codigo_ibge INTEGER UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    estado_id INTEGER NOT NULL REFERENCES estados(id),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    populacao INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Setores organizacionais
CREATE TABLE setores (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    sigla VARCHAR(20) NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Grupos de usuários (papéis)
CREATE TABLE grupos_usuarios (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    nivel_hierarquico INTEGER DEFAULT 0, -- 0=formador, 1=coordenador, 2=gerente, 3=superintendência
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 3. CATEGORIAS DE PROJETOS
-- =====================================================

-- Categorias principais (Superintendência, ACerta, Brincando, Vidas, Projetos Específicos)
CREATE TABLE categorias_projetos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    descricao TEXT,
    cor_identificacao VARCHAR(7), -- Código hex da cor
    icone VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 4. PROJETOS E COLEÇÕES
-- =====================================================

-- Projetos principais
CREATE TABLE projetos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) UNIQUE NOT NULL,
    nome VARCHAR(300) NOT NULL,
    descricao TEXT,
    categoria_id INTEGER NOT NULL REFERENCES categorias_projetos(id),
    tipo_projeto VARCHAR(50) NOT NULL, -- 'colecao' ou 'evento'
    ativo BOOLEAN DEFAULT TRUE,
    data_inicio DATE,
    data_fim DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 5. USUÁRIOS E PESSOAS
-- =====================================================

-- Pessoas (entidade física)
CREATE TABLE pessoas (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4(),
    nome_completo VARCHAR(300) NOT NULL,
    primeiro_nome VARCHAR(150) NOT NULL,
    sobrenome VARCHAR(150) NOT NULL,
    cpf VARCHAR(11) UNIQUE,
    email VARCHAR(255) UNIQUE,
    telefone VARCHAR(20),
    data_nascimento DATE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usuários do sistema (conta de acesso)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    pessoa_id INTEGER NOT NULL REFERENCES pessoas(id),
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relacionamento pessoa-setor
CREATE TABLE pessoas_setores (
    id SERIAL PRIMARY KEY,
    pessoa_id INTEGER NOT NULL REFERENCES pessoas(id),
    setor_id INTEGER NOT NULL REFERENCES setores(id),
    cargo VARCHAR(200),
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relacionamento pessoa-grupo
CREATE TABLE pessoas_grupos (
    id SERIAL PRIMARY KEY,
    pessoa_id INTEGER NOT NULL REFERENCES pessoas(id),
    grupo_id INTEGER NOT NULL REFERENCES grupos_usuarios(id),
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 6. ATRIBUIÇÕES DE PROJETOS
-- =====================================================

-- Atribuições de pessoas a projetos (coordenador, formador, gerente)
CREATE TABLE atribuicoes_projetos (
    id SERIAL PRIMARY KEY,
    pessoa_id INTEGER NOT NULL REFERENCES pessoas(id),
    projeto_id INTEGER NOT NULL REFERENCES projetos(id),
    municipio_id INTEGER REFERENCES municipios(id), -- NULL = todos os municípios
    papel VARCHAR(50) NOT NULL, -- 'coordenador', 'formador', 'gerente'
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 7. TIPOS DE EVENTOS E SOLICITAÇÕES
-- =====================================================

-- Tipos de eventos
CREATE TABLE tipos_eventos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    descricao TEXT,
    duracao_horas DECIMAL(5,2),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Solicitações de eventos
CREATE TABLE solicitacoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) UNIQUE NOT NULL,
    projeto_id INTEGER NOT NULL REFERENCES projetos(id),
    municipio_id INTEGER NOT NULL REFERENCES municipios(id),
    tipo_evento_id INTEGER NOT NULL REFERENCES tipos_eventos(id),
    solicitante_id INTEGER NOT NULL REFERENCES pessoas(id),
    coordenador_id INTEGER REFERENCES pessoas(id),
    titulo VARCHAR(300) NOT NULL,
    descricao TEXT,
    data_evento DATE NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    local_evento VARCHAR(300),
    status VARCHAR(50) DEFAULT 'pendente', -- 'pendente', 'aprovada', 'rejeitada', 'cancelada'
    observacoes TEXT,
    data_solicitacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_aprovacao TIMESTAMP WITH TIME ZONE,
    aprovador_id INTEGER REFERENCES pessoas(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Formadores atribuídos a solicitações
CREATE TABLE solicitacoes_formadores (
    id SERIAL PRIMARY KEY,
    solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id),
    formador_id INTEGER NOT NULL REFERENCES pessoas(id),
    confirmado BOOLEAN DEFAULT FALSE,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 8. ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices para busca de texto
CREATE INDEX idx_pessoas_nome_trgm ON pessoas USING gin (nome_completo gin_trgm_ops);
CREATE INDEX idx_pessoas_cpf ON pessoas (cpf) WHERE cpf IS NOT NULL;
CREATE INDEX idx_pessoas_email ON pessoas (email) WHERE email IS NOT NULL;

-- Índices para relacionamentos
CREATE INDEX idx_atribuicoes_pessoa_projeto ON atribuicoes_projetos (pessoa_id, projeto_id);
CREATE INDEX idx_atribuicoes_projeto_municipio ON atribuicoes_projetos (projeto_id, municipio_id);
CREATE INDEX idx_atribuicoes_papel ON atribuicoes_projetos (papel) WHERE ativo = TRUE;

-- Índices para solicitações
CREATE INDEX idx_solicitacoes_projeto ON solicitacoes (projeto_id);
CREATE INDEX idx_solicitacoes_municipio ON solicitacoes (municipio_id);
CREATE INDEX idx_solicitacoes_solicitante ON solicitacoes (solicitante_id);
CREATE INDEX idx_solicitacoes_status ON solicitacoes (status);
CREATE INDEX idx_solicitacoes_data_evento ON solicitacoes (data_evento);

-- Índices para usuários
CREATE INDEX idx_usuarios_pessoa ON usuarios (pessoa_id);
CREATE INDEX idx_usuarios_username ON usuarios (username);
CREATE INDEX idx_usuarios_email ON usuarios (email);

-- =====================================================
-- 9. TRIGGERS PARA AUDITORIA
-- =====================================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger em todas as tabelas principais
CREATE TRIGGER update_estados_updated_at BEFORE UPDATE ON estados FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_municipios_updated_at BEFORE UPDATE ON municipios FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_setores_updated_at BEFORE UPDATE ON setores FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_grupos_usuarios_updated_at BEFORE UPDATE ON grupos_usuarios FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_categorias_projetos_updated_at BEFORE UPDATE ON categorias_projetos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projetos_updated_at BEFORE UPDATE ON projetos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pessoas_updated_at BEFORE UPDATE ON pessoas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_usuarios_updated_at BEFORE UPDATE ON usuarios FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pessoas_setores_updated_at BEFORE UPDATE ON pessoas_setores FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pessoas_grupos_updated_at BEFORE UPDATE ON pessoas_grupos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_atribuicoes_projetos_updated_at BEFORE UPDATE ON atribuicoes_projetos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tipos_eventos_updated_at BEFORE UPDATE ON tipos_eventos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_solicitacoes_updated_at BEFORE UPDATE ON solicitacoes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_solicitacoes_formadores_updated_at BEFORE UPDATE ON solicitacoes_formadores FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 10. VIEWS PARA CONSULTAS COMUNS
-- =====================================================

-- View para pessoas com seus papéis ativos
CREATE VIEW v_pessoas_papeis AS
SELECT 
    p.id,
    p.uuid,
    p.nome_completo,
    p.primeiro_nome,
    p.sobrenome,
    p.cpf,
    p.email,
    p.telefone,
    p.ativo,
    s.nome as setor_nome,
    s.sigla as setor_sigla,
    g.nome as grupo_nome,
    g.nivel_hierarquico,
    ps.cargo,
    ps.data_inicio as data_inicio_setor,
    pg.data_inicio as data_inicio_grupo
FROM pessoas p
LEFT JOIN pessoas_setores ps ON p.id = ps.pessoa_id AND ps.ativo = TRUE
LEFT JOIN setores s ON ps.setor_id = s.id
LEFT JOIN pessoas_grupos pg ON p.id = pg.pessoa_id AND pg.ativo = TRUE
LEFT JOIN grupos_usuarios g ON pg.grupo_id = g.id;

-- View para atribuições de projetos com detalhes
CREATE VIEW v_atribuicoes_detalhadas AS
SELECT 
    ap.id,
    p.nome_completo as pessoa_nome,
    p.cpf,
    p.email,
    pr.nome as projeto_nome,
    pr.codigo as projeto_codigo,
    cat.nome as categoria_nome,
    m.nome as municipio_nome,
    m.codigo_ibge as municipio_codigo,
    e.sigla as estado_sigla,
    ap.papel,
    ap.data_inicio,
    ap.data_fim,
    ap.ativo
FROM atribuicoes_projetos ap
JOIN pessoas p ON ap.pessoa_id = p.id
JOIN projetos pr ON ap.projeto_id = pr.id
JOIN categorias_projetos cat ON pr.categoria_id = cat.id
LEFT JOIN municipios m ON ap.municipio_id = m.id
LEFT JOIN estados e ON m.estado_id = e.id;

-- View para solicitações com detalhes completos
CREATE VIEW v_solicitacoes_detalhadas AS
SELECT 
    s.id,
    s.codigo,
    s.titulo,
    s.descricao,
    pr.nome as projeto_nome,
    pr.codigo as projeto_codigo,
    cat.nome as categoria_nome,
    m.nome as municipio_nome,
    e.sigla as estado_sigla,
    te.nome as tipo_evento_nome,
    sol.nome_completo as solicitante_nome,
    coord.nome_completo as coordenador_nome,
    s.data_evento,
    s.hora_inicio,
    s.hora_fim,
    s.local_evento,
    s.status,
    s.data_solicitacao,
    s.data_aprovacao,
    aprov.nome_completo as aprovador_nome
FROM solicitacoes s
JOIN projetos pr ON s.projeto_id = pr.id
JOIN categorias_projetos cat ON pr.categoria_id = cat.id
JOIN municipios m ON s.municipio_id = m.id
JOIN estados e ON m.estado_id = e.id
JOIN tipos_eventos te ON s.tipo_evento_id = te.id
JOIN pessoas sol ON s.solicitante_id = sol.id
LEFT JOIN pessoas coord ON s.coordenador_id = coord.id
LEFT JOIN pessoas aprov ON s.aprovador_id = aprov.id;

-- =====================================================
-- 11. COMENTÁRIOS PARA DOCUMENTAÇÃO
-- =====================================================

COMMENT ON TABLE estados IS 'Estados brasileiros com códigos IBGE';
COMMENT ON TABLE municipios IS 'Municípios brasileiros com códigos IBGE e coordenadas';
COMMENT ON TABLE setores IS 'Setores organizacionais da empresa';
COMMENT ON TABLE grupos_usuarios IS 'Grupos/papéis de usuários no sistema';
COMMENT ON TABLE categorias_projetos IS 'Categorias principais de projetos (Superintendência, ACerta, etc.)';
COMMENT ON TABLE projetos IS 'Projetos e coleções do sistema';
COMMENT ON TABLE pessoas IS 'Pessoas físicas (entidade real)';
COMMENT ON TABLE usuarios IS 'Contas de acesso ao sistema';
COMMENT ON TABLE atribuicoes_projetos IS 'Atribuições de pessoas a projetos (coordenador, formador, gerente)';
COMMENT ON TABLE solicitacoes IS 'Solicitações de eventos';
COMMENT ON TABLE solicitacoes_formadores IS 'Formadores atribuídos a solicitações';

-- =====================================================
-- 12. DADOS INICIAIS ESSENCIAIS
-- =====================================================

-- Inserir estados brasileiros (principais)
INSERT INTO estados (codigo_ibge, sigla, nome, regiao) VALUES
(11, 'RO', 'Rondônia', 'Norte'),
(12, 'AC', 'Acre', 'Norte'),
(13, 'AM', 'Amazonas', 'Norte'),
(14, 'RR', 'Roraima', 'Norte'),
(15, 'PA', 'Pará', 'Norte'),
(16, 'AP', 'Amapá', 'Norte'),
(17, 'TO', 'Tocantins', 'Norte'),
(21, 'MA', 'Maranhão', 'Nordeste'),
(22, 'PI', 'Piauí', 'Nordeste'),
(23, 'CE', 'Ceará', 'Nordeste'),
(24, 'RN', 'Rio Grande do Norte', 'Nordeste'),
(25, 'PB', 'Paraíba', 'Nordeste'),
(26, 'PE', 'Pernambuco', 'Nordeste'),
(27, 'AL', 'Alagoas', 'Nordeste'),
(28, 'SE', 'Sergipe', 'Nordeste'),
(29, 'BA', 'Bahia', 'Nordeste'),
(31, 'MG', 'Minas Gerais', 'Sudeste'),
(32, 'ES', 'Espírito Santo', 'Sudeste'),
(33, 'RJ', 'Rio de Janeiro', 'Sudeste'),
(35, 'SP', 'São Paulo', 'Sudeste'),
(41, 'PR', 'Paraná', 'Sul'),
(42, 'SC', 'Santa Catarina', 'Sul'),
(43, 'RS', 'Rio Grande do Sul', 'Sul'),
(50, 'MS', 'Mato Grosso do Sul', 'Centro-Oeste'),
(51, 'MT', 'Mato Grosso', 'Centro-Oeste'),
(52, 'GO', 'Goiás', 'Centro-Oeste'),
(53, 'DF', 'Distrito Federal', 'Centro-Oeste');

-- Inserir grupos de usuários
INSERT INTO grupos_usuarios (codigo, nome, descricao, nivel_hierarquico) VALUES
('formador', 'Formador', 'Formadores que ministram eventos', 0),
('coordenador', 'Coordenador', 'Coordenadores de projetos e municípios', 1),
('gerente', 'Gerente', 'Gerentes de projetos', 2),
('superintendencia', 'Superintendência', 'Pessoal da superintendência', 3),
('controle', 'Controle', 'Pessoal de controle', 1),
('dat', 'DAT', 'Desenvolvimento e Apoio Tecnológico', 1);

-- Inserir categorias de projetos
INSERT INTO categorias_projetos (codigo, nome, descricao, cor_identificacao) VALUES
('superintendencia', 'Superintendência', 'Projetos coordenados pela superintendência', '#1f77b4'),
('acerta', 'ACerta', 'Projetos ACerta com estrutura própria', '#ff7f0e'),
('brincando', 'Brincando', 'Projetos Brincando e Aprendendo', '#2ca02c'),
('vidas', 'Vidas', 'Projetos Vidas (Ciências, Matemática, Linguagem)', '#d62728'),
('projetos_especificos', 'Projetos Específicos', 'Projetos pequenos com estrutura própria', '#9467bd');

-- Inserir setores
INSERT INTO setores (codigo, nome, sigla, descricao) VALUES
('superintendencia', 'Superintendência', 'SUP', 'Superintendência geral'),
('acerta', 'ACerta', 'ACE', 'Setor ACerta'),
('brincando', 'Brincando', 'BRI', 'Setor Brincando'),
('vidas', 'Vidas', 'VID', 'Setor Vidas'),
('controle', 'Controle', 'CON', 'Setor de Controle'),
('dat', 'DAT', 'DAT', 'Desenvolvimento e Apoio Tecnológico');

-- Inserir tipos de eventos básicos
INSERT INTO tipos_eventos (codigo, nome, descricao, duracao_horas) VALUES
('formacao', 'Formação', 'Evento de formação de professores', 8.0),
('capacitacao', 'Capacitação', 'Evento de capacitação', 4.0),
('workshop', 'Workshop', 'Workshop prático', 2.0),
('reuniao', 'Reunião', 'Reunião de trabalho', 1.0),
('evento_saeb', 'Evento SAEB', 'Evento de preparação para SAEB', 6.0);

-- =====================================================
-- FIM DO SCHEMA
-- =====================================================
