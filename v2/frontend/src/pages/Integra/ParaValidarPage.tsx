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
        prototipo:
          'Não há envio de link no protótipo, então o prazo é fixo: vale a resposta até o dia 20 do segundo mês do ciclo (no ciclo de novembro e dezembro, até 20/12). A tela da pesquisa mostra esse prazo. Contar 10 dias a partir do envio fica para a versão real, quando houver o link.',
        paraDecidir: 'Confirmar os 10 dias a partir do envio.',
      },
      {
        titulo: 'Relatório mensal até o 5º dia útil do mês seguinte',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'O coordenador manda o relatório mensal até o 5º dia útil do mês seguinte.',
        prototipo:
          'O relatório entra a qualquer momento, sem prazo e sem aviso de atraso. As formações e visitas realizadas sobre as previstas dão o cronograma cumprido do ciclo.',
        paraDecidir: 'Confirmar o prazo.',
      },
      {
        titulo: 'Ata da reunião de escuta em até 5 dias úteis',
        origem: 'Sugestão do PDF do Semáforo (seção 2)',
        oQueDiz: 'A gestora de referência registra a ata da reunião de escuta em até 5 dias úteis.',
        prototipo:
          'A reunião é registrada com a data em que aconteceu (até hoje), o que ficou combinado e o momento reservado, sem prazo para o registro e sem aviso de atraso.',
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
        prototipo:
          'Segue esta regra: o NPS é a média das notas, a média da pesquisa junta os 6 itens de todas as respostas, e o município respondeu quando pelo menos um articulador respondeu no prazo.',
        paraDecidir: 'Confirmar a média e o "pelo menos um".',
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
        titulo: 'Média, NPS e cronograma: a cor sai do número que aparece na tela',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 3) não fecha a conta',
        oQueDiz:
          'O PDF dá as faixas com números redondos (média 4,0 ou mais é verde e 3,0 a 3,9 é amarelo; cronograma 90% ou mais é verde e 70% a 89% é amarelo) e não diz o que fazer com um valor no meio, como 3,95 ou 89,5%.',
        prototipo:
          'A cor sai do número que aparece na tela, como no ICA: a média e o NPS com uma casa decimal, o cronograma em % sem casa. Assim, 3,95 aparece "4,0" e fica verde; 89,5% aparece "90%" e fica verde.',
        paraDecidir: 'Confirmar que vale o número que aparece na tela.',
      },
      {
        titulo: 'NPS: média das notas, e as notas quebradas',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 3) não fecha a conta',
        oQueDiz:
          'O PDF usa a média das notas de 0 a 10, e não o NPS de costume (quem dá 9 ou 10 menos quem dá 0 a 6). As faixas são: 9 ou 10 é verde, 7 ou 8 é amarelo, 0 a 6 é vermelho.',
        prototipo:
          'Segue a média do PDF. Uma média quebrada fica na faixa de baixo até chegar à nota de cima: 8,5 é amarelo; 6,9 é vermelho.',
        paraDecidir: 'Confirmar a média e o corte das notas quebradas.',
      },
      {
        titulo: 'Ocorrências no trimestre: que trimestre?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 3) não fecha a conta',
        oQueDiz: 'O indicador conta as ocorrências "no trimestre", mas o ciclo do Semáforo é de dois meses.',
        prototipo:
          'Conta os 3 meses corridos até a data da conta: no ciclo fechado, até o último dia do ciclo; no ciclo atual, até hoje. Não usa o trimestre do calendário (janeiro a março, abril a junho...).',
        paraDecidir: '3 meses corridos ou trimestre do calendário?',
      },
      {
        titulo: 'Prazos das tarefas: horas, dias corridos e dias úteis',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz:
          'No vermelho: contato em 48 h, reunião com a Secretaria em 5 dias, plano de ação em 15 dias e devolutiva em 30 dias. No amarelo: contato com o articulador em até 10 dias úteis.',
        prototipo:
          'O prazo conta a partir do dia em que o Comitê publica a cor. 48 h viram 2 dias. Os prazos de 5, 15 e 30 dias são dias corridos e podem cair num domingo: uma cor publicada em 24/11/2026 dá a reunião com a Secretaria em 29/11, um domingo. Os dias úteis contam de segunda a sexta, sem feriados, e o dia da publicação não conta.',
        paraDecidir: 'Os prazos em dias são corridos ou úteis? Feriados contam?',
      },
      {
        titulo: '"No bimestre" e "no semestre": a partir de quando?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz: 'A observação de uma formação (amarelo) vale "no bimestre", e a visita técnica (vermelho), "no semestre".',
        prototipo:
          'Viraram 2 e 6 meses depois da publicação. Quando o dia não existe no mês final, vale o último dia do mês (31/12 mais 2 meses dá 28/02).',
        paraDecidir: 'O prazo conta da publicação ou vai até o fim do bimestre ou do semestre do calendário?',
      },
      {
        titulo: 'Três amarelos também mudam a cor na hora?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 4) não fecha a conta',
        oQueDiz:
          'Um indicador em vermelho deixa o município vermelho na hora, e três amarelos no mesmo ciclo também valem vermelho. A tabela de alertas diz "Município passa a vermelho: na hora", sem separar os dois casos.',
        prototipo:
          'Nos dois casos, a cor sugerida vira vermelho assim que o dado chega, e a tela de registro avisa que o Comitê confirma a cor em reunião extraordinária. A regra, porém, só marca como "vermelho na hora" o caso de um indicador em vermelho.',
        paraDecidir: 'Três amarelos também chamam o Comitê extraordinário, ou esperam o fim do ciclo?',
      },
      {
        titulo: 'A volta ao verde depois de um alerta',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 4) não fecha a conta',
        oQueDiz: 'O município só volta ao verde depois de 2 ciclos seguidos sem alerta.',
        prototipo:
          'A contagem parte da cor que o Comitê publicou no ciclo anterior. Se foi amarelo ou vermelho, o município fica amarelo "em recuperação" até somar 2 ciclos seguidos sem alerta. Só conta ciclo fechado: o ciclo em andamento (com a pesquisa ainda no prazo) não soma como ciclo sem alerta, e até ele fechar continua sugerida a cor publicada. No ciclo em andamento, a cor só muda na hora para piorar: um vermelho vale na hora, e um amarelo também, se a cor publicada era verde. Sair do vermelho espera o ciclo fechar. Se o Comitê publicou verde, volta direto. Indicador sem dado não conta como alerta.',
        paraDecidir:
          'Confirmar os 2 ciclos, que a contagem parte da cor publicada pelo Comitê e que o ciclo em andamento só conta quando fechar.',
      },
      {
        titulo: 'Quem faz cada tarefa de cada cor',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz:
          'O PDF diz quem age em cada cor, e não em cada tarefa. No vermelho, o "contato em 48 h" não diz com quem.',
        prototipo:
          'A tarefa do vermelho se chama "Contato com o município". As rotinas (pesquisa a cada 2 meses, reunião de escuta a cada 6 ou 3 meses, acompanhamento a cada 15 dias) aparecem só como texto, sem prazo nem situação.',
        paraDecidir: 'Quem faz cada tarefa? O contato em 48 h é com quem?',
      },
      {
        titulo: 'Quando o Comitê publica a cor',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seção 6) não marca o dia',
        oQueDiz:
          'O Comitê ordinário se reúne depois que a pesquisa do ciclo fecha. No vermelho imediato, o sistema muda a cor na hora, avisa a gestora de referência e a SPE e permite convocar o Comitê em caráter extraordinário.',
        prototipo:
          'Cada ciclo fechado foi publicado numa sexta-feira depois do fim do ciclo (o de setembro e outubro, em 06/11/2026). O vermelho imediato de Horizonte-CE foi publicado em reunião extraordinária em 02/12/2026, sem esperar o fim do ciclo.',
        paraDecidir: 'Em que dia o Comitê publica? Todo vermelho imediato chama reunião extraordinária?',
      },
      {
        titulo: 'Vermelho imediato: a cor em vigor muda na hora ou espera o Comitê?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (seção 4) diz as duas coisas',
        oQueDiz:
          'No vermelho imediato, o PDF diz: "O sistema muda a cor na hora, avisa a gestora de referência e a SPE e permite convocar o Comitê em caráter extraordinário". Na atualização da cor, diz: "O sistema calcula uma cor sugerida; o Comitê confirma e publica".',
        prototipo:
          'A cor sugerida vira vermelho na hora, e a tela de registro mostra o alerta. A cor em vigor (a das contagens, do painel da gestora e da ficha do município) só muda quando o Comitê publica, e as tarefas do vermelho nascem nessa publicação.',
        paraDecidir: 'No vermelho imediato, a cor em vigor muda sozinha, antes do Comitê? Se sim, as tarefas do vermelho já nascem nessa hora?',
      },
      {
        titulo: 'A tarefa só nasce quando a cor em vigor muda',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seção 5) não fecha a conta',
        oQueDiz:
          'O PDF lista as tarefas de cada cor, mas não diz o que acontece quando o Comitê confirma a mesma cor no ciclo seguinte.',
        prototipo:
          'As tarefas nascem só quando a cor em vigor muda. Se o Comitê confirma o mesmo vermelho no ciclo seguinte, o "contato em 48 h" não volta a abrir.',
        paraDecidir: 'Confirmar a mesma cor abre de novo as tarefas da cor?',
      },
      {
        titulo: 'O amarelo "em recuperação" recebe as tarefas do amarelo',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seções 4 e 5) não fecha a conta',
        oQueDiz:
          'O município que sai do vermelho fica amarelo "em recuperação" até somar 2 ciclos sem alerta. O PDF dá as tarefas do amarelo, mas não diz se elas valem também para quem está em recuperação.',
        prototipo:
          'O amarelo "em recuperação" recebe as mesmas tarefas do amarelo: contato com o articulador em até 10 dias úteis e observação de uma formação no bimestre.',
        paraDecidir: 'O amarelo em recuperação tem as tarefas do amarelo, outras mais leves ou nenhuma?',
      },
      {
        titulo: 'Um relatório mensal por município ou por coordenador?',
        origem: 'Escolha do protótipo: o PDF do Semáforo (seção 2) não fecha a conta',
        oQueDiz:
          'O relatório mensal é do coordenador. Alguns municípios têm mais de um contrato, cada um com o seu coordenador.',
        prototipo:
          'O Semáforo usa um coordenador por município: o do primeiro contrato que tem coordenador. Só ele manda o relatório mensal desse município.',
        paraDecidir: 'Cada coordenador manda o seu relatório? Se sim, como juntar os números no cronograma do município?',
      },
      {
        titulo: 'O "cronograma confirmado" da reunião de escuta entra na conta?',
        origem: 'Leitura do protótipo: o PDF do Semáforo (coleta 4) não fecha a conta',
        oQueDiz: 'Na reunião de escuta (coleta 4), a gestora registra se o cronograma foi confirmado com a Secretaria.',
        prototipo:
          'A confirmação aparece na ficha do município, mas não entra na conta: o cronograma cumprido usa só as formações e as visitas realizadas sobre as previstas dos relatórios mensais.',
        paraDecidir: 'A confirmação muda o número do cronograma ou só ajuda a leitura do Comitê?',
      },
      {
        titulo: 'Os indicadores da Líder do NFP que o protótipo não mede',
        origem: 'Lacuna do protótipo: o PDF do Semáforo (seção 7) lista, o protótipo ainda não calcula',
        oQueDiz:
          'Para a Líder do NFP, o PDF lista: satisfação média e NPS por município, coordenador, gestora e projeto; reuniões de escuta no período (meta 100%); taxa de resposta à pesquisa (meta 80% ou mais); tempo médio de resposta a ocorrências (meta 48 h ou menos); municípios em vermelho com plano de ação no prazo; convergência entre a pesquisa e as ocorrências; e a distribuição do ICA (meta entre 70 e 130).',
        prototipo:
          'A tela Indicadores da Líder mostra a taxa de resposta, as reuniões no período, a satisfação média e o NPS (por coordenador e por gestora na tela; por município na planilha), o plano de ação no prazo e a distribuição do ICA. Não mede o tempo médio de resposta a ocorrências (as ocorrências não guardam quando foram respondidas), a convergência entre a pesquisa e as ocorrências (o PDF não diz como medir) nem a satisfação por projeto (a pesquisa não diz que projeto o articulador avalia).',
        paraDecidir:
          'Como medir a convergência? A ocorrência passa a guardar quando foi respondida? A pesquisa pergunta o projeto avaliado?',
      },
      {
        titulo: 'Painel da gestora: atas a registrar',
        origem: 'Lacuna do protótipo: o PDF do Semáforo (seção 7) lista, o protótipo não acompanha',
        oQueDiz:
          'O painel da gestora de referência mostra as pendências da carteira: pesquisas sem resposta, reuniões a agendar e atas a registrar.',
        prototipo:
          'O painel mostra as pesquisas sem resposta no ciclo atual e as reuniões de escuta a agendar (sem reunião nos últimos 6 meses no verde, ou nos últimos 3 no amarelo e no vermelho). Atas a registrar não aparecem: a reunião entra já com o que ficou combinado, então não há ata pendente.',
        paraDecidir: 'A reunião de escuta é marcada antes e a ata registrada depois (com o prazo de 5 dias úteis)?',
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
      },
      {
        titulo: 'Craíbas-AL: Longo ou Muito longo?',
        origem: 'Contradição dentro do PDF do Deslocamento (lista de municípios × limite das faixas)',
        oQueDiz:
          'Craíbas-AL tem 18h00 de ida e volta e o relatório a põe em "Muito longo". Pelo limite do próprio relatório (Longo até 18h), seria "Longo", como Cairu-BA e Indianópolis-MG, que também têm 18h00.',
        prototipo: 'Segue o relatório: Craíbas-AL fica em "Muito longo". Só assim as contagens por faixa batem com as do relatório.',
        paraDecidir: 'Craíbas-AL é Longo ou Muito longo?',
      },
      {
        titulo: 'Mediana: coluna Ida (17h45) ou coluna Ida e volta (17h48)?',
        origem: 'Diferença dentro do PDF do Deslocamento (página 1 × tabela de municípios)',
        oQueDiz:
          'A página 1 informa a mediana de 17h45 de ida e volta. O relatório calcula a mediana pela coluna Ida e dobra: dá exatamente 17h45. Com a coluna Ida e volta da mesma tabela, que o relatório arredondou à parte, a mediana dá 17h47min30s, que arredonda para 17h48.',
        prototipo:
          'As telas do Deslocamento mostram os dois números. O ICA usa a coluna Ida e volta (17h48) para o município sem localidade definida.',
        paraDecidir: 'Qual coluna o ICA usa para o município sem localidade: a Ida dobrada (17h45, como o relatório) ou a Ida e volta (17h48)?',
      },
      {
        titulo: 'Amigos do Bem: em que município e estado?',
        origem: 'Lacuna do PDF do Deslocamento (lista de contratos)',
        oQueDiz: 'O relatório lista o contrato Amigos do Bem sem município e, por isso, sem tempo de deslocamento.',
        prototipo:
          'Aparece como "Amigos do Bem-CE": o CE entrou só porque o cadastro pede um estado e não conta como estado na carteira do coordenador. No ICA, ele usa a mediana, marcado como estimado.',
        paraDecidir: 'Em que município e estado fica o Amigos do Bem? Que tempo de referência ele usa?',
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
    dado: 'Coordenador de cada município',
    onde: ['aprender'],
    detalhe: 'O coordenador de cada município no Plano Anual e a equipe de cada gerência.',
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
    detalhe: 'O município não tem status de contrato nem a data da mudança. Suspenso não conta no ICA.',
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
        que o protótipo fez por enquanto e o que falta decidir.
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
