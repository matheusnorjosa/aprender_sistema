/**
 * EditSolicitacaoPage — o que a tela trava antes do Salvar.
 *
 * - Evento no Google pela planilha (`publicado_fora_do_sistema`) e sincronização em andamento
 *   (`gcal_status` PENDING) não abrem o formulário (o servidor recusa salvar; D27).
 * - Publicado: o texto diz o caminho que existe (D25: o Apoio ou o Controle tira só do Google), não
 *   "Cancele o evento", que quem pediu não consegue fazer.
 * - Observações têm o limite de 5000 da Nova Solicitação (D76).
 * - SUPER aprovada: mudar o que a aprovação aprovou avisa antes do Salvar que volta para aprovação.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import message from 'antd/es/message';

const { getSolicitacaoMock, updateSolicitacaoMock } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  updateSolicitacaoMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: updateSolicitacaoMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/ComboBox', () => ({
  default: ({ placeholder = '', onChange }: { placeholder?: string; onChange?: (item: unknown) => void }) =>
    placeholder.includes('município') ? (
      <button type="button" onClick={() => onChange?.({ id: 6, label: 'Crato-CE' })}>
        Trocar município
      </button>
    ) : null,
}));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));
vi.mock('../../../components/CoordenadoresPicker', () => ({ default: () => null }));

import EditSolicitacaoPage from '../EditSolicitacaoPage';

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
  inicio: '2099-10-10T12:00:00Z',
  fim: '2099-10-10T15:00:00Z',
  status: 'aprovado',
  fluxo: 'SUPER',
  gcal_status: 'NONE',
  external_event_id: null,
  publicado_fora_do_sistema: false,
  participations: [
    {
      role: 'FORMADOR',
      usuario: { id: 99, first_name: 'Bruno', last_name: 'Formador', email: null },
    },
  ],
};

const FORMULARIO = 'Salvar Alterações';
const VOLTA = 'Esta mudança volta o evento para aprovação.';

function renderPage(): void {
  render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('EditSolicitacaoPage — travas antes do Salvar', { timeout: 20000 }, () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset();
    updateSolicitacaoMock.mockReset();
    vi.spyOn(message, 'success').mockImplementation(vi.fn()).mockClear();
    vi.spyOn(message, 'warning').mockImplementation(vi.fn()).mockClear();
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
  });

  test('evento no Google pela planilha: o formulário não abre e o texto diz a quem pedir', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, publicado_fora_do_sistema: true });
    renderPage();
    expect(
      await screen.findByText(
        'Este evento já está no Google Agenda pela planilha; mudar aqui não muda a agenda. Para mudar, peça ao Apoio de Coordenação da sua gerência ou ao Controle.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(FORMULARIO)).not.toBeInTheDocument();
  });

  test('sincronização com o Google em andamento: o formulário não abre e manda aguardar', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, gcal_status: 'PENDING' });
    renderPage();
    expect(
      await screen.findByText(
        'A sincronização com o Google Agenda está em andamento. Aguarde e recarregue a página para editar.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(FORMULARIO)).not.toBeInTheDocument();
  });

  test('publicado que o Apoio ou o Controle tira do Google: diz o caminho, sem "Cancele o evento"', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, gcal_status: 'PUBLISHED', external_event_id: 'g-1' });
    renderPage();
    expect(
      await screen.findByText(
        'Este evento já está no Google Agenda. Para editar, peça ao Apoio de Coordenação da sua gerência, na tela Publicar na agenda, ou ao Controle, na Pré-agenda, que tire o evento só do Google; depois disso, você consegue editar aqui.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Cancele o evento/)).not.toBeInTheDocument();
    expect(screen.queryByText(FORMULARIO)).not.toBeInTheDocument();
  });

  test('publicado que ninguém tira do Google (já passou): manda falar com a administração', async () => {
    getSolicitacaoMock.mockResolvedValue({
      ...SOLICITACAO,
      gcal_status: 'PUBLISHED',
      external_event_id: 'g-1',
      fim: '2020-01-01T15:00:00Z',
    });
    renderPage();
    expect(
      await screen.findByText(
        'Este evento já está no Google Agenda e não dá para editá-lo aqui. Para mudar, fale com a administração do sistema.',
      ),
    ).toBeInTheDocument();
  });

  test('Observações acima de 5000 caracteres: a tela avisa e não salva', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, status: 'pendente' });
    renderPage();
    fireEvent.change(await screen.findByLabelText('Observações'), { target: { value: 'x'.repeat(5001) } });
    expect(await screen.findByText('Máximo 5000 caracteres')).toBeInTheDocument();
  });

  test('SUPER aprovada: mudar o município avisa antes do Salvar que volta para aprovação', async () => {
    getSolicitacaoMock.mockResolvedValue(SOLICITACAO);
    renderPage();
    await screen.findByText(FORMULARIO);
    expect(screen.queryByText(VOLTA)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Trocar município'));
    await waitFor(() => expect(screen.getByText(VOLTA)).toBeInTheDocument());
  });

  test('SUPER aprovada: mudar só o que a aprovação não olha (Local) não avisa', async () => {
    getSolicitacaoMock.mockResolvedValue(SOLICITACAO);
    renderPage();
    fireEvent.change(await screen.findByLabelText('Local do Evento'), { target: { value: 'Escola X' } });
    expect(screen.queryByText(VOLTA)).not.toBeInTheDocument();
  });

  test('SUPER pendente: mudar o município não avisa', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, status: 'pendente' });
    renderPage();
    await screen.findByText(FORMULARIO);
    fireEvent.click(screen.getByText('Trocar município'));
    expect(screen.queryByText(VOLTA)).not.toBeInTheDocument();
  });

  test('NAO_SUPER aprovada: mudar o município não avisa', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, fluxo: 'NAO_SUPER' });
    renderPage();
    await screen.findByText(FORMULARIO);
    fireEvent.click(screen.getByText('Trocar município'));
    expect(screen.queryByText(VOLTA)).not.toBeInTheDocument();
  });
});
