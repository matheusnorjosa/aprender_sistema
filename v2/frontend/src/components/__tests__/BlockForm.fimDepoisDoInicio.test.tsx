/**
 * G08: o servidor recusa bloqueio com fim igual ao início (serializers/agenda.py, `fim <= inicio`).
 * O formulário aceitava esse caso e a pessoa só descobria o erro pela volta do servidor. Agora o
 * próprio formulário barra: o fim tem que ser depois do início.
 *
 * O DatePicker real do antd é frágil em jsdom; aqui ele vira um input que entrega um Dayjs ao
 * Form.Item, como o original. O validador e as regras do formulário são os reais.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import dayjs from 'dayjs';
import { describe, expect, test, vi } from 'vitest';

import BlockForm from '../BlockForm';

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  const dayjsLib = (await import('dayjs')).default;
  const MockDatePicker = ({
    id,
    value,
    onChange,
  }: {
    id?: string;
    value?: import('dayjs').Dayjs | null;
    onChange?: (v: import('dayjs').Dayjs | null) => void;
  }) => (
    <input
      id={id}
      value={value ? value.format('YYYY-MM-DDTHH:mm') : ''}
      onChange={(e) => onChange?.(e.target.value ? dayjsLib(e.target.value) : null)}
    />
  );
  return { ...actual, DatePicker: MockDatePicker };
});

const MENSAGEM = 'O fim deve ser depois do início.';

async function preencher(inicio: string, fim: string): Promise<void> {
  fireEvent.change(screen.getByLabelText('Data/Hora Início'), { target: { value: inicio } });
  fireEvent.change(screen.getByLabelText('Data/Hora Fim'), { target: { value: fim } });
  const user = userEvent.setup();
  await user.click(screen.getByRole('combobox', { name: 'Tipo de Bloqueio' }));
  await user.click(await screen.findByText('Total (T)'));
  await user.click(screen.getByRole('button', { name: 'Criar Bloqueio' }));
}

describe('BlockForm: o fim tem que ser depois do início', { timeout: 20000 }, () => {
  const amanha = dayjs().add(1, 'day').format('YYYY-MM-DD');

  test('início igual ao fim não envia e mostra a mensagem', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BlockForm onSubmit={onSubmit} />);

    await preencher(`${amanha}T10:00`, `${amanha}T10:00`);

    expect((await screen.findAllByText(MENSAGEM)).length).toBeGreaterThan(0);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test('fim depois do início envia', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BlockForm onSubmit={onSubmit} />);

    await preencher(`${amanha}T10:00`, `${amanha}T11:00`);

    await vi.waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(MENSAGEM)).not.toBeInTheDocument();
  });
});
