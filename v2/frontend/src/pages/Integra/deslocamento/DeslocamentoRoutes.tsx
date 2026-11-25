/**
 * Deslocamento: sub-rotas e a moldura das telas (caminho, aviso de quem vê na versão real, de onde vêm
 * os dados e o menu local).
 *
 * Os tempos NÃO são simulados: são as estimativas do relatório da Coordenação Pedagógica (nov/2026, em
 * `dados/deslocamento.ts`; o próprio relatório diz que não são horários reais); os
 * coordenadores e as carteiras são os FICTÍCIOS do gerador. Montado em `/integra/deslocamento/*` por
 * `IntegraRoutes`. O menu é uma lista de links que quebra linha (sem
 * rolagem horizontal); a tela atual leva `aria-current="page"`.
 */
import type { JSX } from 'react';
import { Link, Navigate, NavLink, Outlet, Route, Routes } from 'react-router';

import { QUEM_VE } from '../quemVe';
import RegrasDoCalculo from './RegrasDoCalculo';
import SomaPorCoordenador from './SomaPorCoordenador';
import TemposPorMunicipio from './TemposPorMunicipio';

const TELAS_DO_DESLOCAMENTO: readonly { para: string; rotulo: string; fim?: boolean }[] = [
  { para: '/integra/deslocamento', rotulo: 'Tempos por município', fim: true },
  { para: '/integra/deslocamento/regras', rotulo: 'Como o tempo é calculado' },
  { para: '/integra/deslocamento/coordenadores', rotulo: 'Soma por coordenador' },
];

function MolduraDeslocamento(): JSX.Element {
  return (
    <div>
      <p className="mb-2 text-sm">
        <Link to="/integra">Integra</Link>
        <span aria-hidden="true"> › </span>
        <span>Deslocamento</span>
      </p>
      <div role="note" className="mb-3 rounded border-l-4 border-primary-dark bg-[#EEF5F3] p-3 text-sm">
        <p className="m-0">{QUEM_VE.deslocamento.aviso}</p>
      </div>
      <p className="mb-3 text-sm">
        Os tempos não são simulados: são as estimativas do relatório da Coordenação Pedagógica (novembro de 2026),
        saindo de Fortaleza. Os coordenadores e as carteiras são fictícios.
      </p>
      <nav aria-label="Telas do Deslocamento" className="mb-6 print:hidden">
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {TELAS_DO_DESLOCAMENTO.map(({ para, rotulo, fim }) => (
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

export default function DeslocamentoRoutes(): JSX.Element {
  return (
    <Routes>
      <Route element={<MolduraDeslocamento />}>
        <Route index element={<TemposPorMunicipio />} />
        <Route path="regras" element={<RegrasDoCalculo />} />
        <Route path="coordenadores" element={<SomaPorCoordenador />} />
        <Route path="*" element={<Navigate to="/integra/deslocamento" replace />} />
      </Route>
    </Routes>
  );
}
