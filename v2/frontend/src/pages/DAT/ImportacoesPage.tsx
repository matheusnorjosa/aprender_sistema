/**
 * DAT > Importações — página unificada de importações em massa.
 *
 * Plano DAT-Imports (2026-04-29) — PR-B (1º).
 *
 * Centraliza os 11 fluxos de upload de planilha do projeto em uma única
 * página, organizados por categoria. Substitui (em passos seguintes — PR-D)
 * os botões espalhados em ControlePage, ComprasPage, Disponibilidade e
 * DeslocamentosPage.
 *
 * Categorias:
 * - Cadastros base: Usuários, Municípios, Coleções, Cadastros DAT, Vínculos
 * - Operacional: Compras, Ações, Eventos, Produtos
 * - Disponibilidade: Bloqueios, Deslocamentos
 *
 * Acesso: DAT/superuser only (guard em AppRoutes via canDAT).
 *
 * Reutiliza:
 * - `ImportUploader` para UI de cada card
 * - Funções `import*` de `api/ops.ts` (sem alteração)
 *
 * Não toca em:
 * - ASQ-005 async (`/api/imports/bloqueios/`) — Phase 2 separada
 * - PR municípios IBGE (#1298 já mergeado)
 * - Lógica interna dos services de import (PR-A1 trata gate backend)
 */

import { Card, Col, Row, Typography } from 'antd';

import {
  importAcoes,
  importBloqueios,
  importCadastros,
  importColecoes,
  importCompras,
  importDeslocamentos,
  importEquipeGerencia,
  importEventos,
  importMunicipios,
  importProdutos,
  importUsuarios,
} from '../../api/ops';
import type { ImportResult } from '../../api/ops';
import ImportUploader from '../../components/ImportUploader';
import type { ApplyResult, ValidationResult } from '../../components/ImportUploader';

const { Title, Text } = Typography;

/** Helper para converter ImportResult → ValidationResult (mesmo padrão de ControlePage). */
function toValidationResult(result: ImportResult): ValidationResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
    errors: result.errors.map((e) => `Linha ${e.row}: ${e.message}`),
  };
}

/** Helper para converter ImportResult → ApplyResult. */
function toApplyResult(result: ImportResult): ApplyResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
  };
}

/**
 * Configuração canônica dos 11 cards de importação.
 *
 * Cada card recebe label, description e os callbacks de dry-run/apply ligados
 * a uma função existente em `api/ops.ts`. Mudar conteúdo de um card não
 * requer mexer em ImportUploader nem em outras páginas — escopo isolado.
 */
interface ImportCard {
  key: string;
  label: string;
  description: string;
  importFn: (file: File, dryRun?: boolean) => Promise<ImportResult>;
}

const CADASTROS_BASE: ImportCard[] = [
  {
    key: 'usuarios',
    label: 'Importar USUÁRIOS',
    description: 'CSV/XLSX: cpf, nome (obrigatórios); email, telefone, cargo, grupos (opcionais)',
    importFn: importUsuarios,
  },
  {
    key: 'municipios',
    label: 'Importar MUNICÍPIOS',
    description: 'CSV/XLSX: nome, uf (obrigatórios); ibge_code, ativo (opcionais)',
    importFn: importMunicipios,
  },
  {
    key: 'colecoes',
    label: 'Importar COLEÇÕES',
    description: 'CSV/XLSX: codigo, nome, projeto (obrigatórios)',
    importFn: importColecoes,
  },
  {
    key: 'cadastros-dat',
    label: 'Importar CADASTROS DAT',
    description: 'CSV/XLSX consolidado de cadastros administrados pelo DAT',
    importFn: importCadastros,
  },
  {
    key: 'vinculos',
    label: 'Importar VÍNCULOS (Equipe-Gerência)',
    description: 'CSV/XLSX: usuario (cpf ou email), gerencia, funcao (obrigatórios)',
    importFn: importEquipeGerencia,
  },
];

const OPERACIONAL: ImportCard[] = [
  {
    key: 'compras',
    label: 'Importar COMPRAS',
    description: 'CSV/XLSX: codigo, produto, quant, municipio, uf, data, uso',
    importFn: importCompras,
  },
  {
    key: 'acoes',
    label: 'Importar AÇÕES',
    description: 'CSV/XLSX de Ações de Controle (Município, Projeto, Coordenador, Datas, Observação)',
    importFn: importAcoes,
  },
  {
    key: 'eventos',
    label: 'Importar EVENTOS',
    description:
      'CSV/XLSX: municipio, projeto, tipo_evento, data, hora_inicio, hora_fim, coordenador, formador1-5',
    importFn: importEventos,
  },
  {
    key: 'produtos',
    label: 'Importar PRODUTOS',
    description: 'CSV/XLSX: codigo, nome, projeto (obrigatórios), descricao (opcional)',
    importFn: importProdutos,
  },
];

const DISPONIBILIDADE: ImportCard[] = [
  {
    key: 'bloqueios',
    label: 'Importar BLOQUEIOS',
    description: 'CSV/XLSX: usuario, inicio, fim, tipo (T/P), motivo',
    importFn: importBloqueios,
  },
  {
    key: 'deslocamentos',
    label: 'Importar DESLOCAMENTOS',
    description: 'CSV/XLSX: usuario, origem, destino, data_inicio, data_fim, observacao',
    importFn: importDeslocamentos,
  },
];

interface ImportSectionProps {
  title: string;
  description: string;
  cards: ImportCard[];
}

function ImportSection({ title, description, cards }: ImportSectionProps): JSX.Element {
  return (
    <section aria-label={title} className="mb-8">
      <header className="mb-3">
        <Title level={3} className="!mb-1">
          {title}
        </Title>
        <Text type="secondary">{description}</Text>
      </header>
      <Row gutter={[16, 16]}>
        {cards.map((card) => (
          <Col key={card.key} xs={24} md={12} lg={8}>
            <Card variant="outlined">
              <ImportUploader
                label={card.label}
                description={card.description}
                onDryRun={async (file: File) => toValidationResult(await card.importFn(file, true))}
                onApply={async (file: File) => toApplyResult(await card.importFn(file, false))}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </section>
  );
}

export default function ImportacoesPage(): JSX.Element {
  return (
    <main className="p-6 bg-gray-50 min-h-screen" aria-labelledby="importacoes-title">
      <header className="mb-6">
        <Title level={2} id="importacoes-title">
          DAT &gt; Importações
        </Title>
        <Text type="secondary">
          Centralize aqui todas as importações em massa da plataforma. Acesso restrito ao DAT
          e superusuários.
        </Text>
      </header>

      <ImportSection
        title="Cadastros base"
        description="Carga inicial e atualização dos cadastros administrados pelo DAT."
        cards={CADASTROS_BASE}
      />

      <ImportSection
        title="Operacional"
        description="Importações operacionais (compras, ações, eventos, produtos)."
        cards={OPERACIONAL}
      />

      <ImportSection
        title="Disponibilidade"
        description="Importação em massa de bloqueios e deslocamentos. Lançamento manual permanece nas páginas específicas."
        cards={DISPONIBILIDADE}
      />
    </main>
  );
}
