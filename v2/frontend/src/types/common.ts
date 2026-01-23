/**
 * Common TypeScript types for AS v2 Frontend
 *
 * Generic types used across the application.
 */

/**
 * Paginated API response wrapper
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Generic API error response
 */
export interface ApiError {
  detail?: string;
  message?: string;
  non_field_errors?: string[];
  [key: string]: unknown;
}

/**
 * Standard status for forms and async operations
 */
export type LoadingStatus = 'idle' | 'loading' | 'success' | 'error';

/**
 * Generic ID type (backend uses integers)
 */
export type ID = number;

/**
 * ISO datetime string (from Django DateTimeField)
 */
export type ISODateTime = string;

/**
 * ISO date string (from Django DateField)
 */
export type ISODate = string;

/**
 * Decimal string (from Django DecimalField)
 */
export type DecimalString = string;
