/**
 * Botão "Dar feedback" (11/11/2026) e a caixa "Enviar feedback" no modelo do dono (12/11/2026): abre no
 * clique, exige nota e tipo, envia a rota da tela e avisa o resultado.
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

const PERGUNTA_NOTA = 'Como você avalia o sistema hoje?';
const PERGUNTA_TIPO = 'Qual é o tipo do seu feedback?';
const COMENTARIO = 'Conte mais (opcional)';

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
  return screen.findByRole('dialog', { name: 'Enviar feedback' });
}

/** O input do rádio fica invisível: o clique vai no rótulo (a caixinha da estrela ou o cartão), como na tela. */
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

    expect(within(caixa).getByRole('radiogroup', { name: PERGUNTA_NOTA })).toBeInTheDocument();
    expect(within(caixa).getByRole('radiogroup', { name: PERGUNTA_TIPO })).toBeInTheDocument();
    expect(within(caixa).getByRole('radio', { name: 'Sugestão' })).toBeInTheDocument();
    expect(within(caixa).getByLabelText(COMENTARIO)).toHaveAttribute('maxlength', '2000');
  });

  test('modelo novo: perguntas com dica, notas de 1 a 5, tipos com descrição e o aviso do que vai junto', async () => {
    const user = userEvent.setup();
    renderBotao();
    const caixa = await abrir(user);

    expect(within(caixa).getByText('Ajude a melhorar o sistema! Conte como está sendo a sua experiência.')).toBeInTheDocument();
    // Transparência (LGPD): a frase não está no modelo, mas fica.
    expect(within(caixa).getByText('Seu nome e a tela em que você está vão junto.')).toBeInTheDocument();
    expect(within(caixa).getByRole('button', { name: 'Enviar feedback' })).toBeInTheDocument();

    const nota = within(caixa).getByRole('radiogroup', { name: PERGUNTA_NOTA });
    expect(nota).toHaveAccessibleDescription('Escolha uma nota de 1 a 5.');
    expect(within(nota).getAllByRole('radio')).toHaveLength(5);
    for (const nome of ['1: muito ruim', '2: ruim', '3: regular', '4: bom', '5: muito bom']) {
      expect(within(nota).getByRole('radio', { name: nome })).not.toBeChecked();
    }

    const tipo = within(caixa).getByRole('radiogroup', { name: PERGUNTA_TIPO });
    expect(tipo).toHaveAccessibleDescription('Selecione a opção que melhor descreve o seu comentário.');
    const descricoes: Record<string, string> = {
      Elogio: 'Algo que está funcionando bem.',
      Problema: 'Algo que não está funcionando como deveria.',
      Sugestão: 'Uma ideia de melhoria para o sistema.',
      Dúvida: 'Uma pergunta sobre o uso do sistema.',
    };
    for (const [nome, descricao] of Object.entries(descricoes)) {
      expect(within(tipo).getByRole('radio', { name: nome })).toHaveAccessibleDescription(descricao);
    }

    const comentario = within(caixa).getByLabelText(COMENTARIO);
    expect(comentario).toHaveAccessibleDescription('Descreva sua experiência, o que aconteceu ou a sua sugestão em detalhes.');
    expect(comentario).toHaveAttribute('placeholder', 'Escreva seu comentário aqui...');
    expect(within(caixa).getByText('0 / 2000')).toBeInTheDocument();
  });

  test('escolher uma nota marca só ela: as anteriores não acendem', async () => {
    const user = userEvent.setup();
    renderBotao();
    const caixa = await abrir(user);
    const nota = within(caixa).getByRole('radiogroup', { name: PERGUNTA_NOTA });

    await marcar(user, caixa, '4: bom');
    expect(within(nota).getByRole('radio', { checked: true })).toBe(within(nota).getByRole('radio', { name: '4: bom' }));

    await marcar(user, caixa, '2: ruim');
    expect(within(nota).getByRole('radio', { checked: true })).toBe(within(nota).getByRole('radio', { name: '2: ruim' }));
  });

  test('rádios de verdade: cada grupo tem um name só, que faz as setas do teclado andarem entre as opções', async () => {
    const user = userEvent.setup();
    renderBotao();
    const caixa = await abrir(user);
    const nomes = (pergunta: string): string[] =>
      within(within(caixa).getByRole('radiogroup', { name: pergunta }))
        .getAllByRole('radio')
        .map((radio) => (radio as HTMLInputElement).name);

    const notas = new Set(nomes(PERGUNTA_NOTA));
    const tipos = new Set(nomes(PERGUNTA_TIPO));
    expect(notas.size).toBe(1);
    expect(tipos.size).toBe(1);
    expect([...notas][0]).not.toBe('');
    expect([...tipos][0]).not.toBe([...notas][0]);
  });

  test('no celular o botão é só o ícone, com nome acessível', () => {
    act(() => definirLarguraTela(360));
    renderBotao();
    const botao = screen.getByRole('button', { name: 'Dar feedback' });
    expect(botao).toHaveAttribute('aria-label', 'Dar feedback');
    expect(botao).not.toHaveTextContent('Dar feedback');
  });

  test('nota e tipo são obrigatórios: sem eles nada é enviado, e o erro fica ligado ao campo', async () => {
    const user = userEvent.setup();
    renderBotao();
    const caixa = await abrir(user);

    await user.click(within(caixa).getByRole('button', { name: 'Enviar feedback' }));

    expect(await within(caixa).findByText('Escolha uma nota.')).toBeInTheDocument();
    expect(within(caixa).getByText('Escolha o tipo.')).toBeInTheDocument();
    const nota = within(caixa).getByRole('radiogroup', { name: PERGUNTA_NOTA });
    const tipo = within(caixa).getByRole('radiogroup', { name: PERGUNTA_TIPO });
    expect(nota).toHaveAttribute('aria-invalid', 'true');
    expect(nota).toHaveAccessibleDescription(/Escolha uma nota\.$/);
    expect(tipo).toHaveAttribute('aria-invalid', 'true');
    expect(tipo).toHaveAccessibleDescription(/Escolha o tipo\.$/);
    expect(enviarFeedback).not.toHaveBeenCalled();
  });

  test('envia nota, tipo, comentário e a rota da tela (sem query string), agradece e fecha', async () => {
    const user = userEvent.setup();
    const sucesso = vi.spyOn(message, 'success');
    vi.mocked(enviarFeedback).mockResolvedValue({} as never);
    renderBotao();
    const caixa = await abrir(user);

    await marcar(user, caixa, '4: bom');
    await marcar(user, caixa, 'Sugestão');
    await user.type(within(caixa).getByLabelText(COMENTARIO), '  Filtro por mês  ');
    await user.click(within(caixa).getByRole('button', { name: 'Enviar feedback' }));

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

    await marcar(user, caixa, '2: ruim');
    await marcar(user, caixa, 'Problema');
    await user.click(within(caixa).getByRole('button', { name: 'Enviar feedback' }));

    await waitFor(() =>
      expect(erro).toHaveBeenCalledWith('Não foi possível enviar o feedback. Sem conexão com o servidor.'),
    );
    expect(screen.getByRole('dialog', { name: 'Enviar feedback' })).toBeInTheDocument();
    expect(within(caixa).getByRole('radio', { name: 'Problema' })).toBeChecked();
    expect(within(caixa).getByRole('radio', { name: '2: ruim' })).toBeChecked();
  });

  test('limite de envios (429): pede para tentar mais tarde', async () => {
    const user = userEvent.setup();
    const erro = vi.spyOn(message, 'error');
    vi.mocked(enviarFeedback).mockRejectedValue(Object.assign(new Error('throttled'), { status: 429 }));
    renderBotao();
    const caixa = await abrir(user);

    await marcar(user, caixa, '5: muito bom');
    await marcar(user, caixa, 'Elogio');
    await user.click(within(caixa).getByRole('button', { name: 'Enviar feedback' }));

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
