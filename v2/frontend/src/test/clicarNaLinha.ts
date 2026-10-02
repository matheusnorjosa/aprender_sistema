/**
 * Clica num botão da linha de uma tabela quando a tabela deixa.
 *
 * Lista que recarrega sozinha (ao montar, quando chegam metadados; depois de salvar) fica sob o Spin
 * do AntD, que põe `pointer-events: none` na tabela: o user-event recusa o clique (CI, 01/10). Ele
 * recusa antes de disparar qualquer evento no botão, então tentar de novo até a lista assentar não
 * clica duas vezes. A linha é buscada a cada tentativa: a recarga pode trocar o nó.
 */
import { screen, waitFor, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';

/**
 * @param textoDaLinha texto único de uma célula da linha (o nome do registro)
 * @param botao nome acessível do botão: "Editar: <registro>", "Expandir linha de <registro>"
 */
export async function clicarNaLinha(user: UserEvent, textoDaLinha: string, botao: string): Promise<void> {
  const alvo = (): HTMLElement =>
    within(screen.getByText(textoDaLinha).closest<HTMLElement>('tr')!).getByRole('button', { name: botao });
  await waitFor(() => user.click(alvo()), { timeout: 15000 });
}
