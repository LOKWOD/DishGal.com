#!/usr/bin/env python3
"""Merge DishGal recipe expansion files into the generated build input and reject duplicates."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE_PATH = Path("content/recipes.json")
EXTRA_DIR = Path("content/recipes-extra")


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def main() -> None:
    recipes = json.loads(BASE_PATH.read_text(encoding="utf-8"))
    extras = []
    for path in sorted(EXTRA_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise SystemExit(f"{path}: expected a JSON list")
        extras.extend(payload)

    slugs = set()
    titles = set()
    images = set()

    for recipe in recipes + extras:
        slug = recipe.get("slug", "").strip()
        title = recipe.get("title", "").strip()
        image = recipe.get("image", "").strip()
        if not slug or not title or not image:
            raise SystemExit(f"recipe missing slug/title/image: {title or slug or '<unknown>'}")
        ntitle = norm(title)
        if slug in slugs:
            raise SystemExit(f"duplicate recipe slug: {slug}")
        if ntitle in titles:
            raise SystemExit(f"duplicate recipe title: {title}")
        if image in images:
            raise SystemExit(f"duplicate recipe image: {title} -> {image}")
        slugs.add(slug)
        titles.add(ntitle)
        images.add(image)

    recipes.extend(extras)
    BASE_PATH.write_text(json.dumps(recipes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DishGal recipe merge passed: {len(extras)} expansion recipes, {len(recipes)} total; all slugs, titles, and images unique.")


if __name__ == "__main__":
    main()
