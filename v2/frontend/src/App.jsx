/**
 * App Principal - AS v2 Frontend
 *
 * Roteamento simples para página de Disponibilidade.
 */

import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import Disponibilidade from './pages/Disponibilidade';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={ptBR}>
      <div className="App">
        <Disponibilidade />
      </div>
    </ConfigProvider>
  );
}

export default App;
