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
  Descriptions,
  Tag,
} from 'antd';
import {
  FileTextOutlined,
  TeamOutlined,
  EditOutlined,
  CheckOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { createSolicitacao } from '../../api/solicitacoes';
import {
  lookupMunicipios,
  lookupProjetos,
  lookupTiposEvento,
} from '../../api/lookup';
import DateTimeRange from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import FormadoresPicker from '../../components/FormadoresPicker';
import CoordenadoresPicker from '../../components/CoordenadoresPicker';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Step } = Steps;


export default function NewSolicitacaoWizard() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);

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
    coordenadores: [],
    // Passo 3
    tipo: '',
    encontro: '',
    segmento: '',
    observacoes: '',
  });

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
      // Garantir que formadores é um array
      const formadores = Array.isArray(formData.formadores) ? formData.formadores : [];

      if (formadores.length === 0) {
        message.error('Por favor, selecione pelo menos um formador');
        setLoading(false);
        return;
      }

      // Validar dados completos
      const coordenadores = Array.isArray(formData.coordenadores) ? formData.coordenadores : [];

      // Validações específicas
      if (!formData.inicio || !formData.fim) {
        message.error('Por favor, selecione data/hora de início e fim');
        setLoading(false);
        return;
      }

      if (!formData.municipio) {
        message.error('Por favor, selecione um município');
        setLoading(false);
        return;
      }

      if (!formData.projeto) {
        message.error('Por favor, selecione um projeto');
        setLoading(false);
        return;
      }

      if (!formData.tipoEvento) {
        message.error('Por favor, selecione um tipo de evento');
        setLoading(false);
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
        coordenador_acompanha: coordenadores.length > 0,
        // Backend espera participantes dentro de extra_participants
        extra_participants: {
          formador_ids: formadores.map(f => f.id),
          coord_acompanha_ids: coordenadores.map(c => c.id),
        },
      };

      console.log('=== DEBUG: Payload sendo enviado ===');
      console.log('FormData completo:', formData);
      console.log('Payload preparado:', payload);
      console.log('Tipos dos campos:');
      console.log('- municipio:', typeof payload.municipio, payload.municipio);
      console.log('- projeto:', typeof payload.projeto, payload.projeto);
      console.log('- tipo_evento:', typeof payload.tipo_evento, payload.tipo_evento);
      console.log('- inicio:', typeof payload.inicio, payload.inicio);
      console.log('- fim:', typeof payload.fim, payload.fim);
      console.log('- coordenador_acompanha:', typeof payload.coordenador_acompanha, payload.coordenador_acompanha);
      console.log('- extra_participants:', payload.extra_participants);

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
            message="Selecione os Participantes"
            description="Selecione os formadores que participarão do evento e, opcionalmente, os coordenadores acompanhantes."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="Formadores"
            name="formadores"
            rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
          >
            <FormadoresPicker
              value={formData.formadores}
              onChange={(value) => setFormData({ ...formData, formadores: value })}
            />
          </Form.Item>

          <Form.Item
            label="Coordenadores Acompanhantes"
            name="coordenadores"
          >
            <CoordenadoresPicker
              value={formData.coordenadores}
              onChange={(value) => setFormData({ ...formData, coordenadores: value })}
            />
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
                ? formData.formadores.map(f => f.label || f.name).join(', ')
                : 'Nenhum'}
            </Descriptions.Item>
            <Descriptions.Item label="Coordenadores Acompanhantes">
              {formData.coordenadores.length > 0
                ? formData.coordenadores.map(c => c.label || c.name).join(', ')
                : 'Nenhum'}
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
