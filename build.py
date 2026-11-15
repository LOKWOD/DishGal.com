Warning: truncated output (original token count: 87097)
Total output lines: 3501

#!/usr/bin/env python3
from __future__ import annotations

import html
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / os.environ.get("PUBLIC_DIR", "public")
RECIPES = json.loads((ROOT / "content" / "recipes.json").read_text(encoding="utf-8"))
ARTICLES = json.loads((ROOT / "content" / "articles.json").read_text(encoding="utf-8"))

SITE_NAME = "DishGal"
SITE_URL = "https://dishgal.com"
BASE = os.environ.get("SITE_BASE", "/DishGal.com").rstrip("/")
if BASE == "/":
    BASE = ""
FORM_EMAIL = os.environ.get("FORM_EMAIL") or "hello@dishgal.com"
AMAZON_TAG = (os.environ.get("AMAZON_TAG") or "dishgal-20").strip()
ADSENSE_CLIENT = (os.environ.get("ADSENSE_CLIENT") or "").strip()
ADSENSE_PUBLISHER_ID = (os.environ.get("ADSENSE_PUBLISHER_ID") or "").strip()
CLOUDFLARE_TOKEN = (os.environ.get("CLOUDFLARE_TOKEN") or "").strip()

COLLECTION_META = {
    "30-minute": ("30-Minute Dinners", "Fast dinners with enough structure to feel like a real meal.", "⏱"),
    "instant-pot": ("Instant Pot Family Dinners", "Pressure-cooker dinners with realistic total times, mild-first seasoning, and fewer dishes for busy family nights.", "⚡"),
    "one-pot": ("One-Pot Dinners", "Less cleanup, full dinner energy, one main pot.", "🍲"),
    "sheet-pan": ("Sheet-Pan Dinners", "Hands-off roasting, browned edges, fewer dishes.", "🥘"),
    "slow-cooker": ("Slow-Cooker Dinners", "Set-it-up meals for days when dinner needs to wait for you.", "♨"),
    "budget": ("Budget Dinners", "Good dinners built around useful, repeatable groceries.", "💸"),
    "breakfast": ("Breakfast Recipes", "Practical breakfasts with clear timing, realistic costs, and options for busy mornings or relaxed brunches.", "☀"),
    "vegetarian": ("Vegetarian Dinners", "Meatless meals that still eat like dinner.", "🥬"),
    "family": ("Family Favorites", "Low-drama dinners designed for the whole table.", "🍽"),
}

INGREDIENT_HUBS = {
    "chicken": {
        "title": "Easy Chicken Recipes",
        "description": "Practical chicken dinners for busy nights, from fast skillets and rice bowls to sheet-pan meals and family casseroles.",
        "terms": {"chicken"},
    },
    "beef": {
        "title": "Easy Beef Recipes",
        "description": "Weeknight beef recipes with clear timing, useful swaps, and options ranging from ground-beef dinners to steak-night favorites.",
        "terms": {"beef", "steak", "ribeye", "brisket", "ground-beef"},
    },
    "ground-beef": {
        "title": "Easy Ground Beef Recipes",
        "description": "Reliable ground beef dinners for tacos, skillets, casseroles, pasta, and other family-friendly meals that earn a repeat.",
        "terms": {"ground-beef", "ground beef", "ground chuck"},
    },
    "ribeye": {
        "title": "Ribeye Steak Recipes",
        "description": "Ribeye recipes for skillets, grills, sandwiches, tacos, and steakhouse-style dinners, with practical doneness and slicing notes.",
        "terms": {"ribeye"},
    },
    "pork": {
        "title": "Easy Pork Recipes",
        "description": "Straightforward pork dinners built around chops, tenderloin, sausage, and other weeknight-friendly cuts and flavors.",
        "terms": {"pork", "bacon", "ham", "prosciutto", "sausage", "kielbasa", "chorizo"},
    },
    "seafood": {
        "title": "Easy Seafood Recipes",
        "description": "Approachable seafood dinners featuring shrimp, salmon, fish, tuna, and more, with realistic cook times and no guesswork.",
        "terms": {"seafood", "fish", "salmon", "shrimp", "tuna", "trout", "cod", "tilapia", "calamari"},
    },
}

PROTEIN_META = {
    "beef": "Beef",
    "chicken": "Chicken",
    "pork": "Pork",
    "turkey": "Turkey",
    "lamb": "Lamb",
    "sausage": "Sausage",
    "seafood": "Seafood",
    "meatless": "Meatless",
}

GUIDE_CATEGORY_META = {
    "meal-planning": ("Meal Planning", "Smarter weekly plans with less waste and fewer one-use groceries.", "🗓"),
    "kitchen-systems": ("Kitchen Systems", "Practical routines that reduce weeknight decision fatigue.", "✓"),
    "kitchen-gear": ("Kitchen Gear", "Honest buying guidance based on function, fit, and tradeoffs.", "🍳"),
}

SHOP_CARD_CSS = """<style>
.shop-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin-top:1.25rem}
.shop-card{display:flex;min-width:0;flex-direction:column;overflow:hidden;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow-sm);text-decoration:none;transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
.shop-card:hover{transform:translateY(-3px);border-color:var(--tomato);box-shadow:0 15px 34px rgba(61,38,26,.14)}
.shop-card:focus-visible{outline:3px solid var(--mustard);outline-offset:3px}
.shop-card-media{display:block;position:relative;overflow:hidden;aspect-ratio:3/2;background-color:#eee7dd;background-position:center;background-repeat:no-repeat;background-size:cover}
.shop-card-media::after{content:"Kitchen pick";position:absolute;right:.7rem;bottom:.7rem;padding:.28rem .55rem;color:#fff;background:rgba(32,28,25,.78);border-radius:999px;font-size:.69rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
.shop-card-media img{width:100%;height:100%;object-fit:cover;transition:transform .3s ease}
.shop-card:hover .shop-card-media img{transform:scale(1.035)}
.shop-card-copy{display:flex;flex:1;min-width:0;flex-direction:column;align-items:flex-start;padding:1rem 1.05rem 1.1rem}\n.shop-card--text-only .shop-card-copy{min-height:190px;justify-content:flex-start}
.shop-card-copy small{margin-bottom:.28rem;color:var(--tomato-dark);font-size:.71rem;font-weight:850;letter-spacing:.065em;text-transform:uppercase}
.shop-card-copy strong{font-family:Georgia,"Times New Roman",serif;font-size:1.18rem;line-height:1.2}
.shop-card-copy span{margin-top:.45rem;color:var(--ink-soft);font-size:.9rem;line-height:1.45}
.shop-card-copy b{margin-top:auto;padding-top:.8rem;color:var(--plum);font-size:.84rem}
@media(max-width:860px){.shop-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.shop-grid{grid-template-columns:1fr}.shop-card{display:grid;grid-template-columns:124px minmax(0,1fr)}.shop-card-media{height:100%;min-height:168px;aspect-ratio:auto}.shop-card-copy{padding:.9rem}.shop-card-media::after{display:none}}
</style>"""

def esc(value) -> str:
    return html.escape(str(value), quote=True)

def clean_text(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()

def pretty_slug(slug: str) -> str:
    return slug.replace("-", " ").title()

def recipe_proteins(recipe) -> list[str]:
    explicit = recipe.get("protein", [])
    if isinstance(explicit, str):
        explicit = [explicit]
    cleaned = [str(value).strip().lower() for value in explicit if str(value).strip()]
    if cleaned:
        return list(dict.fromkeys(cleaned))

    haystack = " ".join([
        recipe.get("title", ""),
        recipe.get("dek", ""),
        " ".join(recipe.get("tags", [])),
        " ".join(recipe.get("ingredients", [])),
        " ".join(recipe.get("pantry", [])),
    ]).lower()
    rules = {
        "beef": ("beef", "steak", "ribeye", "brisket", "chuck roast", "ground chuck"),
        "chicken": ("chicken",),
        "pork": ("pork", "bacon", "ham", "prosciutto"),
        "turkey": ("turkey",),
        "lamb": ("lamb",),
        "sausage": ("sausage", "kielbasa", "chorizo"),
        "seafood": ("seafood", "fish", "salmon", "tuna", "shrimp", "cod", "tilapia"),
    }
    matches = [
        protein
        for protein, terms in rules.items()
        if any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", haystack) for term in terms)
    ]
    tags = {str(tag).lower() for tag in recipe.get("tags", [])}
    if not matches and tags.intersection({"vegetarian", "vegan"}):
        matches.append("meatless")
    return matches

def recipe_search_text(recipe) -> str:
    return " ".join([
        recipe.get("title", ""),
        recipe.get("dek", ""),
        " ".join(recipe.get("tags", [])),
        " ".join(recipe.get("ingredients", [])),
        " ".join(recipe.get("pantry", [])),
        " ".join(recipe_proteins(recipe)),
    ]).lower()

def recipes_for_ingredient(slug: str):
    terms = INGREDIENT_HUBS[slug]["terms"]
    protein_hub_groups = {
        "chicken": {"chicken"},
        "beef": {"beef"},
        "ground-beef": {"beef"},
        "ribeye": {"beef"},
        "pork": {"pork", "sausage"},
        "seafood": {"seafood", "fish", "salmon", "tuna", "shrimp", "cod", "tilapia", "trout", "calamari"},
    }
    matches = []
    for recipe in RECIPES:
        tags = {str(tag).lower() for tag in recipe.get("tags", [])}
        proteins = set(recipe_proteins(recipe))
        if slug in protein_hub_groups and not proteins.intersection(protein_hub_groups[slug]):
            continue
        haystack = " ".join([
            recipe.get("title", ""),
            " ".join(recipe.get("tags", [])),
            " ".join(recipe.get("pantry", [])),
            " ".join(recipe_proteins(recipe)),
        ]).lower()
        if tags.intersection(terms) or proteins.intersection(terms) or any(term in haystack for term in terms):
            matches.append(recipe)
    return stable_recipe_mix(matches)

def ingredient_hubs_for_recipe(recipe):
    active_slugs = {slug for slug, _ in active_ingredient_hubs()}
    return [slug for slug in INGREDIENT_HUBS if slug in active_slugs and recipe in recipes_for_ingredient(slug)]

def active_ingredient_hubs():
    return [(slug, meta) for slug, meta in INGREDIENT_HUBS.items() if len(recipes_for_ingredient(slug)) >= 3]

def recipe_seo_title(recipe) -> str:
    title = clean_text(recipe.get("title", "Recipe"))
    if len(title) > 49 and " with " in title.lower():
        title = re.split(r"\s+with\s+", title, maxsplit=1, flags=re.IGNORECASE)[0]
    if "recipe" not in title.lower():
        title += " Recipe"
    return title

def truncate_description(value: str, limit: int = 158) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    shortened = value[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return shortened + "…"

def rss_date(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return format_datetime(parsed)

def recipe_meta_description(recipe) -> str:
    minutes = int(recipe.get("total_minutes", int(recipe.get("prep_minutes", 0)) + int(recipe.get("cook_minutes", 0))))
    return truncate_description(f"Make {recipe.get('title', 'this recipe')} in {minutes} minutes. {recipe.get('dek', '')}")

def stable_recipe_mix(recipes):
    """Keep browsing varied without changing the order on every page load."""
    return sorted(
        recipes,
        key=lambda recipe: hashlib.sha256(recipe.get("slug", "").encode("utf-8")).hexdigest(),
    )

def href(path: str = "/") -> str:
    if not path.startswith("/"):
        path = "/" + path
    if path == "/":
        return f"{BASE}/" if BASE else "/"
    return f"{BASE}{path}" if BASE else path

def canonical(path: str = "/") -> str:
    if not path.startswith("/"):
        path = "/" + path
    return SITE_URL.rstrip("/") + path

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def write_page(path: str, content: str) -> None:
    if path == "/":
        target = PUBLIC / "index.html"
    elif path == "/404.html":
        target = PUBLIC / "404.html"
    else:
        target = PUBLIC / path.strip("/") / "index.html"
    ensure_dir(target.parent)
    target.write_text(content, encoding="utf-8")

def json_script(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

def brand() -> str:
    return f'''<a class="brand" href="{href('/')}">
      <span class="brand-name">Dish<em>Gal</em></span>
    </a>'''

def header() -> str:
    return f'''<header class="site-header">
      <div class="wrap header-inner">
        {brand()}
        <nav class="main-nav" aria-label="Primary">
          <a href="{href('/recipes/')}">Recipes</a>
          <a href="{href('/collections/instant-pot/')}">Instant Pot</a>
          <a href="{href('/#browse-recipes')}">Collections</a>
          <a href="{href('/meal-planner/')}">Meal Planner</a>
          <a href="{href('/guides/')}">Kitchen Picks</a>
          <a href="{href('/saved/')}">Saved</a>
        </nav>
        <div class="header-actions">
          <a class="btn btn-sm btn-primary" href="{href('/recipes/')}">Find dinner</a>
          <button class="icon-button menu-button" type="button" data-menu-button aria-expanded="false" aria-label="Open menu">☰</button>
        </div>
      </div>
    </header>'''

def footer() -> str:
    return f'''<footer class="site-footer">
      <div class="wrap">
        <div class="footer-grid">
          <div class="footer-brand">
            {brand()}
            <p>Dinner help for real nights: practical recipes, useful planning tools, and kitchen advice without the performance.</p>
          </div>
          <div class="footer-column"><h3>Cook</h3>
            <a href="{href('/recipes/')}">All recipes</a>
            <a href="{href('/collections/instant-pot/')}">Instant Pot dinners</a>
            <a href="{href('/collections/30-minute/')}">30-minute dinners</a>
            {''.join(f'<a href="{href("/ingredients/" + slug + "/")}">{esc(meta["title"])}</a>' for slug, meta in active_ingredient_hubs()[:3])}
            <a href="{href('/dinner-decider/')}">Dinner Decider</a>
            <a href="{href('/pantry-rescue/')}">Pantry Rescue</a>
          </div>
          <div class="footer-column"><h3>Plan</h3>
            <a href="{href('/meal-planner/')}">5-night planner</a>
            <a href="{href('/saved/')}">Saved recipes</a>
            <a href="{href('/guides/')}">Kitchen picks</a>
            <a href="{href('/newsletter/')}">Newsletter</a>
          </div>
          <div class="footer-column"><h3>DishGal</h3>
            <a href="{href('/about/')}">About</a>
            <a href="{href('/editorial-policy/')}">Editorial policy</a>
            <a href="{href('/affiliate-disclosure/')}">Affiliate disclosure</a>
            <a href="{href('/contact/')}">Contact</a>
          </div>
        </div>
        <div class="footer-bottom">
          <span>© <span data-current-year></span> DishGal.com</span>
          <span><a href="{href('/privacy/')}">Privacy</a> · <a href="{href('/terms/')}">Terms</a></span>
        </div>
      </div>
    </footer>'''

def page(title: str, description: str, path: str, body: str, *, schema=None, noindex=False,
         image=None, page_type="website", published=None, modified=None, needs_recipe_data=False) -> str:
    title_full = title if title.endswith("DishGal") else f"{title} | DishGal"
    desc = clean_text(description)
    schema_html = ""
    if schema is not None:
        schema_html = f'<script type="application/ld+json">{json_script(schema)}</script>'
    adsense = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(ADSENSE_CLIENT)}" crossorigin="anonymous"></script>' if ADSENSE_CLIENT else ""
    cloudflare = (
        '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
        f'data-cf-beacon=\'{{"token":"{esc(CLOUDFLARE_TOKEN)}"}}\'></script>'
        if CLOUDFLARE_TOKEN else ""
    )
    robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large">'
    social_image = image or f"{SITE_URL}/assets/social-card.png"
    article_meta = ""
    if page_type == "article":
        if published:
            article_meta += f'\n  <meta property="article:published_time" content="{esc(published)}">'
        if modified:
            article_meta += f'\n  <meta property="article:modified_time" content="{esc(modified)}">'
    recipe_data_script = f'<script defer src="{href("/assets/js/recipes.js?v=20261012compactimages1")}"></script>' if needs_recipe_data else ""
    return f'''<!doctype html>
<html lang="en" data-base="{esc(BASE)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(title_full)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="theme-color" content="#e94f37">
  {robots}
  <link rel="canonical" href="{esc(canonical(path))}">
  <meta property="og:type" content="{esc(page_type)}">
  <meta property="og:site_name" content="DishGal">
  <meta property="og:title" content="{esc(title_full)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{esc(canonical(path))}">
  <meta property="og:image" content="{esc(social_image)}">
  <meta property="og:image:alt" content="{esc(title)}">
  {article_meta}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title_full)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{esc(social_image)}">
  <link rel="alternate" type="application/rss+xml" title="DishGal recipes and guides" href="{href('/feed.xml')}">
  <link rel="preconnect" href="https://images.pexels.com" crossorigin>
  <link rel="preconnect" href="https://images.unsplash.com" crossorigin>
  <link rel="stylesheet" href="{href('/assets/css/styles.css')}?v=20260922b">\n  {SHOP_CARD_CSS}
  <link rel="manifest" href="{href('/site.webmanifest')}">
  {adsense}
  {schema_html}
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  {header()}
  <main id="main">{body}</main>
  {footer()}
  <script>window.DISHGAL_BASE={json.dumps(BASE)};</script>
  {recipe_data_script}
  <script defer src="{href('/assets/js/site.js?v=20261012images1')}"></script>
  {cloudflare}
</body>
</html>'''

def breadcrumbs(items) -> str:
    parts = [f'<a href="{href("/")}">Home</a>']
    for label, path in items:
        if path:
            parts.append(f'<span><a href="{href(path)}">{esc(label)}</a></span>')
        else:
            parts.append(f'<span>{esc(label)}</span>')
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>'

def breadcrumb_schema(items) -> dict:
    entries = [("Home", "/")] + [(label, path) for label, path in items]
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": label,
                **({"item": canonical(path)} if path else {}),
            }
            for position, (label, path) in enumerate(entries, start=1)
        ],
    }

def recipe_card(recipe) -> str:
    minutes = int(recipe.get("total_minutes", int(recipe.get("prep_minutes", 0)) + int(recipe.get("cook_minutes", 0))))
    tags = " ".join(recipe.get("tags", []))
    proteins = " ".join(recipe_proteins(recipe))
    search = recipe_search_text(recipe)
    return f'''<article class="recipe-card" data-recipe-card data-search="{esc(search)}" data-tags="{esc(tags)}" data-proteins="{esc(proteins)}" data-collection="{esc(recipe.get('collection',''))}" data-minutes="{minutes}">
      <button class="icon-button recipe-card-save" data-save-recipe="{esc(recipe['slug'])}" aria-label="Save recipe">♡</button>
      <a class="recipe-card-media" href="{href('/recipes/' + recipe['slug'] + '/')}">
        <img src="{esc(recipe.get('image',''))}" alt="{esc(recipe.get('image_alt', recipe.get('title','Recipe')))}" loading="lazy" decoding="async" width="800" height="600">
        <span class="recipe-card-badge">{minutes} min</span>
      </a>
      <div class="recipe-card-body">
        <h3><a href="{href('/recipes/' + recipe['slug'] + '/')}">{esc(recipe.get('title','Recipe'))}</a></h3>
        <p>{esc(recipe.get('dek',''))}</p>
        <div class="recipe-card-meta"><span>⏱ {minutes} min</span><span>{esc(recipe.get('cost_per_serving',''))}/serving</span></div>
      </div>
    </article>'''

def article_card(article) -> str:
    return f'''<article class="article-card">
      <img src="{esc(article.get('image',''))}" alt="{esc(article.get('image_alt', article.get('title','Guide')))}" loading="lazy" decoding="async" width="800" height="500">
      <div class="article-card-body">
        <small>{esc(article.get('category','Guide'))}</small>
        <h3><a href="{href('/guides/' + article['slug'] + '/')}">{esc(article.get('title','Guide'))}</a></h3>
        <p>{esc(article.get('dek',''))}</p>
        <a class="read-link" href="{href('/guides/' + article['slug'] + '/')}">See the guide →</a>
      </div>
    </article>'''

SHOP_IMAGES = {
    "6 quart electric pressure cooker": ("https://upload.wikimedia.org/wikipedia/commons/3/31/Instant_Pot_DUO60_pressure_cooker.jpg", "Stainless six-quart electric pressure cooker with a locking lid and digital controls"),
    "enameled cooking pot with lid": ("https://images.pexels.com/photos/20430669/pexels-photo-20430669.jpeg?auto=compress&dpr=1&h=750&w=1260", "Red enameled cooking pot with a fitted lid and two side handles"),
    "enameled dutch oven 6 quart": ("https://images.pexels.com/photos/20430669/pexels-photo-20430669.jpeg?auto=compress&dpr=1&h=750&w=1260", "Red enameled Dutch oven on a kitchen work surface"),
    "immersion blender stainless steel": ("https://images.pexels.com/photos/6605163/pexels-photo-6605163.jpeg?auto=compress&dpr=1&h=750&w=1260", "Chef using an immersion blender in a tall mixing cup"),
    "digital probe meat thermometer": ("https://images.unsplash.com/photo-1622001545761-9bd12a4b465b?auto=format&fit=crop&w=900&q=80", "Two digital probe cooking thermometers beside prepared ingredients"),
    "stainless steel pasta pot colander": ("https://images.pexels.com/photos/5907595/pexels-photo-5907595.jpeg?auto=compress&dpr=1&h=750&w=1260", "Pasta draining through a stainless-steel colander"),
    "stainless steel mesh colander strainer": ("https://images.pexels.com/photos/5907595/pexels-photo-5907595.jpeg?auto=compress&dpr=1&h=750&w=1260", "Pasta being lifted from a stainless-steel mesh colander"),
    "microplane zester grater stainless": ("https://images.pexels.com/photos/6287524/pexels-photo-6287524.jpeg?auto=compress&dpr=1&h=750&w=1260", "Cheese being grated on a stainless-steel grater"),
    "stainless steel kitchen tongs silicone tip": ("https://images.pexels.com/photos/11968836/pexels-photo-11968836.jpeg?auto=compress&dpr=1&h=750&w=1260", "Kitchen tongs turning food over a grill"),
    "long stainless steel kitchen tongs": ("https://images.pexels.com/photos/11968836/pexels-photo-11968836.jpeg?auto=compress&dpr=1&h=750&w=1260", "Long stainless-steel kitchen tongs turning food over a grill"),
    "heavy gauge aluminum half sheet pan": ("https://images.pexels.com/photos/13156063/pexels-photo-13156063.jpeg?auto=compress&dpr=1&h=750&w=1260", "Rimmed metal baking sheet lined with parchment"),
    "9 by 13 baking dish casserole": ("https://images.pexels.com/photos/19145679/pexels-photo-19145679/free-photo-of-meal-in-glass-box.jpeg?auto=compress&dpr=1&h=750&w=1260", "Rectangular glass baking dish filled with a browned eggplant casserole"),
    "oven safe baking dish": ("https://images.unsplash.com/photo-1533777324565-a040eb52facd?auto=format&fit=crop&w=900&q=80", "Oven-safe rectangular baking dish holding a finished baked meal"),
    "silicone oven mitts heat resistant": ("https://images.unsplash.com/photo-1743684456567-a3d32dbf702e?auto=format&fit=crop&w=900&q=80", "Two heat-safe oven mitts hanging above kitchen pots and pans"),
    "heat resistant oven mitts": ("https://images.unsplash.com/photo-1743684456567-a3d32dbf702e?auto=format&fit=crop&w=900&q=80", "Two heat-resistant oven mitts hanging above kitchen pots and pans"),
    "rice cooker family stainless inner pot": ("https://images.unsplash.com/photo-1599182345361-9542815e73f6?auto=format&fit=crop&w=900&h=600&q=80", "Round countertop rice cooker with a metal lid and removable inner pot"),
    "glass meal prep containers locking lids": ("https://images.pexels.com/photos/30635719/pexels-photo-30635719.jpeg?auto=compress&dpr=1&h=750&w=1260", "Prepared meals arranged in clear lidded containers"),
    "digital kitchen scale grams ounces": ("https://images.pexels.com/photos/5622193/pexels-photo-5622193.jpeg", "Bowl of vegetables resting on a digital kitchen scale"),
    "12 inch cast iron skillet": ("https://images.unsplash.com/photo-1569810912653-c0e8d1184623?auto=format&fit=crop&w=900&q=80", "Cast-iron skillet with a finished baked pasta"),
    "cast iron skillet": ("https://images.unsplash.com/photo-1569810912653-c0e8d1184623?auto=format&fit=crop&w=900&q=80", "Cast-iron skillet with a finished baked pasta"),
    "silicone fish spatula turner": ("https://images.unsplash.com/photo-1673155225557-bee5d2540158?auto=format&fit=crop&w=900&q=80", "Flexible kitchen spatula being used during cooking"),
    "stainless steel mixing bowls nesting": ("https://images.pexels.com/photos/31109993/pexels-photo-31109993.jpeg?auto=compress&dpr=1&h=750&w=1260", "Stainless-steel mixing bowl and matching strainer bowl"),
    "stainless steel bowl colander set": ("https://images.pexels.com/photos/31109993/pexels-photo-31109993.jpeg?auto=compress&dpr=1&h=750&w=1260", "Stainless-steel bowl and matching colander set"),
    "stainless steel measuring scoops set": ("https://images.unsplash.com/photo-1781082580025-407abed1d50f?auto=format&fit=crop&w=900&h=600&crop=entropy&q=80", "Stainless-steel measuring scoops arranged on a work surface"),
    "8 inch chef knife kitchen": ("https://images.unsplash.com/photo-1711065060638-675df8e8c358?auto=format&fit=crop&w=900&q=80", "Chef's knife resting on a wooden cutting board"),
    "chef knife kitchen": ("https://images.unsplash.com/photo-1711065060638-675df8e8c358?auto=format&fit=crop&w=900&q=80", "Chef's knife resting on a wooden cutting board"),
    "large nonslip cutting board": ("https://images.unsplash.com/photo-1635321593217-40050ad13c74?auto=format&fit=crop&w=900&q=80", "Large cutting board with a chef's knife and vegetables"),
    "family size air fryer wide basket": ("https://images.pexels.com/photos/29461935/pexels-photo-29461935.jpeg?auto=compress&dpr=1&h=750&w=1260", "Countertop air fryer in a home kitchen"),
    "heavy gauge aluminum half sheet pan wire rack": ("https://images.pexels.com/photos/7059458/pexels-photo-7059458.jpeg?auto=compress&dpr=1&h=750&w=1260", "Rimmed sheet pan holding roasted potatoes and asparagus"),
    "glass meal prep containers locking lids stackable": ("https://images.pexels.com/photos/30635719/pexels-photo-30635719.jpeg?auto=compress&dpr=1&h=750&w=1260", "Stackable clear meal-prep containers filled with food"),
}

DEFAULT_SHOP_IMAGE = (
    "https://images.unsplash.com/photo-1635321593217-40050ad13c74?auto=format&fit=crop&w=900&q=80",
    "Useful kitchen tools arranged on a food-prep surface",
)

SHOP_IMAGE_RULES = [
    (("cut-resistant", "cut resistant"), ("https://images.pexels.com/photos/8093920/pexels-photo-8093920.jpeg?auto=compress&dpr=1&h=750&w=1260", "Gloved hands using kitchen knives on a cutting board")),
    (("immersion blender",), ("https://images.pexels.com/photos/6605163/pexels-photo-6605163.jpeg?auto=compress&dpr=1&h=750&w=1260", "Chef using an immersion blender in a tall mixing cup")),
    (("baking dish", "casserole dish", "baking pan"), ("https://images.unsplash.com/photo-1533777324565-a040eb52facd?auto=format&fit=crop&w=900&q=80", "Oven-safe baking dishes holding finished food")),
    (("sheet pan",), ("https://images.pexels.com/photos/7059458/pexels-photo-7059458.jpeg?auto=compress&dpr=1&h=750&w=1260", "Rimmed sheet pan holding roasted vegetables")),
    (("pantry",), ("https://images.pexels.com/photos/8580727/pexels-photo-8580727.jpeg?auto=compress&dpr=1&h=750&w=1260", "Clear pantry jars arranged on shelves")),
    (("handle cover", "scraper"), ("https://images.unsplash.com/photo-1569810912653-c0e8d1184623?auto=format&fit=crop&w=900&q=80", "Cast-iron cookware ready for a family meal")),
    (("lid knob",), ("https://images.pexels.com/photos/20430669/pexels-photo-20430669.jpeg?auto=compress&dpr=1&h=750&w=1260", "Enameled Dutch oven with a fitted lid knob")),
    (("mandoline",), ("https://images.pexels.com/photos/11369848/pexels-photo-11369848.jpeg?auto=compress&dpr=1&h=750&w=1260", "Mandoline slicer beside onions and cabbage")),
    (("tongs",), ("https://images.pexels.com/photos/11968836/pexels-photo-11968836.jpeg?auto=compress&dpr=1&h=750&w=1260", "Kitchen tongs turning food over a grill")),
    (("utensil", "measuring spoon", "measuring cup"), ("https://images.pexels.com/photos/38848778/pexels-photo-38848778.jpeg?auto=compress&dpr=1&h=750&w=1260", "Assorted measuring tools and kitchen utensils")),
    (("knife", "cutting board", "spatula"), ("https://images.unsplash.com/photo-1635321593217-40050ad13c74?auto=format&fit=crop&w=900&q=80", "Kitchen prep tools on a cutting board")),
    (("cookware set", "pot set", "pans set", "saucepan", "saute pan", "sauté pan"), ("https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=900&q=80", "Pots and pans in use in a home kitchen")),
    (("skillet", "dutch oven", "cookware"), ("https://images.unsplash.com/photo-1569810912653-c0e8d1184623?auto=format&fit=crop&w=900&q=80", "Sturdy cookware ready for a family meal")),
    (("food processor",), ("https://images.pexels.com/photos/5847235/pexels-photo-5847235.jpeg?auto=compress&dpr=1&h=750&w=1260", "Food processor bowl with ingredients around the center blade")),
    (("stand mixer",), ("https://images.pexels.com/photos/1450907/pexels-photo-1450907.jpeg?auto=compress&dpr=1&h=750&w=1260", "Stand mixer with a stainless-steel bowl")),
    (("blender",), ("https://images.pexels.com/photos/6802635/pexels-photo-6802635.jpeg?auto=compress&dpr=1&h=750&w=1260", "Countertop blender mixing ingredients")),
    (("mixing bowl",), ("https://images.unsplash.com/photo-1540660290370-8aa90e451e8a?auto=format&fit=crop&w=900&q=80", "Mixing bowl and ingredients on a kitchen counter")),
    (("rice cooker",), ("https://images.pexels.com/photos/11770362/pexels-photo-11770362.jpeg?auto=compress&dpr=1&h=750&w=1260", "Countertop rice cooker in a home kitchen")),
    (("slow cooker",), ("https://upload.wikimedia.org/wikipedia/commons/6/65/6_quart_Crock_Pot_slow_cooker.jpg", "Six-quart oval slow cooker with its glass lid closed")),
    (("air fryer", "toaster oven"), ("https://images.pexels.com/photos/29461935/pexels-photo-29461935.jpeg?auto=compress&dpr=1&h=750&w=1260", "Countertop air fryer and toaster oven")),
    (("thermometer",), ("https://images.unsplash.com/photo-1622001545761-9bd12a4b465b?auto=format&fit=crop&w=900&q=80", "Two digital probe cooking thermometers beside prepared ingredients")),
    (("scale",), ("https://images.pexels.com/photos/5622193/pexels-photo-5622193.jpeg", "Bowl resting on a digital kitchen scale")),
    (("refrigerator",), ("https://images.pexels.com/photos/5418583/pexels-photo-5418583.jpeg?auto=compress&dpr=1&h=750&w=1260", "Food and containers organized on refrigerator shelves")),
    (("container", "storage", "labels"), ("https://images.pexels.com/photos/30635719/pexels-photo-30635719.jpeg?auto=compress&dpr=1&h=750&w=1260", "Organized food in clear storage containers")),
    (("colander", "strainer", "pasta"), ("https://images.pexels.com/photos/5907595/pexels-photo-5907595.jpeg?auto=compress&dpr=1&h=750&w=1260", "Pasta draining through a stainless-steel colander")),
    (("grater", "microplane"), ("https://images.pexels.com/photos/6287524/pexels-photo-6287524.jpeg?auto=compress&dpr=1&h=750&w=1260", "Cheese being grated on a stainless-steel grater")),
]

def shop_image(query: str):
    normalized = clean_text(query).lower()
    if normalized in SHOP_IMAGES:
        return SHOP_IMAGES[normalized]
    for terms, image in SHOP_IMAGE_RULES:
        if any(term in normalized for term in terms):
            return image
    return DEFAULT_SHOP_IMAGE

def amazon_link(query: str, label: str, note: str = "") -> str:
    """Render a compliant text-first Amazon category card.

    DishGal intentionally does not attach editorial/stock photography to an
    Amazon shopping link. A product image belongs on a commercial card only
    when the exact linked product/category image has been independently
    verified through an approved Amazon mechanism. Until that verification is
    available, the text-first card is more accurate than a decorative photo
    that could imply the wrong product.
    """
    url = f"https://www.amazon.com/s?k={quote_plus(query)}&amp;tag={quote_plus(AMAZON_TAG)}"
    return f"""<a class="shop-card shop-card--text-only" href="{url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-commercial-link="true" data-affiliate-active="true" data-affiliate-network="amazon" data-affiliate-tag="{esc(AMAZON_TAG)}">
      <span class="shop-card-copy"><small>Compare on Amazon</small><strong>{esc(label)}</strong>{f'<span>{esc(note)}</span>' if note else ''}<b>See current options →</b></span>
    </a>"""

def recipe_shop(recipe) -> str:
    haystack = " ".join([
        recipe.get("title", ""), recipe.get("dek", ""), recipe.get("collection", ""),
        " ".join(recipe.get("tags", [])), " ".join(recipe.get("ingredients", [])),
    ]).lower()
    if "austrian linzer torte" in haystack:
        products = [
            ("9 inch fluted tart pan removable bottom", "9-inch fluted tart pan", "A removable base releases the low nut-rich torte without disturbing its delicate side crust, while the fluted ring keeps the photographed round outline neat."),
            ("digital kitchen scale grams ounces baking", "Digital kitchen scale", "Weights keep the flour, two ground nuts and soft butter in balance so the lattice holds its shape instead of becoming dry or spreading."),
            ("food processor small bowl pulse nuts", "Food processor", "Short controlled pulses grind toasted hazelnuts and almonds with flour into fine meal without forcing the nut oils into paste."),
        ]
    elif "malaysian hainanese chicken chop" in haystack:
        products = [
            ("12 inch heavy skillet shallow frying", "Wide 12-inch heavy skillet", "A broad heat-steady surface gives two breaded thighs room to fry without crowding and keeps the measured oil temperature steadier between batches."),
            ("half sheet pan wire rack oven safe", "Half-sheet pan with oven-safe rack", "The rack drains fried cutlets without trapping steam, holds them for a safe oven finish if needed and reheats leftovers while restoring the crust."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe verifies each thigh reaches 165°F and refrigerated chicken reheats to the same temperature without treating crust color as a safety cue."),
        ]
    elif "costa rican gallo pinto" in haystack:
        products = [
            ("12 inch heavy cast iron skillet", "Wide 12-inch skillet", "A broad heat-steady surface reduces the seasoned bean liquid, folds in six portions of rice and creates toasted patches without crowding."),
            ("3 quart stainless steel saucepan with lid", "3-quart saucepan with lid", "A close-fitting lid and measured capacity cook the long-grain rice evenly before it cools for the skillet."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe verifies the fried eggs reach the USDA 160°F target and refrigerated leftovers reheat to 165°F."),
        ]
    elif "georgian lobio" in haystack:
        products = [
            ("wide 6 quart enameled dutch oven", "Wide 6-quart Dutch oven", "A roomy heavy pot provides safe headroom for the required vigorous kidney-bean boil, then steady heat for the long tenderizing simmer and final mash."),
            ("12 inch heavy cast iron skillet", "12-inch heavy skillet", "One broad heat-steady surface toasts the walnuts and coriander, then cooks all six compact mchadi corn cakes in an uncrowded layer."),
            ("food processor small bowl", "Food processor", "Short pulses turn toasted walnuts, coriander, fenugreek, chile and garlic into a fine pebbly seasoning without releasing enough oil to make walnut butter."),
        ]
    elif "provençal pissaladière" in haystack or "provencal pissaladiere" in haystack:
        products = [
            ("12 inch heavy stainless steel skillet", "Wide 12-inch heavy skillet", "A broad heavy base gives three pounds of sliced onions room to lose moisture slowly without steaming or scorching at the edges."),
            ("heavy rimmed aluminum half sheet pan", "Heavy rimmed half-sheet pan", "A rigid conductive pan supports the 10-by-14-inch rectangle and crisps its olive-oiled bottom while the substantial onion topping heats through."),
            ("stainless steel pizza wheel cutter", "Sturdy pizza wheel", "A sharp wheel divides the rested rectangular tart into clean appetizer squares without dragging the whole anchovies or olives through the soft onion layer."),
        ]
    elif "königsberger klopse" in haystack or "konigsberger klopse" in haystack:
        products = [
            ("wide 6 quart enameled dutch oven", "Wide 6-quart Dutch oven", "A broad heavy pot keeps twelve large meatballs in a quiet poach, then gives the roux and strained broth room to become a smooth caper cream sauce."),
            ("fine mesh stainless steel strainer large", "Large fine-mesh strainer", "Straining removes the poaching onion, bay and peppercorns before the seasoned broth is measured into the pale sauce."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe checks several meatball centers for the USDA-required 160°F without relying on their deliberately pale poached color."),
        ]
    elif "meat-filled deruny" in haystack or "meat filled potato pancakes" in haystack:
        products = [
            ("stainless steel box grater fine coarse", "Sturdy box grater", "Fine grating releases enough potato starch to bind the crisp shell, while a stable nonslip base keeps the five-potato prep controlled."),
            ("12 inch heavy cast iron skillet", "12-inch heavy skillet", "A broad heavy pan holds a steady 340–350°F oil temperature through four small batches so the filled pancakes brown evenly instead of soaking up cool oil."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe can enter sideways through the potato edge to confirm the enclosed ground-beef center reaches 160°F without mistaking crust color for doneness."),
        ]
    elif "egyptian molokhia" in haystack or "egyptian molokheya" in haystack:
        products = [
            ("heavy bottom stockpot 8 quart stainless steel", "Heavy 8-quart stockpot", "A roomy heavy pot keeps the whole chicken submerged at a quiet simmer while producing enough clear broth for both the molokhia and rice."),
            ("fine mesh stainless steel strainer large", "Large fine-mesh strainer", "Straining the poaching broth removes the onion, cardamom and surface particles before the broth is divided between the green soup and vermicelli rice."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe verifies the deepest breast and innermost thigh both reach 165°F before the chicken is browned and carved."),
        ]
    elif "kuku sabzi" in haystack:
        products = [
            ("10 inch oven safe nonstick skillet", "10-inch oven-safe skillet", "A measured 10-inch surface gives the herb-heavy egg mixture enough depth for clean wedges while moving safely from a browned stovetop base to an evenly set oven finish."),
            ("large salad spinner herb dryer", "Large salad spinner", "Thoroughly dried parsley, cilantro, dill, chives and scallions build a firm green crumb instead of steaming water into the egg cake."),
            ("instant read digital thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe checks the thick center for the FDA's 160°F egg-dish target without relying on the naturally dark-green surface for doneness."),
        ]
    elif "singapore-style kaya toast" in haystack or "singapore style kaya toast" in haystack:
        products = [
            ("heatproof glass mixing bowl double boiler", "Heatproof double-boiler bowl", "A bowl that sits securely above—not in—barely simmering water protects the coconut-egg custard from direct heat while leaving room for continuous stirring."),
            ("fine mesh strainer stainless steel medium", "Medium fine-mesh strainer", "Straining before cooking removes egg strands; a second pass can smooth small curds without thinning the finished kaya."),
            ("instant read digital thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe confirms the kaya has reached 160°F in several spots without relying on pandan-influenced color as a safety cue."),
        ]
    elif "afghan-style aushak" in haystack or "afghan style aushak" in haystack:
        products = [
            ("wide stock pot 8 quart stainless steel", "Wide 8-quart stockpot", "A broad pot gives delicate dumplings room to rise and circulate in three calm batches without crowding or colliding."),
            ("wide stainless steel slotted spoon", "Wide slotted spoon", "A broad shallow bowl supports the cooked wrappers while their water drains, avoiding the tearing and pileup caused by tipping them into a colander."),
            ("large oval serving platter ceramic", "Large oval serving platter", "A broad platter holds the dumplings in one slightly overlapping layer so the tomato sauce, yogurt ribbons and mint stay visible and evenly distributed."),
        ]
    elif "brazilian pão de queijo" in haystack or "brazilian pao de queijo" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Thirty-gram portions bake at the same rate, and weighing tapioca starch avoids the compaction errors that make this dough unexpectedly dry."),
            ("heavy rimmed aluminum half sheet pan", "Heavy rimmed half-sheet pan", "A rigid conductive pan gives all 24 rolls room to puff while browning their bases and scattered cheese patches evenly."),
            ("stand mixer paddle attachment 5 quart", "Stand mixer with paddle", "The paddle works hot liquid into resistant tapioca starch, then emulsifies the eggs without requiring you to wrestle the sticky dough by hand."),
        ]
    elif "dark-roux shrimp" in haystack or "dark roux shrimp" in haystack:
        products = [
            ("heavy bottom 6 quart dutch oven", "Heavy 6-quart Dutch oven", "A broad heavy base spreads the heat under the roux and leaves enough room to whisk in six measured cups of stock without splashing."),
            ("stainless steel flat roux whisk", "Flat roux whisk", "A flat whisk reaches the pot's bottom and corners during the constant 30-minute stir, where flour is most likely to scorch."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe checks the thickest shrimp for 145°F without relying only on shell color or curl."),
        ]
    elif "individual beef cottage pies" in haystack:
        products = [
            ("4 inch mini pie tins set", "4-inch individual pie tins", "Shallow metal tins conduct heat into the pastry bases and give all six pies the crisp freestanding shape shown in the finished dish."),
            ("stainless steel potato ricer", "Stainless-steel potato ricer", "Fine, lump-free potatoes pass cleanly through a large piping tip and hold defined ridges as they brown."),
            ("reusable piping bag large star tip", "Piping bag with large star tip", "A broad star tip builds the overlapping potato swirls that cover the filling and create extra golden edges."),
        ]
    elif "grilled turmeric chicken satay" in haystack:
        products = [
            ("flat bamboo skewers 8 inch grilling", "Flat bamboo grilling skewers", "Flat-sided skewers help the thin chicken strips stay facing the heat instead of spinning when they are turned."),
            ("cast iron grill pan 12 inch", "12-inch cast-iron grill pan", "A broad ridged pan provides a reliable indoor route to charred edges when an outdoor grill is unavailable."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe checks the thickest folded chicken section for 165°F without relying on yellow color or grill marks."),
        ]
    elif "stuffed acorn squash with wheat berries" in haystack:
        products = [
            ("heavy rimmed half sheet pan", "Heavy rimmed half-sheet pan", "A broad sturdy pan fits all four squash halves cut-side down so their maple-brushed edges caramelize without crowding."),
            ("3 quart stainless steel saucepan with lid", "3-quart saucepan with lid", "A medium covered saucepan gives the wheat berries room to simmer until plump while limiting evaporation during their longer cook."),
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "A broad skillet evaporates the mushrooms' moisture, browns the vegetables and holds the grain-lentil filling without steaming."),
        ]
    elif "thai-style red curry fish cakes" in haystack or "thai style red curry fish cakes" in haystack:
        products = [
            ("food processor 8 cup", "8-cup food processor", "A chilled processor bowl and short pulses turn the cold fish into a cohesive paste without warming it into a loose puree."),
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "A broad skillet fits four cakes without crowding, helping the shallow oil stay near the target temperature between batches."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe checks the thickest cake for a 145°F center without relying on exterior color or firmness."),
        ]
    elif "honey-walnut baked pears" in haystack or "honey walnut baked pears" in haystack:
        products = [
            ("2 quart ceramic baking dish", "2-quart baking dish", "A snug oven-safe dish holds eight pear halves in one layer so the measured steam and glaze stay close to the fruit."),
            ("stainless steel melon baller small", "Small melon baller", "A compact round scoop removes the fibrous seed core while leaving a thick fruit wall that will not leak."),
            ("silicone pastry brush small", "Small pastry brush", "A soft brush distributes the cinnamon-honey mixture over the cut fruit and into every hollow without bruising the pears."),
        ]
    elif "miso savory oats" in haystack:
        products = [
            ("2 quart stainless steel saucepan with lid", "2-quart saucepan", "A small heavy saucepan keeps the oats at a controlled simmer and leaves enough room to stir without splashing."),
            ("fine mesh skimmer spoon stainless steel", "Fine-mesh skimmer", "A shallow mesh skimmer lifts poached eggs gently while draining their cooking water."),
            ("small nonstick skillet 8 inch", "Small skillet", "A compact skillet toasts the sesame-panko topping evenly without needing extra oil."),
        ]
    elif "smoky warm lentils" in haystack:
        products = [
            ("3 quart stainless steel saucepan with lid", "3-quart saucepan", "A medium saucepan gives lentils enough water to move freely while keeping the simmer easy to control."),
            ("fine mesh strainer stainless steel large", "Large fine-mesh strainer", "Small lentils drain cleanly without escaping, and a broad basket sheds the cooking water quickly."),
            ("8 inch chef knife kitchen", "8-inch chef's knife", "A sharp, controllable blade makes uniform pepper and onion dice for even cooking."),
        ]
    elif "crispy fried beef empanadas" in haystack:
        products = [
            ("6 quart enameled cast iron dutch oven", "5- to 6-quart Dutch oven", "High sides contain the two-inch oil layer and give it room to bubble safely without approaching the rim."),
            ("deep fry thermometer clip pot", "Clip-on deep-fry thermometer", "Continuous temperature readings keep each batch in the 340°F to 360°F crisping range."),
            ("half sheet pan wire rack set", "Sheet pan with wire rack", "A rack lets excess oil drain without trapping steam against the crisp underside of the empanadas."),
        ]
    elif "soupy sichuan-style dan dan noodles" in haystack or "soupy sichuan style dan dan noodles" in haystack:
        products = [
            ("stainless steel pasta pot colander", "Pasta pot and colander", "A roomy pot lets the wheat noodles move freely, while fast draining keeps them springy before they enter the hot sesame broth."),
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "A broad skillet gives the pork room to brown before the aromatics, chile-bean paste and preserved mustard greens are added."),
            ("large ramen bowls set", "Deep ramen-style bowls", "Deep heat-safe bowls leave enough room to whisk the sesame base with broth, then add noodles and toppings without spilling."),
        ]
    elif "weeknight aloo gobi" in haystack:
        products = [
            ("12 inch saute pan with lid", "Wide 12-inch sauté pan with lid", "The broad base coats the vegetables evenly, while the lid traps enough steam to tenderize potatoes and cauliflower without turning the curry soupy."),
            ("8 inch chef knife kitchen", "8-inch chef’s knife", "A sharp all-purpose blade makes even potato cubes and clean cauliflower florets so the vegetables become tender at the same time."),
            ("digital instant read thermometer kitchen", "Instant-read thermometer", "A thin probe confirms refrigerated leftovers have reheated to 165°F without relying on steam or touch."),
        ]
    elif "turkish çılbır" in haystack or "turkish cilbir" in haystack:
        products = [
            ("3 quart wide stainless steel saucepan", "Wide 3-quart saucepan", "A broad base gives four eggs room to poach in two calm batches without crowding or colliding."),
            ("stainless steel slotted spoon egg poacher", "Stainless-steel slotted spoon", "A shallow perforated bowl lifts delicate eggs while leaving excess poaching water behind."),
            ("instant read food thermometer thin probe", "Thin-probe instant-read thermometer", "A slim probe can verify a firm-cooked egg reaches 160°F without tearing most of the white."),
        ]
    elif "creamy lemon-parmesan farfalle" in haystack or "creamy lemon parmesan farfalle" in haystack:
        products = [
            ("stainless steel pasta pot colander", "Pasta pot and colander", "A roomy pot lets farfalle circulate, while fast draining preserves the starchy water needed to emulsify the cream sauce."),
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "A broad skillet warms the tomatoes gently and gives the pasta room to toss through the sauce without crushing the bow ties."),
            ("microplane zester grater stainless", "Fine zester and grater", "A fine tool removes fragrant lemon zest and produces Parmesan thin enough to melt smoothly off the heat."),
        ]
    elif "skillet chicken meatballs in tomato-basil sauce" in haystack or "skillet chicken meatballs in tomato basil sauce" in haystack:
        products = [
            ("wide 12 inch heavy skillet", "Wide 12-inch skillet", "A broad heavy pan browns the meatballs in batches, then holds all sixteen in one sauce layer for even simmering."),
            ("instant read thermometer ground poultry", "Instant-read thermometer", "Check the largest meatball and a cooler edge position for the required 165°F center without relying on color."),
            ("heavy rimmed sheet pan", "Heavy rimmed sheet pan", "A sturdy pan gives the garlic bread room to toast at the edges while the meatballs finish in their sauce."),
        ]
    elif "spinach-feta stuffed portobellos" in haystack or "spinach feta stuffed portobellos" in haystack:
        products = [
            ("heavy rimmed sheet pan", "Heavy rimmed sheet pan", "A broad metal pan gives four large mushroom caps room to shed moisture during the first roast without crowding."),
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "The broad surface evaporates liquid from the chopped stems and spinach before the creamy filling is assembled."),
            ("medium saucepan with lid 3 quart", "3-quart saucepan with lid", "A close-fitting lid and steady base cook pearl couscous evenly in the measured vegetable broth."),
        ]
    elif "air fryer chili-lime shrimp avocado toast" in haystack or "air fryer chili lime shrimp avocado toast" in haystack:
        products = [
            ("5 quart basket air fryer", "5- to 6-quart basket air fryer", "A roomy basket keeps one pound of shrimp in an uncrowded layer and then crisps the sourdough with the appliance already hot."),
            ("instant read digital food thermometer", "Instant-read thermometer", "Check the thickest shrimp for 145°F without extending the short cook until every piece curls tightly."),
            ("fine citrus zester microplane", "Fine citrus zester", "Remove fragrant lime zest for the shrimp while leaving the bitter white pith behind."),
        ]
    elif "roasted pumpkin-cardamom soup" in haystack or "roasted pumpkin cardamom soup" in haystack:
        products = [
            ("heavy rimmed sheet pan", "Heavy rimmed sheet pan", "A broad metal surface roasts the pumpkin wedges in one layer so their cut sides brown instead of steaming."),
            ("enameled dutch oven 5 quart", "5- to 6-quart Dutch oven", "A heavy pot softens the aromatics evenly and contains the hot soup safely during immersion blending."),
            ("immersion blender stainless steel", "Immersion blender", "Blend the roasted pumpkin directly in the pot with the head submerged, avoiding the transfer of hot soup to a sealed jar."),
        ]
    elif "chicken chilaquiles verdes" in haystack:
        products = [
            ("heavy rimmed sheet pan", "Heavy rimmed sheet pan", "A broad broiler-safe surface blisters the tomatillos, peppers, onion and garlic in one uncrowded layer."),
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "The wide base reduces the salsa evenly and gives sturdy tortilla chips room to fold without crushing."),
            ("digital probe cooking thermometer", "Instant-read thermometer", "Verify the reheated shredded chicken reaches 165°F before the tortilla chips enter the skillet."),
        ]
    elif "breton buckwheat galettes with smoked salmon" in haystack:
        products = [
            ("10 inch nonstick crepe pan", "10-inch nonstick crepe pan", "A low-sided, evenly heated surface makes it easier to spread, release and turn each thin buckwheat galette."),
            ("thin flexible silicone crepe spatula", "Thin flexible crepe spatula", "A broad, slim edge slides beneath a fully set galette without tearing its lacy rim."),
            ("mixing bowl with pouring spout", "Batter bowl with pouring spout", "A handled bowl keeps the rested batter easy to whisk and portion consistently between eight skillet rounds."),
        ]
    elif "slow cooker apple cider pulled pork sandwiches" in haystack:
        products = [
            ("6 quart programmable slow cooker", "6-quart programmable slow cooker", "The four pork portions, onions and measured cider-broth braise are calibrated for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several pork chunks for the 195 to 205°F shredding range instead of relying on the clock alone."),
            ("stainless steel fat separator 4 cup", "Fat separator", "Separate rendered pork fat from the cider braising liquid before reducing it into a concentrated finishing sauce."),
        ]
    elif "no-knead tomato, olive & red onion focaccia" in haystack or "no-knead tomato olive red onion focaccia" in haystack:
        products = [
            ("9 by 13 metal baking pan", "9-by-13-inch metal baking pan", "A light-colored metal pan gives the olive-oiled dough crisp, evenly browned edges without scorching the base."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Gram weights keep the high-hydration dough consistent and prevent extra flour from closing its open crumb."),
            ("digital probe cooking thermometer", "Instant-read thermometer", "A center reading of 200 to 205°F confirms the moist bread crumb has set before cooling."),
        ]
    elif "instant pot turkish kuru fasulye" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The soaked-bean volume, five-cup thin-liquid base and 20-minute natural release are written for this family capacity."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Pick over, rinse and drain the white beans cleanly before and after their overnight soak."),
            ("stainless steel soup ladle", "Stainless-steel soup ladle", "A deep ladle portions the creamy beans with enough tomato broth in every bowl."),
        ]
    elif "instant pot norwegian fårikål" in haystack or "instant pot norwegian farikal" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1½-cup thin-broth base, 20-minute cycle and two-stage release are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several lamb pieces away from bone for a safe center, then use temperature and fork texture to judge braise tenderness."),
            ("silicone tipped kitchen tongs", "Silicone-tipped kitchen tongs", "Brown lamb in batches and lift tender cabbage wedges without scratching the inner pot."),
        ]
    elif "cantonese-style char siu pork belly" in haystack:
        products = [
            ("heavy gauge aluminum half sheet pan wire rack", "Rimmed sheet pan with wire rack", "The rack circulates heat around the pork and keeps it above rendered fat while the glaze lacquers."),
            ("silicone pastry brush", "Silicone pastry brush", "Apply thin, even layers of the clean reserved honey marinade near the end of roasting."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Confirm the pork clears 145°F with a three-minute rest and continue toward the recipe's tender belly range."),
        ]
    elif "filipino lumpiang sariwa" in haystack:
        products = [
            ("8 inch nonstick skillet", "8-inch nonstick skillet", "A small slick surface turns the thin egg batter into consistently sized, flexible fresh-lumpia wrappers."),
            ("julienne peeler hand guard", "Julienne peeler with hand guard", "Uniform carrot and sweet-potato matchsticks cook evenly; use the guard and stop before the piece is unsafe to hold."),
            ("silicone whisk heat resistant", "Heat-safe silicone whisk", "Whisk the peanut sauce and cornstarch slurry smooth as they thicken on the stove."),
        ]
    elif "japanese dorayaki" in haystack:
        products = [
            ("12 inch nonstick griddle", "Nonstick griddle", "Steady medium-low heat produces several smooth, evenly golden three-inch pancake rounds at once."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weighing 120 grams of flour prevents a packed cup from making the honey pancakes dry."),
            ("2 tablespoon cookie scoop", "2-tablespoon scoop", "Equal batter portions make sixteen rounds that pair neatly around the anko filling."),
        ]
    elif "instant pot korean-style dakbokkeumtang" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1½-cup thin-broth base, eight-minute cycle and two-stage release are calibrated for this common family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several bone-in chicken pieces at their thickest points without touching bone and confirm each reaches 165°F."),
            ("silicone tipped kitchen tongs", "Silicone-tipped kitchen tongs", "Turn chicken and lift tender potatoes without scratching the inner pot or breaking the finished stew apart."),
        ]
    elif "instant pot romanian-style sarmale" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The half-full grain safeguard, 1½-cup broth base and 15-minute natural release are written for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Probe through the cabbage into several roll centers and verify every ground-meat filling reaches 160°F."),
            ("stainless steel slotted spoon", "Wide slotted spoon", "Lift the tender cabbage rolls from their broth with less tearing after the pressure release."),
        ]
    elif "dutch boerenkool stamppot" in haystack:
        products = [
            ("enameled dutch oven 6 quart", "Large Dutch oven", "One roomy pot simmers potatoes, steams kale and reheats the intact smoked sausage."),
            ("stainless steel potato masher", "Hand potato masher", "A hand masher combines the drained vegetables without releasing the excess starch a food processor would."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Confirm the fully cooked smoked sausage is reheated to 165°F at its center."),
        ]
    elif "puerto rican mofongo with garlic shrimp" in haystack:
        products = [
            ("wooden pilon mortar pestle large", "Large pilón or mortar", "Pound hot fried plantains with garlic and measured broth into four cohesive, rustic portions."),
            ("deep fry thermometer clip on", "Clip-on frying thermometer", "Hold the oil between 300°F and 325°F so the thick plantain rounds cook through without hardening."),
            ("digital probe cooking thermometer", "Instant-read thermometer", "Remove the shrimp from the simmering broth as soon as their thickest parts reach 145°F."),
        ]
    elif "australian lamingtons" in haystack:
        products = [
            ("8 inch square metal cake pan", "8-inch square metal cake pan", "The recipe's bake time and sixteen 2-inch portions are calibrated for this pan size."),
            ("wire cooling rack rimmed sheet pan", "Wire rack and rimmed sheet pan", "The rack catches excess chocolate and coconut while air reaches every coated side."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Gram weights keep the sponge light and the confectioners' sugar-to-cocoa coating consistent."),
        ]
    elif "instant pot french-style coq au vin" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The wine-and-broth base, ten-minute cycle and two-stage release are calibrated for this common family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several chicken thighs beside, but not touching, the bone and confirm each reaches 165°F."),
            ("silicone tipped kitchen tongs", "Silicone-tipped kitchen tongs", "Turn chicken and vegetables cleanly without scratching the inner pot during the two browning stages."),
        ]
    elif "instant pot vegan corn & potato chowder" in haystack or "instant pot vegan corn and potato chowder" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The four-cup thin-broth base, five-minute cycle and controlled release are written for this capacity."),
            ("immersion blender stainless steel", "Immersion blender", "Short pulses thicken part of the chowder while leaving visible potato pieces and corn kernels."),
            ("stainless steel soup ladle", "Stainless-steel soup ladle", "A deep ladle portions the chunky finished chowder without crushing its reserved corn and potatoes."),
        ]
    elif "spanish tortilla española" in haystack or "spanish tortilla espanola" in haystack:
        products = [
            ("10 inch nonstick skillet oven safe", "10-inch nonstick skillet", "A predictable release makes the thick potato-and-egg round safer to invert and slide back into the pan."),
            ("stainless steel mandoline slicer hand guard", "Mandoline with hand guard", "Uniform 1/8-inch potato slices soften at the same pace; always use the guard and stop early."),
            ("digital probe cooking thermometer", "Instant-read thermometer", "Check the thick center for the 160°F egg-safety target without overcooking the outer layers."),
        ]
    elif "sheet-pan chicken shawarma stuffed pitas" in haystack:
        products = [
            ("heavy gauge aluminum half sheet pan", "Heavy rimmed sheet pan", "Preheating a broad metal pan gives marinated thighs room to brown instead of steam."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify multiple thighs reach 165°F before resting, chopping or broiling their edges."),
            ("microplane zester grater stainless", "Fine zester", "Finely grate garlic for the marinade and sauce, then take clean zest from the lemon."),
        ]
    elif "argentine alfajores de maicena" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weighed cornstarch and flour prevent compacted cups from making the delicate cookies chalky."),
            ("2.5 inch round cookie cutter", "2½-inch round cutter", "One consistent diameter produces 28 matching rounds and 14 tidy sandwich cookies."),
            ("heavy rimmed baking sheet set", "Rimmed sheet pans", "Flat, light-colored pans help the cornstarch cookies set while their tops remain characteristically pale."),
        ]
    elif "instant pot mexican-style beef birria" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The three-cup thin-broth base, 45-minute cycle and 20-minute natural release are written for this family capacity."),
            ("fine mesh stainless steel strainer", "Fine-mesh strainer", "Strain the blended chile broth for a smoother consommé and fewer solids that can settle against the cooker base."),
            ("cast iron griddle 12 inch", "12-inch griddle", "A broad, heat-steady surface crisps several filled corn tortillas at once without crowding."),
        ]
    elif "instant pot indian-style vegetable biryani" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-cup rice quantity, measured thin broth, half-full safeguard and controlled release are calibrated for this capacity."),
            ("fine mesh rice strainer", "Fine-mesh rice strainer", "Rinse basmati thoroughly and drain it for ten minutes so the pressure-cooker liquid ratio stays accurate."),
            ("stainless steel serving fork rice", "Wide serving fork", "A broad fork lifts and separates the cooked grains without crushing the tender vegetables."),
        ]
    elif "greek-style lamb moussaka" in haystack:
        products = [
            ("9 by 13 ceramic baking dish deep", "Deep 9-by-13-inch baking dish", "Enough depth supports two eggplant layers, the lamb filling and a tall béchamel cap."),
            ("heavy rimmed baking sheet set", "Rimmed sheet pans", "Two broad pans roast the eggplant in one layer so it browns instead of steaming."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify the ground lamb reaches 160°F and the assembled casserole reaches 165°F at the center."),
        ]
    elif "korean-style tteokbokki" in haystack:
        products = [
            ("12 inch stainless steel skillet", "Wide 12-inch skillet", "A broad cooking surface reduces the broth into a glossy sauce while the rice cakes stay in a shallow, even layer."),
            ("silicone spatula heat resistant", "Heat-safe silicone spatula", "Frequent bottom-scraping keeps softening rice cakes from sticking without scratching the skillet."),
            ("digital probe cooking thermometer", "Instant-read thermometer", "Confirm the fish cakes are reheated to 165°F before serving."),
        ]
    elif "breton kouign-amann" in haystack:
        products = [
            ("standard metal muffin pan 12 cup", "12-cup metal muffin pan", "Metal cups drive the dark caramel shell and hold each folded pastry upright as it expands."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Gram weights keep the dough, butter block and shaping sugar balanced for dependable lamination."),
            ("french rolling pin hardwood", "Straight rolling pin", "A long smooth pin applies even pressure across the butter packet without creating thin hot spots."),
        ]
    elif "instant pot brazilian-style feijoada" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The soaked-bean volume, four-cup thin-broth base and 20-minute natural release are written for this family capacity."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Rinse and inspect black beans before soaking, then drain them thoroughly before pressure cooking."),
            ("stainless steel potato masher", "Stainless-steel bean masher", "Mash a measured scoop of tender beans against the pot wall to thicken the stew naturally."),
        ]
    elif "instant pot uzbek-style lamb plov" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-stage lamb-and-rice method, half-full grain limit and controlled releases are calibrated for this family capacity."),
            ("fine mesh rice strainer", "Fine-mesh rice strainer", "Rinse basmati until nearly clear and drain it for 15 minutes so the measured liquid ratio remains accurate."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify lamb reaches at least 145°F with a three-minute rest, then use tenderness to judge shoulder collagen."),
        ]
    elif "turkish mercimek köftesi" in haystack or "turkish mercimek koftesi" in haystack:
        products = [
            ("heavy bottom saucepan 3 quart", "Heavy 3-quart saucepan", "Even heat lets red lentils collapse without scorching as the last cooking liquid reduces."),
            ("stainless steel measuring cups spoons", "Measuring cup and spoon set", "Accurate lentil, water and fine-bulgur proportions determine whether the mixture shapes cleanly."),
            ("large rectangular serving platter", "Large serving platter", "A broad platter keeps the ridged kofta in neat rows with lemon and lettuce at the edges."),
        ]
    elif "peruvian causa rellena" in haystack:
        products = [
            ("stainless steel potato ricer", "Stainless-steel potato ricer", "Rice hot potatoes into a smooth, non-gluey base that holds a clean molded edge."),
            ("3 inch food ring molds set", "3-inch ring molds", "Straight-sided molds build six compact potato, tuna and avocado stacks with tidy layers."),
            ("offset spatula small stainless", "Small offset spatula", "Level each potato layer and lift filling cleanly without dragging it up the mold walls."),
        ]
    elif "south african-style malva puddings" in haystack:
        products = [
            ("8 ounce ceramic ramekins set of 6", "Six 8-ounce ramekins", "Individual dishes create the rounded presentation and give every serving caramelized edges."),
            ("rimmed baking sheet heavy duty", "Rimmed baking sheet", "A sturdy sheet keeps the six ramekins stable and contains any sauce that bubbles over."),
            ("digital probe cooking thermometer", "Digital cooking thermometer", "Check the egg-flour sponge for a 200–205°F center before adding the hot cream sauce."),
        ]
    elif "instant pot jamaican-style oxtail" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-cup thin-broth base, 45-minute cycle and 20-minute natural release are written for this family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check oxtail for safe temperature, then use the 195–205°F tenderness range and fork texture to judge collagen breakdown."),
            ("gravy fat separator heat resistant", "Heat-safe fat separator", "Separate the rendered oxtail fat from the cooking liquid before reducing the glossy butter-bean gravy."),
        ]
    elif "instant pot ghanaian-style chicken peanut stew" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-cup thin-broth base, six-minute cycle and ten-minute natural release are calibrated for this family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several chicken-thigh pieces at their centers for 165°F before finishing the peanut sauce."),
            ("silicone whisk heat resistant", "Heat-safe silicone whisk", "Whisk hot broth into peanut butter smoothly without scratching the pressure cooker's inner pot."),
        ]
    elif "balkan-style meat burek" in haystack:
        products = [
            ("12 inch round metal baking pan", "12-inch round baking pan", "A shallow metal pan supports the coiled phyllo and encourages a crisp, evenly browned base."),
            ("silicone pastry brush", "Silicone pastry brush", "A flexible brush spreads a thin, even layer of butter without tearing delicate phyllo sheets."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify the beef filling reaches 160°F and the assembled burek is hot through at the center."),
        ]
    elif "armenian-style ghapama" in haystack:
        products = [
            ("8 inch chef knife kitchen", "Chef's knife", "A sharp, controllable blade cuts the pumpkin lid cleanly; angle it inward so the lid cannot fall through."),
            ("enameled dutch oven 6 quart", "Snug Dutch oven", "A heavy, close-fitting vessel steadies the whole pumpkin and catches any syrup as the shell softens."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip and forearm coverage matter when moving a heavy, softened stuffed pumpkin from the oven."),
        ]
    elif "eastern european syrniki" in haystack:
        products = [
            ("12 inch nonstick skillet", "12-inch skillet", "A broad, even surface cooks four delicate cheese patties at a time without crowding."),
            ("silicone fish spatula turner", "Thin flexible spatula", "A slim edge slides beneath tender syrniki so their golden crusts stay intact when turned."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Confirm the egg-based centers reach 160°F without overbrowning the cheese cakes."),
        ]
    elif "instant pot hainanese-style chicken rice" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-cup thin-broth base, five-minute cycle, half-full grain safeguard and ten-minute natural release are written for this family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several chicken thighs beside, but not touching, the bone for 165°F before slicing or serving."),
            ("fine mesh rice strainer", "Fine-mesh rice strainer", "Rinse jasmine rice until the water is nearly clear, then drain it thoroughly so the measured pressure-cooker ratio stays accurate."),
        ]
    elif "instant pot greek beef stifado" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The wine-and-broth base, layered tomato, 35-minute cycle and 15-minute natural release are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Confirm beef clears 145°F with its three-minute rest, then use fork texture to judge the additional collagen breakdown needed for a braise."),
            ("silicone tipped kitchen tongs", "Silicone-tipped kitchen tongs", "Turn pearl onions and beef batches cleanly without scratching the inner pot or crowding the browning surface."),
        ]
    elif "thai-style shrimp som tam" in haystack:
        products = [
            ("large granite mortar pestle thai", "Large mortar and pestle", "A roomy sturdy mortar bruises green papaya and beans while leaving their centers crisp."),
            ("julienne peeler hand guard", "Julienne peeler with hand guard", "Uniform green-papaya strands absorb dressing evenly; use the guard and stop before the piece becomes unsafe to hold."),
            ("stainless steel citrus press", "Handheld citrus press", "Press enough fresh lime juice quickly for the sharp-salty-sweet dressing without seeds."),
        ]
    elif "syrian-style muhammara" in haystack:
        products = [
            ("food processor 8 cup", "8-cup food processor", "Short controlled pulses combine roasted peppers, walnuts and breadcrumbs while preserving the dip's characteristic texture."),
            ("rimmed baking sheet heavy duty", "Rimmed baking sheet", "Toast walnuts evenly, then reuse the same pan for zaatar-dusted pita wedges."),
            ("silicone spatula heat resistant", "Flexible silicone spatula", "Scrape the processor bowl thoroughly and shape the finished dip into a clean serving swirl."),
        ]
    elif "belgian liège waffles" in haystack or "belgian liege waffles" in haystack:
        products = [
            ("belgian waffle maker adjustable temperature", "Adjustable Belgian waffle maker", "Medium heat gives the enriched dough time to cook through while pearl sugar caramelizes instead of scorching."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weigh flour, butter, pearl sugar and each dough portion for eight evenly cooking waffles."),
            ("digital probe cooking thermometer", "Digital cooking thermometer", "Check 105–110°F milk for yeast and a minimum 190°F in each waffle's bready center."),
        ]
    elif "instant pot dominican-style sancocho" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-stage pork, chicken and root-vegetable method, four-cup thin-broth base and controlled releases are written for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check chicken pieces for 165°F and pork for at least 145°F plus fork-tender texture before serving the family bowls."),
            ("8 inch chef knife kitchen", "8-inch chef’s knife", "A sharp all-purpose blade makes consistent cuts through plantain, yuca, squash, corn and both meats."),
        ]
    elif "instant pot italian-style creamy polenta" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The trivet, base-water amount, ten-minute cycle and natural release are calibrated for this common family capacity."),
            ("stainless steel pressure cooker insert bowl 3 quart", "Pressure-cooker-safe inner bowl", "A 2½- to 3-quart uncovered metal bowl keeps expanding cornmeal off the heating element for pot-in-pot cooking."),
            ("12 inch cast iron skillet", "12-inch skillet", "A broad hot surface browns sliced mushrooms in batches while the polenta cooks hands-off."),
        ]
    elif "finnish lohikeitto" in haystack:
        products = [
            ("heavy bottom dutch oven 5 quart", "Heavy 5-quart soup pot", "Steady heat brings potatoes to tenderness, then holds the salmon and cream at a bare simmer."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several thick salmon pieces for 145°F without overcooking the entire pot."),
            ("stainless steel fish bone tweezers", "Fish-bone tweezers", "A precise grip removes hidden pin bones cleanly before the salmon is cut into soup-size pieces."),
        ]
    elif "south indian-style masala dosa" in haystack:
        products = [
            ("countertop blender glass jar", "High-speed countertop blender", "Separate smooth rice and urad-dal batters combine into a reliably aerated base for overnight fermentation."),
            ("cast iron dosa tawa griddle 12 inch", "12-inch dosa griddle", "A broad, moderately hot surface gives the ladle room to spread thin spirals and crisp their undersides."),
            ("stainless steel offset spatula wide", "Wide offset spatula", "A slim broad edge releases each lacy dosa without tearing before the potato filling is added."),
        ]
    elif "german bienenstich" in haystack:
        products = [
            ("9 inch springform pan", "9-inch springform pan", "Tall removable sides support the yeast cake, almond crown and substantial vanilla-cream layer."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weighed flour keeps the enriched dough soft enough to rise while still holding the filling."),
            ("digital probe meat thermometer", "Digital cooking thermometer", "Check warm milk, pastry cream and the cake center at their different target temperatures instead of guessing."),
        ]
    elif "instant pot vietnamese-style bò kho" in haystack or "instant pot vietnamese-style bo kho" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The two-stage meat-and-root-vegetable method, measured thin broth and controlled releases are written for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check beef for at least 145°F and honeycomb tripe for 160°F before serving the aromatic noodle bowls."),
            ("stainless steel pasta pot colander", "Pasta pot and colander", "Cook and drain the noodles separately so their starch cannot thicken the pressure-cooker liquid or stick to its base."),
        ]
    elif "instant pot egyptian-style ful medames" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The soaked-bean volume, half-full safeguard, 35-minute cycle and full natural release are calibrated for this capacity."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Fine mesh contains the small fava beans while you rinse them, inspect for stones and drain the overnight soak."),
            ("stainless steel potato masher", "Stainless-steel bean masher", "Mash one-third of the cooked favas directly in the pot to build the platter's naturally creamy body."),
        ]
    elif "japanese oyakodon" in haystack:
        products = [
            ("10 inch stainless steel skillet lid", "10-inch skillet with lid", "A lidded shallow pan cooks the chicken in one layer and lets the two egg additions set evenly over the onion."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify several chicken pieces reach 165°F and the finished egg mixture reaches 160°F without overcooking the whole bowl."),
            ("stainless steel rice cooker family", "Family-size rice cooker", "Cook and hold the short-grain rice hands-off while the chicken-and-egg topping comes together in about 20 minutes."),
        ]
    elif "bacalhau à brás" in haystack or "bacalhau a bras" in haystack:
        products = [
            ("stainless steel mandoline slicer hand guard", "Mandoline with hand guard", "Uniform 1/8-inch potato matchsticks fry at the same rate; always use the included guard and a cut-resistant glove."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Confirm the poached cod reaches 145°F and the final egg mixture reaches 160°F."),
            ("stainless steel spider strainer", "Spider strainer", "Lift each batch of crisp potato sticks from the hot oil quickly while leaving loose crumbs behind."),
        ]
    elif "tarte tatin" in haystack:
        products = [
            ("10 inch cast iron skillet", "10-inch cast-iron skillet", "A heat-steady oven-safe skillet takes the caramel, tightly packed apples and pastry from stovetop to oven in one pan."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weights keep the apple and pastry proportions consistent so the inverted tart is fruit-forward without overloading its crust."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure hand and forearm protection is essential when inverting a skillet filled with very hot caramel."),
        ]
    elif "instant pot louisiana-style red beans" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The six-cup thin-liquid ratio, half-full bean limit and long natural release are written for this common family capacity."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Fine mesh contains dry kidney beans while you rinse away dust and inspect carefully for small stones."),
            ("heavy bottom rice saucepan lid", "Heavy saucepan with lid", "Cooking the white rice separately keeps its grains fluffy while the beans complete their much longer pressure cycle."),
        ]
    elif "instant pot persian-style chicken fesenjan" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The thin-broth pressure stage and post-pressure walnut reduction are calibrated for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several chicken thighs for 165°F before building the thick walnut-pomegranate sauce."),
            ("food processor 8 cup", "8-cup food processor", "Short pulses grind toasted walnuts finely enough to thicken the sauce without turning them into nut butter."),
        ]
    elif "instant pot taiwanese-style lu rou fan" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1 1/2-cup thin-broth base, 18-minute cycle and staged release are calibrated for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check pork from different parts of the pot for 145°F followed by the specified three-minute rest."),
            ("stainless steel rice cooker family", "Family-size rice cooker", "It cooks and holds the separate short-grain rice while the pork browns, pressure-cooks and reduces."),
        ]
    elif "instant pot swedish-style meatballs" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1 1/2-cup thin-broth base, two loose meatball layers and staged release are written for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check beef-and-pork meatballs from both layers through the center for the required 160°F."),
            ("stainless steel potato masher", "Stainless-steel potato masher", "Mash the separately simmered Yukon Golds while the pressure-cooked meatballs rest before their gravy finish."),
        ]
    elif "instant pot japanese-style beef curry" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The short sirloin-and-vegetable cycle, thin-broth base and fill-limit guidance are written for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several sirloin pieces for 145°F and give them the specified three-minute rest before serving."),
            ("stainless steel rice cooker family", "Family-size rice cooker", "It cooks and holds the short-grain rice while the beef and vegetables complete their shared pressure cycle."),
        ]
    elif "instant pot rajma masala" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The layered tomato method, 1 1/2-cup thin-liquid base and staged release are calibrated for this capacity."),
            ("stainless steel potato masher", "Stainless-steel potato masher", "A few presses against the pot wall thicken the bean gravy without turning every kidney bean into purée."),
            ("12 inch cast iron skillet", "12-inch cast-iron skillet", "A broad dry surface warms six roti quickly while the finished rajma rests off heat."),
        ]
    elif "instant pot filipino-style chicken arroz caldo" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The six-cup thin-broth base, half-full grain limit and staged release are written for this common family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several chicken pieces for 165°F before shredding instead of relying on pressure time alone."),
            ("stainless steel mesh colander strainer", "Fine-mesh strainer", "Fine mesh keeps jasmine rice contained while you rinse away excess surface starch before pressure cooking."),
        ]
    elif "instant pot polish-style bigos" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1 1/2-cup thin-broth base, 30-minute cycle and staged release are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Temperature plus easy fork tenderness confirms that pork shoulder is both safe and ready to eat."),
            ("8 inch chef knife kitchen", "8-inch chef’s knife", "A sharp all-purpose blade handles pork cubes, cabbage ribbons, mushrooms and sausage with consistent cuts."),
        ]
    elif "instant pot cuban-style ropa vieja" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1 1/2-cup thin-broth base, 50-minute cycle and staged release are written for this family-size capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Chuck becomes safe before it becomes shreddable; temperature plus an easy-pulling texture confirms the intended finish."),
            ("long stainless steel kitchen tongs", "Long stainless-steel tongs", "A secure reach makes browning large pieces and lifting hot pressure-braised beef safer and more controlled."),
        ]
    elif "instant pot ukrainian-style beet borscht" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The six-cup thin-liquid base, vegetable load and staged release are calibrated for this common capacity."),
            ("8 inch chef knife kitchen", "8-inch chef’s knife", "A sharp controllable blade makes the beet, potato, carrot and cabbage prep faster and more even."),
            ("glass meal prep containers locking lids", "Glass meal-prep containers", "Shallow lidded containers help the soup cool promptly and make refrigerator or freezer portions practical."),
        ]
    elif "instant pot korean galbijjim" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The thin-broth base, 35-minute cycle and staged release are written for this common family size."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Short ribs become safe before they become tender; temperature plus an easy-piercing texture confirms the intended finish."),
            ("stainless steel mesh colander strainer", "Fine-mesh strainer", "A fine strainer catches bone fragments during a quick rinse and helps skim the finished pear-soy braising sauce cleanly."),
        ]
    elif "instant pot lowcountry shrimp boil" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1 1/2-cup thin-liquid base and four-minute potato cycle are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several shrimp for 145°F during their brief post-pressure finish instead of guessing from color alone."),
            ("long stainless steel kitchen tongs", "Long stainless-steel tongs", "A secure reach moves hot corn, sausage and shrimp from the seasoned broth without crowding the platter."),
        ]
    elif "instant pot québec-style yellow split pea soup" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The liquid, half-full limit, pressurizing allowance and natural release are written for this common family size."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Fine mesh contains small split peas while you rinse away dust and sort out any debris before pressure cooking."),
            ("glass meal prep containers locking lids", "Glass meal-prep containers", "Shallow lidded containers help the thick soup cool promptly and make portioned refrigerator or freezer storage practical."),
        ]
    elif "instant pot saffron shrimp risotto" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The four-cup thin-liquid ratio, five-minute cycle and controlled release are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several shrimp for 145°F during the brief Sauté finish instead of pressure-cooking them until rubbery."),
            ("microplane zester grater stainless", "Fine zester and grater", "One fine tool handles the lemon zest and Parmesan that brighten and finish the creamy rice."),
        ]
    elif "instant pot smoky black bean soup" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The six-cup thin-liquid ratio, half-full limit and long natural release are written for this common family size."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Fine mesh keeps dry black beans contained while you rinse away dust and check carefully for small stones."),
            ("immersion blender stainless steel", "Immersion blender", "A few controlled pulses thicken the soup while leaving plenty of whole beans for texture."),
        ]
    elif "instant pot chicken cacciatore" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The deglazed wine-and-broth base, ten-minute cycle and staged release are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check every bone-in chicken piece away from bone for at least 165°F before serving."),
            ("stainless steel pasta pot colander", "Pasta pot and colander", "Boiling the egg noodles separately keeps them springy while the chicken and tomato sauce pressure-cook."),
        ]
    elif "instant pot dal makhani" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The five-cup thin-water base, half-full bean limit and long natural release are written for this capacity."),
            ("stainless steel mesh colander strainer", "Fine-mesh colander", "Fine mesh keeps whole black gram and kidney beans contained while you rinse and inspect them carefully."),
            ("12 inch cast iron skillet", "12-inch cast-iron skillet", "A broad dry surface warms six naan quickly while the finished dal rests off heat."),
        ]
    elif "instant pot hawaiian-style kālua pork" in haystack or "instant pot hawaiian-style kalua pork" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The four equal pork chunks, 1 1/4-cup thin-liquid base and staged release are calibrated for this capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Temperature plus easy fork-twisting confirms that pork shoulder is both safe and ready to shred."),
            ("stainless steel rice cooker family", "Family-size rice cooker", "It cooks and holds the separate medium-grain rice while pork pressure-cooks and cabbage finishes in the juices."),
        ]
    elif "instant pot thai-style massaman chicken" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The 1 1/2-cup thin-broth base, six-minute cycle and staged release are calibrated for this common family capacity."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check chicken pieces from several parts of the pot for 165°F before the coconut finish."),
            ("stainless steel rice cooker family", "Family-size rice cooker", "It cooks and holds the jasmine rice separately while the curry pressure-cooks and its coconut sauce reduces."),
        ]
    elif "instant pot lebanese-style mujaddara" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The divided 3 3/4-cup thin-broth ratio, half-full grain limit and two natural releases are written for this capacity."),
            ("12 inch cast iron skillet", "12-inch cast-iron skillet", "A broad surface gives three onions room to lose moisture and caramelize while the lentils and rice cook."),
            ("stainless steel mesh colander strainer", "Fine-mesh strainer", "Fine mesh contains lentils and brown rice while you rinse away dust and excess surface starch."),
        ]
    elif "instant pot southern chicken & flat dumplings" in haystack or "instant pot southern chicken and flat dumplings" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The four-cup thin-broth base, eight-minute cycle and staged release are calibrated for this common family capacity."),
            ("wood rolling pin 18 inch", "Wooden rolling pin", "A smooth pin rolls the rested dumpling dough evenly to the thin one-eighth-inch sheet needed for flat strips."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Check several thigh pieces for 165°F and the finished creamy soup for a safe 165°F reheat."),
        ]
    elif "instant pot ecuadorian-style locro de queso" in haystack:
        products = [
            ("6 quart electric pressure cooker", "6-quart electric pressure cooker", "The four-cup thin-broth base, potato load and controlled release are written for this capacity."),
            ("stainless steel potato masher", "Stainless-steel potato masher", "Coarse mashing thickens the locro naturally while leaving enough visible potato pieces for texture."),
 …37097 tokens truncated…h uncoated chili-lime shrimp, breaded chicken cutlets and soaked potato wedges by food type, basket temperature, turning point and reliable doneness cue.",
    },
    "air-fryer-chicken-parmesan": {
        "slugs": ["air-fryer-chili-lime-shrimp-avocado-toasts", "air-fryer-salmon-bites", "air-fryer-crispy-potato-wedges"],
        "eyebrow": "Air-fryer technique",
        "title": "Choose an air-fryer recipe by coating and doneness cue",
        "copy": "Compare breaded chicken cutlets with uncoated chili-lime shrimp, salmon cubes and soaked potato wedges by food type, basket temperature, turning point and reliable doneness cue.",
    },
    "air-fryer-crispy-potato-wedges": {
        "slugs": ["air-fryer-chili-lime-shrimp-avocado-toasts", "air-fryer-salmon-bites", "air-fryer-chicken-parmesan"],
        "eyebrow": "Air-fryer technique",
        "title": "Choose an air-fryer recipe by coating and doneness cue",
        "copy": "Compare soaked potato wedges with uncoated chili-lime shrimp, salmon cubes and breaded chicken cutlets by food type, basket temperature, turning point and reliable doneness cue.",
    },
    "roasted-pumpkin-cardamom-soup-pepitas-lime-crema": {
        "slugs": ["roasted-sweet-potato-ginger-soup", "instant-pot-vegan-corn-potato-chowder-chives", "instant-pot-broccoli-cheddar-soup"],
        "eyebrow": "Blended soup methods",
        "title": "Choose a cozy soup by base and blending method",
        "copy": "Compare silky oven-roasted pumpkin with warm spices, roasted sweet potato with ginger, a partially blended vegan corn-potato chowder and pressure-cooked broccoli-cheddar soup by vegetable base, texture and richness.",
    },
    "roasted-sweet-potato-ginger-soup": {
        "slugs": ["roasted-pumpkin-cardamom-soup-pepitas-lime-crema", "instant-pot-vegan-corn-potato-chowder-chives", "instant-pot-broccoli-cheddar-soup"],
        "eyebrow": "Blended soup methods",
        "title": "Choose a cozy soup by base and blending method",
        "copy": "Compare roasted sweet potato with ginger, silky oven-roasted pumpkin with warm spices, a partially blended vegan corn-potato chowder and pressure-cooked broccoli-cheddar soup by vegetable base, texture and richness.",
    },
    "instant-pot-vegan-corn-potato-chowder-chives": {
        "slugs": ["roasted-pumpkin-cardamom-soup-pepitas-lime-crema", "roasted-sweet-potato-ginger-soup", "instant-pot-broccoli-cheddar-soup"],
        "eyebrow": "Blended soup methods",
        "title": "Choose a cozy soup by base and blending method",
        "copy": "Compare a partially blended vegan corn-potato chowder with silky oven-roasted pumpkin and warm spices, roasted sweet potato with ginger and pressure-cooked broccoli-cheddar soup by vegetable base, texture and richness.",
    },
    "instant-pot-broccoli-cheddar-soup": {
        "slugs": ["roasted-pumpkin-cardamom-soup-pepitas-lime-crema", "roasted-sweet-potato-ginger-soup", "instant-pot-vegan-corn-potato-chowder-chives"],
        "eyebrow": "Blended soup methods",
        "title": "Choose a cozy soup by base and blending method",
        "copy": "Compare pressure-cooked broccoli-cheddar soup with silky oven-roasted pumpkin and warm spices, roasted sweet potato with ginger and a partially blended vegan corn-potato chowder by vegetable base, texture and richness.",
    },
    "chicken-chilaquiles-verdes-cotija-red-onion": {
        "slugs": ["rotisserie-chicken-enchilada-casserole", "instant-pot-mexican-beef-birria-tacos-consomme", "weeknight-beef-taco-skillet"],
        "eyebrow": "Mexican-inspired tortilla formats",
        "title": "Choose a tortilla dinner by texture and method",
        "copy": "Compare salsa-folded chilaquiles with a layered enchilada casserole, pressure-braised birria tacos and a one-pan beef-and-rice taco skillet by tortilla format, active time and texture.",
    },
    "rotisserie-chicken-enchilada-casserole": {
        "slugs": ["chicken-chilaquiles-verdes-cotija-red-onion", "instant-pot-mexican-beef-birria-tacos-consomme", "weeknight-beef-taco-skillet"],
        "eyebrow": "Mexican-inspired tortilla formats",
        "title": "Choose a tortilla dinner by texture and method",
        "copy": "Compare a layered enchilada casserole with salsa-folded chilaquiles, pressure-braised birria tacos and a one-pan beef-and-rice taco skillet by tortilla format, active time and texture.",
    },
    "instant-pot-mexican-beef-birria-tacos-consomme": {
        "slugs": ["chicken-chilaquiles-verdes-cotija-red-onion", "rotisserie-chicken-enchilada-casserole", "weeknight-beef-taco-skillet"],
        "eyebrow": "Mexican-inspired tortilla formats",
        "title": "Choose a tortilla dinner by texture and method",
        "copy": "Compare crisp pressure-braised birria tacos with salsa-folded chilaquiles, a layered enchilada casserole and a one-pan beef-and-rice taco skillet by tortilla format, active time and texture.",
    },
    "weeknight-beef-taco-skillet": {
        "slugs": ["chicken-chilaquiles-verdes-cotija-red-onion", "rotisserie-chicken-enchilada-casserole", "instant-pot-mexican-beef-birria-tacos-consomme"],
        "eyebrow": "Mexican-inspired tortilla formats",
        "title": "Choose a tortilla dinner by texture and method",
        "copy": "Compare a one-pan beef-and-rice taco skillet with salsa-folded chilaquiles, a layered enchilada casserole and crisp pressure-braised birria tacos by tortilla format, active time and texture.",
    },
    "breton-buckwheat-galettes-smoked-salmon-dill-creme-fraiche": {
        "slugs": ["bistro-croque-madame-gruyere-bechamel-greens", "smoky-roasted-pepper-shakshuka-feta", "spanish-tortilla-espanola-potato-onion"],
        "eyebrow": "Savory brunch techniques",
        "title": "Choose a savory brunch by pan method",
        "copy": "Compare thin buckwheat galettes with cool smoked-salmon toppings, a griddled croque madame, eggs poached in pepper-tomato sauce and a deep potato-onion tortilla by active time, pan technique and make-ahead potential.",
    },
    "bistro-croque-madame-gruyere-bechamel-greens": {
        "slugs": ["breton-buckwheat-galettes-smoked-salmon-dill-creme-fraiche", "smoky-roasted-pepper-shakshuka-feta", "spanish-tortilla-espanola-potato-onion"],
        "eyebrow": "Savory brunch techniques",
        "title": "Choose a savory brunch by pan method",
        "copy": "Compare a griddled croque madame with thin buckwheat galettes and cool smoked-salmon toppings, eggs poached in pepper-tomato sauce and a deep potato-onion tortilla by active time, pan technique and make-ahead potential.",
    },
    "smoky-roasted-pepper-shakshuka-feta": {
        "slugs": ["breton-buckwheat-galettes-smoked-salmon-dill-creme-fraiche", "bistro-croque-madame-gruyere-bechamel-greens", "spanish-tortilla-espanola-potato-onion"],
        "eyebrow": "Savory brunch techniques",
        "title": "Choose a savory brunch by pan method",
        "copy": "Compare eggs poached in pepper-tomato sauce with thin buckwheat galettes and cool smoked-salmon toppings, a griddled croque madame and a deep potato-onion tortilla by active time, pan technique and make-ahead potential.",
    },
    "spanish-tortilla-espanola-potato-onion": {
        "slugs": ["persian-style-kuku-sabzi-walnuts-barberries", "breton-buckwheat-galettes-smoked-salmon-dill-creme-fraiche", "bistro-croque-madame-gruyere-bechamel-greens", "smoky-roasted-pepper-shakshuka-feta"],
        "eyebrow": "Savory brunch techniques",
        "title": "Choose a savory brunch by pan method",
        "copy": "Compare a deep potato-onion tortilla with thin buckwheat galettes and cool smoked-salmon toppings, a griddled croque madame and eggs poached in pepper-tomato sauce by active time, pan technique and make-ahead potential.",
    },
    "slow-cooker-apple-cider-pulled-pork-sandwiches-mustard-slaw": {
        "slugs": ["slow-cooker-salsa-verde-chicken", "slow-cooker-white-chicken-chili", "slow-cooker-beef-mushroom-ragu"],
        "eyebrow": "Slow-cooker dinner methods",
        "title": "Choose a slow-cooker dinner by cut and finish",
        "copy": "Compare shreddable cider-braised pork sandwiches, bright salsa-verde chicken, creamy white chicken chili and beef-mushroom ragu by protein, finishing step and serving style.",
    },
    "slow-cooker-salsa-verde-chicken": {
        "slugs": ["slow-cooker-apple-cider-pulled-pork-sandwiches-mustard-slaw", "slow-cooker-white-chicken-chili", "slow-cooker-beef-mushroom-ragu"],
        "eyebrow": "Slow-cooker dinner methods",
        "title": "Choose a slow-cooker dinner by cut and finish",
        "copy": "Compare bright salsa-verde chicken with shreddable cider-braised pork sandwiches, creamy white chicken chili and beef-mushroom ragu by protein, finishing step and serving style.",
    },
    "slow-cooker-white-chicken-chili": {
        "slugs": ["slow-cooker-apple-cider-pulled-pork-sandwiches-mustard-slaw", "slow-cooker-salsa-verde-chicken", "slow-cooker-beef-mushroom-ragu"],
        "eyebrow": "Slow-cooker dinner methods",
        "title": "Choose a slow-cooker dinner by cut and finish",
        "copy": "Compare creamy white chicken chili with shreddable cider-braised pork sandwiches, bright salsa-verde chicken and beef-mushroom ragu by protein, finishing step and serving style.",
    },
    "slow-cooker-beef-mushroom-ragu": {
        "slugs": ["slow-cooker-apple-cider-pulled-pork-sandwiches-mustard-slaw", "slow-cooker-salsa-verde-chicken", "slow-cooker-white-chicken-chili"],
        "eyebrow": "Slow-cooker dinner methods",
        "title": "Choose a slow-cooker dinner by cut and finish",
        "copy": "Compare beef-mushroom ragu with shreddable cider-braised pork sandwiches, bright salsa-verde chicken and creamy white chicken chili by protein, finishing step and serving style.",
    },
    "no-knead-tomato-olive-red-onion-focaccia": {
        "slugs": ["homemade-margherita-pizza-no-cook-tomato-sauce", "irish-brown-soda-bread-buttermilk-oats", "adjarian-khachapuri-feta-mozzarella-jammy-egg"],
        "eyebrow": "Bread-making techniques",
        "title": "Choose a homemade bread project by technique",
        "copy": "Compare high-hydration no-knead focaccia, hand-stretched pizza, quick soda bread and an enriched cheese-filled bread boat by leavening, shaping and total time.",
    },
    "homemade-margherita-pizza-no-cook-tomato-sauce": {
        "slugs": ["no-knead-tomato-olive-red-onion-focaccia", "irish-brown-soda-bread-buttermilk-oats", "adjarian-khachapuri-feta-mozzarella-jammy-egg"],
        "eyebrow": "Bread-making techniques",
        "title": "Choose a homemade bread project by technique",
        "copy": "Compare hand-stretched pizza, high-hydration no-knead focaccia, quick soda bread and an enriched cheese-filled bread boat by leavening, shaping and total time.",
    },
    "irish-brown-soda-bread-buttermilk-oats": {
        "slugs": ["no-knead-tomato-olive-red-onion-focaccia", "homemade-margherita-pizza-no-cook-tomato-sauce", "adjarian-khachapuri-feta-mozzarella-jammy-egg"],
        "eyebrow": "Bread-making techniques",
        "title": "Choose a homemade bread project by technique",
        "copy": "Compare quick soda bread with high-hydration no-knead focaccia, hand-stretched pizza and an enriched cheese-filled bread boat by leavening, shaping and total time.",
    },
    "adjarian-khachapuri-feta-mozzarella-jammy-egg": {
        "slugs": ["no-knead-tomato-olive-red-onion-focaccia", "homemade-margherita-pizza-no-cook-tomato-sauce", "irish-brown-soda-bread-buttermilk-oats"],
        "eyebrow": "Bread-making techniques",
        "title": "Choose a homemade bread project by technique",
        "copy": "Compare an enriched cheese-filled bread boat with high-hydration no-knead focaccia, hand-stretched pizza and quick soda bread by leavening, shaping and total time.",
    },
    "turkish-mercimek-koftesi-lemon-fresh-herbs": {
        "slugs": ["syrian-style-muhammara-roasted-pepper-walnut-dip", "crispy-herb-falafel-pita-lemon-tahini-sauce", "georgian-beet-pkhali-mchadi-pomegranate"],
        "eyebrow": "Plant-based mezze",
        "title": "Build a varied plant-based sharing table",
        "copy": "Pair no-fry lentil-and-bulgur kofta with roasted-pepper walnut dip, crisp chickpea falafel, and beet-walnut pkhali to compare four distinct bases, textures, and make-ahead strategies.",
    },
    "syrian-style-muhammara-roasted-pepper-walnut-dip": {
        "slugs": ["turkish-mercimek-koftesi-lemon-fresh-herbs", "crispy-herb-falafel-pita-lemon-tahini-sauce", "georgian-beet-pkhali-mchadi-pomegranate"],
        "eyebrow": "Plant-based mezze",
        "title": "Build a varied plant-based sharing table",
        "copy": "Pair roasted-pepper walnut dip with no-fry lentil-and-bulgur kofta, crisp chickpea falafel, and beet-walnut pkhali to compare four distinct bases, textures, and make-ahead strategies.",
    },
    "georgian-beet-pkhali-mchadi-pomegranate": {
        "slugs": ["turkish-mercimek-koftesi-lemon-fresh-herbs", "syrian-style-muhammara-roasted-pepper-walnut-dip", "crispy-herb-falafel-pita-lemon-tahini-sauce"],
        "eyebrow": "Plant-based mezze",
        "title": "Build a varied plant-based sharing table",
        "copy": "Pair beet-walnut pkhali with no-fry lentil-and-bulgur kofta, roasted-pepper walnut dip, and crisp chickpea falafel to compare four distinct bases, textures, and make-ahead strategies.",
    },
    "palestinian-style-musakhan-sumac-chicken-onion-flatbread": {
        "slugs": ["lebanese-style-chicken-shish-tawook-pita-garlic-yogurt", "crispy-herb-falafel-pita-lemon-tahini-sauce", "creamy-stovetop-butter-chicken-garlic-naan"],
        "eyebrow": "Flatbread dinners",
        "title": "Choose a flatbread-centered dinner by technique",
        "copy": "Compare sumac-roasted chicken over onion-soaked bread, grilled yogurt-marinated skewers, crisp falafel with tahini, and tomato-cream chicken with naan by cooking method and weeknight effort.",
    },
    "lebanese-style-chicken-shish-tawook-pita-garlic-yogurt": {
        "slugs": ["palestinian-style-musakhan-sumac-chicken-onion-flatbread", "crispy-herb-falafel-pita-lemon-tahini-sauce", "creamy-stovetop-butter-chicken-garlic-naan"],
        "eyebrow": "Flatbread dinners",
        "title": "Choose a flatbread-centered dinner by technique",
        "copy": "Compare sumac-roasted chicken over onion-soaked bread, grilled yogurt-marinated skewers, crisp falafel with tahini, and tomato-cream chicken with naan by cooking method and weeknight effort.",
    },
    "crispy-herb-falafel-pita-lemon-tahini-sauce": {
        "slugs": ["palestinian-style-musakhan-sumac-chicken-onion-flatbread", "lebanese-style-chicken-shish-tawook-pita-garlic-yogurt", "creamy-stovetop-butter-chicken-garlic-naan"],
        "eyebrow": "Flatbread dinners",
        "title": "Choose a flatbread-centered dinner by technique",
        "copy": "Compare sumac-roasted chicken over onion-soaked bread, grilled yogurt-marinated skewers, crisp falafel with tahini, and tomato-cream chicken with naan by cooking method and weeknight effort.",
    },
    "creamy-stovetop-butter-chicken-garlic-naan": {
        "slugs": ["palestinian-style-musakhan-sumac-chicken-onion-flatbread", "lebanese-style-chicken-shish-tawook-pita-garlic-yogurt", "crispy-herb-falafel-pita-lemon-tahini-sauce"],
        "eyebrow": "Flatbread dinners",
        "title": "Choose a flatbread-centered dinner by technique",
        "copy": "Compare sumac-roasted chicken over onion-soaked bread, grilled yogurt-marinated skewers, crisp falafel with tahini, and tomato-cream chicken with naan by cooking method and weeknight effort.",
    },
    "indonesian-beef-rendang-coconut-toasted-spices": {
        "slugs": ["moroccan-lamb-tagine-prunes-almonds-quail-eggs", "filipino-style-pork-adobo-eggs-steamed-rice", "oven-braised-beef-stew-potatoes-mushrooms-peas"],
        "eyebrow": "Braising technique",
        "title": "Compare four paths to tender, deeply flavored meat",
        "copy": "See how uncovered coconut reduction, a covered fruit-and-spice tagine, soy-vinegar adobo and a red-wine oven braise use different liquids and finishing methods to transform collagen-rich cuts.",
    },
    "moroccan-lamb-tagine-prunes-almonds-quail-eggs": {
        "slugs": ["indonesian-beef-rendang-coconut-toasted-spices", "filipino-style-pork-adobo-eggs-steamed-rice", "oven-braised-beef-stew-potatoes-mushrooms-peas"],
        "eyebrow": "Braising technique",
        "title": "Compare four paths to tender, deeply flavored meat",
        "copy": "See how uncovered coconut reduction, a covered fruit-and-spice tagine, soy-vinegar adobo and a red-wine oven braise use different liquids and finishing methods to transform collagen-rich cuts.",
    },
    "filipino-style-pork-adobo-eggs-steamed-rice": {
        "slugs": ["indonesian-beef-rendang-coconut-toasted-spices", "moroccan-lamb-tagine-prunes-almonds-quail-eggs", "oven-braised-beef-stew-potatoes-mushrooms-peas"],
        "eyebrow": "Braising technique",
        "title": "Compare four paths to tender, deeply flavored meat",
        "copy": "See how uncovered coconut reduction, a covered fruit-and-spice tagine, soy-vinegar adobo and a red-wine oven braise use different liquids and finishing methods to transform collagen-rich cuts.",
    },
    "oven-braised-beef-stew-potatoes-mushrooms-peas": {
        "slugs": ["indonesian-beef-rendang-coconut-toasted-spices", "moroccan-lamb-tagine-prunes-almonds-quail-eggs", "filipino-style-pork-adobo-eggs-steamed-rice"],
        "eyebrow": "Braising technique",
        "title": "Compare four paths to tender, deeply flavored meat",
        "copy": "See how uncovered coconut reduction, a covered fruit-and-spice tagine, soy-vinegar adobo and a red-wine oven braise use different liquids and finishing methods to transform collagen-rich cuts.",
    },
    "classic-new-england-clam-chowder-potatoes-saltines": {
        "slugs": ["moroccan-style-vegetarian-harira-lentils-chickpeas", "classic-french-onion-soup-gruyere-toasts", "turkish-red-lentil-soup-aleppo-butter"],
        "eyebrow": "Soup technique",
        "title": "Compare four ways to build a satisfying soup",
        "copy": "Move between a creamy potato-thickened chowder, flour-finished harira, long-caramelized onion broth, and smoothly blended red lentils by matching the thickening method to the result you want.",
    },
    "moroccan-style-vegetarian-harira-lentils-chickpeas": {
        "slugs": ["classic-new-england-clam-chowder-potatoes-saltines", "classic-french-onion-soup-gruyere-toasts", "turkish-red-lentil-soup-aleppo-butter"],
        "eyebrow": "Soup technique",
        "title": "Compare four ways to build a satisfying soup",
        "copy": "Move between a creamy potato-thickened chowder, flour-finished harira, long-caramelized onion broth, and smoothly blended red lentils by matching the thickening method to the result you want.",
    },
    "classic-french-onion-soup-gruyere-toasts": {
        "slugs": ["classic-new-england-clam-chowder-potatoes-saltines", "moroccan-style-vegetarian-harira-lentils-chickpeas", "turkish-red-lentil-soup-aleppo-butter"],
        "eyebrow": "Soup technique",
        "title": "Compare four ways to build a satisfying soup",
        "copy": "Move between a creamy potato-thickened chowder, flour-finished harira, long-caramelized onion broth, and smoothly blended red lentils by matching the thickening method to the result you want.",
    },
    "turkish-red-lentil-soup-aleppo-butter": {
        "slugs": ["classic-new-england-clam-chowder-potatoes-saltines", "moroccan-style-vegetarian-harira-lentils-chickpeas", "classic-french-onion-soup-gruyere-toasts"],
        "eyebrow": "Soup technique",
        "title": "Compare four ways to build a satisfying soup",
        "copy": "Move between a creamy potato-thickened chowder, flour-finished harira, long-caramelized onion broth, and smoothly blended red lentils by matching the thickening method to the result you want.",
    },
    "cottage-cheese-protein-pancakes": {
        "slugs": ["turkish-cilbir-poached-eggs-garlicky-yogurt-aleppo-butter", "eastern-european-syrniki-sour-cream-fruit", "cottage-cheese-frittata-tomatoes-green-peppers", "freezer-breakfast-burritos", "berry-almond-chia-pudding-toasted-seeds"],
        "eyebrow": "Breakfast planning",
        "title": "Build a fast and make-ahead breakfast rotation",
        "copy": "Compare fresh-poached çılbır, hot protein pancakes, farmer-cheese syrniki, a vegetable-packed frittata, freezer-ready burritos and no-cook chia cups by total time, cost, storage and morning effort.",
    },
    "cottage-cheese-frittata-tomatoes-green-peppers": {
        "slugs": ["persian-style-kuku-sabzi-walnuts-barberries", "turkish-cilbir-poached-eggs-garlicky-yogurt-aleppo-butter", "cottage-cheese-protein-pancakes", "eastern-european-syrniki-sour-cream-fruit", "freezer-breakfast-burritos", "berry-almond-chia-pudding-toasted-seeds"],
        "eyebrow": "Breakfast planning",
        "title": "Build a fast and make-ahead breakfast rotation",
        "copy": "Compare fresh-poached çılbır, hot protein pancakes, farmer-cheese syrniki, a vegetable-packed frittata, freezer-ready burritos and no-cook chia cups by total time, cost, storage and morning effort.",
    },
    "freezer-breakfast-burritos": {
        "slugs": ["turkish-cilbir-poached-eggs-garlicky-yogurt-aleppo-butter", "cottage-cheese-protein-pancakes", "eastern-european-syrniki-sour-cream-fruit", "cottage-cheese-frittata-tomatoes-green-peppers", "berry-almond-chia-pudding-toasted-seeds"],
        "eyebrow": "Breakfast planning",
        "title": "Build a fast and make-ahead breakfast rotation",
        "copy": "Compare fresh-poached çılbır, hot protein pancakes, farmer-cheese syrniki, a vegetable-packed frittata, freezer-ready burritos and no-cook chia cups by total time, cost, storage and morning effort.",
    },
    "berry-almond-chia-pudding-toasted-seeds": {
        "slugs": ["turkish-cilbir-poached-eggs-garlicky-yogurt-aleppo-butter", "cottage-cheese-protein-pancakes", "eastern-european-syrniki-sour-cream-fruit", "cottage-cheese-frittata-tomatoes-green-peppers", "freezer-breakfast-burritos"],
        "eyebrow": "Breakfast planning",
        "title": "Build a fast and make-ahead breakfast rotation",
        "copy": "Compare fresh-poached çılbır, hot protein pancakes, farmer-cheese syrniki, a vegetable-packed frittata, freezer-ready burritos and no-cook chia cups by total time, cost, storage and morning effort.",
    },
    "eastern-european-syrniki-sour-cream-fruit": {
        "slugs": ["turkish-cilbir-poached-eggs-garlicky-yogurt-aleppo-butter", "cottage-cheese-protein-pancakes", "cottage-cheese-frittata-tomatoes-green-peppers", "freezer-breakfast-burritos", "berry-almond-chia-pudding-toasted-seeds"],
        "eyebrow": "Breakfast planning",
        "title": "Build a fast and make-ahead breakfast rotation",
        "copy": "Compare fresh-poached çılbır, hot protein pancakes, farmer-cheese syrniki, a vegetable-packed frittata, freezer-ready burritos and no-cook chia cups by total time, cost, storage and morning effort.",
    },
}

def recipe_topic_cluster(recipe) -> str:
    cluster = CURATED_RECIPE_CLUSTERS.get(recipe.get("slug", ""))
    if not cluster:
        return ""
    recipes_by_slug = {candidate["slug"]: candidate for candidate in RECIPES}
    linked = [recipes_by_slug[slug] for slug in cluster["slugs"] if slug in recipes_by_slug]
    if not linked:
        return ""
    return f'''<section class="section-tight section-paper related-section" aria-labelledby="recipe-cluster-heading"><div class="wrap">
      <div class="section-heading"><div><p class="eyebrow">{esc(cluster["eyebrow"])}</p><h2 id="recipe-cluster-heading">{esc(cluster["title"])}</h2></div><p>{esc(cluster["copy"])}</p></div>
      <div class="recipe-grid">{''.join(recipe_card(candidate) for candidate in linked)}</div>
    </div></section>'''

def build_recipe_pages():
    for recipe in RECIPES:
        slug = recipe["slug"]
        minutes = int(recipe.get("total_minutes", int(recipe.get("prep_minutes",0)) + int(recipe.get("cook_minutes",0))))
        ingredients = "".join(f'''<li><label><input type="checkbox"><span data-ingredient data-original="{esc(item)}">{esc(item)}</span></label></li>''' for item in recipe.get("ingredients",[]))
        steps = "".join(f'''<li><div><h3>{esc(step.get("name", f"Step {i+1}"))}</h3><p>{esc(step.get("text",""))}</p></div></li>''' for i, step in enumerate(recipe.get("instructions",[])))
        tips = "".join(f'<div class="tip-card"><strong>Why it works</strong>{esc(t)}</div>' for t in recipe.get("why_it_works",[]))
        swaps = "".join(f"<li>{esc(x)}</li>" for x in recipe.get("swaps",[]))
        notes = "".join(f"<li>{esc(x)}</li>" for x in recipe.get("notes",[]))
        faqs = "".join(f'''<details><summary>{esc(x.get("q","Question"))}</summary><p>{esc(x.get("a",""))}</p></details>''' for x in recipe.get("faqs",[]))
        cook_steps = "".join(f'''<div class="cook-step"><strong>{i+1}. {esc(step.get("name", "Step"))}</strong>{esc(step.get("text",""))}</div>''' for i, step in enumerate(recipe.get("instructions",[])))
        collection_slug = recipe.get("collection", "")
        collection_title = COLLECTION_META.get(collection_slug, (pretty_slug(collection_slug or "recipe"), "", ""))[0]
        topic_links = []
        if collection_slug:
            topic_links.append(f'<a href="{href("/collections/" + collection_slug + "/")}">{esc(collection_title)}</a>')
        for hub_slug in ingredient_hubs_for_recipe(recipe)[:2]:
            topic_links.append(f'<a href="{href("/ingredients/" + hub_slug + "/")}">{esc(INGREDIENT_HUBS[hub_slug]["title"])}</a>')
        related = related_recipes(recipe)
        photo_credit = ""
        if recipe.get("image_credit") and recipe.get("image_credit_url") and recipe.get("image_license") and recipe.get("image_license_url"):
            photo_credit = f'''<p class="recipe-photo-credit" style="margin:.55rem .15rem 0;font-size:.75rem;color:var(--ink-soft)">Photo: <a href="{esc(recipe['image_credit_url'])}" target="_blank" rel="noopener noreferrer">{esc(recipe['image_credit'])}</a> · <a href="{esc(recipe['image_license_url'])}" target="_blank" rel="noopener noreferrer">{esc(recipe['image_license'])}</a></p>'''
        related_html = f'''<section class="section-tight section-paper related-section"><div class="wrap">
          <div class="section-heading"><div><p class="eyebrow">Cook next</p><h2>More recipes you’ll like</h2></div><a class="btn btn-outline" href="{href('/recipes/')}">All recipes</a></div>
          <div class="recipe-grid">{''.join(recipe_card(candidate) for candidate in related)}</div>
        </div></section>'''
        cluster_html = recipe_topic_cluster(recipe)
        body = f'''<section class="recipe-hero" data-recipe-page data-servings="{int(recipe.get('servings',4))}">
          <div class="wrap">{breadcrumbs([("Recipes","/recipes/"),(recipe.get("title","Recipe"),None)])}
          <div class="recipe-hero-grid">
            <div><img class="recipe-hero-image" src="{esc(recipe.get('image',''))}" alt="{esc(recipe.get('image_alt', recipe.get('title','Recipe')))}" width="900" height="968" fetchpriority="high" decoding="async">{photo_credit}</div>
            <div><p class="eyebrow">{esc(collection_title)}</p>
              <h1>{esc(recipe.get('title','Recipe'))}</h1><p class="lede">{esc(recipe.get('dek',''))}</p>
              <p class="recipe-byline">Developed for DishGal · Updated {esc(recipe.get('date_modified','2026-08-17'))}</p>
              <div class="recipe-topic-links" aria-label="Recipe topics">{''.join(topic_links)}</div>
              <div class="recipe-meta-grid">
                <div class="recipe-meta-item"><small>Prep</small><strong>{int(recipe.get('prep_minutes',0))} min</strong></div>
                <div class="recipe-meta-item"><small>Cook</small><strong>{int(recipe.get('cook_minutes',0))} min</strong></div>
                <div class="recipe-meta-item"><small>Total</small><strong>{minutes} min</strong></div>
                <div class="recipe-meta-item"><small>Cost</small><strong>{esc(recipe.get('cost_per_serving','—'))}</strong></div>
              </div>
              <div class="button-row">
                <button class="btn btn-primary" type="button" data-open-cook>Start cook mode</button>
                <button class="btn btn-outline" type="button" data-print>Print</button>
                <button class="btn btn-outline" type="button" data-save-recipe="{esc(slug)}"><span data-save-label>Save recipe</span></button>
              </div>
            </div>
          </div></div>
        </section>
        <section class="section-tight"><div class="wrap recipe-main">
          <aside>
            <div class="recipe-panel sticky-panel"><div class="serving-control"><strong>Ingredients</strong><div class="serving-buttons"><button type="button" data-serving-minus>−</button><span><span data-servings-output>{int(recipe.get('servings',4))}</span> servings</span><button type="button" data-serving-plus>+</button></div></div><ul class="ingredient-list">{ingredients}</ul></div>
          </aside>
          <div>
            <div class="recipe-panel"><h2>Directions</h2><ol class="step-list">{steps}</ol></div>
            <div class="recipe-panel"><h2>Why this works</h2><div class="tip-grid">{tips}</div></div>
            {recipe_shop(recipe)}
            <div class="recipe-panel"><h2>Swaps & notes</h2><h3>Easy swaps</h3><ul class="dot-list">{swaps}</ul><h3>Cook notes</h3><ul class="dot-list">{notes}</ul><h3>Storage</h3><p>{esc(recipe.get('storage','Store covered in the refrigerator and reheat until hot.'))}</p></div>
            <div class="recipe-panel"><h2>Questions</h2><div class="faq-list">{faqs}</div></div>
          </div>
        </div></section>
        {cluster_html}
        {related_html}
        <div class="cook-mode" data-cook-mode><div class="cook-mode-inner"><div class="cook-mode-head"><div><strong>{esc(recipe.get('title','Recipe'))}</strong><div class="muted">Screen stays awake when supported.</div></div><button class="btn btn-dark" type="button" data-close-cook>Exit cook mode</button></div>{cook_steps}</div></div>'''
        schema = [
            recipe_schema(recipe),
            breadcrumb_schema([("Recipes", "/recipes/"), (recipe.get("title", "Recipe"), None)]),
        ]
        write_page(f"/recipes/{slug}/", page(
            recipe_seo_title(recipe),
            recipe_meta_description(recipe),
            f"/recipes/{slug}/",
            body,
            schema=schema,
            image=recipe.get("image"),
            page_type="article",
            published=recipe.get("date_published"),
            modified=recipe.get("date_modified", recipe.get("date_published")),
        ))

def build_collections():
    collections = sorted({r.get("collection","") for r in RECIPES if r.get("collection")})
    for slug in collections:
        recipes = stable_recipe_mix([r for r in RECIPES if r.get("collection") == slug])
        title, desc, _ = COLLECTION_META.get(slug, (pretty_slug(slug), f"Browse DishGal's {pretty_slug(slug).lower()} recipes.", "🍴"))
        seo_title = title if "recipe" in title.lower() else f"{title} Recipes"
        full_description = f"{desc} Browse {len(recipes)} complete recipes with timing, cost, substitutions, and storage notes."
        collection_intro = ""
        collection_faq = ""
        if slug in dict(active_ingredient_hubs()):
            hub_count = len(recipes_for_ingredient(slug))
            collection_intro = f'''<section class="section-tight section-paper"><div class="wrap"><p>This collection is a smaller selection. <a href="{href('/ingredients/' + slug + '/')}">Browse all {hub_count} {esc(slug)} recipes</a> for the complete ingredient library.</p></div></section>'''
        if slug == "instant-pot":
            collection_intro = f'''<section class="section-tight section-paper"><div class="wrap">
              <div class="section-heading"><div><p class="eyebrow">Built for the 6-quart pot</p><h2>Pressure-cooker recipes that tell the whole truth about time.</h2></div><p>Every total includes a realistic allowance for coming to pressure and releasing pressure—not just the programmed cook time on the display.</p></div>
              <div class="tip-grid">
                <div class="tip-card"><strong>Protect against the burn warning</strong>Thin liquid goes in first. Tomato sauce, salsa, and other thick ingredients stay on top unless the directions specifically say to stir.</div>
                <div class="tip-card"><strong>Keep family dinner mild</strong>The base recipes are kid-manageable. Hot sauce, jalapeños, and crushed pepper are finishing options for the adults who want them.</div>
                <div class="tip-card"><strong>Use the right release</strong>Each recipe states natural, quick, or controlled release. Never force the lid; wait until the float valve drops completely.</div>
              </div>
              <div class="recipe-panel" style="margin-top:1.5rem">
                <p class="eyebrow">DishGal quick reference</p><h3>Match the pressure release to the food—not the clock.</h3>
                <div class="tip-grid">
                  <div class="tip-card"><strong>Natural release</strong>Best for beans, split peas, large roasts and other foods that foam or keep cooking as pressure falls. Wait the recipe's full time; do not force the lid.</div>
                  <div class="tip-card"><strong>Controlled release</strong>Use short venting pulses for rice, pasta and starchy dishes. Pause immediately if liquid or foam sputters, and resume only when the vent is quiet.</div>
                  <div class="tip-card"><strong>Quick release</strong>Useful for delicate vegetables and seafood when the recipe calls for it. Keep hands and face away from steam and never cover the valve with a towel.</div>
                  <div class="tip-card"><strong>Fill-limit check</strong>Stay below the half-full line for beans, grains, pasta and foods that expand or foam. Other foods must remain below the model's maximum-fill line.</div>
                </div>
                <h3 style="margin-top:1.5rem">Busy-night pressure-cooker chooser</h3>
                <p>Compare total time, release style and the work left after pressure falls. The programmed cycle is only one part of the clock.</p>
                <div style="overflow-x:auto">
                  <table style="width:100%;border-collapse:collapse;text-align:left">
                    <thead><tr><th style="padding:.65rem;border-bottom:2px solid var(--line)">Recipe</th><th style="padding:.65rem;border-bottom:2px solid var(--line)">Total</th><th style="padding:.65rem;border-bottom:2px solid var(--line)">Release</th><th style="padding:.65rem;border-bottom:2px solid var(--line)">After pressure</th><th style="padding:.65rem;border-bottom:2px solid var(--line)">Best fit</th></tr></thead>
                    <tbody>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-filipino-chicken-arroz-caldo-ginger-calamansi/')}">Chicken arroz caldo</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Shred chicken; loosen porridge</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Gentle breakfast or supper</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-polish-bigos-pork-kielbasa-sauerkraut/')}">Polish-style bigos</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">100 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Reduce; reheat kielbasa</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Make-ahead freezer braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-cuban-ropa-vieja-yellow-rice-plantains/')}">Cuban-style ropa vieja</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">100 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Shred and reduce; finish sides</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Complete family platter</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-ukrainian-beet-borscht-white-beans-dill/')}">Beet borscht with white beans</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">55 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Simmer cabbage and beans</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Budget meatless meal prep</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-lowcountry-shrimp-boil-corn-potatoes/')}">Lowcountry shrimp boil</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">40 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Controlled quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Sauté shrimp 3–5 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Fast shareable seafood</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-korean-galbijjim-pear-chestnuts/')}">Korean galbijjim</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">100 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Defat and reduce 8–10 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Special family braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-smoky-black-bean-soup-lime-crema/')}">Smoky black bean soup</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">90 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Partially blend</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Vegetarian meal prep</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-chicken-cacciatore-mushrooms-egg-noodles/')}">Chicken cacciatore</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Reduce sauce; add noodles</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Saucy family dinner</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-louisiana-red-beans-rice-andouille/')}">Louisiana-style red beans</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">95 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mash; reheat andouille; add rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Smoky budget family meal</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-persian-chicken-fesenjan-walnut-pomegranate/')}">Chicken fesenjan</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">75 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Reduce walnut-pomegranate sauce</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Sweet-tart family braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-quebec-yellow-split-pea-soup-ham/')}">Yellow split pea soup</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Shred ham; adjust body</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Budget freezer meal</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-saffron-shrimp-risotto-lemon-chives/')}">Saffron shrimp risotto</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">40 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Controlled quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Sauté shrimp; enrich rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Fast seafood dinner</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-japanese-beef-curry-potatoes-carrots/')}">Japanese-style beef curry</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">80 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">5-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Whisk in curry roux; add rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mild family comfort food</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-rajma-masala-warm-roti/')}">Rajma masala</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mash and reduce; warm roti</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Budget vegetarian busy night</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-teriyaki-chicken-rice-bowls/')}">Teriyaki chicken rice bowls</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">40 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Glaze chicken; fluff rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">All-in-one rice bowl</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-taiwanese-lu-rou-fan-braised-pork-rice/')}">Taiwanese-style lu rou fan</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">80 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Reduce gravy; add rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Savory pork rice bowls</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-swedish-meatballs-mashed-potatoes-lingonberries/')}">Swedish-style meatballs</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">85 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">5-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Thicken gravy; finish mash</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Classic family comfort food</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-dal-makhani-garlic-naan/')}">Dal makhani with garlic naan</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">95 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Finish tomato-cream sauce; warm naan</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Meatless bean supper</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-hawaiian-style-kalua-pork-cabbage-rice/')}">Hawaiian-style kālua pork</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">110 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Shred pork; sauté cabbage; add rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Smoky family platter</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-thai-style-massaman-chicken-potatoes/')}">Thai-style Massaman chicken</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Add coconut milk; simmer sauce</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mild chicken curry night</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-lebanese-style-mujaddara-caramelized-onions/')}">Lebanese-style mujaddara</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">90 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Two 10-min natural releases</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Fold in onions; rest grains</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Budget meatless pantry meal</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-vietnamese-style-bo-kho-carrots-noodles/')}">Vietnamese-style bò kho</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">95 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled; second controlled quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Cook noodles; garnish bowls</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Aromatic beef noodle supper</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-egyptian-style-ful-medames-breakfast-platter/')}">Egyptian-style ful medames</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">100 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mash; season; build platter</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Vegan breakfast meal prep</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-dominican-style-sancocho-chicken-pork-root-vegetables/')}">Dominican-style sancocho</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">115 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Two 10-min natural releases, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Check meats; mash vegetables</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Weekend family stew</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-italian-creamy-polenta-mushrooms-parmesan/')}">Creamy polenta with mushrooms</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">55 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Whisk polenta; add mushrooms</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Meatless pot-in-pot supper</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-hainanese-style-chicken-rice-ginger-scallion-sauce/')}">Hainanese-style chicken rice</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">55 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Verify chicken; crisp skin; mix sauces</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">All-in-one mild family bowl</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-greek-beef-stifado-pearl-onions/')}">Greek beef stifado</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">110 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Simmer onions; balance sauce</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Make-ahead beef braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-jamaican-style-oxtail-butter-beans/')}">Jamaican-style oxtail</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">120 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Defat; add beans; reduce</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Special make-ahead beef braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-ghanaian-style-chicken-peanut-stew-sweet-potatoes/')}">Ghanaian-style chicken peanut stew</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Whisk in peanut butter; wilt spinach</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Weeknight chicken one-bowl stew</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-brazilian-style-feijoada-collards-farofa/')}">Brazilian-style feijoada</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">125 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Add sausage; mash beans; cook collards</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Complete pork-and-bean platter</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-uzbek-style-lamb-plov-carrots/')}">Uzbek-style lamb plov</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">100 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Two 10-min natural releases, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Fold in garlic; fluff and rest rice</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Celebration-style one-pot rice</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-southern-chicken-flat-dumplings/')}">Southern chicken &amp; flat dumplings</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">70 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Shred chicken; simmer dumplings; add dairy</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Comfort-food family supper</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-ecuadorian-locro-de-queso-avocado/')}">Ecuadorian-style locro de queso</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">50 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Controlled quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mash potatoes; add dairy and garnishes</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Meatless potato-soup night</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-mexican-beef-birria-tacos-consomme/')}">Mexican-style beef birria tacos</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">115 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Shred beef; skim broth; crisp tacos</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Freezer-friendly taco night</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-indian-vegetable-biryani-pomegranate-raita/')}">Indian-style vegetable biryani</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">70 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Steam peas; fluff rice; mix raita</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Meatless celebration-style rice</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-french-style-coq-au-vin-mushrooms/')}">French-style coq au vin</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">80 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Verify chicken; finish vegetables and sauce</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Make-ahead chicken braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-vegan-corn-potato-chowder-chives/')}">Vegan corn &amp; potato chowder</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">50 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">5-min rest, then controlled quick</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Partially blend; add oat milk</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Budget vegan freezer meal</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-korean-dakbokkeumtang-chicken-potatoes/')}">Korean-style dakbokkeumtang</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">70 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Verify chicken; finish glass noodles</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mild-first chicken stew</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-romanian-sarmale-beef-pork-rice/')}">Romanian-style sarmale</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">110 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Verify roll centers; finish polenta</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Make-ahead stuffed-cabbage platter</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-turkish-kuru-fasulye-white-bean-stew/')}">Turkish kuru fasulye</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">95 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Check bean centers; adjust broth</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Budget meatless pantry stew</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-norwegian-farikal-lamb-cabbage-potatoes/')}">Norwegian fårikål</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">90 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">15-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Check lamb tenderness; finish broth</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Autumn lamb-and-cabbage braise</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-ethiopian-doro-wat-eggs-injera/')}">Ethiopian-style doro wat</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">65 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Verify chicken; reduce sauce; warm eggs</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Chicken-and-injera family platter</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/instant-pot-portuguese-caldo-verde-chourico-kale/')}">Portuguese-style caldo verde</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">50 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">10-min natural, then controlled</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Mash potatoes; wilt kale; reheat sausage</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Fast soup-and-bread night</td></tr>
                      <tr><td style="padding:.65rem"><a href="{href('/recipes/instant-pot-pork-carnitas/')}">Pork carnitas</a></td><td style="padding:.65rem">75 min</td><td style="padding:.65rem">15-min natural, then quick</td><td style="padding:.65rem">Shred and broil</td><td style="padding:.65rem">Cook once, repurpose twice</td></tr>
                    </tbody>
                  </table>
                </div>
                <h3 style="margin-top:1.5rem">What belongs near the heating plate?</h3>
                <div class="table-wrap">
                  <table>
                    <thead><tr><th>Ingredient type</th><th>Where it goes</th><th>Why</th></tr></thead>
                    <tbody>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">Water, broth or another recipe-approved thin liquid</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">First, against a clean deglazed base</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">This is the free-flowing liquid the cooker needs to generate steam.</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">Meat and water-rich vegetables</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Above the thin liquid; stir only when the recipe directs</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">They release moisture, but should not replace the measured minimum liquid for the model.</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">Tomato paste, thick tomato sauce, nut butter or another concentrated sauce</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Diluted and floated on top, or added after pressure, exactly as directed</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Thick or sugary mixtures can settle and scorch before enough steam develops.</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">Beans, rice, pasta and other expanding foods</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">In the recipe's measured liquid and below the half-full line</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">They absorb liquid, expand and can foam; improvised ratios change both texture and safety margins.</td></tr>
                      <tr><td style="padding:.65rem">Dairy, cheese and cornstarch slurry</td><td style="padding:.65rem">Usually after pressure unless a tested recipe specifically says otherwise</td><td style="padding:.65rem">Adding them during the finishing stage reduces scorching, curdling and over-thickening.</td></tr>
                    </tbody>
                  </table>
                </div>
                <h3 style="margin-top:1.5rem">Five-point preflight before you press Start</h3>
                <ol class="dot-list">
                  <li>Confirm the sealing ring is seated, the float valve and steam-release path move freely, and the anti-block shield is clean.</li>
                  <li>Check that the outside of the inner pot and the cooker heating plate are clean and dry before inserting the pot.</li>
                  <li>Scrape the base completely smooth after browning; thick sauce, dairy and starch belong where the recipe layers them.</li>
                  <li>Measure the stated thin liquid and stay below the half-full line for grains, beans, pasta and other expanding foods.</li>
                  <li>Match the valve position and release method to the exact recipe, keeping hands and face away from escaping steam.</li>
                </ol>
                <h3 style="margin-top:1.5rem">Stop-and-check signals during release</h3>
                <ul class="dot-list">
                  <li><strong>Liquid sputters from the valve:</strong> close it, wait 2 minutes and resume in shorter controlled pulses; never cover the vent with a towel.</li>
                  <li><strong>The float valve is still raised:</strong> pressure remains inside. Keep the lid locked and wait—never twist or force it open.</li>
                  <li><strong>The recipe contains beans, grains or other foaming food:</strong> respect the half-full limit and the specified natural-release interval before any venting.</li>
                </ul>
                <h3 style="margin-top:1.5rem">Pressure-release recovery guide</h3>
                <div class="table-wrap">
                  <table>
                    <thead><tr><th>What you observe</th><th>Safe next move</th><th>What not to do</th></tr></thead>
                    <tbody>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">Only clear steam exits during a controlled release</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Continue the recipe's short pulses while keeping hands and face away</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Do not lean over the valve or touch it with bare hands</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">Foam, starch or food sputters from the valve</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Close the valve, wait at least 2 minutes, then retry more slowly; repeat as needed</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Do not hold the valve open or cover it with a towel</td></tr>
                      <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)">The float valve stays raised after the stated natural release</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Treat the cooker as pressurized and follow the recipe's controlled-release direction</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Never twist, pry or force the lid</td></tr>
                      <tr><td style="padding:.65rem">The cooker displays a burn warning before pressure</td><td style="padding:.65rem">Cancel, let pressure dissipate, then follow the model manual before opening and inspecting the base, liquid and layering</td><td style="padding:.65rem">Do not bypass the warning, add liquid through the vent or move a pressurized cooker</td></tr>
                    </tbody>
                  </table>
                </div>
                <h3 style="margin-top:1.5rem">Where to measure doneness after pressure</h3>
                <div class="tip-grid">
                  <div class="tip-card"><strong>Bone-in poultry: 165°F</strong>Probe the thickest meat beside—but not touching—the bone. Check more than one piece because sizes and positions in the pot vary.</div>
                  <div class="tip-card"><strong>Ground-meat rolls: 160°F</strong>Insert the probe through the wrapper into the very center of several rolls. Hot broth or tender cabbage does not prove the filling is done.</div>
                  <div class="tip-card"><strong>Whole pork or beef: 145°F + rest</strong>Use the recipe's stated rest and target; do not substitute this rule for ground meat, poultry or a recipe that intentionally cooks a tough cut further for tenderness.</div>
                  <div class="tip-card"><strong>Below target?</strong>Return the food to hot liquid and use Sauté or the recipe's finishing step until every checked portion reaches its safe temperature; never rely on color alone.</div>
                </div>
                <p class="muted" style="margin-top:1rem">Safety method: confirm the minimum liquid, fill limits, pre-use inspection, warning response and venting procedure in the <a href="https://instantpot.com/pages/product-manuals" target="_blank" rel="noopener noreferrer">manufacturer manual for your model</a>. DishGal's doneness targets follow the <a href="https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/safe-temperature-chart" target="_blank" rel="noopener noreferrer">USDA safe-temperature chart</a>. Comparison, layering and pressure-release recovery guides reviewed October 12, 2026.</p>
              </div>
              <p class="muted" style="margin-top:1rem">Instant Pot is a trademark of its owner. DishGal is not affiliated with or endorsed by the brand; these recipes also work in comparable 6-quart electric pressure cookers when the manufacturer permits the stated method.</p>
            </div></section>'''
            collection_faq = f'''<section class="section-tight"><div class="narrow recipe-panel"><p class="eyebrow">Before you start</p><h2>Three rules for safer, better pressure cooking</h2><div class="faq-list">
              <details><summary>Can I double these recipes?</summary><p>Do not automatically double the liquid or exceed your cooker's maximum-fill line. Beans, grains, pasta, and other expanding foods should remain below the half-full line. Keep the programmed cook time the same only when piece size stays the same, and allow more time for the fuller pot to reach pressure.</p></details>
              <details><summary>Why does the total time exceed the pressure-cook time?</summary><p>The display countdown begins only after the cooker reaches pressure. A full family meal commonly needs 10 to 20 minutes to pressurize, plus the stated release time, so DishGal includes those stages in the total.</p></details>
              <details><summary>Which Instant Pot size are these written for?</summary><p>These recipes are developed around a 6-quart electric pressure cooker. An 8-quart model may need additional thin liquid according to its manual. Always follow the minimum-liquid, fill-limit, and release instructions for your exact model.</p></details>
            </div></div></section>'''
        elif slug == "breakfast":
            collection_intro = f'''<section class="section-tight section-paper"><div class="wrap">
              <div class="section-heading"><div><p class="eyebrow">DishGal morning chooser</p><h2>Match breakfast to the time, cost and texture you want.</h2></div><p>These are complete recipes, not serving suggestions. Compare hands-on method, realistic total time, estimated cost and what can be made ahead.</p></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Breakfast</th><th>Total time</th><th>Est. cost</th><th>Main method</th><th>Make-ahead fit</th></tr></thead>
                  <tbody>
                    <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/turkish-cilbir-poached-eggs-garlicky-yogurt-aleppo-butter/')}">Turkish çılbır</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">$2.25/serving</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Quiet poach + warm spiced butter</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Prep yogurt and butter; poach eggs fresh</td></tr>
                    <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/cottage-cheese-protein-pancakes/')}">Cottage-cheese protein pancakes</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">20 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">$1.35/serving</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Blend + griddle</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Freeze cooked pancakes up to 2 months</td></tr>
                    <tr><td style="padding:.65rem;border-bottom:1px solid var(--line)"><a href="{href('/recipes/freezer-breakfast-burritos/')}">Freezer breakfast burritos</a></td><td style="padding:.65rem;border-bottom:1px solid var(--line)">40 min</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">$1.90/serving</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Skillet + batch assembly</td><td style="padding:.65rem;border-bottom:1px solid var(--line)">Purpose-built for freezing</td></tr>
                    <tr><td style="padding:.65rem"><a href="{href('/recipes/apple-cinnamon-baked-oatmeal/')}">Apple-cinnamon baked oatmeal</a></td><td style="padding:.65rem">50 min</td><td style="padding:.65rem">$1.05/serving</td><td style="padding:.65rem">Mix + bake</td><td style="padding:.65rem">Refrigerate slices 4 days or freeze</td></tr>
                  </tbody>
                </table>
              </div>
              <p class="muted" style="margin-top:1rem">Cost estimates reflect the ingredient quantities used when each recipe was published and vary by store and season. Food-safety timing and temperature guidance appears on each recipe page. Comparison reviewed October 22, 2026.</p>
            </div></section>'''
        body = f'''<section class="page-hero"><div class="wrap">{breadcrumbs([("Recipes","/recipes/"),(title,None)])}<p class="eyebrow">Dinner collection</p><h1>{esc(seo_title)}</h1><p class="lede">{esc(full_description)}</p></div></section>
        {collection_intro}
        <section class="section-tight"><div class="wrap"><div class="recipe-grid">{''.join(recipe_card(r) for r in recipes)}</div></div></section>
        {collection_faq}'''
        path = f"/collections/{slug}/"
        schema = [
            collection_schema(seo_title, full_description, path, recipes),
            breadcrumb_schema([("Recipes", "/recipes/"), (title, None)]),
        ]
        write_page(path, page(seo_title, truncate_description(full_description), path, body, schema=schema))

def build_ingredient_hubs():
    for slug, meta in INGREDIENT_HUBS.items():
        recipes = recipes_for_ingredient(slug)
        if len(recipes) < 3:
            continue
        title = meta["title"]
        description = f'{meta["description"]} Browse {len(recipes)} complete DishGal recipes with realistic timing, substitutions, and storage notes.'
        path = f"/ingredients/{slug}/"
        collection_link = ""
        if any(recipe.get("collection") == slug for recipe in RECIPES):
            collection_link = f'<p class="muted">Looking for the smaller original selection? <a href="{href("/collections/" + slug + "/")}">View the {esc(slug)} collection</a>.</p>'
        body = f'''<section class="page-hero"><div class="wrap">{breadcrumbs([("Recipes", "/recipes/"), (title, None)])}<p class="eyebrow">Recipes by ingredient</p><h1>{esc(title)}</h1><p class="lede">{esc(description)}</p></div></section>
        <section class="section-tight"><div class="wrap">{collection_link}<div class="recipe-grid">{''.join(recipe_card(recipe) for recipe in recipes)}</div></div></section>'''
        schema = [
            collection_schema(title, description, path, recipes),
            breadcrumb_schema([("Recipes", "/recipes/"), (title, None)]),
        ]
        write_page(path, page(title, truncate_description(description), path, body, schema=schema))

def build_saved():
    body = f'''<section class="page-hero"><div class="wrap"><p class="eyebrow">Your shortlist</p><h1>Saved recipes</h1><p class="lede">Recipes you heart are stored in this browser on this device. No account required.</p></div></section>
    <section class="section-tight"><div class="wrap"><div class="recipe-grid" data-saved-grid></div></div></section>'''
    write_page("/saved/", page("Saved Recipes", "Keep a browser-based shortlist of DishGal recipes without creating an account or sharing personal information.", "/saved/", body, noindex=True, needs_recipe_data=True))

def build_decider():
    collections = sorted({r.get("collection","") for r in RECIPES if r.get("collection")})
    coll_chips = "".join(f'<button class="option-chip" type="button" data-choice="collection" data-value="{esc(c)}">{esc(COLLECTION_META.get(c,(pretty_slug(c),"",""))[0])}</button>' for c in collections)
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">Decision tool</p><h1>Tell us the night. Get one dinner.</h1><p class="lede">Pick what matters. DishGal chooses a recipe. You can reroll if the first answer gets vetoed.</p></div></section>
    <section class="tool-page"><div class="narrow"><div class="tool-shell" data-decider>
      <div class="option-group"><h3>How much time?</h3><div class="option-chips"><button class="option-chip" type="button" data-choice="time" data-value="25">25 minutes</button><button class="option-chip" type="button" data-choice="time" data-value="30">30 minutes</button><button class="option-chip" type="button" data-choice="time" data-value="45">45 minutes</button><button class="option-chip" type="button" data-choice="time" data-value="60">An hour</button></div></div>
      <div class="option-group"><h3>What kind of dinner?</h3><div class="option-chips">{coll_chips}</div></div>
      <div class="option-group"><h3>Any preference?</h3><div class="option-chips"><button class="option-chip" type="button" data-choice="tag" data-value="vegetarian">Vegetarian</button><button class="option-chip" type="button" data-choice="tag" data-value="family">Family-friendly</button><button class="option-chip" type="button" data-choice="tag" data-value="budget">Budget</button><button class="option-chip" type="button" data-choice="tag" data-value="high-protein">High protein</button></div></div>
      <button class="btn btn-primary" type="button" data-decide>Decide dinner</button>
      <div class="tool-results" data-decider-result></div>
    </div></div></section>'''
    write_page("/dinner-decider/", page("Dinner Decider", "Choose your available time and dinner preferences, then let DishGal pick one practical recipe for tonight.", "/dinner-decider/", body, needs_recipe_data=True))

def build_pantry():
    pantry_terms = ["chicken","beef","pork","eggs","pasta","rice","potatoes","beans","tomatoes","broccoli","spinach","cheese","tortillas","lemon","onion"]
    items = "".join(f'<label class="pantry-item"><input type="checkbox" value="{esc(x)}"> {esc(x.title())}</label>' for x in pantry_terms)
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">Use what you have</p><h1>Pantry Rescue</h1><p class="lede">Check a few ingredients. We rank DishGal recipes by overlap so you can start with what is already in the kitchen.</p></div></section>
    <section class="tool-page"><div class="wrap"><div class="tool-shell" data-pantry-tool>
      <div class="pantry-grid">{items}</div>
      <div class="field" style="margin-top:1rem"><label for="extras">Anything else?</label><input id="extras" name="extras" placeholder="mushrooms, feta, zucchini"></div>
      <div class="button-row" style="margin-top:1rem"><button class="btn btn-primary" type="button" data-match-pantry>Find matches</button></div>
      <div class="tool-results" data-pantry-results></div>
    </div></div></section>'''
    write_page("/pantry-rescue/", page("Pantry Rescue", "Select ingredients you already have and DishGal will rank recipes by ingredient overlap to help reduce waste and dinner indecision.", "/pantry-rescue/", body, needs_recipe_data=True))

def build_planner():
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">Five nights, handled</p><h1>Weeknight meal planner</h1><p class="lede">Build five varied dinners, then turn them into a checkable grocery list. Reroll until the week feels right.</p></div></section>
    <section class="tool-page"><div class="wrap"><div class="tool-shell" data-planner>
      <div class="filter-row" style="grid-template-columns:1fr 1fr auto">
        <div class="field"><label for="planner-time">Max weeknight time</label><select id="planner-time" name="planner-time"><option value="30">30 minutes</option><option value="45" selected>45 minutes</option><option value="60">60 minutes</option><option value="999">No limit</option></select></div>
        <label class="pantry-item" style="align-self:end;min-height:45px"><input type="checkbox" name="planner-vegetarian"> Vegetarian week</label>
        <button class="btn btn-primary" type="button" data-build-plan>Build my week</button>
      </div>
      <div class="planner-grid" data-plan-grid></div>
      <div class="button-row" style="margin-top:1.25rem"><button class="btn btn-outline" type="button" data-build-plan>Reroll week</button><button class="btn btn-dark" type="button" data-build-list>Make grocery list</button></div>
      <div data-shopping-wrap hidden style="margin-top:2rem"><h2>Grocery checklist</h2><ul class="shopping-list" data-shopping-list></ul></div>
    </div></div></section>'''
    write_page("/meal-planner/", page("5-Night Meal Planner", "Build a five-night DishGal dinner plan based on your available cooking time, then generate a practical grocery checklist.", "/meal-planner/", body, needs_recipe_data=True))

def build_guides():
    category_cards = []
    for slug, (name, desc, icon) in GUIDE_CATEGORY_META.items():
        count = sum(1 for article in ARTICLES if article.get("category", "").lower().replace(" ", "-") == slug)
        if count:
            category_cards.append(f'''<a class="collection-pill" href="{href('/guides/category/' + slug + '/')}"><span class="collection-icon">{icon}</span><strong>{esc(name)}</strong><small>{count} guides</small></a>''')
    affiliate_count = sum(1 for article in ARTICLES if article.get("affiliate"))
    body = f'''<section class="page-hero"><div class="wrap"><p class="eyebrow">DishGal Kitchen Picks</p><h1>Buy less. Choose better. Cook more.</h1><p class="lede">{len(ARTICLES)} practical guides—including {affiliate_count} product-focused picks—built around capacity, materials, cleanup, storage, and the jobs your kitchen actually needs done.</p></div></section>
    <section class="section-tight section-paper"><div class="wrap"><div class="collection-grid">{''.join(category_cards)}</div></div></section>
    <section class="section-tight"><div class="wrap"><div class="section-heading"><div><p class="eyebrow">The complete library</p><h2>Kitchen picks & planning guides</h2></div><p>No invented tests, star ratings, or universal winners—just clear criteria and tradeoffs.</p></div><div class="article-grid">{''.join(article_card(a) for a in ARTICLES)}</div></div></section>'''
    hub_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "DishGal Kitchen Picks",
        "description": "Practical kitchen gear and meal-planning guides based on function, capacity, materials, cleanup, and storage.",
        "url": canonical("/guides/"),
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(ARTICLES), "itemListElement": [
            {"@type": "ListItem", "position": index + 1, "url": canonical('/guides/' + article['slug'] + '/'), "name": article.get("title", "Guide")}
            for index, article in enumerate(ARTICLES)
        ]},
    }
    write_page("/guides/", page("Kitchen Picks & Buying Guides", "Practical DishGal kitchen buying guides covering cookware, appliances, prep tools, storage, and meal-planning systems.", "/guides/", body, schema=hub_schema))
    for article in ARTICLES:
        sections = "".join(f"<h2>{esc(sec[0])}</h2><p>{esc(sec[1])}</p>" for sec in article.get("sections",[]))
        disclosure = '<div class="disclosure-box"><strong>Paid links:</strong> As an Amazon Associate I earn from qualifying purchases. You pay no additional cost.</div>' if article.get("affiliate") else ""
        shop = ""
        if article.get("affiliate"):
            shop_items = article.get("shop_items", [])
            if not shop_items and article.get("shop_query"):
                shop_items = [[article["shop_query"], "Compare current options", "Use the guide criteria before choosing."]]
            if shop_items:
                cards = "".join(amazon_link(*item) for item in shop_items)
                shop = f'''<div class="shop-box"><h3>Compare the useful options</h3><p>Use the criteria above first. These links open current Amazon category results, so you can compare specifications, availability, and price.</p><div class="shop-grid">{cards}</div></div>'''
        related = [candidate for candidate in ARTICLES if candidate["slug"] != article["slug"] and candidate.get("category") == article.get("category")][:3]
        if len(related) < 3:
            related_slugs = {candidate["slug"] for candidate in related}
            related.extend(candidate for candidate in ARTICLES if candidate["slug"] != article["slug"] and candidate["slug"] not in related_slugs) 
            related = related[:3]
        related_html = f'''<section class="section section-paper"><div class="wrap"><div class="section-heading"><div><p class="eyebrow">Keep choosing well</p><h2>Related kitchen guides</h2></div><a class="btn btn-outline" href="{href('/guides/')}">All Kitchen Picks</a></div><div class="article-grid">{''.join(article_card(candidate) for candidate in related)}</div></div></section>'''
        body = f'''<section class="page-hero"><div class="narrow">{breadcrumbs([("Kitchen Picks","/guides/"),(article.get("title","Guide"),None)])}<p class="eyebrow">{esc(article.get("category","Guide"))}</p><h1>{esc(article.get("title","Guide"))}</h1><p class="lede">{esc(article.get("dek",""))}</p><p class="muted">{int(article.get("read_minutes",5))} minute read · Updated August 24, 2026</p></div></section>
        <div class="wrap"><img class="article-hero-image" src="{esc(article.get('image',''))}" alt="{esc(article.get('image_alt', article.get('title','Guide')))}" width="1080" height="675" fetchpriority="high" decoding="async"></div>
        <section class="section-tight"><article class="narrow prose">{disclosure}<p>{esc(article.get("dek",""))}</p>{sections}{shop}</article></section>
        {related_html}
        {newsletter_block()}'''
        article_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article.get("title", "Guide"),
            "description": article.get("dek", ""),
            "image": [article.get("image", "")],
            "datePublished": "2026-08-24",
            "dateModified": "2026-08-24",
            "author": {"@type": "Organization", "name": "DishGal"},
            "publisher": {"@type": "Organization", "name": "DishGal"},
            "mainEntityOfPage": canonical('/guides/' + article['slug'] + '/'),
        }
        path = f"/guides/{article['slug']}/"
        schema = [
            article_schema,
            breadcrumb_schema([("Kitchen Picks", "/guides/"), (article.get("title", "Guide"), None)]),
        ]
        write_page(path, page(
            article.get("title", "Guide"),
            article.get("dek", "Practical kitchen and meal-planning guidance from DishGal."),
            path,
            body,
            schema=schema,
            image=article.get("image"),
            page_type="article",
            published="2026-08-24",
            modified="2026-08-24",
        ))

def build_category_indexes():
    for slug, (name, desc, _) in GUIDE_CATEGORY_META.items():
        matches = [a for a in ARTICLES if a.get("category","").lower().replace(" ","-") == slug]
        path = f"/guides/category/{slug}/"
        body = f'''<section class="page-hero"><div class="wrap">{breadcrumbs([("Kitchen Picks", "/guides/"), (name, None)])}<p class="eyebrow">DishGal guides</p><h1>{esc(name)}</h1><p class="lede">{esc(desc)}</p></div></section>
        <section class="section-tight"><div class="wrap"><div class="article-grid">{''.join(article_card(a) for a in matches) if matches else '<div class="empty-state is-visible"><h3>More guides coming</h3><p>Browse all current guides while this section grows.</p></div>'}</div></div></section>'''
        schema = [
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": name,
                "description": desc,
                "url": canonical(path),
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(matches),
                    "itemListElement": [
                        {"@type": "ListItem", "position": index + 1, "url": canonical('/guides/' + article['slug'] + '/'), "name": article.get("title", "Guide")}
                        for index, article in enumerate(matches)
                    ],
                },
            },
            breadcrumb_schema([("Kitchen Picks", "/guides/"), (name, None)]),
        ]
        write_page(path, page(name, f"{desc} Browse DishGal's current {name.lower()} guides.", path, body, schema=schema))

def simple_page(path, title, eyebrow, lede, sections):
    content = "".join(f"<h2>{esc(h)}</h2><p>{esc(p)}</p>" for h,p in sections)
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1><p class="lede">{esc(lede)}</p></div></section><section class="section-tight"><article class="narrow prose"><p>{esc(lede)}</p>{content}</article></section>'''
    write_page(path, page(title, lede, path, body))

def build_utility_pages():
    simple_page("/about/","About DishGal","Why this exists","DishGal is built for the nightly question, not the food-influencer audition.",[
        ("Dinner first","Useful information comes before storytelling. Recipes show timing, cost, substitutions, storage, and common questions."),
        ("Tools, not pressure","The Dinner Decider, Pantry Rescue, saved recipes, and meal planner are designed to reduce decisions without requiring an account."),
        ("Editorial independence","Commercial relationships are disclosed. DishGal does not invent testing claims, ratings, or personal experience.")
    ])
    simple_page("/editorial-policy/","Editorial Policy","How DishGal publishes","Our standard is useful, specific, transparent cooking information that a reader can actually act on.",[
        ("Recipe standard","Recipes include full ingredient lists, numbered directions, timing, serving size, substitutions, storage guidance, and FAQs."),
        ("Corrections","Material errors are corrected when found. Dates may be updated when a page is substantially revised."),
        ("Commercial content","Affiliate relationships do not determine editorial conclusions. Buying guides explain criteria and tradeoffs.")
    ])
    simple_page("/affiliate-disclosure/","Affiliate Disclosure","Commercial transparency","As an Amazon Associate I earn from qualifying purchases. DishGal may earn commissions from qualifying purchases made through clearly labeled outbound product links.",[
        ("No extra cost","Affiliate commissions do not increase the price you pay."),
        ("No invented testing","A commercial link does not mean DishGal personally tested a product unless a page explicitly and truthfully says so."),
        ("Editorial separation","Product recommendations should be grounded in the criteria discussed on the page, not commission rate.")
    ])
    simple_page("/privacy/","Privacy Policy","Plain-language privacy","DishGal is designed to work with very little personal data and no account requirement.",[
        ("Saved recipes","Saved recipes are stored in your browser's local storage unless and until a future account feature is explicitly introduced."),
        ("Forms","If you submit an email or contact form, the information is used to respond or deliver the requested communication."),
        ("Analytics and advertising","The site may use privacy-conscious analytics and advertising technology. Those providers may process technical information under their own policies.")
    ])
    simple_page("/terms/","Terms of Use","Site terms","DishGal provides general cooking, meal-planning, and kitchen information for personal use.",[
        ("Food safety","Use appropriate food-safety practices and verify safe internal temperatures for meat, poultry, seafood, and leftovers."),
        ("No warranty","Recipes, timing, nutrition estimates, and cost estimates vary with ingredients, equipment, location, and technique."),
        ("Content use","DishGal content may not be republished wholesale without permission.")
    ])
    simple_page("/image-credits/","Image Credits","Visual sourcing","DishGal uses properly sourced editorial photography and original site design assets.",[
        ("Editorial images","Recipe and guide images are sourced from Unsplash, Pexels, Pixabay, and Wikimedia Commons under their applicable licenses."),
        ("Attribution","Photographers retain rights under the applicable source license and platform terms. Wikimedia recipe pages display the creator and license beside the photograph."),
        ("Future images","DishGal may replace launch imagery with original photography or licensed assets over time.")
    ])
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">Say hello</p><h1>Contact DishGal</h1><p class="lede">Corrections, recipe questions, partnerships, and useful feedback can all come through here.</p></div></section>
    <section class="section-tight"><div class="wrap contact-grid"><div><h2>What belongs here</h2><p>Found a recipe issue? Have a substitution question? Want to discuss a relevant partnership? Send it.</p></div>
    <form class="contact-form" action="https://formsubmit.co/{esc(FORM_EMAIL)}" method="POST">
      <div class="field"><label for="name">Name</label><input id="name" name="name" required></div>
      <div class="field"><label for="email">Email</label><input id="email" type="email" name="email" required></div>
      <div class="field"><label for="message">Message</label><textarea id="message" name="message" required></textarea></div>
      <input class="honeypot" type="text" name="_honey" tabindex="-1" autocomplete="off"><button class="btn btn-primary" type="submit">Send message</button>
    </form></div></section>'''
    write_page("/contact/", page("Contact", "Contact DishGal with recipe questions, corrections, partnership inquiries, or useful feedback about the site.", "/contact/", body))
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">The useful email</p><h1>Dinner ideas worth opening.</h1><p class="lede">Join for new recipes, planning shortcuts, and useful kitchen guidance without daily inbox clutter.</p></div></section>{newsletter_block()}'''
    write_page("/newsletter/", page("Newsletter", "Join the DishGal newsletter for practical recipes, meal-planning shortcuts, and useful kitchen guidance.", "/newsletter/", body))

def build_404():
    body = f'''<section class="page-hero"><div class="narrow"><p class="eyebrow">404</p><h1>This dinner went missing.</h1><p class="lede">The page is not here, but the recipe library is.</p><div class="button-row" style="justify-content:center;margin-top:1.5rem"><a class="btn btn-primary" href="{href('/recipes/')}">Browse recipes</a><a class="btn btn-outline" href="{href('/')}">Go home</a></div></div></section>'''
    write_page("/404.html", page("Page Not Found", "The requested DishGal page could not be found. Browse the current recipe library or return to the homepage.", "/404.html", body, noindex=True))

def copy_assets():
    ensure_dir(PUBLIC / "assets" / "css")
    ensure_dir(PUBLIC / "assets" / "js")
    shutil.copy2(ROOT / "assets" / "css" / "styles.css", PUBLIC / "assets" / "css" / "styles.css")
    shutil.copy2(ROOT / "assets" / "dishgal-brand.webp", PUBLIC / "assets" / "dishgal-brand.webp")
    source_js = (ROOT / "assets" / "js" / "site.js").read_text(encoding="utf-8")
    source_js = source_js.replace('href="/recipes/', 'href="${window.DISHGAL_BASE || ""}/recipes/')
    (PUBLIC / "assets" / "js" / "site.js").write_text(source_js, encoding="utf-8")
    tool_fields = ("slug", "title", "dek", "image", "image_alt", "collection", "tags", "prep_minutes", "cook_minutes", "total_minutes", "cost_per_serving", "ingredients", "pantry")
    tool_recipes = [{**{key: recipe[key] for key in tool_fields if key in recipe}, "protein": recipe_proteins(recipe)} for recipe in stable_recipe_mix(RECIPES)]
    tool_json = json.dumps(tool_recipes, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (PUBLIC / "assets" / "js" / "recipes.js").write_text("window.DISHGAL_RECIPES=" + tool_json + ";", encoding="utf-8")
    social = ROOT / "assets" / "social-card.png"
    if social.exists():
        shutil.copy2(social, PUBLIC / "assets" / "social-card.png")

def build_machine_files():
    html_paths = []
    for file in sorted(PUBLIC.rglob("*.html")):
        rel = file.relative_to(PUBLIC).as_posix()
        if rel == "404.html":
            continue
        if '<meta name="robots" content="noindex' in file.read_text(encoding="utf-8"):
            continue
        if rel == "index.html":
            url_path = "/"
        elif rel.endswith("/index.html"):
            url_path = "/" + rel[:-10]
        else:
            url_path = "/" + rel
        html_paths.append(url_path)
    recipe_dates = {f"/recipes/{recipe['slug']}/": recipe.get("date_modified", recipe.get("date_published", "2026-08-17")) for recipe in RECIPES}
    latest_recipe_date = max(recipe_dates.values(), default="2026-08-17")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in html_paths:
        if path in recipe_dates:
            lastmod = recipe_dates[path]
        elif path.startswith("/guides/"):
            lastmod = "2026-08-24"
        else:
            lastmod = latest_recipe_date
        sitemap.append(f"  <url><loc>{esc(canonical(path))}</loc><lastmod>{esc(lastmod)}</lastmod></url>")
    sitemap.append("</urlset>")
    (PUBLIC / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (PUBLIC / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    feed_items = []
    newest_recipes = sorted(RECIPES, key=lambda recipe: recipe.get("date_published", ""), reverse=True)[:30]
    for recipe in newest_recipes:
        recipe_url = canonical('/recipes/' + recipe['slug'] + '/')
        published = recipe.get("date_published", "2026-08-17")
        feed_items.append(f"<item><title>{esc(recipe.get('title','Recipe'))}</title><link>{esc(recipe_url)}</link><guid>{esc(recipe_url)}</guid><pubDate>{esc(rss_date(published))}</pubDate><description>{esc(recipe.get('dek',''))}</description></item>")
    for article in ARTICLES[:10]:
        article_url = canonical('/guides/' + article['slug'] + '/')
        feed_items.append(f"<item><title>{esc(article.get('title','Guide'))}</title><link>{esc(article_url)}</link><guid>{esc(article_url)}</guid><description>{esc(article.get('dek',''))}</description></item>")
    (PUBLIC / "feed.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>DishGal</title><link>{SITE_URL}</link><description>Dinner, decided.</description>{''.join(feed_items)}</channel></rss>''', encoding="utf-8")
    ads = f"google.com, {ADSENSE_PUBLISHER_ID}, DIRECT, f08c47fec0942fa0\n" if ADSENSE_PUBLISHER_ID else "# DishGal.com advertising inventory is not yet configured.\n"
    (PUBLIC / "ads.txt").write_text(ads, encoding="utf-8")
    (PUBLIC / "CNAME").write_text("dishgal.com\n", encoding="utf-8")
    (PUBLIC / ".nojekyll").write_text("", encoding="utf-8")
    manifest = {
        "name": "DishGal",
        "short_name": "DishGal",
        "start_url": href("/"),
        "display": "standalone",
        "background_color": "#fbf6ee",
        "theme_color": "#e94f37",
        "description": "Dinner, decided."
    }
    (PUBLIC / "site.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def main():
    if PUBLIC.exists() and os.environ.get("DISHGAL_NO_CLEAN") != "1":
        shutil.rmtree(PUBLIC)
    ensure_dir(PUBLIC)
    copy_assets()
    build_home()
    build_recipe_index()
    build_recipe_pages()
    build_collections()
    build_ingredient_hubs()
    build_saved()
    build_decider()
    build_pantry()
    build_planner()
    build_guides()
    build_category_indexes()
    build_utility_pages()
    build_404()
    build_machine_files()
    count = len(list(PUBLIC.rglob("*.html")))
    print(f"Built DishGal: {count} HTML pages, {len(RECIPES)} recipes, {len(ARTICLES)} guides, base={BASE or '/'}")

if __name__ == "__main__":
    main()



