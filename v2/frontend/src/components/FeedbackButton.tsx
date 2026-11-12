/**
 * Botão "Dar feedback" (pedido do dono, 11/11/2026): fixo no canto inferior direito, para toda
 * pessoa logada. Abre só no clique (nunca sozinho) a caixa "Enviar feedback", no modelo que o dono
 * mandou em 12/11/2026: nota (1 a 5) e tipo, obrigatórios, e um comentário opcional de até 2.000
 * caracteres; envia a rota da tela (`location.pathname`).
 *
 * A nota é um grupo de botões de rádio, não o `Rate` do AntD: as estrelas do Rate não têm nome
 * acessível e marcam como "selecionadas" todas as anteriores à escolhida. Nota e tipo são rádios
 * nativos, com um `name` por grupo (é ele que faz as setas do teclado andarem entre as opções); o
 * desenho do modelo fica no rótulo de cada rádio.
 * Montado uma vez no layout logado (App.tsx), atrás do fundo da sidebar sobreposta (z-index 998).
 */
import { useId, useState, type JSX, type ReactNode } from 'react';
import { useLocation } from 'react-router';
import { Button, ConfigProvider, Form, Grid, Input, Modal, message, theme, type ThemeConfig } from 'antd';
import {
  BulbOutlined,
  LikeOutlined,
  MessageOutlined,
  QuestionCircleOutlined,
  SendOutlined,
  StarFilled,
  StarOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { COMENTARIO_MAX, TIPOS_FEEDBACK, enviarFeedback, type TipoFeedback } from '../api/feedback';
import type { ErroHttp } from '../api/config';
import { BRAND_COLORS } from '../contexts/ThemeContext';

interface Valores {
  nota?: number;
  tipo?: TipoFeedback;
  comentario?: string;
}

/** O que o Form.Item injeta no campo: valor, troca, id e os aria do obrigatório e do erro. */
interface CampoDoForm<T> {
  value?: T;
  onChange?: (valor: T) => void;
  id?: string;
  'aria-describedby'?: string;
  'aria-invalid'?: 'true';
  'aria-required'?: 'true';
}

const NOTAS = [
  { valor: 1, nome: '1: muito ruim' },
  { valor: 2, nome: '2: ruim' },
  { valor: 3, nome: '3: regular' },
  { valor: 4, nome: '4: bom' },
  { valor: 5, nome: '5: muito bom' },
];

const DESCRICAO_DO_TIPO: Record<TipoFeedback, string> = {
  ELOGIO: 'Algo que está funcionando bem.',
  PROBLEMA: 'Algo que não está funcionando como deveria.',
  SUGESTAO: 'Uma ideia de melhoria para o sistema.',
  DUVIDA: 'Uma pergunta sobre o uso do sistema.',
};

// Verde de destaque (nota escolhida e pílula "Muito bom"): a marca a 15% sobre o branco, mais forte
// que o fundo do painel (`--as-primary-light`).
const VERDE_DESTAQUE = 'color-mix(in srgb, var(--as-primary) 15%, white)';

// Detalhe do canto (modelo do dono): duas manchas verde-claras, como uma onda. É só fundo: não cobre
// o botão fechar nem o texto.
const DETALHE_DO_CANTO = [
  `radial-gradient(130px 96px at 100% 0, ${BRAND_COLORS.primaryLight} 0 68%, transparent 70%)`,
  `radial-gradient(220px 150px at 100% 0, ${BRAND_COLORS.primaryLight}99 0 66%, transparent 68%)`,
].join(', ');

// O AntD não dá prop para o botão fechar: aqui ele vira um círculo branco de 40 px (alvo de toque)
// sobre o detalhe do canto. O `button.` do seletor passa a especificidade do AntD sem `!important`.
const FECHAR_EM_CIRCULO = [
  '[&_button.ant-modal-close]:end-3',
  '[&_button.ant-modal-close]:top-3',
  '[&_button.ant-modal-close]:size-10',
  '[&_button.ant-modal-close]:rounded-full',
  '[&_button.ant-modal-close]:bg-white',
  '[&_button.ant-modal-close]:shadow',
].join(' ');

function juntarIds(...ids: Array<string | undefined>): string {
  return ids.filter(Boolean).join(' ');
}

function mensagemDeErro(error: unknown): string {
  if ((error as ErroHttp).status === 429) {
    return 'Você enviou muitos feedbacks em pouco tempo. Tente de novo mais tarde.';
  }
  return `Não foi possível enviar o feedback. ${(error as Error).message}`;
}

/** Pergunta em negrito, com o asterisco de obrigatório, e a dica embaixo. */
function Enunciado({ base, pergunta, dica }: { base: string; pergunta: string; dica: string }): JSX.Element {
  const { token } = theme.useToken();
  return (
    <div className="min-w-0">
      <p id={`${base}-pergunta`} className="m-0 font-semibold">
        {pergunta}
        {/* Vermelho 7: 4,7:1 no fundo do painel. O obrigatório chega ao leitor de tela pelo aria-required. */}
        <span aria-hidden="true" style={{ color: token.red7 }}>
          {' *'}
        </span>
      </p>
      <p id={`${base}-dica`} className="m-0 text-sm" style={{ color: token.colorTextSecondary }}>
        {dica}
      </p>
    </div>
  );
}

function EscolhaDaNota({
  value,
  onChange,
  id,
  'aria-describedby': erro,
  'aria-invalid': invalido,
  'aria-required': obrigatorio,
}: CampoDoForm<number>): JSX.Element {
  const { token } = theme.useToken();
  const base = useId();
  return (
    <div
      className="flex flex-col gap-3 rounded-xl p-4 sm:flex-row sm:items-center sm:justify-between"
      style={{ background: BRAND_COLORS.primaryLight }}
    >
      <Enunciado base={base} pergunta="Como você avalia o sistema hoje?" dica="Escolha uma nota de 1 a 5." />
      <div
        role="radiogroup"
        id={id}
        aria-labelledby={`${base}-pergunta`}
        aria-describedby={juntarIds(`${base}-dica`, erro)}
        aria-invalid={invalido}
        aria-required={obrigatorio}
        className="shrink-0"
      >
        <div className="flex gap-2">
          {NOTAS.map(({ valor, nome }) => {
            const escolhida = value === valor;
            const Estrela = escolhida ? StarFilled : StarOutlined;
            return (
              <label key={valor} title={nome} className="relative flex cursor-pointer flex-col items-center gap-1">
                <input
                  type="radio"
                  name={`${base}-nota`}
                  value={valor}
                  checked={escolhida}
                  onChange={() => onChange?.(valor)}
                  aria-label={nome}
                  className="peer sr-only"
                />
                <span
                  className="grid size-11 place-items-center rounded-lg border bg-white text-xl peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary"
                  style={
                    escolhida
                      ? { borderWidth: 2, borderColor: BRAND_COLORS.primary, background: VERDE_DESTAQUE, color: BRAND_COLORS.primary }
                      : { borderColor: token.colorBorder, color: token.colorTextTertiary }
                  }
                >
                  <Estrela aria-hidden />
                </span>
                <span
                  aria-hidden="true"
                  className={escolhida ? 'font-semibold' : undefined}
                  style={{ color: escolhida ? BRAND_COLORS.primary : token.colorTextSecondary }}
                >
                  {valor}
                </span>
              </label>
            );
          })}
        </div>
        {/* Os nomes dos rádios já dizem "1: muito ruim" e "5: muito bom": as pílulas são só para o olho. */}
        <div aria-hidden="true" className="mt-2 flex justify-between text-xs">
          <span className="rounded-full px-2 py-0.5" style={{ background: token.colorFillSecondary, color: token.colorTextSecondary }}>
            Muito ruim
          </span>
          <span className="rounded-full px-2 py-0.5" style={{ background: VERDE_DESTAQUE, color: BRAND_COLORS.primaryDark }}>
            Muito bom
          </span>
        </div>
      </div>
    </div>
  );
}

function EscolhaDoTipo({
  value,
  onChange,
  id,
  'aria-describedby': erro,
  'aria-invalid': invalido,
  'aria-required': obrigatorio,
}: CampoDoForm<TipoFeedback>): JSX.Element {
  const { token } = theme.useToken();
  const base = useId();
  const icones: Record<TipoFeedback, ReactNode> = {
    ELOGIO: <LikeOutlined aria-hidden style={{ color: BRAND_COLORS.primary }} />,
    PROBLEMA: <WarningOutlined aria-hidden style={{ color: token.red6 }} />,
    SUGESTAO: <BulbOutlined aria-hidden style={{ color: token.blue6 }} />,
    DUVIDA: <QuestionCircleOutlined aria-hidden style={{ color: token.purple6 }} />,
  };
  return (
    <div>
      <Enunciado
        base={base}
        pergunta="Qual é o tipo do seu feedback?"
        dica="Selecione a opção que melhor descreve o seu comentário."
      />
      <div
        role="radiogroup"
        id={id}
        aria-labelledby={`${base}-pergunta`}
        aria-describedby={juntarIds(`${base}-dica`, erro)}
        aria-invalid={invalido}
        aria-required={obrigatorio}
        className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4"
      >
        {TIPOS_FEEDBACK.map(({ value: tipo, label }) => {
          const escolhido = value === tipo;
          return (
            <label
              key={tipo}
              className="flex cursor-pointer flex-col gap-1 rounded-xl border bg-white p-3 shadow-sm has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary"
              style={
                escolhido
                  ? { borderColor: BRAND_COLORS.primary, background: BRAND_COLORS.primaryLight, boxShadow: `0 0 0 1px ${BRAND_COLORS.primary}` }
                  : { borderColor: token.colorBorder }
              }
            >
              <span className="flex items-start justify-between gap-2">
                <span className="text-[22px] leading-none">{icones[tipo]}</span>
                <input
                  type="radio"
                  name={`${base}-tipo`}
                  value={tipo}
                  checked={escolhido}
                  onChange={() => onChange?.(tipo)}
                  aria-labelledby={`${base}-${tipo}`}
                  aria-describedby={`${base}-${tipo}-descricao`}
                  className="m-0 size-4 cursor-pointer accent-primary"
                />
              </span>
              <span id={`${base}-${tipo}`} className="font-semibold">
                {label}
              </span>
              <span id={`${base}-${tipo}-descricao`} className="text-xs" style={{ color: token.colorTextSecondary }}>
                {DESCRICAO_DO_TIPO[tipo]}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

export function FeedbackButton(): JSX.Element {
  const location = useLocation();
  const compacto = !Grid.useBreakpoint().sm;
  const { token } = theme.useToken();
  const idComentario = useId();
  const [aberto, setAberto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [form] = Form.useForm<Valores>();

  // AA (4,5:1) nesta caixa: o AntD pinta o erro do campo com o colorError (3,3:1 no branco) e o texto
  // de exemplo com 25% de preto (1,8:1); aqui ficam no vermelho 7 (5,6:1) e no terciário (4,7:1).
  // A borda verde do comentário (modelo) é o colorPrimaryBorder: 3,8:1 no branco.
  const temaDaCaixa: ThemeConfig = {
    token: { colorError: token.red7 },
    components: {
      Input: { colorBorder: token.colorPrimaryBorder, colorTextPlaceholder: token.colorTextTertiary, borderRadius: 12 },
    },
  };

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
        width={640}
        className={FECHAR_EM_CIRCULO}
        styles={{ content: { backgroundImage: DETALHE_DO_CANTO }, header: { background: 'transparent', marginBottom: 2 } }}
        // Só o título dá nome à caixa; o subtítulo fica no corpo, ao lado do ícone (que sai do título para baixo).
        title={
          <span
            className="relative block pe-12 ps-16 text-xl font-bold leading-7 sm:text-[22px]"
            style={{ color: BRAND_COLORS.primaryDark }}
          >
            <MessageOutlined aria-hidden className="absolute start-0 top-0.5 text-[48px]" style={{ color: BRAND_COLORS.primary }} />
            Enviar feedback
          </span>
        }
        onCancel={fechar}
        destroyOnHidden
        footer={[
          <Button key="cancelar" size="large" onClick={fechar}>
            Cancelar
          </Button>,
          <Button
            key="enviar"
            size="large"
            type="primary"
            icon={<SendOutlined aria-hidden />}
            loading={enviando}
            onClick={() => form.submit()}
          >
            Enviar feedback
          </Button>,
        ]}
      >
        <ConfigProvider theme={temaDaCaixa}>
          <p className="mb-5 pe-12 ps-16" style={{ color: token.colorTextSecondary }}>
            Ajude a melhorar o sistema! Conte como está sendo a sua experiência.
          </p>
          <Form<Valores> form={form} layout="vertical" name="feedback" onFinish={(v) => void enviar(v)}>
            <Form.Item name="nota" rules={[{ required: true, message: 'Escolha uma nota.' }]}>
              <EscolhaDaNota />
            </Form.Item>
            <Form.Item name="tipo" rules={[{ required: true, message: 'Escolha o tipo.' }]}>
              <EscolhaDoTipo />
            </Form.Item>
            <label htmlFor={idComentario} className="block">
              <span className="font-semibold">Conte mais</span> (opcional)
            </label>
            <p id={`${idComentario}-dica`} className="mb-2 text-sm" style={{ color: token.colorTextSecondary }}>
              Descreva sua experiência, o que aconteceu ou a sua sugestão em detalhes.
            </p>
            <Form.Item name="comentario">
              <Input.TextArea
                id={idComentario}
                aria-describedby={`${idComentario}-dica`}
                rows={4}
                maxLength={COMENTARIO_MAX}
                showCount
                placeholder="Escreva seu comentário aqui..."
              />
            </Form.Item>
          </Form>
          {/* Transparência (LGPD): não está no modelo, mas fica, discreta, perto do envio. O mt-6 garante
              24 px abaixo da caixa de texto, onde fica o contador (22 px); no celular a margem do item é 12 px. */}
          <p className="mt-6 text-xs" style={{ color: token.colorTextTertiary }}>
            Seu nome e a tela em que você está vão junto.
          </p>
        </ConfigProvider>
      </Modal>
    </>
  );
}
