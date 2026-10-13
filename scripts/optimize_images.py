#!/usr/bin/env python3
"""Publish verified responsive copies of existing editorial images; preserve originals on failure."""
import concurrent.futures
import hashlib
import html
import io
import json
import re
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DEST = PUBLIC / "assets" / "food"
DEST.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / ".image-cache"
CACHE.mkdir(exist_ok=True)
records = json.loads((ROOT / "content/recipes.json").read_text()) + json.loads((ROOT / "content/articles.json").read_text())
urls = sorted({r.get("image") for r in records if r.get("image", "").startswith("https://")})

def optimize(url):
    try:
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        cache_record = CACHE / f"{key}.json"
        if cache_record.exists():
            result = json.loads(cache_record.read_text())
            if all((CACHE / Path(v["url"]).name).exists() for v in result["variants"]):
                for variant in result["variants"]:
                    (DEST / Path(variant["url"]).name).write_bytes((CACHE / Path(variant["url"]).name).read_bytes())
                return url, result, None
        request = urllib.request.Request(url, headers={"User-Agent": "DishGalImageOptimizer/1.0 (https://dishgal.com/contact/)", "Accept": "image/*"})
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(35 * 1024 * 1024 + 1)
        if len(raw) > 35 * 1024 * 1024:
            raise ValueError("Source exceeds 35 MB")
        with Image.open(io.BytesIO(raw)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
        if image.width < 200 or image.height < 100:
            raise ValueError("Source resolution too small")
        variants = []
        total_bytes = 0
        widths = sorted({min(width, image.width) for width in (480, 800, 1400)})
        for width in widths:
            height = max(1, round(image.height * width / image.width))
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            target = DEST / f"{key}-{width}.webp"
            resized.save(target, "WEBP", quality=80, method=5)
            with Image.open(target) as check:
                check.verify()
            (CACHE / target.name).write_bytes(target.read_bytes())
            variants.append({"url": "/assets/food/" + target.name, "width": width, "height": height, "bytes": target.stat().st_size})
            total_bytes += target.stat().st_size
        result = {"variants": variants, "original_bytes": len(raw), "total_variant_bytes": total_bytes}
        cache_record.write_text(json.dumps(result))
        return url, result, None
    except Exception as exc:
        return url, None, str(exc)

images = {}
failures = []
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    for url, result, error in executor.map(optimize, urls):
        if result:
            images[url] = result
        else:
            failures.append({"url": url, "reason": error})

def attributes(url, sizes):
    variants = images[url]["variants"]
    chosen = min(variants, key=lambda v: abs(v["width"] - 800))
    srcset = ", ".join(f'{v["url"]} {v["width"]}w' for v in variants)
    return chosen["url"], srcset, chosen["width"], chosen["height"], sizes

image_count = 0
for page in PUBLIC.rglob("*.html"):
    text = page.read_text()
    def rewrite(match):
        global image_count
        tag = match.group(0)
        found = re.search(r'\bsrc="([^"]+)"', tag)
        if not found or html.unescape(found[1]) not in images:
            return tag
        url = html.unescape(found[1])
        hero = "hero-image" in tag
        sizes = "(max-width: 900px) 100vw, 700px" if hero else "(max-width: 560px) 100vw, (max-width: 900px) 50vw, 360px"
        src, srcset, width, height, sizes = attributes(url, sizes)
        tag = re.sub(r'\s(?:src|srcset|sizes|width|height)="[^"]*"', "", tag)
        image_count += 1
        return tag[:-1] + f' src="{src}" srcset="{srcset}" sizes="{sizes}" width="{width}" height="{height}">'
    page.write_text(re.sub(r'<img\b[^>]*>', rewrite, text))

bundle = PUBLIC / "assets/js/recipes.js"
raw = bundle.read_text()
data = json.loads(raw.split("=", 1)[1].rstrip(";"))
for record in data:
    if record.get("image") in images:
        src, srcset, _, _, _ = attributes(record["image"], "")
        record["image"] = src
        record["image_srcset"] = srcset
bundle.write_text("window.DISHGAL_RECIPES=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")

report = {"sources": len(urls), "optimized_sources": len(images), "responsive_image_instances": image_count,
          "original_bytes": sum(v["original_bytes"] for v in images.values()),
          "all_variant_bytes": sum(v["total_variant_bytes"] for v in images.values()), "failures": failures}
(PUBLIC / "image-optimization.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
