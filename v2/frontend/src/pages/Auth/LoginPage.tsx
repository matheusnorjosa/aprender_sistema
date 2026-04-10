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
import logoLogin from '../../assets/logo-login.png';
import logger from '../../utils/logger';
import { BRAND_COLORS } from '../../contexts/ThemeContext';

/**
 * Login form values interface
 */
interface LoginFormValues {
  username: string;
  password: string;
}

/**
 * LoginPage props interface
 */
export interface LoginPageProps {
  onLoginSuccess?: () => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps): JSX.Element {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: LoginFormValues): Promise<void> => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('Login realizado com sucesso!');
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      logger.error('Erro no login:', error);
      message.error('Usuário ou senha incorretos.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <main
        id="main"
        className="login-page flex flex-col items-center justify-start"
        style={{ minHeight: '100vh', paddingTop: '60px', background: BRAND_COLORS.primaryDark }}
        aria-labelledby="login-title"
      >
      {/* Logo */}
      <header style={{ marginBottom: '40px' }}>
        <img
          src={logoLogin}
          alt="Aprender Sistema"
          width={140}
          height={157}
          // @ts-expect-error React 18 doesn't type fetchpriority yet
          fetchpriority="high"
          style={{
            width: '140px',
            height: 'auto',
          }}
        />
      </header>

      {/* Card de Login */}
      <article
        className="login-card"
        style={{
          width: '100%',
          maxWidth: '420px',
          background: BRAND_COLORS.primaryLight,
          borderRadius: '24px 24px 24px 24px',
          padding: '40px 32px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        }}
      >
        <h1 id="login-title" style={{
          color: BRAND_COLORS.primaryDark,
          fontSize: '24px',
          fontWeight: '500',
          marginBottom: '32px',
          textAlign: 'center',
        }}>
          Login
        </h1>

        <Form
          name="login"
          onFinish={handleSubmit}
          layout="vertical"
          autoComplete="off"
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
              className="login-submit"
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
      </article>
      </main>
    </>
  );
}
