/**
 * useCrudOperations Hook — Standardized CRUD Operations
 *
 * Issue #302: Reduce code duplication in DATModule pages
 *
 * Features:
 * - Loading state management
 * - Pagination support
 * - CRUD operations with error handling
 * - Delete confirmation modal
 * - Ant Design message feedback
 *
 * Usage:
 *   const crud = useCrudOperations({
 *     listFn: listCompras,
 *     createFn: createCompra,
 *     updateFn: updateCompra,
 *     deleteFn: deleteCompra,
 *     entityName: 'Compra',
 *   });
 *
 *   // Use in component
 *   useEffect(() => { crud.fetchData(); }, []);
 *
 *   <Table dataSource={crud.data} loading={crud.loading} />
 *   <Button onClick={() => crud.confirmDelete(record)}>Excluir</Button>
 */

import { useState, useCallback } from 'react';
import { message, Modal } from 'antd';
import logger from '../utils/logger';

/**
 * Hook for standardized CRUD operations
 *
 * @param {Object} config - Configuration object
 * @param {Function} config.listFn - API function to list records
 * @param {Function} [config.createFn] - API function to create record
 * @param {Function} [config.updateFn] - API function to update record
 * @param {Function} [config.deleteFn] - API function to delete record
 * @param {string} [config.entityName='registro'] - Entity name for messages
 * @param {number} [config.pageSize=15] - Default page size
 * @returns {Object} CRUD state and handlers
 */
export function useCrudOperations({
  listFn,
  createFn,
  updateFn,
  deleteFn,
  entityName = 'registro',
  pageSize = 15,
}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize,
    total: 0,
  });

  /**
   * Fetch data with optional params
   * @param {Object} params - Query params (filters, page, etc)
   */
  const fetchData = useCallback(async (params = {}) => {
    setLoading(true);
    try {
      const queryParams = {
        page: params.page || pagination.current,
        page_size: params.pageSize || pagination.pageSize,
        ...params,
      };

      const response = await listFn(queryParams);

      // Handle both paginated and non-paginated responses
      const results = response.results || response || [];
      const total = response.count ?? results.length;

      setData(results);
      setPagination(prev => ({
        ...prev,
        current: queryParams.page,
        total,
      }));

      return { success: true, data: results, total };
    } catch (error) {
      message.error(`Erro ao carregar ${entityName}s: ${error.message}`);
      return { success: false, error };
    } finally {
      setLoading(false);
    }
  }, [listFn, entityName, pagination.current, pagination.pageSize]);

  /**
   * Create a new record
   * @param {Object} values - Record data
   * @returns {Promise<{success: boolean, data?: Object, error?: Error}>}
   */
  const handleCreate = useCallback(async (values) => {
    if (!createFn) {
      logger.warn('createFn not provided to useCrudOperations');
      return { success: false };
    }

    try {
      const result = await createFn(values);
      message.success(`${entityName} criado com sucesso`);
      return { success: true, data: result };
    } catch (error) {
      message.error(`Erro ao criar ${entityName}: ${error.message}`);
      return { success: false, error };
    }
  }, [createFn, entityName]);

  /**
   * Update an existing record
   * @param {number|string} id - Record ID
   * @param {Object} values - Updated data
   * @returns {Promise<{success: boolean, data?: Object, error?: Error}>}
   */
  const handleUpdate = useCallback(async (id, values) => {
    if (!updateFn) {
      logger.warn('updateFn not provided to useCrudOperations');
      return { success: false };
    }

    try {
      const result = await updateFn(id, values);
      message.success(`${entityName} atualizado com sucesso`);
      return { success: true, data: result };
    } catch (error) {
      message.error(`Erro ao atualizar ${entityName}: ${error.message}`);
      return { success: false, error };
    }
  }, [updateFn, entityName]);

  /**
   * Create or update based on whether id exists
   * @param {Object} values - Record data
   * @param {number|string|null} id - Record ID (null for create)
   * @returns {Promise<{success: boolean, data?: Object, error?: Error}>}
   */
  const handleSave = useCallback(async (values, id = null) => {
    if (id) {
      return handleUpdate(id, values);
    }
    return handleCreate(values);
  }, [handleCreate, handleUpdate]);

  /**
   * Delete a record (direct, no confirmation)
   * @param {number|string} id - Record ID
   * @returns {Promise<{success: boolean, error?: Error}>}
   */
  const handleDelete = useCallback(async (id) => {
    if (!deleteFn) {
      logger.warn('deleteFn not provided to useCrudOperations');
      return { success: false };
    }

    try {
      await deleteFn(id);
      message.success(`${entityName} excluído com sucesso`);
      return { success: true };
    } catch (error) {
      message.error(`Erro ao excluir ${entityName}: ${error.message}`);
      return { success: false, error };
    }
  }, [deleteFn, entityName]);

  /**
   * Delete with confirmation modal
   * @param {Object} record - Record to delete
   * @param {Object} [options] - Options
   * @param {string} [options.idField='id'] - Field name for ID
   * @param {string} [options.nameField='nome'] - Field name for display name
   * @param {Function} [options.onSuccess] - Callback after successful delete
   */
  const confirmDelete = useCallback((record, options = {}) => {
    const {
      idField = 'id',
      nameField = 'nome',
      onSuccess,
    } = options;

    const recordName = record[nameField] || `#${record[idField]}`;

    Modal.confirm({
      title: `Excluir ${entityName}?`,
      content: `Deseja excluir "${recordName}"? Esta ação não pode ser desfeita.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        const result = await handleDelete(record[idField]);
        if (result.success && onSuccess) {
          onSuccess();
        }
        return result;
      },
    });
  }, [entityName, handleDelete]);

  /**
   * Handle table pagination change
   * @param {number} page - New page number
   * @param {number} newPageSize - New page size
   * @param {Object} [extraParams] - Additional params to include
   */
  const handleTableChange = useCallback((page, newPageSize, extraParams = {}) => {
    setPagination(prev => ({
      ...prev,
      current: page,
      pageSize: newPageSize || prev.pageSize,
    }));
    fetchData({ page, pageSize: newPageSize, ...extraParams });
  }, [fetchData]);

  /**
   * Refresh current page
   * @param {Object} [extraParams] - Additional params to include
   */
  const refresh = useCallback((extraParams = {}) => {
    return fetchData({ page: pagination.current, ...extraParams });
  }, [fetchData, pagination.current]);

  return {
    // State
    data,
    loading,
    pagination,

    // Core operations
    fetchData,
    handleCreate,
    handleUpdate,
    handleSave,
    handleDelete,
    confirmDelete,

    // Helpers
    handleTableChange,
    refresh,

    // Direct setters (for edge cases)
    setData,
    setPagination,
  };
}

export default useCrudOperations;
