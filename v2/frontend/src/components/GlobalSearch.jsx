/**
 * AS v2 - GlobalSearch Component (Issue #418)
 *
 * Global search component with instant results across multiple data types.
 * Uses Fuse.js client-side index for fast, fuzzy search.
 *
 * Usage:
 * ```jsx
 * <GlobalSearch
 *   onSelect={(item, type) => console.log('Selected:', item, type)}
 *   placeholder="Buscar..."
 * />
 * ```
 */

import { useState, useMemo, useCallback } from 'react';
import { Input, List, Typography, Tag, Empty, Spin, Popover } from 'antd';
import { SearchOutlined, UserOutlined, EnvironmentOutlined, ProjectOutlined, CalendarOutlined } from '@ant-design/icons';
import PropTypes from 'prop-types';
import { useGlobalSearch } from '../hooks/useInstantSearch';

const { Text } = Typography;

// Index type configuration
const INDEX_CONFIG = {
  municipios: {
    label: 'Municipios',
    icon: <EnvironmentOutlined />,
    color: 'blue',
    displayField: 'nome',
    secondaryField: 'uf',
  },
  projetos: {
    label: 'Projetos',
    icon: <ProjectOutlined />,
    color: 'green',
    displayField: 'nome',
    secondaryField: 'codigo',
  },
  usuarios: {
    label: 'Usuarios',
    icon: <UserOutlined />,
    color: 'purple',
    displayField: 'nome',
    secondaryField: 'email',
  },
  tiposEvento: {
    label: 'Tipos',
    icon: <CalendarOutlined />,
    color: 'orange',
    displayField: 'nome',
    secondaryField: null,
  },
};

/**
 * Search result item component.
 */
function SearchResultItem({ item, config, onClick }) {
  const displayValue = item[config.displayField] || item.nome || item.titulo;
  const secondaryValue = config.secondaryField ? item[config.secondaryField] : null;
  const matchScore = item._score !== undefined ? Math.round((1 - item._score) * 100) : null;

  return (
    <List.Item
      onClick={() => onClick(item)}
      style={{ cursor: 'pointer', padding: '8px 12px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
        <span style={{ color: '#1890ff' }}>{config.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text ellipsis style={{ display: 'block' }}>{displayValue}</Text>
          {secondaryValue && (
            <Text type="secondary" style={{ fontSize: 12 }}>{secondaryValue}</Text>
          )}
        </div>
        {matchScore !== null && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {matchScore}%
          </Text>
        )}
      </div>
    </List.Item>
  );
}

SearchResultItem.propTypes = {
  item: PropTypes.object.isRequired,
  config: PropTypes.object.isRequired,
  onClick: PropTypes.func.isRequired,
};

/**
 * Global search with multi-index results.
 */
export function GlobalSearch({ onSelect, placeholder = 'Buscar municipios, projetos, usuarios...', style }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const { results, isSearching } = useGlobalSearch(query, {
    debounceMs: 150,
    limitPerIndex: 5,
    minLength: 2,
  });

  // Check if there are any results
  const hasResults = useMemo(() => {
    return Object.values(results).some((arr) => arr.length > 0);
  }, [results]);

  // Total results count
  const totalCount = useMemo(() => {
    return Object.values(results).reduce((sum, arr) => sum + arr.length, 0);
  }, [results]);

  // Handle selection
  const handleSelect = useCallback(
    (item, indexKey) => {
      setQuery('');
      setOpen(false);
      onSelect?.(item, indexKey);
    },
    [onSelect]
  );

  // Search results content
  const searchContent = useMemo(() => {
    if (!query || query.length < 2) {
      return (
        <div style={{ padding: 16, textAlign: 'center' }}>
          <Text type="secondary">Digite ao menos 2 caracteres</Text>
        </div>
      );
    }

    if (isSearching) {
      return (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Spin size="small" />
        </div>
      );
    }

    if (!hasResults) {
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhum resultado" />;
    }

    return (
      <div style={{ maxHeight: 400, overflow: 'auto' }}>
        {Object.entries(results).map(([indexKey, items]) => {
          const config = INDEX_CONFIG[indexKey];
          if (!config || items.length === 0) return null;

          return (
            <div key={indexKey} style={{ marginBottom: 8 }}>
              <div style={{ padding: '4px 12px', background: '#fafafa' }}>
                <Tag color={config.color} style={{ margin: 0 }}>
                  {config.icon} {config.label} ({items.length})
                </Tag>
              </div>
              <List
                size="small"
                dataSource={items}
                renderItem={(item) => (
                  <SearchResultItem
                    key={item.id}
                    item={item}
                    config={config}
                    onClick={() => handleSelect(item, indexKey)}
                  />
                )}
              />
            </div>
          );
        })}
      </div>
    );
  }, [query, isSearching, hasResults, results, handleSelect]);

  return (
    <Popover
      content={searchContent}
      title={
        totalCount > 0 ? (
          <Text type="secondary">{totalCount} resultado(s)</Text>
        ) : null
      }
      trigger="click"
      open={open && query.length >= 2}
      onOpenChange={setOpen}
      placement="bottomLeft"
      overlayStyle={{ width: 360 }}
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          if (e.target.value.length >= 2) {
            setOpen(true);
          }
        }}
        onFocus={() => query.length >= 2 && setOpen(true)}
        allowClear
        style={{ width: 280, ...style }}
      />
    </Popover>
  );
}

GlobalSearch.propTypes = {
  onSelect: PropTypes.func,
  placeholder: PropTypes.string,
  style: PropTypes.object,
};

export default GlobalSearch;
