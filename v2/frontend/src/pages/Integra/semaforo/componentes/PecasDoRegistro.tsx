/**
 * Peças comuns das telas do Semáforo que registram dados (Pesquisa, Relatório mensal) e da tela da Líder:
 * etiqueta de cor, aviso de quem vê na versão real, escolha do município e o retorno do registro
 * ("Antes: Verde → Agora: Vermelho", com o alerta que seria enviado e a cor em vigor, que no vermelho muda na
 * hora: decisões 38 e 39).
 */
import type { JSX } from 'react';

import { CLASSE_CAMPO, CLASSE_ROTULO, formatarDia } from '../../ica/componentes/estilos';
import { QUEM_VE, type ChaveTela } from '../../quemVe';
import { explicarCor, mudancaEntreCiclos, ROTULO_COR, textoSemDado } from '../regras';
import { useSemaforoDemo } from '../SemaforoDemoContext';
import type { CorIndicador } from '../tipos';
import { COR_SEMAFORO, coordenadoresDoMunicipio, destinatariosDaPiora, nomeDoMunicipio, sugeridaAgora, type Retorno } from './corEAlerta';

/** A cor sempre com o nome escrito. */
export function EtiquetaCor({ cor }: { cor: CorIndicador }): JSX.Element {
  const { fundo, texto } = COR_SEMAFORO[cor];
  return (
    <span className="inline-block rounded px-2 py-0.5 text-sm font-semibold" style={{ background: fundo, color: texto }}>
      {ROTULO_COR[cor]}
    </span>
  );
}

/** "Na versão real, quem vê esta tela: …" (matriz de `quemVe.ts`). */
export function AvisoQuemVe({ tela }: { tela: ChaveTela }): JSX.Element {
  return (
    <p role="note" className="mb-4 rounded border-l-4 border-primary-dark bg-[#EEF5F3] p-3 text-sm">
      {QUEM_VE[tela].aviso}
    </p>
  );
}

interface CampoMunicipioProps {
  id: string;
  valor: string;
  aoMudar: (valor: string) => void;
}

/** Lista dos municípios em ordem alfabética, com a cor em vigor escrita. */
export function CampoMunicipio({ id, valor, aoMudar }: CampoMunicipioProps): JSX.Element {
  const { dados, situacoes } = useSemaforoDemo();
  const ordenados = [...dados.municipios].sort((a, b) => nomeDoMunicipio(a).localeCompare(nomeDoMunicipio(b), 'pt-BR'));
  return (
    <div>
      <label htmlFor={id} className={CLASSE_ROTULO}>
        Município
      </label>
      <select id={id} className={CLASSE_CAMPO} value={valor} onChange={(e) => aoMudar(e.target.value)}>
        <option value="">Escolha o município</option>
        {ordenados.map((m) => {
          const cor = situacoes.find((s) => s.municipio === m.id)?.cor_vigente ?? 'verde';
          return (
            <option key={m.id} value={String(m.id)}>
              {nomeDoMunicipio(m)} · em vigor: {ROTULO_COR[cor]}
            </option>
          );
        })}
      </select>
    </div>
  );
}

/**
 * Erros do registro (role="alert"), ou o "antes → agora" da cor sugerida, com o alerta quando piorou. A
 * região do "antes → agora" (role="status") fica sempre montada, vazia até o registro dar certo: região que
 * nasce já com o texto pode não ser anunciada pelo leitor de tela.
 */
export function RetornoDoRegistro({ retorno }: { retorno: Retorno | null }): JSX.Element {
  return (
    <>
      {retorno && !retorno.ok && (
        <div role="alert" className="mt-3 rounded border border-[#A8251B] bg-[#FCE4E2] p-3 text-[#8A1C14]">
          <p className="m-0 font-semibold">Falta corrigir:</p>
          <ul className="m-0 pl-5">
            {retorno.erros.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      )}
      <div role="status">{retorno?.ok && <RegistroFeito retorno={retorno} />}</div>
    </>
  );
}

function RegistroFeito({ retorno }: { retorno: Extract<Retorno, { ok: true }> }): JSX.Element | null {
  const { dados, situacoes } = useSemaforoDemo();
  const municipio = dados.municipios.find((m) => m.id === retorno.municipio);
  const situacao = situacoes.find((s) => s.municipio === retorno.municipio);
  const depois = sugeridaAgora(situacoes, retorno.municipio);
  if (!municipio || !situacao || !depois) return null;
  const { antes } = retorno;
  // Registro que não mexe na cor (ex.: marcar uma reunião): só a frase do que foi feito.
  if (!antes) {
    return (
      <div className="mt-3 rounded border border-[#8c8c8c] bg-white p-3">
        <p className="m-0 font-semibold">{retorno.titulo}</p>
      </div>
    );
  }
  const mudanca = mudancaEntreCiclos(antes.cor, depois.cor);
  const semDado = textoSemDado(depois);
  const gestora = dados.pessoas.find((p) => p.id === municipio.gestora_referencia)?.nome ?? 'Gestora de referência';
  // Decisão 46: os coordenadores de todos os projetos do município.
  const coordenadores = coordenadoresDoMunicipio(municipio, dados.coordenadores).map((c) => c.nome);
  // Decisões 38 e 42: o Comitê desfez o vermelho neste ciclo, e o mesmo alerta não muda a cor de novo
  // (`aplicarVermelhoAutomatico`): a sugerida fica vermelha com outra cor em vigor.
  const vigente = situacao.decisao_vigente;
  const desfeito =
    depois.vermelho_imediato && situacao.cor_vigente !== 'vermelho' && vigente?.ciclo === dados.ciclo_atual && vigente.origem !== 'vermelho_automatico'
      ? vigente
      : null;

  return (
    <div className="mt-3 rounded border border-[#8c8c8c] bg-white p-3">
      <p className="m-0 font-semibold">{retorno.titulo}</p>
      <p className="mb-1 mt-2">
        Cor sugerida do ciclo atual. Antes: <EtiquetaCor cor={antes.cor} /> → Agora: <EtiquetaCor cor={depois.cor} />
        {mudanca.mudanca === 'piorou' && ' (▲ piorou)'}
        {mudanca.mudanca === 'melhorou' && ' (▼ melhorou)'}
      </p>
      <p className="m-0">{explicarCor(depois)}</p>
      {semDado && <p className="m-0 text-sm">{semDado}</p>}
      <p className="m-0 mt-1 text-sm">
        Cor em vigor: {ROTULO_COR[situacao.cor_vigente]}
        {situacao.aguardando_comite && retorno.aguardandoAntes ? ', ' : '. '}
        {/* Decisões 38 e 39; o número fica fora do texto: não diz nada a quem registra. */}
        {situacao.aguardando_comite && situacao.decisao_vigente
          ? retorno.aguardandoAntes
            ? `na hora desde ${formatarDia(situacao.decisao_vigente.publicada_em)}: as tarefas do vermelho começaram nessa data. O Comitê confirma ou desfaz depois.`
            : `Mudou na hora com este registro: as tarefas do vermelho começaram em ${formatarDia(situacao.decisao_vigente.publicada_em)}. O Comitê confirma ou desfaz depois.`
          : desfeito
            ? `O Comitê desfez o vermelho em ${formatarDia(desfeito.publicada_em)}: o mesmo alerta não muda a cor em vigor de novo; só um alerta novo (outro indicador, ou um que piore) muda.`
            : 'Só o vermelho muda a cor em vigor na hora; as outras mudanças esperam o Comitê.'}
      </p>
      {mudanca.mudanca === 'piorou' && depois.cor !== 'verde' && (
        <div className="mt-2 rounded border-l-4 border-[#A8251B] bg-[#FCE4E2] p-2 text-[#8A1C14]">
          <p className="m-0 font-semibold">
            Alerta: {nomeDoMunicipio(municipio)} passou para {ROTULO_COR[depois.cor].toLowerCase()}.
            {/* Decisões 38 a 41 e 52: o vermelho vale na hora e a SPE decide se convoca o extraordinário; o aviso do amarelo continua. */}
            {depois.cor === 'vermelho'
              ? ' A SPE decide se convoca o Comitê extraordinário.'
              : ' O Comitê ordinário confirma a cor, na data marcada pela SPE.'}
          </p>
          {/* Decisão 83: o alerta chega dentro do sistema e por e-mail institucional. */}
          <p className="m-0">
            Seria enviado no sistema e por e-mail institucional para: {destinatariosDaPiora(depois.cor, gestora, coordenadores).join(', ')}.
          </p>
          {retorno.reservado && (
            <p className="m-0">
              {/* Decisão 78: quem lê o momento reservado. */}
              O alerta diz só a cor: o que foi dito no momento reservado não vai junto; a queixa só é lida pela gestora
              de referência principal, pela Líder do NFP e pela SPE.
            </p>
          )}
          <p className="m-0 text-sm">Nada é enviado no protótipo, nem no sistema nem por e-mail: o alerta só aparece aqui.</p>
        </div>
      )}
    </div>
  );
}
