/**
 * Página de Login - AS v2
 *
 * Design baseado na identidade visual do Programa Aprender
 * - Logo no topo
 * - Card com cantos arredondados e fundo claro
 * - Campos minimalistas
 */

import { useState } from 'react';
import { Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { login } from '../../api/auth';
import logoAprender from '../../assets/logo-aprender.png';

export default function LoginPage({ onLoginSuccess }) {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('Login realizado com sucesso!');
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      console.error('Erro no login:', error);
      message.error('Usuário ou senha incorretos.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start',
      paddingTop: '60px',
      background: '#004B3D',
    }}>
      {/* Logo */}
      <div style={{ marginBottom: '40px' }}>
        <img
          src={logoAprender}
          alt="Aprender"
          style={{
            width: '200px',
            height: 'auto',
            filter: 'brightness(0) invert(1)',
          }}
        />
      </div>

      {/* Card de Login */}
      <div
        style={{
          width: '100%',
          maxWidth: '420px',
          background: '#E5EDE5',
          borderRadius: '24px 24px 24px 24px',
          padding: '40px 32px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        }}
      >
        <h2 style={{
          color: '#004B3D',
          fontSize: '24px',
          fontWeight: '500',
          marginBottom: '32px',
          textAlign: 'center',
        }}>
          Login
        </h2>

        <Form
          name="login"
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
        >
          <Form.Item
            label="CPF"
            name="username"
            rules={[
              { required: true, message: 'Por favor, insira seu CPF!' }
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
              placeholder="CPF"
            />
          </Form.Item>

          <Form.Item
            label="Senha"
            name="password"
            rules={[
              { required: true, message: 'Por favor, insira sua senha!' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
              placeholder="Sua senha"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: '48px',
                fontSize: '16px',
                fontWeight: '500',
              }}
            >
              Entrar
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}
