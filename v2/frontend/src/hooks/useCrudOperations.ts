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

import { useState, useCallback, type Dispatch, type SetStateAction } from 'react';
import { message, Modal } from 'antd';
import logger from '../utils/logger';
import type { ID, PaginatedResponse } from '../types';

/**
 * Query parameters for list operations
 */
export interface ListParams {
  page?: number;
  pageSize?: number;
  page_size?: number;
  [key: string]: unknown;
}

/**
 * Pagination state
 */
export interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

/**
 * Operation result
 */
export interface OperationResult<T = unknown> {
  success: boolean;
  data?: T;
  total?: number;
  error?: Error;
}

/**
 * Delete confirmation options
 */
export interface DeleteConfirmOptions {
  idField?: string;
  nameField?: string;
  onSuccess?: () => void;
}

/**
 * CRUD config options
 */
export interface CrudConfig<T> {
  listFn: (params: ListParams) => Promise<PaginatedResponse<T> | T[]>;
  createFn?: (data: Partial<T>) => Promise<T>;
  updateFn?: (id: ID, data: Partial<T>) => Promise<T>;
  deleteFn?: (id: ID) => Promise<void>;
  entityName?: string;
  pageSize?: number;
}

/**
 * Return type for useCrudOperations
 */
export interface UseCrudOperationsReturn<T> {
  data: T[];
  loading: boolean;
  pagination: PaginationState;
  fetchData: (params?: ListParams) => Promise<OperationResult<T[]>>;
  handleCreate: (values: Partial<T>) => Promise<OperationResult<T>>;
  handleUpdate: (id: ID, values: Partial<T>) => Promise<OperationResult<T>>;
  handleSave: (values: Partial<T>, id?: ID | null) => Promise<OperationResult<T>>;
  handleDelete: (id: ID) => Promise<OperationResult>;
  confirmDelete: (record: T & { id?: ID; nome?: string }, options?: DeleteConfirmOptions) => void;
  handleTableChange: (page: number, newPageSize?: number, extraParams?: ListParams) => void;
  refresh: (extraParams?: ListParams) => Promise<OperationResult<T[]>>;
  setData: Dispatch<SetStateAction<T[]>>;
  setPagination: Dispatch<SetStateAction<PaginationState>>;
}

/**
 * Hook for standardized CRUD operations
 */
export function useCrudOperations<T extends Record<string, unknown>>({
  listFn,
  createFn,
  updateFn,
  deleteFn,
  entityName = 'registro',
  pageSize = 15,
}: CrudConfig<T>): UseCrudOperationsReturn<T> {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize,
    total: 0,
  });

  /**
   * Fetch data with optional params
   */
  const fetchData = useCallback(async (params: ListParams = {}): Promise<OperationResult<T[]>> => {
    setLoading(true);
    try {
      const queryParams: ListParams = {
        page: params.page || pagination.current,
        page_size: params.pageSize || pagination.pageSize,
        ...params,
      };

      const response = await listFn(queryParams);

      // Handle both paginated and non-paginated responses
      const results = (response as PaginatedResponse<T>).results || (response as T[]) || [];
      const total = (response as PaginatedResponse<T>).count ?? results.length;

      setData(results);
      setPagination(prev => ({
        ...prev,
        current: queryParams.page as number,
        total,
      }));

      return { success: true, data: results, total };
    } catch (error) {
      const err = error as Error;
      message.error(`Erro ao carregar ${entityName}s: ${err.message}`);
      return { success: false, error: err };
    } finally {
      setLoading(false);
    }
  }, [listFn, entityName, pagination.current, pagination.pageSize]);

  /**
   * Create a new record
   */
  const handleCreate = useCallback(async (values: Partial<T>): Promise<OperationResult<T>> => {
    if (!createFn) {
      logger.warn('createFn not provided to useCrudOperations');
      return { success: false };
    }

    try {
      const result = await createFn(values);
      message.success(`${entityName} criado com sucesso`);
      return { success: true, data: result };
    } catch (error) {
      const err = error as Error;
      message.error(`Erro ao criar ${entityName}: ${err.message}`);
      return { success: false, error: err };
    }
  }, [createFn, entityName]);

  /**
   * Update an existing record
   */
  const handleUpdate = useCallback(async (id: ID, values: Partial<T>): Promise<OperationResult<T>> => {
    if (!updateFn) {
      logger.warn('updateFn not provided to useCrudOperations');
      return { success: false };
    }

    try {
      const result = await updateFn(id, values);
      message.success(`${entityName} atualizado com sucesso`);
      return { success: true, data: result };
    } catch (error) {
      const err = error as Error;
      message.error(`Erro ao atualizar ${entityName}: ${err.message}`);
      return { success: false, error: err };
    }
  }, [updateFn, entityName]);

  /**
   * Create or update based on whether id exists
   */
  const handleSave = useCallback(async (values: Partial<T>, id: ID | null = null): Promise<OperationResult<T>> => {
    if (id) {
      return handleUpdate(id, values);
    }
    return handleCreate(values);
  }, [handleCreate, handleUpdate]);

  /**
   * Delete a record (direct, no confirmation)
   */
  const handleDelete = useCallback(async (id: ID): Promise<OperationResult> => {
    if (!deleteFn) {
      logger.warn('deleteFn not provided to useCrudOperations');
      return { success: false };
    }

    try {
      await deleteFn(id);
      message.success(`${entityName} excluído com sucesso`);
      return { success: true };
    } catch (error) {
      const err = error as Error;
      message.error(`Erro ao excluir ${entityName}: ${err.message}`);
      return { success: false, error: err };
    }
  }, [deleteFn, entityName]);

  /**
   * Delete with confirmation modal
   */
  const confirmDelete = useCallback((record: T & { id?: ID; nome?: string }, options: DeleteConfirmOptions = {}): void => {
    const {
      idField = 'id',
      nameField = 'nome',
      onSuccess,
    } = options;

    const recordId = record[idField] as ID;
    const recordName = (record[nameField] as string) || `#${recordId}`;

    Modal.confirm({
      title: `Excluir ${entityName}?`,
      content: `Deseja excluir "${recordName}"? Esta ação não pode ser desfeita.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        const result = await handleDelete(recordId);
        if (result.success && onSuccess) {
          onSuccess();
        }
        return result;
      },
    });
  }, [entityName, handleDelete]);

  /**
   * Handle table pagination change
   */
  const handleTableChange = useCallback((page: number, newPageSize?: number, extraParams: ListParams = {}): void => {
    setPagination(prev => ({
      ...prev,
      current: page,
      pageSize: newPageSize || prev.pageSize,
    }));
    fetchData({ page, pageSize: newPageSize, ...extraParams });
  }, [fetchData]);

  /**
   * Refresh current page
   */
  const refresh = useCallback((extraParams: ListParams = {}): Promise<OperationResult<T[]>> => {
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
