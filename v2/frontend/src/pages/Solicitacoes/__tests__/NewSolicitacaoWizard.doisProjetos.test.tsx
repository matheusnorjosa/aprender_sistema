/**
 * NewSolicitacaoWizard — evento de dois projetos (combo, #2036; decisões do dono de 07 e 08/11/2026).
 *
 * O combo guarda os dois projetos, sem principal. O 2º campo só aparece depois do 1º e só lista os
 * projetos que podem ir juntos (mesma gerência e mesmo fluxo: `mesmo_grupo_de` do lookup). Trocar o 1º
 * limpa o 2º; tirar o 1º sobe o 2º. A compra precisa cobrir os dois: o município é reconferido com o
 * 2º projeto, e sem compra para ele o evento vai para aprovação. O erro do par vem na chave `projeto_2`.
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { renderNoRoteador } from '../../../test/comRoteador';
import { botaoDoTexto } from './localizadores';

const { lookupMunicipiosWithFiltersMock, lookupProjetosMock, escolha } = vi.hoisted(() => ({
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  // O que o clique em cada campo escolhe (cada teste troca).
  escolha: {
    projeto: { id: 123, label: 'UNI DUNI TÊ', fluxo: 'SUPER' },
    projeto2: { id: 124, label: 'Cataventos', fluxo: 'SUPER' },
    municipio: { id: 456, label: 'Sobral-CE', kind: 'municipio', sem_compra: false },
  },
}));

vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: vi.fn() }));
vi.mock('../../../api/availability', () => ({ getMe: vi.fn().mockResolvedValue({ is_superuser: false }) }));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));
vi.mock('../../../components/CoordenadoresPicker', () => ({ default: () => null }));

const PH_PROJETO = 'Busque ou selecione um projeto';
const PH_PROJETO_2 = 'Opcional: o outro projeto do combo';
const PH_MUNICIPIO = 'Busque ou selecione um município';

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  value,
  disabled = false,
}: {
  placeholder?: string;
  lookupFunction: (query: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  value?: { label?: string } | null;
  disabled?: boolean;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  // Lido no clique: o teste troca a escolha entre um clique e outro.
  const item = (): unknown =>
    placeholder === PH_PROJETO ? escolha.projeto : placeholder === PH_PROJETO_2 ? escolha.projeto2 : escolha.municipio;
  return (
    <>
      <button type="button" disabled={disabled} onClick={() => onChange?.(item())}>
        {placeholder}
      </button>
      <button type="button" onClick={() => onChange?.(null)}>{`limpar: ${placeholder}`}</button>
      <output>{`valor: ${placeholder}: ${value?.label ?? ''}`}</output>
    </>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import { buildSolicitacaoPayload } from '../NewSolicitacaoWizard';
import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

const valorDe = (placeholder: string): string =>
  screen.getByText((_, el) => el?.tagName === 'OUTPUT' && (el.textContent ?? '').startsWith(`valor: ${placeholder}:`))
    .textContent.slice(`valor: ${placeholder}: `.length);

describe('NewSolicitacaoWizard — evento de dois projetos', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lookupProjetosMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    escolha.projeto = { id: 123, label: 'UNI DUNI TÊ', fluxo: 'SUPER' };
    escolha.projeto2 = { id: 124, label: 'Cataventos', fluxo: 'SUPER' };
    escolha.municipio = { id: 456, label: 'Sobral-CE', kind: 'municipio', sem_compra: false };
  });

  test('o 2º campo só aparece depois do 1º e só lista os compatíveis', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await waitFor(() => botaoDoTexto(PH_PROJETO));
    expect(screen.queryByText(PH_PROJETO_2)).not.toBeInTheDocument();

    fireEvent.click(botaoDoTexto(PH_PROJETO));
    await waitFor(() => botaoDoTexto(PH_PROJETO_2));
    await waitFor(() =>
      expect(lookupProjetosMock).toHaveBeenCalledWith('', { com_compra: true, mesmo_grupo_de: 123 }),
    );
  });

  test('trocar o 1º limpa o 2º', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO)));
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO_2)));
    await waitFor(() => expect(valorDe(PH_PROJETO_2)).toBe('Cataventos'));

    escolha.projeto = { id: 125, label: 'Miudezas', fluxo: 'SUPER' };
    fireEvent.click(botaoDoTexto(PH_PROJETO));
    await waitFor(() => expect(valorDe(PH_PROJETO_2)).toBe(''));
  });

  test('tirar o 1º sobe o 2º', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO)));
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO_2)));
    await waitFor(() => expect(valorDe(PH_PROJETO_2)).toBe('Cataventos'));

    fireEvent.click(screen.getByText(`limpar: ${PH_PROJETO}`));
    await waitFor(() => expect(valorDe(PH_PROJETO)).toBe('Cataventos'));
    expect(valorDe(PH_PROJETO_2)).toBe('');
  });

  test('a lista de municípios confere a compra dos dois', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO)));
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO_2)));
    await waitFor(() =>
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        marcar_sem_compra: true,
        projeto_id: 123,
        projeto_2_id: 124,
      }),
    );
  });

  test('"Aprovado na hora" some quando o 2º não tem compra no município escolhido', async () => {
    escolha.projeto = { id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER' };
    escolha.projeto2 = { id: 124, label: 'Projeto Y', fluxo: 'NAO_SUPER' };
    renderNoRoteador(<NewSolicitacaoWizard />);
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_PROJETO)));
    fireEvent.click(await waitFor(() => botaoDoTexto(PH_MUNICIPIO)));
    expect(await screen.findByText('Aprovado na hora')).toBeInTheDocument();

    // A reconferência do município escolhido, agora com os dois projetos: sem compra para o 2º.
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ ...escolha.municipio, sem_compra: true }]);
    fireEvent.click(botaoDoTexto(PH_PROJETO_2));
    await waitFor(() =>
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        marcar_sem_compra: true,
        projeto_id: 123,
        projeto_2_id: 124,
        municipio_id: 456,
      }),
    );
    expect(await screen.findByText('Vai para aprovação')).toBeInTheDocument();
    expect(screen.queryByText('Aprovado na hora')).not.toBeInTheDocument();
    // O município escolhido continua.
    expect(valorDe(PH_MUNICIPIO)).toBe('Sobral-CE');
  });
});

describe('buildSolicitacaoPayload — o 2º projeto', () => {
  const base = {
    municipioId: 1,
    projetoId: 2,
    tipoEventoId: 3,
    inicio: '2026-12-01T12:00:00Z',
    fim: '2026-12-01T15:00:00Z',
    tipo: '',
    encontro: '',
    segmento: '',
    observacoes: '',
    local: '',
    isOnline: false,
    formadorIds: [],
    coordenadorResponsavelId: null,
    coordenadorExtraIds: [],
    coordenadorAcompanha: false,
    avaliar: null,
  };

  test('o payload leva projeto_2 no combo', () => {
    expect(buildSolicitacaoPayload({ ...base, projeto2Id: 9 })).toMatchObject({ projeto: 2, projeto_2: 9 });
  });

  test('evento de um projeto não manda projeto_2', () => {
    expect(buildSolicitacaoPayload(base)).not.toHaveProperty('projeto_2');
  });
});
