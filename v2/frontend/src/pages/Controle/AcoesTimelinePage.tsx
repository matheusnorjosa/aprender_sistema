import { useEffect, useMemo, useState } from 'react';
import { Card, Empty, Select, Space, Timeline, Typography, message } from 'antd';

import { listAcoesByCiclo, listCiclosAcoes } from '../../api/acoesNotificacao';
import type { AcaoInstancia, CicloAcoes } from '../../types/acoesNotificacao';

const { Title, Text } = Typography;

function getTimelineColor(estado: string): string {
  if (estado === 'CONCLUIDA') {
    return 'green';
  }
  if (estado === 'ATRASADA') {
    return 'red';
  }
  if (estado === 'EM_ANDAMENTO') {
    return 'blue';
  }
  return 'gray';
}

export default function AcoesTimelinePage(): JSX.Element {
  const [cycles, setCycles] = useState<CicloAcoes[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [actions, setActions] = useState<AcaoInstancia[]>([]);
  const [loadingCycles, setLoadingCycles] = useState<boolean>(false);
  const [loadingActions, setLoadingActions] = useState<boolean>(false);

  const loadCycles = async () => {
    setLoadingCycles(true);
    try {
      const data = await listCiclosAcoes({ page_size: 100, ordering: '-ano' });
      setCycles(data.results);
      if (!selectedCycleId && data.results.length > 0) {
        setSelectedCycleId(data.results[0].id);
      }
    } catch (error) {
      message.error(`Erro ao carregar ciclos: ${(error as Error).message}`);
    } finally {
      setLoadingCycles(false);
    }
  };

  const loadActions = async (cycleId: number) => {
    setLoadingActions(true);
    try {
      const data = await listAcoesByCiclo(cycleId);
      setActions(data);
    } catch (error) {
      message.error(`Erro ao carregar timeline: ${(error as Error).message}`);
    } finally {
      setLoadingActions(false);
    }
  };

  useEffect(() => {
    void loadCycles();
  }, []);

  useEffect(() => {
    if (selectedCycleId) {
      void loadActions(selectedCycleId);
    }
  }, [selectedCycleId]);

  const items = useMemo(() => {
    return [...actions]
      .sort((a, b) => a.ordem - b.ordem)
      .map((action) => ({
        color: getTimelineColor(action.estado),
        children: (
          <Space direction="vertical" size={0}>
            <Text strong>
              #{action.ordem} - {action.template_nome}
            </Text>
            <Text type="secondary">Estado: {action.estado}</Text>
            <Text type="secondary">Âncora: {action.data_ancora || '-'}</Text>
            <Text type="secondary">Vencimento: {action.data_vencimento || '-'}</Text>
            <Text type="secondary">Realização: {action.data_realizacao || '-'}</Text>
          </Space>
        ),
      }));
  }, [actions]);

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>
            Timeline das Ações
          </Title>
          <Text type="secondary">Visão cronológica do status operacional por ciclo.</Text>
        </div>

        <Card>
          <Select
            loading={loadingCycles}
            value={selectedCycleId ?? undefined}
            onChange={(value) => setSelectedCycleId(value)}
            placeholder="Selecione o ciclo"
            options={cycles.map((cycle) => ({
              value: cycle.id,
              label: `${cycle.projeto_nome} / ${cycle.municipio_nome} (${cycle.semestre}/${cycle.ano})`,
            }))}
            style={{ width: 520, maxWidth: '100%' }}
          />
        </Card>

        <Card loading={loadingActions}>
          {items.length === 0 ? <Empty description="Sem ações para o ciclo selecionado" /> : <Timeline items={items} />}
        </Card>
      </Space>
    </main>
  );
}
