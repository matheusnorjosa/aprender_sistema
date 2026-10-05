/**
 * C2 (Programa C) — Municípios: importação, salvar e estados que não mentem.
 *
 * - A validação da importação lia um formato antigo (`stats`/`pendencias`, que o cliente
 *   `importMunicipios` já achata em `ImportResult`): mostrava sempre 0/0/0 e "Validação OK",
 *   mesmo com pendência que bloqueia. Agora mostra as contagens e as pendências reais.
 * - O erro de validação do backend (IBGE repetido) aparece com o motivo, no campo.
 * - Salvar com loading; UF antes do nome, já com a UF do filtro; vazio do filtro com "Limpar".
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { MUNICIPIO } = vi.hoisted(() => ({
  MUNICIPIO: { id: 917, nome: 'São Sebastião dos Campos Gerais', uf: 'BA', ibge_code: '2927408', ativo: true },
}));

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));
vi.mock('../../../api/ops', () => ({ importMunicipios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listMunicipios: vi.fn(),
  createMunicipio: vi.fn(),
  updateMunicipio: vi.fn(),
  deleteMunicipio: vi.fn(),
  autocompleteMunicipiosAdmin: vi.fn().mockResolvedValue([]),
}));

import { checkAuth } from '../../../api/auth';
import { importMunicipios } from '../../../api/ops';
import { deleteMunicipio, listMunicipios, updateMunicipio } from '../../../api/adminDAT';
import MunicipiosPage from '../MunicipiosPage';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <MunicipiosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linha(): Promise<HTMLElement> {
  const nome = await screen.findByText(MUNICIPIO.nome, { selector: 'td, td *' }, { timeout: 15000 });
  return nome.closest<HTMLElement>('tr')!;
}

async function abrirEditar(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(within(await linha()).getByRole('button', { name: `Editar: ${MUNICIPIO.nome} - BA` }));
  return (await screen.findByText('Editar Município', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;
}

describe('MunicipiosPage: importar e salvar (C2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    vi.mocked(listMunicipios).mockResolvedValue({ results: [MUNICIPIO], count: 1, next: null, previous: null } as never);
  });

  test('importação pela tela é só do superusuário: para os demais o cartão de importar não aparece', async () => {
    // Decisão do dono (02/10/2026). O backend também recusa (403).
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: false } } as never);
    const { container } = renderPage();
    await linha();
    await waitFor(() => expect(checkAuth).toHaveBeenCalled());

    expect(screen.queryByText('Importação de Municípios')).not.toBeInTheDocument();
    expect(container.querySelector('input[type="file"]')).toBeNull();
  }, 30000);

  test('superusuário vê o cartão de importar', async () => {
    renderPage();
    await linha();

    expect(await screen.findByText('Importação de Municípios')).toBeInTheDocument();
  }, 30000);

  test('validação da importação: contagens e pendências reais; pendência que bloqueia não diz "Validação OK"', async () => {
    // O que o cliente `importMunicipios` devolve (ImportResult, já achatado pelo api/ops).
    vi.mocked(importMunicipios).mockResolvedValue({
      created: 3,
      updated: 1,
      skipped: 2,
      errors: [{ row: 4, message: '[uf_missing] UF ausente — Cidade Fictícia' }],
      warnings: [],
    });
    const user = userEvent.setup();
    const { container } = renderPage();
    await linha();
    await screen.findByText('Importação de Municípios');

    const arquivo = new File(['nome,uf\nCidade Fictícia,\n'], 'municipios.csv', { type: 'text/csv' });
    await user.upload(container.querySelector<HTMLInputElement>('input[type="file"]')!, arquivo);
    await user.click(await screen.findByRole('button', { name: /Validar Importação/ }));

    expect(await screen.findByText('Validação com Erros', {}, { timeout: 10000 })).toBeInTheDocument();
    expect(screen.queryByText('Validação OK')).not.toBeInTheDocument();
    expect(screen.getByText('Linha 4: [uf_missing] UF ausente — Cidade Fictícia')).toBeInTheDocument();
    const contagens = Array.from(document.querySelectorAll('.ant-statistic-content-value')).map((n) => n.textContent);
    expect(contagens).toEqual(['3', '1', '2']);
  }, 40000);

  test('erro de validação ao salvar: o motivo do backend no toast e no campo', async () => {
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    vi.mocked(updateMunicipio).mockRejectedValue(
      Object.assign(new Error('Erro de validação.'), {
        response: {
          status: 400,
          data: { detail: 'Erro de validação.', errors: { ibge_code: ['município com este Código IBGE já existe.'] } },
        },
      }),
    );
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Erro: município com este Código IBGE já existe.'));
    expect(await within(modal).findByText('município com este Código IBGE já existe.')).toBeInTheDocument();
    erro.mockRestore();
  }, 40000);

  test('Salvar fica em loading enquanto a API trabalha (sem clique mudo nem envio duplo)', async () => {
    vi.mocked(updateMunicipio).mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(within(modal).getByRole('button', { name: /Salvar/ })).toHaveClass('ant-btn-loading'));
  }, 40000);

  test('Novo: a UF vem antes do nome e já com a UF do filtro', async () => {
    const user = userEvent.setup();
    renderPage();
    await linha();

    await user.click(screen.getByRole('combobox', { name: 'Filtrar por UF' }));
    await user.click(await screen.findByTitle('BA'));
    await user.click(screen.getByRole('button', { name: /Novo Município/ }));

    const modal = (await screen.findByText('Novo Município', { selector: '.ant-modal-title' })).closest<HTMLElement>(
      '[role="dialog"]',
    )!;
    const rotulos = Array.from(modal.querySelectorAll('label')).map((l) => l.textContent);
    expect(rotulos.indexOf('UF')).toBeLessThan(rotulos.indexOf('Nome do Município'));
    expect(within(modal).getByRole('combobox', { name: 'UF' }).closest('.ant-select')).toHaveTextContent('BA');
    expect(within(modal).getByRole('combobox', { name: 'Nome do Município' })).toBeEnabled();
  }, 40000);

  test('filtro sem resultado: diz que é o filtro e oferece limpá-lo', async () => {
    const user = userEvent.setup();
    renderPage();
    await linha();
    vi.mocked(listMunicipios).mockResolvedValue({ results: [], count: 0, next: null, previous: null });

    await user.click(screen.getByRole('combobox', { name: 'Filtrar por UF' }));
    await user.click(await screen.findByTitle('PI'));

    expect(await screen.findByText('Nenhum município para a UF PI.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Limpar filtro de UF' }));
    await waitFor(() => expect(listMunicipios).toHaveBeenLastCalledWith(expect.objectContaining({ uf: undefined })));
  }, 40000);

  test('falha ao carregar a lista: o motivo e "Tentar de novo", não "Não há dados"', async () => {
    vi.mocked(listMunicipios).mockRejectedValue(new Error('Recurso não encontrado.'));
    renderPage();

    const alerta = await screen.findByText('Não foi possível carregar a lista.', {}, { timeout: 15000 });
    expect(alerta.closest('[role="alert"]')).toHaveTextContent('Recurso não encontrado.');
    expect(screen.queryByText('Não há dados')).not.toBeInTheDocument();
    // Sem número no título: "(0)" diria que não há município.
    expect(screen.getByRole('heading', { level: 3, name: /^Municípios/ })).toHaveTextContent(/^Municípios$/);
  }, 30000);

  test('excluir registro em uso (409): o motivo e "Desativar", que grava ativo=false e recarrega a lista (C2b)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Compras, Solicitações de Evento).';
    vi.mocked(deleteMunicipio).mockRejectedValue(
      Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }),
    );
    vi.mocked(updateMunicipio).mockResolvedValue({ ...MUNICIPIO, ativo: false } as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha()).getByRole('button', { name: `Excluir: ${MUNICIPIO.nome} - BA` }));
    await confirmar.mock.calls[0]![0].onOk!();
    // O diálogo do 409 só abre quando a confirmação termina de fechar: um por vez, sem perder o foco.
    expect(confirmar).toHaveBeenCalledTimes(1);
    confirmar.mock.calls[0]![0].afterClose!();

    expect(erro).not.toHaveBeenCalled();
    expect(confirmar).toHaveBeenCalledTimes(2);
    const emUso = confirmar.mock.calls[1]![0];
    expect(String(emUso.content)).toContain(motivo);
    expect(String(emUso.content)).toContain(`Você pode desativar o município "${MUNICIPIO.nome} - BA"`);
    expect(emUso.okText).toBe('Desativar');
    const cargas = vi.mocked(listMunicipios).mock.calls.length;
    await emUso.onOk!();

    expect(updateMunicipio).toHaveBeenCalledWith(MUNICIPIO.id, { ativo: false });
    expect(sucesso).toHaveBeenCalledWith('Município desativado');
    await waitFor(() => expect(listMunicipios).toHaveBeenCalledTimes(cargas + 1));
    confirmar.mockRestore();
    erro.mockRestore();
    sucesso.mockRestore();
  }, 30000);
});
