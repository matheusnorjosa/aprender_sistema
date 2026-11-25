/**
 * Integra: a página que reúne as ferramentas do gestor pedagógico (reunião de 23/11/2026; decisão do
 * dono Q10, 24/11). Cinco cartões, no padrão do `AccessCard` da Página Inicial:
 * ICA, Semáforo, Deslocamento, DFF (no endereço atual, em outra aba) e Avaliação do Coordenador (em breve).
 */
import { useId, type JSX, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Card, Col, Row, Tag, Typography } from 'antd';
import {
  AlertOutlined,
  AuditOutlined,
  CarOutlined,
  CheckSquareOutlined,
  DashboardOutlined,
  ExportOutlined,
  ReadOutlined,
} from '@ant-design/icons';

import { EXTERNAL_URLS } from '../../constants/urls';
import { BRAND_COLORS } from '../../contexts/ThemeContext';

const { Title, Paragraph } = Typography;

/** Texto de apoio com contraste AA sobre branco (o `type="secondary"` do antd fica em 3,4:1). */
const COR_TEXTO_APOIO = '#595959';

/** Contorno de foco visível nos cartões que são link (WCAG 2.4.7). */
const CLASSE_FOCO =
  'block h-full rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark';

type Destino = { tipo: 'interno'; para: string } | { tipo: 'externo'; href: string } | { tipo: 'em-breve' };

interface Ferramenta {
  titulo: string;
  descricao: string;
  icone: ReactNode;
  destino: Destino;
}

const FERRAMENTAS: readonly Ferramenta[] = [
  {
    titulo: 'ICA',
    descricao: 'Índice de Carga de Acompanhamento: a carga de cada coordenador comparada com a média da equipe.',
    icone: <DashboardOutlined />,
    destino: { tipo: 'interno', para: '/integra/ica' },
  },
  {
    titulo: 'Semáforo de Risco Municipal',
    descricao: 'A cor de risco de cada município, para o comitê e as gestoras.',
    icone: <AlertOutlined />,
    destino: { tipo: 'interno', para: '/integra/semaforo' },
  },
  {
    titulo: 'Deslocamento',
    descricao: 'Quanto tempo leva para chegar a cada município, ida e volta, e a soma desses tempos na carteira de cada coordenador.',
    icone: <CarOutlined />,
    destino: { tipo: 'interno', para: '/integra/deslocamento' },
  },
  {
    titulo: 'DFF',
    descricao: 'Observação de formação e PDI, no endereço de sempre.',
    icone: <ReadOutlined />,
    destino: { tipo: 'externo', href: EXTERNAL_URLS.DFF_PLATFORM },
  },
  {
    titulo: 'Avaliação do Coordenador',
    descricao: 'O nome ainda vai ser escolhido.',
    icone: <AuditOutlined />,
    destino: { tipo: 'em-breve' },
  },
];

function CorpoDoCartao({ ferramenta, idTitulo }: { ferramenta: Ferramenta; idTitulo: string }): JSX.Element {
  const emBreve = ferramenta.destino.tipo === 'em-breve';
  return (
    <Card
      hoverable={!emBreve}
      style={{ height: '100%', ...(emBreve && { background: '#f5f5f5', cursor: 'default' }) }}
    >
      <div className="flex items-start justify-between gap-2">
        <span aria-hidden="true" style={{ fontSize: 32, color: BRAND_COLORS.primaryDark }}>
          {ferramenta.icone}
        </span>
        {emBreve && <Tag>Em breve</Tag>}
      </div>
      <Title level={2} id={idTitulo} style={{ fontSize: 18, marginTop: 12, marginBottom: 4 }}>
        {ferramenta.titulo}
      </Title>
      <Paragraph style={{ color: COR_TEXTO_APOIO, marginBottom: 0 }}>{ferramenta.descricao}</Paragraph>
      {ferramenta.destino.tipo === 'externo' && (
        <Paragraph style={{ color: BRAND_COLORS.primaryDark, marginTop: 8, marginBottom: 0 }}>
          <ExportOutlined aria-hidden="true" /> Abre em outra aba
        </Paragraph>
      )}
    </Card>
  );
}

function CartaoFerramenta({ ferramenta }: { ferramenta: Ferramenta }): JSX.Element {
  const idTitulo = useId();
  const corpo = <CorpoDoCartao ferramenta={ferramenta} idTitulo={idTitulo} />;
  const { destino } = ferramenta;
  if (destino.tipo === 'interno') {
    return (
      <Link to={destino.para} className={CLASSE_FOCO}>
        {corpo}
      </Link>
    );
  }
  if (destino.tipo === 'externo') {
    return (
      <a href={destino.href} target="_blank" rel="noopener noreferrer" className={CLASSE_FOCO}>
        {corpo}
      </a>
    );
  }
  return (
    <div role="group" aria-labelledby={idTitulo} aria-disabled="true" className="h-full">
      {corpo}
    </div>
  );
}

export default function IntegraPage(): JSX.Element {
  return (
    <div>
      <Title level={1} style={{ fontSize: 26, marginBottom: 4 }}>
        Integra
      </Title>
      <Paragraph style={{ color: COR_TEXTO_APOIO }}>
        As ferramentas do gestor pedagógico num lugar só. As pessoas e os números destas telas são simulados; os municípios são reais, e os tempos de deslocamento são as estimativas do relatório da Coordenação Pedagógica.
      </Paragraph>

      <Row gutter={[16, 16]} className="mt-4">
        {FERRAMENTAS.map((ferramenta) => (
          <Col key={ferramenta.titulo} xs={24} sm={12} lg={8}>
            <CartaoFerramenta ferramenta={ferramenta} />
          </Col>
        ))}
      </Row>

      <Card className="mt-6">
        <p className="m-0 flex items-start gap-2">
          <CheckSquareOutlined aria-hidden="true" style={{ fontSize: 20, color: BRAND_COLORS.primaryDark }} />
          <span>
            <Link to="/integra/para-validar">Para validar no dia 7</Link>
            <span style={{ color: COR_TEXTO_APOIO }}>
              : as sugestões e os pontos abertos da reunião, e como o protótipo resolveu cada um.
            </span>
          </span>
        </p>
      </Card>
    </div>
  );
}
