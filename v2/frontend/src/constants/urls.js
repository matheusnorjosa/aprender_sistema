/**
 * External URLs configuration
 *
 * Issue #446: Move external URLs to config
 * URLs can be overridden via environment variables.
 */

export const EXTERNAL_URLS = {
  // Formar Platform (Moodle LMS)
  FORMAR_PLATFORM: import.meta.env.VITE_FORMAR_URL || 'https://www.aprenderformar.com.br/plataforma/',

  // Avaliar Platform (Assessment)
  AVALIAR_PLATFORM: import.meta.env.VITE_AVALIAR_URL || 'https://avaliar.aprenderformar.com.br/',
};
