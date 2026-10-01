/**
 * Opções que não carregaram (Programa C, C2): o motivo e "Tentar de novo" num Alert (role=alert)
 * FORA do Select, logo abaixo do campo (`extra` do Form.Item) ou do filtro. Dentro do dropdown
 * (`notFoundContent`) o botão ficava num portal fora da ordem do Tab, o alerta ia para dentro do
 * listbox (axe: aria-required-children) e o erro só aparecia com o Select aberto. Quem usa deixa
 * o Select desabilitado enquanto ele estiver sem opções por erro.
 *
 * Foco: quem usa mantém o erro até a resposta, então o botão não some com o foco nele (sumia, e o
 * foco caía no body, fora do modal). Se falhar de novo, o foco fica no botão. Se carregar, o aviso
 * sai e o foco vai para o `campo` que carregou, mas só se ainda estava no botão: quem já foi
 * digitar em outro campo durante a espera fica onde está.
 * O nome do botão diz o que recarrega ("Tentar de novo: carregar os projetos"): há modal com dois.
 * Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */
import { useState, type JSX, type RefObject } from 'react';
import { Alert, Button } from 'antd';

interface FalhaAoCarregarProps {
  /** O que não carregou, com artigo: "os setores", "os projetos". */
  oque: string;
  /** O motivo (mensagem do backend). */
  erro: string;
  /** Recarrega e devolve se carregou; o erro fica na tela até a resposta. */
  onTentarDeNovo: () => Promise<boolean>;
  /** O campo que recarregou: recebe o foco quando carrega. */
  campo: RefObject<{ focus: () => void } | null>;
  className?: string;
}

export function FalhaAoCarregar({ oque, erro, onTentarDeNovo, campo, className = 'mt-1' }: FalhaAoCarregarProps): JSX.Element {
  // Loading enquanto recarrega: se falhar com o mesmo motivo, a tela não mudaria e o clique pareceria morto.
  const [tentando, setTentando] = useState(false);

  const tentar = async (): Promise<void> => {
    setTentando(true);
    const carregou = await onTentarDeNovo();
    setTentando(false);
    // Carregou: o aviso já saiu e levou o botão. Se o foco estava nele, caiu no body; se a pessoa
    // já tinha ido para outro campo, está lá e não é tirado dela.
    if (carregou && document.activeElement === document.body) campo.current?.focus();
  };

  return (
    <Alert
      type="error"
      showIcon
      className={`text-left ${className}`}
      message={`Não foi possível carregar ${oque}.`}
      description={erro}
      action={
        <Button
          size="small"
          loading={tentando}
          aria-label={`Tentar de novo: carregar ${oque}`}
          onClick={() => void tentar()}
        >
          Tentar de novo
        </Button>
      }
    />
  );
}
