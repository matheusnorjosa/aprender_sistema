/**
 * Registros de Turmas e Plano Anual (alinhamento das telas, 05/11/2026).
 *
 * - Registros: a confirmação de excluir dizia "Esta ação requer permissão de Superintendência".
 *   Excluir é do DAT (`execute_restricted_operations`), não da Superintendência.
 * - Plano Anual: as abas "Calendário" e "Resumo" só mostravam "em desenvolvimento..." e saíram;
 *   o título é o do menu ("Plano Anual"); os textos ganharam acento; e o aviso de excluir não
 *   promete mais remover tudo: o servidor recusa (409) plano com formação concluída.
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { Modal } from 'antd';

import { ComAcesso } from '../../../test/comAcesso';
import { atorRbac } from '../../../test/atoresRbac';

const { registroRow, planoRow } = vi.hoisted(() => ({
  registroRow: {
    id: 9,
    municipio_nome: 'Sobral',
    municipio_uf: 'CE',
    projeto_geral_nome: 'Coleção Y',
    projeto_nome: 'Projeto Y',
    ano: 2026,
    turma_formar_status: 'criada',
  },
  planoRow: {
    id: 1,
    municipio: 1,
    municipio_nome: 'Crato',
    municipio_uf: 'CE',
    projeto: 1,
    projeto_nome: 'Projeto Teste',
    coordenador: null,
    coordenador_nome: null,
    ch_estudo: 10,
    ch_anual: 20,
    observacoes: null,
    formacoes_list: [],
    acompanhamentos_list: [],
    provas_list: [],
  },
}));

vi.mock('../../../api/datModule', () => ({
  listDATRegistros: vi.fn().mockResolvedValue({ results: [registroRow], count: 1, next: null, previous: null }),
  createDATRegistro: vi.fn(),
  updateDATRegistro: vi.fn(),
  deleteDATRegistro: vi.fn(),
  exportDATRegistros: vi.fn(),
  listPlanoFormacoes: vi.fn().mockResolvedValue({ results: [planoRow], count: 1, next: null, previous: null }),
  createPlanoFormacoes: vi.fn().mockResolvedValue({}),
  updatePlanoFormacoes: vi.fn().mockResolvedValue({}),
  deletePlanoFormacoes: vi.fn().mockResolvedValue({}),
  getPlanoFormacoesStats: vi.fn().mockResolvedValue({
    total_planos: 1, total_formacoes: 0, total_realizadas: 0, taxa_realizacao: 0, ch_total: 20,
  }),
  updateFormacaoInline: vi.fn().mockResolvedValue({}),
  updateAcompanhamentoInline: vi.fn().mockResolvedValue({}),
  updateProvaInline: vi.fn().mockResolvedValue({}),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProjetosGeraisOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

import DATRegistrosPage from '../DATRegistrosPage';
import PlanoFormacoesPage from '../PlanoFormacoesPage';

const DAT = atorRbac('DAT').policies;
const REGISTRO = 'Sobral - CE · Projeto Y · 2026';

function renderPagina(pagina: 'registros' | 'plano'): void {
  render(
    <MemoryRouter>
      <ComAcesso policies={DAT}>{pagina === 'registros' ? <DATRegistrosPage /> : <PlanoFormacoesPage />}</ComAcesso>
    </MemoryRouter>,
  );
}

/** Modal.confirm não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe. */
function espiarConfirm(): ReturnType<typeof vi.spyOn> {
  return vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
}

beforeEach(() => vi.clearAllMocks());

describe('Registros de Turmas: confirmação de excluir', { timeout: 20000 }, () => {
  test('não fala em Superintendência', async () => {
    const confirmar = espiarConfirm();
    renderPagina('registros');
    const excluir = await screen.findByRole('button', { name: `Excluir: ${REGISTRO}` }, { timeout: 15000 });

    fireEvent.click(excluir);

    expect(confirmar).toHaveBeenCalledTimes(1);
    const { title, content } = confirmar.mock.calls[0]![0] as { title: string; content: string };
    expect(title).toBe('Confirmar exclusão');
    expect(content).toBe('Excluir registro de "Sobral"? Esta ação não pode ser desfeita.');
    confirmar.mockRestore();
  });
});

describe('Plano Anual', { timeout: 20000 }, () => {
  test('o título é o do menu e o texto tem acento', async () => {
    renderPagina('plano');
    expect(await screen.findByRole('heading', { name: 'Plano Anual' }, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.getByText('Gestão do plano anual de formações por município e projeto')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Município' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Ações' })).toBeInTheDocument();
  });

  test('sem as abas Calendário e Resumo (só "em desenvolvimento...")', async () => {
    renderPagina('plano');
    await screen.findByRole('button', { name: /^Editar: / }, { timeout: 15000 });
    for (const nome of [/Calend[aá]rio/, /Resumo/, /^Tabela$/]) {
      expect(screen.queryByRole('button', { name: nome })).not.toBeInTheDocument();
    }
    expect(screen.queryByText(/em desenvolvimento/)).not.toBeInTheDocument();
  });

  test('o aviso de excluir diz que plano com formação concluída não se exclui', async () => {
    const confirmar = espiarConfirm();
    renderPagina('plano');
    const linha = (await screen.findByRole('button', { name: /^Excluir: / }, { timeout: 15000 })).closest('tr')!;

    fireEvent.click(within(linha).getByRole('button', { name: /^Excluir: / }));

    expect(confirmar).toHaveBeenCalledTimes(1);
    const { title, content } = confirmar.mock.calls[0]![0] as { title: string; content: string };
    expect(title).toBe('Confirmar exclusão');
    expect(content).toBe(
      'Excluir o plano de "Crato" - "Projeto Teste"? As formações, os acompanhamentos e as provas do plano '
        + 'também são excluídos. Plano com formação concluída não pode ser excluído, para preservar o '
        + 'histórico.',
    );
    confirmar.mockRestore();
  });
});
