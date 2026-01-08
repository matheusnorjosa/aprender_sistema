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

import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Form,
  Input,
  Button,
  Card,
  Alert,
  message,
  Typography,
  Spin,
  Checkbox,
  Result,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  CalendarOutlined,
  StopOutlined,
} from '@ant-design/icons';
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

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;

const RANGE_TIMEZONE = 'America/Fortaleza';

export default function EditSolicitacaoPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [solicitacao, setSolicitacao] = useState(null);
  const [error, setError] = useState(null);

  // Estado do formulário
  const [formData, setFormData] = useState({
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
    const fetchSolicitacao = async () => {
      try {
        setLoading(true);
        const data = await getSolicitacao(id);
        setSolicitacao(data);

        // Extrair formadores das participations
        const formadores = (data.participations || [])
          .filter(p => p.role === 'FORMADOR' && p.usuario)
          .map(p => ({
            id: p.usuario.id,
            label: p.usuario.first_name && p.usuario.last_name
              ? `${p.usuario.first_name} ${p.usuario.last_name}`.trim()
              : p.usuario.username,
            email: p.usuario.email,
          }));

        // Preencher o formData com os dados existentes
        setFormData({
          projeto: data.projeto ? { id: data.projeto, label: data.projeto_nome } : null,
          tipoEvento: data.tipo_evento ? { id: data.tipo_evento, label: data.tipo_evento_nome } : null,
          municipio: data.municipio ? { id: data.municipio, label: data.municipio_nome } : null,
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
        if (err.response?.status === 404) {
          setError('Solicitação não encontrada.');
        } else if (err.response?.status === 403) {
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

  // Handler para DateTimeRange
  const handleRangeChange = (range) => {
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
  };

  // Derivar rangeValue para o componente DateTimeRange
  const rangeValue = formData.inicio && formData.fim
    ? {
        date: dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('YYYY-MM-DD'),
        start: dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('HH:mm'),
        end: dayjs(formData.fim).tz(RANGE_TIMEZONE).format('HH:mm'),
      }
    : { date: '', start: '', end: '' };

  // Submit
  const handleSubmit = async () => {
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

      await updateSolicitacao(id, payload);
      message.success('Solicitação atualizada com sucesso!');
      navigate('/solicitacoes/minhas');
    } catch (err) {
      logger.error('Erro ao atualizar solicitação:', err);

      // Tratar erros específicos do backend
      if (err.response?.data?.non_field_errors) {
        message.error(err.response.data.non_field_errors[0]);
      } else if (err.response?.status === 403) {
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
  const isPublished = solicitacao?.gcal_status === 'PUBLISHED';
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
          {solicitacao?.gcal_status && solicitacao.gcal_status !== 'NONE' && (
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

        <Form form={form} layout="vertical">
          <Form.Item
            label="Projeto"
            rules={[{ required: true, message: 'Por favor selecione um projeto' }]}
          >
            <ComboBox
              lookupFunction={lookupProjetos}
              onChange={(value) => setFormData({ ...formData, projeto: value })}
              value={formData.projeto}
              placeholder="Busque ou selecione um projeto"
            />
          </Form.Item>

          <Form.Item
            label="Tipo de Evento"
            rules={[{ required: true, message: 'Por favor selecione um tipo de evento' }]}
          >
            <ComboBox
              lookupFunction={lookupTiposEvento}
              onChange={(value) => setFormData({ ...formData, tipoEvento: value })}
              value={formData.tipoEvento}
              placeholder="Busque ou selecione um tipo de evento"
            />
          </Form.Item>

          <Form.Item
            label="Município"
            rules={[{ required: true, message: 'Por favor selecione um município' }]}
          >
            <ComboBox
              lookupFunction={lookupMunicipios}
              onChange={(value) => setFormData({ ...formData, municipio: value })}
              value={formData.municipio}
              placeholder="Busque ou selecione um município"
            />
          </Form.Item>

          <Form.Item
            label="Formadores"
            rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
          >
            <FormadoresPicker
              value={formData.formadores}
              onChange={(value) => setFormData({ ...formData, formadores: value })}
            />
          </Form.Item>

          <DateTimeRange
            labelStart="Data/Hora Início"
            labelEnd="Data/Hora Fim"
            required
            value={rangeValue}
            onChange={handleRangeChange}
          />

          <Form.Item
            label="Tipo"
            name="tipo"
            rules={[{ max: 50, message: 'Máximo 50 caracteres' }]}
          >
            <Input
              placeholder="Ex: evento, reunião"
              value={formData.tipo}
              onChange={(e) => setFormData({ ...formData, tipo: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, encontro: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, segmento: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, local: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
            />
          </Form.Item>

          <Form.Item name="is_online" valuePropName="checked">
            <Checkbox
              checked={formData.is_online}
              onChange={(e) => setFormData({ ...formData, is_online: e.target.checked })}
            >
              Evento online (Google Meet)
            </Checkbox>
          </Form.Item>

          <Alert
            message="Modalidade do evento"
            description={
              formData.is_online
                ? 'Link do Google Meet será gerado automaticamente após publicação do evento no calendário.'
                : 'Evento presencial — nenhum link de reunião será gerado.'
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
