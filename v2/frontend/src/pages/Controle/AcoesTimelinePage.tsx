import { useEffect, useMemo, useState, type JSX } from 'react';
import { Card, Empty, Select, Space, Timeline, Typography, message } from 'antd';
import dayjs from 'dayjs';

import { listAcoesByCiclo, listCiclosAcoes } from '../../api/acoesNotificacao';
import type { AcaoInstancia, CicloAcoes } from '../../types/acoesNotificacao';

const { Title, Text } = Typography;

const ESTADO_LABELS: Record<string, string> = {
  AGUARDANDO_ANCORA: 'Aguardando âncora',
  EM_ANDAMENTO: 'Em andamento',
  CONCLUIDA: 'Concluída',
  ATRASADA: 'Atrasada',
};

const formatarData = (value: string | null): string => (value ? dayjs(value).format('DD/MM/YYYY') : '-');

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
  const [cycleSearch, setCycleSearch] = useState<string>('');
  // Guarda o ciclo escolhido inteiro: a busca troca a lista e ele pode sair dela.
  const [selectedCycle, setSelectedCycle] = useState<CicloAcoes | null>(null);
  const selectedCycleId = selectedCycle?.id ?? null;
  const [actions, setActions] = useState<AcaoInstancia[]>([]);
  const [loadingCycles, setLoadingCycles] = useState<boolean>(false);
  const [loadingActions, setLoadingActions] = useState<boolean>(false);

  const loadActions = async (cycleId: number) => {
    setLoadingActions(true);
    try {
      const data = await listAcoesByCiclo(cycleId);
      setActions(data);
    } catch (error) {
      message.error(`Erro ao carregar a linha do tempo: ${(error as Error).message}`);
    } finally {
      setLoadingActions(false);
    }
  };

  // Busca no servidor (projeto e município): a lista traz até 100 ciclos por vez.
  useEffect(() => {
    let ignore = false;
    const timer = window.setTimeout(
      () => {
        setLoadingCycles(true);
        listCiclosAcoes({ page_size: 100, ordering: '-ano', search: cycleSearch })
          .then((data) => {
            if (ignore) return;
            setCycles(data.results);
            const firstCycle = data.results[0];
            if (firstCycle) {
              setSelectedCycle((current) => current ?? firstCycle);
            }
          })
          .catch((error: unknown) => {
            if (!ignore) message.error(`Erro ao carregar ciclos: ${(error as Error).message}`);
          })
          .finally(() => {
            if (!ignore) setLoadingCycles(false);
          });
      },
      cycleSearch ? 300 : 0,
    );
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [cycleSearch]);

  const cycleOptions =
    selectedCycle && !cycles.some((cycle) => cycle.id === selectedCycle.id) ? [selectedCycle, ...cycles] : cycles;

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
            <Text type="secondary">Estado: {ESTADO_LABELS[action.estado] ?? action.estado}</Text>
            <Text type="secondary">Âncora: {formatarData(action.data_ancora)}</Text>
            <Text type="secondary">Vencimento: {formatarData(action.data_vencimento)}</Text>
            <Text type="secondary">Realização: {formatarData(action.data_realizacao)}</Text>
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
            aria-label="Ciclo"
            loading={loadingCycles}
            value={selectedCycleId ?? undefined}
            onChange={(value) => setSelectedCycle(cycleOptions.find((cycle) => cycle.id === value) ?? null)}
            placeholder="Busque por projeto ou município"
            showSearch
            filterOption={false}
            onSearch={setCycleSearch}
            notFoundContent={loadingCycles ? 'Buscando...' : 'Nenhum ciclo encontrado'}
            options={cycleOptions.map((cycle) => ({
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
