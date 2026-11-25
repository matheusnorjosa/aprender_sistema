/**
 * Semáforo — Painel da gestora de referência (DADOS SIMULADOS).
 *
 * Escolhida a gestora (também pelo endereço, `?gestora=<id>`): as tarefas em aberto da carteira dela,
 * com o que vence hoje primeiro, depois as vencidas e as que estão no prazo (do prazo mais perto ao mais
 * longe), as pendências da carteira (pesquisa sem resposta no ciclo, reunião de escuta a agendar; as atas o
 * protótipo não acompanha) e os municípios da carteira com a cor em vigor. Sem escolha, abre na primeira gestora
 * que tem tarefa vencendo hoje ou vencida. Requisitos: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf, seções 5 e 7.
 */
import type { JSX } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { CLASSE_CAMPO, CLASSE_ROTULO, formatarDia } from '../ica/componentes/estilos';
import { AvisoQuemVe } from './componentes/PecasDoRegistro';
import { CorComNome, Mudanca } from './componentes/PecasDoAcompanhamento';
import { mesesDoCiclo, periodoDoCiclo, type MunicipioSemaforo, type SituacaoMunicipio } from './dados';
import { estadoDaTarefa, reuniaoEmDia } from './regras';
import { useSemaforoDemo } from './SemaforoDemoContext';
import type { Cor, EstadoTarefa, TarefaResposta } from './tipos';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const GRAVIDADE: Record<Cor, number> = { vermelho: 0, amarelo: 1, verde: 2 };

const GRUPOS: readonly { estado: Exclude<EstadoTarefa, 'concluida'>; titulo: string; vazio: string }[] = [
  { estado: 'vence_hoje', titulo: 'Vence hoje', vazio: 'Nada vence hoje.' },
  { estado: 'vencida', titulo: 'Vencidas', vazio: 'Nenhuma tarefa vencida.' },
  { estado: 'no_prazo', titulo: 'No prazo', vazio: 'Nenhuma tarefa no prazo.' },
];

interface LinhaMunicipio {
  m: MunicipioSemaforo;
  s: SituacaoMunicipio;
  abertas: number;
}

const nomeDe = (m: MunicipioSemaforo): string => `${m.nome}-${m.uf}`;

export default function PainelGestora(): JSX.Element {
  const { dados, situacoes } = useSemaforoDemo();
  const [busca, setBusca] = useSearchParams();
  const estadoDaFicha = useEstadoDaFicha();
  const hoje = dados.data_referencia;

  const carteiraDe = (gestora: number): MunicipioSemaforo[] => dados.municipios.filter((m) => m.gestora_referencia === gestora);
  const tarefasDe = (gestora: number): TarefaResposta[] => {
    const ids = new Set(carteiraDe(gestora).map((m) => m.id));
    return dados.tarefas.filter((t) => ids.has(t.municipio));
  };
  const abertasDe = (gestora: number): TarefaResposta[] => tarefasDe(gestora).filter((t) => t.concluida_em === null);
  const urgente = (t: TarefaResposta): boolean => ['vence_hoje', 'vencida'].includes(estadoDaTarefa(t, hoje));

  const pedida = dados.pessoas.find((p) => String(p.id) === busca.get('gestora'));
  const gestora = pedida ?? dados.pessoas.find((p) => tarefasDe(p.id).some(urgente)) ?? dados.pessoas[0];

  if (!gestora) {
    return (
      <section aria-labelledby="semaforo-gestora-titulo">
        <Title level={1} id="semaforo-gestora-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
          Painel da gestora de referência
        </Title>
        <p>Nenhuma gestora de referência nos dados.</p>
      </section>
    );
  }

  const carteira = carteiraDe(gestora.id);
  const todas = tarefasDe(gestora.id);
  const concluidas = todas.filter((t) => t.concluida_em !== null).length;
  const municipioDe = (id: number): MunicipioSemaforo | undefined => carteira.find((m) => m.id === id);

  const linhas: LinhaMunicipio[] = carteira
    .map((m) => ({
      m,
      s: situacoes.find((x) => x.municipio === m.id)!,
      abertas: todas.filter((t) => t.municipio === m.id && t.concluida_em === null).length,
    }))
    .sort((a, b) => GRAVIDADE[a.s.cor_vigente] - GRAVIDADE[b.s.cor_vigente] || a.m.nome.localeCompare(b.m.nome, 'pt-BR'));

  // Pendências (seção 7 do PDF): na ordem da carteira (o pior primeiro).
  const semResposta = linhas
    .map((l) => l.m)
    .filter((m) => !dados.respostas.some((r) => r.municipio === m.id && r.ciclo === dados.ciclo_atual));
  const aAgendar = linhas
    .map(({ m, s }) => {
      const datas = dados.reunioes.filter((x) => x.municipio === m.id && x.data <= hoje).map((x) => x.data);
      return { m, s, datas, ultima: datas.reduce<string | null>((max, d) => (max === null || d > max ? d : max), null) };
    })
    .filter(({ s, datas }) => !reuniaoEmDia(datas, s.cor_vigente, hoje));

  const colunas: ColunaResponsiva<LinhaMunicipio>[] = [
    {
      title: 'Município',
      key: 'municipio',
      className: 'break-words',
      render: (_v, l) => <Link to={`/integra/semaforo/municipio/${l.m.id}`} state={estadoDaFicha}>{nomeDe(l.m)}</Link>,
    },
    { title: 'Em vigor', key: 'vigente', width: 110, render: (_v, l) => <CorComNome cor={l.s.cor_vigente} /> },
    {
      title: 'Sugerida agora',
      key: 'sugerida',
      width: 130,
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, l) => <CorComNome cor={l.s.ciclos.at(-1)!.resultado.cor} />,
    },
    {
      title: 'Desde o ciclo anterior',
      key: 'mudanca',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, l) => {
        const atual = l.s.ciclos.at(-1)!;
        return <Mudanca anterior={l.s.ciclos.at(-2)?.decisao?.cor_publicada ?? null} atual={atual.decisao?.cor_publicada ?? atual.resultado.cor} />;
      },
    },
    { title: 'Tarefas em aberto', key: 'abertas', width: 140, responsive: VISIVEL_A_PARTIR.md, render: (_v, l) => l.abertas },
  ];

  return (
    <section aria-labelledby="semaforo-gestora-titulo">
      <Title level={1} id="semaforo-gestora-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Painel da gestora de referência
      </Title>
      <AvisoQuemVe tela="gestora" />

      <div className="mb-4 max-w-md">
        <label htmlFor="semaforo-gestora" className={CLASSE_ROTULO}>
          Gestora de referência
        </label>
        <select
          id="semaforo-gestora"
          className={CLASSE_CAMPO}
          value={String(gestora.id)}
          onChange={(e) => setBusca({ gestora: e.target.value }, { replace: true })}
        >
          {dados.pessoas.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.nome} ({abertasDe(p.id).length} em aberto)
            </option>
          ))}
        </select>
      </div>
      <p>
        Hoje é {formatarDia(hoje)}. {carteira.length} municípios na carteira; {concluidas}{' '}
        {concluidas === 1 ? 'tarefa já concluída' : 'tarefas já concluídas'}.
      </p>

      {GRUPOS.map(({ estado, titulo, vazio }) => {
        const doGrupo = todas.filter((t) => estadoDaTarefa(t, hoje) === estado).sort((a, b) => a.prazo_em.localeCompare(b.prazo_em));
        const idTitulo = `semaforo-gestora-${estado}`;
        return (
          <section key={estado} aria-labelledby={idTitulo} className="mb-4">
            <Title level={2} id={idTitulo} style={{ fontSize: 20 }}>
              {titulo}
            </Title>
            {doGrupo.length === 0 ? (
              <p>{vazio}</p>
            ) : (
              <ul className="m-0 grid list-none gap-2 p-0">
                {doGrupo.map((t) => {
                  const m = municipioDe(t.municipio);
                  return (
                    <li key={`${t.municipio}-${t.chave}-${t.criada_em}`} className="rounded border border-[#d9d9d9] bg-white p-3">
                      <strong>{t.titulo}</strong>
                      {' · '}
                      {m ? <Link to={`/integra/semaforo/municipio/${m.id}`} state={estadoDaFicha}>{nomeDe(m)}</Link> : `Município ${t.municipio}`}
                      {' · '}prazo {formatarDia(t.prazo_em)}
                      {' · '}
                      <CorComNome cor={t.cor} rotulo="Da cor" />
                      <span className="block text-sm text-[#3D3D3D]">Criada em {formatarDia(t.criada_em)}, quando a cor foi publicada.</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}

      <section aria-labelledby="semaforo-gestora-pendencias" className="mb-4">
        <Title level={2} id="semaforo-gestora-pendencias" style={{ fontSize: 20 }}>
          Pendências da carteira
        </Title>
        <div className="grid gap-4 md:grid-cols-3">
          <section aria-labelledby="semaforo-pendencia-pesquisa">
            <Title level={3} id="semaforo-pendencia-pesquisa" style={{ fontSize: 16 }}>
              Pesquisa sem resposta
            </Title>
            <p className="mb-2 text-sm">
              Ciclo {dados.ciclo_atual} ({mesesDoCiclo(dados.ciclo_atual)}) · prazo para responder:{' '}
              {formatarDia(periodoDoCiclo(dados.ciclo_atual).prazo_pesquisa)}.
            </p>
            {semResposta.length === 0 ? (
              <p>Todos os municípios da carteira já responderam.</p>
            ) : (
              <ul aria-label={`Pesquisa sem resposta no ciclo ${dados.ciclo_atual}`} className="m-0 pl-5">
                {semResposta.map((m) => (
                  <li key={m.id}>
                    <Link to={`/integra/semaforo/municipio/${m.id}`} state={estadoDaFicha}>{nomeDe(m)}</Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-labelledby="semaforo-pendencia-reuniao">
            <Title level={3} id="semaforo-pendencia-reuniao" style={{ fontSize: 16 }}>
              Reunião de escuta a agendar
            </Title>
            <p className="mb-2 text-sm">Sem reunião nos últimos 6 meses no verde, ou nos últimos 3 no amarelo e no vermelho.</p>
            {aAgendar.length === 0 ? (
              <p>Nenhuma reunião de escuta atrasada.</p>
            ) : (
              <ul aria-label="Reunião de escuta a agendar" className="m-0 pl-5">
                {aAgendar.map(({ m, s, ultima }) => (
                  <li key={m.id}>
                    <Link to={`/integra/semaforo/municipio/${m.id}`} state={estadoDaFicha}>{nomeDe(m)}</Link> ·{' '}
                    <CorComNome cor={s.cor_vigente} rotulo="Em vigor" /> · última:{' '}
                    {ultima ? formatarDia(ultima) : 'nenhuma registrada'}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-labelledby="semaforo-pendencia-atas">
            <Title level={3} id="semaforo-pendencia-atas" style={{ fontSize: 16 }}>
              Atas a registrar
            </Title>
            <p>
              O protótipo não acompanha: a reunião de escuta entra já com o que ficou combinado. O prazo da ata (5 dias
              úteis, sugestão do PDF) está em &ldquo;Para validar no dia 7&rdquo;.
            </p>
          </section>
        </div>
      </section>

      <Title level={2} style={{ fontSize: 20 }}>
        Municípios da carteira
      </Title>
      <ResponsiveTable<LinhaMunicipio>
        caption={<span className="sr-only">Municípios de {gestora.nome}</span>}
        rowKey={(l) => l.m.id}
        columns={colunas}
        dataSource={linhas}
        pagination={false}
        locale={{ emptyText: 'Nenhum município nesta carteira.' }}
        nomeDaLinha={(l) => nomeDe(l.m)}
      />
    </section>
  );
}
