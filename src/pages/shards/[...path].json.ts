import type { APIRoute, GetStaticPaths } from "astro";
import { SHARD_SIZE, getScopes, shardCount, toCard } from "../../data/gallery";

// One small JSON file per (scope, page): /shards/all/0.json, /shards/artists/<slug>/0.json, ...
export const getStaticPaths: GetStaticPaths = () => {
  const paths = [];
  for (const [scope, works] of getScopes()) {
    for (let n = 0; n < shardCount(works.length); n++) {
      paths.push({ params: { path: `${scope}/${n}` }, props: { works: works.slice(n * SHARD_SIZE, (n + 1) * SHARD_SIZE) } });
    }
  }
  return paths;
};

export const GET: APIRoute = ({ props }) =>
  new Response(JSON.stringify((props.works as Parameters<typeof toCard>[0][]).map(toCard)), {
    headers: { "Content-Type": "application/json" },
  });
