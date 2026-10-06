/**
 * Payload de criação da Nova Solicitação.
 *
 * #1666: o FK `coordenador` (responsável) vai no payload quando escolhido.
 * Decisão do dono (05/10/2026): a lista "Coordenadores Acompanhantes" saiu; `coordenador_acompanha`
 * é a resposta Sim/Não da pergunta "O coordenador responsável vai acompanhar o evento?". A resposta
 * de "pretende avaliar o formador" só vai quando a pergunta foi feita.
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
  coordenadorResponsavelId: null as number | null,
  coordenadorAcompanha: false,
  avaliar: null as { pretende: boolean; formadorAvaliadoId: number | null } | null,
};

describe('buildSolicitacaoPayload', () => {
  it('envia o FK coordenador quando um responsável é escolhido', () => {
    expect(buildSolicitacaoPayload({ ...base, coordenadorResponsavelId: 42 }).coordenador).toBe(42);
  });

  it('coordenador = null quando nenhum responsável (backend usa quem cria, se for coordenador)', () => {
    expect(buildSolicitacaoPayload(base).coordenador).toBeNull();
  });

  it('coordenador_acompanha segue a resposta Sim/Não', () => {
    expect(buildSolicitacaoPayload({ ...base, coordenadorAcompanha: true }).coordenador_acompanha).toBe(true);
    expect(buildSolicitacaoPayload({ ...base, coordenadorAcompanha: false }).coordenador_acompanha).toBe(false);
  });

  it('não manda mais a lista de coordenadores acompanhantes', () => {
    const p = buildSolicitacaoPayload(base);
    expect(p.extra_participants).toEqual({ formador_ids: [10] });
  });

  it('sem a pergunta de avaliar, não manda resposta', () => {
    const p = buildSolicitacaoPayload(base);
    expect(p).not.toHaveProperty('pretende_avaliar_formador');
    expect(p).not.toHaveProperty('formador_avaliado');
  });

  it('com a pergunta de avaliar, manda a resposta e o formador escolhido', () => {
    const sim = buildSolicitacaoPayload({ ...base, avaliar: { pretende: true, formadorAvaliadoId: 10 } });
    expect(sim.pretende_avaliar_formador).toBe(true);
    expect(sim.formador_avaliado).toBe(10);
    const nao = buildSolicitacaoPayload({ ...base, avaliar: { pretende: false, formadorAvaliadoId: null } });
    expect(nao.pretende_avaliar_formador).toBe(false);
    expect(nao.formador_avaliado).toBeNull();
  });

  it('mantém o contrato existente (municipio/projeto/tipo_evento + datas UTC)', () => {
    const p = buildSolicitacaoPayload(base);
    expect(p.municipio).toBe(1);
    expect(p.projeto).toBe(2);
    expect(p.tipo_evento).toBe(3);
    expect(String(p.inicio)).toMatch(/Z$|\+00:00$/); // formatado em UTC
  });
});
