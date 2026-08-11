/**
 * Conteúdo da Política de Privacidade (LGPD) — SCAFFOLD.
 *
 * ⚠️ Este é um ANDAIME para o Encarregado (DPO) + jurídico revisarem e completarem.
 * O conteúdo técnico (quais dados, finalidade, compartilhamento com Google, retenção,
 * segurança, como exercer direitos) reflete o sistema REAL e pode ser mantido. Os trechos
 * marcados com <Pendente> exigem decisão do controlador/advogado (identificação legal,
 * contato do Encarregado, base legal específica, data de vigência) — NÃO são texto
 * jurídico vinculante gerado automaticamente.
 *
 * Reutilizado na rota autenticada `/politica-privacidade` e no Drawer do aviso no login.
 */
import type { JSX, ReactNode } from 'react';
import { Typography, Divider } from 'antd';

const { Title, Paragraph, Text } = Typography;

/** Realça um trecho que o controlador/advogado precisa preencher. */
function Pendente({ children }: { children: ReactNode }): JSX.Element {
  return (
    <Text
      mark
      style={{ padding: '0 4px' }}
      aria-label="Trecho pendente de preenchimento pelo jurídico"
    >
      [A PREENCHER] {children}
    </Text>
  );
}

export default function PoliticaPrivacidadeContent(): JSX.Element {
  return (
    <Typography>
      <Title level={2}>Política de Privacidade</Title>
      <Paragraph type="secondary">
        Versão: <Pendente>vX.Y</Pendente> · Vigência a partir de <Pendente>dd/mm/aaaa</Pendente>.
        Este documento explica como o Aprender Sistema trata seus dados pessoais, conforme a
        Lei nº 13.709/2018 (LGPD).
      </Paragraph>

      <Title level={3}>1. Quem é o controlador</Title>
      <Paragraph>
        O controlador dos dados é <Pendente>razão social, CNPJ e endereço</Pendente>. Para
        assuntos de privacidade, fale com o Encarregado (DPO): <Pendente>nome, e-mail e
        canal de contato do Encarregado</Pendente>.
      </Paragraph>

      <Title level={3}>2. Quais dados tratamos</Title>
      <Paragraph>Para operar a plataforma, tratamos:</Paragraph>
      <ul>
        <li><Text strong>Cadastro:</Text> CPF, nome, e-mail, telefone e cargo.</li>
        <li><Text strong>Organização:</Text> setores e funções (perfil de acesso).</li>
        <li>
          <Text strong>Operação:</Text> solicitações e eventos de formação, disponibilidade
          e bloqueios de agenda, aprovações.
        </li>
        <li>
          <Text strong>Registros de acesso e auditoria:</Text> data/hora, ação realizada e,
          quando aplicável, endereço IP e navegador — para segurança e prestação de contas.
        </li>
      </ul>

      <Title level={3}>3. Para que tratamos (finalidade)</Title>
      <Paragraph>
        Gestão das formações e da agenda dos formadores/coordenadores, verificação de
        disponibilidade e conflitos, fluxo de aprovação, publicação de eventos no calendário
        e comunicação com os envolvidos. O acesso é de colaboradores da organização.
      </Paragraph>

      <Title level={3}>4. Com que base legal</Title>
      <Paragraph>
        <Pendente>
          base legal específica a confirmar pelo jurídico. Por ser um sistema interno de
          colaboradores, tipicamente NÃO é consentimento — costuma ser execução de contrato,
          cumprimento de obrigação legal/regulatória e/ou legítimo interesse (arts. 7º e 11
          da LGPD). Confirmar o enquadramento por tipo de dado.
        </Pendente>
      </Paragraph>

      <Title level={3}>5. Com quem compartilhamos</Title>
      <Paragraph>
        Não vendemos seus dados. Compartilhamos com <Text strong>Google Calendar</Text> os
        dados necessários para publicar e notificar eventos de agenda (título, local, data e
        os e-mails dos participantes convidados). Não há outros compartilhamentos além dos
        estritamente necessários à operação e às obrigações legais.
      </Paragraph>

      <Title level={3}>6. Transferência internacional</Title>
      <Paragraph>
        A integração de calendário usa o Google, que pode processar dados fora do Brasil
        (art. 33 da LGPD), sob as salvaguardas contratuais e de segurança do próprio Google.
      </Paragraph>

      <Title level={3}>7. Por quanto tempo guardamos</Title>
      <ul>
        <li>Dados de cadastro: enquanto durar o vínculo/uso do sistema.</li>
        <li>Registros de auditoria/acesso: retenção alinhada à obrigação legal (Marco Civil, mínimo de 6 meses).</li>
        <li>Arquivos de importação com dados pessoais: expurgados automaticamente após o período de processamento.</li>
      </ul>
      <Paragraph type="secondary">
        Prazos exatos: <Pendente>confirmar/oficializar os prazos de retenção por categoria</Pendente>.
      </Paragraph>

      <Title level={3}>8. Como protegemos</Title>
      <Paragraph>
        Comunicação cifrada (TLS/HTTPS), backups criptografados, controle de acesso por papel
        (cada pessoa vê apenas o necessário), senhas armazenadas com hash e trilha de auditoria
        das operações sensíveis.
      </Paragraph>

      <Title level={3}>9. Seus direitos e como exercê-los</Title>
      <Paragraph>
        A LGPD (art. 18) garante, entre outros, os direitos de acesso, correção,
        portabilidade e eliminação. No próprio sistema, em <Text strong>“Meu perfil”</Text>,
        você pode:
      </Paragraph>
      <ul>
        <li><Text strong>Acessar</Text> seus dados de cadastro (CPF, e-mail, telefone, cargo).</li>
        <li><Text strong>Corrigir</Text> seu telefone de contato.</li>
        <li><Text strong>Exportar</Text> uma cópia dos seus dados (portabilidade), em JSON.</li>
      </ul>
      <Paragraph>
        Para <Text strong>exclusão/anonimização</Text> ou qualquer outra solicitação, procure
        o Encarregado: <Pendente>canal de contato do Encarregado</Pendente>. Responderemos nos
        prazos da LGPD.
      </Paragraph>

      <Title level={3}>10. Alterações</Title>
      <Paragraph>
        Esta política pode ser atualizada. Publicaremos a nova versão aqui, com a data de
        vigência. Dúvidas: <Pendente>canal de contato do Encarregado</Pendente>.
      </Paragraph>

      <Divider />
      <Paragraph type="secondary" style={{ fontSize: 12 }}>
        Documento em preenchimento pelo controlador e pelo Encarregado (DPO). Os trechos
        realçados como [A PREENCHER] ainda não têm valor jurídico definitivo.
      </Paragraph>
    </Typography>
  );
}
