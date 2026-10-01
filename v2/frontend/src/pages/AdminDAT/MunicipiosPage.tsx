/**
 * Admin DAT - Municípios
 *
 * CRUD de municípios com indicadores (UF, ativo).
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useEffect, useRef, useState, type JSX } from 'react';
import { Button, Input, Tag, Typography, Card, message, Select, Modal, Form, Checkbox, AutoComplete, Grid, Space } from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
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
import { aplicacaoDoImport, validacaoDoImport } from '../../components/resultadoDoImport';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { DEFAULT_PAGE_SIZE, UF_NORDESTE_OPTIONS } from '../../constants';
import type { ID } from '../../types';
import { errosDosCampos, mensagemDoErro } from './usuario_form_helpers';

const { Title, Text } = Typography;
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

/** Nome de tela do município: com a UF, porque há municípios de mesmo nome em UFs diferentes. */
function nomeDoMunicipio(municipio: MunicipioRecord): string {
  return `${municipio.nome} - ${municipio.uf}`;
}

function normalizeMunicipioName(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
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
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });
  const [salvando, setSalvando] = useState(false);
  const [erroLista, setErroLista] = useState<string | null>(null);
  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações", e a UF sai da
  // grade (fica junto do nome: há municípios de mesmo nome em UFs diferentes).
  const acoesCompactas = !Grid.useBreakpoint().sm;

  const [form] = Form.useForm<MunicipioFormValues>();
  const watchedNome = Form.useWatch('nome', form);
  const watchedUf = Form.useWatch('uf', form);
  const lookupRequestRef = useRef(0);
  const selectingSuggestionRef = useRef(false);

  const fetchMunicipios = async (
    current = pagination.current || 1,
    pageSize = pagination.pageSize || DEFAULT_PAGE_SIZE,
  ): Promise<void> => {
    setLoading(true);
    try {
      const data = await listMunicipios({
        search: searchText,
        uf: ufFilter,
        ordering: 'nome',
        page: current,
        page_size: pageSize,
      });
      setMunicipios(data.results as MunicipioRecord[]);
      setErroLista(null);
      setPagination((prev) => ({
        ...prev,
        current,
        pageSize,
        total: data.count,
      }));
    } catch (error) {
      setErroLista(mensagemDoErro(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchMunicipios(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText, ufFilter]);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    void fetchMunicipios(
      newPagination.current || 1,
      newPagination.pageSize || pagination.pageSize || DEFAULT_PAGE_SIZE,
    );
  };

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

    const timerId = window.setTimeout(() => {
      void (async () => {
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
      })();
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
    if (!match) return;
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
    // Quem filtrou por UF está cadastrando naquela UF: o nome já fica liberado.
    if (ufFilter) form.setFieldsValue({ uf: ufFilter });
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
    setSalvando(true);
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
      void fetchMunicipios(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    } catch (error) {
      form.setFields(errosDosCampos(error));
      message.error(`Erro: ${mensagemDoErro(error)}`);
    } finally {
      setSalvando(false);
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
      content: `Tem certeza que deseja excluir o município "${nomeDoMunicipio(municipio)}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      // Ação destrutiva: o foco começa no Cancelar (senão um Enter repetido exclui sem confirmar).
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteMunicipio(municipio.id);
          message.success('Município excluído com sucesso');
          void fetchMunicipios(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
        } catch (error) {
          message.error(`Erro ao excluir: ${mensagemDoErro(error)}`);
        }
      },
    });
  };

  // Vazio que diz o que fazer: o filtro de UF (com o jeito de limpá-lo), a busca, ou cadastrar.
  const vazio = ufFilter ? (
    <Space direction="vertical" size={4}>
      <span>Nenhum município para a UF {ufFilter}.</span>
      <Button size="small" onClick={() => setUfFilter(undefined)}>
        Limpar filtro de UF
      </Button>
    </Space>
  ) : searchText ? (
    `Nenhum município encontrado para "${searchText}".`
  ) : (
    'Nenhum município cadastrado. Use "Novo Município" ou importe uma planilha abaixo.'
  );

  // C2: lista enxuta, por prioridade de largura (VISIVEL_A_PARTIR). O que some da linha vai
  // para a linha expandida (ResponsiveTable). O ID interno não vai para a grade.
  const columns: ColunaResponsiva<MunicipioRecord>[] = [
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      // Sem detalhe que mostre o nome inteiro, ele quebra linha em vez de cortar. No celular, a
      // UF (fora da grade) vai junto: há municípios de mesmo nome em UFs diferentes.
      render: (_, record) => (
        <Text className="min-w-0 max-w-full break-words">
          {record.nome}
          {acoesCompactas ? <Text type="secondary"> - {record.uf}</Text> : null}
        </Text>
      ),
    },
    {
      title: 'UF',
      dataIndex: 'uf',
      key: 'uf',
      width: 64,
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_, record) => <Tag color="blue" style={{ marginInlineEnd: 0 }}>{record.uf}</Tag>,
    },
    {
      title: 'IBGE',
      dataIndex: 'ibge_code',
      key: 'ibge_code',
      width: 104,
      responsive: VISIVEL_A_PARTIR.md,
      render: (_, record) => record.ibge_code || '-',
    },
    {
      title: 'Situação',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 88,
      render: (_, record) => {
        const cor = record.ativo ? 'green' : 'red';
        return (
          <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
            {record.ativo ? 'Ativo' : 'Inativo'}
          </Tag>
        );
      },
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: larguraAcoesLinha(2, acoesCompactas),
      render: (_, record) => (
        <AcoesLinha
          compacto={acoesCompactas}
          alvo={nomeDoMunicipio(record)}
          acoes={[
            { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => handleEdit(record) },
            {
              chave: 'excluir',
              rotulo: 'Excluir',
              icone: <DeleteOutlined />,
              onClick: () => handleDelete(record),
              perigo: true,
            },
          ]}
        />
      ),
    },
  ];

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="municipios-title">
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="municipios-title">
            {/* Lista que falhou não tem total: "(0)" diria que não há município. */}
            Municípios{erroLista ? '' : ` (${pagination.total || 0})`}
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Search
              placeholder="Buscar por nome ou IBGE"
              aria-label="Buscar municípios por nome ou IBGE"
              allowClear
              style={{ width: 250, maxWidth: '100%' }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="Filtrar por UF"
              aria-label="Filtrar por UF"
              allowClear
              style={{ width: 140 }}
              value={ufFilter}
              onChange={setUfFilter}
              options={UF_NORDESTE_OPTIONS}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchMunicipios(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
              loading={loading}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Município
            </Button>
          </div>
        </header>

        <ResponsiveTable<MunicipioRecord>
          columns={columns}
          dataSource={municipios}
          rowKey="id"
          nomeDaLinha={nomeDoMunicipio}
          loading={loading}
          erro={erroLista}
          onTentarDeNovo={() => void fetchMunicipios(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
          locale={{ emptyText: vazio }}
          onChange={handleTableChange}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => `Total: ${total}`,
          }}
        />
      </Card>

      <Card className="mt-6">
        <header className="flex justify-between items-center mb-4">
          <Title level={4} className="m-0">Importação de Municípios</Title>
        </header>
        <ImportUploader
          label="Importar Municípios"
          description="CSV/XLSX com colunas: nome, uf (obrigatórios), ibge_code e ativo (opcionais)"
          onDryRun={async (file: File) => validacaoDoImport(await importMunicipios(file, true))}
          onApply={async (file: File) => aplicacaoDoImport(await importMunicipios(file, false))}
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
        confirmLoading={salvando}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          onFinish={handleSave}
        >
          {/* A UF vem primeiro: o nome só libera (e o autocomplete só busca) com a UF escolhida. */}
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
