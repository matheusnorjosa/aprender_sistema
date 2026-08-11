/**
 * Aviso de transparência LGPD (art. 9º) para a tela de login — SCAFFOLD.
 *
 * NÃO é um portão de consentimento: para um sistema interno de colaboradores a base legal
 * tipicamente não é consentimento (ver Política). É apenas informação ao titular no momento
 * da coleta. Self-contained (gerencia o próprio Drawer) para funcionar no login, que roda
 * fora do react-router. Os trechos [A PREENCHER] dependem do jurídico/Encarregado.
 */
import { useState, type JSX } from 'react';
import { Alert, Button, Drawer, Typography } from 'antd';
import PoliticaPrivacidadeContent from './PoliticaPrivacidadeContent';
import { BRAND_COLORS } from '../../contexts/ThemeContext';

const { Text } = Typography;

export default function AvisoTransparenciaLGPD(): JSX.Element {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Alert
        type="info"
        showIcon
        style={{ width: '100%', maxWidth: 420, marginTop: 24 }}
        message="Tratamento dos seus dados"
        description={
          <span>
            Ao acessar, seus dados de cadastro (CPF, nome e contato) são tratados para a
            gestão de formações e da agenda. Base legal:{' '}
            <Text mark>[A PREENCHER pelo jurídico]</Text>. Encarregado (DPO):{' '}
            <Text mark>[A PREENCHER]</Text>.{' '}
            <Button
              type="link"
              size="small"
              style={{ padding: 0, color: BRAND_COLORS.primaryDark, textDecoration: 'underline' }}
              onClick={() => setOpen(true)}
            >
              Ler a Política de Privacidade
            </Button>
            .
          </span>
        }
      />
      <Drawer
        title="Política de Privacidade"
        placement="right"
        width={Math.min(720, typeof window !== 'undefined' ? window.innerWidth : 720)}
        open={open}
        onClose={() => setOpen(false)}
      >
        <PoliticaPrivacidadeContent />
      </Drawer>
    </>
  );
}
