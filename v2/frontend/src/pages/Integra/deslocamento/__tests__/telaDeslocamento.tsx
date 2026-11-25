/**
 * Monta as telas do Deslocamento nos testes: o estado da demonstração (carteiras simuladas) e as rotas
 * do Deslocamento, para que o menu local e os links entre as telas funcionem.
 */
import { MemoryRouter, Route, Routes } from 'react-router';
import { render, type RenderResult } from '@testing-library/react';

import { IntegraDemoProvider } from '../../dados/IntegraDemoContext';
import DeslocamentoRoutes from '../DeslocamentoRoutes';

export function renderTelaDeslocamento(rota: string): RenderResult {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <IntegraDemoProvider>
        <Routes>
          <Route path="/integra/deslocamento/*" element={<DeslocamentoRoutes />} />
          <Route path="/integra/ica/*" element={<p>Tela do ICA</p>} />
        </Routes>
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}
