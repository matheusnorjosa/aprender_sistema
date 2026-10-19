/**
 * PR16: ComboBox com Autocomplete
 *
 * Componente reutilizável para autocomplete de municípios, projetos, tipos de evento
 * Trabalha com objetos {id, label} e fornece busca via lookup API
 */

import { ReactNode, useState, useEffect, useRef, useCallback, type JSX } from 'react';
import { AutoComplete, Spin } from 'antd';
import type { RefSelectProps } from 'antd/es/select';
import { FalhaAoCarregar } from './FalhaAoCarregar';
import logger from '../utils/logger';
import type { ID } from '../types';

/**
 * Lookup item interface
 */
export interface LookupItem {
  id: ID;
  label: string;
  [key: string]: unknown;
}

/**
 * AutoComplete option interface
 */
interface AutoCompleteOption {
  value: string;
  label: string;
  data: LookupItem;
}

/**
 * ComboBox props interface
 */
export interface ComboBoxProps {
  value?: LookupItem | null;
  onChange?: (item: LookupItem | null) => void;
  lookupFunction: (query: string) => Promise<LookupItem[]>;
  placeholder?: string;
  disabled?: boolean;
  notFoundContent?: ReactNode;
  /** O que a lista carrega, com artigo ("os municípios"): vai na mensagem de falha ao carregar. */
  oQueCarrega?: string;
  /** Do Form.Item: liga o rótulo ao campo e o erro ao leitor de tela. */
  id?: string;
  'aria-describedby'?: string;
  'aria-invalid'?: boolean | 'true' | 'false';
}

export default function ComboBox({
  value = null,
  onChange,
  lookupFunction,
  placeholder = 'Digite para buscar...',
  disabled = false,
  notFoundContent = 'Nenhum resultado encontrado',
  oQueCarrega = 'as opções',
  ...doFormItem
}: ComboBoxProps): JSX.Element {
  const [options, setOptions] = useState<AutoCompleteOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  // Falha ao carregar: o motivo fica na tela (com "Tentar de novo") em vez de "Nenhum resultado".
  const [erro, setErro] = useState<string | null>(null);
  const campoRef = useRef<RefSelectProps>(null);

  /** Busca e troca as opções; devolve se carregou. */
  const carregar = useCallback(async (query: string): Promise<boolean> => {
    try {
      setLoading(true);
      const results = await lookupFunction(query);
      setOptions(results.map(item => ({
        value: String(item.id),
        label: item.label,
        data: item
      })));
      setErro(null);
      return true;
    } catch (error) {
      logger.error('Erro ao buscar:', error);
      setErro((error as Error)?.message || 'Tente de novo em instantes.');
      return false;
    } finally {
      setLoading(false);
    }
  }, [lookupFunction]);

  // Carregar opções iniciais
  useEffect(() => {
    void carregar('');
  }, [carregar]);

  // Atualizar searchValue quando value muda
  useEffect(() => {
    if (value && value.label) {
      setSearchValue(value.label);
    } else {
      setSearchValue('');
    }
  }, [value]);

  const handleSearch = async (query: string): Promise<void> => {
    setSearchValue(query);
    // Menos de 2 letras: recarrega as opções iniciais.
    await carregar(!query || query.length < 2 ? '' : query);
  };

  const handleSelect = (_value: string, option: AutoCompleteOption): void => {
    if (onChange) {
      onChange(option.data);
    }
  };

  const handleChange = (text: string): void => {
    setSearchValue(text);

    // Se o texto está vazio, limpar seleção
    if (!text && onChange) {
      onChange(null);
    }
  };

  // Texto digitado sem escolher uma opção não vale: ao sair, a caixa volta a mostrar o valor guardado.
  const handleBlur = (): void => {
    setSearchValue(value?.label ?? '');
  };

  return (
    <>
      <AutoComplete
        ref={campoRef}
        {...doFormItem}
        value={searchValue}
        options={options}
        onSearch={handleSearch}
        onSelect={handleSelect}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        disabled={disabled}
        style={{ width: '100%' }}
        notFoundContent={loading ? <Spin size="small" /> : erro ? null : notFoundContent}
        allowClear
      />
      {erro && !disabled && (
        <FalhaAoCarregar
          oque={oQueCarrega}
          erro={erro}
          onTentarDeNovo={() => carregar(searchValue.length < 2 ? '' : searchValue)}
          campo={campoRef}
        />
      )}
    </>
  );
}
