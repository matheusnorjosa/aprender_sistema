import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const { getMyEventsMock } = vi.hoisted(() => ({
  getMyEventsMock: vi.fn(),
}));

vi.mock('../../../api/me', () => ({
  getMyEvents: getMyEventsMock,
}));

vi.mock('../../../components/MeetLink', () => ({
  MeetLink: ({ href }: { href: string | null }) =>
    href ? <a href={href}>Entrar na reunião</a> : null,
}));

import MeusEventosPage from '../MeusEventosPage';
import type { MeEvent } from '../../../api/me';
import type { PaginatedResponse } from '../../../types/common';

function renderPage() {
  return render(
    <MemoryRouter>
      <MeusEventosPage />
    </MemoryRouter>
  );
}

function makeEvent(overrides: Partial<MeEvent> = {}): MeEvent {
  return {
    id: 1,
    inicio: '2026-05-10T13:00:00Z',
    fim: '2026-05-10T17:00:00Z',
    municipio_nome: 'Salvador',
    projeto_nome: 'Vidas',
    tipo_evento_nome: 'Formação',
    local: 'Escola Municipal X',
    formadores: ['Ana Vidas', 'Bruno Fluir'],
    is_online: false,
    meet_link: null,
    status: 'aprovado',
    ...overrides,
  };
}

function makePage(items: MeEvent[]): PaginatedResponse<MeEvent> {
  return { count: items.length, next: null, previous: null, results: items };
}

describe('MeusEventosPage', () => {
  beforeEach(() => {
    getMyEventsMock.mockReset();
  });

  test('renderiza título da página', async () => {
    getMyEventsMock.mockResolvedValueOnce(makePage([]));
    renderPage();
    expect(await screen.findByRole('heading', { name: /meus eventos/i })).toBeInTheDocument();
  });

  test('exibe eventos retornados pela API com municipio, projeto e formadores', async () => {
    getMyEventsMock.mockResolvedValueOnce(
      makePage([
        makeEvent({ id: 10, municipio_nome: 'Salvador', projeto_nome: 'Vidas' }),
        makeEvent({ id: 11, municipio_nome: 'Fortaleza', projeto_nome: 'Fluir' }),
      ])
    );
    renderPage();

    expect(await screen.findByText('Salvador')).toBeInTheDocument();
    expect(await screen.findByText('Fortaleza')).toBeInTheDocument();
    expect(await screen.findByText('Vidas')).toBeInTheDocument();
    expect(await screen.findByText('Fluir')).toBeInTheDocument();
    // formadores juntados por vírgula
    expect(await screen.findAllByText('Ana Vidas, Bruno Fluir')).toHaveLength(2);
  });

  test('mostra empty state quando não há eventos', async () => {
    getMyEventsMock.mockResolvedValueOnce(makePage([]));
    renderPage();
    expect(await screen.findByText(/você não tem eventos agendados/i)).toBeInTheDocument();
  });

  test('exibe tag "Online" para eventos com is_online=true', async () => {
    getMyEventsMock.mockResolvedValueOnce(
      makePage([makeEvent({ id: 20, is_online: true, local: '' })])
    );
    renderPage();
    expect(await screen.findByText('Online')).toBeInTheDocument();
  });

  test('renderiza link Meet quando meet_link existe', async () => {
    getMyEventsMock.mockResolvedValueOnce(
      makePage([
        makeEvent({
          id: 30,
          is_online: true,
          meet_link: 'https://meet.google.com/abc-defg-hij',
        }),
      ])
    );
    renderPage();
    expect(await screen.findByRole('link', { name: /entrar na reunião/i })).toHaveAttribute(
      'href',
      'https://meet.google.com/abc-defg-hij'
    );
  });

  test('chama getMyEvents com page=1 e page_size=20 no carregamento inicial', async () => {
    getMyEventsMock.mockResolvedValueOnce(makePage([]));
    renderPage();
    await waitFor(() => {
      expect(getMyEventsMock).toHaveBeenCalledWith({ page: 1, page_size: 20 });
    });
  });
});
