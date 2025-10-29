/**
 * Página de Login - AS v2
 *
 * Design baseado em: paginadelogin/screen.png
 * - Login com CPF (com/sem máscara) ou username + senha
 * - Backend aceita CPF ou username no mesmo campo
 * - Link "Esqueci a senha?"
 * - Link "Cadastre-se" (futuro)
 * - Layout centralizado e clean
 */

import { useState } from 'react';
import { Form, Input, Button, Typography, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { login } from '../../api/auth';

const { Title, Text, Link } = Typography;

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
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card
        style={{
          width: 450,
          boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
          borderRadius: '8px',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Title level={2} style={{ marginBottom: '8px' }}>
            Bem-vindo de volta!
          </Title>
          <Text type="secondary">
            Acesse sua conta para continuar.
          </Text>
        </div>

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
            <Link href="#" style={{ float: 'right' }}>
              Esqueci a senha?
            </Link>
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

        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <Text type="secondary">
            Ainda não tem uma conta?{' '}
            <Link href="#">Cadastre-se</Link>
          </Text>
        </div>
      </Card>
    </div>
  );
}
