import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Link, MemoryRouter } from 'react-router';
import Modal from 'antd/es/modal';

import { ComAcesso } from '../../../test/comAcesso';
import { apagarAvisoDoLogin, avisarSaidaAsOutrasAbas, guardarAvisoDoLogin, storageKeys } from '../../../utils/storage';

const {
  createSolicitacaoMock,
  getMeMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
} = vi.hoisted(() => ({
  createSolicitacaoMock: vi.fn(),
  getMeMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('../../../api/solicitacoes', () => ({
  createSolicitacao: createSolicitacaoMock,
}));

vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
}));

vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
}));

vi.mock('../../../components/DateTimeRange', () => ({
  default: () => <div data-testid="datetime-range">DateTimeRange</div>,
}));

vi.mock('../../../components/FormadoresPicker', () => ({
  default: () => <div data-testid="formadores-picker">FormadoresPicker</div>,
}));


function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  disabled = false,
}: {
  placeholder?: string;
  lookupFunction: (query: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  disabled?: boolean;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);

  return (
    <button
      type="button"
      data-testid={placeholder}
      disabled={disabled}
      onClick={() => {
        if (placeholder.includes('projeto')) {
          onChange?.({ id: 123, label: 'Projeto X', fluxo: 'SUPER' });
          return;
        }
        onChange?.({ id: 456, label: 'Fortaleza - CE' });
      }}
    >
      {placeholder}
    </button>
  );
}

vi.mock('../../../components/ComboBox', () => ({
  default: MockComboBox,
}));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

describe('NewSolicitacaoWizard - filtros dependentes municipio/projeto', () => {
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
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ is_superuser: false });
  });

  test('usuário comum consulta municípios elegíveis por projeto e mostra estado vazio', async () => {
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );

    const municipioDisabledButton = await screen.findByRole('button', {
      name: 'Selecione um projeto para carregar municípios elegíveis',
    });
    expect(municipioDisabledButton).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));

    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        com_compra: true,
        projeto_id: 123,
      });
    });

    expect(await screen.findByText('Sem municípios elegíveis')).toBeInTheDocument();
    expect(
      screen.getByText('Não há municípios com compra que libere o projeto selecionado.')
    ).toBeInTheDocument();
  });

  // PR 7 das permissões: a dispensa da compra vem da policy create_solicitation_without_purchase
  // (hoje só o superusuário a recebe), não do is_superuser do /me.
  test('quem dispensa a compra mantém lookup de municípios sem filtro de compra/projeto', async () => {
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ id: 1, label: 'Fortaleza - CE' }]);

    render(
      <MemoryRouter>
        <ComAcesso policies={['create_solicitation', 'create_solicitation_without_purchase']}>
          <NewSolicitacaoWizard />
        </ComAcesso>
      </MemoryRouter>
    );

    const municipioButton = await screen.findByRole('button', {
      name: 'Busque ou selecione um município',
    });
    expect(municipioButton).not.toBeDisabled();

    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalled();
    });

    const firstCallArg = lookupMunicipiosWithFiltersMock.mock.calls[0][0];
    expect(firstCallArg.q).toBe('');
    expect(firstCallArg.com_compra).toBeUndefined();
    expect(firstCallArg.projeto_id).toBeUndefined();

    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));

    await waitFor(() => {
      const lastCallArg =
        lookupMunicipiosWithFiltersMock.mock.calls[lookupMunicipiosWithFiltersMock.mock.calls.length - 1][0];
      expect(lastCallArg.q).toBe('');
      expect(lastCallArg.com_compra).toBeUndefined();
      expect(lastCallArg.projeto_id).toBeUndefined();
    });

    expect(screen.queryByText('Sem municípios elegíveis')).not.toBeInTheDocument();
  });

  // Regra da compra: o projeto "em espera" (sem compra que o libere) some da lista.
  test('usuário comum busca projetos com com_compra e vê a linha de ajuda', async () => {
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(getMeMock).toHaveBeenCalled();
      expect(lookupProjetosMock).toHaveBeenLastCalledWith('', { com_compra: true });
    });
    expect(screen.getByText('Projetos sem compra não aparecem.')).toBeInTheDocument();
  });

  test('quem dispensa a compra busca projetos sem filtro de compra', async () => {
    render(
      <MemoryRouter>
        <ComAcesso policies={['create_solicitation', 'create_solicitation_without_purchase']}>
          <NewSolicitacaoWizard />
        </ComAcesso>
      </MemoryRouter>
    );

    await screen.findByRole('button', { name: 'Busque ou selecione um município' });
    await waitFor(() => {
      expect(lookupProjetosMock).toHaveBeenLastCalledWith('', {});
    });
    expect(screen.queryByText('Projetos sem compra não aparecem.')).not.toBeInTheDocument();
  });

  test('is_superuser no /me sem a policy: continua filtrando por compra (o payload não decide)', async () => {
    getMeMock.mockResolvedValue({ is_superuser: true });
    render(
      <MemoryRouter>
        <ComAcesso policies={['create_solicitation']}>
          <NewSolicitacaoWizard />
        </ComAcesso>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(getMeMock).toHaveBeenCalled();
      expect(lookupProjetosMock).toHaveBeenLastCalledWith('', { com_compra: true });
    });
  });
});

describe('NewSolicitacaoWizard - sair do assistente (item 36)', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ is_superuser: false });
  });

  const sair = () => screen.getByRole('button', { name: /Voltar para Minhas Solicitações/i });

  test('sem nada preenchido, sai direto para Minhas Solicitações', async () => {
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await screen.findByRole('button', { name: 'Busque ou selecione um projeto' });
    fireEvent.click(sair());
    expect(navigateMock).toHaveBeenCalledWith('/solicitacoes/minhas', { replace: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('com algo preenchido, pergunta antes de descartar, começando no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Busque ou selecione um projeto' }));
    fireEvent.click(sair());

    expect(confirmar).toHaveBeenCalledTimes(1);
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes).toMatchObject({
      title: 'Sair sem criar a solicitação?',
      content: 'O que você preencheu será perdido.',
      okText: 'Sair e descartar',
      cancelText: 'Continuar preenchendo',
      autoFocusButton: 'cancel',
    });
    expect(navigateMock).not.toHaveBeenCalled();
    void opcoes.onOk?.();
    expect(navigateMock).toHaveBeenCalledWith('/solicitacoes/minhas', { replace: true });
    confirmar.mockRestore();
  });

  const preencher = async (): Promise<void> => {
    fireEvent.click(await screen.findByRole('button', { name: 'Busque ou selecione um projeto' }));
  };

  test('recarregar ou fechar a aba com algo preenchido pede o aviso do navegador; vazio, não', async () => {
    // No app, o monitor de sessão grava o horário comum às abas ao montar.
    localStorage.setItem(storageKeys.sessaoUltimaResposta, String(Date.now()));
    const { unmount } = render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await screen.findByRole('button', { name: 'Busque ou selecione um projeto' });
    const vazio = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(vazio);
    expect(vazio.defaultPrevented).toBe(false);

    await preencher();
    const preenchido = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(preenchido);
    expect(preenchido.defaultPrevented).toBe(true);
    unmount();
  });

  test('o reload do próprio app (sessão encerrada ou Sair) não é segurado, mesmo com algo preenchido', async () => {
    localStorage.setItem(storageKeys.sessaoUltimaResposta, String(Date.now()));
    const { unmount } = render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await preencher();
    const descarregar = (): boolean => {
      const evento = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(evento);
      return evento.defaultPrevented;
    };
    expect(descarregar()).toBe(true);

    // Sessão encerrada (expirou ou caiu em outra aba): o App guarda o motivo e recarrega para o login.
    guardarAvisoDoLogin('Sua sessão expirou.');
    expect(descarregar()).toBe(false);
    apagarAvisoDoLogin();

    // "Sair": o App apaga o horário comum às abas e recarrega.
    avisarSaidaAsOutrasAbas();
    expect(descarregar()).toBe(false);
    unmount();
  });

  test('o Voltar do navegador (ou do Android) com algo preenchido pergunta antes de sair', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    const voltar = vi.spyOn(window.history, 'go').mockImplementation(() => {});
    const { unmount } = render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await preencher();
    const entradas = window.history.length;

    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(confirmar).toHaveBeenCalledTimes(1);
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes).toMatchObject({ title: 'Sair sem criar a solicitação?', autoFocusButton: 'cancel' });
    // Com o aviso aberto, o próximo Voltar já está segurado: a entrada repetida volta na hora.
    expect(window.history.length).toBe(entradas + 1);
    // Sair e descartar: segue o Voltar que a pessoa pediu, passando pela entrada repetida.
    void opcoes.onOk?.();
    expect(voltar).toHaveBeenCalledWith(-2);
    unmount();
    voltar.mockRestore();
    confirmar.mockRestore();
  });

  test('o Voltar do Android com o aviso aberto fecha o aviso e continua no assistente', async () => {
    const destruir = vi.fn();
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: destruir, update: vi.fn(), then: vi.fn() }) as never);
    const voltar = vi.spyOn(window.history, 'go').mockImplementation(() => {});
    const { unmount } = render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await preencher();

    window.dispatchEvent(new PopStateEvent('popstate'));
    const entradas = window.history.length;
    window.dispatchEvent(new PopStateEvent('popstate'));

    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(destruir).toHaveBeenCalledTimes(1);
    expect(voltar).not.toHaveBeenCalled();
    // Segue segurando o Voltar seguinte.
    expect(window.history.length).toBe(entradas + 1);
    unmount();
    voltar.mockRestore();
    confirmar.mockRestore();
  });

  test('o aviso de sair não fica aberto sobre outra tela quando o assistente sai', async () => {
    const destruir = vi.fn();
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: destruir, update: vi.fn(), then: vi.fn() }) as never);
    const { unmount } = render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await preencher();
    fireEvent.click(sair());
    expect(confirmar).toHaveBeenCalledTimes(1);

    unmount();
    expect(destruir).toHaveBeenCalledTimes(1);
    confirmar.mockRestore();
  });

  test('um link do menu lateral com algo preenchido pergunta antes de sair', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    const { unmount } = render(
      <MemoryRouter initialEntries={['/solicitacoes/nova']}>
        <nav><Link to="/home?x=1">Página Inicial</Link></nav>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await preencher();

    fireEvent.click(screen.getByRole('link', { name: 'Página Inicial' }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(navigateMock).not.toHaveBeenCalled();
    void confirmar.mock.calls[0]![0].onOk?.();
    expect(navigateMock).toHaveBeenCalledWith('/home?x=1', { replace: true });
    unmount();
    confirmar.mockRestore();
  });
});
