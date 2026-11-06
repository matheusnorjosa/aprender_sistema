/**
 * G30 (Programa C) — Mapa de Eventos sem rolagem horizontal.
 *
 * As três tabelas (Detalhes por Estado, Eventos por Coordenador e Detalhes por Município) tinham
 * `scroll.x: max-content`. Agora são o ResponsiveTable, com colunas por prioridade de largura. Os
 * cartões "Eventos por Estado" e "Detalhes por Estado" só dividem a largura a partir de 1600 px (na
 * metade da área principal, de 992 px em diante, a tabela e as etiquetas não cabiam), e as
 * etiquetas da lista, do resumo por estado e da legenda quebram linha.
 *
 * O react-leaflet é trocado por um mapa de botões (como em MapaBrasilPage.erros.test.tsx).
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { ReactNode } from 'react';

import { definirLarguraTela } from '../../../test/larguraTela';

const { fetchAPIMock } = vi.hoisted(() => ({ fetchAPIMock: vi.fn() }));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/config')>();
  return { ...actual, fetchAPI: fetchAPIMock };
});

vi.mock('../../../data/brazil-states.json', () => ({
  default: {
    type: 'FeatureCollection',
    features: [{ type: 'Feature', properties: { name: 'Ceará', sigla: 'CE' }, geometry: null }],
  },
}));

interface FakeFeature {
  properties: { name: string; sigla: string };
}

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useMap: () => ({ flyTo: vi.fn(), flyToBounds: vi.fn() }),
  GeoJSON: ({
    data,
    onEachFeature,
  }: {
    data: { features: FakeFeature[] };
    onEachFeature: (feature: FakeFeature, layer: unknown) => void;
  }) => (
    <div>
      {data.features.map((feature) => {
        const handlers: Record<string, () => void> = {};
        onEachFeature(feature, {
          bindTooltip: () => undefined,
          on: (h: Record<string, () => void>) => Object.assign(handlers, h),
          getBounds: () => ({ isValid: () => false }),
          setStyle: () => undefined,
          bringToFront: () => undefined,
        });
        return (
          <button key={feature.properties.sigla} type="button" onClick={() => handlers['click']?.()}>
            {`estado ${feature.properties.sigla}`}
          </button>
        );
      })}
    </div>
  ),
}));

import MapaBrasilPage from '../MapaBrasilPage';

const MAPA_OK = {
  totals: { all: 1, by_status: { aprovado: 1 }, compras: 0 },
  by_uf: [{ uf: 'CE', eventos: 1, projetos: 1, municipios: 1, coordenadores: 1, compras: 0 }],
  by_municipio: [
    {
      municipio: 'Fortaleza',
      uf: 'CE',
      latitude: -3.7,
      longitude: -38.5,
      projetos: 1,
      eventos: 1,
      coordenadores: 1,
      compras: 0,
    },
  ],
  top_projetos: [],
};

type Rota = (url: string) => Promise<unknown>;

function rotear(rotas: Record<string, Rota>): void {
  fetchAPIMock.mockImplementation((url: string) => {
    const chave = Object.keys(rotas).find((prefixo) => url.includes(prefixo));
    if (!chave) return Promise.reject(new Error(`rota não mockada: ${url}`));
    return rotas[chave]!(url);
  });
}


const COORDENADORES = {
  coordenadores: [
    {
      id: 7,
      nome: 'Pessoa Ficticia',
      eventos: 1,
      projetos: [{ nome: 'Projeto Longo de Alfabetização', eventos: 1 }],
      municipios: [{ nome: 'Fortaleza', eventos: 1 }],
    },
  ],
};

function cabecalhosDe(celula: HTMLElement): string[] {
  const tabela = celula.closest('table');
  if (!tabela) throw new Error('o texto não está numa tabela');
  return within(tabela)
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

/**
 * A tabela que monta depois da carga lê a largura no efeito de montagem (Grid.useBreakpoint do
 * AntD) e só então põe as colunas por prioridade: espera os cabeçalhos assentarem.
 */
async function esperarCabecalhos(achar: () => HTMLElement, esperado: string[]): Promise<void> {
  await waitFor(() => expect(cabecalhosDe(achar())).toEqual(esperado));
}

function semLarguraForcada(container: HTMLElement): void {
  expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
  for (const conteudo of Array.from(container.querySelectorAll('.ant-table-content'))) {
    expect(conteudo.getAttribute('style') ?? '').not.toMatch(/overflow/);
  }
  for (const tabela of Array.from(container.querySelectorAll('table'))) expect(tabela.style.width).toBe('');
}

/** A célula da UF na tabela "Detalhes por Estado". */
async function celulaDoEstado(): Promise<HTMLElement> {
  const card = (await screen.findByText('Detalhes por Estado', {}, { timeout: 15000 })).closest<HTMLElement>('.ant-card')!;
  return within(card).findByText('CE', { selector: 'td, td *' });
}

describe('Mapa de Eventos sem rolagem horizontal (G30)', { timeout: 30000 }, () => {
  beforeEach(() => {
    fetchAPIMock.mockReset();
    rotear({
      '/options/projetos/': () => Promise.resolve([]),
      '/metrics/map/coordinators/': () => Promise.resolve(COORDENADORES),
      '/metrics/map/': () => Promise.resolve(MAPA_OK),
    });
  });

  test('a 1280 px: Detalhes por Estado com todas as colunas, sem largura forçada', async () => {
    const { container } = render(<MapaBrasilPage />);

    const uf = await celulaDoEstado();
    await esperarCabecalhos(() => uf, ['Estado', 'Municípios', 'Eventos', 'Coordenadores', 'Compras']);
    semLarguraForcada(container);
  });

  test('a 360 px: estado e eventos na linha; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    render(<MapaBrasilPage />);

    const uf = await celulaDoEstado();
    await esperarCabecalhos(() => uf, ['Estado', 'Eventos']);
  });

  test('os cartões por estado só dividem a largura a partir de xxl; as etiquetas quebram linha', async () => {
    render(<MapaBrasilPage />);
    await celulaDoEstado();

    for (const titulo of ['Eventos por Estado', 'Detalhes por Estado']) {
      const coluna = screen.getByText(titulo).closest('.ant-col');
      expect(coluna).toHaveClass('ant-col-xs-24', 'ant-col-xxl-12');
      expect(coluna).not.toHaveClass('ant-col-lg-12');
    }
    expect(screen.getByText('1 Eventos').closest('.ant-space')).toHaveStyle({ flexWrap: 'wrap' });
    expect((await screen.findByText('Com eventos', {}, { timeout: 15000 })).closest('.ant-space')).toHaveStyle({ flexWrap: 'wrap' });
  });

  test('vista Lista: as etiquetas do município quebram linha', async () => {
    render(<MapaBrasilPage />);
    await celulaDoEstado();

    fireEvent.click(screen.getByText('Lista'));
    const item = (await screen.findByText('Fortaleza-CE')).closest<HTMLElement>('.ant-list-item')!;
    expect(within(item).getByText('1 eventos').closest('.ant-space')).toHaveStyle({ flexWrap: 'wrap' });
  });

  test('estado clicado: coordenadores e municípios no ResponsiveTable, com projetos que quebram linha', async () => {
    const { container } = render(<MapaBrasilPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'estado CE' }, { timeout: 15000 }));

    const coordenador = await screen.findByText('Pessoa Ficticia');
    await esperarCabecalhos(() => coordenador, ['Coordenador', 'Eventos', 'Projetos (eventos)', 'Municípios (eventos)']);
    expect(screen.getByText('Projeto Longo de Alfabetização', { exact: false }).closest('.ant-tag')).toHaveStyle({
      whiteSpace: 'normal',
    });
    const card = screen.getByText('Detalhes por Município').closest<HTMLElement>('.ant-card')!;
    await esperarCabecalhos(() => within(card).getByText('Fortaleza', { selector: 'td, td *' }), [
      'Município',
      'Eventos',
      'Coordenadores',
      'Projetos',
      'Compras',
    ]);
    semLarguraForcada(container);
  });
});
