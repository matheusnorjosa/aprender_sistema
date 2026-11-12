/**
 * Botão "Dar feedback" (pedido do dono, 11/11/2026): fixo no canto inferior direito, para toda
 * pessoa logada. Abre só no clique (nunca sozinho). A caixa pede nota (1 a 5) e tipo, obrigatórios,
 * e um comentário opcional de até 2.000 caracteres; envia a rota da tela (`location.pathname`).
 *
 * A nota é um grupo de botões de rádio, não o `Rate` do AntD: as estrelas do Rate não têm nome
 * acessível e marcam como "selecionadas" todas as anteriores à escolhida.
 * Montado uma vez no layout logado (App.tsx), atrás do fundo da sidebar sobreposta (z-index 998).
 */
import { useState, type JSX } from 'react';
import { useLocation } from 'react-router';
import { Button, Form, Grid, Input, Modal, Radio, message } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
import { COMENTARIO_MAX, TIPOS_FEEDBACK, enviarFeedback, type TipoFeedback } from '../api/feedback';
import type { ErroHttp } from '../api/config';

interface Valores {
  nota?: number;
  tipo?: TipoFeedback;
  comentario?: string;
}

// O AntD repassa `role` ao div do Radio.Group (pickAttrs), mas o tipo não o declara: o grupo
// precisa do papel para o nome (aria-label) valer para o leitor de tela.
const GRUPO: Record<string, string> = { role: 'radiogroup' };

const NOTAS = [
  { value: 1, label: '1', title: '1: muito ruim' },
  { value: 2, label: '2', title: '2: ruim' },
  { value: 3, label: '3', title: '3: regular' },
  { value: 4, label: '4', title: '4: bom' },
  { value: 5, label: '5', title: '5: muito bom' },
];

function mensagemDeErro(error: unknown): string {
  if ((error as ErroHttp).status === 429) {
    return 'Você enviou muitos feedbacks em pouco tempo. Tente de novo mais tarde.';
  }
  return `Não foi possível enviar o feedback. ${(error as Error).message}`;
}

export function FeedbackButton(): JSX.Element {
  const location = useLocation();
  const compacto = !Grid.useBreakpoint().sm;
  const [aberto, setAberto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [form] = Form.useForm<Valores>();

  const fechar = (): void => {
    setAberto(false);
    form.resetFields();
  };

  const enviar = async (valores: Valores): Promise<void> => {
    setEnviando(true);
    try {
      await enviarFeedback({
        nota: valores.nota as number,
        tipo: valores.tipo as TipoFeedback,
        comentario: valores.comentario?.trim() ?? '',
        pagina: location.pathname,
      });
      message.success('Obrigado! Seu feedback foi enviado.');
      fechar();
    } catch (error) {
      message.error(mensagemDeErro(error));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <Button
        type="primary"
        shape={compacto ? 'circle' : 'round'}
        icon={<MessageOutlined aria-hidden />}
        aria-label={compacto ? 'Dar feedback' : undefined}
        onClick={() => setAberto(true)}
        // 32 px de altura a 12 px da borda: fica abaixo da paginação das telas (48 px de folga no fim delas).
        style={{ position: 'fixed', right: 16, bottom: 12, zIndex: 998, boxShadow: '0 2px 8px rgba(0, 0, 0, 0.25)' }}
      >
        {compacto ? null : 'Dar feedback'}
      </Button>
      <Modal
        open={aberto}
        title="Dar feedback"
        onCancel={fechar}
        destroyOnHidden
        footer={[
          <Button key="cancelar" onClick={fechar}>
            Cancelar
          </Button>,
          <Button key="enviar" type="primary" loading={enviando} onClick={() => form.submit()}>
            Enviar
          </Button>,
        ]}
      >
        <p>Conte como está sendo usar o sistema. Seu nome e a tela em que você está vão junto.</p>
        <Form<Valores> form={form} layout="vertical" name="feedback" onFinish={(v) => void enviar(v)}>
          <Form.Item
            name="nota"
            label="Nota (1 = muito ruim, 5 = muito bom)"
            rules={[{ required: true, message: 'Escolha uma nota de 1 a 5.' }]}
          >
            <Radio.Group
              {...GRUPO}
              aria-label="Nota (1 = muito ruim, 5 = muito bom)"
              optionType="button"
              options={NOTAS}
            />
          </Form.Item>
          <Form.Item name="tipo" label="Tipo" rules={[{ required: true, message: 'Escolha o tipo.' }]}>
            <Radio.Group {...GRUPO} aria-label="Tipo" options={[...TIPOS_FEEDBACK]} />
          </Form.Item>
          <Form.Item name="comentario" label="Comentário (opcional)">
            <Input.TextArea rows={4} maxLength={COMENTARIO_MAX} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
