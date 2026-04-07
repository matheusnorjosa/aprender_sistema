/**
 * Admin DAT - Municípios
 *
 * CRUD de municípios com indicadores (UF, ativo).
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useEffect, useRef, useState } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Select, Modal, Form, Checkbox, AutoComplete } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import {
  listMunicipios,
  createMunicipio,
  updateMunicipio,
  deleteMunicipio,
  autocompleteMunicipiosAdmin,
} from '../../api/adminDAT';
import type { MunicipioAutocompleteItem } from '../../api/adminDAT';
import { importMunicipios } from '../../api/ops';
import ImportUploader from '../../components/ImportUploader';
import type { ValidationResult, ApplyResult } from '../../components/ImportUploader';
import { UF_NORDESTE_OPTIONS } from '../../constants';
import type { ID } from '../../types';

const { Title } = Typography;
const { Search } = Input;

/**
 * Municipio record interface
 */
interface MunicipioRecord {
  id: ID;
  nome: string;
  uf: string;
  ibge_code: string | null;
  ativo: boolean;
}

/**
 * Municipio form values interface
 */
interface MunicipioFormValues {
  nome: string;
  uf: string;
  ibge_code: string;
  ativo: boolean;
}

function normalizeMunicipioName(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function toValidationResult(report: Record<string, unknown>): ValidationResult {
  const stats = (report.stats as Record<string, number | undefined>) || {};
  return {
    stats: {
      created: stats.created || 0,
      updated: stats.updated || 0,
      unchanged: stats.unchanged || 0,
    },
    errors: [],
    pendencias: (report.pendencias as Record<string, unknown>) || {},
  };
}

function toApplyResult(report: Record<string, unknown>): ApplyResult {
  const stats = (report.stats as Record<string, number | undefined>) || {};
  return {
    stats: {
      created: stats.created || 0,
      updated: stats.updated || 0,
      unchanged: stats.unchanged || 0,
    },
  };
}

export default function MunicipiosPage(): JSX.Element {
  const [municipios, setMunicipios] = useState<MunicipioRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [ufFilter, setUfFilter] = useState<string | undefined>(undefined);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMunicipio, setEditingMunicipio] = useState<MunicipioRecord | null>(null);
  const [lookupOptions, setLookupOptions] = useState<MunicipioAutocompleteItem[]>([]);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [ibgeLocked, setIbgeLocked] = useState(false);

  const [form] = Form.useForm<MunicipioFormValues>();
  const watchedNome = Form.useWatch('nome', form);
  const watchedUf = Form.useWatch('uf', form);
  const lookupRequestRef = useRef(0);
  const selectingSuggestionRef = useRef(false);

  const fetchMunicipios = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listMunicipios({
        search: searchText,
        uf: ufFilter,
        ordering: 'nome',
      });
      setMunicipios(data.results as MunicipioRecord[]);
    } catch (error) {
      message.error(`Erro ao carregar municípios: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMunicipios();
  }, [searchText, ufFilter]);

  useEffect(() => {
    if (!modalVisible) {
      setLookupOptions([]);
      setLookupLoading(false);
      return;
    }

    const nome = (watchedNome || '').trim();
    const uf = (watchedUf || '').trim().toUpperCase();

    if (nome.length < 2 || uf.length !== 2) {
      setLookupOptions([]);
      setLookupLoading(false);
      return;
    }

    const requestId = lookupRequestRef.current + 1;
    lookupRequestRef.current = requestId;

    const timerId = window.setTimeout(async () => {
      setLookupLoading(true);
      try {
        const results = await autocompleteMunicipiosAdmin({ q: nome, uf, limit: 20 });
        if (lookupRequestRef.current === requestId) {
          setLookupOptions(results);
        }
      } catch {
        if (lookupRequestRef.current === requestId) {
          setLookupOptions([]);
        }
      } finally {
        if (lookupRequestRef.current === requestId) {
          setLookupLoading(false);
        }
      }
    }, 250);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [modalVisible, watchedNome, watchedUf]);

  useEffect(() => {
    if (!modalVisible) {
      return;
    }

    const nome = String(watchedNome || '').trim();
    const uf = String(watchedUf || '').trim().toUpperCase();

    if (nome.length < 2 || uf.length !== 2 || lookupLoading) {
      return;
    }

    const normalizedNome = normalizeMunicipioName(nome);
    const exactMatches = lookupOptions.filter((item) => (
      item.uf.toUpperCase() === uf
      && normalizeMunicipioName(item.nome) === normalizedNome
    ));

    if (exactMatches.length !== 1) {
      return;
    }

    const match = exactMatches[0];
    if (!(match.ibge_code && match.confidence === 'high')) {
      return;
    }

    const currentIbge = String(form.getFieldValue('ibge_code') || '').trim();
    if (currentIbge !== match.ibge_code) {
      form.setFieldValue('ibge_code', match.ibge_code);
    }
    if (!ibgeLocked) {
      setIbgeLocked(true);
    }
  }, [modalVisible, watchedNome, watchedUf, lookupOptions, lookupLoading, form, ibgeLocked]);

  const handleCreate = (): void => {
    setEditingMunicipio(null);
    setLookupOptions([]);
    setIbgeLocked(false);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (municipio: MunicipioRecord): void => {
    setEditingMunicipio(municipio);
    setLookupOptions([]);
    setIbgeLocked(false);
    form.setFieldsValue({
      nome: municipio.nome,
      uf: municipio.uf,
      ibge_code: municipio.ibge_code || '',
      ativo: municipio.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: MunicipioFormValues): Promise<void> => {
    try {
      if (editingMunicipio) {
        await updateMunicipio(editingMunicipio.id, values);
        message.success('Município atualizado com sucesso');
      } else {
        await createMunicipio(values);
        message.success('Município criado com sucesso');
      }
      setModalVisible(false);
      setLookupOptions([]);
      setIbgeLocked(false);
      form.resetFields();
      fetchMunicipios();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleMunicipioSearch = (value: string): void => {
    if (selectingSuggestionRef.current) {
      selectingSuggestionRef.current = false;
      return;
    }

    if (!value) {
      setLookupOptions([]);
    }

    if (ibgeLocked) {
      setIbgeLocked(false);
      form.setFieldValue('ibge_code', '');
    }
  };

  const handleMunicipioSelect = (value: string): void => {
    const currentUf = String(form.getFieldValue('uf') || '').toUpperCase();
    const selectedOption =
      lookupOptions.find((item) => item.nome === value && item.uf === currentUf)
      || lookupOptions.find((item) => item.nome === value);

    if (!selectedOption) {
      return;
    }

    selectingSuggestionRef.current = true;
    form.setFieldsValue({
      nome: selectedOption.nome,
      uf: selectedOption.uf,
    });

    if (selectedOption.ibge_code) {
      form.setFieldValue('ibge_code', selectedOption.ibge_code);
      setIbgeLocked(true);
      return;
    }

    setIbgeLocked(false);
    form.setFieldValue('ibge_code', '');
  };

  const handleDelete = (municipio: MunicipioRecord): void => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o município "${municipio.nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteMunicipio(municipio.id);
          message.success('Município excluído com sucesso');
          fetchMunicipios();
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const columns: ColumnsType<MunicipioRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'UF', dataIndex: 'uf', key: 'uf', width: 80, render: (uf: string) => <Tag color="blue">{uf}</Tag> },
    { title: 'IBGE', dataIndex: 'ibge_code', key: 'ibge_code', width: 120, render: (ibgeCode: string | null) => ibgeCode || '-' },
    {
      title: 'Ativo',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 100,
      render: (ativo: boolean) => <Tag color={ativo ? 'green' : 'red'}>{ativo ? 'Sim' : 'Não'}</Tag>,
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Editar
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            Excluir
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="municipios-title">
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="municipios-title">
            Municípios ({municipios.length})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou IBGE"
              allowClear
              style={{ width: '100%', maxWidth: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="Filtrar por UF"
              allowClear
              style={{ width: '100%', maxWidth: 100 }}
              onChange={setUfFilter}
              options={UF_NORDESTE_OPTIONS}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchMunicipios} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Município
            </Button>
          </Space>
        </header>

        <Table
          columns={columns}
          dataSource={municipios}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Card className="mt-6">
        <header className="flex justify-between items-center mb-4">
          <Title level={4} className="m-0">Importação de Municípios</Title>
        </header>
        <ImportUploader
          label="Importar Municípios"
          description="CSV/XLSX com colunas: nome, uf (obrigatórios), ibge_code e ativo (opcionais)"
          onDryRun={async (file: File) => toValidationResult(await importMunicipios(file, true) as unknown as Record<string, unknown>)}
          onApply={async (file: File) => toApplyResult(await importMunicipios(file, false) as unknown as Record<string, unknown>)}
        />
      </Card>

      {/* Modal Criar/Editar Município */}
      <Modal
        title={editingMunicipio ? 'Editar Município' : 'Novo Município'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setLookupOptions([]);
          setIbgeLocked(false);
        }}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          onFinish={handleSave}
        >
          <Form.Item
            name="nome"
            label="Nome do Município"
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <AutoComplete
              options={lookupOptions.map((item) => ({
                value: item.nome,
                label: `${item.nome} - ${item.uf}${item.ibge_code ? ` (${item.ibge_code})` : ''}`,
              }))}
              onSearch={handleMunicipioSearch}
              onSelect={handleMunicipioSelect}
              filterOption={false}
              notFoundContent={lookupLoading ? 'Buscando...' : 'Sem correspondências'}
              disabled={!watchedUf}
            >
              <Input placeholder={watchedUf ? 'Digite ao menos 2 letras (autocomplete)' : 'Selecione a UF primeiro'} />
            </AutoComplete>
          </Form.Item>

          <Form.Item
            name="uf"
            label="UF"
            rules={[{ required: true, message: 'UF é obrigatória' }]}
          >
            <Select
              placeholder="Selecione a UF"
              options={UF_NORDESTE_OPTIONS}
              onChange={() => {
                setLookupOptions([]);
                setIbgeLocked(false);
                form.setFieldValue('ibge_code', '');
              }}
            />
          </Form.Item>

          <Form.Item
            name="ibge_code"
            label="Código IBGE"
            rules={[
              { required: true, message: 'Código IBGE é obrigatório' },
              { pattern: /^\d{7}$/, message: 'Código IBGE deve conter 7 dígitos numéricos' },
            ]}
            extra={
              ibgeLocked
                ? 'Preenchido automaticamente por correspondência confiável.'
                : 'Preencha manualmente quando não houver correspondência confiável.'
            }
          >
            <Input placeholder="Ex: 2927408" maxLength={7} disabled={ibgeLocked} />
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Município ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
