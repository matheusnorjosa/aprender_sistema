/**
 * Helper functions for CoordenadoresPage
 * Issue #303: Split large DATModule pages
 */

import { AREA_COLORS } from './constants';

/**
 * Coordenador interface for grouping
 */
export interface CoordenadorForGroup {
  area?: string;
  [key: string]: unknown;
}

/**
 * Grouped coordenadores type
 */
export type GroupedCoordenadores = Record<string, CoordenadorForGroup[]>;

/**
 * Get Ant Design color for an area
 * @param area - Area name
 * @returns Ant Design color name
 */
export function getAreaColor(area: string | null | undefined): string {
  if (!area) return 'default';
  return AREA_COLORS[area] || 'default';
}

/**
 * Get initials from a name for avatar display
 * @param nome - Full name
 * @returns Initials (1-2 characters)
 */
export function getInitials(nome: string | null | undefined): string {
  if (!nome) return '?';
  const parts = nome.split(' ');
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Group coordenadores by area
 * @param coordenadores - List of coordenadores
 * @returns Grouped by area name
 */
export function groupByArea(coordenadores: CoordenadorForGroup[]): GroupedCoordenadores {
  return coordenadores.reduce<GroupedCoordenadores>((acc, coord) => {
    const area = coord.area || 'Sem área';
    if (!acc[area]) acc[area] = [];
    acc[area].push(coord);
    return acc;
  }, {});
}
