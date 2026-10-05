/**
 * Página de Login - AS v2
 *
 * Design baseado na identidade visual do Programa Aprender
 * - Logo no topo
 * - Card com cantos arredondados e fundo claro
 * - Campos minimalistas
 */

import { useEffect, useState, type JSX } from 'react';
import { Form, Input, Button, message, Alert } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { login } from '../../api/auth';
import type { ErroHttp } from '../../api/config';
import logoLogin from '../../assets/logo-login.webp';
import logger from '../../utils/logger';
import { apagarAvisoDoLogin, lerAvisoDoLogin } from '../../utils/storage';
import { BRAND_COLORS } from '../../contexts/ThemeContext';
// Aviso LGPD ocultado temporariamente ate o juridico preencher a base legal e o Encarregado (DPO)
// em AvisoTransparenciaLGPD (placeholders [A PREENCHER]). Reativar: descomentar este import e o uso abaixo.
// import AvisoTransparenciaLGPD from '../../components/lgpd/AvisoTransparenciaLGPD';

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

/** Quanto esperar depois de um 429, em palavras (o Retry-After vem em segundos). */
function tempoDeEspera(segundos: number | undefined): string {
  if (!segundos) return 'cerca de um minuto';
  if (segundos <= 90) return `${segundos} segundos`;
  return `cerca de ${Math.ceil(segundos / 60)} minutos`;
}

/**
 * Frase do erro ao entrar, por causa. Decide pelo STATUS (a falha de login responde
 * `{error}`, sem `code`). Senha errada e bloqueio por tentativas têm a MESMA frase de
 * propósito: o servidor não revela o bloqueio (#745).
 */
function mensagemDoErroDeLogin(error: unknown): string {
  if (error instanceof TypeError) {
    return 'Sem conexão com o servidor. Confira a internet e tente de novo. Sua senha não foi recusada.';
  }
  const { status, retryAfter } = error as ErroHttp;
  if (status === 429) {
    return `Muitas tentativas de entrada vindas desta rede. Aguarde ${tempoDeEspera(retryAfter)} e tente de novo. Sua senha não foi recusada.`;
  }
  if (status === 400) {
    return 'CPF ou senha incorretos. Depois de 10 erros o acesso fica bloqueado por alguns minutos.';
  }
  return 'Não foi possível entrar agora. O problema é no sistema, não na sua senha. Tente de novo em alguns minutos.';
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps): JSX.Element {
  const [loading, setLoading] = useState(false);
  // Erro da última tentativa: fica na tela (um toast some antes de a pessoa ler).
  const [erro, setErro] = useState<string | null>(null);
  // Motivo guardado pelo App antes do reload (ex.: "Sua sessão expirou por inatividade").
  // Lido uma vez e apagado, para não reaparecer no próximo login.
  const [aviso] = useState(lerAvisoDoLogin);
  useEffect(() => {
    apagarAvisoDoLogin();
  }, []);

  const handleSubmit = async (values: LoginFormValues): Promise<void> => {
    setLoading(true);
    setErro(null);
    try {
      await login(values.username, values.password);
      message.success('Login realizado com sucesso!');
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      logger.error('Erro no login:', error);
      setErro(mensagemDoErroDeLogin(error));
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
          fetchPriority="high"
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

        {/* Um alerta só: o erro da tentativa substitui o aviso de sessão expirada. */}
        {erro
          ? <Alert type="error" showIcon message={erro} style={{ marginBottom: '24px' }} />
          : aviso && <Alert type="warning" showIcon message={aviso} style={{ marginBottom: '24px' }} />}

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

      {/* LGPD art. 9º: aviso de transparência no momento da coleta (não é consentimento).
          Ocultado temporariamente ate o juridico preencher a base legal e o Encarregado (DPO) —
          os placeholders [A PREENCHER] apareciam ao usuario. Reativar: descomentar o import (topo)
          e a linha abaixo. O componente e a Politica de Privacidade permanecem intactos. */}
      {/* <AvisoTransparenciaLGPD /> */}
      </main>
    </>
  );
}
