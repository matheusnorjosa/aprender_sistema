/**
 * EditSolicitacaoPage — evento de dois projetos (combo, #2036; decisões do dono de 07 e 08/11/2026).
 *
 * Cada campo mostra um projeto (o seletor não mostra o rótulo "A + B" do evento). O 2º só lista os
 * compatíveis; trocar o 1º limpa o 2º e tirar o 1º sobe o 2º. Ganhar, trocar ou perder o 2º numa SUPER
 * aprovada volta para aprovação; inverter os dois não muda nada (o servidor compara o conjunto).
 */
import { useEffect } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock, updateSolicitacaoMock, lookupProjetosMock, escolha } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  updateSolicitacaoMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  escolha: {
    projeto: { id: 125, label: 'Miudezas', fluxo: 'SUPER' },
    projeto2: { id: 125, label: 'Miudezas', fluxo: 'SUPER' },
  },
}));

const PH_PROJETO = 'Busque ou selecione um projeto';
const PH_PROJETO_2 = 'Opcional: o outro projeto do combo';

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: updateSolicitacaoMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
}));
function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  value,
}: {
  placeholder?: string;
  lookupFunction?: (q: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  value?: { label?: string } | null;
}) {
  useEffect(() => {
    void lookupFunction?.('');
  }, [lookupFunction]);
  if (placeholder !== PH_PROJETO && placeholder !== PH_PROJETO_2) return null;
  return (
    <>
      <button type="button" onClick={() => onChange?.(placeholder === PH_PROJETO ? escolha.projeto : escolha.projeto2)}>
        {placeholder}
      </button>
      <button type="button" onClick={() => onChange?.(null)}>{`limpar: ${placeholder}`}</button>
      <output>{`valor: ${placeholder}: ${value?.label ?? ''}`}</output>
    </>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

import message from 'antd/es/message';
import { ComAcesso } from '../../../test/comAcesso';
import EditSolicitacaoPage from '../EditSolicitacaoPage';

const COMBO = {
  id: 42,
  usuario: 1,
  municipio: 5,
  municipio_nome: 'Sobral',
  projeto: 123,
  projeto_2: 124,
  projeto_nome: 'Cataventos + UNI DUNI TÊ',
  projetos: [
    { id: 123, nome: 'UNI DUNI TÊ' },
    { id: 124, nome: 'Cataventos' },
  ],
  tipo_evento: 2,
  tipo_evento_nome: 'Formação',
  inicio: '2026-12-10T12:00:00Z',
  fim: '2026-12-10T15:00:00Z',
  status: 'aprovado',
  fluxo: 'SUPER',
  gcal_status: 'NONE',
  participations: [
    { role: 'FORMADOR', usuario: { id: 7, username: 'formador1', first_name: 'Ana', last_name: 'Lima', email: '' } },
  ],
};

const AVISO_VOLTA = 'Esta mudança volta o evento para aprovação.';

const valorDe = (placeholder: string): string =>
  screen
    .getByText((_, el) => el?.tagName === 'OUTPUT' && (el.textContent ?? '').startsWith(`valor: ${placeholder}:`))
    .textContent.slice(`valor: ${placeholder}: `.length);

async function abrir(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = userEvent.setup();
  render(
    <ComAcesso policies={[]}>
      <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
        <Routes>
          <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
        </Routes>
      </MemoryRouter>
    </ComAcesso>,
  );
  await screen.findByText('Editar Solicitação #42');
  return user;
}

const salvar = async (user: ReturnType<typeof userEvent.setup>): Promise<Record<string, unknown>> => {
  await user.click(screen.getByRole('button', { name: /salvar alterações/i }));
  await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
  return updateSolicitacaoMock.mock.calls[0]![1] as Record<string, unknown>;
};

describe('EditSolicitacaoPage — evento de dois projetos', { timeout: 20000 }, () => {
  beforeEach(() => {
    escolha.projeto = { id: 125, label: 'Miudezas', fluxo: 'SUPER' };
    escolha.projeto2 = { id: 125, label: 'Miudezas', fluxo: 'SUPER' };
    getSolicitacaoMock.mockReset().mockResolvedValue(COMBO);
    updateSolicitacaoMock.mockReset().mockResolvedValue(COMBO);
    lookupProjetosMock.mockReset().mockResolvedValue([]);
    vi.spyOn(message, 'success').mockImplementation(vi.fn());
    vi.spyOn(message, 'warning').mockImplementation(vi.fn());
  });

  test('cada campo mostra um projeto, não o rótulo do evento', async () => {
    await abrir();
    expect(valorDe(PH_PROJETO)).toBe('UNI DUNI TÊ');
    expect(valorDe(PH_PROJETO_2)).toBe('Cataventos');
  });

  test('o 2º lista só os compatíveis com o 1º', async () => {
    await abrir();
    await waitFor(() =>
      expect(lookupProjetosMock).toHaveBeenCalledWith('', { com_compra: true, mesmo_grupo_de: 123 }),
    );
  });

  test('salvar sem mexer manda os dois e não avisa volta para aprovação', async () => {
    const user = await abrir();
    expect(screen.queryByText(AVISO_VOLTA)).not.toBeInTheDocument();
    expect(await salvar(user)).toMatchObject({ projeto: 123, projeto_2: 124 });
  });

  test('tirar o 2º manda null e avisa que volta para aprovação', async () => {
    const user = await abrir();
    await user.click(screen.getByText(`limpar: ${PH_PROJETO_2}`));
    expect(await screen.findByText(AVISO_VOLTA)).toBeInTheDocument();
    expect(await salvar(user)).toMatchObject({ projeto: 123, projeto_2: null });
  });

  test('trocar o 1º limpa o 2º', async () => {
    const user = await abrir();
    await user.click(screen.getByText(PH_PROJETO));
    await waitFor(() => expect(valorDe(PH_PROJETO_2)).toBe(''));
    expect(valorDe(PH_PROJETO)).toBe('Miudezas');
  });

  test('inverter os dois não avisa volta para aprovação', async () => {
    const user = await abrir();
    // Tirar o 1º sobe o 2º; depois o antigo 1º entra como 2º.
    await user.click(screen.getByText(`limpar: ${PH_PROJETO}`));
    await waitFor(() => expect(valorDe(PH_PROJETO)).toBe('Cataventos'));
    expect(valorDe(PH_PROJETO_2)).toBe('');
    escolha.projeto2 = { id: 123, label: 'UNI DUNI TÊ', fluxo: 'SUPER' };
    await user.click(screen.getByText(PH_PROJETO_2));
    await waitFor(() => expect(valorDe(PH_PROJETO_2)).toBe('UNI DUNI TÊ'));
    expect(screen.queryByText(AVISO_VOLTA)).not.toBeInTheDocument();
  });

  test('evento de um projeto não manda projeto_2', async () => {
    getSolicitacaoMock.mockResolvedValue({
      ...COMBO,
      projeto_2: null,
      projeto_nome: 'UNI DUNI TÊ',
      projetos: [{ id: 123, nome: 'UNI DUNI TÊ' }],
    });
    const user = await abrir();
    expect(valorDe(PH_PROJETO_2)).toBe('');
    expect(await salvar(user)).not.toHaveProperty('projeto_2');
  });
});
