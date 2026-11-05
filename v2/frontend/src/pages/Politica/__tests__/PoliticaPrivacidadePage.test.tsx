/**
 * Tests da página /politica-privacidade.
 *
 * - A seção tem nome acessível curto ("Política de Privacidade"), não o documento inteiro.
 * - O texto diz que o acesso vem da lotação (gerência e papel), não de setores e funções.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import PoliticaPrivacidadePage from '../PoliticaPrivacidadePage';

describe('PoliticaPrivacidadePage', { timeout: 20000 }, () => {
  test('a seção se chama "Política de Privacidade"', () => {
    render(<PoliticaPrivacidadePage />);
    expect(screen.getByRole('region', { name: 'Política de Privacidade' })).toBeInTheDocument();
  });

  test('diz que o acesso vem da lotação (gerência e papel)', async () => {
    render(<PoliticaPrivacidadePage />);
    expect(await screen.findByText(/gerência e papel \(lotação\), que definem o acesso/)).toBeInTheDocument();
    expect(screen.queryByText(/setores e funções/)).not.toBeInTheDocument();
  });
});
