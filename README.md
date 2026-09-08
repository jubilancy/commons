# Open Collection Archive (NGA prototype)

A [Public Domain Image Archive](https://pdimagearchive.org/)–style browsing site built on top
of the [National Gallery of Art Open Data Program](https://github.com/NationalGalleryOfArt/opendata).

Static Astro site. Browse by artist / century / style, each with Catalog, Infinite-scroll,
and Shuffle view modes, plus a detail page per artwork with full-size IIIF image and rights info.

**This is a prototype**: it ships with a sample of **1,500** open-access works (out of ~63,700
currently available in the full dataset) so the site structure and UX can be reviewed before
scaling up. See "Scaling up" below.

## Stack

- [Astro](https://astro.build) (static output, no server)
- Data: NGA's `objects.csv` + `published_images.csv` + `constituents.csv` +
  `objects_constituents.csv`, joined and filtered by `scripts/build_dataset.py`
- Images served directly from NGA's IIIF endpoint (`api.nga.gov/iiif/...`) — not rehosted,
  so there's no image storage/bandwidth cost on our side
- Deploy: GitHub Actions → GitHub Pages (see `.github/workflows/deploy.yml`)

## Local development

```bash
npm install
npm run dev
```

Site runs at `http://localhost:4321`.

```bash
npm run build    # outputs to dist/
npm run preview  # serve the built site locally
```

## Regenerating the dataset

The site reads from `src/data/artworks.json` and `src/data/facets.json`, which are generated
by `scripts/build_dataset.py`. That script is **not run automatically** — it downloads large
CSVs from GitHub and does the join/filter/sample step, so it's meant to be re-run manually
whenever you want to refresh or resize the dataset.

```bash
cd scripts
pip install -r requirements.txt

# Download the four source CSVs (large — objects.csv and published_images.csv
# are 70-90MB each). Re-run this whenever you want fresh data from NGA.
curl -sLO https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects.csv
curl -sLO https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/published_images.csv
curl -sLO https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/constituents.csv
curl -sLO https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects_constituents.csv

# Build the prototype-sized dataset (1,500 records, round-robin sampled across
# classification so facet pages have variety)
python3 build_dataset.py --limit 1500 --out ../src/data/artworks.json
mv facets.json ../src/data/facets.json
```

### Scaling up

To use the **full** ~63,700 open-access image set instead of the prototype sample:

```bash
python3 build_dataset.py --limit 0 --out ../src/data/artworks.json
mv facets.json ../src/data/facets.json
```

Before doing this, be aware:

- `artworks.json` will grow from ~1.8MB to roughly **75MB+**, since it's bundled at build time.
  At that size you'll likely want to switch from a single JSON import to per-page JSON files
  or an Astro content collection, so every page doesn't pull in the whole dataset.
- Astro will generate a static page per artist/century/style value **and** per artwork. With
  the full dataset that's tens of thousands of artist pages and ~63,700 detail pages — build
  time and repo size will grow accordingly. Consider paginating facet listings and/or
  generating detail pages on-demand rather than statically once you scale past a few thousand
  records.
- Double-check what NGA's `openaccess` flag actually guarantees (full reuse rights vs. just
  "viewable") before treating the full set as freely reusable in a public archive — see
  their [Open Access Policy](https://www.nga.gov/notices/open-access-policy.html).

## Data model

Each artwork record (`src/data/artworks.json`) has:

| Field | Source | Notes |
|---|---|---|
| `id` | `published_images.csv: uuid` | Used in the IIIF URL and as the detail-page slug |
| `title`, `medium`, `date` | `objects.csv` | |
| `classification` | `objects.csv: classification` | Powers the "Style" facet |
| `century` | `objects.csv: visualbrowsertimespan` | Pre-bucketed by NGA, powers "Century" facet |
| `artist`, `nationality` | `constituents.csv`, joined via `objects_constituents.csv` (`roletype == 'artist'`, first by `displayorder`) | |
| `iiif_url`, `thumb_url` | `published_images.csv` | `iiif_url` + `/full/!W,H/0/default.jpg` gets any size |
| `alt_text` | `published_images.csv: assistivetext` | NGA-provided AI image description; used as `<img alt>` and on detail pages |
| `wikidata` | `objects.csv: wikidataid` | Optional cross-link |
| `source_url` | derived | Links back to the object's nga.gov page |

## Attribution

Metadata and image links come from the National Gallery of Art Open Data Program (CC0).
Every page footer and artwork detail page links back to NGA and the dataset repo. This project
is not affiliated with or endorsed by the National Gallery of Art.
