/**
 * DateTimeRange - Componente para seleção de data e intervalo de horas
 *
 * Props:
 * - value: { date, start, end } (strings no formato 'YYYY-MM-DD' e 'HH:mm')
 * - onChange: (value) => void
 *
 * Usa dayjs com timezone America/Fortaleza.
 */

import { useState, useEffect, type JSX } from 'react';
import { DatePicker, TimePicker, Space, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { Text } = Typography;

/**
 * DateTimeRange value interface
 */
export interface DateTimeRangeValue {
  date?: string | null;
  start?: string | null;
  end?: string | null;
}

/**
 * DateTimeRange props interface
 */
export interface DateTimeRangeProps {
  value?: DateTimeRangeValue;
  onChange?: (value: DateTimeRangeValue) => void;
  /** Motivo de o horário não valer, junto dos campos: marca os vazios ou, com tudo preenchido, o Fim. */
  erro?: string | null;
}

const ID_DO_ERRO = 'data-horario-erro';

/**
 * Internal state for change trigger
 */
interface ChangeState {
  date: Dayjs | null;
  start: Dayjs | null;
  end: Dayjs | null;
}

export default function DateTimeRange({ value = {}, onChange, erro = null }: DateTimeRangeProps): JSX.Element {
  const [date, setDate] = useState<Dayjs | null>(value.date ? dayjs(value.date) : null);
  const [start, setStart] = useState<Dayjs | null>(value.start ? dayjs(value.start, 'HH:mm') : null);
  const [end, setEnd] = useState<Dayjs | null>(value.end ? dayjs(value.end, 'HH:mm') : null);

  useEffect(() => {
    if (value.date) setDate(dayjs(value.date));
    if (value.start) setStart(dayjs(value.start, 'HH:mm'));
    if (value.end) setEnd(dayjs(value.end, 'HH:mm'));
  }, [value]);

  const handleDateChange = (newDate: Dayjs | null): void => {
    setDate(newDate);
    triggerChange({ date: newDate, start, end });
  };

  const handleStartChange = (newStart: Dayjs | null): void => {
    setStart(newStart);
    triggerChange({ date, start: newStart, end });
  };

  const handleEndChange = (newEnd: Dayjs | null): void => {
    setEnd(newEnd);
    triggerChange({ date, start, end: newEnd });
  };

  const triggerChange = (changedValue: ChangeState): void => {
    if (onChange) {
      const formatted: DateTimeRangeValue = {
        date: changedValue.date ? changedValue.date.format('YYYY-MM-DD') : null,
        start: changedValue.start ? changedValue.start.format('HH:mm') : null,
        end: changedValue.end ? changedValue.end.format('HH:mm') : null,
      };
      onChange(formatted);
    }
  };

  // Com erro: os campos vazios; com tudo preenchido, o Fim (a ordem dos horários).
  const algumVazio = !date || !start || !end;
  const marcar = (vazio: boolean, ehFim = false): { 'aria-invalid'?: 'true'; 'aria-describedby'?: string; status?: 'error'; 'data-campo-horario': true } =>
    erro && (algumVazio ? vazio : ehFim)
      ? { 'aria-invalid': 'true', 'aria-describedby': ID_DO_ERRO, status: 'error', 'data-campo-horario': true }
      : { 'data-campo-horario': true };

  return (
    <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
      <legend className="sr-only">Data e horário do evento</legend>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <label htmlFor="date-picker">
            <Text strong>Data:</Text>
          </label>
          <DatePicker
            id="date-picker"
            value={date}
            onChange={handleDateChange}
            format="DD/MM/YYYY"
            placeholder="Selecione a data"
            className="w-full mt-2"
            {...marcar(!date)}
          />
        </div>
        <Space direction="horizontal" style={{ width: '100%' }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="time-start">
              <Text strong>Início:</Text>
            </label>
            <TimePicker
              id="time-start"
              value={start}
              onChange={handleStartChange}
              format="HH:mm"
              placeholder="HH:mm"
              className="w-full mt-2"
              minuteStep={15}
              // O horário escolhido nas colunas vale sem o OK (sair do campo não o descarta).
              needConfirm={false}
              {...marcar(!start)}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label htmlFor="time-end">
              <Text strong>Fim:</Text>
            </label>
            <TimePicker
              id="time-end"
              value={end}
              onChange={handleEndChange}
              format="HH:mm"
              placeholder="HH:mm"
              className="w-full mt-2"
              minuteStep={15}
              needConfirm={false}
              {...marcar(!end, true)}
            />
          </div>
        </Space>
        {erro ? (
          <div id={ID_DO_ERRO} role="alert">
            <Text type="danger">{erro}</Text>
          </div>
        ) : null}
      </Space>
    </fieldset>
  );
}
