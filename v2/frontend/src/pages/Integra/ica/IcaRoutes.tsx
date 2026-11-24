/**
 * ICA (Índice de Carga de Acompanhamento): sub-rotas e o menu local das telas.
 *
 * Montado em `/integra/ica/*` por `IntegraRoutes`. O menu é uma lista de links que quebra linha
 * (sem rolagem horizontal em nenhuma largura); a tela atual leva `aria-current="page"`.
 * A ficha do coordenador abre pelo painel (`coordenador/:id`), sem item no menu.
 */
import type { JSX } from 'react';
import { Link, Navigate, NavLink, Outlet, Route, Routes } from 'react-router';

import AlertasIca from './AlertasIca';
import Comparativo from './Comparativo';
import FichaCoordenador from './FichaCoordenador';
import Historico from './Historico';
import PainelIca from './PainelIca';
import PesosFaixas from './PesosFaixas';
import Simulador from './Simulador';
import VisaoGerencia from './VisaoGerencia';

/** Itens do menu local, na ordem de uso. `fim`: só marca quando o endereço é exatamente esse. */
const TELAS_DO_ICA: readonly { para: string; rotulo: string; fim?: boolean }[] = [
  { para: '/integra/ica', rotulo: 'Painel', fim: true },
  { para: '/integra/ica/simulador', rotulo: 'Simulador' },
  { para: '/integra/ica/pesos', rotulo: 'Pesos e faixas' },
  { para: '/integra/ica/gerencias', rotulo: 'Por gerência' },
  { para: '/integra/ica/comparativo', rotulo: 'Comparativo' },
  { para: '/integra/ica/historico', rotulo: 'Histórico' },
  { para: '/integra/ica/alertas', rotulo: 'Alertas' },
];

function MolduraIca(): JSX.Element {
  return (
    <div>
      <p className="mb-2 text-sm">
        <Link to="/integra">Integra</Link>
        <span aria-hidden="true"> › </span>
        <span>ICA</span>
      </p>
      <nav aria-label="Telas do ICA" className="mb-6 print:hidden">
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {TELAS_DO_ICA.map(({ para, rotulo, fim }) => (
            <li key={para}>
              <NavLink
                to={para}
                end={fim === true}
                className={({ isActive }) =>
                  [
                    'inline-block rounded border px-3 py-1 text-sm no-underline',
                    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark',
                    isActive
                      ? 'border-primary-dark bg-primary-dark font-semibold text-white'
                      : 'border-[#8c8c8c] bg-white text-[#1f1f1f] hover:border-primary-dark',
                  ].join(' ')
                }
              >
                {rotulo}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </div>
  );
}

export default function IcaRoutes(): JSX.Element {
  return (
    <Routes>
      <Route element={<MolduraIca />}>
        <Route index element={<PainelIca />} />
        <Route path="coordenador/:id" element={<FichaCoordenador />} />
        <Route path="simulador" element={<Simulador />} />
        <Route path="pesos" element={<PesosFaixas />} />
        <Route path="gerencias" element={<VisaoGerencia />} />
        <Route path="comparativo" element={<Comparativo />} />
        <Route path="historico" element={<Historico />} />
        <Route path="alertas" element={<AlertasIca />} />
        <Route path="*" element={<Navigate to="/integra/ica" replace />} />
      </Route>
    </Routes>
  );
}
