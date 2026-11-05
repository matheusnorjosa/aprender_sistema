/**
 * EditSolicitacaoPage — o nome de quem está no evento (D15: o login não é nome).
 *
 * O servidor manda só `first_name` e `last_name` (sem `username`, que é o CPF). Quem tem só o
 * primeiro nome aparece com ele; sem nome nenhum, `#<id>`. Nunca "undefined" na tag, no "Remover"
 * nem no seletor "Qual formador você pretende avaliar?".
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock } = vi.hoisted(() => ({ getSolicitacaoMock: vi.fn() }));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: vi.fn(),
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/ComboBox', () => ({ default: () => null }));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));

import EditSolicitacaoPage from '../EditSolicitacaoPage';

// Como o servidor manda (UserSlimSerializer): sem `username`.
const pessoa = (id: number, first: string, last: string) => ({
  id,
  first_name: first,
  last_name: last,
  email: null,
});

const SOLICITACAO = {
  id: 42,
  usuario: 1,
  municipio: 5,
  municipio_nome: 'Sobral',
  projeto: 10,
  projeto_nome: 'Vidas',
  tipo_evento: 2,
  tipo_evento_nome: 'Formação',
  coordenador: 1,
  coordenador_nome: 'Ana Coordenadora',
  coordenador_acompanha: false,
  pretende_avaliar_formador: true,
  formador_avaliado: 99,
  avaliaveis_ids: [99],
  projeto_pergunta_avaliar_formador: true,
  inicio: '2026-10-10T12:00:00Z',
  fim: '2026-10-10T15:00:00Z',
  status: 'pendente',
  fluxo: 'SUPER',
  gcal_status: 'NONE',
  participations: [
    { role: 'COORDENADOR', usuario: pessoa(1, 'Ana', 'Coordenadora') },
    { role: 'FORMADOR', usuario: pessoa(99, 'Bruno', '') },
    { role: 'FORMADOR', usuario: pessoa(77, '', '') },
    { role: 'COORD_ACOMPANHA', usuario: pessoa(8, 'Dora', '') },
  ],
};

function renderPage(): void {
  render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('EditSolicitacaoPage — nome de quem está no evento', { timeout: 20000 }, () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset().mockResolvedValue(SOLICITACAO);
  });

  test('formador com só o primeiro nome: a tag, o "Remover" e a opção de avaliação usam o nome', async () => {
    renderPage();
    const formadores = await screen.findByLabelText('Formadores selecionados');
    expect(within(formadores).getByText('Bruno')).toBeInTheDocument();
    expect(within(formadores).getByLabelText('Remover Bruno dos formadores')).toBeInTheDocument();
    // Sem nome nenhum: o número, nunca o login.
    expect(within(formadores).getByText('#77')).toBeInTheDocument();

    const avaliado = document.getElementById('edit-formador-avaliado')!.closest('.ant-select')!;
    await waitFor(() => expect(avaliado.querySelector('.ant-select-selection-item')).toHaveTextContent(/^Bruno$/));
    expect(document.body).not.toHaveTextContent('undefined');
  });

  test('coordenador extra com só o primeiro nome: a tag e o "Remover" usam o nome', async () => {
    renderPage();
    const coordenadores = await screen.findByLabelText('Coordenadores selecionados');
    expect(within(coordenadores).getByText('Dora')).toBeInTheDocument();
    expect(within(coordenadores).getByLabelText('Remover Dora dos coordenadores')).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('undefined');
  });
});
