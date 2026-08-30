/**
 * H.2 (robustez): um crash de página deve ficar ISOLADO no conteúdo e a navegação deve
 * recuperar sem full reload. O ErrorBoundary ganhou `resetKeys`: ao mudar (ex.: a rota),
 * limpa o estado de erro. Este teste reproduz o padrão do AppRoutes (ErrorBoundary keyed
 * por location.pathname envolvendo as Routes): uma rota estoura → mostra o fallback →
 * navegar para uma rota sã recupera.
 *
 * RED no código antigo (sem resetKeys, o boundary fica preso no erro após navegar).
 */
import { describe, expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation, useNavigate } from 'react-router';
import { ErrorBoundary } from '../ErrorBoundary';

function Boom(): never {
  throw new Error('boom');
}

function Harness() {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <button onClick={() => navigate('/ok')}>ir para ok</button>
      <ErrorBoundary resetKeys={[location.pathname]}>
        <Routes>
          <Route path="/ok" element={<div>PAGINA OK</div>} />
          <Route path="/boom" element={<Boom />} />
        </Routes>
      </ErrorBoundary>
    </>
  );
}

describe('ErrorBoundary com resetKeys (recuperação por navegação — H.2)', () => {
  test('rota que estoura mostra o fallback; navegar para rota sã recupera', async () => {
    // Silencia o console.error do React ao capturar o throw (ruído esperado).
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/boom']}>
        <Harness />
      </MemoryRouter>,
    );

    // fallback do ErrorBoundary
    expect(await screen.findByText('Algo deu errado')).toBeInTheDocument();
    expect(screen.queryByText('PAGINA OK')).toBeNull();

    // navega para a rota sã → resetKeys muda → boundary reseta
    await user.click(screen.getByRole('button', { name: /ir para ok/i }));

    expect(await screen.findByText('PAGINA OK')).toBeInTheDocument();
    expect(screen.queryByText('Algo deu errado')).toBeNull();

    spy.mockRestore();
  });
});
