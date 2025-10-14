/**
 * App Principal - AS v2 Frontend
 *
 * Roteamento para todas as páginas do sistema.
 */

import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu } from 'antd';
import { CalendarOutlined, CheckCircleOutlined } from '@ant-design/icons';
import ptBR from 'antd/locale/pt_BR';
import Disponibilidade from './pages/Disponibilidade';
import Solicitacoes from './pages/Solicitacoes';
import './App.css';

const { Header, Content } = Layout;

function App() {
  return (
    <ConfigProvider locale={ptBR}>
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Header style={{ display: 'flex', alignItems: 'center', padding: '0 24px' }}>
            <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold', marginRight: '40px' }}>
              AS v2
            </div>
            <Menu
              theme="dark"
              mode="horizontal"
              defaultSelectedKeys={['disponibilidade']}
              style={{ flex: 1, minWidth: 0 }}
            >
              <Menu.Item key="disponibilidade" icon={<CalendarOutlined />}>
                <Link to="/disponibilidade">Disponibilidade</Link>
              </Menu.Item>
              <Menu.Item key="solicitacoes" icon={<CheckCircleOutlined />}>
                <Link to="/solicitacoes">Solicitações</Link>
              </Menu.Item>
            </Menu>
          </Header>
          <Content style={{ padding: '0' }}>
            <Routes>
              <Route path="/" element={<Navigate to="/disponibilidade" replace />} />
              <Route path="/disponibilidade" element={<Disponibilidade />} />
              <Route path="/solicitacoes" element={<Solicitacoes />} />
            </Routes>
          </Content>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
