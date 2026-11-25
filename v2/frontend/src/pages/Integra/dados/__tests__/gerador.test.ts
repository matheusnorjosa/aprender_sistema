/**
 * Dados simulados da Integra: determinísticos, no formato das entidades reais e calibrados para a
 * história da ata de 23/11/2026 (17 coordenadores: 3 Sobrecarga, 2 Atenção, 6 Adequada, 6 Capacidade).
 * Na demonstração, um dos 17 está sem municípios e fica fora dos estratos (PDF, seção 3): o Painel
 * mostra 5 em Capacidade disponível + 1 sem municípios. A diferença com a ata está no "Para validar".
 */
import { describe, expect, it } from 'vitest';
import {
  PESOS_ORIGINAIS_V5,
  PESOS_REVISADOS,
  calcularEquipe,
  compararPesos,
  medianaDeslocamento,
} from '../../ica/calculo';
import { DESLOCAMENTO_MUNICIPIOS, medianaIdaVolta } from '../deslocamento';
import { carregarDadosIntegra } from '../fonte';
import { SEMENTE_DEMO, criarPrng, gerarDadosSimulados } from '../gerador';
import { contarNomesReais, guardaDeNomesReaisAtiva } from '../../__tests__/nomesReais';

const dados = gerarDadosSimulados();
const atual = calcularEquipe(dados.base, PESOS_REVISADOS);

describe('PRNG com semente', () => {
  it('mesma semente, mesma sequência; outra semente, outra sequência', () => {
    const a = criarPrng(42);
    const b = criarPrng(42);
    const c = criarPrng(43);
    const seqA = [a(), a(), a()];
    expect([b(), b(), b()]).toEqual(seqA);
    expect([c(), c(), c()]).not.toEqual(seqA);
    expect(seqA.every((x) => x >= 0 && x < 1)).toBe(true);
  });
});

describe('gerarDadosSimulados', () => {
  it('é determinístico e é o que a fonte entrega', () => {
    expect(gerarDadosSimulados()).toEqual(dados);
    expect(gerarDadosSimulados(SEMENTE_DEMO)).toEqual(dados);
    expect(carregarDadosIntegra()).toEqual(dados);
    expect(dados.origem).toBe('simulado');
  });

  it('17 coordenadores, 3 gerências com gestora técnica, 4–5 gestoras de referência', () => {
    expect(dados.base.coordenadores).toHaveLength(17);
    expect(dados.gerencias).toHaveLength(3);
    const ids = new Set(dados.pessoas.map((p) => p.id));
    expect(dados.gerencias.every((g) => ids.has(g.gestora_tecnica))).toBe(true);
    const referencia = new Set(dados.base.municipios.map((m) => m.gestora_referencia));
    expect(referencia.has(null)).toBe(false);
    expect(referencia.size).toBeGreaterThanOrEqual(4);
    expect(referencia.size).toBeLessThanOrEqual(5);
  });

  it('os 92 municípios do relatório de deslocamento, com o tempo real de ida e volta e o meio', () => {
    const ms = dados.base.municipios;
    // 92 do relatório + o contrato sem município definido (Amigos do Bem).
    expect(ms).toHaveLength(DESLOCAMENTO_MUNICIPIOS.length + 1);
    expect(DESLOCAMENTO_MUNICIPIOS).toHaveLength(92);
    expect(new Set(ms.map((m) => `${m.nome}-${m.uf}`)).size).toBe(ms.length);
    for (const real of DESLOCAMENTO_MUNICIPIOS) {
      const m = ms.find((x) => x.nome === real.nome && x.uf === real.uf);
      expect(m, `${real.nome}-${real.uf}`).toBeDefined();
      // A medida do ICA é a ida e volta (a mesma das faixas do relatório), não a ida.
      expect(m?.deslocamento_horas).toBe(real.ida_volta_horas);
      expect(m?.deslocamento_meio).toBe(real.meio);
    }
    expect(ms.find((m) => m.nome === 'Petrolina' && m.uf === 'PE')?.deslocamento_meio).toBe('carro');
    expect(ms.find((m) => m.nome === 'Milagres' && m.uf === 'CE')?.deslocamento_meio).toBe('carro');
  });

  it('as carteiras cobrem os 92 municípios do relatório', () => {
    const atendidos = new Set(dados.base.atendimentos.map((a) => a.municipio));
    const fora = dados.base.municipios.filter((m) => !atendidos.has(m.id)).map((m) => m.nome);
    expect(fora).toEqual([]);
  });

  it('suspensos = os 4 com ações suspensas no relatório', () => {
    const suspensos = dados.base.municipios.filter((m) => m.status === 'suspenso').map((m) => `${m.nome}-${m.uf}`);
    const doRelatorio = DESLOCAMENTO_MUNICIPIOS.filter((m) => m.acoes_suspensas).map((m) => `${m.nome}-${m.uf}`);
    expect(doRelatorio).toHaveLength(4);
    expect(suspensos.sort()).toEqual(doRelatorio.sort());
  });

  it('um sem localidade (Amigos do Bem), que usa a mediana: a do relatório (17h45, até 5 min de arredondamento)', () => {
    const semLocalidade = dados.base.municipios.filter((m) => m.deslocamento_horas === null);
    expect(semLocalidade.map((m) => m.nome)).toEqual(['Amigos do Bem']);
    expect(semLocalidade[0]?.deslocamento_meio).toBeNull();
    const mediana = medianaDeslocamento(dados.base.municipios);
    expect(mediana).toBe(medianaIdaVolta(DESLOCAMENTO_MUNICIPIOS));
    expect(Math.abs(mediana - 17.75)).toBeLessThanOrEqual(5 / 60);
  });

  it('distribuição: 3 Sobrecarga (uma perto de 170), 2 Atenção, 6 Adequada, 5 Capacidade + 1 sem municípios', () => {
    expect(atual.porEstrato).toEqual({ sobrecarga: 3, atencao: 2, adequada: 6, capacidade: 5 });
    expect(atual.semMunicipios).toBe(1);
    const maior = Math.max(...atual.coordenadores.map((r) => r.conta.icaExibido));
    expect(maior).toBeGreaterThanOrEqual(165);
    expect(maior).toBeLessThanOrEqual(175);
  });

  it('a história: um "dado incompleto", um "sem municípios", um estimado, um improvável, um contrato sem coordenador', () => {
    expect(atual.coordenadores.filter((r) => r.dadoIncompleto)).toHaveLength(1);
    expect(atual.coordenadores.filter((r) => r.semMunicipios)).toHaveLength(1);
    expect(atual.coordenadores.filter((r) => r.deslocamentoEstimado)).toHaveLength(1);
    expect(atual.coordenadores.filter((r) => r.valoresImprovaveis.length > 0)).toHaveLength(1);
    expect(atual.contratosSemCoordenador).toHaveLength(1);
  });

  it('cada coleção aparece uma vez por município (frente = município × coleção)', () => {
    const chaves = dados.base.atendimentos.map((a) => `${a.municipio}×${a.projeto_geral}`);
    expect(new Set(chaves).size).toBe(chaves.length);
  });

  it('há municípios compartilhados entre coordenadores', () => {
    const compartilhados = atual.coordenadores.flatMap((r) => r.carteira).filter((l) => l.compartilhadoCom.length > 0);
    expect(compartilhados.length).toBeGreaterThan(0);
  });

  it('pessoas fictícias: os nomes são exatamente os da lista fixa do gerador', () => {
    // Garantia que vale no CI: um nome novo só entra mudando esta lista, e a revisão vê. A lista dos
    // nomes reais (ata e PDFs) não fica no repositório; a guarda abaixo só roda na máquina que a tem.
    expect(dados.base.coordenadores.map((c) => c.nome)).toEqual([
      'Lucinéia Barreto',
      'Otávio Rangel',
      'Rosimeire Cavalcante',
      'Heloísa Pimentel',
      'Wanderson Brito',
      'Ivonete Sampaio',
      'Jucélia Montenegro',
      'Edvaldo Quaresma',
      'Marlene Fontenele',
      'Rogério Assunção',
      'Socorro Bezerra Lins',
      'Taciana Holanda',
      'Cleidiane Rocha',
      'Valdir Maciel',
      'Joelma Furtado',
      'Neide Carvalhedo',
      'Priscila Vasconcelos',
    ]);
    expect(dados.pessoas.map((p) => p.nome)).toEqual([
      'Albaniza Coelho',
      'Rejane Tavares',
      'Lindalva Moura',
      'Francisca Diógenes',
      'Mirtes Araújo',
      'Zuleide Paiva',
      'Gerlane Siqueira',
      'Eliane Saboia',
    ]);
  });

  it.skipIf(!guardaDeNomesReaisAtiva)('pessoas fictícias: nenhum nome da ata nem do PDF (guarda local)', () => {
    const nomes = [...dados.base.coordenadores.map((c) => c.nome), ...dados.pessoas.map((p) => p.nome)];
    expect(contarNomesReais(nomes.join(' '))).toBe(0);
  });
});

describe('versões de pesos e histórico', () => {
  it('duas versões (v5 e revisada), vigente a revisada, com autor, data e justificativa', () => {
    expect(dados.versoes_pesos.map((v) => v.pesos)).toEqual([PESOS_ORIGINAIS_V5, PESOS_REVISADOS]);
    expect(dados.versao_vigente).toBe(dados.versoes_pesos[1]?.id);
    for (const v of dados.versoes_pesos) {
      expect(v.autor).not.toBe('');
      expect(v.justificativa).not.toBe('');
      expect(Number.isNaN(Date.parse(v.criada_em))).toBe(false);
    }
  });

  it('o comparativo v5 × revisada tem quem muda de estrato', () => {
    const c = compararPesos(dados.base, PESOS_ORIGINAIS_V5, PESOS_REVISADOS);
    expect(c.mudaramDeEstrato.length).toBeGreaterThanOrEqual(1);
  });

  it('3 semestres; o último é a carteira atual', () => {
    expect(dados.historico.map((h) => h.semestre)).toEqual(['2025.2', '2026.1', '2026.2']);
    expect(dados.semestre_atual).toBe('2026.2');
    expect(dados.historico[2]?.base).toEqual(dados.base);
    const ids = new Set(dados.versoes_pesos.map((v) => v.id));
    expect(dados.historico.every((h) => ids.has(h.versao_pesos))).toBe(true);
  });

  it('remanejamentos aplicados batem com os retratos dos semestres', () => {
    expect(dados.remanejamentos.length).toBeGreaterThanOrEqual(2);
    for (const r of dados.remanejamentos) {
      expect(r.status).toBe('aplicado');
      const i = dados.historico.findIndex((h) => h.semestre === r.semestre);
      expect(i).toBeGreaterThan(0);
      const antes = dados.historico[i - 1]?.base;
      const depois = dados.historico[i]?.base;
      for (const m of r.movimentos) {
        const dono = (b: typeof antes) => b?.atendimentos.filter((a) => a.municipio === m.municipioId).map((a) => a.coordenador);
        expect(dono(antes)).toContain(m.deCoordenadorId);
        expect(dono(depois)).toContain(m.paraCoordenadorId);
        expect(dono(depois)).not.toContain(m.deCoordenadorId);
      }
    }
  });

  it('suspensos estavam ativos no semestre anterior', () => {
    const anterior = dados.historico[1]?.base;
    for (const m of dados.base.municipios.filter((x) => x.status === 'suspenso')) {
      expect(anterior?.municipios.find((x) => x.id === m.id)?.status).toBe('ativo');
    }
  });

  it('cada semestre calcula sem erro e tem coordenadores com carteira', () => {
    for (const h of dados.historico) {
      const v = dados.versoes_pesos.find((x) => x.id === h.versao_pesos);
      const r = calcularEquipe(h.base, v?.pesos ?? PESOS_REVISADOS);
      expect(r.dispersao.quantidade).toBeGreaterThanOrEqual(15);
    }
  });
});
