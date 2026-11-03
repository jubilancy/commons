export interface CardPayload {
  id: string;
  title: string;
  artist: string;
  thumb: string;
  alt: string;
}

const shardCache = new Map<string, Promise<CardPayload[]>>();

export function fetchShard(scope: string, n: number): Promise<CardPayload[]> {
  const url = `/shards/${scope}/${n}.json`;
  let p = shardCache.get(url);
  if (!p) {
    p = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${url}: ${r.status}`);
      return r.json();
    });
    p.catch(() => shardCache.delete(url));
    shardCache.set(url, p);
  }
  return p;
}

// Built with DOM APIs (not innerHTML) because titles/artists come from third-party metadata.
export function renderCard(a: CardPayload): HTMLAnchorElement {
  const card = document.createElement("a");
  card.className = "card";
  card.href = `/artwork/${a.id}/`;

  const wrap = document.createElement("div");
  wrap.className = "thumb-wrap";
  const img = document.createElement("img");
  img.src = a.thumb;
  img.alt = a.alt;
  img.loading = "lazy";
  wrap.appendChild(img);

  const meta = document.createElement("div");
  meta.className = "meta";
  const title = document.createElement("p");
  title.className = "title";
  title.textContent = a.title;
  const artist = document.createElement("p");
  artist.className = "artist";
  artist.textContent = a.artist;
  meta.append(title, artist);

  card.append(wrap, meta);
  return card;
}
