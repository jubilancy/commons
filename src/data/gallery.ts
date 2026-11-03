import artworksRaw from "./artworks.json";
import commonsRaw from "./commons.json";

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
  // Wikimedia Commons records only
  source?: "commons";
  full_url?: string;
  license?: string;
}

export const artworks: Artwork[] = [...(artworksRaw as Artwork[]), ...(commonsRaw as Artwork[])];

function groupBy(field: "artist_slug" | "century_slug" | "classification_slug"): Map<string, Artwork[]> {
  const map = new Map<string, Artwork[]>();
  for (const a of artworks) {
    const list = map.get(a[field]);
    if (list) list.push(a);
    else map.set(a[field], [a]);
  }
  return map;
}

// Built once per build, so each page does O(1) lookups instead of scanning every record.
const byId = new Map(artworks.map((a) => [a.id, a]));
const byArtist = groupBy("artist_slug");
const byCentury = groupBy("century_slug");
const byClassification = groupBy("classification_slug");

export function getArtworkById(id: string): Artwork | undefined {
  return byId.get(id);
}

export function getByArtistSlug(slug: string): Artwork[] {
  return byArtist.get(slug) ?? [];
}

export function getByCenturySlug(slug: string): Artwork[] {
  return byCentury.get(slug) ?? [];
}

export function getByClassificationSlug(slug: string): Artwork[] {
  return byClassification.get(slug) ?? [];
}

interface FacetEntry {
  slug: string;
  count: number;
  label: string;
}

function buildFacet(groups: Map<string, Artwork[]>, field: "artist" | "century" | "classification"): FacetEntry[] {
  return Array.from(groups, ([slug, works]) => ({ slug, count: works.length, label: works[0][field] })).sort(
    (a, b) => b.count - a.count
  );
}

const artistFacets = buildFacet(byArtist, "artist");
const centuryFacets = buildFacet(byCentury, "century");
const classificationFacets = buildFacet(byClassification, "classification");

export function getArtistFacets(): FacetEntry[] {
  return artistFacets;
}

export function getCenturyFacets(): FacetEntry[] {
  return centuryFacets;
}

export function getClassificationFacets(): FacetEntry[] {
  return classificationFacets;
}

// --- Client payload shards -------------------------------------------------
// The infinite/shuffle views fetch small JSON shards on demand instead of embedding
// every record in the page HTML. A "scope" is "all", "artists/<slug>", "centuries/<slug>"
// or "styles/<slug>".
export const SHARD_SIZE = 60;

export interface CardPayload {
  id: string;
  title: string;
  artist: string;
  thumb: string;
  alt: string;
}

export function toCard(a: Artwork): CardPayload {
  return { id: a.id, title: a.title, artist: a.artist, thumb: thumbUrl(a), alt: a.alt_text || a.title };
}

export function getScopes(): Map<string, Artwork[]> {
  const scopes = new Map<string, Artwork[]>([["all", artworks]]);
  for (const [slug, works] of byArtist) scopes.set(`artists/${slug}`, works);
  for (const [slug, works] of byCentury) scopes.set(`centuries/${slug}`, works);
  for (const [slug, works] of byClassification) scopes.set(`styles/${slug}`, works);
  return scopes;
}

export function shardCount(total: number): number {
  return Math.max(1, Math.ceil(total / SHARD_SIZE));
}

// IIIF helper: request a specific square/box size instead of the baked-in 200x200 thumb
export function iiifSized(iiifUrl: string, size: number = 400): string {
  return `${iiifUrl}/full/!${size},${size}/0/default.jpg`;
}

// Image URL helpers that work for both NGA (IIIF) and Commons records
export function thumbUrl(a: Artwork): string {
  return a.source === "commons" ? a.thumb_url : iiifSized(a.iiif_url, 400);
}

export function fullUrl(a: Artwork): string {
  return a.source === "commons" ? (a.full_url ?? a.thumb_url) : iiifSized(a.iiif_url, 1200);
}
