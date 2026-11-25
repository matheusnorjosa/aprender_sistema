/**
 * Monta as telas do Semáforo nos testes com as rotas do Semáforo (que trazem o estado da demonstração),
 * para que os links entre as telas (ex.: o nome no Comitê abre a ficha) funcionem. Com `dados`, as telas
 * leem esses dados em vez dos do gerador (ex.: mudar o "hoje" para ver uma tarefa vencida).
 */
import { MemoryRouter, Route, Routes } from 'react-router';
import { render, type RenderResult } from '@testing-library/react';

import type { DadosSemaforo } from '../dados';
import SemaforoRoutes from '../SemaforoRoutes';

export function renderTelaSemaforo(rota: string, dados?: DadosSemaforo): RenderResult {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route path="/integra/semaforo/*" element={<SemaforoRoutes dados={dados} />} />
      </Routes>
    </MemoryRouter>,
  );
}
