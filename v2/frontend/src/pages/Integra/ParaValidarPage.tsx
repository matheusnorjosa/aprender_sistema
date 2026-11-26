/**
 * "Para validar no dia 7" (decisão do dono Q14, 24/11/2026): pauta da reunião de validação de 07/12/2026.
 *
 * Quatro partes:
 * 1. cada item marcado "sugestão" nos PDFs de requisitos (ICA e Semáforo), cada ponto em aberto da ata
 *    de 23/11, as leituras das regras do Semáforo onde o PDF não fecha a conta (`semaforo/regras.ts`) e as
 *    contradições do relatório de deslocamento, com o que o protótipo fez por enquanto;
 * 2. quem vê o quê na versão real: a matriz de cargos × telas de `quemVe.ts`, com o que já foi decidido e
 *    as perguntas do mapa de cargos que ainda estão em aberto;
 * 3. de onde virá cada dado (o Aprender Sistema junta os dados de todos os módulos; nenhuma ferramenta
 *    mantém cadastro próprio);
 * 4. para quem vai cada resultado.
 *
 * Texto fixo, sem dado simulado. Sem nomes de pessoas reais: a ata veio de transcrição automática e o
 * protótipo só usa nomes fictícios; a matriz usa só papéis. Só listas e cartões (a matriz também: um
 * cartão por tela), e a página nunca rola para o lado.
 *
 * As perguntas que o dono respondeu em 25/11 (decisões 30 a 57, `liberacao/relatorios/integra_decisoes_2026-11-24.md`)
 * ficam nos cartões com o selo "Decidido (decisão N)": o par "Para decidir" vira "Decidido", com a resposta. As
 * leituras que o protótipo teve de fazer para aplicar essas respostas continuam como pontos para decidir.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';
import { BRAND_COLORS } from '../../contexts/ThemeContext';
import { ACOES, DECIDIDO, PAPEIS, PERGUNTAS_EM_ABERTO, QUEM_VE, TELAS, type Acao, type Celula, type Modulo } from './quemVe';

const { Title } = Typography;

// ---------------------------------------------------------------- 1. sugestões e pontos em aberto

interface Ponto {
  titulo: string;
  /** Que tipo de item é e de onde saiu (PDF e seção, ou a ata). */
  origem: string;
  oQueDiz: string;
  prototipo: string;
  /** A pergunta como foi feita; no cartão decidido, a resposta do dono fica no lugar dela. */
  paraDecidir: string;
  /** A pergunta já respondida pelo dono: o número da decisão e a resposta, em palavras simples. */
  decidido?: { numero: number; resposta: string };
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
          'Segue a decisão 21 (em "Já decidido", abaixo): o coordenador não entra na Integra e não vê o ICA, nem a própria ficha. Só entram na Integra os superusuários, as gerentes da Superintendência (NFP) e quem está lotado como Equipe ou Gerente na gerência SPE. A Diretoria entra quando a gerência dela estiver cadastrada no Aprender Sistema, o que ainda não aconteceu.',
        paraDecidir: 'Nada: a decisão 21 já fechou este ponto. Ele fica na lista porque tira uma sugestão do PDF.',
      },
      {
        titulo: 'Quem aprova o remanejamento?',
        origem: 'PDF do ICA (seções 1 e 4) × decisão da reunião de 23/11',
        oQueDiz:
          'O PDF diz que a Líder do NFP aprova os remanejamentos. Na reunião, a Líder ficou só com papel consultivo, sem aprovação.',
        prototipo:
          'Segue a decisão 20 (em "Já decidido", abaixo): a gestora pedagógica propõe e a SPE aplica; a Líder do NFP só consulta. No simulador, o botão é "Aprovar (SPE)", e quem tem acesso aparece como "Você (demonstração)". Nos remanejamentos simulados dos semestres anteriores, quem aprovou ainda aparece como "Líder do NFP", como no PDF.',
        paraDecidir: 'Quem aprova já está decidido. Falta só: a Líder do NFP é avisada de cada remanejamento aplicado?',
      },
      {
        titulo: 'Quem vê o registro do momento reservado com a Secretaria',
        origem: 'Sugestão do PDF do Semáforo (seção 1)',
        oQueDiz:
          'O registro é confidencial: a gestora de referência e a SPE veem; a sugestão é que a Líder do NFP também veja. O coordenador do município nunca vê.',
        prototipo:
          'A queixa do momento reservado entra junto com a reunião de escuta, na tela Relatório mensal e formulários. Ela conta nas ocorrências do município e aparece na ficha dele como "Momento reservado (confidencial)". No protótipo, quem tem acesso à Integra vê tudo (decisão de 24/11); quem vê na versão real está em "Quem vê o quê", abaixo.',
        paraDecidir: 'A Líder do NFP vê o momento reservado?',
      },
      {
        titulo: 'Painel do coordenador no Semáforo',
        origem: 'Sugestão do PDF do Semáforo (seção 7)',
        oQueDiz:
          'O coordenador veria os relatórios mensais a preencher e o resultado agregado da pesquisa dos seus municípios, sem o momento reservado e sem saber quem respondeu.',
        prototipo:
          'Segue a decisão 21: o coordenador não entra na Integra; o relatório mensal e as tarefas dele no amarelo ficam numa tela à parte do sistema. Essa tela ainda não existe no protótipo: o relatório mensal está na tela Relatório mensal e formulários, preenchido por quem entra na Integra.',
        paraDecidir: 'O que mais entra na tela à parte do coordenador? Por exemplo, o resultado agregado da pesquisa dos municípios dele, sem o momento reservado e sem saber quem respondeu.',
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
        paraDecidir: 'Quem continua em Sobrecarga recebe o aviso de novo a cada recálculo? A gestora pedagógica e a Líder do NFP também recebem?',
      },
      {
        titulo: 'Publicação em até 5 dias úteis, depois da conferência da SPE',
        origem: 'Sugestão do PDF do ICA (seção 4)',
        oQueDiz:
          'Quando muda um projeto, uma coleção ou um status, o ICA é refeito na hora e publicado depois que a SPE confere, em até 5 dias úteis.',
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
        prototipo:
          'Não há envio de link no protótipo, então o prazo é fixo: vale a resposta até o dia 20 do segundo mês do ciclo (no ciclo de novembro e dezembro, até 20/12). A tela da pesquisa mostra esse prazo. Contar 10 dias a partir do envio fica para a versão real, quando houver o link.',
        paraDecidir: 'Confirmar os 10 dias a partir do envio.',
      },
      {
        titulo: 'Relatório mensal até o 5º dia útil do mês seguinte',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'O coordenador manda o relatório mensal até o 5º dia útil do mês seguinte.',
        prototipo:
          'O relatório entra sem prazo e sem aviso de atraso, mas só para os meses do ciclo atual, até o mês corrente. Assim, o mês em andamento já pode entrar antes de o mês terminar, e o relatório do último mês de um ciclo não entra depois que o ciclo vira. A ocorrência tem a mesma trava: a ocorrência de um ciclo que já fechou não pode ser registrada depois. As formações e visitas realizadas sobre as previstas dão o cronograma cumprido do ciclo.',
        paraDecidir:
          'Confirmar o prazo. O relatório do último mês do ciclo pode entrar no começo do ciclo seguinte, até o 5º dia útil? O mês em andamento pode entrar antes de terminar? E a ocorrência de um ciclo que já fechou pode ser registrada depois, se ela conta na cor do ano (decisão 32)?',
      },
      {
        titulo: 'Ata da reunião de escuta em até 5 dias úteis',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'A gestora de referência registra a ata da reunião de escuta em até 5 dias úteis.',
        prototipo:
          'A reunião é marcada antes, na tela Relatório mensal e formulários (a data pode ser depois de hoje). A ata, com o que ficou combinado e o momento reservado, é registrada depois, até 5 dias úteis após a reunião. Passado o prazo, a ficha do município e o painel da gestora mostram "ata atrasada".',
        paraDecidir: 'Confirmar o prazo.',
        decidido: {
          numero: 48,
          resposta: 'A reunião de escuta é marcada antes, e a ata registrada até 5 dias úteis depois; passado o prazo, "ata atrasada".',
        },
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
        prototipo:
          'A pesquisa é por projeto: cada projeto do município tem a sua resposta no ciclo, e o mesmo articulador em dois projetos responde uma vez por projeto (a segunda resposta do mesmo projeto é recusada). Como a média e o NPS do município somam os projetos está no ponto "Média e NPS do município", abaixo. O NPS é a média das notas, e a tela mostra também a maior e a menor. O município respondeu quando cada projeto respondeu no prazo: vale o pior projeto.',
        paraDecidir: 'Confirmar a média e o "pelo menos um".',
        decidido: {
          numero: 51,
          resposta:
            'A pesquisa é por projeto: cada projeto pode ter o seu articulador; se for o mesmo, ele responde uma por projeto. O NPS mostra a maior nota, a menor e a média, e a cor sai da média (decisão 31).',
        },
      },
      {
        titulo: 'Indicador sem dado fica fora da regra do pior',
        origem: 'Sugestão do PDF do Semáforo (seção 3)',
        oQueDiz:
          'Se um indicador não tem dado no ciclo (por exemplo, nenhuma formação prevista), ele fica "sem dado" e não puxa a cor para baixo.',
        prototipo:
          'Segue esta regra: o indicador sem dado aparece escrito "Sem dado" e não conta para a cor. Isso vale para a média, o NPS, o cronograma (nada previsto no período) e a resposta à pesquisa. Ocorrências nunca ficam sem dado: nenhuma ocorrência é verde.',
        paraDecidir: 'Confirmar.',
      },
      {
        titulo: 'Município que não responde à pesquisa',
        origem: 'Ponto em aberto da reunião de 23/11',
        oQueDiz:
          'Não responder é falta de compromisso ou insatisfação? Pelo PDF, não responder em um ciclo deixa o indicador amarelo; em dois ciclos seguidos, vermelho.',
        prototipo:
          'Segue o PDF: um ciclo sem resposta deixa o indicador "Resposta à pesquisa" amarelo; dois seguidos, vermelho. Enquanto o prazo está aberto e ninguém respondeu, ele fica "sem dado", e não amarelo. Sem resposta, a média e o NPS também ficam sem dado, para a mesma falta não pesar duas vezes. O Comitê confirma a cor e pode mudá-la, com justificativa.',
        paraDecidir: 'A regra do PDF basta, ou o "não respondeu" pede outro tratamento?',
      },
    ],
  },
  {
    // Leituras de `semaforo/regras.ts` onde o PDF não fecha a conta.
    id: 'tema-semaforo-leituras',
    titulo: 'Semáforo: como o protótipo leu o PDF',
    pontos: [
      {
        titulo: 'Média, NPS e cronograma: a cor sai do número exato',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 3) não fecha a conta',
        oQueDiz:
          'O PDF dá as faixas com números redondos (média 4,0 ou mais é verde e 3,0 a 3,9 é amarelo; cronograma 90% ou mais é verde e 70% a 89% é amarelo) e não diz o que fazer com um valor no meio, como 3,95 ou 89,5%.',
        prototipo:
          'A cor sai do número exato, sem arredondar: 3,95 é amarelo e 89,5% é amarelo. A tela mostra 2 casas (3,95 e 89,50%), para o número que aparece ser o que deu a cor. As faixas ficam escritas sem buraco: de 3,0 a menos de 4,0; de 70% a menos de 90%.',
        paraDecidir: 'Confirmar que vale o número que aparece na tela.',
        decidido: { numero: 30, resposta: 'A cor sai do número exato, não do arredondado: 3,95 é amarelo; 89,5% é amarelo. A tela mostra 2 casas.' },
      },
      {
        titulo: 'NPS: média das notas, e as notas quebradas',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 3) não fecha a conta',
        oQueDiz:
          'O PDF usa a média das notas de 0 a 10, e não o NPS de costume (quem dá 9 ou 10 menos quem dá 0 a 6). As faixas são: 9 ou 10 é verde, 7 ou 8 é amarelo, 0 a 6 é vermelho.',
        prototipo:
          'Segue a média do PDF, com o número exato: 8,5 é amarelo; 6,9 é vermelho. A ficha do município, os Indicadores da Líder e a planilha mostram a maior nota, a menor e a média.',
        paraDecidir: 'Confirmar a média e o corte das notas quebradas.',
        decidido: { numero: 31, resposta: 'A tela mostra a maior nota, a menor e a média; a cor sai da média (8,5 é amarelo).' },
      },
      {
        titulo: 'Ocorrências no trimestre: que trimestre?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 3) não fecha a conta',
        oQueDiz: 'O indicador conta as ocorrências "no trimestre", mas o ciclo do Semáforo é de dois meses.',
        prototipo:
          'Contam desde a 1ª formação do ano no município (o mês vem do relatório mensal) até a data da conta, e zeram em janeiro. Nada é apagado: as ocorrências dos anos anteriores e as de antes da 1ª formação continuam na ficha do município, marcadas como "não conta na cor".',
        paraDecidir: '3 meses corridos ou trimestre do calendário?',
        decidido: {
          numero: 32,
          resposta:
            'As ocorrências contam desde a 1ª formação do ano no município e zeram no ano seguinte; o histórico fica guardado (decisão 57: zerar uma contagem nunca apaga dado).',
        },
      },
      {
        titulo: 'Prazos das tarefas: horas, dias corridos e dias úteis',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz:
          'No vermelho: contato em 48 h, reunião com a Secretaria em 5 dias, plano de ação em 15 dias e devolutiva em 30 dias. No amarelo: contato com o articulador em até 10 dias úteis.',
        prototipo:
          'Os prazos contam em dias úteis, de segunda a sexta, a partir do dia em que a cor é publicada (que não conta). Feriado em dia de semana conta como dia útil, pela opção que o dono escolheu (ver o ponto "Feriados contam como dia útil nos prazos?", abaixo). O contato com o articulador municipal vence em 2 dias úteis; a reunião com a Secretaria, em 5; o plano de ação, em 15; a devolutiva, em 30. Uma cor publicada na sexta-feira 04/12/2026 dá o contato na terça, 08/12/2026, e a reunião com a Secretaria na sexta, 11/12/2026.',
        paraDecidir: 'Os prazos em dias são corridos ou úteis? Feriados contam?',
        decidido: {
          numero: 33,
          resposta:
            'Prazos em dias úteis (segunda a sexta): reunião com a Secretaria em 5, plano de ação em 15, devolutiva em 30. O "contato em 48 h" vira 2 dias úteis (decisão 34).',
        },
      },
      {
        titulo: '"No bimestre" e "no semestre": a partir de quando?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz: 'A observação de uma formação (amarelo) vale "no bimestre", e a visita técnica (vermelho), "no semestre".',
        prototipo:
          'Viraram 2 e 6 meses depois da publicação. Quando o dia não existe no mês final, vale o último dia do mês: 31/12/2026 mais 2 meses dá 28/02/2027, um domingo, e o prazo passa para a segunda, 01/03/2027 (ver o ponto do prazo em meses que cai no fim de semana, abaixo).',
        paraDecidir: 'O prazo conta da publicação ou vai até o fim do bimestre ou do semestre do calendário?',
        decidido: { numero: 35, resposta: '"No bimestre" e "no semestre" contam a partir da publicação da cor (2 e 6 meses).' },
      },
      {
        titulo: 'Três amarelos também mudam a cor na hora?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 4) não fecha a conta',
        oQueDiz:
          'Um indicador em vermelho deixa o município vermelho na hora, e três amarelos no mesmo ciclo também valem vermelho. A tabela de alertas diz "Município passa a vermelho: na hora", sem separar os dois casos.',
        prototipo:
          'Três amarelos no mesmo ciclo mudam a cor em vigor para vermelho na hora, como um indicador em vermelho: o alerta sai e as tarefas do vermelho começam. A SPE decide se convoca o Comitê extraordinário; o Comitê confirma ou desfaz depois.',
        paraDecidir: 'Três amarelos também chamam o Comitê extraordinário, ou esperam o fim do ciclo?',
        decidido: { numero: 39, resposta: 'Três amarelos no mesmo ciclo também viram vermelho na hora.' },
      },
      {
        titulo: 'A volta ao verde depois de um alerta',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 4) não fecha a conta',
        oQueDiz: 'O município só volta ao verde depois de 2 ciclos seguidos sem alerta.',
        prototipo:
          'A contagem parte da cor que o Comitê publicou no ciclo anterior. Se foi amarelo ou vermelho, o município fica amarelo "em recuperação" até somar 2 ciclos seguidos sem alerta. Só conta ciclo fechado: o ciclo em andamento (com a pesquisa ainda no prazo) não soma como ciclo sem alerta, e até ele fechar continua sugerida a cor publicada. No ciclo em andamento, a cor sugerida só muda na hora para piorar: um vermelho, ou três amarelos, vale na hora (e muda também a cor em vigor), e um amarelo também, se a cor publicada era verde. Sair do vermelho espera o ciclo fechar. Se o Comitê publicou verde, volta direto. Indicador sem dado não conta como alerta.',
        paraDecidir:
          'Confirmar os 2 ciclos, que a contagem parte da cor publicada pelo Comitê e que o ciclo em andamento só conta quando fechar.',
        decidido: {
          numero: 45,
          resposta:
            'Volta ao verde depois de 2 ciclos fechados seguidos sem alerta, contados da cor publicada; o ciclo em andamento só conta ao fechar.',
        },
      },
      {
        titulo: 'Quem faz cada tarefa de cada cor',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz:
          'O PDF diz quem age em cada cor, e não em cada tarefa. No vermelho, o "contato em 48 h" não diz com quem.',
        prototipo:
          'As tarefas do vermelho ficam com as duas gestoras juntas, a de referência e a pedagógica. A primeira tarefa do vermelho se chama "Contato com o articulador municipal", em 2 dias úteis. A pesquisa a cada 2 meses e o acompanhamento a cada 15 dias aparecem só como texto. A reunião de escuta tem situação: o painel da gestora mostra a que está a agendar pela janela de 6 ou 3 meses, e a Líder mede quem está em dia.',
        paraDecidir: 'Quem faz cada tarefa? O contato em 48 h é com quem?',
        decidido: {
          numero: 36,
          resposta:
            'As tarefas do vermelho ficam com as duas gestoras juntas, a de referência e a pedagógica. O contato inicial do vermelho é com o articulador municipal (decisão 37).',
        },
      },
      {
        titulo: 'Aviso quando o município piora para amarelo',
        origem: 'Leitura do protótipo: a lista de alertas do PDF do Semáforo (seção 8) não tem essa linha',
        oQueDiz:
          'A tabela de alertas do PDF diz quem recebe o aviso quando o município passa a vermelho, mas não tem linha para quando ele passa a amarelo.',
        prototipo:
          'Quando o município piora para amarelo, a tela de registro mostra o aviso para quem age no amarelo (a gestora de referência e os coordenadores dos projetos do município) e para a SPE. Nada é enviado no protótipo.',
        paraDecidir: 'Manter o aviso de piora para amarelo?',
        decidido: { numero: 52, resposta: 'Manter o aviso quando o município piora para amarelo.' },
      },
      {
        titulo: 'Quando o Comitê publica a cor',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seção 6) não marca o dia',
        oQueDiz:
          'O Comitê ordinário se reúne depois que a pesquisa do ciclo fecha. No vermelho imediato, o sistema muda a cor na hora, avisa a gestora de referência e a SPE e permite convocar o Comitê em caráter extraordinário.',
        prototipo:
          'O Comitê ordinário se reúne na data marcada pela SPE a cada ciclo: na tela do Comitê, a SPE marca a data do próximo. Nos dados simulados, cada ciclo fechado foi publicado numa sexta-feira depois do fim do ciclo (o de setembro e outubro, em 06/11/2026), e o ordinário do ciclo atual está marcado para 08/01/2027. O extraordinário é convocado a critério da SPE, por um botão na tela do Comitê: o vermelho na hora de Horizonte-CE foi confirmado em reunião extraordinária em 02/12/2026.',
        paraDecidir: 'Em que dia o Comitê publica? Todo vermelho imediato chama reunião extraordinária?',
        decidido: {
          numero: 40,
          resposta:
            'O Comitê ordinário se reúne em data marcada pela SPE a cada ciclo. O extraordinário é convocado a critério da SPE (decisão 41).',
        },
      },
      {
        titulo: 'Vermelho imediato: a cor em vigor muda na hora ou espera o Comitê?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 4) diz as duas coisas',
        oQueDiz:
          'No vermelho imediato, o PDF diz: "O sistema muda a cor na hora, avisa a gestora de referência e a SPE e permite convocar o Comitê em caráter extraordinário". Na atualização da cor, diz: "O sistema calcula uma cor sugerida; o Comitê confirma e publica".',
        prototipo:
          'A cor em vigor muda na hora para vermelho, na data do dado que disparou (um indicador em vermelho ou três amarelos), e as tarefas do vermelho começam nessa data; nunca antes da decisão que estava em vigor (ver o ponto "Dado registrado com atraso", abaixo). O Comitê confirma (as tarefas seguem) ou desfaz: nesse caso, as tarefas abertas do vermelho ficam "canceladas pelo Comitê", e as feitas continuam registradas.',
        paraDecidir: 'No vermelho imediato, a cor em vigor muda sozinha, antes do Comitê? Se sim, as tarefas do vermelho já nascem nessa hora?',
        decidido: {
          numero: 38,
          resposta:
            'O vermelho imediato muda a cor oficial na hora, e as tarefas começam; o Comitê confirma ou desfaz depois. Se desfaz, as tarefas abertas ficam "canceladas pelo Comitê", e as feitas continuam registradas (decisão 42).',
        },
      },
      {
        titulo: 'Mesma cor confirmada de novo: as tarefas abrem de novo?',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz:
          'O PDF lista as tarefas de cada cor, mas não diz o que acontece quando o Comitê confirma a mesma cor no ciclo seguinte.',
        prototipo:
          'Quando a mesma cor é publicada de novo num ciclo seguinte, o sistema reabre todas as tarefas da cor, e as abertas da publicação anterior ficam "substituídas", guardadas na ficha do município. No mesmo ciclo, confirmar a cor que já vale não mexe nas tarefas.',
        paraDecidir: 'Confirmar a mesma cor abre de novo as tarefas da cor?',
        decidido: { numero: 43, resposta: 'A mesma cor confirmada de novo reabre todas as tarefas da cor.' },
      },
      {
        titulo: 'O amarelo "em recuperação" recebe as tarefas do amarelo',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seções 4 e 5) não fecha a conta',
        oQueDiz:
          'O município que sai do vermelho fica amarelo "em recuperação" até somar 2 ciclos sem alerta. O PDF dá as tarefas do amarelo, mas não diz se elas valem também para quem está em recuperação.',
        prototipo:
          'O amarelo "em recuperação" recebe as mesmas tarefas do amarelo: contato com o articulador em até 10 dias úteis e observação de uma formação no bimestre.',
        paraDecidir: 'O amarelo em recuperação tem as tarefas do amarelo, outras mais leves ou nenhuma?',
        decidido: { numero: 44, resposta: 'O amarelo "em recuperação" recebe as tarefas do amarelo.' },
      },
      {
        titulo: 'Um relatório mensal por município ou por coordenador?',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seção 2) não fecha a conta',
        oQueDiz:
          'O relatório mensal é do coordenador. Alguns municípios têm mais de um projeto, cada um com o seu coordenador.',
        prototipo:
          'Cada projeto do município manda o seu relatório mensal, com as formações e as visitas dele; cada projeto tem o seu cronograma e a sua cor, e na cor do município entra o pior projeto. A tela do relatório mostra o cronograma de cada projeto e o do município. Até o critério de cada projeto chegar, todos usam a régua do PDF (ver o ponto "Cronograma por projeto", abaixo).',
        paraDecidir: 'Cada coordenador manda o seu relatório? Se sim, como juntar os números no cronograma do município?',
        decidido: {
          numero: 46,
          resposta:
            'Cada projeto da Aprender Editora contratado pelo município tem o seu coordenador, as suas formações e o seu relatório mensal. Cada projeto tem o seu cronograma e a sua cor; na cor do município entra o pior. O critério de cada projeto o dono define depois.',
        },
      },
      {
        titulo: 'O "cronograma confirmado" da reunião de escuta entra na conta?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (coleta 4) não fecha a conta',
        oQueDiz: 'Na reunião de escuta (coleta 4), a gestora registra se o cronograma foi confirmado com a Secretaria.',
        prototipo:
          'A confirmação aparece na ficha do município, mas não entra na conta: o cronograma cumprido usa só as formações e as visitas realizadas sobre as previstas dos relatórios mensais. A formação adiada de comum acordo é só observação.',
        paraDecidir: 'A confirmação muda o número do cronograma ou só ajuda a leitura do Comitê?',
        decidido: { numero: 47, resposta: 'Formação adiada de comum acordo é só observação: não muda o número do cronograma.' },
      },
      {
        titulo: 'Os indicadores da Líder do NFP que o protótipo não media',
        origem: 'Lacuna do protótipo: o PDF do Semáforo (seção 7) lista, o protótipo não calculava',
        oQueDiz:
          'Para a Líder do NFP, o PDF lista: satisfação média e NPS por município, coordenador, gestora e projeto; reuniões de escuta no período (meta 100%); taxa de resposta à pesquisa (meta 80% ou mais); tempo médio de resposta a ocorrências (meta 48 h ou menos); municípios em vermelho com plano de ação no prazo; convergência entre a pesquisa e as ocorrências; e a distribuição do ICA (meta entre 70 e 130).',
        prototipo:
          'A tela Indicadores da Líder mostra todos: a taxa de resposta (por projeto), as reuniões no período, a satisfação média e o NPS (por projeto, por coordenador e por gestora na tela; por município na planilha), o plano de ação no prazo, a distribuição do ICA, o tempo médio de resposta às ocorrências contra a meta de 48 h (a ocorrência guarda quando foi registrada e quando foi respondida) e a convergência entre a pesquisa e as ocorrências, com a lista dos municípios que divergem.',
        paraDecidir:
          'Como medir a convergência? A ocorrência passa a guardar quando foi respondida? A pesquisa pergunta o projeto avaliado?',
        decidido: {
          numero: 49,
          resposta:
            'Medir a convergência e listar os municípios que divergem. Medir o tempo de resposta: a ocorrência guarda quando foi respondida, e a meta é 48 h (decisão 50). A pesquisa é por projeto (decisão 51).',
        },
      },
      {
        titulo: 'Painel da gestora: atas a registrar',
        origem: 'Lacuna do protótipo: o PDF do Semáforo (seção 7) lista, o protótipo não acompanha',
        oQueDiz:
          'O painel da gestora de referência mostra as pendências da carteira: pesquisas sem resposta, reuniões a agendar e atas a registrar.',
        prototipo:
          'O painel mostra as pesquisas sem resposta no ciclo atual (por projeto), as reuniões de escuta a agendar e as já marcadas, e as atas a registrar e atrasadas, a atrasada primeiro (a ata vai até 5 dias úteis depois da reunião).',
        paraDecidir: 'A reunião de escuta é marcada antes e a ata registrada depois (com o prazo de 5 dias úteis)?',
        decidido: {
          numero: 48,
          resposta: 'A reunião de escuta é marcada antes e a ata registrada até 5 dias úteis depois; passado o prazo, o painel mostra "ata atrasada".',
        },
      },
      // Leituras do protótipo para as decisões de 25/11 (32, 38 a 43, 46 e 49), onde a resposta não fecha um detalhe.
      {
        titulo: 'Ocorrências do ano: a partir de que dia conta?',
        origem: 'Leitura do protótipo: decisão 32 (ocorrências desde a 1ª formação do ano)',
        oQueDiz: 'As ocorrências contam desde a 1ª formação do ano no município e zeram no ano seguinte; o histórico fica guardado.',
        prototipo:
          'O relatório mensal diz o mês da formação, mas não o dia. A contagem começa no dia 1º do mês da 1ª formação realizada no ano. Antes dela, nada conta: o município fica verde nesse indicador, e a ocorrência continua guardada na ficha.',
        paraDecidir: 'Confirmar o dia 1º do mês. Quando o sistema tiver a data de cada formação, a contagem começa nesse dia?',
      },
      {
        titulo: 'Ocorrências do ano: a régua de 1 e 2 vale o ano inteiro?',
        origem: 'Leitura do protótipo: decisão 32 (ocorrências do ano) com os limites do PDF do Semáforo (seção 3), pensados para um trimestre',
        oQueDiz:
          'O PDF dá os limites: 1 ocorrência leve é amarelo; 2 ou mais, ou 1 reclamação, é vermelho. Eles eram para um trimestre. Com a decisão 32, as ocorrências contam desde a 1ª formação do ano até dezembro.',
        prototipo:
          'Os limites continuam os mesmos, agora para o ano inteiro. Assim, uma ocorrência leve deixa o indicador amarelo até janeiro, e duas no ano dão vermelho na hora (decisão 38), mesmo com meses de distância entre elas. O "volta ao verde depois de 2 ciclos sem alerta" (decisão 45) não acontece enquanto a ocorrência contar. Maringá-PR mostra isso: o Comitê publicou verde em 06/11 por causa de um pedido de material já resolvido, e no ciclo atual a cor sugerida voltou a amarelo pela mesma ocorrência. O Comitê precisa alterar a cor de novo a cada ciclo. O mesmo vale para os três amarelos "no mesmo ciclo" (decisão 39): a ocorrência de outro ciclo conta como um deles. Pereiro-CE mostra isso: a ocorrência leve de 06/06/2026 ainda deixa o indicador de ocorrências amarelo no ciclo atual; se a pesquisa chegar com a média e o NPS em amarelo, são três amarelos, e o vermelho vale na hora, com as tarefas do vermelho.',
        paraDecidir:
          'Os limites de 1 e 2 ocorrências continuam valendo para o ano inteiro, ou mudam? Por exemplo: as leves contam só no ciclo, e as reclamações no ano. E a ocorrência de outro ciclo conta como amarelo "no mesmo ciclo" para os três amarelos que dão vermelho na hora?',
      },
      {
        titulo: 'Município sem formação registrada no ano: a reclamação não conta?',
        origem: 'Leitura do protótipo: decisão 32 (ocorrências desde a 1ª formação do ano)',
        oQueDiz: 'As ocorrências contam desde a 1ª formação do ano no município.',
        prototipo:
          'O mês da 1ª formação vem do relatório mensal. Um projeto sem coordenador não manda relatório mensal; se o município só tem esse projeto, ele não tem formação registrada no ano, e nenhuma ocorrência conta na cor, nem uma reclamação. A ocorrência fica guardada na ficha, e o indicador mostra "Nenhuma que conte", com quantas ficaram de fora.',
        paraDecidir:
          'No município sem formação registrada no ano, a reclamação deve contar assim mesmo? Na versão real, a data da formação virá dos eventos do sistema, e não só do relatório mensal.',
      },
      {
        titulo: 'Média e NPS do município: juntar os projetos ou valer o pior?',
        origem: 'Leitura do protótipo: decisões 46 e 51 (cada projeto tem a sua cor e a sua pesquisa)',
        oQueDiz:
          'Cada projeto tem o seu cronograma e a sua cor; na cor do município entra o pior (decisão 46). A pesquisa é por projeto (decisão 51).',
        prototipo:
          'No cronograma e na resposta à pesquisa, vale o pior projeto. Já a média da pesquisa e o NPS do município juntam as respostas de todos os projetos. Isso pode esconder um projeto ruim: notas 10 num projeto e 6 no outro dão média 8 (amarelo), mas o segundo projeto, sozinho, seria vermelho. A pesquisa diz o nome do projeto no título, e a nota de recomendação pergunta pelo projeto avaliado, e não pela parceria com a Aprender Editora, como no PDF: quem responde por dois projetos dá uma nota para cada um.',
        paraDecidir:
          'A média e o NPS do município juntam as respostas de todos os projetos, ou vale o pior projeto, como no cronograma (decisão 46)? A nota de recomendação é sobre o projeto ou sobre a parceria inteira?',
      },
      {
        titulo: 'Aviso e alerta de prazo: para qual coordenador?',
        origem: 'Leitura do protótipo: decisões 46 e 52 (cada projeto tem o seu coordenador; aviso de piora para amarelo)',
        oQueDiz:
          'No amarelo, agem a gestora de referência e os coordenadores. Cada projeto do município tem o seu coordenador, e há municípios com projetos de coordenadores diferentes.',
        prototipo:
          'O aviso de piora para amarelo e o alerta de prazo das tarefas do amarelo vão para os coordenadores de todos os projetos do município, e não só para o do projeto que piorou: a cor e as tarefas são do município. Na tela da Líder, em "Por gerência", o município conta na gerência de cada coordenador dos seus projetos, e a planilha lista todos os coordenadores.',
        paraDecidir: 'O aviso vai para os coordenadores de todos os projetos do município, ou só para o do projeto que piorou?',
      },
      {
        titulo: 'Cronograma por projeto: qual régua até o critério de cada projeto?',
        origem: 'Leitura do protótipo: decisão 46 (o critério de cada projeto o dono define depois)',
        oQueDiz: 'Cada projeto tem o seu cronograma e a sua cor; na cor do município entra o pior projeto.',
        prototipo:
          'Enquanto o critério de cada projeto não vem, todos os projetos usam a régua do PDF: 90% ou mais é verde, de 70% a menos de 90% é amarelo, menos de 70% é vermelho.',
        paraDecidir: 'Qual o critério de cada projeto?',
      },
      {
        titulo: 'Depois que o Comitê desfaz um vermelho, o que faz a cor mudar de novo?',
        origem: 'Leitura do protótipo: decisões 38, 39 e 42 (vermelho na hora; o Comitê confirma ou desfaz)',
        oQueDiz: 'Um indicador em vermelho ou três amarelos mudam a cor oficial na hora. O Comitê confirma ou desfaz depois.',
        prototipo:
          'Se o Comitê desfez, o mesmo alerta não volta a mudar a cor sozinho (uma segunda reclamação, com o indicador de ocorrências já em vermelho, não muda). Muda de novo com um alerta novo: outro indicador em vermelho, ou um indicador que piorou.',
        paraDecidir: 'Confirmar: só um alerta novo refaz o vermelho que o Comitê desfez?',
      },
      {
        titulo: 'Confirmar o vermelho na hora não reabre as tarefas',
        origem: 'Leitura do protótipo: decisões 38 e 43 (o Comitê confirma; a mesma cor reabre as tarefas)',
        oQueDiz:
          'Quando o Comitê confirma o vermelho na hora, as tarefas seguem. Quando a mesma cor é confirmada de novo, todas as tarefas da cor reabrem.',
        prototipo:
          'No mesmo ciclo, confirmar a cor que já vale não mexe nas tarefas (é a confirmação). No ciclo seguinte, a mesma cor publicada de novo reabre todas as tarefas da cor, e as abertas de antes ficam "substituídas". Quando a cor muda de amarelo para vermelho, as tarefas abertas do amarelo continuam abertas, mesmo quando o Comitê muda o amarelo no mesmo ciclo (para vermelho ou para verde): só as do vermelho que o Comitê desfaz ficam canceladas (decisão 42).',
        paraDecidir:
          'Confirmar as três leituras, em especial as tarefas do amarelo quando o município vai para o vermelho, e quando o Comitê muda o amarelo no mesmo ciclo.',
      },
      {
        titulo: 'A decisão registrada na tela do Comitê é do ordinário ou do extraordinário?',
        origem: 'Leitura do protótipo: decisões 40 e 41 (data marcada pela SPE; extraordinário a critério da SPE)',
        oQueDiz: 'O Comitê ordinário se reúne na data marcada pela SPE; o extraordinário, quando a SPE convoca.',
        prototipo:
          'Na demonstração, a decisão registrada na tela vale como do Comitê extraordinário quando a SPE o convocou para hoje; senão, vale como do ordinário, com a data de hoje, mesmo que a data marcada seja depois.',
        paraDecidir: 'Na versão real, a tela do Comitê só registra decisões no dia de uma reunião marcada ou convocada?',
      },
      {
        titulo: 'Indicadores da Líder: como o protótipo fez as contas novas',
        origem: 'Leitura do protótipo: decisões 46, 50 e 51 (projeto, tempo de resposta e pesquisa por projeto)',
        oQueDiz:
          'A tela da Líder passa a mostrar a satisfação por projeto e o tempo médio de resposta às ocorrências, e a pesquisa é respondida por projeto.',
        prototipo:
          'A satisfação por projeto junta, pelo nome do projeto, as respostas de todos os municípios que têm aquele projeto. O tempo médio de resposta usa todas as ocorrências do ano do calendário (de 1º de janeiro até hoje), inclusive as de antes da 1ª formação do ano, que não contam na cor. Na taxa de resposta à pesquisa, o município conta como "respondeu" só quando todos os projetos dele responderam no prazo.',
        paraDecidir: 'Confirmar as três contas, em especial a do município com um projeto que não respondeu.',
      },
      {
        titulo: 'Convergência: quem entra na conta e o que é "concordar"',
        origem: 'Leitura do protótipo: decisão 49 (medir e listar a convergência)',
        oQueDiz: 'Medir a porcentagem de municípios em que a pesquisa e as ocorrências concordam e listar os que divergem.',
        prototipo:
          'No último ciclo fechado, a cor da pesquisa é a pior entre a média e o NPS. Divergem quando uma está verde e a outra vermelha; o resto conta como "concorda" (amarelo com verde também). O município sem resposta à pesquisa no ciclo fica fora da conta. A cor das ocorrências é a que o Semáforo mostra: conta as ocorrências do ano até o fim do ciclo (decisão 32), e a pesquisa é só a do ciclo. Uma reclamação de março, com a pesquisa verde, deixa o município entre os que divergem em todos os ciclos até dezembro.',
        paraDecidir:
          'Confirmar a régua: amarelo com verde conta como concordar? E na comparação vale a cor das ocorrências do ano, como no Semáforo, ou só as ocorrências do ciclo?',
      },
      // Rodada 2 de revisão: leituras do protótipo que a pauta não registrava.
      {
        titulo: 'Quando o município sai do vermelho, as tarefas abertas do vermelho continuam?',
        origem: 'Leitura do protótipo: decisões 42 a 44 (o que acontece com as tarefas quando a cor muda)',
        oQueDiz:
          'Quando o Comitê desfaz o vermelho, as tarefas abertas do vermelho ficam "canceladas pelo Comitê" (decisão 42). O amarelo "em recuperação" recebe as tarefas do amarelo (decisão 44). Nenhuma das duas diz o que acontece com as tarefas abertas do vermelho quando o município sai do vermelho pelo ciclo, para o amarelo em recuperação ou para o verde.',
        prototipo:
          'Ao sair do vermelho pelo ciclo, as tarefas abertas do vermelho continuam abertas até o prazo, e o alerta de prazo delas segue para quem age no vermelho. Nos dados simulados, Sobral-CE (em recuperação, amarelo desde 06/11/2026) ainda tem aberta a visita técnica do vermelho, com prazo em 15/02/2027. Ao publicar uma cor, o aviso do Comitê diz quais tarefas de outra cor continuam abertas. Nada é apagado (decisão 57).',
        paraDecidir:
          'Ao sair do vermelho, as tarefas abertas do vermelho fecham (guardadas com o estado, como manda a decisão 57) ou seguem até o prazo?',
      },
      {
        titulo: 'Feriados contam como dia útil nos prazos?',
        origem: 'Pergunta 29 (a) das perguntas de 07/12: prazos em dias corridos ou úteis, e se feriado conta',
        oQueDiz:
          'A pergunta tinha quatro opções. A 3 era "Dias úteis (segunda a sexta)"; a 4, "Dias úteis descontando também os feriados". O dono escolheu a 3.',
        prototipo:
          'O feriado em dia de semana conta como dia útil. Nos dados simulados, a devolutiva de Horizonte-CE, com a cor de 30/11/2026, vence em 11/01/2027, contando 25/12 e 01/01 como dias úteis.',
        paraDecidir: 'Os feriados devem ser descontados dos prazos?',
        decidido: {
          numero: 33,
          resposta: 'Dias úteis de segunda a sexta (opção 3). A opção 4, que descontava os feriados, ficou de fora.',
        },
      },
      {
        titulo: 'Prazo em meses que cai no sábado ou no domingo',
        origem: 'Leitura do protótipo: decisões 33 e 35 (prazos em dias úteis; "no bimestre" e "no semestre" contam da publicação)',
        oQueDiz:
          'Os prazos em dias são dias úteis (decisão 33). A observação de uma formação (2 meses) e a visita técnica (6 meses) contam da publicação (decisão 35), e a conta em meses pode cair no fim de semana.',
        prototipo:
          'O prazo em meses que cai no sábado ou no domingo passa para a segunda-feira seguinte. Nos dados simulados, a visita técnica de Horizonte-CE, com a cor de 30/11/2026, vence em 31/05/2027 (30/05 é domingo).',
        paraDecidir: 'O prazo em meses que cai no fim de semana passa para a segunda-feira, ou fica no próprio dia?',
      },
      {
        titulo: 'Uma resposta por projeto: e se outra pessoa do mesmo projeto já respondeu?',
        origem: 'Leitura do protótipo: decisão 51 (a pesquisa é por projeto)',
        oQueDiz:
          'Cada projeto pode ter o seu articulador; se for o mesmo, ele responde uma pesquisa por projeto. A decisão não fala de duas pessoas respondendo pelo mesmo projeto.',
        prototipo:
          'Só entra uma resposta por projeto no ciclo, e a segunda é recusada, mesmo que venha de outra pessoa. A tela aceita também a resposta do secretário ou da secretária municipal de educação: se o secretário responde primeiro, o articulador do mesmo projeto não consegue mais responder.',
        paraDecidir:
          'Pode haver mais de uma resposta por projeto no ciclo (por exemplo, a do articulador e a do secretário), com a média das notas, como sugeria o PDF?',
      },
      {
        titulo: 'Meta de 48 h da resposta à ocorrência: horas corridas ou dias úteis?',
        origem: 'Leitura do protótipo: decisões 34 e 50 (o "contato em 48 h" virou 2 dias úteis; a resposta à ocorrência tem meta de 48 h)',
        oQueDiz:
          'O PDF usa "48 h" em dois lugares. O contato do vermelho virou 2 dias úteis (decisão 34). A meta do tempo de resposta às ocorrências ficou em 48 h (decisão 50).',
        prototipo:
          'A meta da resposta conta horas corridas, com sábado e domingo; a ficha do município, os Indicadores da Líder e o formulário da ocorrência dizem "48 h corridas". Uma ocorrência registrada na sexta às 16h e respondida na segunda às 10h leva 66 h e fica "fora da meta", mesmo respondida no 1º dia útil.',
        paraDecidir: 'A meta de 48 h da resposta conta horas corridas, ou 2 dias úteis, como o contato do vermelho?',
      },
      {
        titulo: 'Observação de formação do amarelo: quem faz e quem recebe o alerta do prazo?',
        origem: 'Leitura do protótipo: decisão 36 (quem faz as tarefas) e o PDF do Semáforo (seção 5 e coleta 6)',
        oQueDiz:
          'O PDF põe a observação de uma formação entre as tarefas do amarelo, em que agem a gestora de referência e os coordenadores (seção 5). Na coleta 6, quem registra a observação é a gestora pedagógica. A decisão 36 respondeu só pelas tarefas do vermelho.',
        prototipo:
          'O amarelo fica com a gestora de referência e os coordenadores, e o alerta de prazo da observação vai para eles e para a SPE. Já o formulário da observação, na tela Relatório mensal e formulários, é da gestora pedagógica.',
        paraDecidir: 'Quem faz a observação de formação do amarelo, e quem recebe o alerta do prazo dela?',
      },
      {
        titulo: 'Dado registrado com atraso: as tarefas contam do dia do dado ou do dia do registro?',
        origem: 'Leitura do protótipo: decisão 38 (o vermelho imediato muda a cor na hora)',
        oQueDiz:
          'O vermelho imediato muda a cor oficial na hora, e as tarefas começam. O PDF e a decisão não dizem de que dia contam as tarefas quando o dado é registrado dias depois de acontecer.',
        prototipo:
          'As tarefas contam do dia do dado (a data da ocorrência, ou a da reunião, para a queixa do momento reservado), mas nunca antes da decisão que estava em vigor: assim, a lista de decisões do município fica em ordem. Com isso, um dado registrado com atraso pode criar tarefas que já nascem vencidas. Exemplo: em Sobral-CE, registrar hoje a ata atrasada da reunião de 27/11 com uma reclamação no momento reservado deixa o município vermelho desde 27/11, e o contato (01/12) e a reunião com a Secretaria (04/12) já nascem vencidos.',
        paraDecidir: 'Quando o dado é registrado com atraso, as tarefas contam do dia do dado ou do dia em que ele foi registrado?',
      },
      {
        titulo: 'Queixa feita na reunião e registrada com a ata: de onde conta o tempo de resposta?',
        origem: 'Leitura do protótipo: decisões 48 e 50 (a ata vai até 5 dias úteis depois da reunião; meta de 48 h para responder)',
        oQueDiz:
          'A ata da reunião de escuta pode ser registrada até 5 dias úteis depois da reunião (decisão 48). O tempo de resposta às ocorrências tem a meta de 48 h (decisão 50). Nenhuma das duas diz de onde conta o tempo da queixa feita no momento reservado.',
        prototipo:
          'A queixa fica com a data da reunião, que é quando foi feita e o dia que conta na cor. O tempo de resposta conta do dia e da hora em que a ata é registrada, que é quando a queixa chega a quem responde: a tela da ata pede essa hora. Assim, a ata registrada no prazo não põe a queixa fora da meta antes de alguém saber dela.',
        paraDecidir: 'O tempo de resposta da queixa do momento reservado conta da reunião ou do registro da ata?',
      },
      // Rodada 4 de revisão: leituras que as decisões de 25/11 não cobrem.
      {
        titulo: 'Amigos do Bem no Semáforo: entra?',
        origem: 'Leitura do protótipo: decisões 46, 51 e 56 (cada projeto com o seu cronograma e a sua pesquisa; o Amigos do Bem usa o local de cada formação)',
        oQueDiz:
          'No Semáforo, cada projeto do município tem o seu relatório, o seu cronograma e a sua pesquisa (decisões 46 e 51). O Amigos do Bem é uma ONG, sem articulador municipal, e o local dele é o de cada formação (decisão 56). Nenhuma decisão diz se ele entra no Semáforo.',
        prototipo:
          'O Amigos do Bem conta na carga do coordenador no ICA, mas fica fora do Semáforo: não tem relatório mensal, pesquisa, cronograma nem cor. Nas fichas de Petrolina-PE e Santana do Ipanema-AL aparecem só os outros projetos do município, e Mauriti-CE não está no Semáforo.',
        paraDecidir: 'O Amigos do Bem entra no Semáforo como um projeto do município de cada local de formação? Quem responderia a pesquisa dele?',
      },
      {
        titulo: 'Relatório mensal com mais formações realizadas que previstas',
        origem: 'Leitura do protótipo: decisões 46 e 47 (o cronograma de cada projeto; a formação adiada de comum acordo é só observação)',
        oQueDiz:
          'O cronograma cumprido é o realizado dividido pelo previsto no ciclo. A formação adiada pode acontecer num mês seguinte, e as decisões não dizem se o realizado do mês pode passar do previsto.',
        prototipo:
          'A tela aceita mais formações ou visitas realizadas que previstas, sem aviso. A conta soma o ciclo inteiro e pode passar de 100%: 2 de 5 em novembro e 8 de 5 em dezembro dão 100% e verde, e o mês fraco some. Um erro de digitação (40 no lugar de 4) também passa.',
        paraDecidir: 'O realizado pode passar do previsto no mês (reposição)? Se puder, o cronograma fica limitado a 100%? Se não puder, a tela recusa?',
      },
      {
        titulo: 'Alerta de prazo "um dia antes": dia corrido ou dia útil?',
        origem: 'Leitura do protótipo: decisões 33 e 34 (prazos em dias úteis) e seção 8 do PDF (alerta um dia antes e no vencimento)',
        oQueDiz:
          'O PDF manda o alerta de prazo um dia antes e no dia do vencimento. Os prazos são em dias úteis, de segunda a sexta (decisões 33 e 34).',
        prototipo:
          'O "um dia antes" conta o dia útil: na sexta-feira, avisa a tarefa que vence na segunda, com a situação "Vence no próximo dia útil". Contando o dia corrido, o aviso cairia no domingo e não sairia.',
        paraDecidir: 'O alerta de "um dia antes" sai no dia útil anterior (a sexta, para o prazo de segunda)?',
      },
      // Rodada 5 de revisão: leituras que as decisões de 25/11 não cobrem.
      {
        titulo: 'Ocorrência sem resposta há mais de 48 h: conta como fora da meta?',
        origem: 'Leitura do protótipo: decisão 50 (medir o tempo de resposta às ocorrências; meta de 48 h)',
        oQueDiz: 'A ocorrência guarda quando foi respondida, e o tempo de resposta é medido contra a meta de 48 h.',
        prototipo:
          'A média e o "fora da meta" usam só as ocorrências já respondidas. A ocorrência ainda sem resposta aparece à parte, como "Sem resposta", mesmo registrada há dias: ela não piora a média nem entra na lista "Fora da meta" da tela da Líder.',
        paraDecidir: 'A ocorrência sem resposta que já passou de 48 h do registro deve contar como fora da meta?',
      },
      {
        titulo: 'Reunião de escuta: uma por vez, a 30 dias ou mais da outra?',
        origem: 'Leitura do protótipo: decisão 48 (a reunião é marcada antes) e seção 5 do PDF do Semáforo (a cada 6 meses no verde, a cada 3 no amarelo e no vermelho)',
        oQueDiz:
          'A reunião de escuta é semestral no verde e trimestral no amarelo e no vermelho. Ela é marcada antes, e a ata vem depois (decisão 48). Nada diz se pode haver duas reuniões perto uma da outra.',
        prototipo:
          'Nos dados simulados e na tela, a periodicidade sai da cor em vigor do município, e fica uma reunião por vez: a tela recusa marcar uma reunião a menos de 30 dias de outra. Jequié-BA, com a reunião de 10/12/2026 marcada, não aceita outra em 11/12/2026. A reunião já marcada não muda de periodicidade quando a cor muda.',
        paraDecidir: 'Pode haver mais de uma reunião de escuta marcada perto uma da outra? Quando a cor muda, a reunião já marcada muda de periodicidade?',
      },
      {
        titulo: 'O Comitê desfaz o vermelho na hora: a tarefa que ele substituiu volta?',
        origem: 'Leitura do protótipo: decisões 42, 43 e 57 (desfazer cancela as tarefas do vermelho; a mesma cor reabre as tarefas; nada some)',
        oQueDiz:
          'O vermelho na hora reabre todas as tarefas do vermelho, e as abertas de antes ficam "substituídas" (decisão 43). Quando o Comitê desfaz o vermelho, as tarefas abertas dele ficam "canceladas pelo Comitê" (decisão 42). Nenhuma das duas diz o que acontece com a tarefa que o vermelho desfeito tinha substituído.',
        prototipo:
          'A tarefa substituída pelo vermelho desfeito volta a ficar aberta, como estava antes dele, com o mesmo prazo; a substituição desfeita não fica anotada na tarefa. Sobral-CE mostra isso: com uma reclamação hoje, a visita técnica do vermelho de 14/08/2026 (prazo em 15/02/2027) fica substituída; se o Comitê desfaz esse vermelho, as tarefas novas ficam canceladas e a visita técnica volta a ficar aberta até 15/02/2027. Sem isso, o município ficaria sem nenhuma visita técnica aberta.',
        paraDecidir:
          'Confirmar: ao desfazer o vermelho, a tarefa que ele tinha substituído volta a ficar aberta? A substituição desfeita deve ficar anotada no histórico da tarefa (decisão 57)?',
      },
    ],
  },
  {
    id: 'tema-deslocamento-pdf',
    titulo: 'Deslocamento: o relatório se contradiz ou não diz',
    pontos: [
      {
        titulo: '16 ou 23 municípios só por terra?',
        origem: 'Contradição dentro do PDF do Deslocamento (página 1 e regra "Escolha do modal")',
        oQueDiz:
          'O relatório diz que 16 municípios vão só por terra por decisão da gestão. Mas o grupo que ele lista (Ceará, Paraíba, Afrânio, Lagoa Grande, Petrolina e Filadélfia) soma 23: 17 do Ceará, 2 da Paraíba e 4 avulsos.',
        prototipo: 'Marca os 23 do grupo listado como "só por terra, por decisão da gestão".',
        paraDecidir: 'Quais são os 16? Ou o número certo é 23?',
        decidido: { numero: 53, resposta: 'Valem os 23 municípios por terra da lista do relatório.' },
      },
      {
        titulo: 'Craíbas-AL: Longo ou Muito longo?',
        origem: 'Contradição dentro do PDF do Deslocamento (lista de municípios × limite das faixas)',
        oQueDiz:
          'Craíbas-AL tem 18h00 de ida e volta e o relatório a põe em "Muito longo". Pelo limite do próprio relatório (Longo até 18h), seria "Longo", como Cairu-BA e Indianópolis-MG, que também têm 18h00.',
        prototipo:
          'Craíbas-AL fica em "Longo", pelo limite do próprio relatório (18h00, como Cairu-BA e Indianópolis-MG). A correção fica registrada no roteiro que lê o relatório, para não voltar quando ele for lido de novo.',
        paraDecidir: 'Craíbas-AL é Longo ou Muito longo?',
        decidido: { numero: 54, resposta: 'Craíbas-AL é "Longo" (18h00, pelo limite do próprio relatório).' },
      },
      {
        titulo: 'Mediana: coluna Ida (17h45) ou coluna Ida e volta (17h48)?',
        origem: 'Diferença dentro do PDF do Deslocamento (página 1 × tabela de municípios)',
        oQueDiz:
          'A página 1 informa a mediana de 17h45 de ida e volta. O relatório calcula a mediana pela coluna Ida e dobra: dá exatamente 17h45. Com a coluna Ida e volta da mesma tabela, que o relatório arredondou à parte, a mediana dá 17h47min30s, que arredonda para 17h48.',
        prototipo:
          'O ICA usa 17h45 (a coluna Ida dobrada, o número do relatório), marcado como estimado, para o município sem localidade definida, e as telas mostram só esse número.',
        paraDecidir: 'Qual coluna o ICA usa para o município sem localidade: a Ida dobrada (17h45, como o relatório) ou a Ida e volta (17h48)?',
        decidido: { numero: 55, resposta: 'O tempo do meio é 17h45, o número do relatório.' },
      },
      {
        titulo: 'Amigos do Bem: em que município e estado?',
        origem: 'Lacuna do PDF do Deslocamento (lista de projetos)',
        oQueDiz: 'O relatório lista o projeto Amigos do Bem sem município e, por isso, sem tempo de deslocamento.',
        prototipo:
          'Segue o Aprender Sistema: o Amigos do Bem não tem um município fixo, e cada local de formação é uma linha de município. No protótipo, os locais (simulados) são Mauriti-CE, Santana do Ipanema-AL e Petrolina-PE. O tempo é o do local no relatório. Mauriti-CE não está no relatório (ver o ponto "Local de formação conhecido que não está no relatório", abaixo).',
        paraDecidir: 'Em que município e estado fica o Amigos do Bem? Que tempo de referência ele usa?',
        decidido: {
          numero: 56,
          resposta: 'Amigos do Bem segue o sistema: o local é o de cada formação (pode ser em AL, CE ou PE).',
        },
      },
      {
        titulo: 'Amigos do Bem no ICA: como o protótipo contou',
        origem: 'Leitura do protótipo ao aplicar a decisão 56',
        oQueDiz: 'O tempo do Amigos do Bem é o do local de cada formação, que pode ser em AL, CE ou PE (decisão 56).',
        prototipo:
          'Na carga do coordenador, cada local de formação conta como um município: entra na contagem de municípios e de frentes e soma uma ida e volta no deslocamento, como qualquer outro município da carteira. A exceção é o local que não está no relatório (Mauriti-CE): entra com o tempo do meio e não soma estado (ver o ponto abaixo).',
        paraDecidir: 'Cada local de formação do Amigos do Bem conta como um município na carga do coordenador?',
      },
      // Rodada 3 de revisão: a decisão 55 respondeu pelo município sem localidade; o local conhecido ficou sem resposta.
      {
        titulo: 'Local de formação conhecido que não está no relatório: que tempo usar?',
        origem: 'Leitura do protótipo: decisões 55 e 56 (o tempo do meio; o Amigos do Bem usa o local de cada formação)',
        oQueDiz:
          'A pergunta 40 era sobre o município sem localidade definida, como um projeto novo ainda sem local, e a resposta foi o tempo do meio, 17h45 (decisão 55). A decisão 56 diz que o tempo do Amigos do Bem depende do local de cada formação. Nenhuma das duas diz que tempo usar quando o local é conhecido, mas não está no relatório.',
        prototipo:
          'Mauriti-CE, um local (simulado) do Amigos do Bem, não está no relatório. O protótipo usa para ele o tempo do meio, 17h45, marcado como estimado, como para o município sem localidade. Também como ele, o estado desse local não entra na contagem de estados do coordenador no ICA: o CE de Mauriti não conta.',
        paraDecidir:
          'Para o local conhecido que não está no relatório, vale o tempo do meio até alguém calcular o tempo real? E o estado dele conta na carga do coordenador?',
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
          'A Integra tem 5 cartões: ICA, Semáforo, Deslocamento, DFF (no link atual) e Avaliação do Coordenador (em breve). Formar e Avaliar já têm link no sistema e podem virar cartões.',
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
      {
        titulo: 'Observação de formação: registrada no Semáforo ou feita na DFF?',
        origem: 'O PDF do Semáforo (coleta 6 e seção 9) e o cartão da DFF na Integra dizem coisas diferentes',
        oQueDiz:
          'Pelo PDF do Semáforo, a gestora pedagógica registra as observações de formação num formulário do sistema, e elas vão para o PDI do coordenador na Plataforma DFF. O cartão da DFF, na página da Integra, diz que a observação de formação é feita lá.',
        prototipo:
          'Segue o PDF: a observação é registrada na tela Relatório mensal e formulários do Semáforo e, na demonstração, fica só na lista do que foi registrado na sessão.',
        paraDecidir:
          'Onde a observação nasce: num formulário novo do Aprender Sistema, que manda para a DFF, ou na DFF, e o Aprender Sistema lê de lá?',
      },
    ],
  },
];

// ---------------------------------------------------------------- 3. de onde virá cada dado

type Onde = 'aprender' | 'dff' | 'logistica' | 'falta';

const ONDE: Record<Onde, { nome: string; fundo: string; texto: string }> = {
  aprender: { nome: 'Aprender Sistema', fundo: '#E3F0EC', texto: BRAND_COLORS.primaryDark },
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
    dado: 'Coordenador de cada projeto',
    onde: ['aprender'],
    detalhe:
      'O coordenador de cada projeto do município no Plano Anual e a equipe de cada gerência. Um município pode ter projetos de coordenadores diferentes.',
  },
  {
    dado: 'Coordenador: atuação e gestora pedagógica',
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
    detalhe: 'O projeto do município não tem status (ativo ou suspenso) nem a data da mudança. Suspenso não conta no ICA.',
  },
  {
    dado: 'Gestora de referência',
    onde: ['falta'],
    detalhe: 'Função nova, combinada em 23/11. É o mesmo cadastro para o ICA e o Semáforo.',
  },
  {
    dado: 'Tempo de deslocamento',
    onde: ['falta'],
    detalhe:
      'O mesmo tempo do bloco Deslocamento, abaixo: hoje vem do relatório de deslocamento (92 municípios), que é o que o protótipo usa. Na versão real, fica no cadastro de municípios do sistema e o ICA lê de lá; o Deslocamento e a tela de viagens viram um módulo só (decisão 29).',
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
    detalhe:
      'O projeto avaliado, os 6 itens, a nota NPS e se respondeu no prazo: uma por projeto do município. Na versão real, link sem login; no protótipo, respondida na mesma tela.',
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
    dado: 'Relatório mensal de cada projeto',
    onde: ['falta'],
    detalhe:
      'Formulário novo, um por projeto e mês, mandado pelo coordenador do projeto. A parte das formações pode vir preenchida com o que o Aprender Sistema já tem. Se o coordenador corrige um mês, vale o novo, e a versão anterior fica guardada.',
  },
  {
    dado: 'Ocorrências',
    onde: ['falta'],
    detalhe: 'Registro do comercial e do relacionamento, num fluxo único, com a data e hora do registro e da resposta ao município.',
  },
  {
    dado: 'Reunião de escuta',
    onde: ['falta'],
    detalhe:
      'A data marcada e, depois, a ata (até 5 dias úteis após a reunião): participantes, encaminhamentos e o registro confidencial do momento reservado.',
  },
  {
    dado: 'Datas do Comitê',
    onde: ['falta'],
    detalhe: 'A data do Comitê ordinário, marcada pela SPE a cada ciclo, e o Comitê extraordinário, quando a SPE convoca.',
  },
  {
    dado: 'Observação de formação',
    onde: ['falta'],
    detalhe:
      'Formulário novo, pelo PDF do Semáforo (coleta 6): a gestora pedagógica registra a observação, e ela vai para o PDI do coordenador na Plataforma DFF. No protótipo, fica na tela Relatório mensal e formulários. Se a observação já é feita na DFF, a origem muda: ver "A Integra e as outras ferramentas", acima.',
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

const DADOS_DESLOCAMENTO: Dado[] = [
  {
    dado: 'Tempo de referência de cada município',
    onde: ['falta'],
    detalhe:
      'Hoje vem do relatório de deslocamento (92 municípios), que é o que o protótipo usa. Na versão real, fica no cadastro de municípios do sistema, e o ICA, a Logística e a FRV leem desse cadastro: ninguém guarda uma cópia.',
  },
  {
    dado: 'Viagens registradas',
    onde: ['aprender'],
    detalhe:
      'A tela de viagens do sistema já registra as viagens de cada pessoa. Na versão real, o Deslocamento e a tela de viagens viram um módulo só (decisão 29), e a tela mostra o tempo esperado ao lado do registrado.',
  },
];

// ---------------------------------------------------------------- 4. para quem vai cada resultado

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
      'Comitê de Satisfação Municipal e quem age em cada cor, com as tarefas e os prazos: a gestora de referência; no amarelo, também os coordenadores dos projetos; no vermelho, também a gestora pedagógica. Pelo Aprender Sistema, os outros módulos, como o comercial e o relacionamento.',
  },
  {
    resultado: 'Resposta do articulador',
    vaiPara: 'Semáforo e Avaliação do Coordenador ao mesmo tempo (combinado em 23/11).',
  },
  {
    resultado: 'Observação de formação e relatório de visita',
    vaiPara: 'PDI do coordenador na Plataforma DFF (PDF do Semáforo, seção 9).',
  },
  {
    resultado: 'Tempo de deslocamento de cada município',
    vaiPara:
      'Componente "Tempo de deslocamento" do ICA, somado por coordenador; a tela de viagens, com o tempo esperado ao lado do registrado; e, quando migrarem, a Logística e a FRV.',
  },
];

// ---------------------------------------------------------------- tela

const PARTES = [
  { id: 'validar-pontos', titulo: 'Sugestões e pontos em aberto' },
  { id: 'validar-quem-ve', titulo: 'Quem vê o quê na versão real' },
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

// ---------------------------------------------------------------- 2. quem vê o quê (matriz)

/** Cor de cada ação; a ação vai sempre escrita ao lado. */
const COR_ACAO: Record<Acao | 'aberta', { fundo: string; texto: string }> = {
  ve: { fundo: '#E3F0EC', texto: BRAND_COLORS.primaryDark },
  propoe: { fundo: '#DCEBFA', texto: '#0B4A80' },
  aplica: { fundo: '#EDE7F6', texto: '#4A2A7A' },
  registra: { fundo: '#FCE8DB', texto: '#7A3410' },
  nada: { fundo: '#F2F2F2', texto: '#4D4D4D' },
  aberta: { fundo: '#FFF0C2', texto: '#6B4A00' },
};

const LEGENDA: { chave: Acao | 'aberta'; nome: string; significa: string }[] = [
  { chave: 've', nome: ACOES.ve, significa: 'abre a tela e consulta.' },
  { chave: 'propoe', nome: ACOES.propoe, significa: 'sugere uma mudança, que outra pessoa aplica.' },
  { chave: 'aplica', nome: ACOES.aplica, significa: 'confirma e grava a mudança.' },
  { chave: 'registra', nome: ACOES.registra, significa: 'preenche e envia informação.' },
  { chave: 'nada', nome: ACOES.nada, significa: 'não abre a tela.' },
  { chave: 'aberta', nome: 'Em aberto', significa: 'depende de uma pergunta para o dia 7 (lista abaixo dos cartões).' },
];

const MODULOS: Modulo[] = ['ICA', 'Semáforo', 'Deslocamento', 'DFF'];

const BORDA_CARGO = 'border-0 border-t border-solid border-[#d9d9d9]';

function Selo({ cor, children }: { cor: Acao | 'aberta'; children: string }): JSX.Element {
  const c = COR_ACAO[cor];
  return (
    <span className="inline-block rounded px-2 py-0.5 text-sm font-semibold" style={{ background: c.fundo, color: c.texto }}>
      {children}
    </span>
  );
}

function CelulaQuemVe({ celula }: { celula: Celula }): JSX.Element {
  return (
    <span className="flex flex-col items-start gap-1">
      {celula.faz !== undefined && <Selo cor={celula.faz}>{ACOES[celula.faz]}</Selo>}
      {celula.aberta !== undefined && <Selo cor="aberta">{`Em aberto (${celula.aberta === 'P2-painel' ? 'P2' : celula.aberta})`}</Selo>}
      {celula.nota !== undefined && <span>{celula.nota}</span>}
      {celula.decisao !== undefined && <span className="text-xs">(decisão {celula.decisao})</span>}
    </span>
  );
}

/**
 * A matriz cargos × telas em cartões: um por tela, agrupados por módulo, com cada cargo escrito ao lado do que ele
 * faz. Como tabela, as 9 colunas pediam pelo menos 1168 px e rolavam para o lado em qualquer largura desta página.
 */
function MatrizQuemVe(): JSX.Element {
  return (
    <section aria-labelledby="quem-ve-legenda">
      <Title level={3} id="quem-ve-legenda" style={{ fontSize: 18 }}>
        Quem faz o quê em cada tela, na versão real
      </Title>
      {MODULOS.map((modulo, i) => (
        <section key={modulo} aria-labelledby={`quem-ve-modulo-${i}`} className="mt-4">
          <Title level={4} id={`quem-ve-modulo-${i}`} style={{ fontSize: 16 }}>
            {modulo}
          </Title>
          <ul className="m-0 grid list-none gap-3 p-0">
            {TELAS.filter((t) => QUEM_VE[t].modulo === modulo).map((t) => (
              <li key={t} className={CARTAO}>
                <Title level={5} style={{ fontSize: 16, marginBottom: 8 }}>
                  {QUEM_VE[t].titulo}
                </Title>
                <dl className="m-0 grid gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-4">
                  {PAPEIS.map((p) => (
                    <div key={p.chave} className={`${BORDA_CARGO} pt-2`}>
                      <dt className="font-semibold">{p.nome}</dt>
                      <dd className="m-0 mt-1 text-sm">
                        <CelulaQuemVe celula={QUEM_VE[t].quem[p.chave]} />
                      </dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}

/** As telas da matriz em que a pergunta aparece. */
function telasDaPergunta(id: string): string[] {
  return TELAS.filter((t) => PAPEIS.some((p) => QUEM_VE[t].quem[p.chave].aberta === id)).map(
    (t) => `${QUEM_VE[t].titulo} (${QUEM_VE[t].modulo})`,
  );
}

function QuemVeOQue(): JSX.Element {
  return (
    <>
      <p>
        No protótipo, quem entra na Integra vê tudo (decisão de 24/11). Na versão real, cada cargo verá só o que é
        seu. Os cartões abaixo, um por tela, mostram o que os documentos de requisitos, a reunião de 23/11 e as
        decisões do dono já dizem. O que está marcado <strong>Em aberto</strong> é para decidir no dia 7.
      </p>
      <ul className="m-0 mb-4 grid list-none gap-1 p-0" aria-label="O que quer dizer cada palavra dos cartões">
        {LEGENDA.map((l) => (
          <li key={l.chave}>
            <Selo cor={l.chave}>{l.nome}</Selo> {l.significa}
          </li>
        ))}
      </ul>
      <MatrizQuemVe />
      <p className="mt-3">
        O Comitê de Satisfação Municipal não é um cargo: são a SPE, a Gestão Operacional e as gestoras pedagógicas
        juntas. Sem conta no sistema, por link: articuladores e secretários municipais respondem à pesquisa; o
        formador responde à Avaliação do Coordenador sem se identificar; o distribuidor registra ocorrências pelo
        Comercial.
      </p>

      <section aria-labelledby="quem-ve-decidido" className="mt-6">
        <Title level={3} id="quem-ve-decidido" style={{ fontSize: 18 }}>
          Já decidido
        </Title>
        <p>
          Inclui as respostas do dono de 25/11 sobre as regras (decisões 30 a 57), que também aparecem nos cartões da
          primeira parte, com o selo &ldquo;Decidido&rdquo;.
        </p>
        <ul className="m-0 grid list-none gap-3 p-0">
          {DECIDIDO.map((d) => (
            <li key={d.numero} className={CARTAO}>
              <Selo cor="ve">{`Decidido (decisão ${d.numero})`}</Selo>
              <p className="m-0 mt-1">{d.texto}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="quem-ve-aberto" className="mt-6">
        <Title level={3} id="quem-ve-aberto" style={{ fontSize: 18 }}>
          Em aberto — decidir no dia 7
        </Title>
        <ul className="m-0 grid list-none gap-3 p-0">
          {PERGUNTAS_EM_ABERTO.map((p) => {
            const telas = telasDaPergunta(p.id);
            return (
              <li key={p.id} className={CARTAO}>
                <Selo cor="aberta">{`${p.rotulo}: em aberto — decidir no dia 7`}</Selo>
                <p className="m-0 mt-1 font-semibold">{p.pergunta}</p>
                {p.porque !== undefined && <p className="m-0 mt-1">{p.porque}</p>}
                {telas.length > 0 && <p className="m-0 mt-1 text-sm">Nos cartões: {telas.join(', ')}.</p>}
              </li>
            );
          })}
        </ul>
      </section>
    </>
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
        documentos de requisitos do ICA e do Semáforo (não estavam na proposta v5), os pontos que ficaram em aberto
        na reunião de 23/11 e os lugares em que os documentos não fecham a conta ou se contradizem. Para cada um, o
        que o protótipo fez por enquanto e o que falta decidir. Os cartões com o selo{' '}
        <strong>Decidido</strong> trazem a resposta do dono de 25/11 e o que o protótipo já faz com ela.
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
                  {p.decidido && (
                    <p className="m-0 mb-1">
                      <Selo cor="ve">{`Decidido (decisão ${p.decidido.numero})`}</Selo>
                    </p>
                  )}
                  <p className="mb-2 text-sm italic">{p.origem}</p>
                  <dl className="m-0 grid gap-y-1">
                    <dt className="font-semibold">O que dizem</dt>
                    <dd className="m-0 mb-1">{p.oQueDiz}</dd>
                    <dt className="font-semibold">{p.decidido ? 'Como o protótipo resolveu' : 'Como o protótipo resolveu por enquanto'}</dt>
                    <dd className="m-0 mb-1">{p.prototipo}</dd>
                    <dt className="font-semibold">{p.decidido ? 'Decidido' : 'Para decidir'}</dt>
                    <dd className="m-0">{p.decidido ? p.decidido.resposta : p.paraDecidir}</dd>
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
        <QuemVeOQue />
      </section>

      <section aria-labelledby={PARTES[2].id} className="mt-10">
        <Title level={2} id={PARTES[2].id} style={{ fontSize: 22 }}>
          {PARTES[2].titulo}
        </Title>
        <p>
          O Aprender Sistema junta os dados de todos os módulos e entrega para as ferramentas: nenhuma ferramenta tem
          cadastro próprio. O protótipo usa dados simulados com o mesmo formato do cadastro real, para que trocar o
          simulado pelo real seja só trocar a fonte. Abaixo, onde cada dado está hoje. Os marcados &ldquo;Não existe
          ainda&rdquo; são a lista do que precisa ser cadastrado para a versão real.
        </p>
        <ListaDeDados titulo="ICA" id="validar-origem-ica" dados={DADOS_ICA} />
        <ListaDeDados titulo="Semáforo" id="validar-origem-semaforo" dados={DADOS_SEMAFORO} />
        <ListaDeDados titulo="Deslocamento" id="validar-origem-deslocamento" dados={DADOS_DESLOCAMENTO} />
      </section>

      <section aria-labelledby={PARTES[3].id} className="mt-10">
        <Title level={2} id={PARTES[3].id} style={{ fontSize: 22 }}>
          {PARTES[3].titulo}
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
