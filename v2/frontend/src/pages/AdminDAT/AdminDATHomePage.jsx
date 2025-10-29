/**
 * Admin DAT - Landing Page
 *
 * Página inicial do módulo de administração interna do DAT.
 * Substitui uso cotidiano do Django Admin para gestão de:
 * - Usuários (CRUD + CPF + grupos)
 * - Municípios (CRUD + indicadores)
 * - Grupos/Setores (CRUD + vínculos)
 * - Projetos (CRUD + fluxo + municípios)
 *
 * Fase 1 - Plano DAT/GCal 2025-10-29
 */

import { Card, Row, Col, Typography } from 'antd';
import { UserOutlined, EnvironmentOutlined, TeamOutlined, ProjectOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

export default function AdminDATHomePage() {
  const navigate = useNavigate();

  const modules = [
    {
      key: 'usuarios',
      title: 'Usuários',
      description: 'Gerenciar usuários, CPF, grupos e perfis',
      icon: <UserOutlined style={{ fontSize: '48px', color: '#1890ff' }} />,
      path: '/admin-dat/usuarios',
      status: 'Em desenvolvimento',
    },
    {
      key: 'municipios',
      description: 'CRUD de municípios com indicadores (UF, ativo)',
      icon: <EnvironmentOutlined style={{ fontSize: '48px', color: '#52c41a' }} />,
      path: '/admin-dat/municipios',
      status: 'Pendente',
    },
    {
      key: 'grupos',
      title: 'Grupos/Setores',
      description: 'Gerenciar grupos e vínculos usuário↔setor',
      icon: <TeamOutlined style={{ fontSize: '48px', color: '#faad14' }} />,
      path: '/admin-dat/grupos',
      status: 'Pendente',
    },
    {
      key: 'projetos',
      title: 'Projetos',
      description: 'CRUD de projetos, fluxo (SUPER/NAO_SUPER) e municípios',
      icon: <ProjectOutlined style={{ fontSize: '48px', color: '#722ed1' }} />,
      path: '/admin-dat/projetos',
      status: 'Pendente',
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>Admin DAT</Title>
        <Text type="secondary">
          Gestão interna de cadastros do DAT - substitui uso cotidiano do Django Admin
        </Text>
      </div>

      {/* Cards de módulos */}
      <Row gutter={[16, 16]}>
        {modules.map((module) => (
          <Col xs={24} sm={12} md={8} lg={6} key={module.key}>
            <Card
              hoverable
              style={{
                textAlign: 'center',
                height: '100%',
                cursor: module.status === 'Em desenvolvimento' ? 'pointer' : 'not-allowed',
                opacity: module.status === 'Em desenvolvimento' ? 1 : 0.6,
              }}
              onClick={() => {
                if (module.status === 'Em desenvolvimento') {
                  navigate(module.path);
                }
              }}
            >
              <div style={{ marginBottom: '16px' }}>{module.icon}</div>
              <Title level={4} style={{ marginBottom: '8px' }}>
                {module.title}
              </Title>
              <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                {module.description}
              </Text>
              <Text
                type={module.status === 'Em desenvolvimento' ? 'success' : 'warning'}
                strong
                style={{ fontSize: '11px' }}
              >
                {module.status}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
