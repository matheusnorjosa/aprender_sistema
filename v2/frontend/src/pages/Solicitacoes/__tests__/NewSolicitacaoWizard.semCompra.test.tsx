/**
 * NewSolicitacaoWizard — município sem compra (pedido do dono, 03/11/2026).
 *
 * Quem cria pode escolher um município sem compra para o projeto: a lista traz os dois, marcados
 * (`marcar_sem_compra`), e a tela avisa que o evento vai para aprovação. O aviso fica ligado ao campo
 * Município por `aria-describedby`. Quem é isento da regra da compra não vê aviso.
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { ComAcesso } from '../../../test/comAcesso';
import { renderNoRoteador } from '../../../test/comRoteador';
import { botaoDoTexto } from './localizadores';

const { getMeMock, lookupMunicipiosWithFiltersMock, lookupProjetosMock, escolha } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  // O município que o clique no campo escolhe (cada teste troca).
  escolha: {
    projeto: { id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER' },
    municipio: { id: 456, label: 'Sobral-CE', kind: 'municipio', sem_compra: true },
  },
}));

vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: vi.fn() }));
vi.mock('../../../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));
vi.mock('../../../components/CoordenadoresPicker', () => ({ default: () => null }));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  disabled = false,
  'aria-describedby': descritoPor,
}: {
  placeholder?: string;
  lookupFunction: (query: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  disabled?: boolean;
  'aria-describedby'?: string;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  return (
    <button
      type="button"
      disabled={disabled}
      aria-describedby={descritoPor}
      onClick={() =>
        onChange?.(
          placeholder.includes('projeto') ? escolha.projeto : escolha.municipio,
        )
      }
    >
      {placeholder}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

const AVISO = 'Sem compra neste município para este projeto. O evento vai para aprovação.';

describe('NewSolicitacaoWizard — município sem compra', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lookupProjetosMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ is_superuser: false });
    escolha.projeto = { id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER' };
    escolha.municipio = { id: 456, label: 'Sobral-CE', kind: 'municipio', sem_compra: true };
  });

  const escolherProjetoEMunicipio = async (): Promise<HTMLElement> => {
    fireEvent.click(await waitFor(() => botaoDoTexto('Busque ou selecione um projeto')));
    const municipio = await waitFor(() => botaoDoTexto('Busque ou selecione um município'));
    fireEvent.click(municipio);
    return municipio;
  };

  test('a lista de municípios pede a marca de sem compra pelo projeto', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    fireEvent.click(await waitFor(() => botaoDoTexto('Busque ou selecione um projeto')));
    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenLastCalledWith({
        q: '',
        marcar_sem_compra: true,
        projeto_id: 123,
      });
    });
  });

  test('município sem compra: aviso ligado ao campo e a situação diz que vai para aprovação', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    const municipio = await escolherProjetoEMunicipio();

    const aviso = await screen.findByText(AVISO);
    const ids = (municipio.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);
    expect(ids.some((id) => document.getElementById(id)?.contains(aviso))).toBe(true);
    expect(aviso.closest('.ant-alert-warning')).not.toBeNull();
    expect(screen.getByText('Vai para aprovação')).toBeInTheDocument();
    expect(screen.queryByText('Aprovado na hora')).not.toBeInTheDocument();
  });

  test('município com compra: sem aviso e o NAO_SUPER segue aprovado na hora', async () => {
    escolha.municipio = { id: 457, label: 'Crato-CE', kind: 'municipio', sem_compra: false };
    renderNoRoteador(<NewSolicitacaoWizard />);
    await escolherProjetoEMunicipio();

    expect(await screen.findByText('Aprovado na hora')).toBeInTheDocument();
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test('o aviso sai quando o projeto muda (o município sai junto)', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await escolherProjetoEMunicipio();
    await screen.findByText(AVISO);

    // Outro projeto: o cartão limpa o município.
    escolha.projeto = { id: 124, label: 'Projeto Y', fluxo: 'NAO_SUPER' };
    fireEvent.click(botaoDoTexto('Busque ou selecione um projeto'));
    await waitFor(() => expect(screen.queryByText(AVISO)).not.toBeInTheDocument());
  });

  test('quem é isento da regra da compra não vê aviso', async () => {
    renderNoRoteador(
      <ComAcesso policies={['create_solicitation', 'create_solicitation_without_purchase']}>
        <NewSolicitacaoWizard />
      </ComAcesso>,
    );
    await escolherProjetoEMunicipio();

    expect(await screen.findByText('Aprovado na hora')).toBeInTheDocument();
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });
});
