import { describe, it, expect } from 'vitest';

import { TURMA_STATUS_OPTIONS, ETAPA_STATUS_OPTIONS } from '../constants';
import { renderStatusIcon } from '../helpers';

/**
 * M16-08: a UI usava uma única lista (`pendente/em_andamento/concluido`) para dois enums
 * distintos do backend. Ofereciam-se valores que o serializer rejeitava (400) e escondiam-se
 * valores válidos (`criada`, `erro`, `nao_aplicavel`). Estes valores espelham
 * DATRegistro.TURMA_STATUS_CHOICES e DATRegistro.STATUS_CHOICES.
 */
const TURMA_BACKEND = ['criada', 'pendente', 'erro'];
const ETAPA_BACKEND = ['concluido', 'pendente', 'em_andamento', 'nao_aplicavel', 'erro'];

describe('DATRegistros status options — contrato com o backend (M16-08)', () => {
  it('TURMA_STATUS_OPTIONS bate exatamente com TURMA_STATUS_CHOICES', () => {
    expect(TURMA_STATUS_OPTIONS.map((o) => o.value).sort()).toEqual([...TURMA_BACKEND].sort());
  });

  it('ETAPA_STATUS_OPTIONS bate exatamente com STATUS_CHOICES', () => {
    expect(ETAPA_STATUS_OPTIONS.map((o) => o.value).sort()).toEqual([...ETAPA_BACKEND].sort());
  });

  it('nenhuma opção oferece valor fora dos choices do backend (nada dá 400)', () => {
    for (const o of TURMA_STATUS_OPTIONS) expect(TURMA_BACKEND).toContain(o.value);
    for (const o of ETAPA_STATUS_OPTIONS) expect(ETAPA_BACKEND).toContain(o.value);
  });
});

describe('renderStatusIcon — erro distinto de nao_aplicavel (M16-08)', () => {
  it('erro e nao_aplicavel renderizam ícones distintos (antes ambos caíam no cinza)', () => {
    const erro = renderStatusIcon('erro');
    const na = renderStatusIcon('nao_aplicavel');
    expect(erro.type).not.toBe(na.type);
    expect(erro.props.className).not.toEqual(na.props.className);
  });

  it('erro é vermelho e nao_aplicavel é cinza', () => {
    expect(renderStatusIcon('erro').props.className).toContain('text-red');
    expect(renderStatusIcon('nao_aplicavel').props.className).toContain('text-gray');
  });

  it('valor desconhecido não é renderizado como nao_aplicavel', () => {
    expect(renderStatusIcon('xpto').type).not.toBe(renderStatusIcon('nao_aplicavel').type);
  });
});
