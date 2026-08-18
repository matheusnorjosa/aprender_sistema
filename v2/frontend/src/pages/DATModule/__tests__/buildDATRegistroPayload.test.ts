import { describe, it, expect } from 'vitest';
import dayjs from 'dayjs';

import { buildDATRegistroPayload } from '../DATRegistrosPage';

/**
 * M16-07: o formulário de /dat/registros perdia datas em silêncio.
 * Estas asserções codificam o contrato que o payload precisa cumprir:
 * - datas FORMAR viram `YYYY-MM-DD` (Dayjs cru -> datetime ISO -> 400 no DateField);
 * - datas AVALIAR são multivaloradas (JSONField array): o payload envia TODAS as datas
 *   escolhidas no DatePicker `multiple`. O resíduo do parcial 3954e208 truncava ao
 *   primeiro item (single-picker + firstOf/toISODateList), perdendo o histórico.
 */
describe('buildDATRegistroPayload (M16-07)', () => {
  const base = { municipio: 1, projeto_geral: 2, projeto: 3 } as const;

  it('converte todas as datas FORMAR para YYYY-MM-DD (nunca datetime ISO)', () => {
    const payload = buildDATRegistroPayload({
      ...base,
      reuniao_dat: dayjs('2026-07-20'),
      chaves_inscricao_data: dayjs('2026-07-21'),
      instrucoes_data: dayjs('2026-07-22'),
      envio_codigos_data: dayjs('2026-07-23'),
    });

    expect(payload.reuniao_dat).toBe('2026-07-20');
    expect(payload.chaves_inscricao_data).toBe('2026-07-21');
    expect(payload.instrucoes_data).toBe('2026-07-22');
    expect(payload.envio_codigos_data).toBe('2026-07-23');

    for (const k of ['reuniao_dat', 'chaves_inscricao_data', 'instrucoes_data', 'envio_codigos_data']) {
      expect(String(payload[k])).not.toMatch(/T\d{2}:/); // nenhum datetime ISO
    }
  });

  it('AVALIAR multivalorado: envia TODAS as datas escolhidas (array), sem truncar ao primeiro', () => {
    const payload = buildDATRegistroPayload({
      ...base,
      alunos_recebidos_datas: [dayjs('2026-07-20'), dayjs('2026-08-01')],
      alunos_validados_datas: [dayjs('2026-07-21')],
      alunos_importados_datas: [dayjs('2026-07-22'), dayjs('2026-09-10'), dayjs('2026-10-05')],
    });

    // TODAS as datas preservadas — o resíduo antigo reduzia o array ao primeiro item.
    expect(payload.alunos_recebidos_datas).toEqual(['2026-07-20', '2026-08-01']);
    expect(payload.alunos_validados_datas).toEqual(['2026-07-21']);
    expect(payload.alunos_importados_datas).toEqual(['2026-07-22', '2026-09-10', '2026-10-05']);

    // Os nomes singulares antigos não existem mais (o form usa o plural do serializer).
    expect(payload).not.toHaveProperty('alunos_recebidos_data');
    expect(payload).not.toHaveProperty('alunos_validados_data');
    expect(payload).not.toHaveProperty('alunos_importados_data');
  });

  it('datas ausentes: FORMAR viram null e AVALIAR viram lista vazia', () => {
    const payload = buildDATRegistroPayload({ ...base });

    expect(payload.reuniao_dat).toBeNull();
    expect(payload.chaves_inscricao_data).toBeNull();
    expect(payload.instrucoes_data).toBeNull();
    expect(payload.envio_codigos_data).toBeNull();
    expect(payload.alunos_recebidos_datas).toEqual([]);
    expect(payload.alunos_validados_datas).toEqual([]);
    expect(payload.alunos_importados_datas).toEqual([]);
  });

  it('preserva os demais campos do formulário (status, ids, observações)', () => {
    const payload = buildDATRegistroPayload({
      ...base,
      aluno_qtde: 30,
      turma_formar_status: 'criada',
      chaves_inscricao_status: 'concluido',
      obs_formar: 'ok',
    });

    expect(payload.municipio).toBe(1);
    expect(payload.aluno_qtde).toBe(30);
    expect(payload.turma_formar_status).toBe('criada');
    expect(payload.chaves_inscricao_status).toBe('concluido');
    expect(payload.obs_formar).toBe('ok');
  });
});
