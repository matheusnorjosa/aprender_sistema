/**
 * Única porta de entrada dos dados da Integra.
 *
 * Hoje devolve os DADOS SIMULADOS do gerador (nada é lido nem gravado no banco). Na versão real,
 * esta função lê a API do Aprender Sistema, que junta os dados de todos os módulos, no mesmo
 * formato de `DadosIntegra`; as contas (`ica/calculo.ts`) e as telas não mudam.
 */
import { gerarDadosSimulados } from './gerador';
import type { DadosIntegra } from './tipos';

export function carregarDadosIntegra(): DadosIntegra {
  return gerarDadosSimulados();
}
