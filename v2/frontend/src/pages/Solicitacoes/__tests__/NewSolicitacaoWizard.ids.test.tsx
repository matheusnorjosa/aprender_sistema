/**
 * Nova Solicitação com vários eventos: nenhum id repetido no DOM (PR 5).
 *
 * Com os componentes de verdade (ComboBox, DateTimeRange, FormadoresPicker), porque são eles que
 * põem os ids nos campos. Id repetido quebra `label for`, `aria-describedby` e o foco do resumo:
 * o leitor de tela leria o campo (ou o erro) do outro evento.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderNoRoteador } from '../../../test/comRoteador';
import { botaoDoTexto, cartao } from './localizadores';

vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: vi.fn() }));
vi.mock('../../../api/availability', () => ({
  getMe: vi.fn().mockResolvedValue({ id: 1, name: 'Ana', username: 'ana', is_superuser: false }),
  checkAvailabilityMany: vi.fn().mockResolvedValue({ ok: true, results: [] }),
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

function idsRepetidos(): string[] {
  const contagem = new Map<string, number>();
  document.querySelectorAll('[id]').forEach((el) => contagem.set(el.id, (contagem.get(el.id) ?? 0) + 1));
  return [...contagem].filter(([, n]) => n > 1).map(([id]) => id);
}

function nomesDeRadioRepetidos(): string[] {
  const porNome = new Map<string, Set<Element>>();
  document.querySelectorAll('input[type="radio"]').forEach((el) => {
    const nome = el.getAttribute('name') ?? '';
    const grupo = el.closest('[role="radiogroup"]');
    if (!grupo) return;
    porNome.set(nome, (porNome.get(nome) ?? new Set()).add(grupo));
  });
  return [...porNome].filter(([, grupos]) => grupos.size > 1).map(([nome]) => nome);
}

describe('NewSolicitacaoWizard — ids com vários eventos', { timeout: 30000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('com 3 eventos, e com os erros de todos à vista, nenhum id nem nome de radio se repete', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await waitFor(() => cartao(1));
    const adicionar = botaoDoTexto(/Adicionar outro evento/);
    fireEvent.click(adicionar);
    fireEvent.click(adicionar);
    expect(document.querySelectorAll('section[aria-labelledby^="evento-"]')).toHaveLength(3);
    expect(idsRepetidos()).toEqual([]);

    // Os erros (inclusive o do horário, que tem id próprio) aparecem nos 3 de uma vez.
    fireEvent.click(botaoDoTexto('Criar 3 eventos'));
    await waitFor(
      () => expect(screen.getAllByText('Escolha a data e os horários de início e de fim do evento.')).toHaveLength(3),
      { timeout: 5000 },
    );
    await waitFor(() => expect(screen.getAllByText('Por favor selecione um projeto')).toHaveLength(3), { timeout: 5000 });
    expect(idsRepetidos()).toEqual([]);
    expect(nomesDeRadioRepetidos()).toEqual([]);
  });
});
