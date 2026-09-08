import artworksRaw from "./artworks.json";

export interface Artwork {
  id: string;
  objectid: number;
  title: string;
  artist: string;
  artist_slug: string;
  nationality: string;
  date: string;
  century: string;
  century_slug: string;
  classification: string;
  classification_slug: string;
  medium: string;
  iiif_url: string;
  thumb_url: string;
  width: number | null;
  height: number | null;
  alt_text: string;
  wikidata: string;
  source_url: string;
}

export const artworks: Artwork[] = artworksRaw as Artwork[];

export function getArtworkById(id: string): Artwork | undefined {
  return artworks.find((a) => a.id === id);
}

export function getByArtistSlug(slug: string): Artwork[] {
  return artworks.filter((a) => a.artist_slug === slug);
}

export function getByCenturySlug(slug: string): Artwork[] {
  return artworks.filter((a) => a.century_slug === slug);
}

export function getByClassificationSlug(slug: string): Artwork[] {
  return artworks.filter((a) => a.classification_slug === slug);
}

interface FacetEntry {
  slug: string;
  count: number;
  label: string;
}

function buildFacet(field: "artist" | "century" | "classification", slugField: "artist_slug" | "century_slug" | "classification_slug"): FacetEntry[] {
  const map = new Map<string, FacetEntry>();
  for (const a of artworks) {
    const slug = a[slugField];
    const label = a[field];
    if (!map.has(slug)) {
      map.set(slug, { slug, count: 0, label });
    }
    map.get(slug)!.count++;
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}

export function getArtistFacets(): FacetEntry[] {
  return buildFacet("artist", "artist_slug");
}

export function getCenturyFacets(): FacetEntry[] {
  return buildFacet("century", "century_slug");
}

export function getClassificationFacets(): FacetEntry[] {
  return buildFacet("classification", "classification_slug");
}

// IIIF helper: request a specific square/box size instead of the baked-in 200x200 thumb
export function iiifSized(iiifUrl: string, size: number = 400): string {
  return `${iiifUrl}/full/!${size},${size}/0/default.jpg`;
}
