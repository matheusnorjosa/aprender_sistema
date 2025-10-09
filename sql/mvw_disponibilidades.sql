DROP MATERIALIZED VIEW IF EXISTS mvw_disp_normalizada;

CREATE MATERIALIZED VIEW mvw_disp_normalizada AS
SELECT * FROM vw_disp_normalizada;

-- Índice não único para permitir múltiplos registros por user/tipo/início
CREATE INDEX IF NOT EXISTS idx_mvw_disp_norm_row
  ON mvw_disp_normalizada (user_id, tipo, ts_inicio);

-- índice GIST direto na coluna persistida (sem expressão non-immutable)
CREATE INDEX IF NOT EXISTS idx_mvw_disp_norm_intervalo_gist
  ON mvw_disp_normalizada
  USING GIST (intervalo);
