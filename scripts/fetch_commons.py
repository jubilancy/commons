#!/usr/bin/env python3
"""
Fetch files from the Wikimedia Commons categories listed in sources.txt and write
src/data/commons.json in the same shape as artworks.json (plus thumb_url/full_url/source).

Stdlib only:  uv run scripts/fetch_commons.py [--limit 500]
"""
import argparse, html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "commons-archive-prototype/0.1 (https://github.com/jubilancy/commons)"
ROOT = Path(__file__).resolve().parent.parent


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", (s or "").lower().strip())
    return re.sub(r"[\s_]+", "-", s).strip("-") or "unknown"


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def api_get(params):
    url = f"{API}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # 429 etc: back off and retry
            wait = 2 ** attempt * 2
            print(f"  request failed ({e}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit("Wikimedia API kept failing")


def read_sources(path):
    cats = []
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            cats.append(line if line.lower().startswith("category:") else f"Category:{line}")
    return cats


def century_bucket(date):
    m = re.search(r"\b(1\d{3}|20\d{2})\b", date or "")
    if not m:
        return "Unknown"
    y = int(m.group(1))
    start = (y - 1) // 50 * 50 + 1
    return f"{start} to {start + 49}"


def fetch_category(cat, limit):
    label = cat.split(":", 1)[1].replace("_", " ")
    params = {
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "categorymembers", "gcmtitle": cat, "gcmtype": "file", "gcmlimit": 50,
        "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 400,
        "maxlag": 5,
    }
    out, cont = [], {}
    while True:
        data = api_get({**params, **cont})
        for p in data.get("query", {}).get("pages", []):
            info = (p.get("imageinfo") or [None])[0]
            if not info or not info.get("thumburl"):
                continue
            md = {k: v.get("value", "") for k, v in info.get("extmetadata", {}).items()}
            if md.get("Copyrighted") == "True":  # keep only public-domain / freely licensed
                if not md.get("License", "").startswith(("pd", "cc0")):
                    continue
            title = strip_html(md.get("ObjectName")) or p["title"].removeprefix("File:")
            artist = strip_html(md.get("Artist")) or "Unknown"
            date = strip_html(md.get("DateTimeOriginal"))
            century = century_bucket(date)
            out.append({
                "id": f"commons-{p['pageid']}", "objectid": p["pageid"],
                "title": title, "artist": artist, "artist_slug": slugify(artist),
                "nationality": "Unknown", "date": date,
                "century": century, "century_slug": slugify(century),
                "classification": label, "classification_slug": slugify(label),
                "medium": "", "iiif_url": "",
                "thumb_url": info["thumburl"], "full_url": info["url"],
                "width": info.get("width"), "height": info.get("height"),
                "alt_text": strip_html(md.get("ImageDescription")),
                "wikidata": "", "source_url": info["descriptionurl"],
                "license": strip_html(md.get("LicenseShortName")),
                "source": "commons",
            })
            if limit and len(out) >= limit:
                return out
        if "continue" not in data:
            return out
        cont = data["continue"]
        print(f"  {cat}: {len(out)} so far", file=sys.stderr)
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=ROOT / "sources.txt")
    ap.add_argument("--out", default=ROOT / "src/data/commons.json")
    ap.add_argument("--limit", type=int, default=500, help="max files per category (0 = all)")
    args = ap.parse_args()

    records, seen = [], set()
    for cat in read_sources(args.sources):
        print(f"Fetching {cat}")
        for r in fetch_category(cat, args.limit):
            if r["id"] not in seen:
                seen.add(r["id"])
                records.append(r)
    Path(args.out).write_text(json.dumps(records, separators=(",", ":"), ensure_ascii=False))
    print(f"Wrote {len(records)} records to {args.out}")


if __name__ == "__main__":
    main()
