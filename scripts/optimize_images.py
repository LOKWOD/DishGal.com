#!/usr/bin/env python3
"""Publish verified responsive copies of existing editorial images; preserve originals on failure."""
import concurrent.futures
import hashlib
import html
import io
import json
import os
import re
import time
import urllib.request
import urllib.error
import threading
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DEST = PUBLIC / "assets" / "food"
DEST.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / ".image-cache"
CACHE.mkdir(exist_ok=True)
STATE_FILE = CACHE / "provider-state.json"
OFFLINE = os.environ.get("IMAGE_OPTIMIZER_OFFLINE") == "1"
WIKIMEDIA_PROVIDER = "wikimedia"
WIKIMEDIA_ATTEMPT_LIMIT = 10
WIKIMEDIA_WINDOW = timedelta(hours=24)
WIKIMEDIA_MIN_SPACING_SECONDS = 10
# A Wikimedia 429 was observed on 2026-10-13. Do not send another uncached
# request before the user-directed recovery window opens.
WIKIMEDIA_COOLDOWN_FLOOR = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
records = json.loads((ROOT / "content/recipes.json").read_text()) + json.loads((ROOT / "content/articles.json").read_text())
urls = sorted({r.get("image") for r in records if r.get("image", "").startswith("https://")})

def provider_key(url):
    host = urlparse(url).netloc.lower()
    if host == "wikimedia.org" or host.endswith(".wikimedia.org"):
        return WIKIMEDIA_PROVIDER
    return host

def utc_now():
    return datetime.now(timezone.utc)

def parse_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def load_provider_state():
    try:
        loaded = json.loads(STATE_FILE.read_text())
        if isinstance(loaded, dict) and isinstance(loaded.get("providers", {}), dict):
            return loaded
    except (OSError, ValueError):
        pass
    return {"version": 1, "providers": {}}

provider_state = load_provider_state()
state_lock = threading.Lock()

def save_provider_state():
    temporary = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    temporary.write_text(json.dumps(provider_state, indent=2, sort_keys=True))
    temporary.replace(STATE_FILE)

def provider_record(provider):
    return provider_state["providers"].setdefault(provider, {"attempts": [], "cooldown_until": None})

def set_cooldown(provider, until, reason):
    with state_lock:
        record = provider_record(provider)
        existing = parse_timestamp(record.get("cooldown_until"))
        if existing is None or until > existing:
            record["cooldown_until"] = until.astimezone(timezone.utc).isoformat()
        record["cooldown_reason"] = reason
        save_provider_state()

def retry_after_deadline(value, now):
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return now + timedelta(seconds=int(value))
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None

def begin_uncached_attempt(provider):
    if OFFLINE:
        raise ValueError("Offline validation mode; uncached source retained")
    now = utc_now()
    with state_lock:
        record = provider_record(provider)
        cooldown = parse_timestamp(record.get("cooldown_until"))
        if provider == WIKIMEDIA_PROVIDER and (cooldown is None or cooldown < WIKIMEDIA_COOLDOWN_FLOOR):
            cooldown = WIKIMEDIA_COOLDOWN_FLOOR
            record["cooldown_until"] = cooldown.isoformat()
            record["cooldown_reason"] = "Manual recovery window after Wikimedia HTTP 429"
            save_provider_state()
        if cooldown and now < cooldown:
            blocked_providers.add(provider)
            raise ValueError(f"Provider cooldown active until {cooldown.isoformat()}; original retained")
        if provider != WIKIMEDIA_PROVIDER:
            return
        cutoff = now - WIKIMEDIA_WINDOW
        attempts = [stamp for stamp in (parse_timestamp(value) for value in record.get("attempts", [])) if stamp and stamp > cutoff]
        if len(attempts) >= WIKIMEDIA_ATTEMPT_LIMIT:
            cooldown = min(attempts) + WIKIMEDIA_WINDOW
            record["attempts"] = [stamp.isoformat() for stamp in attempts]
            record["cooldown_until"] = cooldown.isoformat()
            record["cooldown_reason"] = "Ten uncached Wikimedia attempts in a rolling 24-hour window"
            blocked_providers.add(provider)
            save_provider_state()
            raise ValueError(f"Wikimedia 24-hour attempt limit reached; original retained until {cooldown.isoformat()}")
        last_attempt = max(attempts) if attempts else None
    if last_attempt:
        wait_seconds = (last_attempt + timedelta(seconds=WIKIMEDIA_MIN_SPACING_SECONDS) - utc_now()).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
    now = utc_now()
    with state_lock:
        record = provider_record(provider)
        cutoff = now - WIKIMEDIA_WINDOW
        attempts = [stamp for stamp in (parse_timestamp(value) for value in record.get("attempts", [])) if stamp and stamp > cutoff]
        if len(attempts) >= WIKIMEDIA_ATTEMPT_LIMIT:
            cooldown = min(attempts) + WIKIMEDIA_WINDOW
            record["attempts"] = [stamp.isoformat() for stamp in attempts]
            record["cooldown_until"] = cooldown.isoformat()
            record["cooldown_reason"] = "Ten uncached Wikimedia attempts in a rolling 24-hour window"
            blocked_providers.add(provider)
            save_provider_state()
            raise ValueError(f"Wikimedia 24-hour attempt limit reached; original retained until {cooldown.isoformat()}")
        attempts.append(now)
        record["attempts"] = [stamp.isoformat() for stamp in attempts]
        record["last_attempt_at"] = now.isoformat()
        record["cooldown_until"] = None
        record.pop("cooldown_reason", None)
        save_provider_state()

provider_locks = {}
blocked_providers = set()
for url in urls:
    provider_locks.setdefault(provider_key(url), threading.Lock())

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
        provider = provider_key(url)
        with provider_locks[provider]:
            if provider in blocked_providers:
                raise ValueError("Provider cooldown active this run; original retained without another request")
            begin_uncached_attempt(provider)
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    raw = response.read(35 * 1024 * 1024 + 1)
            except urllib.error.HTTPError as exc:
                now = utc_now()
                retry_until = retry_after_deadline(exc.headers.get("Retry-After"), now)
                try:
                    response_text = exc.read(8192).decode("utf-8", "ignore").lower()
                except Exception:
                    response_text = ""
                explicit_block = any(phrase in response_text for phrase in (
                    "verify you are human", "unusual traffic", "automated traffic",
                    "bot traffic", "captcha", "too many requests", "rate limit",
                ))
                if exc.code == 429 or explicit_block:
                    minimum = now + timedelta(hours=24)
                    set_cooldown(provider, max(minimum, retry_until or minimum), f"HTTP {exc.code} provider block")
                    blocked_providers.add(provider)
                elif retry_until:
                    set_cooldown(provider, retry_until, f"HTTP {exc.code} Retry-After")
                    blocked_providers.add(provider)
                raise
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

with state_lock:
    now = utc_now()
    provider_summary = {}
    for provider, record in provider_state["providers"].items():
        recent_attempts = [stamp for stamp in (parse_timestamp(value) for value in record.get("attempts", [])) if stamp and stamp > now - timedelta(hours=24)]
        provider_summary[provider] = {
            "uncached_attempts_last_24h": len(recent_attempts),
            "last_attempt_at": record.get("last_attempt_at"),
            "cooldown_until": record.get("cooldown_until"),
            "cooldown_reason": record.get("cooldown_reason"),
        }

report = {"sources": len(urls), "optimized_sources": len(images), "remaining_sources": len(urls) - len(images),
          "responsive_image_instances": image_count, "offline_validation": OFFLINE,
          "original_bytes": sum(v["original_bytes"] for v in images.values()),
          "all_variant_bytes": sum(v["total_variant_bytes"] for v in images.values()),
          "provider_policy": {"wikimedia_uncached_limit_per_24h": WIKIMEDIA_ATTEMPT_LIMIT,
                              "wikimedia_min_seconds_between_attempts": WIKIMEDIA_MIN_SPACING_SECONDS,
                              "providers": provider_summary},
          "failures": failures}
(PUBLIC / "image-optimization.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
