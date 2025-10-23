/**
 * App Principal - AS v2 Frontend
 *
 * Roteamento para todas as páginas do sistema.
 */

import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu } from 'antd';
import { CalendarOutlined, CheckCircleOutlined, TableOutlined, ShoppingOutlined, DatabaseOutlined } from '@ant-design/icons';
import ptBR from 'antd/locale/pt_BR';
import DisponibilidadeBlocks from './pages/Disponibilidade';
import MonthlyPage from './pages/Disponibilidade/MonthlyPage';
import Solicitacoes from './pages/Solicitacoes';
import ControlePage from './pages/Controle/ControlePage';
import DATPage from './pages/DAT/DATPage';
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
              <Menu.Item key="grade-mensal" icon={<TableOutlined />}>
                <Link to="/disponibilidade">Grade Mensal</Link>
              </Menu.Item>
              <Menu.Item key="bloqueios" icon={<CalendarOutlined />}>
                <Link to="/bloqueios">Bloqueios</Link>
              </Menu.Item>
              <Menu.Item key="solicitacoes" icon={<CheckCircleOutlined />}>
                <Link to="/solicitacoes">Solicitações</Link>
              </Menu.Item>
              <Menu.Item key="controle" icon={<ShoppingOutlined />}>
                <Link to="/controle">Controle</Link>
              </Menu.Item>
              <Menu.Item key="dat" icon={<DatabaseOutlined />}>
                <Link to="/dat">DAT</Link>
              </Menu.Item>
            </Menu>
          </Header>
          <Content style={{ padding: '0' }}>
            <Routes>
              <Route path="/" element={<Navigate to="/disponibilidade" replace />} />
              <Route path="/disponibilidade" element={<MonthlyPage />} />
              <Route path="/bloqueios" element={<DisponibilidadeBlocks />} />
              <Route path="/solicitacoes" element={<Solicitacoes />} />
              <Route path="/controle" element={<ControlePage />} />
              <Route path="/dat" element={<DATPage />} />
            </Routes>
          </Content>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
