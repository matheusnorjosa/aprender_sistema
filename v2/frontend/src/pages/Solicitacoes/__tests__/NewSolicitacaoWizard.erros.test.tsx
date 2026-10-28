/**
 * Nova Solicitação — erros que a pessoa consegue corrigir (item 36, 19/10/2026; página única, 28/10/2026).
 *
 * - Fim antes (ou igual) do início não envia: a mensagem fica junto do horário.
 * - "Criar solicitação" com campo faltando não envia, mostra um resumo no topo e leva o foco ao
 *   primeiro campo com erro (não é clique mudo); se o erro está em "Mais detalhes", abre a seção.
 * - Recusa do backend por campo mostra o motivo de `errors`, não o genérico "Erro de validação.".
 * - Sem conexão, a mensagem diz isso, e não "Verifique os dados".
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderNoRoteador } from '../../../test/comRoteador';
import message from 'antd/es/message';

const {
  createSolicitacaoMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
  horario,
} = vi.hoisted(() => ({
  createSolicitacaoMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
  horario: { atual: { date: '2026-08-01', start: '09:00', end: '11:00' } },
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useNavigate: () => navigateMock };
});
vi.mock('../../../api/solicitacoes', () => ({ createSolicitacao: createSolicitacaoMock }));
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
  default: ({ onChange, erro }: { onChange?: (v: unknown) => void; erro?: string | null }) => (
    <div>
      <button type="button" data-testid="set-date" onClick={() => onChange?.(horario.atual)}>
        set-date
      </button>
      {/* Como o real: o campo marcado com erro leva `data-campo-horario` e `aria-invalid`. */}
      <input data-testid="campo-horario" data-campo-horario aria-invalid={erro ? 'true' : undefined} readOnly />
      {erro ? <p data-testid="erro-horario">{erro}</p> : null}
    </div>
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

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  id,
}: {
  placeholder?: string;
  lookupFunction: (q: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  id?: string;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  const testid = placeholder.includes('respons')
    ? 'cb-responsavel'
    : placeholder.includes('munic')
      ? 'cb-municipio'
      : placeholder.includes('projeto')
        ? 'cb-projeto'
        : 'cb-tipo';
  return (
    <button
      type="button"
      id={id}
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') onChange?.({ id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER', responsavel_padrao: true });
        else if (testid === 'cb-tipo') onChange?.({ id: 789, label: 'Formação' });
        else if (testid === 'cb-responsavel') onChange?.({ id: 7, label: 'Carla Coordenadora' });
        else onChange?.({ id: 456, label: 'Fortaleza - CE' });
      }}
    >
      {testid}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

function renderWizard(): void {
  renderNoRoteador(
    <NewSolicitacaoWizard />
  );
}

const criar = (): HTMLElement => screen.getByRole('button', { name: 'Criar solicitação' });
// A validação do Form do AntD é assíncrona; com a suíte inteira e a cobertura na CI ela passa de 1 s.
const ESPERA_VALIDACAO = { timeout: 5000 };

async function preencherLinha1EHorario(): Promise<void> {
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
}

async function preencherTudo(): Promise<void> {
  await preencherLinha1EHorario();
  fireEvent.click(screen.getByTestId('pick-formador'));
  fireEvent.click(within(screen.getByRole('radiogroup', { name: /vai acompanhar o evento/ })).getByLabelText('Não'));
  // A prévia de agenda termina antes do clique (o aviso de verificando sai da tela).
  await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled(), ESPERA_VALIDACAO);
  await waitFor(() => expect(screen.queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(), ESPERA_VALIDACAO);
  expect(criar()).not.toBeDisabled();
}

// A página com antd leva ~3 s por teste isolado; na suíte inteira passa dos 5 s padrão.
describe('NewSolicitacaoWizard — erros que a pessoa consegue corrigir (item 36)', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
    horario.atual = { date: '2026-08-01', start: '09:00', end: '11:00' };
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacaoMock.mockResolvedValue({ id: 1 });
  });

  test('fim antes do início não envia e a mensagem fica junto do horário', async () => {
    horario.atual = { date: '2026-08-01', start: '14:00', end: '10:00' };
    renderWizard();
    await preencherTudo();
    fireEvent.click(criar());
    expect(await screen.findByTestId('erro-horario')).toHaveTextContent('O horário de fim precisa ser depois do início.');
    // O resumo do topo diz o mesmo e o foco vai ao horário (único problema).
    expect(await screen.findByRole('alert')).toHaveTextContent('O horário de fim precisa ser depois do início.');
    await waitFor(() => expect(screen.getByTestId('campo-horario')).toHaveFocus(), ESPERA_VALIDACAO);
    expect(createSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('fim igual ao início também não envia', async () => {
    horario.atual = { date: '2026-08-01', start: '10:00', end: '10:00' };
    renderWizard();
    await preencherTudo();
    fireEvent.click(criar());
    expect(await screen.findByTestId('erro-horario')).toHaveTextContent('O horário de fim precisa ser depois do início.');
    expect(createSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('sem data, o erro aparece junto do horário e também nos outros campos que faltam', async () => {
    renderWizard();
    await screen.findByTestId('cb-projeto');
    fireEvent.click(criar());
    expect(await screen.findByTestId('erro-horario')).toHaveTextContent('Escolha a data e os horários de início e de fim do evento.');
    expect(await screen.findByText('Por favor selecione um projeto', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    expect(createSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('"Criar" com campo faltando mostra um resumo no topo e leva o foco ao primeiro campo com erro', async () => {
    renderWizard();
    await screen.findByTestId('cb-projeto');
    fireEvent.click(screen.getByTestId('set-date'));
    fireEvent.click(criar());

    await waitFor(() => expect(screen.getByTestId('cb-projeto')).toHaveFocus(), ESPERA_VALIDACAO);
    // Uma só região viva: o resumo. Ele diz o evento e o que falta, na ordem dos campos.
    const alertas = screen.getAllByRole('alert');
    expect(alertas).toHaveLength(1);
    const resumo = alertas[0]!;
    expect(resumo).toHaveTextContent('Corrija antes de criar a solicitação');
    expect(resumo).toHaveTextContent('Evento 1: Por favor selecione um projeto');
    expect(resumo).toHaveTextContent('Responda se o coordenador responsável vai acompanhar o evento.');
    expect(resumo.textContent.indexOf('projeto')).toBeLessThan(resumo.textContent.indexOf('formador'));
    expect(createSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('o resumo sai quando a pessoa volta a mexer no evento', async () => {
    renderWizard();
    await screen.findByTestId('cb-projeto');
    fireEvent.click(criar());
    expect(await screen.findByText(/Corrija antes de criar a solicitação/, undefined, ESPERA_VALIDACAO)).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('cb-projeto'));
    await waitFor(() => expect(screen.queryByText(/Corrija antes de criar a solicitação/)).not.toBeInTheDocument());
  });

  test('erro em "Mais detalhes" (recolhido): o limite vale, a seção abre e o foco vai ao campo', async () => {
    renderWizard();
    await preencherTudo();
    const detalhes = screen.getByRole('button', { name: /Mais detalhes/ });
    expect(detalhes).toHaveAttribute('aria-expanded', 'false');
    const encontro = screen.getByLabelText('Encontro');
    fireEvent.change(encontro, { target: { value: 'x'.repeat(101) } });

    fireEvent.click(criar());
    expect(await screen.findByText('Máximo 100 caracteres', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    await waitFor(() => expect(detalhes).toHaveAttribute('aria-expanded', 'true'));
    await waitFor(() => expect(encontro).toHaveFocus(), ESPERA_VALIDACAO);
    expect(createSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('recusa do backend por campo mostra o motivo, não "Erro de validação."', async () => {
    createSolicitacaoMock.mockRejectedValueOnce({
      response: {
        status: 400,
        data: {
          detail: 'Erro de validação.',
          errors: { municipio: ['Não há compra que libere este projeto neste município.'] },
        },
      },
    });
    renderWizard();
    await preencherTudo();
    fireEvent.click(criar());
    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith('Não há compra que libere este projeto neste município.')
    );
    expect(message.error).not.toHaveBeenCalledWith('Erro de validação.');
  });

  test('sem conexão, a mensagem diz isso', async () => {
    createSolicitacaoMock.mockRejectedValueOnce(new TypeError('Sem conexão com o servidor.'));
    renderWizard();
    await preencherTudo();
    fireEvent.click(criar());
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('Sem conexão com o servidor.'));
  });
});
