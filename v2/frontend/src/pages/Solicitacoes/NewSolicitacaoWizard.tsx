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

import { useState, useMemo, useCallback, useEffect, ChangeEvent, JSX, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
// antd - direct imports for tree-shaking (Issue #424)
import Steps from 'antd/es/steps';
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Alert from 'antd/es/alert';
import message from 'antd/es/message';
import Typography from 'antd/es/typography';
import Descriptions from 'antd/es/descriptions';
import Tag from 'antd/es/tag';
import Checkbox from 'antd/es/checkbox';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
// icons - direct imports for tree-shaking (Issue #425)
import FileTextOutlined from '@ant-design/icons/FileTextOutlined';
import TeamOutlined from '@ant-design/icons/TeamOutlined';
import EditOutlined from '@ant-design/icons/EditOutlined';
import CheckOutlined from '@ant-design/icons/CheckOutlined';
import ArrowLeftOutlined from '@ant-design/icons/ArrowLeftOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { createSolicitacao } from '../../api/solicitacoes';
import {
  lookupMunicipiosWithFilters,
  lookupProjetos,
  lookupTiposEvento,
} from '../../api/lookup';
import { getMe } from '../../api/availability';
import { computePermissions } from '../../hooks/usePermissions';
import DateTimeRange from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import FormadoresPicker from '../../components/FormadoresPicker';
import CoordenadoresPicker from '../../components/CoordenadoresPicker';
import logger from '../../utils/logger';
import type { ID, FluxoType } from '../../types';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Step } = Steps;

const RANGE_TIMEZONE = 'America/Fortaleza';

/** ComboBox value type */
interface ComboBoxValue {
  id: ID;
  label: string;
  fluxo?: FluxoType;
}

/** Formador/Coordenador type */
interface ParticipantType {
  id: ID;
  label?: string;
  name?: string;
  email?: string;
}

/** Form data type */
interface FormDataType {
  // Passo 1
  projeto: ComboBoxValue | null;
  tipoEvento: ComboBoxValue | null;
  municipio: ComboBoxValue | null;
  inicio: string | null;
  fim: string | null;
  // Passo 2
  formadores: ParticipantType[];
  coordenadores: ParticipantType[];
  // Passo 3
  tipo: string;
  encontro: string;
  segmento: string;
  observacoes: string;
  local: string;
  // PR19: Modalidade online/presencial
  is_online: boolean;
}

/** Range value type */
interface RangeValueType {
  date: string;
  start: string;
  end: string;
}

/** Step type */
interface StepType {
  title: string;
  icon: ReactNode;
  content: ReactNode;
}

export default function NewSolicitacaoWizard(): JSX.Element {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [currentStep, setCurrentStep] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSuperuser, setIsSuperuser] = useState<boolean>(false);
  const [municipioLookupHasResults, setMunicipioLookupHasResults] = useState<boolean | null>(null);

  // Estado do formulário
  const [formData, setFormData] = useState<FormDataType>({
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
    local: '',
    // PR19: Modalidade online/presencial
    is_online: false,
  });

  useEffect(() => {
    let mounted = true;
    const loadUserRole = async (): Promise<void> => {
      try {
        const me = await getMe();
        if (mounted) {
          // Epic 3.3 cleanup: usa flag derivada (SSOT). Admin escape hatch
          // do wizard — bypassa exigência de projeto/município no Step 2.
          setIsSuperuser(computePermissions(me).isAdmin);
        }
      } catch (error) {
        logger.warn('Falha ao carregar perfil do usuário no wizard:', error);
        if (mounted) {
          setIsSuperuser(false);
        }
      }
    };

    void loadUserRole();
    return () => {
      mounted = false;
    };
  }, []);

  // Handler para DateTimeRange: converte {date, start, end} para ISO UTC (Issue #428)
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

  const handleProjetoChange = useCallback((value: ComboBoxValue | null): void => {
    const projetoChanged = formData.projeto?.id !== value?.id;
    setFormData(prev => ({
      ...prev,
      projeto: value,
      municipio: projetoChanged ? null : prev.municipio,
    }));

    if (projetoChanged) {
      form.setFieldsValue({ municipio: null });
      setMunicipioLookupHasResults(null);
    }
  }, [form, formData.projeto?.id]);

  const lookupMunicipiosElegiveis = useCallback(async (q: string): Promise<Array<{ id: ID; label: string; [key: string]: unknown }>> => {
    const projetoId = formData.projeto?.id;

    // Para usuário comum, exige projeto para aplicar filtro município+projeto.
    if (!isSuperuser && !projetoId) {
      setMunicipioLookupHasResults(false);
      return [];
    }

    const results = await lookupMunicipiosWithFilters({
      q,
      com_compra: isSuperuser ? undefined : true,
      projeto_id: !isSuperuser ? projetoId : undefined,
    });

    if (!q.trim()) {
      setMunicipioLookupHasResults(results.length > 0);
    }

    return results;
  }, [formData.projeto?.id, isSuperuser]);

  // Navegação entre passos
  const next = (): void => {
    form.validateFields().then(values => {
      setFormData({ ...formData, ...values });
      setCurrentStep(currentStep + 1);
    }).catch(err => {
      logger.debug('Validação falhou:', err);
    });
  };

  const prev = (): void => {
    setCurrentStep(currentStep - 1);
  };

  // Submit final
  const handleSubmit = async (): Promise<void> => {
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
        local: formData.local || '',
        // PR19: incluir modalidade no payload
        is_online: !!formData.is_online,
        coordenador_acompanha: coordenadores.length > 0,
        // Backend espera participantes dentro de extra_participants
        extra_participants: {
          formador_ids: formadores.map(f => f.id),
          coord_acompanha_ids: coordenadores.map(c => c.id),
        },
      };

      await createSolicitacao(payload);
      message.success('Solicitação criada com sucesso!');
      navigate('/solicitacoes/minhas');
    } catch (error) {
      logger.error('Erro ao criar solicitação:', error);
      message.error('Erro ao criar solicitação. Verifique os dados e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  // Passos do wizard memoizados (Issue #426)
  const steps: StepType[] = useMemo(() => [
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
              lookupFunction={lookupProjetos as unknown as (query: string) => Promise<Array<{ id: ID; label: string; [key: string]: unknown }>>}
              onChange={handleProjetoChange}
              value={formData.projeto as unknown as { id: ID; label: string; [key: string]: unknown } | null}
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
              lookupFunction={lookupTiposEvento as unknown as (query: string) => Promise<Array<{ id: ID; label: string; [key: string]: unknown }>>}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, tipoEvento: value })}
              value={formData.tipoEvento as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um tipo de evento"
            />
          </Form.Item>

          <Form.Item
            label="Município"
            name="municipio"
            rules={[{ required: true, message: 'Por favor selecione um município' }]}
          >
            <ComboBox
              lookupFunction={lookupMunicipiosElegiveis}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, municipio: value })}
              value={formData.municipio as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder={
                !isSuperuser && !formData.projeto
                  ? 'Selecione um projeto para carregar municípios elegíveis'
                  : 'Busque ou selecione um município'
              }
              disabled={!isSuperuser && !formData.projeto}
              notFoundContent={
                !isSuperuser && formData.projeto
                  ? 'Nenhum município elegível para o projeto selecionado'
                  : 'Nenhum resultado encontrado'
              }
            />
          </Form.Item>

          {!isSuperuser && formData.projeto && municipioLookupHasResults === false && (
            <Alert
              message="Sem municípios elegíveis"
              description="Não há municípios com compra registrada para o projeto selecionado."
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <DateTimeRange
            value={rangeValue}
            onChange={handleRangeChange as unknown as (value: { date?: string | null; start?: string | null; end?: string | null }) => void}
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
            className="mb-4"
          />

          <Form.Item
            label="Formadores"
            name="formadores"
            rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
          >
            <FormadoresPicker
              value={formData.formadores as unknown as Array<{ id: ID; email: string; label: string; name?: string }>}
              onChange={(value: ParticipantType[]) => setFormData({ ...formData, formadores: value })}
            />
          </Form.Item>

          <Form.Item
            label="Coordenadores Acompanhantes"
            name="coordenadores"
          >
            <CoordenadoresPicker
              value={formData.coordenadores as unknown as Array<{ id: ID; email: string; label: string; name?: string }>}
              onChange={(value: ParticipantType[]) => setFormData({ ...formData, coordenadores: value })}
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

          {/* PR19: Modalidade online/presencial */}
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
          />
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
                ? `${dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('DD/MM/YYYY HH:mm')} - ${dayjs(formData.fim).tz(RANGE_TIMEZONE).format('DD/MM/YYYY HH:mm')}`
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
            {formData.local && (
              <Descriptions.Item label="Local">{formData.local}</Descriptions.Item>
            )}
            {formData.observacoes && (
              <Descriptions.Item label="Observações">{formData.observacoes}</Descriptions.Item>
            )}
            <Descriptions.Item label="Modalidade">
              <Tag color={formData.is_online ? 'blue' : 'orange'}>
                {formData.is_online ? 'Online (Google Meet)' : 'Presencial'}
              </Tag>
            </Descriptions.Item>
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
            className="mt-4"
          />
        </>
      ),
    },
  ], [formData, rangeValue, handleRangeChange, handleProjetoChange, lookupMunicipiosElegiveis, isSuperuser, municipioLookupHasResults]);

  return (
    <section className="p-6 max-w-4xl mx-auto" aria-labelledby="nova-solicitacao-title">
      <Card>
        {/* Header semantico com navegacao e titulo */}
        <header>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/solicitacoes/minhas')}
            className="mb-4"
            aria-label="Voltar para minhas solicitacoes"
          >
            Voltar
          </Button>

          <Title level={2} className="mb-2" id="nova-solicitacao-title">Nova Solicitação</Title>
          <Text type="secondary" aria-live="polite">Passo {currentStep + 1} de {steps.length}</Text>
        </header>

        {/* Navegacao do wizard */}
        <nav aria-label="Passos do wizard" className="mt-6 mb-8">
          <Steps current={currentStep}>
            {steps.map((step) => (
              <Step key={step.title} title={step.title} icon={step.icon} />
            ))}
          </Steps>
        </nav>

        {/* Conteudo do passo atual */}
        <Form form={form} layout="vertical" autoComplete="off">
          <section aria-label={`Passo ${currentStep + 1}: ${steps[currentStep].title}`} style={{ minHeight: '400px' }}>
            {steps[currentStep].content}
          </section>
        </Form>

        {/* Footer com botoes de navegacao */}
        <footer className="mt-6 flex gap-2 justify-end" role="navigation" aria-label="Navegacao do wizard">
          {currentStep > 0 && (
            <Button onClick={prev} aria-label="Voltar para passo anterior">
              Anterior
            </Button>
          )}
          {currentStep < steps.length - 1 && (
            <Button type="primary" onClick={next} aria-label="Ir para proximo passo">
              Próximo
            </Button>
          )}
          {currentStep === steps.length - 1 && (
            <Button type="primary" onClick={handleSubmit} loading={loading}>
              Confirmar Solicitação
            </Button>
          )}
        </footer>
      </Card>
    </section>
  );
}
