/**
 * MapaBrasilPage — filtro de projetos e estados de erro (G19, P#20 e B#24).
 *
 * - O filtro de projetos lê /options/projetos/ (aberto a quem está logado, sem paginação), não
 *   /projetos/ (só o DAT lê, e com page_size=100 cortava a lista).
 * - Se a lista de projetos falha, o filtro fica em "Todos os Projetos" com um aviso.
 * - O erro do mapa e o dos coordenadores mostram a mensagem do servidor e "Tentar novamente".
 *
 * O react-leaflet é trocado por um mapa de botões (um por estado): o clique chama o mesmo handler
 * que a página liga em cada camada do GeoJSON.
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { ReactNode } from 'react';

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

function erroHttp(status: number, mensagem: string): Error & { status: number } {
  return Object.assign(new Error(mensagem), { status });
}

type Rota = (url: string) => Promise<unknown>;

function rotear(rotas: Record<string, Rota>): void {
  fetchAPIMock.mockImplementation((url: string) => {
    const chave = Object.keys(rotas).find((prefixo) => url.includes(prefixo));
    if (!chave) return Promise.reject(new Error(`rota não mockada: ${url}`));
    return rotas[chave]!(url);
  });
}

const projetos = Array.from({ length: 120 }, (_, i) => ({ id: i + 1, nome: `Projeto ${String(i + 1).padStart(3, '0')}` }));

describe('MapaBrasilPage — filtro de projetos e erros', { timeout: 20000 }, () => {
  beforeEach(() => {
    fetchAPIMock.mockReset();
  });

  test('o filtro de projetos lê /options/projetos/ e traz todos (mais de 100)', async () => {
    rotear({
      '/options/projetos/': () => Promise.resolve(projetos),
      '/metrics/map/': () => Promise.resolve(MAPA_OK),
    });

    render(<MapaBrasilPage />);

    await waitFor(() => {
      expect(fetchAPIMock.mock.calls.some(([url]) => String(url).includes('/options/projetos/'))).toBe(true);
    });
    const urls = fetchAPIMock.mock.calls.map(([url]) => String(url));
    expect(urls.filter((url) => url.includes('/projetos/') && !url.includes('/options/'))).toEqual([]);
    expect(urls.find((url) => url.includes('/options/projetos/'))).not.toContain('page_size');

    // o filtro mostra o 120º projeto: a lista não é cortada em 100
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Projeto 120' } });
    expect(await screen.findByTitle('Projeto 120')).toBeTruthy();
  });

  test('se a lista de projetos falha (403), o filtro fica em "Todos os Projetos" com aviso', async () => {
    rotear({
      '/options/projetos/': () => Promise.reject(erroHttp(403, 'Você não tem permissão para executar essa ação.')),
      '/metrics/map/': () => Promise.resolve(MAPA_OK),
    });

    render(<MapaBrasilPage />);

    expect(await screen.findByText(/Não foi possível carregar a lista de projetos/)).toBeTruthy();
    expect(screen.getByTitle('Todos os Projetos')).toBeTruthy();
  });

  test('erro do mapa mostra a mensagem do servidor e tenta de novo', async () => {
    let falhar = true;
    rotear({
      '/options/projetos/': () => Promise.resolve([]),
      '/metrics/map/': () =>
        falhar ? Promise.reject(erroHttp(400, 'data_inicio não pode ser maior que data_fim')) : Promise.resolve(MAPA_OK),
    });

    render(<MapaBrasilPage />);

    const alerta = await screen.findByRole('alert');
    expect(within(alerta).getByText('data_inicio não pode ser maior que data_fim')).toBeTruthy();

    falhar = false;
    fireEvent.click(within(alerta).getByRole('button', { name: 'Tentar novamente' }));

    await waitFor(() => {
      expect(screen.queryByText('data_inicio não pode ser maior que data_fim')).toBeNull();
    });
  });

  test('erro dos coordenadores mostra a mensagem do servidor e "Tentar novamente"', async () => {
    let falhar = true;
    rotear({
      '/options/projetos/': () => Promise.resolve([]),
      '/metrics/map/coordinators/': () =>
        falhar
          ? Promise.reject(erroHttp(500, 'Erro 500'))
          : Promise.resolve({ coordenadores: [{ id: 7, nome: 'Pessoa Ficticia', eventos: 1, projetos: [], municipios: [] }] }),
      '/metrics/map/': () => Promise.resolve(MAPA_OK),
    });

    render(<MapaBrasilPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'estado CE' }));

    expect(await screen.findByText(/Não foi possível carregar os coordenadores: Erro 500/)).toBeTruthy();

    falhar = false;
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

    expect(await screen.findByText('Pessoa Ficticia')).toBeTruthy();
  });
});
