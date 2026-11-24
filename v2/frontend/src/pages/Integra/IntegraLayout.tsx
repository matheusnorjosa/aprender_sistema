/**
 * Moldura da Integra (protótipo para a validação de 07/12/2026): a faixa fixa "DADOS SIMULADOS", o
 * estado da demonstração (`IntegraDemoProvider`) e as rotas da Integra.
 *
 * Contas de verdade, dados simulados gerados na tela, nada gravado no banco (decisões do dono Q2 e Q3,
 * 24/11/2026). A faixa fica presa no topo ao rolar e sai também na impressão, no começo do documento;
 * o `integra.css` repete o aviso na margem de cima de toda folha impressa e dá foco visível aos links.
 *
 * As rotas filhas ficam em `IntegraRoutes` (um `<Routes>` descendente) e não em `<Route>` aninhado no
 * AppRoutes: o teste de cobertura sem rolagem horizontal lê o AppRoutes e não aceita rota aninhada.
 */
import { useEffect, useRef, type JSX } from 'react';
import { useLocation, useNavigationType } from 'react-router';
import { ExperimentOutlined } from '@ant-design/icons';

import { IntegraDemoProvider } from './dados/IntegraDemoContext';
import IntegraRoutes from './IntegraRoutes';

import './integra.css';

/** Âmbar escuro sobre âmbar claro: contraste 9:1 (WCAG AA pede 4,5:1). */
const FAIXA = { fundo: '#FFF4CE', texto: '#5C3B00', borda: '#8A5A00' } as const;

/**
 * Troca de tela dentro da Integra (link, não "voltar" do navegador): a tela nova abre no topo e o foco
 * vai para o título dela. Sem isso, o nome clicado no fim do Painel abria a Ficha no meio, e o foco
 * caía no body (o link clicado sai da tela). O app não tem `<ScrollRestoration/>`; no "voltar"
 * (`POP`) fica o comportamento do navegador. Na primeira abertura, o foco não é tirado do lugar.
 */
function useTopoAoTrocarDeTela(): void {
  const { pathname } = useLocation();
  const tipo = useNavigationType();
  // O endereço já tratado, e não um "primeira vez": o StrictMode roda o efeito duas vezes ao montar.
  const tratado = useRef(pathname);

  useEffect(() => {
    if (tratado.current === pathname) return;
    tratado.current = pathname;
    if (tipo === 'POP') return;
    window.scrollTo(0, 0);
    const titulo = document.querySelector<HTMLElement>('.integra h1');
    if (!titulo) return;
    // Focável só por programa (fora do Tab), como o alvo do "Tentar de novo" do ResponsiveTable.
    titulo.setAttribute('tabindex', '-1');
    titulo.focus({ preventScroll: true });
  }, [pathname, tipo]);
}

export default function IntegraLayout(): JSX.Element {
  useTopoAoTrocarDeTela();
  return (
    <IntegraDemoProvider>
      <div className="integra">
        <p
          role="note"
          className="sticky top-0 z-10 m-0 flex flex-wrap items-center gap-x-2 px-6 py-2 text-sm print:static"
          style={{ background: FAIXA.fundo, color: FAIXA.texto, borderBottom: `2px solid ${FAIXA.borda}` }}
        >
          <ExperimentOutlined aria-hidden="true" />
          <strong>DADOS SIMULADOS</strong>
          <span>Pessoas fictícias e números gerados na tela para a demonstração; nada é gravado.</span>
        </p>
        <div className="p-6">
          <IntegraRoutes />
        </div>
      </div>
    </IntegraDemoProvider>
  );
}
