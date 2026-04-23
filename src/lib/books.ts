// Slugs that are shown in their own dedicated feature sections
// (homepage FeatureCard blocks) and should NOT appear in the
// general book listings or search results.
export const FEATURED_EXCLUDE_SLUGS = new Set<string>([
  'amrta-vani-audio-box-en',
  'srila-gour-govinda-swami-calendar-en',
]);

// Helper — filters a list of collection entries down to regular books
// (excluding the feature-card titles above).
export function excludeFeatured<T extends { slug: string }>(books: T[]): T[] {
  return books.filter((b) => !FEATURED_EXCLUDE_SLUGS.has(b.slug));
}
