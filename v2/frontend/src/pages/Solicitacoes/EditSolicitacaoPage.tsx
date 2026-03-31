/**
 * Editar Solicitação - Formulário de Edição
 *
 * Permite editar solicitações existentes antes da publicação no Google Calendar.
 *
 * Regras:
 * - Apenas o criador ou usuários privilegiados (Superintendência/DAT) podem editar
 * - Não é possível editar solicitações já publicadas no Google Calendar
 * - Não é possível editar solicitações reprovadas
 */

import { useState, useEffect, useMemo, useCallback, ChangeEvent, JSX } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
// antd - direct imports for tree-shaking (Issue #424)
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Alert from 'antd/es/alert';
import message from 'antd/es/message';
import Typography from 'antd/es/typography';
import Spin from 'antd/es/spin';
import Checkbox from 'antd/es/checkbox';
import Result from 'antd/es/result';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
// icons - direct imports for tree-shaking (Issue #425)
import ArrowLeftOutlined from '@ant-design/icons/ArrowLeftOutlined';
import SaveOutlined from '@ant-design/icons/SaveOutlined';
import CalendarOutlined from '@ant-design/icons/CalendarOutlined';
import StopOutlined from '@ant-design/icons/StopOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { getSolicitacao, updateSolicitacao } from '../../api/solicitacoes';
import {
  lookupMunicipios,
  lookupProjetos,
  lookupTiposEvento,
} from '../../api/lookup';
import DateTimeRange from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import FormadoresPicker from '../../components/FormadoresPicker';
import logger from '../../utils/logger';
import type { ID, Solicitacao, GCalStatus, Participation } from '../../types';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;

const RANGE_TIMEZONE = 'America/Fortaleza';

/** ComboBox value type */
interface ComboBoxValue {
  id: ID;
  label: string;
  fluxo?: string;
}

/** Formador type */
interface FormadorType {
  id: ID;
  label: string;
  email?: string;
}

/** Form data type */
interface FormDataType {
  projeto: ComboBoxValue | null;
  tipoEvento: ComboBoxValue | null;
  municipio: ComboBoxValue | null;
  inicio: string | null;
  fim: string | null;
  tipo: string;
  encontro: string;
  segmento: string;
  observacoes: string;
  local: string;
  is_online: boolean;
  formadores: FormadorType[];
}

/** Range value type */
interface RangeValueType {
  date: string;
  start: string;
  end: string;
}

/** API error response type */
interface ApiErrorResponse {
  response?: {
    status?: number;
    data?: {
      non_field_errors?: string[];
    };
  };
}

export default function EditSolicitacaoPage(): JSX.Element {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [solicitacao, setSolicitacao] = useState<Solicitacao | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Estado do formulário
  const [formData, setFormData] = useState<FormDataType>({
    projeto: null,
    tipoEvento: null,
    municipio: null,
    inicio: null,
    fim: null,
    tipo: '',
    encontro: '',
    segmento: '',
    observacoes: '',
    local: '',
    is_online: false,
    formadores: [],
  });

  // Carregar dados da solicitação
  useEffect(() => {
    const fetchSolicitacao = async (): Promise<void> => {
      try {
        setLoading(true);
        const data = await getSolicitacao(Number(id)) as Solicitacao;
        setSolicitacao(data);

        // Extrair formadores das participations
        const formadores: FormadorType[] = (data.participations || [])
          .filter((p: Participation) => p.role === 'FORMADOR' && p.usuario)
          .map((p: Participation) => ({
            id: p.usuario!.id,
            label: p.usuario!.first_name && p.usuario!.last_name
              ? `${p.usuario!.first_name} ${p.usuario!.last_name}`.trim()
              : p.usuario!.username,
            email: p.usuario!.email,
          }));

        // Preencher o formData com os dados existentes
        setFormData({
          projeto: data.projeto ? { id: data.projeto, label: data.projeto_nome || '' } : null,
          tipoEvento: data.tipo_evento ? { id: data.tipo_evento, label: data.tipo_evento_nome || '' } : null,
          municipio: data.municipio ? { id: data.municipio, label: data.municipio_nome || '' } : null,
          inicio: data.inicio,
          fim: data.fim,
          tipo: data.tipo || '',
          encontro: data.encontro || '',
          segmento: data.segmento || '',
          observacoes: data.observacoes || '',
          local: data.local || '',
          is_online: data.is_online || false,
          formadores,
        });

        // Preencher o form do Ant Design
        form.setFieldsValue({
          tipo: data.tipo || '',
          encontro: data.encontro || '',
          segmento: data.segmento || '',
          observacoes: data.observacoes || '',
          local: data.local || '',
          is_online: data.is_online || false,
        });
      } catch (err) {
        logger.error('Erro ao carregar solicitação:', err);
        const apiErr = err as ApiErrorResponse;
        if (apiErr.response?.status === 404) {
          setError('Solicitação não encontrada.');
        } else if (apiErr.response?.status === 403) {
          setError('Você não tem permissão para editar esta solicitação.');
        } else {
          setError('Erro ao carregar solicitação. Tente novamente.');
        }
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchSolicitacao();
    }
  }, [id, form]);

  // Handler para DateTimeRange (Issue #428)
  const handleRangeChange = useCallback((range: RangeValueType | null): void => {
    if (!range || !range.date || !range.start || !range.end) {
      setFormData(prev => ({ ...prev, inicio: null, fim: null }));
      return;
    }

    try {
      const dateStr = range.date;
      const startTime = range.start;
      const endTime = range.end;

      const inicioLocal = dayjs.tz(`${dateStr} ${startTime}`, RANGE_TIMEZONE);
      const fimLocal = dayjs.tz(`${dateStr} ${endTime}`, RANGE_TIMEZONE);

      const isoInicio = inicioLocal.utc().format();
      const isoFim = fimLocal.utc().format();

      setFormData(prev => ({ ...prev, inicio: isoInicio, fim: isoFim }));
    } catch (error) {
      logger.error('Erro ao converter data/hora:', error);
      setFormData(prev => ({ ...prev, inicio: null, fim: null }));
    }
  }, []);

  // Derivar rangeValue memoizado (Issue #428)
  const rangeValue = useMemo((): RangeValueType => {
    if (!formData.inicio || !formData.fim) {
      return { date: '', start: '', end: '' };
    }
    return {
      date: dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('YYYY-MM-DD'),
      start: dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('HH:mm'),
      end: dayjs(formData.fim).tz(RANGE_TIMEZONE).format('HH:mm'),
    };
  }, [formData.inicio, formData.fim]);

  // Submit
  const handleSubmit = async (): Promise<void> => {
    setSaving(true);
    try {
      // Validações
      if (!formData.inicio || !formData.fim) {
        message.error('Por favor, selecione data/hora de início e fim');
        setSaving(false);
        return;
      }

      if (!formData.municipio) {
        message.error('Por favor, selecione um município');
        setSaving(false);
        return;
      }

      if (!formData.projeto) {
        message.error('Por favor, selecione um projeto');
        setSaving(false);
        return;
      }

      if (!formData.tipoEvento) {
        message.error('Por favor, selecione um tipo de evento');
        setSaving(false);
        return;
      }

      // Garantir que formadores é um array
      const formadores = Array.isArray(formData.formadores) ? formData.formadores : [];

      if (formadores.length === 0) {
        message.error('Por favor, selecione pelo menos um formador');
        setSaving(false);
        return;
      }

      const payload = {
        municipio: formData.municipio.id,
        projeto: formData.projeto.id,
        tipo_evento: formData.tipoEvento.id,
        inicio: dayjs(formData.inicio).utc().format(),
        fim: dayjs(formData.fim).utc().format(),
        tipo: formData.tipo || null,
        encontro: formData.encontro || null,
        segmento: formData.segmento || null,
        observacoes: formData.observacoes || null,
        local: formData.local || '',
        is_online: !!formData.is_online,
        extra_participants: {
          formador_ids: formadores.map(f => f.id),
        },
      };

      await updateSolicitacao(Number(id), payload);
      message.success('Solicitação atualizada com sucesso!');
      navigate('/solicitacoes/minhas');
    } catch (err) {
      logger.error('Erro ao atualizar solicitação:', err);
      const apiErr = err as ApiErrorResponse;

      // Tratar erros específicos do backend
      if (apiErr.response?.data?.non_field_errors) {
        message.error(apiErr.response.data.non_field_errors[0]);
      } else if (apiErr.response?.status === 403) {
        message.error('Você não tem permissão para editar esta solicitação.');
      } else {
        message.error('Erro ao atualizar solicitação. Verifique os dados e tente novamente.');
      }
    } finally {
      setSaving(false);
    }
  };

  // Estados de loading e erro
  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto flex justify-center items-center min-h-96">
        <Spin size="large" tip="Carregando solicitação..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Result
          status="error"
          title="Erro ao carregar"
          subTitle={error}
          extra={[
            <Button key="back" onClick={() => navigate('/solicitacoes/minhas')}>
              Voltar para Solicitações
            </Button>,
          ]}
        />
      </div>
    );
  }

  // Verificar se pode editar
  const isPublished = solicitacao?.gcal_status === ('PUBLISHED' as GCalStatus);
  const isRejected = solicitacao?.status === 'reprovado';
  const canEdit = !isPublished && !isRejected;

  if (!canEdit) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/solicitacoes/minhas')}
            className="mb-4"
          >
            Voltar
          </Button>

          <Result
            status="warning"
            icon={isPublished ? <CalendarOutlined /> : <StopOutlined />}
            title={isPublished ? 'Solicitação já publicada' : 'Solicitação reprovada'}
            subTitle={
              isPublished
                ? 'Esta solicitação já foi publicada no Google Calendar e não pode ser editada. Cancele o evento primeiro se precisar fazer alterações.'
                : 'Solicitações reprovadas não podem ser editadas. Crie uma nova solicitação se necessário.'
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/solicitacoes/minhas')}
          className="mb-4"
        >
          Voltar
        </Button>

        <Title level={2} className="mb-2">Editar Solicitação #{id}</Title>
        <Text type="secondary">
          Status: <strong>{solicitacao?.status}</strong>
          {solicitacao?.gcal_status && solicitacao.gcal_status !== ('NOT_SYNCED' as GCalStatus) && (
            <> | GCal: <strong>{solicitacao.gcal_status}</strong></>
          )}
        </Text>

        <Alert
          message="Editando solicitação"
          description="Você está editando uma solicitação existente. Após salvar, as alterações serão registradas no histórico de auditoria."
          type="info"
          showIcon
          className="mt-4 mb-6"
        />

        <Form form={form} layout="vertical" autoComplete="off">
          <Form.Item
            label="Projeto"
            rules={[{ required: true, message: 'Por favor selecione um projeto' }]}
          >
            <ComboBox
              lookupFunction={lookupProjetos as unknown as (query: string) => Promise<Array<{ id: ID; label: string; [key: string]: unknown }>>}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, projeto: value })}
              value={formData.projeto as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um projeto"
            />
          </Form.Item>

          <Form.Item
            label="Tipo de Evento"
            rules={[{ required: true, message: 'Por favor selecione um tipo de evento' }]}
          >
            <ComboBox
              lookupFunction={lookupTiposEvento as unknown as (query: string) => Promise<Array<{ id: ID; label: string; [key: string]: unknown }>>}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, tipoEvento: value })}
              value={formData.tipoEvento as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um tipo de evento"
            />
          </Form.Item>

          <Form.Item
            label="Município"
            rules={[{ required: true, message: 'Por favor selecione um município' }]}
          >
            <ComboBox
              lookupFunction={lookupMunicipios as unknown as (query: string) => Promise<Array<{ id: ID; label: string; [key: string]: unknown }>>}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, municipio: value })}
              value={formData.municipio as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um município"
            />
          </Form.Item>

          <Form.Item
            label="Formadores"
            rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
          >
            <FormadoresPicker
              value={formData.formadores as unknown as Array<{ id: ID; email: string; label: string; name?: string }>}
              onChange={(value: FormadorType[]) => setFormData({ ...formData, formadores: value })}
            />
          </Form.Item>

          <DateTimeRange
            value={rangeValue}
            onChange={handleRangeChange as unknown as (value: { date?: string | null; start?: string | null; end?: string | null }) => void}
          />

          <Form.Item
            label="Tipo"
            name="tipo"
            rules={[{ max: 50, message: 'Máximo 50 caracteres' }]}
          >
            <Input
              placeholder="Ex: evento, reunião"
              value={formData.tipo}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, tipo: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Encontro"
            name="encontro"
            rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}
          >
            <Input
              placeholder="Ex: Encontro 1"
              value={formData.encontro}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, encontro: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Segmento"
            name="segmento"
            rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}
          >
            <Input
              placeholder="Ex: Fundamental I, Fundamental II"
              value={formData.segmento}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, segmento: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Local do Evento"
            name="local"
            rules={[{ max: 300, message: 'Máximo 300 caracteres' }]}
          >
            <Input
              placeholder="Ex: Escola Municipal X, Sala 5 / Secretaria de Educação"
              value={formData.local}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, local: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Observações"
            name="observacoes"
          >
            <TextArea
              rows={4}
              placeholder="Observações adicionais sobre o evento"
              value={formData.observacoes}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setFormData({ ...formData, observacoes: e.target.value })}
            />
          </Form.Item>

          <Form.Item name="is_online" valuePropName="checked">
            <Checkbox
              checked={formData.is_online}
              onChange={(e: CheckboxChangeEvent) => setFormData({ ...formData, is_online: e.target.checked })}
            >
              Evento online (Google Meet)
            </Checkbox>
          </Form.Item>

          <Alert
            message="Modalidade do evento"
            description={
              formData.is_online
                ? 'Link do Google Meet será gerado automaticamente após publicação do evento no calendário.'
                : 'Evento presencial - nenhum link de reunião será gerado.'
            }
            type={formData.is_online ? 'info' : 'warning'}
            showIcon
            className="mb-6"
          />

          <div className="flex gap-2 justify-end">
            <Button onClick={() => navigate('/solicitacoes/minhas')}>
              Cancelar
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSubmit}
              loading={saving}
            >
              Salvar Alterações
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
}
