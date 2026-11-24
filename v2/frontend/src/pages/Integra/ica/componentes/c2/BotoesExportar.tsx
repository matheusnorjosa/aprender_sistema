/**
 * "Baixar planilha (CSV)" e "Imprimir / salvar PDF" das telas do ICA. Somem na impressão.
 * A tela monta as linhas e chama `baixarCsv` (`ica/exportar.ts`) em `aoBaixarPlanilha`.
 */
import type { JSX } from 'react';
import { Button } from 'antd';
import { DownloadOutlined, PrinterOutlined } from '@ant-design/icons';

import { imprimirPagina } from '../../exportar';

interface BotoesExportarProps {
  aoBaixarPlanilha: () => void;
}

export function BotoesExportar({ aoBaixarPlanilha }: BotoesExportarProps): JSX.Element {
  return (
    <div className="mb-4 flex flex-wrap gap-2 print:hidden">
      <Button icon={<DownloadOutlined aria-hidden="true" />} onClick={aoBaixarPlanilha}>
        Baixar planilha (CSV)
      </Button>
      <Button icon={<PrinterOutlined aria-hidden="true" />} onClick={() => imprimirPagina()}>
        Imprimir / salvar PDF
      </Button>
    </div>
  );
}
