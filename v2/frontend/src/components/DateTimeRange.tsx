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
  /**
   * `linha`: Data, Início e Fim lado a lado a partir de md e empilhados no celular (cartão da Nova
   * Solicitação). Sem a prop, o arranjo de sempre (Data numa linha, Início e Fim na outra; Edição).
   */
  layout?: 'linha';
  /** Prefixo dos ids (campos e erro), para dois cartões na mesma página não repetirem id. */
  idPrefix?: string;
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

export default function DateTimeRange({
  value = {},
  onChange,
  erro = null,
  layout,
  idPrefix = '',
}: DateTimeRangeProps): JSX.Element {
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
  const idDoErro = `${idPrefix}${ID_DO_ERRO}`;
  const marcar = (vazio: boolean, ehFim = false): { 'aria-invalid'?: 'true'; 'aria-describedby'?: string; status?: 'error'; 'data-campo-horario': true } =>
    erro && (algumVazio ? vazio : ehFim)
      ? { 'aria-invalid': 'true', 'aria-describedby': idDoErro, status: 'error', 'data-campo-horario': true }
      : { 'data-campo-horario': true };

  // Na linha, cada campo encolhe com a coluna (min-w-0) e nada passa da largura da tela.
  const emLinha = layout === 'linha';
  const celula = emLinha ? 'min-w-0' : undefined;
  const metade = emLinha ? undefined : { flex: 1 };
  const campoData = (
    <div className={celula}>
      <label htmlFor={`${idPrefix}date-picker`}>
        <Text strong>Data:</Text>
      </label>
      <DatePicker
        id={`${idPrefix}date-picker`}
        value={date}
        onChange={handleDateChange}
        format="DD/MM/YYYY"
        placeholder="Selecione a data"
        className="w-full mt-2"
        {...marcar(!date)}
      />
    </div>
  );
  const campoInicio = (
    <div className={celula} style={metade}>
      <label htmlFor={`${idPrefix}time-start`}>
        <Text strong>Início:</Text>
      </label>
      <TimePicker
        id={`${idPrefix}time-start`}
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
  );
  const campoFim = (
    <div className={celula} style={metade}>
      <label htmlFor={`${idPrefix}time-end`}>
        <Text strong>Fim:</Text>
      </label>
      <TimePicker
        id={`${idPrefix}time-end`}
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
  );
  // Na linha (cartão da Nova Solicitação) o erro não é região viva: quem anuncia é o resumo da
  // página, uma região só. O campo continua apontando o texto (`aria-describedby`).
  const mensagemDeErro = erro ? (
    <div id={idDoErro} role={emLinha ? undefined : 'alert'}>
      <Text type="danger">{erro}</Text>
    </div>
  ) : null;

  return (
    <fieldset
      // Na linha: a legenda escondida (absoluta) fica dentro do fieldset e não alarga a página
      // (o reset do antd dá `width: 100%` à legend); min-width 0 deixa o fieldset encolher na coluna.
      style={{ border: 'none', padding: 0, margin: 0, ...(emLinha ? { position: 'relative', minWidth: 0 } : {}) }}
    >
      <legend className="sr-only">Data e horário do evento</legend>
      {emLinha ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {campoData}
            {campoInicio}
            {campoFim}
          </div>
          {mensagemDeErro}
        </>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }}>
          {campoData}
          <Space direction="horizontal" style={{ width: '100%' }}>
            {campoInicio}
            {campoFim}
          </Space>
          {mensagemDeErro}
        </Space>
      )}
    </fieldset>
  );
}
