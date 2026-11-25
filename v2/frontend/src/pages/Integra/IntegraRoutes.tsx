/**
 * Rotas da Integra, montadas em `/integra/*` (AppRoutes carrega a moldura sob demanda, com a policy
 * `access_integra`). Endereço desconhecido dentro da Integra volta para a página dela.
 */
import type { JSX } from 'react';
import { Navigate, Route, Routes } from 'react-router';

import DeslocamentoRoutes from './deslocamento/DeslocamentoRoutes';
import IcaRoutes from './ica/IcaRoutes';
import IntegraPage from './IntegraPage';
import ParaValidarPage from './ParaValidarPage';
import SemaforoRoutes from './semaforo/SemaforoRoutes';

export default function IntegraRoutes(): JSX.Element {
  return (
    <Routes>
      <Route index element={<IntegraPage />} />
      <Route path="ica/*" element={<IcaRoutes />} />
      <Route path="semaforo/*" element={<SemaforoRoutes />} />
      <Route path="deslocamento/*" element={<DeslocamentoRoutes />} />
      <Route path="para-validar" element={<ParaValidarPage />} />
      <Route path="*" element={<Navigate to="/integra" replace />} />
    </Routes>
  );
}
