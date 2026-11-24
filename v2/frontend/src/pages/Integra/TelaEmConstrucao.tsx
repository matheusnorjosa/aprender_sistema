/**
 * Tela da Integra que ainda não foi feita: o título dela e o aviso "em construção".
 *
 * Usada pelo Semáforo, que chega na próxima entrega.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';
import { Alert, Typography } from 'antd';

const { Title } = Typography;

interface TelaEmConstrucaoProps {
  /** Título da tela (h1). */
  titulo: string;
  /** Frase do aviso; o padrão é "Esta tela está em construção." */
  aviso?: string;
  /** Mostra o link "Voltar para a Integra" (as telas fora do ICA, que não têm o menu do ICA). */
  comVolta?: boolean;
}

export function TelaEmConstrucao({ titulo, aviso, comVolta = false }: TelaEmConstrucaoProps): JSX.Element {
  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 16 }}>
        {titulo}
      </Title>
      <Alert type="info" showIcon message={aviso ?? 'Esta tela está em construção.'} />
      {comVolta && (
        <p className="mt-4">
          <Link to="/integra">Voltar para a Integra</Link>
        </p>
      )}
    </section>
  );
}
