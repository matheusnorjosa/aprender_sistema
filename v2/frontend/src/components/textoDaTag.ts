/**
 * Cor do texto das tags com contraste AA (4,5:1) (Programa C, padrão responsivo). O AntD pinta
 * o preset com a cor 7 sobre a cor 1, e green, gold e orange reprovam (3,37, 2,76 e 3,34:1);
 * red, blue, geekblue e purple passam. Uso: `<Tag color={cor} style={{ color: TEXTO_DA_TAG[cor] }}>`.
 * Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */
export const TEXTO_DA_TAG: Partial<Record<string, string>> = {
  green: '#237804', // green-8: 5,44:1
  orange: '#ad4e00', // orange-8: 5,09:1
  gold: '#874d00', // gold-9: 6,53:1 (o gold-8 dá 4,25:1)
};
