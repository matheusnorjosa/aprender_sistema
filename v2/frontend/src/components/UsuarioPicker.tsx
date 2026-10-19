/**
 * UsuarioPicker - Seleção múltipla de usuários por papel (autocomplete).
 *
 * Implementação compartilhada dos pickers de usuário (hoje o FormadoresPicker).
 * Parametrizado por papel do lookup, cor da Tag e aria-label; cada picker de
 * domínio vira um wrapper fino sobre este.
 */

import { useRef, useState, type JSX } from 'react';
import { Tag, AutoComplete, Button, Spin } from 'antd';
import type { RefSelectProps } from 'antd/es/select';
import CloseOutlined from '@ant-design/icons/CloseOutlined';
import { lookupUsuarios } from '../api/lookup';
import { FalhaAoCarregar } from './FalhaAoCarregar';
import logger from '../utils/logger';
import type { ID } from '../types';

/** Item de usuário selecionado. */
export interface UsuarioItem {
  id: ID;
  label: string;
  name?: string;
  /** Do lookup: função Formador sem a função Coordenador (pode ser avaliado; 05/10/2026). */
  avaliavel?: boolean;
}

/** Opção do AutoComplete. */
interface UserOption {
  value: string;
  label: string;
  data: {
    id: ID;
    label: string;
    avaliavel: boolean;
  };
}

export interface UsuarioPickerProps {
  value?: UsuarioItem[];
  onChange?: (value: UsuarioItem[]) => void;
  /** Papel para filtrar o lookup (ex.: 'Formador'; vários separados por vírgula = OU). */
  role: string;
  /** Projeto do evento: o lookup oferece só pessoas da gerência dele (PR 9, P9-5). */
  projetoId?: ID | undefined;
  /** Cor da Tag dos selecionados. */
  tagColor?: string;
  /** aria-label da lista de selecionados. */
  ariaLabel?: string;
  /** O que o lookup carrega, com artigo ("os formadores"): vai na mensagem de falha ao carregar. */
  oQueCarrega?: string;
  /** Do Form.Item: liga o rótulo ao campo de busca e o erro ao leitor de tela. */
  id?: string;
  'aria-describedby'?: string;
  'aria-invalid'?: boolean | 'true' | 'false';
}

export default function UsuarioPicker({
  value = [],
  onChange,
  role,
  projetoId,
  tagColor = 'blue',
  ariaLabel,
  oQueCarrega = 'as pessoas',
  ...doFormItem
}: UsuarioPickerProps): JSX.Element {
  const [options, setOptions] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  // Falha ao carregar: o motivo fica na tela (com "Tentar de novo") em vez de uma lista vazia.
  const [erro, setErro] = useState<string | null>(null);
  const campoRef = useRef<RefSelectProps>(null);

  /** Busca e troca as opções; devolve se carregou. */
  const handleSearch = async (query: string): Promise<boolean> => {
    setSearch(query);

    // Permitir busca vazia (mostra lista inicial) ou com 2+ caracteres
    if (query && query.length > 0 && query.length < 2) {
      setOptions([]);
      return true;
    }

    try {
      setLoading(true);
      const results = await lookupUsuarios(query || '', role, projetoId);
      setOptions(
        results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: { id: item.id, label: item.label, avaliavel: item['avaliavel'] === true },
        }))
      );
      setErro(null);
      return true;
    } catch (error) {
      logger.error(`Erro ao buscar ${role}:`, error);
      setErro((error as Error)?.message || 'Tente de novo em instantes.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = (_selectedValue: string, option: UserOption): void => {
    const novo: UsuarioItem = {
      id: option.data.id,
      label: option.data.label,
      name: option.data.label, // Alias para compatibilidade
      avaliavel: option.data.avaliavel,
    };

    // Verificar se já existe (by ID only — SEC-ENUM-01)
    const exists = value.some(u => u.id === novo.id);
    if (exists) {
      return;
    }

    if (onChange) {
      onChange([...value, novo]);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setSearch('');
  };

  const handleRemove = (idRemovido: ID): void => {
    if (onChange) {
      onChange(value.filter((u) => u.id !== idRemovido));
    }
    // O botão some com a pessoa: o foco vai para a busca, e não para o body.
    campoRef.current?.focus();
  };

  return (
    <div>
      {/* Tags dos usuários selecionados */}
      {value.length > 0 && (
        <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: '0 0 8px 0' }} aria-label={ariaLabel}>
          {value.map((usuario) => (
            <li key={usuario.id}>
              {/* O "x" do Tag do antd não recebe foco: o botão próprio é alcançável pelo teclado. */}
              <Tag color={tagColor} className="inline-flex items-center gap-1">
                {usuario.label || usuario.name}
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  aria-label={`Remover ${usuario.label || usuario.name}`}
                  onClick={() => handleRemove(usuario.id)}
                  style={{ width: 20, height: 20, minWidth: 20 }}
                />
              </Tag>
            </li>
          ))}
        </ul>
      )}

      {/* Autocomplete para adicionar */}
      <AutoComplete
        ref={campoRef}
        {...doFormItem}
        value={search}
        options={options}
        onSearch={handleSearch}
        onFocus={() => {
          // Carregar lista inicial ao focar no campo (se ainda não carregou)
          if (options.length === 0 && !loading) {
            void handleSearch('');
          }
        }}
        onSelect={handleAdd}
        onChange={setSearch}
        placeholder="Clique para ver lista ou digite para buscar..."
        style={{ width: '100%' }}
        notFoundContent={loading ? <Spin size="small" /> : null}
      />
      {erro && (
        <FalhaAoCarregar oque={oQueCarrega} erro={erro} onTentarDeNovo={() => handleSearch(search)} campo={campoRef} />
      )}
    </div>
  );
}
