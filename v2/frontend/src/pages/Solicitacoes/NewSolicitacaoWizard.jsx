/**
 * Nova Solicitação - Wizard Multi-Step
 *
 * Design: paginanovasolicitacao/screen.png
 *
 * Passos:
 * 1. Informações Básicas (projeto, tipo, município, data/hora)
 * 2. Participantes (formadores com badges de disponibilidade)
 * 3. Detalhes Adicionais (tipo, encontro, segmento, observações)
 * 4. Revisão e Confirmação
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Steps,
  Form,
  Input,
  Button,
  Card,
  Alert,
  message,
  Typography,
  Row,
  Col,
  Descriptions,
  Tag,
  Space,
  Checkbox,
  Spin,
  List,
} from 'antd';
import {
  FileTextOutlined,
  TeamOutlined,
  EditOutlined,
  CheckOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  StopOutlined,
  MinusCircleOutlined,
  CarOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { createSolicitacao, checkAvailability } from '../../api/solicitacoes';
import { getMe } from '../../api/availability';
import {
  lookupMunicipios,
  lookupProjetos,
  lookupTiposEvento,
  validateSolic,
} from '../../api/lookup';
import DateTimeRange from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import PeoplePicker from '../../components/PeoplePicker';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Step } = Steps;

/**
 * Mapeia código de conflito para ícone
 */
function getConflictIcon(code) {
  const icons = {
    X: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
    T: <StopOutlined style={{ color: '#ff4d4f' }} />,
    P: <MinusCircleOutlined style={{ color: '#fa8c16' }} />,
    D: <CarOutlined style={{ color: '#fa8c16' }} />,
    M: <ClockCircleOutlined style={{ color: '#faad14' }} />,
  };
  return icons[code] || <WarningOutlined style={{ color: '#d9d9d9' }} />;
}

/**
 * Badge de disponibilidade para formador
 */
function AvailabilityBadge({ formador, inicio, fim, municipio }) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (!formador || !inicio || !fim || !municipio) {
      setStatus(null);
      return;
    }

    const check = async () => {
      setLoading(true);
      try {
        const result = await checkAvailability(formador.id, inicio, fim, municipio.id);
        setStatus(result);
      } catch (error) {
        console.error('Erro ao checar disponibilidade:', error);
        setStatus({ available: false, conflicts: [{ code: 'X', title: 'Erro' }] });
      } finally {
        setLoading(false);
      }
    };

    check();
  }, [formador?.id, inicio, fim, municipio?.id]);

  if (loading) {
    return <Spin size="small" />;
  }

  if (!status) {
    return <Tag>Aguardando dados</Tag>;
  }

  if (status.available) {
    return <Tag color="success" icon={<CheckCircleOutlined />}>Disponível</Tag>;
  }

  const firstConflict = status.conflicts[0];
  return (
    <Tag color="error" icon={getConflictIcon(firstConflict.code)}>
      {firstConflict.title}
    </Tag>
  );
}

export default function NewSolicitacaoWizard() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [me, setMe] = useState(null);

  // Estado do formulário
  const [formData, setFormData] = useState({
    // Passo 1
    projeto: null,
    tipoEvento: null,
    municipio: null,
    inicio: null,
    fim: null,
    // Passo 2
    formadores: [],
    coordenadorAcompanha: false,
    // Passo 3
    tipo: '',
    encontro: '',
    segmento: '',
    observacoes: '',
  });

  // Carregar dados do usuário
  useEffect(() => {
    const loadMe = async () => {
      try {
        const userData = await getMe();
        setMe(userData);
      } catch (error) {
        console.error('Erro ao carregar usuário:', error);
        message.error('Erro ao carregar dados do usuário');
      }
    };
    loadMe();
  }, []);

  // Navegação entre passos
  const next = () => {
    form.validateFields().then(values => {
      setFormData({ ...formData, ...values });
      setCurrentStep(currentStep + 1);
    }).catch(err => {
      console.log('Validação falhou:', err);
    });
  };

  const prev = () => {
    setCurrentStep(currentStep - 1);
  };

  // Submit final
  const handleSubmit = async () => {
    setLoading(true);
    try {
      // Validar dados completos
      const payload = {
        municipio_id: formData.municipio.id,
        projeto_id: formData.projeto.id,
        tipo_evento_id: formData.tipoEvento.id,
        inicio: dayjs(formData.inicio).utc().format(),
        fim: dayjs(formData.fim).utc().format(),
        tipo: formData.tipo,
        encontro: formData.encontro,
        segmento: formData.segmento,
        observacoes: formData.observacoes,
        coordenador_acompanha: formData.coordenadorAcompanha,
        formador_ids: formData.formadores.map(f => f.id),
      };

      await createSolicitacao(payload);
      message.success('Solicitação criada com sucesso!');
      navigate('/solicitacoes');
    } catch (error) {
      console.error('Erro ao criar solicitação:', error);
      message.error('Erro ao criar solicitação. Verifique os dados e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  // Passos do wizard
  const steps = [
    {
      title: 'Informações Básicas',
      icon: <FileTextOutlined />,
      content: (
        <>
          <Form.Item
            label="Projeto"
            name="projeto"
            rules={[{ required: true, message: 'Por favor selecione um projeto' }]}
          >
            <ComboBox
              lookupFunction={lookupProjetos}
              onChange={(value) => setFormData({ ...formData, projeto: value })}
              value={formData.projeto}
              placeholder="Busque ou selecione um projeto"
            />
          </Form.Item>

          {formData.projeto && (
            <Alert
              message={`Fluxo: ${formData.projeto.fluxo === 'SUPER' ? 'Superintendência' : 'Não-Superintendência'}`}
              description={
                formData.projeto.fluxo === 'SUPER'
                  ? 'Esta solicitação requer aprovação manual da Superintendência.'
                  : 'Esta solicitação não requer aprovação manual da Superintendência.'
              }
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Form.Item
            label="Tipo de Evento"
            name="tipoEvento"
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
            name="municipio"
            rules={[{ required: true, message: 'Por favor selecione um município' }]}
          >
            <ComboBox
              lookupFunction={lookupMunicipios}
              onChange={(value) => setFormData({ ...formData, municipio: value })}
              value={formData.municipio}
              placeholder="Busque ou selecione um município"
            />
          </Form.Item>

          <DateTimeRange
            labelStart="Data/Hora Início"
            labelEnd="Data/Hora Fim"
            nameStart="inicio"
            nameEnd="fim"
            required
            onChange={(inicio, fim) => setFormData({ ...formData, inicio, fim })}
          />
        </>
      ),
    },
    {
      title: 'Participantes',
      icon: <TeamOutlined />,
      content: (
        <>
          <Alert
            message="Selecione os Formadores"
            description="Os badges de disponibilidade são atualizados em tempo real conforme você seleciona data/hora e município."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="Formadores"
            name="formadores"
            rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
          >
            <PeoplePicker
              multiple
              value={formData.formadores}
              onChange={(value) => setFormData({ ...formData, formadores: value })}
              renderTag={(formador) => (
                <Space>
                  {formador.name}
                  <AvailabilityBadge
                    formador={formador}
                    inicio={formData.inicio}
                    fim={formData.fim}
                    municipio={formData.municipio}
                  />
                </Space>
              )}
            />
          </Form.Item>

          <Form.Item name="coordenadorAcompanha" valuePropName="checked">
            <Checkbox
              checked={formData.coordenadorAcompanha}
              onChange={(e) => setFormData({ ...formData, coordenadorAcompanha: e.target.checked })}
            >
              Coordenador acompanhará o evento
            </Checkbox>
          </Form.Item>

          {formData.projeto && (
            <Alert
              message={formData.projeto.fluxo === 'SUPER' ? 'Aprovação Manual Requerida' : 'Aprovação Automática'}
              description={
                formData.projeto.fluxo === 'SUPER'
                  ? 'Esta solicitação será criada com status "Pendente" e aguardará aprovação manual da Superintendência.'
                  : 'Esta solicitação será aprovada automaticamente ao ser criada e irá direto para a Pré-agenda.'
              }
              type={formData.projeto.fluxo === 'SUPER' ? 'warning' : 'success'}
              showIcon
            />
          )}
        </>
      ),
    },
    {
      title: 'Detalhes',
      icon: <EditOutlined />,
      content: (
        <>
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
        </>
      ),
    },
    {
      title: 'Confirmação',
      icon: <CheckOutlined />,
      content: (
        <>
          <Title level={4}>Revise sua solicitação</Title>

          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Projeto">
              {formData.projeto?.label}
              <Tag color={formData.projeto?.fluxo === 'SUPER' ? 'blue' : 'green'} style={{ marginLeft: 8 }}>
                {formData.projeto?.fluxo === 'SUPER' ? 'SUPER' : 'NAO_SUPER'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Tipo de Evento">
              {formData.tipoEvento?.label}
            </Descriptions.Item>
            <Descriptions.Item label="Município">
              {formData.municipio?.label}
            </Descriptions.Item>
            <Descriptions.Item label="Período">
              {formData.inicio && formData.fim
                ? `${dayjs(formData.inicio).format('DD/MM/YYYY HH:mm')} - ${dayjs(formData.fim).format('DD/MM/YYYY HH:mm')}`
                : 'Não informado'}
            </Descriptions.Item>
            <Descriptions.Item label="Formadores">
              {formData.formadores.length > 0
                ? formData.formadores.map(f => f.name).join(', ')
                : 'Nenhum'}
            </Descriptions.Item>
            <Descriptions.Item label="Coordenador Acompanha">
              {formData.coordenadorAcompanha ? 'Sim' : 'Não'}
            </Descriptions.Item>
            {formData.tipo && (
              <Descriptions.Item label="Tipo">{formData.tipo}</Descriptions.Item>
            )}
            {formData.encontro && (
              <Descriptions.Item label="Encontro">{formData.encontro}</Descriptions.Item>
            )}
            {formData.segmento && (
              <Descriptions.Item label="Segmento">{formData.segmento}</Descriptions.Item>
            )}
            {formData.observacoes && (
              <Descriptions.Item label="Observações">{formData.observacoes}</Descriptions.Item>
            )}
          </Descriptions>

          <Alert
            message={
              formData.projeto?.fluxo === 'SUPER'
                ? 'Status Inicial: Pendente'
                : 'Status Inicial: Aprovado'
            }
            description={
              formData.projeto?.fluxo === 'SUPER'
                ? 'Sua solicitação será criada com status "Pendente" e aguardará aprovação da Superintendência.'
                : 'Sua solicitação será aprovada automaticamente ao ser criada e irá direto para a Pré-agenda.'
            }
            type={formData.projeto?.fluxo === 'SUPER' ? 'warning' : 'success'}
            showIcon
            style={{ marginTop: 16 }}
          />
        </>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <Card>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/solicitacoes')}
          style={{ marginBottom: 16 }}
        >
          Voltar
        </Button>

        <Title level={2} style={{ marginBottom: 8 }}>Nova Solicitação</Title>
        <Text type="secondary">Passo {currentStep + 1} de {steps.length}</Text>

        <Steps current={currentStep} style={{ marginTop: 24, marginBottom: 32 }}>
          {steps.map((step, index) => (
            <Step key={index} title={step.title} icon={step.icon} />
          ))}
        </Steps>

        <Form form={form} layout="vertical">
          <div style={{ minHeight: '400px' }}>
            {steps[currentStep].content}
          </div>
        </Form>

        <div style={{ marginTop: 24, display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          {currentStep > 0 && (
            <Button onClick={prev}>
              Anterior
            </Button>
          )}
          {currentStep < steps.length - 1 && (
            <Button type="primary" onClick={next}>
              Próximo
            </Button>
          )}
          {currentStep === steps.length - 1 && (
            <Button type="primary" onClick={handleSubmit} loading={loading}>
              Confirmar Solicitação
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
