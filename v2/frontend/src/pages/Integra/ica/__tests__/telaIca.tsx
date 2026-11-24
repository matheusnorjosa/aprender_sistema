/**
 * Monta as telas do ICA nos testes: o estado da demonstração (dados simulados) e as rotas do ICA,
 * para que os links entre as telas (ex.: o nome no painel abre a ficha) funcionem.
 */
import { MemoryRouter, Route, Routes } from 'react-router';
import { render, type RenderResult } from '@testing-library/react';

import { IntegraDemoProvider } from '../../dados/IntegraDemoContext';
import IcaRoutes from '../IcaRoutes';

export function renderTelaIca(rota: string): RenderResult {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <IntegraDemoProvider>
        <Routes>
          <Route path="/integra/ica/*" element={<IcaRoutes />} />
        </Routes>
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}
