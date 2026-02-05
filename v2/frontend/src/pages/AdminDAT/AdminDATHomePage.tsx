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

import type { ReactNode } from 'react';
import { Card, Row, Col, Typography } from 'antd';
import { UserOutlined, EnvironmentOutlined, TeamOutlined, ProjectOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

/**
 * Module configuration interface
 */
interface ModuleConfig {
  key: string;
  title: string;
  description: string;
  icon: ReactNode;
  path: string;
  status: 'Disponível' | 'Em breve';
}

export default function AdminDATHomePage(): JSX.Element {
  const navigate = useNavigate();

  const modules: ModuleConfig[] = [
    {
      key: 'usuarios',
      title: 'Usuários',
      description: 'Gerenciar usuários, CPF, grupos e perfis',
      icon: <UserOutlined className="text-5xl text-blue-500" />,
      path: '/dat/admin/usuarios',
      status: 'Disponível',
    },
    {
      key: 'municipios',
      title: 'Municípios',
      description: 'CRUD de municípios com indicadores (UF, ativo)',
      icon: <EnvironmentOutlined className="text-5xl text-green-500" />,
      path: '/dat/admin/municipios',
      status: 'Disponível',
    },
    {
      key: 'grupos',
      title: 'Grupos/Setores',
      description: 'Gerenciar grupos e vínculos usuário↔setor',
      icon: <TeamOutlined className="text-5xl text-yellow-500" />,
      path: '/dat/admin/grupos',
      status: 'Disponível',
    },
    {
      key: 'projetos',
      title: 'Projetos',
      description: 'CRUD de projetos, fluxo (SUPER/NAO_SUPER) e municípios',
      icon: <ProjectOutlined className="text-5xl text-purple-600" />,
      path: '/dat/admin/projetos',
      status: 'Disponível',
    },
    {
      key: 'configuracoes',
      title: 'Configurações',
      description: 'Configurações do sistema (disponibilidade, GCal, sessões, features)',
      icon: <SettingOutlined className="text-5xl text-cyan-500" />,
      path: '/dat/admin/configuracoes',
      status: 'Disponível',
    },
  ];

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="admin-dat-title">
      {/* Header */}
      <header style={{ marginBottom: '24px' }}>
        <Title level={2} id="admin-dat-title">Admin DAT</Title>
        <Text type="secondary">
          Gestão interna de cadastros do DAT - substitui uso cotidiano do Django Admin
        </Text>
      </header>

      {/* Cards de módulos */}
      <nav aria-label="Módulos de administração">
      <Row gutter={[16, 16]}>
        {modules.map((module) => (
          <Col xs={24} sm={12} md={8} lg={6} key={module.key}>
            <Card
              hoverable
              style={{
                textAlign: 'center',
                height: '100%',
                cursor: module.status === 'Disponível' ? 'pointer' : 'not-allowed',
                opacity: module.status === 'Disponível' ? 1 : 0.6,
              }}
              onClick={() => {
                if (module.status === 'Disponível') {
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
                type={module.status === 'Disponível' ? 'success' : 'warning'}
                strong
                style={{ fontSize: '11px' }}
              >
                {module.status}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>
      </nav>
    </section>
  );
}
