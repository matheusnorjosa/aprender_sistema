import { useEffect } from 'react';
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Link } from 'react-router';
import Modal from 'antd/es/modal';

import { ComAcesso } from '../../../test/comAcesso';
import { enderecoAtual, renderNoRoteador } from '../../../test/comRoteador';
import { apagarAvisoDoLogin, avisarSaidaAsOutrasAbas, guardarAvisoDoLogin, storageKeys } from '../../../utils/storage';
import { botaoDoTexto } from './localizadores';

const {
  createSolicitacoesEmLoteMock,
  getMeMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
} = vi.hoisted(() => ({
  createSolicitacoesEmLoteMock: vi.fn(),
  getMeMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  createSolicitacoesEmLote: createSolicitacoesEmLoteMock,
}));

vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
}));

vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
  lookupUsuarios: vi.fn().mockResolvedValue([]),
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
    <>
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
      {placeholder === 'Busque ou selecione um projeto' && (
        <button type="button" onClick={() => onChange?.(null)}>Limpar projeto</button>
      )}
    </>
  );
}

vi.mock('../../../components/ComboBox', () => ({
  default: MockComboBox,
}));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

describe('NewSolicitacaoWizard - filtros dependentes municipio/projeto', { timeout: 20000 }, () => {
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
    renderNoRoteador(
      <NewSolicitacaoWizard />
    );

    const municipioDisabledButton = await waitFor(() => botaoDoTexto('Selecione um projeto para carregar municípios elegíveis'));
    expect(municipioDisabledButton).toBeDisabled();

    fireEvent.click(botaoDoTexto('Busque ou selecione um projeto'));

    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        com_compra: true,
        projeto_id: 123,
      });
    });

    // A situação do cartão diz o motivo da lista vazia (texto estático, sem região viva por cartão).
    expect(await screen.findByText('Sem municípios com compra para este projeto')).toBeInTheDocument();
    expect(screen.queryByText('Compra dispensada')).not.toBeInTheDocument();
  });

  // PR 7 das permissões: a dispensa da compra vem da policy create_solicitation_without_purchase
  // (hoje só o superusuário a recebe), não do is_superuser do /me.
  test('quem dispensa a compra mantém lookup de municípios sem filtro de compra/projeto', async () => {
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ id: 1, label: 'Fortaleza - CE' }]);

    renderNoRoteador(
      <ComAcesso policies={['create_solicitation', 'create_solicitation_without_purchase']}>
        <NewSolicitacaoWizard />
      </ComAcesso>
    );

    const municipioButton = await waitFor(() => botaoDoTexto('Busque ou selecione um município'));
    expect(municipioButton).not.toBeDisabled();

    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalled();
    });

    const firstCallArg = lookupMunicipiosWithFiltersMock.mock.calls[0][0];
    expect(firstCallArg.q).toBe('');
    expect(firstCallArg.com_compra).toBeUndefined();
    expect(firstCallArg.projeto_id).toBeUndefined();

    fireEvent.click(botaoDoTexto('Busque ou selecione um projeto'));

    await waitFor(() => {
      const lastCallArg =
        lookupMunicipiosWithFiltersMock.mock.calls[lookupMunicipiosWithFiltersMock.mock.calls.length - 1][0];
      expect(lastCallArg.q).toBe('');
      expect(lastCallArg.com_compra).toBeUndefined();
      expect(lastCallArg.projeto_id).toBeUndefined();
    });

    expect(screen.queryByText('Sem municípios com compra para este projeto')).not.toBeInTheDocument();
    expect(screen.getByText('Compra dispensada')).toBeInTheDocument();
  });

  // Regra da compra: o projeto "em espera" (sem compra que o libere) some da lista.
  test('usuário comum busca projetos com com_compra e vê a linha de ajuda', async () => {
    renderNoRoteador(
      <NewSolicitacaoWizard />
    );

    await waitFor(() => {
      expect(getMeMock).toHaveBeenCalled();
      expect(lookupProjetosMock).toHaveBeenLastCalledWith('', { com_compra: true });
    });
    expect(screen.getByText('Projetos sem compra não aparecem.')).toBeInTheDocument();
  });

  test('quem dispensa a compra busca projetos sem filtro de compra', async () => {
    renderNoRoteador(
      <ComAcesso policies={['create_solicitation', 'create_solicitation_without_purchase']}>
        <NewSolicitacaoWizard />
      </ComAcesso>
    );

    await waitFor(() => botaoDoTexto('Busque ou selecione um município'));
    await waitFor(() => {
      expect(lookupProjetosMock).toHaveBeenLastCalledWith('', {});
    });
    expect(screen.queryByText('Projetos sem compra não aparecem.')).not.toBeInTheDocument();
  });

  test('is_superuser no /me sem a policy: continua filtrando por compra (o payload não decide)', async () => {
    getMeMock.mockResolvedValue({ is_superuser: true });
    renderNoRoteador(
      <ComAcesso policies={['create_solicitation']}>
        <NewSolicitacaoWizard />
      </ComAcesso>
    );

    await waitFor(() => {
      expect(getMeMock).toHaveBeenCalled();
      expect(lookupProjetosMock).toHaveBeenLastCalledWith('', { com_compra: true });
    });
  });
});

// Decisão do dono (28/10/2026): a Nova Solicitação deixa de ser um assistente de 4 passos e vira uma
// página só, com o evento num cartão em linhas (Projeto | Tipo | Município; Data | Início | Fim;
// Formadores | Coordenador responsável).
describe('NewSolicitacaoWizard - página única com um cartão de evento (28/10/2026)', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ is_superuser: false });
  });

  test('um cartão "Evento 1" com todos os campos à vista e nenhum passo', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);

    expect(await screen.findByRole('heading', { level: 2, name: 'Nova Solicitação' })).toBeInTheDocument();
    const cartao = screen.getByRole('region', { name: 'Evento 1' });
    expect(screen.getByRole('heading', { level: 3, name: 'Evento 1' })).toBeInTheDocument();

    for (const campo of [
      'Busque ou selecione um projeto',
      'Busque ou selecione um tipo de evento',
      'Selecione um projeto para carregar municípios elegíveis',
      'Busque o coordenador responsável',
    ]) {
      expect(within(cartao).getByRole('button', { name: campo })).toBeInTheDocument();
    }
    expect(within(cartao).getByTestId('datetime-range')).toBeInTheDocument();
    expect(within(cartao).getByTestId('formadores-picker')).toBeInTheDocument();
    expect(within(cartao).getByRole('radiogroup', { name: /vai acompanhar o evento/ })).toBeInTheDocument();
    // Os detalhes opcionais ficam recolhidos, mas montados (os limites de tamanho valem recolhidos).
    expect(within(cartao).getByRole('button', { name: /Mais detalhes/ })).toHaveAttribute('aria-expanded', 'false');
    expect(within(cartao).getByLabelText('Observações')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Criar solicitação' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Próximo|proximo passo|Anterior|passo anterior/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /Passos/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Passo \d de \d/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Revise sua solicitação|Confirmar Solicitação/)).not.toBeInTheDocument();
  });

  test('as linhas do cartão são grades que empilham no celular e não passam da largura da tela', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    const projeto = await waitFor(() => botaoDoTexto('Busque ou selecione um projeto'));

    const linha1 = projeto.closest('.md\\:grid-cols-3');
    expect(linha1).toHaveClass('grid', 'grid-cols-1');
    expect(linha1).toHaveTextContent('Projeto');
    expect(linha1).toHaveTextContent('Tipo de Evento');
    expect(linha1).toHaveTextContent('Município');
    expect(Array.from(linha1!.children).every((c) => c.classList.contains('min-w-0'))).toBe(true);

    const linha3 = screen.getByTestId('formadores-picker').closest('.md\\:grid-cols-2');
    expect(linha3).toHaveClass('grid', 'grid-cols-1');
    expect(linha3).toHaveTextContent('Coordenador responsável');
    // A pergunta obrigatória fica junto do coordenador, não escondida em "Mais detalhes".
    expect(linha3).toHaveTextContent('O coordenador responsável vai acompanhar o evento?');
    expect(Array.from(linha3!.children).every((c) => c.classList.contains('min-w-0'))).toBe(true);
  });

  test('a situação do cartão diz, sem região viva, que o evento SUPER vai para aprovação', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    fireEvent.click(await waitFor(() => botaoDoTexto('Busque ou selecione um projeto')));

    const situacao = await screen.findByText('Vai para aprovação');
    expect(situacao.closest('[role="alert"], [role="status"], [aria-live]')).toBeNull();
    expect(screen.queryByText('Aprovado na hora')).not.toBeInTheDocument();
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

  const NOVA = '/solicitacoes/nova';
  // O assistente aberto a partir da Página Inicial, com o menu lateral ao lado.
  const abrir = (antes: string[] = ['/home']) => renderNoRoteador(
    <>
      <nav><Link to="/home?x=1">Página Inicial</Link></nav>
      <NewSolicitacaoWizard />
    </>,
    { em: NOVA, antes },
  );
  const sair = () => botaoDoTexto(/Voltar para Minhas Solicitações/i);
  const preencher = async (): Promise<void> => {
    fireEvent.click(await waitFor(() => botaoDoTexto('Busque ou selecione um projeto')));
  };
  const voltarDoNavegador = async (router: ReturnType<typeof abrir>['router'], passos = 1): Promise<void> => {
    await act(async () => {
      await router.navigate(-passos);
    });
  };
  // O aviso de sair, sem abrir o modal do antd: guarda as opções para o teste responder.
  const espiarAviso = (destruir = vi.fn()) => vi.spyOn(Modal, 'confirm')
    .mockImplementation(() => ({ destroy: destruir, update: vi.fn(), then: vi.fn() }) as never);
  const responder = (confirmar: ReturnType<typeof espiarAviso>, resposta: 'onOk' | 'onCancel'): void => {
    act(() => {
      void confirmar.mock.calls.at(-1)![0][resposta]?.();
    });
  };

  test('sem nada preenchido, o botão do topo sai direto para Minhas Solicitações', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await waitFor(() => botaoDoTexto('Busque ou selecione um projeto'));
    fireEvent.click(sair());
    await waitFor(() => expect(enderecoAtual(router)).toBe('/solicitacoes/minhas'));
    expect(confirmar).not.toHaveBeenCalled();
    confirmar.mockRestore();
  });

  test('com algo preenchido, o botão do topo pergunta uma vez antes de descartar, começando no Cancelar', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await preencher();
    fireEvent.click(sair());

    await waitFor(() => expect(confirmar).toHaveBeenCalledTimes(1));
    expect(confirmar.mock.calls[0]![0]).toMatchObject({
      title: 'Sair sem criar a solicitação?',
      content: 'O que você preencheu será perdido.',
      okText: 'Sair e descartar',
      okType: 'danger',
      cancelText: 'Continuar preenchendo',
      autoFocusButton: 'cancel',
    });
    expect(enderecoAtual(router)).toBe(NOVA);

    responder(confirmar, 'onOk');
    await waitFor(() => expect(enderecoAtual(router)).toBe('/solicitacoes/minhas'));
    expect(confirmar).toHaveBeenCalledTimes(1);
    confirmar.mockRestore();
  });

  test('Continuar preenchendo fica no assistente com o que foi preenchido, e a próxima saída pergunta de novo', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await preencher();
    fireEvent.click(sair());
    await waitFor(() => expect(confirmar).toHaveBeenCalledTimes(1));

    responder(confirmar, 'onCancel');
    expect(enderecoAtual(router)).toBe(NOVA);
    expect(botaoDoTexto('Busque ou selecione um município')).toBeInTheDocument();

    fireEvent.click(sair());
    await waitFor(() => expect(confirmar).toHaveBeenCalledTimes(2));
    expect(enderecoAtual(router)).toBe(NOVA);
    confirmar.mockRestore();
  });

  test('o Voltar do navegador (ou do Android) com algo preenchido pergunta antes de sair', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await preencher();

    await voltarDoNavegador(router);
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ title: 'Sair sem criar a solicitação?', autoFocusButton: 'cancel' });
    expect(enderecoAtual(router)).toBe(NOVA);

    responder(confirmar, 'onOk');
    await waitFor(() => expect(enderecoAtual(router)).toBe('/home'));
    confirmar.mockRestore();
  });

  test('o Voltar com o aviso aberto não abre um segundo aviso nem sai do assistente', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await preencher();

    await voltarDoNavegador(router);
    await voltarDoNavegador(router);
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(enderecoAtual(router)).toBe(NOVA);

    responder(confirmar, 'onOk');
    await waitFor(() => expect(enderecoAtual(router)).toBe('/home'));
    confirmar.mockRestore();
  });

  test('segurar o Voltar e escolher uma página mais antiga pergunta e, ao sair, vai para ela', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir(['/notificacoes', '/home']);
    await preencher();

    await voltarDoNavegador(router, 2);
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(enderecoAtual(router)).toBe(NOVA);

    responder(confirmar, 'onOk');
    await waitFor(() => expect(enderecoAtual(router)).toBe('/notificacoes'));
    confirmar.mockRestore();
  });

  test('esvaziado de novo, o Voltar sai sem perguntar', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await preencher();
    fireEvent.click(botaoDoTexto('Limpar projeto'));

    await voltarDoNavegador(router);
    await waitFor(() => expect(enderecoAtual(router)).toBe('/home'));
    expect(confirmar).not.toHaveBeenCalled();
    confirmar.mockRestore();
  });

  test('um link do menu lateral com algo preenchido pergunta antes de sair', async () => {
    const confirmar = espiarAviso();
    const { router } = abrir();
    await preencher();

    fireEvent.click(screen.getByRole('link', { name: 'Página Inicial' }));
    await waitFor(() => expect(confirmar).toHaveBeenCalledTimes(1));
    expect(enderecoAtual(router)).toBe(NOVA);

    responder(confirmar, 'onOk');
    await waitFor(() => expect(enderecoAtual(router)).toBe('/home?x=1'));
    confirmar.mockRestore();
  });

  test('o aviso de sair não fica aberto sobre outra tela quando o assistente sai', async () => {
    const destruir = vi.fn();
    const confirmar = espiarAviso(destruir);
    const { router, unmount } = abrir();
    await preencher();
    await voltarDoNavegador(router);
    expect(confirmar).toHaveBeenCalledTimes(1);

    unmount();
    expect(destruir).toHaveBeenCalledTimes(1);
    confirmar.mockRestore();
  });

  test('recarregar ou fechar a aba com algo preenchido pede o aviso do navegador; vazio, não', async () => {
    // No app, o monitor de sessão grava o horário comum às abas ao montar.
    localStorage.setItem(storageKeys.sessaoUltimaResposta, String(Date.now()));
    const { unmount } = abrir();
    await waitFor(() => botaoDoTexto('Busque ou selecione um projeto'));
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
    const { unmount } = abrir();
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
});
