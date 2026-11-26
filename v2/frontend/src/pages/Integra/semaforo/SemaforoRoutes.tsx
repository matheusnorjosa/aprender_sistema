/**
 * Semáforo de Risco Municipal (DADOS SIMULADOS): o estado da demonstração, as sub-rotas, o menu local
 * e o índice das 6 telas.
 *
 * Montado em `/integra/semaforo/*` por `IntegraRoutes`. O estado (`SemaforoDemoProvider`) fica aqui:
 * o que for registrado vale enquanto a pessoa anda pelas telas do Semáforo e volta ao original ao sair
 * dele ou recarregar a página. O menu é uma lista de links que quebra linha (sem rolagem horizontal); a
 * tela atual leva `aria-current="page"`. A ficha do município abre pelo nome (`municipio/:id`), sem item
 * no menu.
 */
import type { JSX } from 'react';
import { Link, Navigate, NavLink, Outlet, Route, Routes } from 'react-router';
import { Typography } from 'antd';

import { formatarDia } from '../ica/componentes/estilos';
import Comite from './Comite';
import { HISTORIAS_SEMAFORO, type DadosSemaforo } from './dados';
import FichaMunicipio from './FichaMunicipio';
import IndicadoresLider from './IndicadoresLider';
import PainelGestora from './PainelGestora';
import PesquisaArticulador from './PesquisaArticulador';
import RelatorioMensal from './RelatorioMensal';
import { SemaforoDemoProvider, useSemaforoDemo } from './SemaforoDemoContext';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const RAIZ = '/integra/semaforo';

/** Itens do menu local, na ordem de uso. `fim`: só marca quando o endereço é exatamente esse. */
const MENU: readonly { para: string; rotulo: string; fim?: boolean }[] = [
  { para: RAIZ, rotulo: 'Início', fim: true },
  { para: `${RAIZ}/comite`, rotulo: 'Comitê' },
  { para: `${RAIZ}/gestora`, rotulo: 'Painel da gestora' },
  { para: `${RAIZ}/pesquisa`, rotulo: 'Pesquisa do articulador' },
  { para: `${RAIZ}/lider`, rotulo: 'Indicadores da Líder' },
  { para: `${RAIZ}/relatorio-mensal`, rotulo: 'Relatório mensal' },
];

const CLASSE_FOCO = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark';

function MolduraSemaforo(): JSX.Element {
  return (
    <div>
      <p className="mb-2 text-sm">
        <Link to="/integra">Integra</Link>
        <span aria-hidden="true"> › </span>
        <span>Semáforo</span>
      </p>
      <p className="mb-2 text-sm">
        O que você registrar ou publicar no Semáforo vale só enquanto estiver nele: ir para outra parte da Integra ou
        recarregar a página volta tudo ao original.
      </p>
      <nav aria-label="Telas do Semáforo" className="mb-6 print:hidden">
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {MENU.map(({ para, rotulo, fim }) => (
            <li key={para}>
              <NavLink
                to={para}
                end={fim === true}
                className={({ isActive }) =>
                  [
                    'inline-block rounded border px-3 py-1 text-sm no-underline',
                    CLASSE_FOCO,
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

/** O índice: as 6 telas, com o que cada uma faz. A ficha abre no município da história (vermelho com prazo hoje). */
function IndiceSemaforo(): JSX.Element {
  const { dados } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const { nome, uf } = HISTORIAS_SEMAFORO.vermelho_prazo_hoje;
  const exemplo = dados.municipios.find((m) => m.nome === nome && m.uf === uf) ?? dados.municipios[0];
  const telas: readonly { para: string; titulo: string; texto: string }[] = [
    {
      para: `${RAIZ}/comite`,
      titulo: 'Comitê de Satisfação',
      texto:
        'A cor que a regra sugere para cada município; o Comitê confirma ou altera, com justificativa. Um indicador em vermelho ou três amarelos: o vermelho muda a cor em vigor na hora, e o Comitê confirma ou desfaz depois.',
    },
    {
      para: `${RAIZ}/municipio/${exemplo?.id ?? ''}`,
      titulo: 'Ficha do município',
      texto: `Os projetos, os 5 indicadores, o histórico, as tarefas, as ocorrências e as reuniões. Exemplo: ${exemplo ? `${exemplo.nome}-${exemplo.uf}` : ''}.`,
    },
    {
      para: `${RAIZ}/gestora`,
      titulo: 'Painel da gestora de referência',
      texto: 'Os municípios da gestora e as tarefas por prazo, com o que vence hoje primeiro.',
    },
    {
      para: `${RAIZ}/pesquisa`,
      titulo: 'Pesquisa do articulador',
      texto: 'A pesquisa de satisfação do ciclo, respondida na tela: uma resposta por projeto.',
    },
    {
      para: `${RAIZ}/lider`,
      titulo: 'Indicadores da Líder',
      texto: 'O retrato do Semáforo para a Líder do NFP.',
    },
    {
      para: `${RAIZ}/relatorio-mensal`,
      titulo: 'Relatório mensal e formulários',
      texto:
        'O relatório mensal do coordenador e os registros de ocorrência, de reunião de escuta e de observação de formação.',
    },
  ];
  return (
    <section aria-labelledby="semaforo-indice-titulo">
      <Title level={1} id="semaforo-indice-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Semáforo de Risco Municipal
      </Title>
      <p>
        Cada município ganha uma cor a cada dois meses: verde, amarelo ou vermelho. Um indicador em vermelho, ou três
        amarelos, muda a cor para vermelho na hora, e o Comitê confirma ou desfaz depois. A cor sai de 5 indicadores e
        diz quem age e em quanto tempo. Nesta demonstração, hoje é {formatarDia(dados.data_referencia)}.
      </p>
      <ul aria-label="As 6 telas do Semáforo" className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
        {telas.map((t) => (
          <li key={t.titulo} className="rounded border border-[#d9d9d9] bg-white p-3">
            <Link to={t.para} state={estadoDaFicha} className={`font-semibold ${CLASSE_FOCO}`}>
              {t.titulo}
            </Link>
            <p className="m-0 mt-1 text-sm">{t.texto}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface SemaforoRoutesProps {
  /** Para testes; por padrão, os dados do gerador. */
  dados?: DadosSemaforo | undefined;
}

export default function SemaforoRoutes({ dados }: SemaforoRoutesProps): JSX.Element {
  return (
    <SemaforoDemoProvider {...(dados && { dados })}>
      <Routes>
        <Route element={<MolduraSemaforo />}>
          <Route index element={<IndiceSemaforo />} />
          <Route path="comite" element={<Comite />} />
          <Route path="municipio/:id" element={<FichaMunicipio />} />
          <Route path="gestora" element={<PainelGestora />} />
          <Route path="pesquisa" element={<PesquisaArticulador />} />
          <Route path="lider" element={<IndicadoresLider />} />
          <Route path="relatorio-mensal" element={<RelatorioMensal />} />
          <Route path="*" element={<Navigate to={RAIZ} replace />} />
        </Route>
      </Routes>
    </SemaforoDemoProvider>
  );
}
