/**
 * Helper functions for CoordenadoresPage
 * Issue #303: Split large DATModule pages
 */

import { AREA_COLORS } from './constants';

/**
 * Get Ant Design color for an area
 * @param {string} area - Area name
 * @returns {string} Ant Design color name
 */
export function getAreaColor(area) {
  return AREA_COLORS[area] || 'default';
}

/**
 * Get initials from a name for avatar display
 * @param {string} nome - Full name
 * @returns {string} Initials (1-2 characters)
 */
export function getInitials(nome) {
  if (!nome) return '?';
  const parts = nome.split(' ');
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Group coordenadores by area
 * @param {Array} coordenadores - List of coordenadores
 * @returns {Object} Grouped by area name
 */
export function groupByArea(coordenadores) {
  return coordenadores.reduce((acc, coord) => {
    const area = coord.area || 'Sem área';
    if (!acc[area]) acc[area] = [];
    acc[area].push(coord);
    return acc;
  }, {});
}
