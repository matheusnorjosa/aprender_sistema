/**
 * Rotas da Integra, montadas em `/integra/*` (AppRoutes carrega a moldura sob demanda, com a policy
 * `access_integra`). Endereço desconhecido dentro da Integra volta para a página dela.
 *
 * Desenho do DFF (decisão do dono, 26/11/2026): as telas das ferramentas ficam num cartão branco sobre o fundo
 * verde-claro (`integra.css`), e o texto delas continua no branco; a página da Integra põe os cartões direto no fundo.
 */
import type { JSX } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router';

import DeslocamentoRoutes from './deslocamento/DeslocamentoRoutes';
import IcaRoutes from './ica/IcaRoutes';
import IntegraPage from './IntegraPage';
import ParaValidarPage from './ParaValidarPage';
import SemaforoRoutes from './semaforo/SemaforoRoutes';

export default function IntegraRoutes(): JSX.Element {
  return (
    <Routes>
      <Route index element={<IntegraPage />} />
      <Route
        element={
          <div className="integra-cartao">
            <Outlet />
          </div>
        }
      >
        <Route path="ica/*" element={<IcaRoutes />} />
        <Route path="semaforo/*" element={<SemaforoRoutes />} />
        <Route path="deslocamento/*" element={<DeslocamentoRoutes />} />
        <Route path="para-validar" element={<ParaValidarPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/integra" replace />} />
    </Routes>
  );
}
