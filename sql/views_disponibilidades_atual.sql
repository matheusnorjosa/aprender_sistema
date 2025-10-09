-- sql/views_disponibilidades_atual.sql
-- Normaliza staging agregada (ano/mês) para uma projeção canônica por intervalo mensal fechado [início, fim]

CREATE OR REPLACE VIEW vw_disp_normalizada AS
SELECT
  s.matched_user_id        AS user_id,
  s.tipo                   AS tipo,
  make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza')                          AS ts_inicio,
  (date_trunc('month', make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza'))
     + interval '1 month' - interval '1 second')                                            AS ts_fim,
  tstzrange(
    make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza'),
    (date_trunc('month', make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza'))
       + interval '1 month' - interval '1 second'),
    '[]'
  )                                                                                         AS intervalo,
  s.origem                AS origem,
  COALESCE(s.valido, TRUE) AS valido
FROM ingestao_disponibilidadestaging s
WHERE s.matched_user_id IS NOT NULL;

CREATE OR REPLACE VIEW vw_disp_anual_agregada  AS SELECT * FROM vw_disp_normalizada WHERE tipo = 'ANUAL';
CREATE OR REPLACE VIEW vw_disp_desloc_agregada AS SELECT * FROM vw_disp_normalizada WHERE tipo = 'DESLOC';
CREATE OR REPLACE VIEW vw_disp_bloq_agregada   AS SELECT * FROM vw_disp_normalizada WHERE tipo = 'BLOQ';

CREATE INDEX IF NOT EXISTS idx_dispstg_user            ON ingestao_disponibilidadestaging (matched_user_id);
CREATE INDEX IF NOT EXISTS idx_dispstg_ano_mes         ON ingestao_disponibilidadestaging (ano, mes);
CREATE INDEX IF NOT EXISTS idx_dispstg_intervalo_gist  ON ingestao_disponibilidadestaging USING GIST (
  tstzrange(
    make_timestamptz(ano, mes, 1, 0, 0, 0, 'America/Fortaleza'),
    (date_trunc('month', make_timestamptz(ano, mes, 1, 0, 0, 0, 'America/Fortaleza')) + interval '1 month' - interval '1 second'),
    '[]'
  )
);
