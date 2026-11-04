/**
 * EditSolicitacaoPage — regra da compra nas listas (14/10/2026).
 *
 * A lista de projetos esconde o projeto "em espera" (`com_compra`). A de municípios traz também os
 * sem compra para o projeto escolhido, marcados (`marcar_sem_compra` + `projeto_id`; pedido do dono,
 * 03/11/2026): escolher um deles avisa que o evento vai para aprovação. Quem é isento (superusuário ou
 * a capacidade) recebe tudo do servidor sem marca, então a tela manda os filtros sempre.
 */
import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock, lookupProjetosMock, lookupMunicipiosWithFiltersMock, escolha } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  // O município que o clique no campo escolhe (cada teste troca).
  escolha: { municipio: { id: 6, label: 'Crato-CE', kind: 'municipio', sem_compra: true, projeto_em_espera: false } },
}));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: vi.fn(),
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  'aria-describedby': descritoPor,
}: {
  placeholder?: string;
  lookupFunction: (query: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  'aria-describedby'?: string;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  const item = placeholder.includes('município') ? escolha.municipio : { id: 77, label: 'Projeto Novo' };
  return (
    <button type="button" aria-describedby={descritoPor} onClick={() => onChange?.(item)}>
      {placeholder}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import EditSolicitacaoPage from '../EditSolicitacaoPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('EditSolicitacaoPage — regra da compra', { timeout: 20000 }, () => {
  beforeEach(() => {
    if (!window.matchMedia) {
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });
    }
    vi.clearAllMocks();
    escolha.municipio = { id: 6, label: 'Crato-CE', kind: 'municipio', sem_compra: true, projeto_em_espera: false };
    lookupProjetosMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getSolicitacaoMock.mockResolvedValue({
      id: 42,
      municipio: 5,
      municipio_nome: 'Sobral',
      projeto: 10,
      projeto_nome: 'Vidas',
      tipo_evento: 2,
      tipo_evento_nome: 'Formação',
      coordenador_acompanha: false,
      inicio: '2026-10-10T12:00:00Z',
      fim: '2026-10-10T15:00:00Z',
      status: 'aprovado',
      participations: [],
      fluxo: 'NAO_SUPER',
      gcal_status: 'NONE',
    });
  });

  test('projetos com com_compra e municípios marcados pelo projeto escolhido', async () => {
    renderPage();

    await waitFor(() => {
      expect(lookupProjetosMock).toHaveBeenCalledWith('', { com_compra: true });
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenLastCalledWith({
        q: '',
        com_compra: true,
        marcar_sem_compra: true,
        projeto_id: 10,
      });
    });

    // Trocar o projeto recarrega os municípios com o projeto novo.
    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));
    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        com_compra: true,
        marcar_sem_compra: true,
        projeto_id: 77,
      });
    });
  });

  test('escolher município sem compra avisa, ligado ao campo, que o evento vai para aprovação', async () => {
    renderPage();
    const aviso = 'Sem compra neste município para este projeto. O evento vai para aprovação.';
    const municipio = await screen.findByRole('button', { name: 'Busque ou selecione um município' });
    expect(screen.queryByText(aviso)).not.toBeInTheDocument();

    fireEvent.click(municipio);

    const texto = await screen.findByText(aviso);
    const id = municipio.getAttribute('aria-describedby') ?? '';
    expect(id).not.toBe('');
    expect(document.getElementById(id)?.contains(texto)).toBe(true);
    expect(texto.closest('.ant-alert-warning')).not.toBeNull();

    // Trocar o projeto: a marca era do par antigo; a tela reconfere o par novo (aqui, com compra).
    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));
    await waitFor(() =>
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        com_compra: true,
        marcar_sem_compra: true,
        projeto_id: 77,
        municipio_id: 6,
      }),
    );
    await waitFor(() => expect(screen.queryByText(aviso)).not.toBeInTheDocument());
  });

  test('trocar só o projeto reconfere o município gravado e avisa se o par novo é sem compra', async () => {
    lookupMunicipiosWithFiltersMock.mockImplementation(async (params: { municipio_id?: number }) =>
      params.municipio_id === 5 ? [{ id: 5, label: 'Sobral-CE', kind: 'municipio', sem_compra: true }] : [],
    );
    renderPage();
    const aviso = 'Sem compra neste município para este projeto. O evento vai para aprovação.';
    fireEvent.click(await screen.findByRole('button', { name: 'Busque ou selecione um projeto' }));
    expect(await screen.findByText(aviso)).toBeInTheDocument();
  });

  // Revisão de 03/11: evento num projeto em espera (sem compra em município nenhum): trocar o município
  // não "vai para aprovação", o servidor recusa. A tela diz isso no lugar do aviso de sem compra.
  test('projeto em espera: a tela avisa que ele não recebe evento, e não que vai para aprovação', async () => {
    escolha.municipio = { id: 6, label: 'Crato-CE', kind: 'municipio', sem_compra: true, projeto_em_espera: true };
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Busque ou selecione um município' }));
    const texto = await screen.findByText('Este projeto não tem compra em município nenhum: fica em espera até a compra entrar.');
    expect(screen.queryByText('Sem compra neste município para este projeto. O evento vai para aprovação.')).not.toBeInTheDocument();
    const municipio = screen.getByRole('button', { name: 'Busque ou selecione um município' });
    expect(document.getElementById(municipio.getAttribute('aria-describedby') ?? '')?.contains(texto)).toBe(true);
  });

  test('o par gravado não avisa: salvar com ele não muda o status', async () => {
    escolha.municipio = { id: 5, label: 'Sobral-CE', kind: 'municipio', sem_compra: true, projeto_em_espera: false };
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Busque ou selecione um município' }));
    await waitFor(() => expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalled());
    expect(screen.queryByText('Sem compra neste município para este projeto. O evento vai para aprovação.')).not.toBeInTheDocument();
  });
});
