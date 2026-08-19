import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = resolve(process.argv[2] || "public");
const workerBaseUrl = "https://lokwod-visitor-beacon.syracuseappraiser.workers.dev";
const siteId = "dish-gal";
const markerStart = "<!-- LOKWOD Website Visitor Beacon -->";
const markerEnd = "<!-- End LOKWOD Website Visitor Beacon -->";
const block = `${markerStart}<script defer src="${workerBaseUrl}/beacon.js" data-site="${siteId}"></script>${markerEnd}`;
const markedBlockPattern = /<!--\s*LOKWOD Website Visitor Beacon\s*-->[\s\S]*?<!--\s*End LOKWOD Website Visitor Beacon\s*-->/gi;
const standalonePattern = /<script\b(?=[^>]*\bdata-site=["'][^"']+["'])(?=[^>]*\bsrc=["']https:\/\/[^"']+\/beacon\.js["'])[^>]*>\s*<\/script>/gi;

let processed = 0;
let changed = 0;

function inject(path) {
  const original = readFileSync(path, "utf8");
  if (!/<\/body>/i.test(original)) {
    throw new Error(`Cannot install Visitor Light beacon in ${relative(root, path)}: missing </body>.`);
  }

  const cleaned = original
    .replace(markedBlockPattern, "")
    .replace(standalonePattern, "")
    .replace(/\s+<\/body>/i, "</body>");
  const next = cleaned.replace(/<\/body>/i, `\n${block}\n</body>`);
  processed += 1;

  const beaconCount = (next.match(/\/beacon\.js/g) || []).length;
  const siteCount = (next.match(/data-site=["']dish-gal["']/g) || []).length;
  if (beaconCount !== 1 || siteCount !== 1 || !next.includes(workerBaseUrl)) {
    throw new Error(`Visitor Light beacon verification failed for ${relative(root, path)}.`);
  }

  if (next !== original) {
    writeFileSync(path, next);
    changed += 1;
  }
}

function walk(directory) {
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    const stat = statSync(path);
    if (stat.isDirectory()) walk(path);
    else if (name.toLowerCase().endsWith(".html")) inject(path);
  }
}

walk(root);
if (processed === 0) throw new Error(`No generated HTML pages were found under ${root}.`);
console.log(`DishGal Visitor Light beacon: processed ${processed}, updated ${changed}.`);
