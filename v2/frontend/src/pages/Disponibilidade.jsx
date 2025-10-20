/**
 * Página de Gerenciamento de Disponibilidade
 *
 * Permite ao usuário:
 * - Criar bloqueios de disponibilidade (Total ou Parcial)
 * - Listar seus bloqueios existentes
 * - Excluir bloqueios com status 'pendente'
 */

import { useState, useEffect } from 'react';
import { Card, Row, Col, message, Spin } from 'antd';
import BlockForm from '../components/BlockForm';
import MyBlocksTable from '../components/MyBlocksTable';
import { getBlocks, createBlock as apiCreateBlock, deleteBlock as apiDeleteBlock } from '../api/availability';

export default function Disponibilidade() {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);

  /**
   * Carrega lista de bloqueios do usuário atual.
   */
  const fetchBlocks = async () => {
    setLoading(true);
    try {
      const data = await getBlocks({ owner: 'me' });
      setBlocks(data);
    } catch (error) {
      message.error(`Erro ao carregar bloqueios: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handler para criação de novo bloqueio.
   *
   * @param {object} data - Dados do bloqueio a criar
   */
  const handleCreate = async (data) => {
    try {
      await apiCreateBlock(data);
      message.success('Bloqueio criado com sucesso!');
      await fetchBlocks(); // Recarregar lista
    } catch (error) {
      message.error(`Erro ao criar bloqueio: ${error.message}`);
      throw error; // Propagar erro para o form
    }
  };

  /**
   * Handler para exclusão de bloqueio.
   *
   * @param {number} id - ID do bloqueio a excluir
   */
  const handleDelete = async (id) => {
    try {
      await apiDeleteBlock(id);
      message.success('Bloqueio removido com sucesso!');
      await fetchBlocks(); // Recarregar lista
    } catch (error) {
      message.error(`Erro ao remover bloqueio: ${error.message}`);
    }
  };

  // Carregar bloqueios ao montar componente
  useEffect(() => {
    fetchBlocks();
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <h1>Gerenciar Disponibilidade</h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Crie bloqueios de disponibilidade (Total ou Parcial) para indicar períodos em que você não estará disponível.
      </p>

      <Row gutter={[16, 16]}>
        {/* Card de Criação */}
        <Col xs={24} lg={12}>
          <Card title="Criar Bloqueio" bordered={false}>
            <BlockForm onSubmit={handleCreate} />
          </Card>
        </Col>

        {/* Card de Listagem */}
        <Col xs={24} lg={12}>
          <Card title="Meus Bloqueios" bordered={false}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Spin size="large" tip="Carregando bloqueios..." />
              </div>
            ) : (
              <MyBlocksTable blocks={blocks} onDelete={handleDelete} loading={loading} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
