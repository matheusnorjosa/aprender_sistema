/**
 * Botão "Dar feedback" (11/11/2026): abre no clique, exige nota e tipo, envia a rota da tela e
 * avisa o resultado.
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('../../api/feedback', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api/feedback')>()),
  enviarFeedback: vi.fn(),
}));

import { enviarFeedback } from '../../api/feedback';
import { definirLarguraTela } from '../../test/larguraTela';
import { FeedbackButton } from '../FeedbackButton';

function renderBotao(rota = '/solicitacoes/minhas?aba=2') {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter initialEntries={[rota]}>
        <FeedbackButton />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

type Usuario = ReturnType<typeof userEvent.setup>;

async function abrir(user: Usuario): Promise<HTMLElement> {
  await user.click(screen.getByRole('button', { name: 'Dar feedback' }));
  return screen.findByRole('dialog', { name: 'Dar feedback' });
}

/** O input do rádio do AntD fica invisível (pointer-events: none): o clique vai no rótulo, como na tela. */
async function marcar(user: Usuario, caixa: HTMLElement, nome: string): Promise<void> {
  await user.click(within(caixa).getByRole('radio', { name: nome }).closest('label')!);
}

describe('FeedbackButton', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('a caixa só abre no clique', async () => {
    const user = userEvent.setup();
    renderBotao();

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    const caixa = await abrir(user);

    expect(within(caixa).getByRole('radiogroup', { name: /Nota/ })).toBeInTheDocument();
    expect(within(caixa).getByRole('radiogroup', { name: 'Tipo' })).toBeInTheDocument();
    expect(within(caixa).getByRole('radio', { name: 'Sugestão' })).toBeInTheDocument();
    expect(within(caixa).getByLabelText('Comentário (opcional)')).toHaveAttribute('maxlength', '2000');
  });

  test('no celular o botão é só o ícone, com nome acessível', () => {
    act(() => definirLarguraTela(360));
    renderBotao();
    const botao = screen.getByRole('button', { name: 'Dar feedback' });
    expect(botao).toHaveAttribute('aria-label', 'Dar feedback');
    expect(botao).not.toHaveTextContent('Dar feedback');
  });

  test('nota e tipo são obrigatórios: sem eles nada é enviado', async () => {
    const user = userEvent.setup();
    renderBotao();
    const caixa = await abrir(user);

    await user.click(within(caixa).getByRole('button', { name: 'Enviar' }));

    expect(await within(caixa).findByText('Escolha uma nota de 1 a 5.')).toBeInTheDocument();
    expect(within(caixa).getByText('Escolha o tipo.')).toBeInTheDocument();
    expect(enviarFeedback).not.toHaveBeenCalled();
  });

  test('envia nota, tipo, comentário e a rota da tela (sem query string), agradece e fecha', async () => {
    const user = userEvent.setup();
    const sucesso = vi.spyOn(message, 'success');
    vi.mocked(enviarFeedback).mockResolvedValue({} as never);
    renderBotao();
    const caixa = await abrir(user);

    await marcar(user, caixa, '4');
    await marcar(user, caixa, 'Sugestão');
    await user.type(within(caixa).getByLabelText('Comentário (opcional)'), '  Filtro por mês  ');
    await user.click(within(caixa).getByRole('button', { name: 'Enviar' }));

    await waitFor(() =>
      expect(enviarFeedback).toHaveBeenCalledWith({
        nota: 4,
        tipo: 'SUGESTAO',
        comentario: 'Filtro por mês',
        pagina: '/solicitacoes/minhas',
      }),
    );
    expect(sucesso).toHaveBeenCalledWith('Obrigado! Seu feedback foi enviado.');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  test('erro do servidor: mensagem clara e a caixa continua aberta com o que foi preenchido', async () => {
    const user = userEvent.setup();
    const erro = vi.spyOn(message, 'error');
    vi.mocked(enviarFeedback).mockRejectedValue(new Error('Sem conexão com o servidor.'));
    renderBotao();
    const caixa = await abrir(user);

    await marcar(user, caixa, '2');
    await marcar(user, caixa, 'Problema');
    await user.click(within(caixa).getByRole('button', { name: 'Enviar' }));

    await waitFor(() =>
      expect(erro).toHaveBeenCalledWith('Não foi possível enviar o feedback. Sem conexão com o servidor.'),
    );
    expect(screen.getByRole('dialog', { name: 'Dar feedback' })).toBeInTheDocument();
    expect(within(caixa).getByRole('radio', { name: 'Problema' })).toBeChecked();
  });

  test('limite de envios (429): pede para tentar mais tarde', async () => {
    const user = userEvent.setup();
    const erro = vi.spyOn(message, 'error');
    vi.mocked(enviarFeedback).mockRejectedValue(Object.assign(new Error('throttled'), { status: 429 }));
    renderBotao();
    const caixa = await abrir(user);

    await marcar(user, caixa, '5');
    await marcar(user, caixa, 'Elogio');
    await user.click(within(caixa).getByRole('button', { name: 'Enviar' }));

    await waitFor(() =>
      expect(erro).toHaveBeenCalledWith('Você enviou muitos feedbacks em pouco tempo. Tente de novo mais tarde.'),
    );
  });

  test('Cancelar e Esc fecham sem enviar', async () => {
    const user = userEvent.setup();
    renderBotao();

    let caixa = await abrir(user);
    await user.click(within(caixa).getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    caixa = await abrir(user);
    await waitFor(() => expect(caixa.contains(document.activeElement)).toBe(true));
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: 'Escape', code: 'Escape', keyCode: 27, which: 27 });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(enviarFeedback).not.toHaveBeenCalled();
  });
});
