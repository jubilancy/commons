#!/usr/bin/env python3
"""
NGA Open Data prototype pipeline.

What it does:
1. Loads objects.csv, published_images.csv, constituents.csv, objects_constituents.csv
2. Filters published_images to openaccess == 1 (only freely reusable images)
3. Joins images -> objects (via depictstmsobjectid / objectid)
4. Joins objects -> primary artist (via objects_constituents, roletype == 'artist',
   picking the lowest displayorder as the primary/first-listed artist)
5. Samples down to a prototype-sized set (default 1500 records), trying to keep
   variety across classification (style facet) and century bucket
6. Emits a single artworks.json with the fields the Astro site needs to build
   its artist / century / style / tag facet pages, plus a facets.json summary

Run again later with --limit 0 (no sampling) to scale to the full open-access set.
"""
import pandas as pd
import json
import argparse
import re
from collections import defaultdict

def slugify(s):
    if not s or pd.isna(s):
        return "unknown"
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-") or "unknown"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1500,
                         help="Max number of artworks in the prototype set (0 = no limit)")
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--out", default="artworks.json")
    args = parser.parse_args()

    print("Loading CSVs...")
    objects = pd.read_csv(f"{args.data_dir}/objects.csv", low_memory=False)
    images = pd.read_csv(f"{args.data_dir}/published_images.csv", low_memory=False)
    constituents = pd.read_csv(f"{args.data_dir}/constituents.csv", low_memory=False)
    obj_const = pd.read_csv(f"{args.data_dir}/objects_constituents.csv", low_memory=False)

    print(f"  objects: {len(objects):,}")
    print(f"  published_images: {len(images):,}")
    print(f"  constituents: {len(constituents):,}")
    print(f"  objects_constituents: {len(obj_const):,}")

    # 1. Filter to open access, primary view images only
    images = images[(images["openaccess"] == 1) & (images["viewtype"] == "primary")].copy()
    print(f"  open-access primary images: {len(images):,}")

    # 2. Join images -> objects
    merged = images.merge(
        objects,
        left_on="depictstmsobjectid",
        right_on="objectid",
        how="inner",
        suffixes=("_img", "_obj"),
    )
    print(f"  images joined to objects: {len(merged):,}")

    # 3. Primary artist per object (roletype == artist, lowest displayorder)
    artists_only = obj_const[obj_const["roletype"] == "artist"].copy()
    artists_only = artists_only.sort_values(["objectid", "displayorder"])
    primary_artist = artists_only.drop_duplicates(subset="objectid", keep="first")
    primary_artist = primary_artist.merge(
        constituents,
        on="constituentid",
        how="left",
        suffixes=("", "_const"),
    )
    artist_lookup = primary_artist.set_index("objectid")[
        ["preferreddisplayname", "visualbrowsernationality", "constituentid"]
    ].to_dict("index")

    # 4. Build clean records
    records = []
    for _, row in merged.iterrows():
        objectid = row["objectid"]
        artist_info = artist_lookup.get(objectid, {})
        artist_name = artist_info.get("preferreddisplayname") or "Unknown"
        nationality = artist_info.get("visualbrowsernationality") or "Unknown"

        century_bucket = row.get("visualbrowsertimespan")
        if pd.isna(century_bucket):
            century_bucket = "Unknown"

        classification = row.get("classification")
        if pd.isna(classification):
            classification = "Unknown"

        title = row.get("title")
        if pd.isna(title) or not str(title).strip():
            title = "Untitled"

        assistivetext = row.get("assistivetext")
        assistivetext = "" if pd.isna(assistivetext) else str(assistivetext)

        record = {
            "id": row["uuid_img"],
            "objectid": int(objectid),
            "title": str(title).strip(),
            "artist": artist_name,
            "artist_slug": slugify(artist_name),
            "nationality": nationality,
            "date": "" if pd.isna(row.get("displaydate")) else str(row.get("displaydate")),
            "century": century_bucket,
            "century_slug": slugify(century_bucket),
            "classification": classification,
            "classification_slug": slugify(classification),
            "medium": "" if pd.isna(row.get("medium")) else str(row.get("medium")),
            "iiif_url": row["iiifurl"],
            "thumb_url": row["iiifthumburl"],
            "width": int(row["width"]) if not pd.isna(row["width"]) else None,
            "height": int(row["height"]) if not pd.isna(row["height"]) else None,
            "alt_text": assistivetext,
            "wikidata": "" if pd.isna(row.get("wikidataid")) else str(row.get("wikidataid")),
            "source_url": f"https://www.nga.gov/collection/art-object-page.{int(objectid)}.html",
        }
        records.append(record)

    print(f"Built {len(records):,} clean records")

    # 5. Sample for prototype, stratified a bit by classification so the
    #    facet pages have some variety instead of all being one medium
    if args.limit and len(records) > args.limit:
        by_class = defaultdict(list)
        for r in records:
            by_class[r["classification"]].append(r)

        # round-robin across classifications until we hit the limit
        sampled = []
        buckets = list(by_class.values())
        i = 0
        while len(sampled) < args.limit and any(buckets):
            bucket = buckets[i % len(buckets)]
            if bucket:
                sampled.append(bucket.pop(0))
            i += 1
            if i > args.limit * 10:  # safety valve
                break
        records = sampled
        print(f"Sampled down to {len(records):,} for prototype")

    # 6. Write artworks.json
    with open(args.out, "w") as f:
        json.dump(records, f, indent=None, separators=(",", ":"))
    print(f"Wrote {args.out}")

    # 7. Facet summary (counts per artist/century/classification) for build-time page generation
    facets = {"artists": defaultdict(int), "centuries": defaultdict(int), "classifications": defaultdict(int)}
    for r in records:
        facets["artists"][r["artist_slug"]] += 1
        facets["centuries"][r["century_slug"]] += 1
        facets["classifications"][r["classification_slug"]] += 1

    facets_out = {k: dict(sorted(v.items(), key=lambda x: -x[1])) for k, v in facets.items()}
    with open("facets.json", "w") as f:
        json.dump(facets_out, f, indent=2)
    print("Wrote facets.json")
    print(f"\nUnique artists: {len(facets_out['artists'])}")
    print(f"Unique centuries: {len(facets_out['centuries'])}")
    print(f"Unique classifications: {len(facets_out['classifications'])}")

if __name__ == "__main__":
    main()
