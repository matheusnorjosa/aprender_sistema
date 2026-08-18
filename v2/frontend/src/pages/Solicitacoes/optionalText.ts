/**
 * #1739 (field-drift form<->serializer): campos de texto opcionais cujo model e'
 * `TextField(blank=True)` (sem `null=True`) viram `allow_null=False` no serializer DRF.
 * Enviar `null` para um desses campos toma 400 "Este campo nao pode ser nulo".
 *
 * Coage texto opcional vazio/ausente para string vazia (aceita por `allow_blank=True`),
 * nunca `null`. Usar sempre que o payload mandar um campo de texto opcional ao backend.
 */
export const optionalText = (value: string | null | undefined): string => value || '';
