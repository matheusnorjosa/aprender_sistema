/**
 * B#36 (alinhamento das telas): o item de menu das Ações Internas se chama "Linha do tempo",
 * não "Timeline".
 */
import { MemoryRouter } from 'react-router';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { AppSidebar } from '../AppSidebar';
import { ComAcesso } from '../../test/comAcesso';

describe('AppSidebar — Ações Internas em português', () => {
  test('o filho que leva a /acoes-notificacao/timeline se chama "Linha do tempo"', () => {
    render(
      <MemoryRouter>
        <ComAcesso policies={['manage_internal_actions']}>
          <AppSidebar
            gcalErrorCount={0}
            unreadNotifications={0}
            modo="aberta"
            sidebarCollapsed={false}
            toggleSidebar={() => {}}
            colors={{ sidebarBackground: '#001529', borderLight: '#303030' }}
          />
        </ComAcesso>
      </MemoryRouter>,
    );
    const titulo = Array.from(document.querySelectorAll<HTMLElement>('.ant-menu-submenu-title')).find(
      (el) => (el.textContent || '').trim() === 'Ações Internas',
    );
    fireEvent.click(titulo!);
    expect(screen.getByRole('link', { name: 'Linha do tempo' })).toHaveAttribute('href', '/acoes-notificacao/timeline');
    expect(screen.queryByRole('link', { name: 'Timeline' })).not.toBeInTheDocument();
  });
});
