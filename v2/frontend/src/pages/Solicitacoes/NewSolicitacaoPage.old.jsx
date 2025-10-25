/**
 * PR16: NewSolicitacaoPage - Nova Solicitação com Autocomplete e Validação
 *
 * Fluxo:
 * 1. Preencher formulário com autocomplete (município, projeto, tipo)
 * 2. Selecionar participantes (formadores, coord_acompanha)
 * 3. Validar dados (POST /api/solicitacoes/validate/)
 * 4. Checar disponibilidade (opcional)
 * 5. Submeter com IDs canônicos
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Form,
  Input,
  Button,
  Card,
  Space,
  Alert,
  message,
  Typography,
  Spin,
  Select,
  List,
  Tag,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  ArrowLeftOutlined,
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

/**
 * Mapeia código de conflito para ícone (ISO 9241-110: auto-descritividade)
 */
function getConflictIcon(code) {
  const icons = {
    X: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,      // Sobreposição - vermelho
    T: <StopOutlined style={{ color: '#ff4d4f' }} />,             // Bloqueio Total - vermelho
    P: <MinusCircleOutlined style={{ color: '#fa8c16' }} />,      // Bloqueio Parcial - laranja
    D: <CarOutlined style={{ color: '#fa8c16' }} />,              // Deslocamento - laranja
    M: <ClockCircleOutlined style={{ color: '#faad14' }} />,      // Capacidade - dourado
  };
  return icons[code] || <WarningOutlined style={{ color: '#d9d9d9' }} />;
}

/**
 * Mapeia código de conflito para cor da tag
 */
function getConflictColor(code) {
  const colors = {
    X: 'red',      // Sobreposição - bloqueante
    T: 'red',      // Bloqueio Total - bloqueante
    P: 'orange',   // Bloqueio Parcial - atenção
    D: 'orange',   // Deslocamento - atenção
    M: 'gold',     // Capacidade - aviso
  };
  return colors[code] || 'default';
}

export default function NewSolicitacaoPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [checking, setChecking] = useState(false);

  // Dados do formulário
  const [municipio, setMunicipio] = useState(null);
  const [projeto, setProjeto] = useState(null);
  const [tipoEvento, setTipoEvento] = useState(null);
  const [dateTime, setDateTime] = useState({ date: null, start: null, end: null });
  const [participants, setParticipants] = useState({ formadores: [], coordAcompanha: [] });
  const [tipo, setTipo] = useState('PRESENCIAL');
  const [observacoes, setObservacoes] = useState('');

  // Resultados de validação
  const [validationResult, setValidationResult] = useState(null);
  const [availabilityResult, setAvailabilityResult] = useState(null);

  // Carregar dados do usuário
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await getMe();
        setMe(userData);
      } catch (error) {
        message.error('Erro ao carregar usuário: ' + error.message);
      }
    };
    loadUser();
  }, []);

  /**
   * Validar formulário com backend
   */
  const handleValidate = async () => {
    try {
      setValidating(true);
      setValidationResult(null);
      setAvailabilityResult(null);

      // Verificar campos obrigatórios
      if (!municipio || !projeto || !tipoEvento) {
        message.warning('Preencha município, projeto e tipo de evento');
        return;
      }

      if (!dateTime.date || !dateTime.start || !dateTime.end) {
        message.warning('Preencha data, horário de início e término');
        return;
      }

      if (participants.formadores.length === 0) {
        message.warning('Adicione pelo menos um formador');
        return;
      }

      // Montar payload de validação
      const payloadValidate = {
        municipio: municipio.id ? { id: municipio.id } : municipio.label,
        projeto: projeto.id ? { id: projeto.id } : projeto.label,
        tipo_evento: tipoEvento.id ? { id: tipoEvento.id } : tipoEvento.label,
        date: dateTime.date,
        start: dateTime.start,
        end: dateTime.end,
        participants: {
          coordenador: me?.email || '',
          formadores: participants.formadores.map(f => f.email),
          coord_acompanha: participants.coordAcompanha.map(c => c.email),
        },
      };

      const result = await validateSolic(payloadValidate);
      setValidationResult(result);

      if (result.ok) {
        message.success('Dados validados com sucesso!');
      } else {
        message.error('Erros de validação encontrados');
      }
    } catch (error) {
      message.error('Erro ao validar: ' + error.message);
    } finally {
      setValidating(false);
    }
  };

  /**
   * Checar disponibilidade dos formadores
   */
  const handleCheckAvailability = async () => {
    if (!validationResult || !validationResult.ok) {
      message.warning('Valide os dados primeiro');
      return;
    }

    try {
      setChecking(true);
      setAvailabilityResult(null);

      const results = [];
      const formadorIds = validationResult.canonical.usuarios.formadores_ids || [];

      for (const formadorId of formadorIds) {
        const result = await checkAvailability({
          usuario_id: formadorId,
          inicio: validationResult.canonical.inicio,
          fim: validationResult.canonical.fim,
          municipio_id: validationResult.canonical.municipio_id,
        });

        results.push({
          formadorId,
          disponivel: result.ok,
          conflitos: result.conflicts || [],
        });
      }

      setAvailabilityResult({ results });

      const allAvailable = results.every(r => r.disponivel);
      if (allAvailable) {
        message.success('Todos os formadores estão disponíveis!');
      } else {
        message.warning('Alguns formadores possuem conflitos');
      }
    } catch (error) {
      message.error('Erro ao checar disponibilidade: ' + error.message);
    } finally {
      setChecking(false);
    }
  };

  /**
   * Submeter solicitação
   */
  const handleSubmit = async () => {
    if (!validationResult || !validationResult.ok) {
      message.warning('Valide os dados primeiro');
      return;
    }

    try {
      setLoading(true);

      const canonical = validationResult.canonical;

      // Montar payload para criação
      const payloadCreate = {
        municipio: canonical.municipio_id,
        projeto: canonical.projeto_id,
        tipo_evento: canonical.tipo_evento_id,
        tipo,
        inicio: canonical.inicio,
        fim: canonical.fim,
        observacoes,
        extra_participants: {
          formador_ids: canonical.usuarios.formadores_ids || [],
          formador_emails: canonical.usuarios.formadores_not_found || [],
          coord_acompanha_ids: canonical.usuarios.coord_acompanha_ids || [],
          coord_acompanha_emails: canonical.usuarios.coord_acompanha_not_found || [],
        },
      };

      await createSolicitacao(payloadCreate);
      message.success('Solicitação criada com sucesso!');
      navigate('/solicitacoes/minhas');
    } catch (error) {
      message.error('Erro ao criar solicitação: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <Card>
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/solicitacoes/minhas')}
            >
              Voltar
            </Button>
            <Title level={2} style={{ margin: 0 }}>
              Nova Solicitação
            </Title>
          </Space>
        </Card>

        {/* Informações Básicas */}
        <Card title="Informações Básicas" size="small">
          <Form form={form} layout="vertical">
            <Form.Item label="Município" required>
              <ComboBox
                value={municipio}
                onChange={setMunicipio}
                lookupFunction={lookupMunicipios}
                placeholder="Digite para buscar município..."
              />
            </Form.Item>

            <Form.Item label="Projeto" required>
              <ComboBox
                value={projeto}
                onChange={setProjeto}
                lookupFunction={lookupProjetos}
                placeholder="Digite para buscar projeto..."
              />
            </Form.Item>

            <Form.Item label="Tipo de Evento" required>
              <ComboBox
                value={tipoEvento}
                onChange={setTipoEvento}
                lookupFunction={lookupTiposEvento}
                placeholder="Digite para buscar tipo de evento..."
              />
            </Form.Item>

            <Form.Item label="Tipo de Realização">
              <Select value={tipo} onChange={setTipo}>
                <Select.Option value="PRESENCIAL">Presencial</Select.Option>
                <Select.Option value="REMOTO">Remoto</Select.Option>
              </Select>
            </Form.Item>

            <Form.Item label="Observações">
              <TextArea
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                rows={3}
                placeholder="Informações adicionais..."
              />
            </Form.Item>
          </Form>
        </Card>

        {/* Data e Horário */}
        <Card title="Data e Horário" size="small">
          <DateTimeRange value={dateTime} onChange={setDateTime} />
        </Card>

        {/* Participantes */}
        <PeoplePicker value={participants} onChange={setParticipants} />

        {/* Validação */}
        <Card title="Validação" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type="primary"
              onClick={handleValidate}
              loading={validating}
              block
            >
              Validar Dados
            </Button>

            {validationResult && !validationResult.ok && (
              <Alert
                type="error"
                message="Erros de validação"
                description={
                  <List
                    size="small"
                    dataSource={validationResult.errors}
                    renderItem={item => <List.Item>{item}</List.Item>}
                  />
                }
              />
            )}

            {validationResult && validationResult.ok && (
              <Alert
                type="success"
                message="Dados validados com sucesso!"
                description={
                  <div>
                    <Text>Município ID: {validationResult.canonical.municipio_id}</Text><br/>
                    <Text>Projeto ID: {validationResult.canonical.projeto_id}</Text><br/>
                    <Text>Tipo Evento ID: {validationResult.canonical.tipo_evento_id}</Text><br/>
                    <Text>Formadores: {validationResult.canonical.usuarios.formadores_ids.length}</Text>
                  </div>
                }
              />
            )}
          </Space>
        </Card>

        {/* Disponibilidade */}
        {validationResult && validationResult.ok && (
          <Card title="Disponibilidade" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                onClick={handleCheckAvailability}
                loading={checking}
                icon={<CheckCircleOutlined />}
                block
              >
                Checar Disponibilidade
              </Button>

              {availabilityResult && (
                <List
                  size="small"
                  dataSource={availabilityResult.results}
                  renderItem={item => (
                    <List.Item>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          {item.disponivel ? (
                            <Tag color="green">Disponível</Tag>
                          ) : (
                            <Tag color="red">Conflito</Tag>
                          )}
                          <Text>Formador ID: {item.formadorId}</Text>
                        </Space>
                        {!item.disponivel && item.conflitos.length > 0 && (
                          <div style={{ paddingLeft: 16 }}>
                            <Text type="secondary" style={{ fontSize: '12px' }}>Conflitos detectados:</Text>
                            <Space direction="vertical" size="small" style={{ marginTop: 8, width: '100%' }}>
                              {item.conflitos.map((conflict, idx) => (
                                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                                  {getConflictIcon(conflict.code)}
                                  <div style={{ flex: 1 }}>
                                    <Tag color={getConflictColor(conflict.code)} style={{ marginBottom: 4 }}>
                                      {conflict.code}
                                    </Tag>
                                    <Text strong style={{ fontSize: '13px' }}>{conflict.title}</Text>
                                    <br />
                                    <Text type="secondary" style={{ fontSize: '12px' }}>{conflict.detail}</Text>
                                  </div>
                                </div>
                              ))}
                            </Space>
                          </div>
                        )}
                      </Space>
                    </List.Item>
                  )}
                />
              )}
            </Space>
          </Card>
        )}

        {/* Submeter */}
        <Card>
          <Button
            type="primary"
            size="large"
            onClick={handleSubmit}
            loading={loading}
            disabled={!validationResult || !validationResult.ok}
            block
          >
            Criar Solicitação
          </Button>
        </Card>
      </Space>
    </div>
  );
}
