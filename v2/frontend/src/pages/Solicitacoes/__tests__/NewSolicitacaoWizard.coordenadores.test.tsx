/**
 * Nova Solicitação — vários coordenadores no mesmo horário (decisão do dono, 03/11/2026).
 *
 * - A caixa "Coordenador(es)" aceita mais de um. O 1º escolhido é o responsável (a pergunta "vai
 *   acompanhar?" é sobre ele); os demais vão em `extra_participants.coord_acompanha_ids`, na ordem
 *   de escolha.
 * - Os demais ocupam a agenda sempre: a prévia confere a agenda deles com "Sim" ou "Não".
 * - O erro do servidor em `coord_acompanha_ids` volta para a caixa de coordenadores.
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { renderNoRoteador } from '../../../test/comRoteador';
import { botaoDoTexto, cartao, grupoDaPergunta, PERGUNTA_ACOMPANHA } from './localizadores';

const {
  createSolicitacoesEmLoteMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  coordenadoresEscolhidos,
} = vi.hoisted(() => ({
  createSolicitacoesEmLoteMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  coordenadoresEscolhidos: { atual: [] as Array<{ id: number; label: string }> },
}));

vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: createSolicitacoesEmLoteMock }));
vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
  checkAvailabilityMany: checkAvailabilityManyMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button
      type="button"
      data-testid="set-date"
      onClick={() => onChange?.({ date: '2026-08-01', start: '09:00', end: '11:00' })}
    >
      set-date
    </button>
  ),
}));
vi.mock('../../../components/FormadoresPicker', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button
      type="button"
      data-testid="pick-formador"
      onClick={() => onChange?.([{ id: 99, label: 'Bruno Formador', avaliavel: false }])}
    >
      pick-formador
    </button>
  ),
}));
// A caixa de coordenadores: recebe do Form.Item o id e os aria-* (rótulo, explicação e erro).
vi.mock('../../../components/CoordenadoresPicker', () => ({
  default: ({
    value = [],
    onChange,
    id,
    'aria-describedby': descrito,
    'aria-invalid': invalido,
  }: {
    value?: Array<{ id: number; label: string }>;
    onChange?: (v: unknown) => void;
    id?: string;
    'aria-describedby'?: string;
    'aria-invalid'?: boolean | 'true' | 'false';
  }) => (
    <>
      <input
        data-testid="caixa-coordenadores"
        id={id}
        aria-describedby={descrito}
        aria-invalid={invalido}
        readOnly
        value={value.map((c) => c.label).join(', ')}
      />
      <button type="button" data-testid="pick-coordenadores" onClick={() => onChange?.(coordenadoresEscolhidos.atual)}>
        pick-coordenadores
      </button>
      <button type="button" data-testid="tirar-primeiro" onClick={() => onChange?.(value.slice(1))}>
        tirar-primeiro
      </button>
      <button type="button" data-testid="tirar-ultimo" onClick={() => onChange?.(value.slice(0, -1))}>
        tirar-ultimo
      </button>
    </>
  ),
}));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
}: {
  placeholder?: string;
  lookupFunction: (q: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  const testid = placeholder.includes('munic') ? 'cb-municipio' : placeholder.includes('projeto') ? 'cb-projeto' : 'cb-tipo';
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') {
          onChange?.({ id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER', pergunta_avaliar_formador: false, responsavel_padrao: true });
        } else if (testid === 'cb-tipo') onChange?.({ id: 789, label: 'Formação' });
        else onChange?.({ id: 456, label: 'Fortaleza - CE' });
      }}
    >
      {testid}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

const CARLA = { id: 7, label: 'Carla Coordenadora' };
const DORA = { id: 8, label: 'Dora Coordenadora' };
const EVA = { id: 5, label: 'Eva Coordenadora' };
const ESPERA = { timeout: 5000 };

async function preencher(acompanha: 'Sim' | 'Não' = 'Não'): Promise<void> {
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
  fireEvent.click(screen.getByTestId('pick-formador'));
  fireEvent.click(screen.getByTestId('pick-coordenadores'));
  fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA)).getByLabelText(acompanha));
  await waitFor(() => expect(screen.queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(), ESPERA);
}

const criar = (): HTMLElement => botaoDoTexto('Criar solicitação');
const ultimosIds = (): number[] =>
  [...(checkAvailabilityManyMock.mock.calls.at(-1)?.[0].usuarios_ids as number[])].sort((a, b) => a - b);

describe('NewSolicitacaoWizard — vários coordenadores (03/11/2026)', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    coordenadoresEscolhidos.atual = [CARLA, DORA, EVA];
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacoesEmLoteMock.mockResolvedValue({ eventos: [{ indice: 0, id: 1, status: 'aprovado' }] });
  });

  test('a caixa se chama "Coordenador(es)" e diz, ligado a ela, que o 1º escolhido é o responsável', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    const caixa = await screen.findByTestId('caixa-coordenadores');
    expect(document.querySelector(`label[for="${caixa.id}"]`)).toHaveTextContent(/^Coordenador\(es\)$/);
    const descricao = (caixa.getAttribute('aria-describedby') ?? '')
      .split(' ')
      .map((id) => document.getElementById(id)?.textContent ?? '')
      .join(' ');
    expect(descricao).toContain('O 1º escolhido é o coordenador responsável.');
    // Os textos de ajuda que o dono mandou tirar não voltam.
    expect(screen.queryByText(/Coordenador que vai atuar/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Se Sim, a agenda/)).not.toBeInTheDocument();
    // A pergunta continua sobre o responsável.
    expect(grupoDaPergunta(PERGUNTA_ACOMPANHA)).toBeInTheDocument();
  });

  test('envia o 1º como responsável e os demais em coord_acompanha_ids, na ordem de escolha', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await preencher();
    fireEvent.click(criar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalled(), ESPERA);
    const payload = createSolicitacoesEmLoteMock.mock.calls[0][0][0];
    expect(payload.coordenador).toBe(7);
    expect(payload.coordenador_acompanha).toBe(false);
    expect(payload.extra_participants).toEqual({ formador_ids: [99], coord_acompanha_ids: [8, 5] });
  });

  test('a prévia de agenda confere sempre os demais coordenadores; o responsável só com "Sim"', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await preencher('Não');
    await waitFor(() => expect(ultimosIds()).toEqual([5, 8, 99]), ESPERA);

    fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA)).getByLabelText('Sim'));
    await waitFor(() => expect(ultimosIds()).toEqual([5, 7, 8, 99]), ESPERA);
  });

  test('trocar o 1º (o responsável) apaga a resposta de acompanhar; mexer só nos demais a mantém', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await preencher('Sim');
    const grupo = (): HTMLElement => grupoDaPergunta(PERGUNTA_ACOMPANHA);

    fireEvent.click(screen.getByTestId('tirar-ultimo'));
    expect(within(grupo()).getByLabelText('Sim')).toBeChecked();

    fireEvent.click(screen.getByTestId('tirar-primeiro'));
    await waitFor(() => expect(within(grupo()).getByLabelText('Sim')).not.toBeChecked());
    expect(within(grupo()).getByLabelText('Não')).not.toBeChecked();
    fireEvent.click(criar());
    expect(
      await screen.findByText('Responda se o coordenador responsável vai acompanhar o evento.', undefined, ESPERA),
    ).toBeInTheDocument();
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
  });

  test('o erro do servidor em coord_acompanha_ids volta para a caixa de coordenadores', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await preencher();
    const motivo = 'Cada coordenador precisa ser coordenador da gerência do projeto.';
    createSolicitacoesEmLoteMock.mockRejectedValueOnce({
      status: 400,
      response: {
        status: 400,
        data: {
          code: 'lote_invalido',
          detail: '1 de 1 eventos tem problema. Nada foi criado.',
          errors: { itens: [{ indice: 0, code: 'INVALID', detail: motivo, errors: { coord_acompanha_ids: [motivo] } }] },
        },
      },
    });
    fireEvent.click(criar());

    const c1 = cartao(1);
    const erro = await within(c1).findByText(motivo, undefined, ESPERA);
    const caixa = within(c1).getByTestId('caixa-coordenadores');
    expect(caixa).toHaveAttribute('aria-invalid', 'true');
    expect(erro.closest('.ant-form-item')).toContainElement(caixa);
  });
});
