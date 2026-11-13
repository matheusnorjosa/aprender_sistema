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
 * Cores: as do modelo no tema claro e as do tema ativo no escuro (`coresDaCaixa`).
 * Montado uma vez no layout logado (App.tsx), atrás do fundo da sidebar sobreposta (z-index 998).
 */
import { useContext, useId, useState, type CSSProperties, type JSX, type ReactNode } from 'react';
import { useLocation } from 'react-router';
import {
  Button,
  ConfigProvider,
  Form,
  Grid,
  Input,
  Modal,
  message,
  theme,
  type GlobalToken,
  type ThemeConfig,
} from 'antd';
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
import ThemeContext, { BRAND_COLORS } from '../contexts/ThemeContext';

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

interface CoresDaCaixa {
  titulo: string;
  painel: string;
  destaque: string;
  mancha: string;
  textoDoBom: string;
  vermelho: string;
  discreto: string;
}

/**
 * Cores da caixa que mudam com o tema. O resto vem direto dos tokens do tema ativo: superfície
 * (colorBgElevated), borda (colorBorder), acento dos indicadores (colorPrimary) e verde de texto
 * (colorLink); no claro, os dois verdes são o da marca.
 * No escuro, painel, destaque e mancha são o acento misturado à superfície, com contraste medido
 * no fundo #1f1f1f: título 5,2:1; número escolhido no painel 4,6:1; estrela escolhida no destaque
 * 3,2:1; vermelho 5,9:1 (5,1:1 no painel). O terciário do escuro dá 4,4:1: o texto discreto é o
 * secundário.
 */
function coresDaCaixa(token: GlobalToken, escuro: boolean): CoresDaCaixa {
  const tom = (pct: number): string => `color-mix(in srgb, ${token.colorPrimary} ${pct}%, ${token.colorBgContainer})`;
  if (escuro) {
    return {
      titulo: token.colorLink,
      painel: tom(12),
      destaque: tom(20),
      mancha: tom(7),
      textoDoBom: token.colorText,
      vermelho: token.red8,
      discreto: token.colorTextSecondary,
    };
  }
  return {
    titulo: BRAND_COLORS.primaryDark,
    painel: BRAND_COLORS.primaryLight,
    // A marca a 15% sobre o branco: mais forte que o fundo do painel.
    destaque: tom(15),
    mancha: `${BRAND_COLORS.primaryLight}99`,
    textoDoBom: BRAND_COLORS.primaryDark,
    // Vermelho 7, o colorError do tema claro desde o DEF-28: 4,7:1 no painel e 5,6:1 no branco.
    vermelho: token.red7,
    discreto: token.colorTextTertiary,
  };
}

function useCoresDaCaixa(): { token: GlobalToken; escuro: boolean; cores: CoresDaCaixa } {
  const { token } = theme.useToken();
  // Sem ThemeProvider (teste de componente) vale o claro, como em ApprovalsPage.
  const escuro = useContext(ThemeContext)?.isDark === true;
  return { token, escuro, cores: coresDaCaixa(token, escuro) };
}

// Detalhe do canto (modelo do dono): duas manchas, como uma onda. É só fundo: não cobre o botão
// fechar nem o texto.
function detalheDoCanto(cores: CoresDaCaixa): string {
  return [
    `radial-gradient(130px 96px at 100% 0, ${cores.painel} 0 68%, transparent 70%)`,
    `radial-gradient(220px 150px at 100% 0, ${cores.mancha} 0 66%, transparent 68%)`,
  ].join(', ');
}

// O AntD não dá prop para o botão fechar: aqui ele vira um círculo de 40 px (alvo de toque) na cor
// da superfície (branco no claro), sobre o detalhe do canto. O `button.` do seletor passa a
// especificidade do AntD sem `!important`. As variáveis `--fb-*` vêm do fundo da caixa.
const FECHAR_EM_CIRCULO = [
  '[&_button.ant-modal-close]:end-3',
  '[&_button.ant-modal-close]:top-3',
  '[&_button.ant-modal-close]:size-10',
  '[&_button.ant-modal-close]:rounded-full',
  '[&_button.ant-modal-close]:bg-[color:var(--fb-superficie)]',
  '[&_button.ant-modal-close]:shadow',
].join(' ');

// Texto de exemplo no discreto da caixa. No escuro, o App.css pinta o de todo input com o terciário
// (4,4:1); o `[placeholder]` sobe a especificidade acima dessa regra.
const TEXTO_DE_EXEMPLO = '[&.ant-input[placeholder]::placeholder]:text-[color:var(--fb-exemplo)]';

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
  const { token, cores } = useCoresDaCaixa();
  return (
    <div className="min-w-0">
      <p id={`${base}-pergunta`} className="m-0 font-semibold">
        {pergunta}
        {/* O obrigatório chega ao leitor de tela pelo aria-required. */}
        <span aria-hidden="true" style={{ color: cores.vermelho }}>
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
  const { token, cores } = useCoresDaCaixa();
  const base = useId();
  return (
    <div
      className="flex flex-col gap-3 rounded-xl p-4 sm:flex-row sm:items-center sm:justify-between"
      style={{ background: cores.painel }}
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
                  className="grid size-11 place-items-center rounded-lg border text-xl peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[color:var(--fb-acento)]"
                  style={
                    escolhida
                      ? { borderWidth: 2, borderColor: token.colorPrimary, background: cores.destaque, color: token.colorPrimary }
                      : { borderColor: token.colorBorder, background: token.colorBgElevated, color: token.colorTextTertiary }
                  }
                >
                  <Estrela aria-hidden />
                </span>
                <span
                  aria-hidden="true"
                  className={escolhida ? 'font-semibold' : undefined}
                  style={{ color: escolhida ? token.colorLink : token.colorTextSecondary }}
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
          <span className="rounded-full px-2 py-0.5" style={{ background: cores.destaque, color: cores.textoDoBom }}>
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
  const { token, escuro, cores } = useCoresDaCaixa();
  const base = useId();
  // No escuro, o tom 7 ou 8 da paleta: o 6 fica abaixo de 3:1 no cartão escuro.
  const icones: Record<TipoFeedback, ReactNode> = {
    ELOGIO: <LikeOutlined aria-hidden style={{ color: token.colorPrimary }} />,
    PROBLEMA: <WarningOutlined aria-hidden style={{ color: escuro ? token.red7 : token.red6 }} />,
    SUGESTAO: <BulbOutlined aria-hidden style={{ color: escuro ? token.blue7 : token.blue6 }} />,
    DUVIDA: <QuestionCircleOutlined aria-hidden style={{ color: escuro ? token.purple8 : token.purple6 }} />,
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
              className="flex cursor-pointer flex-col gap-1 rounded-xl border p-3 shadow-sm has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-[color:var(--fb-acento)]"
              style={
                escolhido
                  ? { borderColor: token.colorPrimary, background: cores.painel, boxShadow: `0 0 0 1px ${token.colorPrimary}` }
                  : { borderColor: token.colorBorder, background: token.colorBgElevated }
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
                  className="m-0 size-4 cursor-pointer"
                  // No escuro, o rádio nativo também fica escuro (sem o círculo branco do navegador).
                  style={{ accentColor: token.colorPrimary, colorScheme: escuro ? 'dark' : undefined }}
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
  const { token, cores } = useCoresDaCaixa();
  const idComentario = useId();
  const [aberto, setAberto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [form] = Form.useForm<Valores>();

  // AA nesta caixa: o erro do campo no vermelho da caixa e o contador no texto discreto (no escuro, o
  // colorError e o terciário não chegam a 4,5:1). A borda verde do comentário (modelo) é o
  // colorPrimaryBorder: 3,8:1 no branco; no escuro vale a borda dos inputs escuros (App.css).
  const temaDaCaixa: ThemeConfig = {
    components: {
      Form: { colorError: cores.vermelho },
      Input: { colorBorder: token.colorPrimaryBorder, colorTextDescription: cores.discreto, borderRadius: 12 },
    },
  };
  const fundoDaCaixa = {
    backgroundImage: detalheDoCanto(cores),
    '--fb-superficie': token.colorBgElevated,
    '--fb-acento': token.colorPrimary,
    '--fb-exemplo': cores.discreto,
  } as CSSProperties;

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
        styles={{ content: fundoDaCaixa, header: { background: 'transparent', marginBottom: 2 } }}
        // Só o título dá nome à caixa; o subtítulo fica no corpo, ao lado do ícone (que sai do título para baixo).
        title={
          <span
            className="relative block pe-12 ps-16 text-xl font-bold leading-7 sm:text-[22px]"
            style={{ color: cores.titulo }}
          >
            <MessageOutlined aria-hidden className="absolute start-0 top-0.5 text-[48px]" style={{ color: token.colorPrimary }} />
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
                classNames={{ textarea: TEXTO_DE_EXEMPLO }}
              />
            </Form.Item>
          </Form>
          {/* Transparência (LGPD): não está no modelo, mas fica, discreta, perto do envio. O mt-6 garante
              24 px abaixo da caixa de texto, onde fica o contador (22 px); no celular a margem do item é 12 px. */}
          <p className="mt-6 text-xs" style={{ color: cores.discreto }}>
            Seu nome e a tela em que você está vão junto.
          </p>
        </ConfigProvider>
      </Modal>
    </>
  );
}
