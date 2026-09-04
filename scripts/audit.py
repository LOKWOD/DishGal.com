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
        self.robots = None
        self.og_image = None
        self.scripts = []
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
        if tag == "meta" and data.get("name") == "robots":
            self.robots = data.get("content")
        if tag == "meta" and data.get("property") == "og:image":
            self.og_image = data.get("content")
        if tag == "link" and data.get("rel") == "canonical":
            self.canonical = data.get("href")
        if tag == "script" and data.get("src"):
            self.scripts.append(data["src"])
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
    noindex_canonicals = []
    html_files = sorted(PUBLIC.rglob("*.html"))
    if len(html_files) < 50:
        errors.append(f"Expected at least 50 HTML pages, found {len(html_files)}")

    recipe_schema_pages = 0
    for file in html_files:
        parser = Parser()
        text = file.read_text(encoding="utf-8")
        parser.feed(text)
        rel = file.relative_to(PUBLIC)
        rel_posix = rel.as_posix()
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
        if parser.robots and "noindex" in parser.robots and parser.canonical:
            noindex_canonicals.append((rel, parser.canonical))
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
        found_breadcrumbs = False
        found_item_list = False
        for raw in parser.json_ld:
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON-LD: {exc}")
                continue
            objects = data if isinstance(data, list) else [data]
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                if obj.get("@type") == "Recipe":
                    found_recipe = True
                    for field in ["recipeCategory", "keywords", "mainEntityOfPage", "recipeIngredient", "recipeInstructions"]:
                        if not obj.get(field):
                            errors.append(f"{rel}: Recipe structured data missing {field}")
                if obj.get("@type") == "BreadcrumbList":
                    found_breadcrumbs = True
                if obj.get("@type") == "CollectionPage" and isinstance(obj.get("mainEntity"), dict) and obj["mainEntity"].get("@type") == "ItemList":
                    found_item_list = True
        if rel_posix.startswith("recipes/") and rel.name == "index.html" and rel.parts[-2] != "recipes":
            if not found_recipe:
                errors.append(f"{rel}: recipe page missing Recipe structured data")
            else:
                recipe_schema_pages += 1
            if not found_breadcrumbs:
                errors.append(f"{rel}: recipe page missing breadcrumb structured data")
            if not parser.og_image or parser.og_image.endswith("/assets/social-card.png"):
                errors.append(f"{rel}: recipe page does not use its recipe image for social sharing")
        if (rel_posix.startswith("collections/") or rel_posix.startswith("ingredients/")) and rel.name == "index.html":
            if not found_item_list:
                errors.append(f"{rel}: collection page missing ItemList structured data")
            if not found_breadcrumbs:
                errors.append(f"{rel}: collection page missing breadcrumb structured data")
        recipe_data_loaded = any(src.endswith("/assets/js/recipes.js") for src in parser.scripts)
        tool_pages = {"saved/index.html", "dinner-decider/index.html", "pantry-rescue/index.html", "meal-planner/index.html"}
        if recipe_data_loaded and rel_posix not in tool_pages:
            errors.append(f"{rel}: unnecessarily loads the full recipe data bundle")
        if rel_posix in tool_pages and not recipe_data_loaded:
            errors.append(f"{rel}: interactive recipe tool is missing its data bundle")
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
    if sitemap.count("<lastmod>") != sitemap.count("<url>"):
        errors.append("Sitemap does not provide one legitimate lastmod value per URL")
    for rel, canonical_url in noindex_canonicals:
        if f"<loc>{canonical_url}</loc>" in sitemap:
            errors.append(f"{rel}: noindex URL is present in the sitemap")

    if errors:
        print("DishGal audit FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"DishGal audit passed: {len(html_files)} HTML pages, {recipe_schema_pages} recipe schema pages, {len(titles)} unique titles")
    return 0


if __name__ == "__main__":
    sys.exit(main())

