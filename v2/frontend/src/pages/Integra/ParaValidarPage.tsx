/**
 * "Para validar no dia 7" (decisão do dono Q14, 24/11/2026): pauta da reunião de validação de 07/12/2026.
 *
 * Três partes:
 * 1. cada item marcado "sugestão" nos PDFs de requisitos (ICA e Semáforo) e cada ponto em aberto da ata
 *    de 23/11, com o que o protótipo fez por enquanto;
 * 2. de onde virá cada dado (o Aprender Sistema junta os dados de todos os módulos; nenhuma ferramenta
 *    mantém cadastro próprio);
 * 3. para quem vai cada resultado.
 *
 * Texto fixo, sem dado simulado. Sem nomes de pessoas reais: a ata veio de transcrição automática e o
 * protótipo só usa nomes fictícios. Listas e cartões (sem tabela): nada rola para o lado.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

const { Title } = Typography;

// ---------------------------------------------------------------- 1. sugestões e pontos em aberto

interface Ponto {
  titulo: string;
  /** Que tipo de item é e de onde saiu (PDF e seção, ou a ata). */
  origem: string;
  oQueDiz: string;
  prototipo: string;
  paraDecidir: string;
}

interface Tema {
  id: string;
  titulo: string;
  pontos: Ponto[];
}

const TEMAS: Tema[] = [
  {
    id: 'tema-acesso',
    titulo: 'Quem vê e quem decide',
    pontos: [
      {
        titulo: 'O coordenador vê a própria ficha do ICA?',
        origem: 'Sugestão do PDF do ICA (seção 1) que a reunião de 23/11 contrariou',
        oQueDiz:
          'O PDF sugere que o coordenador consulte o próprio ICA e a composição da carteira. Na reunião, ficou decidido que o ICA é só para gestores: o coordenador não vê nem a própria ficha.',
        prototipo:
          'Segue a reunião. Só entram na Integra os superusuários, as gerentes da Superintendência (NFP) e quem está lotado como Equipe ou Gerente na gerência SPE. A Diretoria entra quando a gerência dela estiver cadastrada no Aprender Sistema, o que ainda não aconteceu. Coordenador não abre nenhuma tela.',
        paraDecidir: 'Confirmar que a sugestão do PDF sai.',
      },
      {
        titulo: 'Quem aprova o remanejamento?',
        origem: 'PDF do ICA (seções 1 e 4) × decisão da reunião de 23/11',
        oQueDiz:
          'O PDF diz que a Líder do NFP aprova os remanejamentos. Na reunião, a Líder ficou só com papel consultivo, sem aprovação.',
        prototipo:
          'No simulador, quem tem acesso propõe, aprova e aplica, e aparece como "Você (demonstração)". Nos remanejamentos simulados dos semestres anteriores, quem aprovou aparece como "Líder do NFP", como no PDF.',
        paraDecidir: 'Quem aprova: a SPE, a gestora técnica ou outra pessoa? A Líder só é avisada?',
      },
      {
        titulo: 'Quem vê o registro do momento reservado com a Secretaria',
        origem: 'Sugestão do PDF do Semáforo (seção 1)',
        oQueDiz:
          'O registro é confidencial: a gestora de referência e a SPE veem; a sugestão é que a Líder do NFP também veja. O coordenador do município nunca vê.',
        prototipo:
          'O Semáforo chega na próxima entrega. No protótipo, quem tem acesso à Integra vê tudo (decisão de 24/11); os perfis ficam para a versão real.',
        paraDecidir: 'A Líder do NFP vê o momento reservado?',
      },
      {
        titulo: 'Painel do coordenador no Semáforo',
        origem: 'Sugestão do PDF do Semáforo (seção 7)',
        oQueDiz:
          'O coordenador veria os relatórios mensais a preencher e o resultado agregado da pesquisa dos seus municípios, sem o momento reservado e sem saber quem respondeu.',
        prototipo: 'Não entra: no protótipo, coordenador não acessa a Integra.',
        paraDecidir: 'Manter o painel? Se sim, por onde o coordenador entra, já que a Integra é só para gestores?',
      },
    ],
  },
  {
    id: 'tema-conta',
    titulo: 'A conta do ICA',
    pontos: [
      {
        titulo: 'Coordenador que vai dirigindo até o município',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz: 'A conta atual não considera se o coordenador vai dirigindo.',
        prototipo:
          'O tempo de deslocamento é do município (ida e volta a partir de Fortaleza, de avião ou de carro) e vale igual para qualquer coordenador. Petrolina-PE e Milagres-CE já estão como carro. Dirigir não soma nada a mais.',
        paraDecidir: 'Dirigir deve pesar mais? Por exemplo, as horas ao volante contarem em dobro, ou um campo próprio.',
      },
      {
        titulo: 'Frente é município × coleção ou município × coleção × segmento?',
        origem: 'Diferença entre o PDF do ICA (seção 2) e a ata de 23/11',
        oQueDiz:
          'O PDF conta 1 frente para cada município com cada coleção. A tabela de pesos da ata fala em município × coleção × segmento.',
        prototipo: 'Segue o PDF: cada coleção em cada município é 1 frente, com qualquer número de segmentos.',
        paraDecidir: 'Qual das duas vale?',
      },
      {
        titulo: 'Quem está sem municípios entra na conta de "Capacidade disponível"?',
        origem: 'Diferença entre o PDF do ICA (seção 3) e a ata de 23/11',
        oQueDiz:
          'O PDF diz que quem não tem município ativo fica com ICA 0 e aparece como "sem municípios", fora da média da equipe. A ata conta 17 coordenadores: 3 em Sobrecarga, 2 em Atenção, 6 adequados e 6 com capacidade disponível.',
        prototipo:
          'Segue o PDF: quem está sem municípios fica fora dos estratos e tem um cartão próprio no Painel. Nos dados simulados, um dos 17 está sem municípios, por isso o Painel mostra 5 com capacidade disponível e 1 sem municípios.',
        paraDecidir: 'Confirmar que quem está sem municípios fica fora dos estratos. Na equipe real, alguém está sem municípios hoje?',
      },
      {
        titulo: 'Alerta de Sobrecarga: só quem entra, ou também quem continua?',
        origem: 'PDF do ICA (seção 6) × fala da reunião de 23/11',
        oQueDiz:
          'O PDF manda avisar quando o coordenador entra em Sobrecarga (130 ou mais). Na reunião, o alerta foi lido como "coordenador em Sobrecarga".',
        prototipo:
          'Segue o PDF: o aviso "Entrou em Sobrecarga" compara com o cálculo anterior, que é o do semestre anterior ou, depois de um remanejamento ou de uma troca de pesos, o cálculo publicado do semestre. Quem já estava em Sobrecarga não recebe o aviso de novo e continua no alerta "Fora da meta", que vai só para a SPE, quando passa de 130 (a meta vai até 130). Com 130 exato, fica dentro da meta e sem alerta.',
        paraDecidir: 'Quem continua em Sobrecarga recebe o aviso de novo a cada recálculo? A gestora técnica e a Líder do NFP também recebem?',
      },
      {
        titulo: 'Publicação em até 5 dias úteis, depois da conferência da SPE',
        origem: 'Sugestão do PDF do ICA (seção 4)',
        oQueDiz:
          'Quando muda um contrato, uma coleção ou um status, o ICA é refeito na hora e publicado depois que a SPE confere, em até 5 dias úteis.',
        prototipo: 'Não há etapa de publicação: a conta é refeita na hora, a cada mudança na tela.',
        paraDecidir: 'Manter a conferência da SPE antes de publicar? E o prazo de 5 dias úteis?',
      },
    ],
  },
  {
    id: 'tema-pessoas',
    titulo: 'Pessoas e carteiras',
    pontos: [
      {
        titulo: 'Quem é a gestora de referência de cada município, e o acesso compartilhado',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz:
          'Cada município terá uma gestora de referência, responsável pelo relacionamento. Duas gestoras (Tema e Novo Lendo) dividiriam o acesso a parte dos municípios.',
        prototipo: 'Cada município tem uma gestora de referência só (nomes fictícios). Não há acesso compartilhado.',
        paraDecidir: 'Um município pode ter duas gestoras? Ou uma responde e a outra só consulta?',
      },
      {
        titulo: 'A gestora com 29 municípios fica sozinha?',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz: 'Uma gestora ficaria com 29 municípios; falou-se em ter um coordenador de referência para apoiar.',
        prototipo: 'Não existe o papel de coordenador de referência; cada município tem uma gestora só.',
        paraDecidir: 'Criar o papel de apoio ou dividir a carteira?',
      },
    ],
  },
  {
    id: 'tema-semaforo-prazos',
    titulo: 'Semáforo: coletas e prazos',
    pontos: [
      {
        titulo: 'Pesquisa respondida em até 10 dias após o envio',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'A pesquisa do articulador é bimestral, e a resposta vale se chegar em até 10 dias depois do envio.',
        prototipo: 'O Semáforo chega na próxima entrega, com este prazo, como no PDF.',
        paraDecidir: 'Confirmar os 10 dias.',
      },
      {
        titulo: 'Relatório mensal até o 5º dia útil do mês seguinte',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'O coordenador manda o relatório mensal até o 5º dia útil do mês seguinte.',
        prototipo: 'O Semáforo chega na próxima entrega, com este prazo, como no PDF.',
        paraDecidir: 'Confirmar o prazo.',
      },
      {
        titulo: 'Ata da reunião de escuta em até 5 dias úteis',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'A gestora de referência registra a ata da reunião de escuta em até 5 dias úteis.',
        prototipo: 'O Semáforo chega na próxima entrega, com este prazo, como no PDF.',
        paraDecidir: 'Confirmar o prazo.',
      },
    ],
  },
  {
    id: 'tema-semaforo-regras',
    titulo: 'Semáforo: regras da cor',
    pontos: [
      {
        titulo: 'Vários articuladores no mesmo município',
        origem: 'Sugestão do PDF do Semáforo (seção 3)',
        oQueDiz:
          'Com mais de uma resposta no município, o NPS é a média das notas, e o município conta como "respondeu" quando pelo menos um articulador responde no prazo.',
        prototipo: 'O Semáforo chega na próxima entrega seguindo esta regra.',
        paraDecidir: 'Confirmar a média e o "pelo menos um".',
      },
      {
        titulo: 'Indicador sem dado fica fora da regra do pior',
        origem: 'Sugestão do PDF do Semáforo (seção 3)',
        oQueDiz:
          'Se um indicador não tem dado no ciclo (por exemplo, nenhuma formação prevista), ele fica "sem dado" e não puxa a cor para baixo.',
        prototipo: 'O Semáforo chega na próxima entrega seguindo esta regra.',
        paraDecidir: 'Confirmar.',
      },
      {
        titulo: 'Município que não responde à pesquisa',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz:
          'Não responder é falta de compromisso ou insatisfação? Pelo PDF, não responder em um ciclo deixa o indicador amarelo; em dois ciclos seguidos, vermelho.',
        prototipo: 'O Semáforo chega na próxima entrega seguindo o PDF; o Comitê lê o caso e pode mudar a cor com justificativa.',
        paraDecidir: 'A regra do PDF basta, ou o "não respondeu" pede outro tratamento?',
      },
    ],
  },
  {
    id: 'tema-integra',
    titulo: 'A Integra e as outras ferramentas',
    pontos: [
      {
        titulo: 'Que outras ferramentas entram na Integra',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz: 'Os gerentes já usam outras ferramentas, como o Formar, o Avaliar e a frequência.',
        prototipo:
          'A Integra tem os 4 cartões combinados: ICA, Semáforo, DFF (no link atual) e Avaliação do Coordenador (em breve). Formar e Avaliar já têm link no sistema e podem virar cartões.',
        paraDecidir: 'Quais entram, e em que ordem?',
      },
      {
        titulo: 'Como avaliar a parte subjetiva da avaliação do gestor',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz: 'A avaliação do gestor tem uma parte objetiva (prazos e entregas) e uma subjetiva (qualidade das entregas).',
        prototipo: 'A Avaliação do Coordenador fica para depois do ICA e do Semáforo; o cartão aparece como "em breve".',
        paraDecidir: 'Notas, conceitos ou indicadores?',
      },
      {
        titulo: 'Filtrar na DFF os formadores que cada coordenador acompanhou',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz: 'A ideia é mandar o link da avaliação só para os formadores que cada coordenador acompanhou.',
        prototipo: 'Não entra nesta entrega: a DFF abre no link atual, em outra aba.',
        paraDecidir: 'A DFF registra quem acompanhou quem? Se sim, o Aprender Sistema pode ler esse vínculo.',
      },
    ],
  },
];

// ---------------------------------------------------------------- 2. de onde virá cada dado

type Onde = 'aprender' | 'dff' | 'logistica' | 'falta';

const ONDE: Record<Onde, { nome: string; fundo: string; texto: string }> = {
  aprender: { nome: 'Aprender Sistema', fundo: '#E3F0EC', texto: '#004B3D' },
  dff: { nome: 'DFF', fundo: '#EDE7F6', texto: '#4A2A7A' },
  logistica: { nome: 'Logística e FRV, quando migrarem', fundo: '#DCEBFA', texto: '#0B4A80' },
  falta: { nome: 'Não existe ainda: precisa ser cadastrado', fundo: '#FFF0C2', texto: '#6B4A00' },
};

interface Dado {
  dado: string;
  onde: Onde[];
  detalhe: string;
}

// Texto para a gestão: os nomes que a pessoa vê nas telas do sistema. O mapa técnico (para quem trocar
// a fonte simulada pela API) é: município = Municipio; coleção = ProjetoGeral; o que cada município recebe
// e o coordenador de cada um = PlanoFormacoes (.coordenadores); gerência e equipe = Gerencia e
// EquipeGerencia; professores e alunos = DATRegistro.professor_qtde e .aluno_qtde; cronograma =
// Solicitacao e Formacao. Ver `dados/tipos.ts`.
const DADOS_ICA: Dado[] = [
  { dado: 'Município (nome e UF)', onde: ['aprender'], detalhe: 'Cadastro de municípios do Aprender Sistema.' },
  {
    dado: 'Coleções e frentes',
    onde: ['aprender'],
    detalhe: 'As coleções já estão cadastradas; o que cada município recebe está no Plano Anual (menu Controle).',
  },
  {
    dado: 'Coordenador de cada município',
    onde: ['aprender'],
    detalhe: 'O coordenador de cada município no Plano Anual e a equipe de cada gerência.',
  },
  {
    dado: 'Coordenador: atuação e gestora técnica',
    onde: ['aprender'],
    detalhe: 'A gerência e a equipe dela. A atuação (Alfabetização + EI, AMMA, Educação Infantil) precisa ser conferida no cadastro.',
  },
  {
    dado: 'Professores em formação',
    onde: ['aprender'],
    detalhe: 'A quantidade de professores por segmento nos Registros de Turmas do DAT. A quantidade de alunos serve para conferir valor improvável.',
  },
  { dado: 'Estados (UFs)', onde: ['aprender'], detalhe: 'Sai da UF do município. Só a configuração original (v5) usa.' },
  { dado: 'Turmas de formação', onde: ['falta'], detalhe: 'Hoje não há contagem de turmas no sistema.' },
  {
    dado: 'Status ativo ou suspenso',
    onde: ['falta'],
    detalhe: 'O município não tem status de contrato nem a data da mudança. Suspenso não conta no ICA.',
  },
  {
    dado: 'Gestora de referência',
    onde: ['falta'],
    detalhe: 'Função nova, combinada em 23/11. É o mesmo cadastro para o ICA e o Semáforo.',
  },
  {
    dado: 'Tempo de deslocamento',
    onde: ['falta', 'logistica'],
    detalhe: 'Hoje está só no relatório da SPE (nov/2026). Quando a Logística e a FRV (pedido de viagem) migrarem, o tempo real pode sair delas.',
  },
  {
    dado: 'Pesos, versões e remanejamentos',
    onde: ['falta'],
    detalhe: 'Registro novo no Aprender Sistema, com autor, data e valor anterior (trilha de auditoria).',
  },
];

const DADOS_SEMAFORO: Dado[] = [
  {
    dado: 'Pesquisa do articulador',
    onde: ['falta'],
    detalhe: 'Os 6 itens, a nota NPS e se respondeu no prazo. Na versão real, link sem login; no protótipo, respondida na mesma tela.',
  },
  {
    dado: 'Cronograma cumprido',
    onde: ['aprender'],
    detalhe: 'Formações previstas e realizadas: as solicitações de formação e os acompanhamentos que já estão no sistema.',
  },
  {
    dado: 'Visitas previstas e realizadas',
    onde: ['logistica'],
    detalhe: 'O pedido de viagem da FRV, quando migrar, pode dizer que visitas aconteceram.',
  },
  {
    dado: 'Relatório mensal do coordenador',
    onde: ['falta'],
    detalhe: 'Formulário novo. A parte das formações pode vir preenchida com o que o Aprender Sistema já tem.',
  },
  { dado: 'Ocorrências', onde: ['falta'], detalhe: 'Registro do comercial e do relacionamento, num fluxo único.' },
  {
    dado: 'Reunião de escuta',
    onde: ['falta'],
    detalhe: 'Ata, participantes, encaminhamentos e o registro confidencial do momento reservado.',
  },
  {
    dado: 'Observação de formação',
    onde: ['dff'],
    detalhe: 'A observação já é feita na Plataforma DFF; o Aprender Sistema lê de lá.',
  },
  {
    dado: 'Vínculo formador × coordenador',
    onde: ['dff'],
    detalhe: 'Para a Avaliação do Coordenador: quais formadores cada coordenador acompanhou. A confirmar se a DFF registra.',
  },
  {
    dado: 'Coleções, coordenadores e gestora do município',
    onde: ['aprender', 'falta'],
    detalhe: 'Coleções e coordenadores vêm do Aprender Sistema; a gestora de referência ainda precisa ser cadastrada.',
  },
];

// ---------------------------------------------------------------- 3. para quem vai cada resultado

interface Destino {
  resultado: string;
  vaiPara: string;
}

const DESTINOS: Destino[] = [
  {
    resultado: 'ICA de cada coordenador',
    vaiPara:
      'Painéis do ICA na Integra; os indicadores da Líder do NFP no Semáforo (distribuição do ICA, meta entre 70 e 130); e, pelo Aprender Sistema, os outros módulos que precisarem.',
  },
  {
    resultado: 'Remanejamento aplicado',
    vaiPara:
      'Volta para a carteira no Aprender Sistema (Plano Anual), o mesmo cadastro que as outras telas usam. Não fica uma cópia na Integra.',
  },
  {
    resultado: 'Cor do Semáforo',
    vaiPara:
      'Comitê de Satisfação Municipal e gestora de referência (tarefas e prazos de cada cor); pelo Aprender Sistema, os outros módulos, como o comercial e o relacionamento.',
  },
  {
    resultado: 'Resposta do articulador',
    vaiPara: 'Semáforo e Avaliação do Coordenador ao mesmo tempo (combinado em 23/11).',
  },
  {
    resultado: 'Observação de formação e relatório de visita',
    vaiPara: 'PDI do coordenador na Plataforma DFF (PDF do Semáforo, seção 9).',
  },
];

// ---------------------------------------------------------------- tela

const PARTES = [
  { id: 'validar-pontos', titulo: 'Sugestões e pontos em aberto' },
  { id: 'validar-origem', titulo: 'De onde virá cada dado' },
  { id: 'validar-destino', titulo: 'Para quem vai cada resultado' },
] as const;

const CARTAO = 'rounded border border-[#8c8c8c] p-3';

function Etiqueta({ onde }: { onde: Onde }): JSX.Element {
  const o = ONDE[onde];
  return (
    <span className="inline-block rounded px-2 py-0.5 text-sm font-semibold" style={{ background: o.fundo, color: o.texto }}>
      {o.nome}
    </span>
  );
}

function ListaDeDados({ titulo, id, dados }: { titulo: string; id: string; dados: Dado[] }): JSX.Element {
  return (
    <section aria-labelledby={id} className="mt-6">
      <Title level={3} id={id} style={{ fontSize: 18 }}>
        {titulo}
      </Title>
      <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
        {dados.map((d) => (
          <li key={d.dado} className={CARTAO}>
            <Title level={4} style={{ fontSize: 16, marginBottom: 4 }}>
              {d.dado}
            </Title>
            <span className="mb-2 flex flex-wrap gap-2">
              {d.onde.map((o) => (
                <Etiqueta key={o} onde={o} />
              ))}
            </span>
            <p className="m-0">{d.detalhe}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function ParaValidarPage(): JSX.Element {
  return (
    <section aria-labelledby="integra-titulo-tela" className="max-w-5xl">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Para validar no dia 7
      </Title>
      <p>
        Pauta da reunião de validação de 07/12/2026. Aqui estão os itens marcados como <strong>sugestão</strong> nos
        documentos de requisitos do ICA e do Semáforo (não estavam na proposta v5) e os pontos que ficaram em aberto
        na reunião de 23/11. Para cada um, o que o protótipo fez por enquanto e o que falta decidir.
      </p>
      <p className="mb-4">
        <Link to="/integra">Voltar para a Integra</Link>
      </p>

      <nav aria-label="Nesta página" className="mb-6 print:hidden">
        <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0">
          {PARTES.map((p) => (
            <li key={p.id}>
              <a href={`#${p.id}`}>{p.titulo}</a>
            </li>
          ))}
        </ul>
      </nav>

      <section aria-labelledby={PARTES[0].id}>
        <Title level={2} id={PARTES[0].id} style={{ fontSize: 22 }}>
          {PARTES[0].titulo}
        </Title>
        {TEMAS.map((tema) => (
          <section key={tema.id} aria-labelledby={tema.id} className="mt-6">
            <Title level={3} id={tema.id} style={{ fontSize: 18 }}>
              {tema.titulo}
            </Title>
            <div className="grid gap-3">
              {tema.pontos.map((p) => (
                <article key={p.titulo} className={CARTAO}>
                  <Title level={4} style={{ fontSize: 16, marginBottom: 4 }}>
                    {p.titulo}
                  </Title>
                  <p className="mb-2 text-sm italic">{p.origem}</p>
                  <dl className="m-0 grid gap-y-1">
                    <dt className="font-semibold">O que dizem</dt>
                    <dd className="m-0 mb-1">{p.oQueDiz}</dd>
                    <dt className="font-semibold">Como o protótipo resolveu por enquanto</dt>
                    <dd className="m-0 mb-1">{p.prototipo}</dd>
                    <dt className="font-semibold">Para decidir</dt>
                    <dd className="m-0">{p.paraDecidir}</dd>
                  </dl>
                </article>
              ))}
            </div>
          </section>
        ))}
      </section>

      <section aria-labelledby={PARTES[1].id} className="mt-10">
        <Title level={2} id={PARTES[1].id} style={{ fontSize: 22 }}>
          {PARTES[1].titulo}
        </Title>
        <p>
          O Aprender Sistema junta os dados de todos os módulos e entrega para as ferramentas: nenhuma ferramenta tem
          cadastro próprio. O protótipo usa dados simulados com o mesmo formato do cadastro real, para que trocar o
          simulado pelo real seja só trocar a fonte. Abaixo, onde cada dado está hoje. Os marcados &ldquo;Não existe
          ainda&rdquo; são a lista do que precisa ser cadastrado para a versão real.
        </p>
        <ListaDeDados titulo="ICA" id="validar-origem-ica" dados={DADOS_ICA} />
        <ListaDeDados titulo="Semáforo" id="validar-origem-semaforo" dados={DADOS_SEMAFORO} />
      </section>

      <section aria-labelledby={PARTES[2].id} className="mt-10">
        <Title level={2} id={PARTES[2].id} style={{ fontSize: 22 }}>
          {PARTES[2].titulo}
        </Title>
        <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {DESTINOS.map((d) => (
            <li key={d.resultado} className={CARTAO}>
              <Title level={3} style={{ fontSize: 16, marginBottom: 4 }}>
                {d.resultado}
              </Title>
              <p className="m-0">
                <strong>Vai para:</strong> {d.vaiPara}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}
