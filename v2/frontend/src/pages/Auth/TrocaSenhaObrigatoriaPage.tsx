/**
 * Troca obrigatória de senha (primeiro acesso) — AS v2
 *
 * A pessoa entrou com uma senha definida por outra pessoa (`deve_trocar_senha` no /api/me/).
 * Enquanto não escolher a própria, o servidor recusa todo o resto (403
 * PASSWORD_CHANGE_REQUIRED), então esta tela ocupa o lugar do sistema: sem menu, sem fechar;
 * só "Salvar e continuar" e "Sair". Mesmo casco visual do login.
 */

import { useState, type JSX } from 'react';
import { Alert, Button, Form, Input } from 'antd';
import { changeMyPassword } from '../../api/me';
import { getMe } from '../../api/availability';
import type { ErroHttp } from '../../api/config';
import logoLogin from '../../assets/logo-login.webp';
import logger from '../../utils/logger';
import { BRAND_COLORS } from '../../contexts/ThemeContext';

export interface TrocaSenhaObrigatoriaPageProps {
  /** A senha foi trocada: o App recarrega o usuário e abre o endereço que a pessoa pediu. */
  onConcluida: () => void | Promise<void>;
  /** "Sair": encerra a sessão sem trocar a senha. */
  onSair: () => void | Promise<void>;
  /** O servidor disse que a sessão acabou no meio da troca. */
  onSessaoEncerrada: () => void | Promise<void>;
}

interface FormValues {
  senha_recebida: string;
  nova_senha: string;
  repetir: string;
}

type Campo = keyof FormValues;

const ID_REGRAS = 'troca-senha-regras';

/** Espelha AUTH_PASSWORD_VALIDATORS (settings.py) + a regra "diferente da recebida". */
const REGRAS = [
  'Pelo menos 8 caracteres.',
  'Não pode ser só números.',
  'Não pode ser uma senha muito comum (como "senha123").',
  'Não pode parecer com seu nome, CPF ou e-mail.',
  'Tem de ser diferente da senha que você recebeu.',
] as const;

const paraTexto = (valor: unknown): string | null => {
  if (typeof valor === 'string' && valor) return valor;
  if (Array.isArray(valor) && valor.length > 0) return valor.map(String).join(' ');
  return null;
};

/**
 * A senha recebida foi recusada (400): se a marca já saiu (troca feita em outra aba), a senha
 * recebida deixou de valer e não há o que corrigir. Consulta o /api/me/ uma vez; na dúvida, não.
 */
const trocaJaFeita = async (error: unknown): Promise<boolean> => {
  const err = error as ErroHttp;
  const dados = (err.response?.data ?? {}) as { errors?: Record<string, unknown> };
  if (err.status !== 400 || !paraTexto(dados.errors?.['old_password'])) return false;
  try {
    return (await getMe()).deve_trocar_senha !== true;
  } catch {
    return false;
  }
};

export default function TrocaSenhaObrigatoriaPage({
  onConcluida,
  onSair,
  onSessaoEncerrada,
}: TrocaSenhaObrigatoriaPageProps): JSX.Element {
  const [form] = Form.useForm<FormValues>();
  const [salvando, setSalvando] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const [erroGeral, setErroGeral] = useState<string | null>(null);

  const erroNoCampo = (campo: Campo, texto: string): void => {
    form.setFields([{ name: campo, errors: [texto] }]);
    (form.getFieldInstance(campo) as { focus?: () => void } | undefined)?.focus?.();
  };

  const handleSubmit = async (values: FormValues): Promise<void> => {
    setSalvando(true);
    setErroGeral(null);
    try {
      await changeMyPassword({ old_password: values.senha_recebida, new_password: values.nova_senha });
    } catch (error) {
      if (await trocaJaFeita(error)) {
        await onConcluida();
        return;
      }
      setSalvando(false);
      if (error instanceof TypeError) {
        setErroGeral('Sem conexão com o servidor. Sua senha não foi alterada. Confira a internet e tente de novo.');
        return;
      }
      const err = error as ErroHttp;
      const dados = (err.response?.data ?? {}) as { code?: string; errors?: Record<string, unknown> };
      if (err.status === 401 || (err.status === 403 && dados.code === 'NOT_AUTHENTICATED')) {
        await onSessaoEncerrada();
        return;
      }
      if (err.status === 429) {
        const espera = err.retryAfter ? `${err.retryAfter} segundos` : 'cerca de um minuto';
        setErroGeral(`Muitas tentativas. Aguarde ${espera} e tente de novo. Sua senha não foi alterada.`);
        return;
      }
      const erroNova = paraTexto(dados.errors?.['new_password']);
      const erroRecebida = paraTexto(dados.errors?.['old_password']);
      if (err.status === 400 && (erroNova || erroRecebida)) {
        // A ordem importa: o foco fica no primeiro campo com erro.
        if (erroNova) erroNoCampo('nova_senha', erroNova);
        if (erroRecebida) {
          erroNoCampo('senha_recebida', 'Esta não é a senha que você recebeu. Confira e digite de novo.');
        }
        return;
      }
      logger.error('Erro na troca obrigatória de senha:', error);
      setErroGeral(
        'Não foi possível salvar a senha agora. O problema é no sistema, não na sua senha. Tente de novo em alguns minutos.',
      );
      return;
    }
    // Sem `setSalvando(false)`: o App troca esta tela pelo sistema.
    await onConcluida();
  };

  const handleSair = async (): Promise<void> => {
    setSaindo(true);
    try {
      await onSair();
    } finally {
      setSaindo(false);
    }
  };

  return (
    <main
      id="main"
      className="login-page flex flex-col items-center justify-start"
      style={{ minHeight: '100vh', padding: '40px 16px', background: BRAND_COLORS.primaryDark }}
      aria-labelledby="troca-senha-titulo"
    >
      <header style={{ marginBottom: '24px' }}>
        <img src={logoLogin} alt="Aprender Sistema" width={96} height={108} style={{ width: '96px', height: 'auto' }} />
      </header>

      <article
        className="login-card"
        style={{
          width: '100%',
          maxWidth: '420px',
          background: BRAND_COLORS.primaryLight,
          borderRadius: '24px',
          padding: '32px 24px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
          color: BRAND_COLORS.primaryDark,
        }}
      >
        <h1
          id="troca-senha-titulo"
          style={{ color: BRAND_COLORS.primaryDark, fontSize: '24px', fontWeight: 500, marginBottom: '12px' }}
        >
          Defina sua senha
        </h1>
        <p style={{ marginBottom: '16px' }}>
          Você entrou com uma senha provisória. Para continuar, crie uma senha só sua.
        </p>

        <p id={`${ID_REGRAS}-titulo`} style={{ fontWeight: 600, marginBottom: '4px' }}>
          Regras da nova senha
        </p>
        <ul
          id={ID_REGRAS}
          aria-labelledby={`${ID_REGRAS}-titulo`}
          style={{ paddingLeft: '20px', marginBottom: '20px', listStyle: 'disc' }}
        >
          {REGRAS.map((regra) => (
            <li key={regra}>{regra}</li>
          ))}
        </ul>

        {erroGeral && (
          <Alert type="error" showIcon role="alert" message={erroGeral} style={{ marginBottom: '16px' }} />
        )}

        <Form<FormValues>
          form={form}
          name="troca-senha-obrigatoria"
          layout="vertical"
          size="large"
          onFinish={handleSubmit}
          onFinishFailed={({ errorFields }) => {
            const primeiro = errorFields[0]?.name[0] as Campo | undefined;
            if (primeiro) (form.getFieldInstance(primeiro) as { focus?: () => void } | undefined)?.focus?.();
          }}
        >
          <Form.Item
            name="senha_recebida"
            label="Senha que você recebeu"
            rules={[{ required: true, message: 'Digite a senha que você recebeu.' }]}
          >
            <Input.Password autoFocus autoComplete="current-password" />
          </Form.Item>

          <Form.Item
            name="nova_senha"
            label="Nova senha"
            dependencies={['senha_recebida']}
            rules={[
              { required: true, message: 'Digite a nova senha.' },
              { min: 8, message: 'A senha precisa de pelo menos 8 caracteres.' },
              ({ getFieldValue }) => ({
                validator(_, value: string | undefined) {
                  if (value && value === getFieldValue('senha_recebida')) {
                    return Promise.reject(new Error('A nova senha tem de ser diferente da que você recebeu.'));
                  }
                  return Promise.resolve();
                },
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" aria-describedby={ID_REGRAS} />
          </Form.Item>

          <Form.Item
            name="repetir"
            label="Repita a nova senha"
            dependencies={['nova_senha']}
            rules={[
              { required: true, message: 'Digite a nova senha outra vez.' },
              ({ getFieldValue }) => ({
                validator(_, value: string | undefined) {
                  if (!value || value === getFieldValue('nova_senha')) return Promise.resolve();
                  return Promise.reject(new Error('As senhas não conferem.'));
                },
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>

          <Form.Item style={{ marginBottom: '12px' }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={salvando}
              disabled={saindo}
              block
              className="login-submit"
              style={{ height: '48px', fontSize: '16px', fontWeight: 500 }}
            >
              Salvar e continuar
            </Button>
          </Form.Item>
          <Button block onClick={() => void handleSair()} loading={saindo} disabled={salvando}>
            Sair
          </Button>
        </Form>
      </article>
    </main>
  );
}
