/**
 * Página de Perfil do usuário autenticado (`/perfil`).
 *
 * MVP: exibe os dados da conta (nome, CPF mascarado, e-mail, setores/funções) e
 * permite **trocar a própria senha** (self-service). Resolve a dívida de segurança
 * do go-live (usuários importados com senha padrão só podiam trocar via admin).
 *
 * Acessível a qualquer usuário logado. Login do sistema é por CPF + senha.
 */

import { useState } from 'react';
import { Button, Card, Descriptions, Form, Input, Space, Tag, Typography, message } from 'antd';
import { DownloadOutlined, LockOutlined, PhoneOutlined, UserOutlined } from '@ant-design/icons';
import { Link } from 'react-router';

import type { CurrentUser } from '../../types/usuario';
import { changeMyPassword, exportMyData, updateMyContact } from '../../api/me';

const { Title } = Typography;

interface ChangePasswordForm {
  senha_atual: string;
  nova_senha: string;
  confirmar: string;
}

interface ContatoForm {
  telefone: string;
}

/** Mascara o CPF (LGPD): mostra só os 3 primeiros e os 2 últimos dígitos. */
export function maskCpf(value: string): string {
  const digits = (value ?? '').replace(/\D/g, '');
  if (digits.length !== 11) return value;
  return `${digits.slice(0, 3)}.***.***-${digits.slice(9, 11)}`;
}

function TagList({ items }: { items: readonly string[] }) {
  if (!items || items.length === 0) return <span>—</span>;
  return (
    <>
      {items.map((it) => (
        <Tag key={it}>{it}</Tag>
      ))}
    </>
  );
}

export default function PerfilPage({ user }: { user: CurrentUser }) {
  const [form] = Form.useForm<ChangePasswordForm>();
  const [contatoForm] = Form.useForm<ContatoForm>();
  const [saving, setSaving] = useState(false);
  const [savingContato, setSavingContato] = useState(false);
  const [exporting, setExporting] = useState(false);
  // Telefone exibido: estado local para refletir a correção sem recarregar a página.
  const [telefone, setTelefone] = useState(user.telefone ?? '');

  // LGPD art. 18-V (portabilidade): baixa o dossiê do titular como JSON.
  const onExport = async () => {
    setExporting(true);
    try {
      const blob = await exportMyData();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'meus-dados-aprender.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      message.success('Seus dados foram exportados.');
    } catch (error) {
      message.error((error as Error).message || 'Não foi possível exportar seus dados.');
    } finally {
      setExporting(false);
    }
  };

  const onFinish = async (values: ChangePasswordForm) => {
    setSaving(true);
    try {
      await changeMyPassword({
        old_password: values.senha_atual,
        new_password: values.nova_senha,
      });
      message.success('Senha alterada com sucesso.');
      form.resetFields();
    } catch (error) {
      message.error((error as Error).message || 'Não foi possível alterar a senha.');
    } finally {
      setSaving(false);
    }
  };

  // LGPD art. 18-III: o titular corrige o próprio telefone.
  const onFinishContato = async (values: ContatoForm) => {
    setSavingContato(true);
    try {
      const atualizado = await updateMyContact({ telefone: values.telefone.trim() });
      setTelefone(atualizado.telefone ?? values.telefone.trim());
      message.success('Telefone atualizado com sucesso.');
    } catch (error) {
      message.error((error as Error).message || 'Não foi possível atualizar o telefone.');
    } finally {
      setSavingContato(false);
    }
  };

  return (
    <section className="p-6 bg-gray-100 min-h-full" aria-labelledby="perfil-title">
      <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 640 }}>
        <Title id="perfil-title" level={3}>
          Meu perfil
        </Title>

        <Card title={
          <span>
            <UserOutlined /> Meus dados
          </span>
        }>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Nome">{user.name || user.username}</Descriptions.Item>
            <Descriptions.Item label="CPF">{maskCpf(user.cpf ?? user.username)}</Descriptions.Item>
            <Descriptions.Item label="E-mail">{user.email || '—'}</Descriptions.Item>
            <Descriptions.Item label="Telefone">{telefone || '—'}</Descriptions.Item>
            <Descriptions.Item label="Cargo">{user.cargo || '—'}</Descriptions.Item>
            <Descriptions.Item label="Setores">
              <TagList items={user.setores} />
            </Descriptions.Item>
            <Descriptions.Item label="Funções">
              <TagList items={user.funcoes} />
            </Descriptions.Item>
          </Descriptions>

          <div className="mt-4">
            <Button icon={<DownloadOutlined />} loading={exporting} onClick={onExport}>
              Exportar meus dados
            </Button>
            <Typography.Text type="secondary" className="ml-2">
              Baixa uma cópia dos seus dados (portabilidade — LGPD art. 18-V).
            </Typography.Text>
          </div>
          <div className="mt-3">
            <Link to="/politica-privacidade">Política de Privacidade</Link>
          </div>
        </Card>

        <Card title={
          <span>
            <PhoneOutlined /> Atualizar telefone
          </span>
        }>
          <Form<ContatoForm>
            form={contatoForm}
            layout="vertical"
            autoComplete="off"
            initialValues={{ telefone }}
            onFinish={onFinishContato}
          >
            <Form.Item
              name="telefone"
              label="Telefone"
              rules={[{ max: 20, message: 'O telefone deve ter no máximo 20 caracteres.' }]}
            >
              <Input placeholder="(85) 99999-0000" allowClear />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<PhoneOutlined />} loading={savingContato}>
                Salvar telefone
              </Button>
            </Form.Item>
          </Form>
        </Card>

        <Card title={
          <span>
            <LockOutlined /> Trocar senha
          </span>
        }>
          <Form<ChangePasswordForm> form={form} layout="vertical" autoComplete="off" onFinish={onFinish}>
            <Form.Item
              name="senha_atual"
              label="Senha atual"
              rules={[{ required: true, message: 'Informe a senha atual.' }]}
            >
              <Input.Password placeholder="Senha atual" autoComplete="current-password" />
            </Form.Item>

            <Form.Item
              name="nova_senha"
              label="Nova senha"
              rules={[
                { required: true, message: 'Informe a nova senha.' },
                { min: 8, message: 'A senha deve ter no mínimo 8 caracteres.' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (value && value === getFieldValue('senha_atual')) {
                      return Promise.reject(new Error('A nova senha deve ser diferente da atual.'));
                    }
                    return Promise.resolve();
                  },
                }),
              ]}
            >
              <Input.Password placeholder="Nova senha" autoComplete="new-password" />
            </Form.Item>

            <Form.Item
              name="confirmar"
              label="Confirmar nova senha"
              dependencies={['nova_senha']}
              rules={[
                { required: true, message: 'Confirme a nova senha.' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || value === getFieldValue('nova_senha')) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('As senhas não conferem.'));
                  },
                }),
              ]}
            >
              <Input.Password placeholder="Confirmar nova senha" autoComplete="new-password" />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<LockOutlined />} loading={saving}>
                Alterar senha
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Space>
    </section>
  );
}
