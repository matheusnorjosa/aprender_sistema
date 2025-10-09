-- ===============================================================
-- Views SQL das Disponibilidades - DIA 3
-- ===============================================================
-- ⚠️  NOTA: A tabela core_stagingdisponanual existente tem estrutura diferente
-- Estrutura atual: id, nome_formador, ano, mes, horas, usuario_id
-- Estrutura esperada: id, matched_user_id, tipo, ts_inicio, ts_fim, origem, valido
--
-- Esta é uma especificação FUTURA para quando a estrutura for ajustada.
-- Por enquanto, a tabela existente serve apenas para dados anuais agregados.
--
-- Criado: 07/10/2025
-- Status: AGUARDANDO MIGRAÇÃO DA ESTRUTURA DA TABELA
-- ===============================================================

-- VIEW BASE: Disponibilidades válidas com intervalo de tempo
CREATE OR REPLACE VIEW vw_disp_base AS
SELECT
  s.id,
  s.matched_user_id AS user_id,
  s.tipo,
  s.ts_inicio,
  s.ts_fim,
  tstzrange(s.ts_inicio, s.ts_fim, '[]') AS intervalo,
  s.origem,
  s.valido
FROM core_stagingdisponanual s
WHERE s.matched_user_id IS NOT NULL
  AND s.valido IS TRUE;

COMMENT ON VIEW vw_disp_base IS 'View base de disponibilidades válidas com user_id e intervalo tstzrange';

-- VIEW: Disponibilidades Anuais
CREATE OR REPLACE VIEW vw_disp_anual AS
SELECT * FROM vw_disp_base
WHERE tipo = 'ANUAL';

COMMENT ON VIEW vw_disp_anual IS 'Disponibilidades do tipo ANUAL (períodos de férias, licenças anuais)';

-- VIEW: Deslocamentos
CREATE OR REPLACE VIEW vw_disp_desloc AS
SELECT * FROM vw_disp_base
WHERE tipo = 'DESLOC';

COMMENT ON VIEW vw_disp_desloc IS 'Disponibilidades do tipo DESLOC (deslocamentos entre municípios)';

-- VIEW: Bloqueios
CREATE OR REPLACE VIEW vw_disp_bloq AS
SELECT * FROM vw_disp_base
WHERE tipo = 'BLOQ';

COMMENT ON VIEW vw_disp_bloq IS 'Disponibilidades do tipo BLOQ (bloqueios pontuais de agenda)';

-- ===============================================================
-- ÍNDICES NA TABELA BASE (staging)
-- ===============================================================
-- Para otimizar queries por usuário, datas e intervalos

-- Índice por usuário (queries de disponibilidade de um formador específico)
CREATE INDEX IF NOT EXISTS idx_stg_disp_user
ON core_stagingdisponanual (matched_user_id)
WHERE matched_user_id IS NOT NULL;

-- Índice por data de início (queries ordenadas cronologicamente)
CREATE INDEX IF NOT EXISTS idx_stg_disp_inicio
ON core_stagingdisponanual (ts_inicio)
WHERE ts_inicio IS NOT NULL;

-- Índice por data de fim (queries de range de datas)
CREATE INDEX IF NOT EXISTS idx_stg_disp_fim
ON core_stagingdisponanual (ts_fim)
WHERE ts_fim IS NOT NULL;

-- Índice GIST para queries de sobreposição de intervalos (overlaps)
-- Permite queries eficientes do tipo "quem está disponível entre X e Y?"
CREATE INDEX IF NOT EXISTS idx_stg_disp_intervalo_gist
ON core_stagingdisponanual
USING GIST (tstzrange(ts_inicio, ts_fim, '[]'))
WHERE ts_inicio IS NOT NULL
  AND ts_fim IS NOT NULL
  AND matched_user_id IS NOT NULL;

-- Índice composto para filtros comuns (tipo + usuário + válido)
CREATE INDEX IF NOT EXISTS idx_stg_disp_tipo_user_valido
ON core_stagingdisponanual (tipo, matched_user_id, valido)
WHERE valido IS TRUE;

-- ===============================================================
-- EXEMPLOS DE USO
-- ===============================================================

-- Exemplo 1: Buscar disponibilidades de um usuário específico
-- SELECT * FROM vw_disp_base WHERE user_id = 'uuid-do-usuario';

-- Exemplo 2: Buscar bloqueios em um período específico
-- SELECT * FROM vw_disp_bloq
-- WHERE intervalo && tstzrange('2025-10-01', '2025-10-31', '[]');

-- Exemplo 3: Buscar usuários disponíveis em uma data
-- SELECT DISTINCT user_id
-- FROM vw_disp_base
-- WHERE intervalo @> '2025-10-15 14:00:00'::timestamptz;

-- Exemplo 4: Buscar conflitos de disponibilidade (overlaps)
-- SELECT d1.user_id, d1.intervalo, d2.intervalo
-- FROM vw_disp_base d1
-- JOIN vw_disp_base d2 ON d1.user_id = d2.user_id
--   AND d1.id < d2.id
--   AND d1.intervalo && d2.intervalo;

-- ===============================================================
-- NOTAS DE PERFORMANCE
-- ===============================================================
-- 1. O índice GIST permite queries O(log n) para overlaps
-- 2. tstzrange usa inclusivo-inclusivo '[]' para incluir bordas
-- 3. Operadores úteis:
--    - && : overlaps (tem sobreposição)
--    - @> : contains (contém um ponto ou intervalo)
--    - <@ : is contained by (está contido em)
-- 4. Para queries muito frequentes, considere MATERIALIZED VIEWS
-- ===============================================================
