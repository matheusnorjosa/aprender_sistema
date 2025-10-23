/**
 * DateTimeRange - Componente para seleção de data e intervalo de horas
 *
 * Props:
 * - value: { date, start, end } (strings no formato 'YYYY-MM-DD' e 'HH:mm')
 * - onChange: (value) => void
 *
 * Usa dayjs com timezone America/Fortaleza.
 */

import { useState, useEffect } from 'react';
import { DatePicker, TimePicker, Space, Typography } from 'antd';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { Text } = Typography;

export default function DateTimeRange({ value = {}, onChange }) {
  const [date, setDate] = useState(value.date ? dayjs(value.date) : null);
  const [start, setStart] = useState(value.start ? dayjs(value.start, 'HH:mm') : null);
  const [end, setEnd] = useState(value.end ? dayjs(value.end, 'HH:mm') : null);

  useEffect(() => {
    if (value.date) setDate(dayjs(value.date));
    if (value.start) setStart(dayjs(value.start, 'HH:mm'));
    if (value.end) setEnd(dayjs(value.end, 'HH:mm'));
  }, [value]);

  const handleDateChange = (newDate) => {
    setDate(newDate);
    triggerChange({ date: newDate, start, end });
  };

  const handleStartChange = (newStart) => {
    setStart(newStart);
    triggerChange({ date, start: newStart, end });
  };

  const handleEndChange = (newEnd) => {
    setEnd(newEnd);
    triggerChange({ date, start, end: newEnd });
  };

  const triggerChange = (changedValue) => {
    if (onChange) {
      const formatted = {
        date: changedValue.date ? changedValue.date.format('YYYY-MM-DD') : null,
        start: changedValue.start ? changedValue.start.format('HH:mm') : null,
        end: changedValue.end ? changedValue.end.format('HH:mm') : null,
      };
      onChange(formatted);
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <div>
        <Text strong>Data:</Text>
        <DatePicker
          value={date}
          onChange={handleDateChange}
          format="DD/MM/YYYY"
          placeholder="Selecione a data"
          style={{ width: '100%', marginTop: 8 }}
        />
      </div>
      <Space direction="horizontal" style={{ width: '100%' }}>
        <div style={{ flex: 1 }}>
          <Text strong>Início:</Text>
          <TimePicker
            value={start}
            onChange={handleStartChange}
            format="HH:mm"
            placeholder="HH:mm"
            style={{ width: '100%', marginTop: 8 }}
            minuteStep={15}
          />
        </div>
        <div style={{ flex: 1 }}>
          <Text strong>Fim:</Text>
          <TimePicker
            value={end}
            onChange={handleEndChange}
            format="HH:mm"
            placeholder="HH:mm"
            style={{ width: '100%', marginTop: 8 }}
            minuteStep={15}
          />
        </div>
      </Space>
    </Space>
  );
}
