/**
 * Semáforo — Pesquisa do articulador (coleta 1 do PDF do Semáforo): os 6 itens de 1 a 5, a nota de
 * recomendação de 0 a 10 e o campo aberto, como o articulador ou o secretário municipal veria.
 *
 * Na versão real, articuladores e secretários municipais respondem por link, sem conta. No protótipo não há link: a pesquisa é
 * respondida nesta tela, entra no ciclo atual com a data de "hoje" da demonstração e a cor sugerida do
 * município é recalculada na hora (`useSemaforoDemo`). DADOS SIMULADOS; nada é gravado.
 */
import { useState, type FormEvent, type JSX } from 'react';
import { Link } from 'react-router';
import { Button, Typography } from 'antd';

import { BotoesExportar } from '../ica/componentes/c2/BotoesExportar';
import { CLASSE_CAMPO, CLASSE_ROTULO, formatarDia } from '../ica/componentes/estilos';
import { baixarCsv } from '../ica/exportar';
import { nomeDoMunicipio, sugeridaAgora, type Retorno } from './componentes/corEAlerta';
import { AvisoQuemVe, CampoMunicipio, EtiquetaCor, RetornoDoRegistro } from './componentes/PecasDoRegistro';
import { periodoDoCiclo } from './dados';
import { useSemaforoDemo } from './SemaforoDemoContext';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

/**
 * Os 6 itens do PDF ("Itens da pesquisa do articulador", página 2), na ordem dele, escritos como frase para
 * a escala de concordância. Cada frase mantém o objeto do item do PDF (no comentário ao lado).
 */
const ITENS: readonly { pergunta: string; curto: string }[] = [
  // Cumprimento do cronograma acordado
  { pergunta: 'O cronograma acordado é cumprido.', curto: 'Cronograma' },
  // Qualidade e pertinência das formações
  { pergunta: 'As formações têm qualidade e tratam do que a rede precisa.', curto: 'Formações' },
  // Presença, disponibilidade e comunicação do coordenador
  { pergunta: 'O coordenador está presente, disponível e se comunica bem.', curto: 'Coordenador' },
  // Apoio nas avaliações internas
  { pergunta: 'A equipe apoia a rede nas avaliações internas.', curto: 'Avaliações internas' },
  // Uso das coleções e materiais em sala
  { pergunta: 'Os professores usam as coleções e os materiais em sala.', curto: 'Coleções e materiais em sala' },
  // Percepção de avanço nas aprendizagens
  { pergunta: 'Percebemos avanço nas aprendizagens.', curto: 'Avanço' },
];
const NOTAS_ITEM = [1, 2, 3, 4, 5] as const;
const NOTAS_NPS = Array.from({ length: 11 }, (_, i) => i);
const FUNCOES = ['Articulador(a) municipal', 'Secretário(a) municipal de educação'] as const;
const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

/** 0 = item sem resposta; -1 = nota de recomendação sem resposta (o contexto recusa os dois). */
const ITENS_VAZIOS: readonly number[] = ITENS.map(() => 0);

const CLASSE_RADIO =
  'h-4 w-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark';

function nomeDoMes(mes: string): string {
  const [ano, m] = mes.split('-');
  return `${MESES[Number(m) - 1]} de ${ano}`;
}

interface EscolhaProps {
  legenda: string;
  nome: string;
  opcoes: readonly number[];
  valor: number;
  aoEscolher: (n: number) => void;
  descricao?: string;
  /** Depois de um envio recusado, o grupo sem resposta diz que falta (WCAG 3.3.1). */
  semResposta?: boolean;
}

function Escolha({ legenda, nome, opcoes, valor, aoEscolher, descricao, semResposta = false }: EscolhaProps): JSX.Element {
  const idErro = `${nome}-erro`;
  const descritoPor = [descricao, semResposta ? idErro : undefined].filter(Boolean).join(' ') || undefined;
  return (
    <fieldset
      className={`m-0 rounded border p-3 ${semResposta ? 'border-2 border-[#A8251B]' : 'border-[#d9d9d9]'}`}
      aria-describedby={descritoPor}
    >
      <legend className="px-1 font-semibold">{legenda}</legend>
      {semResposta && (
        <p id={idErro} className="mb-2 mt-0 font-semibold text-[#8A1C14]">
          Falta responder este item.
        </p>
      )}
      <div className="flex flex-wrap gap-x-4 gap-y-2">
        {opcoes.map((n) => (
          <label key={n} className="flex items-center gap-1">
            <input
              type="radio"
              name={nome}
              value={n}
              className={CLASSE_RADIO}
              checked={valor === n}
              onChange={() => aoEscolher(n)}
              aria-invalid={semResposta || undefined}
            />
            {n}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function PesquisaArticulador(): JSX.Element {
  const { dados, situacoes, registrarResposta } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const [municipio, setMunicipio] = useState('');
  const [funcao, setFuncao] = useState<string>(FUNCOES[0]);
  const [identificacao, setIdentificacao] = useState('');
  const [itens, setItens] = useState<readonly number[]>(ITENS_VAZIOS);
  const [nps, setNps] = useState(-1);
  const [comentario, setComentario] = useState('');
  const [retorno, setRetorno] = useState<Retorno | null>(null);
  const [recusado, setRecusado] = useState(false);

  const ciclo = dados.ciclo_atual;
  const periodo = periodoDoCiclo(ciclo);
  const id = Number(municipio);
  const escolhido = dados.municipios.find((m) => m.id === id);
  const situacao = situacoes.find((s) => s.municipio === id);
  const respostasDoCiclo = dados.respostas.filter((r) => r.ciclo === ciclo);

  const enviar = (e: FormEvent): void => {
    e.preventDefault();
    const antes = sugeridaAgora(situacoes, id);
    const r = registrarResposta({
      municipio: id,
      funcao_respondente: funcao,
      identificacao: identificacao.trim() === '' ? null : identificacao.trim(),
      itens,
      nps,
      comentario: comentario.trim(),
    });
    if (!r.ok || !antes || !escolhido) {
      setRetorno({ ok: false, erros: r.ok ? ['Escolha um município da lista.'] : r.erros });
      setRecusado(true);
      return;
    }
    setRecusado(false);
    setRetorno({ ok: true, municipio: id, titulo: `Resposta registrada para ${nomeDoMunicipio(escolhido)}.`, antes });
    setItens(ITENS_VAZIOS);
    setNps(-1);
    setComentario('');
  };

  const baixarPlanilha = (): void => {
    const nome = (municipioId: number) => dados.municipios.find((m) => m.id === municipioId);
    baixarCsv(
      `semaforo_pesquisa_${ciclo}.csv`,
      ['Município', 'UF', 'Ciclo', 'Respondida em', 'No prazo', 'Função', ...ITENS.map((i, n) => `Item ${n + 1}: ${i.curto}`), 'NPS', 'O que melhorar'],
      respostasDoCiclo.map((r) => [
        nome(r.municipio)?.nome ?? '',
        nome(r.municipio)?.uf ?? '',
        r.ciclo,
        formatarDia(r.respondida_em),
        r.no_prazo ? 'Sim' : 'Não',
        r.funcao_respondente,
        ...r.itens,
        r.nps,
        r.comentario,
      ]),
    );
  };

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Pesquisa do articulador
      </Title>
      <AvisoQuemVe tela="pesquisa" />
      <p className="mb-2">
        Na demonstração, sem link: você responde nesta mesma tela, como o articulador ou o secretário municipal veria,
        e a cor do município é recalculada na hora. Na versão real, articuladores e secretários municipais recebem um
        link e respondem sem conta.
      </p>
      <p className="mb-4 text-sm">
        Ciclo {ciclo} ({nomeDoMes(periodo.meses[0])} e {nomeDoMes(periodo.meses[1])}) · prazo para responder:{' '}
        {formatarDia(periodo.prazo_pesquisa)} · hoje: {formatarDia(dados.data_referencia)}
      </p>
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />
      <p className="mb-4 text-sm">
        A planilha traz as {respostasDoCiclo.length} respostas do ciclo atual, com as desta sessão. A identificação de
        quem respondeu não vai para a planilha.
      </p>

      <form onSubmit={enviar} noValidate className="max-w-3xl rounded border border-[#8c8c8c] bg-white p-4">
        <Title level={2} style={{ fontSize: 20 }}>
          Pesquisa de satisfação do programa
        </Title>
        <div className="mb-3 grid gap-3 md:grid-cols-2">
          <CampoMunicipio id="pesquisa-municipio" valor={municipio} aoMudar={setMunicipio} />
          <div>
            <label htmlFor="pesquisa-funcao" className={CLASSE_ROTULO}>
              Sua função
            </label>
            <select id="pesquisa-funcao" className={CLASSE_CAMPO} value={funcao} onChange={(e) => setFuncao(e.target.value)}>
              {FUNCOES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
        </div>
        {situacao && escolhido && (
          <p className="mb-3 text-sm">
            Agora, {nomeDoMunicipio(escolhido)} tem a cor sugerida{' '}
            <EtiquetaCor cor={situacao.ciclos.at(-1)?.resultado.cor ?? 'verde'} /> e a cor em vigor{' '}
            <EtiquetaCor cor={situacao.cor_vigente} />. Respostas deste município no ciclo atual:{' '}
            {respostasDoCiclo.filter((r) => r.municipio === id).length}.{' '}
            <Link to={`/integra/semaforo/municipio/${id}`} state={estadoDaFicha}>Abrir a ficha de {nomeDoMunicipio(escolhido)}</Link>
          </p>
        )}
        <div className="mb-3">
          <label htmlFor="pesquisa-identificacao" className={CLASSE_ROTULO}>
            Seu nome (opcional)
          </label>
          <input
            id="pesquisa-identificacao"
            type="text"
            autoComplete="name"
            className={CLASSE_CAMPO}
            value={identificacao}
            onChange={(e) => setIdentificacao(e.target.value)}
          />
        </div>

        <p id="pesquisa-escala" className="mb-2">
          Para cada frase, marque de 1 a 5: 1 = discordo totalmente, 5 = concordo totalmente.
        </p>
        <div className="space-y-3">
          {ITENS.map((item, i) => (
            <Escolha
              key={item.curto}
              legenda={`${i + 1}. ${item.pergunta}`}
              nome={`pesquisa-item-${i + 1}`}
              opcoes={NOTAS_ITEM}
              valor={itens[i] ?? 0}
              aoEscolher={(n) => setItens((atuais) => atuais.map((v, k) => (k === i ? n : v)))}
              descricao="pesquisa-escala"
              semResposta={recusado && (itens[i] ?? 0) === 0}
            />
          ))}
          <Escolha
            legenda="7. De 0 a 10, quanto você recomendaria a parceria com a Aprender Editora?"
            nome="pesquisa-nps"
            opcoes={NOTAS_NPS}
            valor={nps}
            aoEscolher={setNps}
            semResposta={recusado && nps === -1}
          />
        </div>

        <div className="mb-3 mt-3">
          <label htmlFor="pesquisa-comentario" className={CLASSE_ROTULO}>
            O que precisamos melhorar com urgência?
          </label>
          <textarea
            id="pesquisa-comentario"
            rows={3}
            className={CLASSE_CAMPO}
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
          />
        </div>
        <Button type="primary" htmlType="submit">
          Enviar resposta
        </Button>
        <RetornoDoRegistro retorno={retorno} />
      </form>
    </section>
  );
}
