#!/usr/bin/env python3
"""Small dependency-free audit for the generated static site."""
from __future__ import annotations

import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
BASE = (os.environ.get("SITE_BASE") or "/DishGal.com").rstrip("/")
if BASE == "/":
    BASE = ""


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.title = []
        self.description = None
        self.canonical = None
        self.json_ld = []
        self._in_title = False
        self._in_json_ld = False
        self._json_buffer = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])
        if tag == "img":
            self.images.append(data)
        if tag == "title":
            self._in_title = True
        if tag == "meta" and data.get("name") == "description":
            self.description = data.get("content")
        if tag == "link" and data.get("rel") == "canonical":
            self.canonical = data.get("href")
        if tag == "script" and data.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld.append("".join(self._json_buffer).strip())
            self._json_buffer = []

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        if self._in_json_ld:
            self._json_buffer.append(data)


def target_for(href: str) -> Path | None:
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
        return None
    path = parsed.path
    if not path.startswith("/"):
        return None
    if BASE and (path == BASE or path.startswith(BASE + "/")):
        path = path[len(BASE):] or "/"
    if path == "/":
        return PUBLIC / "index.html"
    candidate = PUBLIC / path.lstrip("/")
    if path.endswith("/"):
        return candidate / "index.html"
    if candidate.suffix:
        return candidate
    return candidate / "index.html"


def main() -> int:
    errors = []
    titles = {}
    canonicals = {}
    html_files = sorted(PUBLIC.rglob("*.html"))
    if len(html_files) < 50:
        errors.append(f"Expected at least 50 HTML pages, found {len(html_files)}")

    recipe_schema_pages = 0
    for file in html_files:
        parser = Parser()
        text = file.read_text(encoding="utf-8")
        parser.feed(text)
        rel = file.relative_to(PUBLIC)
        title = "".join(parser.title).strip()
        if not title:
            errors.append(f"{rel}: missing title")
        elif title in titles:
            errors.append(f"{rel}: duplicate title also used by {titles[title]}")
        else:
            titles[title] = rel
        if not parser.description or len(parser.description) < 45:
            errors.append(f"{rel}: missing or thin meta description")
        if not parser.canonical:
            errors.append(f"{rel}: missing canonical")
        elif parser.canonical in canonicals and rel.name != "404.html":
            errors.append(f"{rel}: duplicate canonical also used by {canonicals[parser.canonical]}")
        else:
            canonicals[parser.canonical] = rel
        for image in parser.images:
            if not image.get("src"):
                errors.append(f"{rel}: image missing src")
            if image.get("alt") is None:
                errors.append(f"{rel}: image missing alt")
        for link in parser.links:
            target = target_for(link)
            if target is not None and not target.exists():
                errors.append(f"{rel}: broken internal link {link} -> {target.relative_to(PUBLIC)}")
        found_recipe = False
        for raw in parser.json_ld:
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON-LD: {exc}")
                continue
            objects = data if isinstance(data, list) else [data]
            if any(isinstance(obj, dict) and obj.get("@type") == "Recipe" for obj in objects):
                found_recipe = True
        if str(rel).startswith("recipes/") and rel.name == "index.html" and rel.parts[-2] != "recipes":
            if not found_recipe:
                errors.append(f"{rel}: recipe page missing Recipe structured data")
            else:
                recipe_schema_pages += 1
        for placeholder in ["lorem ipsum", "your_email", "example.com/your", "TODO"]:
            if placeholder.lower() in text.lower():
                errors.append(f"{rel}: placeholder text found: {placeholder}")

    if recipe_schema_pages < 25:
        errors.append(f"Expected at least 25 recipe schema pages, found {recipe_schema_pages}")
    for required in ["sitemap.xml", "robots.txt", "feed.xml", "ads.txt", "CNAME", ".nojekyll", "site.webmanifest"]:
        if not (PUBLIC / required).exists():
            errors.append(f"Missing generated {required}")

    sitemap = (PUBLIC / "sitemap.xml").read_text(encoding="utf-8")
    if sitemap.count("<url>") < 50:
        errors.append("Sitemap has fewer than 50 URLs")

    if errors:
        print("DishGal audit FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"DishGal audit passed: {len(html_files)} HTML pages, {recipe_schema_pages} recipe schema pages, {len(titles)} unique titles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
