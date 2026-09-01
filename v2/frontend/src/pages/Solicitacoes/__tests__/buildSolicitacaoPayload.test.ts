/**
 * #1666: o wizard coletava "Coordenadores Acompanhantes" (M2M) mas NUNCA enviava o FK
 * `coordenador` (dono/responsável) → o backend caía no default (o criador). O fix captura
 * um "Coordenador responsável" e o envia como `coordenador`, distinto dos acompanhantes.
 *
 * RED sem o campo `coordenador` no payload construído.
 */
import { describe, it, expect } from 'vitest';
import { buildSolicitacaoPayload } from '../NewSolicitacaoWizard';

const base = {
  municipioId: 1,
  projetoId: 2,
  tipoEventoId: 3,
  inicio: '2026-05-10T13:00:00',
  fim: '2026-05-10T17:00:00',
  tipo: '',
  encontro: '',
  segmento: '',
  observacoes: '',
  local: '',
  isOnline: false,
  formadorIds: [10],
  coordAcompanhaIds: [],
  coordenadorResponsavelId: null as number | null,
};

describe('buildSolicitacaoPayload (#1666)', () => {
  it('envia o FK coordenador quando um responsável é escolhido', () => {
    expect(buildSolicitacaoPayload({ ...base, coordenadorResponsavelId: 42 }).coordenador).toBe(42);
  });

  it('coordenador = null quando nenhum responsável (backend usa o default)', () => {
    expect(buildSolicitacaoPayload(base).coordenador).toBeNull();
  });

  it('o FK coordenador (dono) é DISTINTO dos coord_acompanha_ids (M2M acompanhantes)', () => {
    const p = buildSolicitacaoPayload({ ...base, coordenadorResponsavelId: 42, coordAcompanhaIds: [7, 8] });
    expect(p.coordenador).toBe(42);
    expect((p.extra_participants as { coord_acompanha_ids: number[] }).coord_acompanha_ids).toEqual([7, 8]);
    expect(p.coordenador_acompanha).toBe(true);
  });

  it('mantém o contrato existente (municipio/projeto/tipo_evento + datas UTC)', () => {
    const p = buildSolicitacaoPayload(base);
    expect(p.municipio).toBe(1);
    expect(p.projeto).toBe(2);
    expect(p.tipo_evento).toBe(3);
    expect(String(p.inicio)).toMatch(/Z$|\+00:00$/); // formatado em UTC
  });
});
