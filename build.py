#!/usr/bin/env python3
from __future__ import annotations

import html
import hashlib
import json
import os
import re
import shutil
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
    "one-pot": ("One-Pot Dinners", "Less cleanup, full dinner energy, one main pot.", "🍲"),
    "sheet-pan": ("Sheet-Pan Dinners", "Hands-off roasting, browned edges, fewer dishes.", "🥘"),
    "slow-cooker": ("Slow-Cooker Dinners", "Set-it-up meals for days when dinner needs to wait for you.", "♨"),
    "budget": ("Budget Dinners", "Good dinners built around useful, repeatable groceries.", "💸"),
    "vegetarian": ("Vegetarian Dinners", "Meatless meals that still eat like dinner.", "🥬"),
    "family": ("Family Favorites", "Low-drama dinners designed for the whole table.", "🍽"),
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
.shop-card-copy{display:flex;flex:1;min-width:0;flex-direction:column;align-items:flex-start;padding:1rem 1.05rem 1.1rem}
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
    matches = [protein for protein, terms in rules.items() if any(term in haystack for term in terms)]
    tags = {str(tag).lower() for tag in recipe.get("tags", [])}
    if not matches and tags.intersection({"vegetarian", "vegan"}):
        matches.append("meatless")
    return matches

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
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><path d="M5 7.5c3-4 11-4 14 0-1 2-2.5 3.4-4.5 4.2 2.2.7 3.7 2.2 4.5 4.8-3.4 3.3-10.6 3.3-14 0 .8-2.6 2.3-4.1 4.5-4.8C7.5 10.9 6 9.5 5 7.5Z" fill="currentColor"/></svg>
      </span>
      <span class="brand-name">Dish<em>Gal</em></span>
    </a>'''

def header() -> str:
    return f'''<header class="site-header">
      <div class="wrap header-inner">
        {brand()}
        <nav class="main-nav" aria-label="Primary">
          <a href="{href('/recipes/')}">Recipes</a>
          <a href="{href('/dinner-decider/')}">Dinner Decider</a>
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
            <a href="{href('/collections/30-minute/')}">30-minute dinners</a>
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

def page(title: str, description: str, path: str, body: str, *, schema=None, noindex=False) -> str:
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
    return f'''<!doctype html>
<html lang="en" data-base="{esc(BASE)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(title_full)}</title>
  <meta name="description" content="{esc(desc)}">
  {robots}
  <link rel="canonical" href="{esc(canonical(path))}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title_full)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{esc(canonical(path))}">
  <meta property="og:image" content="{SITE_URL}/assets/social-card.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="stylesheet" href="{href('/assets/css/styles.css')}">\n  {SHOP_CARD_CSS}
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
  <script src="{href('/assets/js/recipes.js')}"></script>
  <script src="{href('/assets/js/site.js')}"></script>
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

def recipe_card(recipe) -> str:
    minutes = int(recipe.get("total_minutes", int(recipe.get("prep_minutes", 0)) + int(recipe.get("cook_minutes", 0))))
    tags = " ".join(recipe.get("tags", []))
    proteins = " ".join(recipe_proteins(recipe))
    search = " ".join([
        recipe.get("title", ""),
        recipe.get("dek", ""),
        tags,
        proteins,
        " ".join(recipe.get("ingredients", [])),
        " ".join(recipe.get("pantry", [])),
    ]).lower()
    return f'''<article class="recipe-card" data-recipe-card data-search="{esc(search)}" data-tags="{esc(tags)}" data-proteins="{esc(proteins)}" data-collection="{esc(recipe.get('collection',''))}" data-minutes="{minutes}">
      <button class="icon-button recipe-card-save" data-save-recipe="{esc(recipe['slug'])}" aria-label="Save recipe">♡</button>
      <a class="recipe-card-media" href="{href('/recipes/' + recipe['slug'] + '/')}">
        <img src="{esc(recipe.get('image',''))}" alt="{esc(recipe.get('image_alt', recipe.get('title','Recipe')))}" loading="lazy">
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
      <img src="{esc(article.get('image',''))}" alt="{esc(article.get('image_alt', article.get('title','Guide')))}" loading="lazy">
      <div class="article-card-body">
        <small>{esc(article.get('category','Guide'))}</small>
        <h3><a href="{href('/guides/' + article['slug'] + '/')}">{esc(article.get('title','Guide'))}</a></h3>
        <p>{esc(article.get('dek',''))}</p>
        <a class="read-link" href="{href('/guides/' + article['slug'] + '/')}">See the guide →</a>
      </div>
    </article>'''

SHOP_IMAGES = {
    "enameled dutch oven 6 quart": ("https://images.pexels.com/photos/20430669/pexels-photo-20430669.jpeg?auto=compress&dpr=1&h=750&w=1260", "Red enameled Dutch oven on a kitchen work surface"),
    "immersion blender stainless steel": ("https://images.pexels.com/photos/6605163/pexels-photo-6605163.jpeg?auto=compress&dpr=1&h=750&w=1260", "Chef using an immersion blender in a tall mixing cup"),
    "digital probe meat thermometer": ("https://images.unsplash.com/photo-1622001545761-9bd12a4b465b?auto=format&fit=crop&w=900&q=80", "Two digital probe cooking thermometers beside prepared ingredients"),
    "stainless steel pasta pot colander": ("https://images.pexels.com/photos/5907595/pexels-photo-5907595.jpeg?auto=compress&dpr=1&h=750&w=1260", "Pasta draining through a stainless-steel colander"),
    "microplane zester grater stainless": ("https://images.pexels.com/photos/6287524/pexels-photo-6287524.jpeg?auto=compress&dpr=1&h=750&w=1260", "Cheese being grated on a stainless-steel grater"),
    "stainless steel kitchen tongs silicone tip": ("https://images.pexels.com/photos/11968836/pexels-photo-11968836.jpeg?auto=compress&dpr=1&h=750&w=1260", "Kitchen tongs turning food over a grill"),
    "heavy gauge aluminum half sheet pan": ("https://images.pexels.com/photos/13156063/pexels-photo-13156063.jpeg?auto=compress&dpr=1&h=750&w=1260", "Rimmed metal baking sheet lined with parchment"),
    "9 by 13 baking dish casserole": ("https://images.pexels.com/photos/19145679/pexels-photo-19145679/free-photo-of-meal-in-glass-box.jpeg?auto=compress&dpr=1&h=750&w=1260", "Rectangular glass baking dish filled with a browned eggplant casserole"),
    "silicone oven mitts heat resistant": ("https://images.unsplash.com/photo-1743684456567-a3d32dbf702e?auto=format&fit=crop&w=900&q=80", "Two heat-safe oven mitts hanging above kitchen pots and pans"),
    "rice cooker family stainless inner pot": ("https://images.unsplash.com/photo-1599182345361-9542815e73f6?auto=format&fit=crop&w=900&h=600&q=80", "White-and-black countertop rice cooker with a glass lid and removable inner pot"),
    "glass meal prep containers locking lids": ("https://images.pexels.com/photos/30635719/pexels-photo-30635719.jpeg?auto=compress&dpr=1&h=750&w=1260", "Prepared meals arranged in clear lidded containers"),
    "digital kitchen scale grams ounces": ("https://images.pexels.com/photos/5622193/pexels-photo-5622193.jpeg?auto=compress&dpr=1&h=750&w=1260", "Bowl of vegetables resting on a digital kitchen scale"),
    "12 inch cast iron skillet": ("https://images.unsplash.com/photo-1569810912653-c0e8d1184623?auto=format&fit=crop&w=900&q=80", "Cast-iron skillet with a finished baked pasta"),
    "silicone fish spatula turner": ("https://images.unsplash.com/photo-1673155225557-bee5d2540158?auto=format&fit=crop&w=900&q=80", "Flexible kitchen spatula being used during cooking"),
    "stainless steel mixing bowls nesting": ("https://images.pexels.com/photos/31109993/pexels-photo-31109993.jpeg?auto=compress&dpr=1&h=750&w=1260", "Stainless-steel mixing bowl and matching strainer bowl"),
    "stainless steel measuring scoops set": ("https://images.unsplash.com/photo-1781082580025-407abed1d50f?auto=format&fit=crop&w=900&h=600&crop=entropy&q=80", "Stainless-steel measuring scoops arranged on a work surface"),
    "8 inch chef knife kitchen": ("https://images.unsplash.com/photo-1711065060638-675df8e8c358?auto=format&fit=crop&w=900&q=80", "Chef's knife resting on a wooden cutting board"),
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
    (("scale",), ("https://images.pexels.com/photos/5622193/pexels-photo-5622193.jpeg?auto=compress&dpr=1&h=750&w=1260", "Bowl resting on a digital kitchen scale")),
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
    url = f"https://www.amazon.com/s?k={quote_plus(query)}&amp;tag={quote_plus(AMAZON_TAG)}"
    image_url, image_alt = shop_image(query)
    return f"""<a class="shop-card" href="{url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-commercial-link="true" data-affiliate-active="true" data-affiliate-network="amazon" data-affiliate-tag="{esc(AMAZON_TAG)}">
      <span class="shop-card-media" style="background-image:url('{esc(image_url)}')"><img src="{esc(image_url)}" alt="{esc(image_alt)}" loading="eager" decoding="async" width="900" height="600"></span>
      <span class="shop-card-copy"><small>Compare on Amazon</small><strong>{esc(label)}</strong>{f'<span>{esc(note)}</span>' if note else ''}<b>See current options →</b></span>
    </a>"""

def recipe_shop(recipe) -> str:
    haystack = " ".join([
        recipe.get("title", ""), recipe.get("dek", ""), recipe.get("collection", ""),
        " ".join(recipe.get("tags", [])), " ".join(recipe.get("ingredients", [])),
    ]).lower()
    if "margherita pizza" in haystack:
        products = [
            ("heavy gauge aluminum half sheet pan", "Heavy half-sheet pan", "Preheating a sturdy inverted pan gives the pizza a broad, intensely hot surface for a crisper underside."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure hand protection matters when transferring the pizza around a sheet pan held at 500°F."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weighing the dough and cheese keeps the topping ratio balanced and the center from becoming overloaded."),
        ]
    elif "kimchi fried rice" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch cast-iron skillet", "A broad heat-steady surface lets cold rice fry in a thin layer instead of steaming into clumps."),
            ("rice cooker family stainless inner pot", "Family-size rice cooker", "Cook and cool the rice ahead, then use the cooker again when doubling the batch for meal prep."),
            ("large nonslip cutting board", "Large nonslip cutting board", "A stable board contains kimchi brine while leaving room to separate scallion whites from their green garnish."),
        ]
    elif "pear frangipane tart" in haystack:
        products = [
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "A secure grip helps when lifting the hot tart pan without pressing against its removable base."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Gram weights keep both flours and the frangipane ratio precise for a crisp shell and tender filling."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "Separate bowls keep the frangipane, sliced pears and warm glaze organized without crowding the counter."),
        ]
    elif "thai basil beef" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch cast-iron skillet", "A wide, heat-steady skillet browns the beef quickly and leaves room to fry crisp-edged eggs."),
            ("rice cooker family stainless inner pot", "Family-size rice cooker", "Hands-off jasmine rice can cook while the sauce is mixed and the basil beef comes together."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Confirm the ground beef reaches 160°F without cooking away all of its moisture."),
        ]
    elif "eggplant parmesan" in haystack:
        products = [
            ("heavy gauge aluminum half sheet pan", "Heavy half-sheet pans", "Two broad rimmed pans let the breaded eggplant bake in one uncrowded layer for a crisper crust."),
            ("9 by 13 baking dish casserole", "9-by-13-inch baking dish", "Straight sides hold the layered eggplant, tomato sauce, and cheese neatly for clean square portions."),
            ("microplane zester grater stainless", "Fine cheese grater", "Finely grated Parmesan distributes evenly through the breading and over the finished casserole."),
        ]
    elif "orange-almond cake" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weights keep the almond-flour and orange-purée ratios precise in this flourless batter."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "Separate bowls make it easy to whisk the dry ingredients, eggs, and citrus syrup without crowding."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "A secure grip helps when moving the hot springform pan and its supporting sheet pan."),
        ]
    elif "pork adobo" in haystack:
        products = [
            ("enameled dutch oven 6 quart", "6-quart Dutch oven", "A heavy, tight-lidded pot browns the pork evenly and holds the gentle simmer needed for tender shoulder and belly."),
            ("rice cooker family stainless inner pot", "Family-size rice cooker", "Reliable steamed rice can finish hands-off while the adobo braises and its sauce reduces."),
            ("stainless steel kitchen tongs silicone tip", "Kitchen tongs", "Turn browned pork and glaze the braised pieces without crushing the tender meat."),
        ]
    elif "herb falafel" in haystack:
        products = [
            ("food processor 12 cup", "12-cup food processor", "Short pulses create the coarse chickpea-and-herb texture that holds together without becoming dense."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "Separate bowls keep the soaked chickpeas, falafel mixture, and lemon-tahini sauce organized."),
            ("stainless steel kitchen tongs silicone tip", "Long kitchen tongs", "A long, secure grip helps manage pita and the draining rack while keeping hands clear of hot oil."),
        ]
    elif "cinnamon rolls" in haystack:
        products = [
            ("stand mixer tilt head", "Stand mixer", "A mixer fitted with its dough hook provides steady kneading while the butter is added gradually."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weight measurements keep the high-hydration dough soft instead of accidentally flour-heavy."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "A secure grip matters when rotating and lifting the hot 9-by-13-inch pan."),
        ]
    elif "lamb tagine" in haystack:
        products = [
            ("enameled dutch oven 6 quart", "6-quart Dutch oven", "A heavy, tight-lidded pot maintains the gentle, even simmer that turns lamb shoulder fork-tender."),
            ("digital probe meat thermometer", "Digital probe thermometer", "Check that the largest lamb pieces reach the collagen-melting braising range without repeatedly cutting them."),
            ("stainless steel kitchen tongs silicone tip", "Kitchen tongs", "Turn and transfer browned lamb cleanly while keeping hands clear of hot oil."),
        ]
    elif "shrimp summer rolls" in haystack:
        products = [
            ("8 inch chef knife kitchen", "8-inch chef’s knife", "A sharp, controllable blade makes even vegetable matchsticks and cleanly halves poached shrimp."),
            ("large nonslip cutting board", "Large nonslip cutting board", "A stable, roomy surface keeps herbs, vegetables, noodles, and cooked shrimp organized for rolling."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "Separate bowls simplify cooling shrimp, holding noodles, and mixing the peanut-hoisin sauce."),
        ]
    elif "tiramisu cups" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weight measurements keep the yolk, sugar, mascarpone, and ladyfinger ratios precise."),
            ("stainless steel mixing bowls nesting", "Heat-safe mixing bowls", "Separate bowls are useful for the cooked yolk base, mascarpone, and whipped cream."),
            ("stainless steel measuring scoops set", "Stainless measuring scoops", "Consistent small measures keep the espresso, vanilla, and cocoa balanced across six cups."),
        ]
    elif "seafood paella" in haystack:
        products = [
            ("12 inch cast iron skillet", "Wide 12-inch skillet", "A broad, heat-steady cooking surface keeps the rice shallow enough to cook evenly and form socarrat."),
            ("stainless steel kitchen tongs", "Stainless-steel kitchen tongs", "Lift and place hot shellfish without crushing shells or disturbing the rice bed."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip matters when rotating and carrying a heavy skillet filled with hot rice and seafood."),
        ]
    elif "croque madame" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch skillet", "A broad, heat-steady skillet crisps two sandwiches at a time and then fries the eggs evenly."),
            ("8 inch chef knife kitchen", "8-inch chef’s knife", "A sharp, controllable knife handles the shallot, trims bread, and halves crisp sandwiches cleanly."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "Separate bowls keep grated cheese, salad greens, and vinaigrette organized for fast assembly."),
        ]
    elif "chocolate-walnut layer cake" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weight measurements keep the cocoa batter even and divide it accurately among three pans."),
            ("stainless steel mixing bowls nesting", "Roomy mixing bowls", "Use separate heat-safe bowls for the batter, ganache, and whipped walnut filling."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip and forearm coverage help when rotating three hot cake pans."),
        ]
    elif "katsu" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch skillet", "A heavy skillet holds steady heat for crisp, even shallow-frying."),
            ("digital probe meat thermometer", "Digital probe thermometer", "Verify the chicken reaches 165°F without cutting through the crust."),
            ("stainless steel kitchen tongs silicone tip", "Kitchen tongs", "Turn breaded cutlets with control while keeping hands clear of hot oil."),
        ]
    elif "red lentil soup" in haystack:
        products = [
            ("enameled dutch oven 6 quart", "Dutch oven", "A wide, heavy pot gives vegetables room to soften and lentils a steady simmer."),
            ("immersion blender stainless steel", "Immersion blender", "Purée the soup in its pot with less transfer and cleanup."),
            ("8 inch chef knife kitchen", "Chef’s knife", "A sharp, comfortable knife makes quick work of the onion, carrot, and potato."),
        ]
    elif "pad thai-style" in haystack:
        products = [
            ("stainless steel pasta pot colander", "Stainless colander", "Drain soaked rice noodles completely so the sauce clings instead of turning watery."),
            ("stainless steel kitchen tongs silicone tip", "Kitchen tongs", "Lift and turn delicate rice noodles without chopping or crushing them."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify shrimp reach 145°F and the egg reaches 160°F without overcooking the seafood."),
        ]
    elif "butter beans" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch skillet", "A wide cooking surface reduces the tomato sauce quickly while giving large beans room to stay whole."),
            ("8 inch chef knife kitchen", "Chef’s knife", "A sharp, controllable knife handles the fine onion dice and thin garlic slices cleanly."),
            ("large nonslip cutting board", "Large cutting board", "A stable prep surface keeps the onion, garlic, and toasted bread organized."),
        ]
    elif "carrot snacking cake" in haystack:
        products = [
            ("stainless steel measuring scoops set", "Stainless measuring scoops", "Measure flour, spices, sugar, vanilla, and lemon consistently for a reliable crumb and frosting."),
            ("stainless steel mixing bowls nesting", "Roomy mixing bowl", "Extra room makes it easier to fold in finely grated carrots without overmixing the batter."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip and forearm coverage help when turning out a hot 9-inch cake pan."),
        ]
    elif "palak paneer" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch skillet", "A wide, heat-steady skillet browns paneer without crowding and gives the tomato masala room to reduce."),
            ("immersion blender stainless steel", "Immersion blender", "Purée the cooled spinach in a tall container with less transfer and cleanup."),
            ("8 inch chef knife kitchen", "Chef’s knife", "A sharp, controllable knife handles the fine aromatics and uniform paneer cubes cleanly."),
        ]
    elif "shish tawook" in haystack:
        products = [
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify the largest chicken pieces reach 165°F without cutting every skewer open."),
            ("stainless steel kitchen tongs silicone tip", "Long kitchen tongs", "Turn hot skewers and oil the grill grate while keeping hands clear of direct heat."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "Use separate bowls for raw-chicken marinade and the finished garlic yogurt to avoid cross-contamination."),
        ]
    elif "cinnamon-apple tart" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weight measurements keep the shortcrust flour and sugar ratio precise and repeatable."),
            ("stainless steel mixing bowls nesting", "Roomy mixing bowl", "A broad bowl makes cutting cold butter into flour and tossing delicate apple slices easier."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip helps when moving the hot removable-bottom tart pan on its supporting sheet pan."),
        ]
    elif "shrimp" in haystack and "grits" in haystack:
        products = [
            ("12 inch cast iron skillet", "12-inch skillet", "A wide, heat-steady skillet sears the shrimp quickly and reduces the smoky tomato sauce without crowding."),
            ("digital probe meat thermometer", "Instant-read thermometer", "Verify the shrimp reach 145°F before they turn firm and rubbery."),
            ("stainless steel measuring scoops set", "Stainless measuring scoops", "Keep the grits-to-liquid ratio and small seasoning quantities consistent."),
        ]
    elif "mushroom risotto" in haystack:
        products = [
            ("enameled dutch oven 6 quart", "Wide Dutch oven", "A heavy, broad pot gives mushrooms room to brown and Arborio rice a steady simmer."),
            ("microplane zester grater stainless", "Fine grater", "Finely grated Parmesan melts smoothly into the risotto instead of clumping."),
            ("stainless steel kitchen tongs silicone tip", "Kitchen tongs", "Turn and transfer browned mushroom slices without crushing them."),
        ]
    elif "basque cheesecake" in haystack:
        products = [
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Weight measurements keep the sugar and flour ratio precise for a custardy set."),
            ("stainless steel mixing bowls nesting", "Roomy mixing bowl", "A large, stable bowl gives the dairy and eggs space to blend smoothly without splashing."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip matters when moving a tall parchment-lined pan on a hot sheet pan."),
        ]
    elif "sheet pan" in haystack:
        products = [
            ("heavy gauge aluminum half sheet pan", "Half-sheet pans", "Heavy-gauge, rimmed pans give food room to roast."),
            ("digital probe meat thermometer", "Digital probe thermometer", "Check food safely without cutting into every piece."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Grip and forearm coverage matter when moving a loaded pan."),
        ]
    elif any(term in haystack for term in ["soup", "chili", "stew"]):
        products = [
            ("enameled dutch oven 6 quart", "Dutch oven", "A wide, heavy pot for browning and steady simmering."),
            ("immersion blender stainless steel", "Immersion blender", "Blend soups in the pot with less transfer and cleanup."),
            ("digital probe meat thermometer", "Digital probe thermometer", "Verify doneness instead of guessing."),
        ]
    elif any(term in haystack for term in ["pasta", "orzo", "noodle"]):
        products = [
            ("stainless steel pasta pot colander", "Pasta pot and colander", "Choose stable handles and a size that fits the dinners you actually cook."),
            ("microplane zester grater stainless", "Fine grater", "Useful for citrus, hard cheese, garlic and finishing details."),
            ("stainless steel kitchen tongs silicone tip", "Kitchen tongs", "A dependable tool for tossing, turning and serving."),
        ]
    elif any(term in haystack for term in ["eggplant", "aubergine"]):
        products = [
            ("8 inch chef knife kitchen", "Chef’s knife", "A sharp, comfortable knife makes scoring eggplant and chopping herbs easier."),
            ("large nonslip cutting board", "Nonslip cutting board", "A roomy, stable prep surface keeps large vegetables under control."),
            ("stainless steel mixing bowls nesting", "Mixing bowls", "Useful for salting vegetables, whisking glaze, and holding toppings."),
        ]
    elif any(term in haystack for term in ["salad", "slaw"]):
        products = [
            ("8 inch chef knife kitchen", "Chef’s knife", "A sharp, comfortable knife makes quick work of vegetables and herbs."),
            ("large nonslip cutting board", "Nonslip cutting board", "A roomy, stable prep surface keeps chopping organized."),
            ("stainless steel mixing bowls nesting", "Mixing bowls", "A large bowl gives salads room to toss without bruising the ingredients."),
        ]
    elif any(term in haystack for term in ["pie", "cobbler", "pastry", "dessert"]):
        products = [
            ("stainless steel measuring scoops set", "Stainless measuring scoops", "A nested set keeps flour, cornmeal and sugar measurements consistent."),
            ("stainless steel mixing bowls nesting", "Mixing bowls", "Use separate bowls for fillings and pastry or cobbler topping."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Secure grip and forearm coverage help when moving hot bakeware."),
        ]
    elif any(term in haystack for term in ["roast", "baked", "oven"]):
        products = [
            ("heavy gauge aluminum half sheet pan", "Half-sheet pans", "Heavy-gauge, rimmed pans give food room to roast."),
            ("digital probe meat thermometer", "Digital probe thermometer", "Check food safely without cutting into every piece."),
            ("silicone oven mitts heat resistant", "Heat-safe oven mitts", "Grip and forearm coverage matter when moving a loaded pan."),
        ]
    elif any(term in haystack for term in ["rice", "bowl", "meal prep"]):
        products = [
            ("rice cooker family stainless inner pot", "Rice cooker", "Compare capacity, cleanup and a simple keep-warm function."),
            ("glass meal prep containers locking lids", "Glass storage containers", "A small matching system stacks better than forty mystery lids."),
            ("digital kitchen scale grams ounces", "Digital kitchen scale", "Fast, repeatable portions and better baking accuracy."),
        ]
    elif any(term in haystack for term in ["skillet", "frittata", "egg", "breakfast"]):
        products = [
            ("12 inch cast iron skillet", "12-inch skillet", "A versatile size for browning, baking and family portions."),
            ("silicone fish spatula turner", "Thin flexible spatula", "Slides under eggs and delicate food without a wrestling match."),
            ("stainless steel mixing bowls nesting", "Nesting mixing bowls", "One sturdy set handles prep without multiplying cabinet clutter."),
        ]
    else:
        products = [
            ("digital probe meat thermometer", "Digital probe thermometer", "Replace doneness guesses with a clear temperature reading."),
            ("8 inch chef knife kitchen", "8-inch chef's knife", "Prioritize comfortable grip, controllable weight and easy maintenance."),
            ("large nonslip cutting board", "Large cutting board", "Enough stable workspace makes prep faster and safer."),
        ]
    cards = "".join(amazon_link(*product) for product in products)
    return f'''<div class="recipe-panel recipe-shop"><p class="eyebrow">Useful kitchen gear</p><h2>Tools that make this easier.</h2>
      <p>Compare the function and specifications first; skip anything your kitchen already handles well.</p>
      <div class="disclosure-box"><strong>Paid links:</strong> As an Amazon Associate I earn from qualifying purchases. You pay no additional cost.</div>
      <div class="shop-grid">{cards}</div>
    </div>'''

def newsletter_block() -> str:
    return f'''<section class="section-tight">
      <div class="wrap">
        <div class="newsletter">
          <div class="newsletter-grid">
            <div><p class="eyebrow">The useful email</p><h2>Dinner ideas worth opening.</h2><p>New recipes, a five-night shortcut, and one useful kitchen idea. No daily inbox ambush.</p></div>
            <form class="newsletter-form" action="https://formsubmit.co/{esc(FORM_EMAIL)}" method="POST">
              <input type="email" name="email" required placeholder="you@example.com" aria-label="Email address">
              <input class="honeypot" type="text" name="_honey" tabindex="-1" autocomplete="off">
              <input type="hidden" name="_subject" value="DishGal newsletter signup">
              <button class="btn btn-primary" type="submit">Join free</button>
            </form>
          </div>
        </div>
      </div>
    </section>'''

def recipe_schema(recipe) -> dict:
    instructions = [
        {"@type": "HowToStep", "name": step.get("name", f"Step {i+1}"), "text": step.get("text", "")}
        for i, step in enumerate(recipe.get("instructions", []))
    ]
    total = int(recipe.get("total_minutes", int(recipe.get("prep_minutes", 0)) + int(recipe.get("cook_minutes", 0))))
    return {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe.get("title", ""),
        "description": recipe.get("dek", ""),
        "image": [recipe.get("image", "")],
        "author": {"@type": "Organization", "name": "DishGal"},
        "datePublished": recipe.get("date_published", "2026-08-17"),
        "dateModified": recipe.get("date_modified", recipe.get("date_published", "2026-08-17")),
        "prepTime": f"PT{int(recipe.get('prep_minutes',0))}M",
        "cookTime": f"PT{int(recipe.get('cook_minutes',0))}M",
        "totalTime": f"PT{total}M",
        "recipeYield": f"{recipe.get('servings',4)} servings",
        "recipeIngredient": recipe.get("ingredients", []),
        "recipeInstructions": instructions,
        "nutrition": {"@type": "NutritionInformation", "calories": f"{recipe.get('calories','')} calories"},
        "url": canonical("/recipes/" + recipe["slug"] + "/"),
    }

def build_home():
    mixed_recipes = stable_recipe_mix(RECIPES)
    featured = mixed_recipes[:8]
    hero = mixed_recipes[0]
    collections = sorted({r.get("collection", "") for r in RECIPES if r.get("collection")})
    collection_html = []
    for slug in collections:
        title, _, icon = COLLECTION_META.get(slug, (pretty_slug(slug), "Browse this dinner collection.", "🍴"))
        count = sum(1 for r in RECIPES if r.get("collection") == slug)
        collection_html.append(f'''<a class="collection-pill" href="{href('/collections/' + slug + '/')}"><span class="collection-icon">{icon}</span><strong>{esc(title)}</strong><small>{count} recipes</small></a>''')
    body = f'''
    <section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">Dinner, decided.</p>
          <h1>Good food for <span>real nights.</span></h1>
          <p class="lede">DishGal gives you practical weeknight recipes, a dinner picker, pantry rescue, and a five-night planner—without turning dinner into a personality test.</p>
          <div class="button-row"><a class="btn btn-primary" href="{href('/dinner-decider/')}">Decide dinner</a><a class="btn btn-outline" href="{href('/recipes/')}">Browse recipes</a></div>
          <div class="hero-proof"><span>{len(RECIPES)} complete recipes</span><span>Real prep + cook times</span><span>Cost per serving</span></div>
        </div>
        <div class="hero-media"><img class="hero-image" src="{esc(hero.get('image',''))}" alt="{esc(hero.get('image_alt','Weeknight dinner'))}"><div class="hero-sticker">No-scroll-before-the-recipe energy.</div></div>
      </div>
    </section>
    <section class="section section-paper">
      <div class="wrap">
        <div class="section-heading"><div><p class="eyebrow">Pick your lane</p><h2>Dinner collections</h2></div><p>Start with the kind of night you are having, not a 2,000-word food memoir.</p></div>
        <div class="collection-grid">{''.join(collection_html)}</div>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <div class="section-heading"><div><p class="eyebrow">Start here</p><h2>Weeknight winners</h2></div><a class="btn btn-outline" href="{href('/recipes/')}">See all recipes</a></div>
        <div class="recipe-grid">{''.join(recipe_card(r) for r in featured)}</div>
      </div>
    </section>
    <section class="section section-plum">
      <div class="wrap">
        <div class="section-heading"><div><p class="eyebrow">Use the tools</p><h2>Less deciding. More eating.</h2></div><p>Three tiny tools for the three most annoying dinner questions.</p></div>
        <div class="tool-strip"><div class="tool-grid">
          <a class="tool-card" href="{href('/dinner-decider/')}"><span class="icon">🎯</span><h3>Dinner Decider</h3><p>Choose your time and vibe. Get one answer.</p></a>
          <a class="tool-card" href="{href('/pantry-rescue/')}"><span class="icon">🧺</span><h3>Pantry Rescue</h3><p>Tell us what you have. We rank the best recipe matches.</p></a>
          <a class="tool-card" href="{href('/meal-planner/')}"><span class="icon">🗓</span><h3>5-Night Planner</h3><p>Build a varied week and turn it into a grocery checklist.</p></a>
        </div></div>
      </div>
    </section>
    <section class="section section-paper">
      <div class="wrap">
        <div class="section-heading"><div><p class="eyebrow">Kitchen brain</p><h2>Kitchen picks</h2></div><a class="btn btn-outline" href="{href('/guides/')}">All {len(ARTICLES)} guides</a></div>
        <div class="article-grid">{''.join(article_card(a) for a in ARTICLES[:6])}</div>
      </div>
    </section>
    {newsletter_block()}
    '''
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "DishGal",
        "url": SITE_URL,
        "description": "Practical recipes, dinner-planning tools, and kitchen guides for real weeknights."
    }
    write_page("/", page("Dinner, Decided", "Practical weeknight recipes, dinner-planning tools, and useful kitchen guides built to answer the question: what are we eating tonight?", "/", body, schema=schema))

def build_recipe_index():
    display_recipes = stable_recipe_mix(RECIPES)
    collections = sorted({r.get("collection","") for r in RECIPES if r.get("collection")})
    options = "".join(f'<option value="{esc(c)}">{esc(COLLECTION_META.get(c,(pretty_slug(c),"",""))[0])}</option>' for c in collections)
    proteins = sorted({protein for recipe in RECIPES for protein in recipe_proteins(recipe)}, key=lambda item: PROTEIN_META.get(item, pretty_slug(item)))
    protein_options = "".join(f'<option value="{esc(protein)}">{esc(PROTEIN_META.get(protein, pretty_slug(protein)))}</option>' for protein in proteins)
    body = f'''<section class="page-hero"><div class="wrap"><p class="eyebrow">Recipe library</p><h1>Find tonight’s dinner.</h1><p class="lede">Filter by time, meat or protein, collection, or diet. Every recipe includes full directions, substitutions, storage notes, FAQs, and realistic timing.</p></div></section>
    <section class="section-tight"><div class="wrap">
      <form class="filter-panel" data-recipe-filters>
        <div class="filter-row">
          <div class="field"><label for="q">Search</label><input id="q" name="q" placeholder="chicken, ribeye, pasta…"></div>
          <div class="field"><label for="time">Max time</label><select id="time" name="time"><option value="">Any</option><option value="25">25 min</option><option value="30">30 min</option><option value="45">45 min</option><option value="60">60 min</option></select></div>
          <div class="field"><label for="protein">Meat / protein</label><select id="protein" name="protein"><option value="">All</option>{protein_options}</select></div>
          <div class="field"><label for="collection">Collection</label><select id="collection" name="collection"><option value="">All</option>{options}</select></div>
          <div class="field"><label for="diet">Diet</label><select id="diet" name="diet"><option value="">Any</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option><option value="gluten-free">Gluten-free</option></select></div>
          <button class="btn btn-outline" type="button" data-reset-filters>Reset</button>
        </div>
      </form>
      <p class="result-count" data-result-count>{len(display_recipes)} recipes</p>
      <div class="recipe-grid">{''.join(recipe_card(r) for r in display_recipes)}</div>
      <div class="empty-state" data-empty-state><h3>No matching dinners</h3><p>Try fewer filters or a broader search.</p></div>
    </div></section>'''
    write_page("/recipes/", page("Recipes", "Browse DishGal's complete recipe library with filters for time, meat or protein, dinner collection, and dietary preferences.", "/recipes/", body))

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
        body = f'''<section class="recipe-hero" data-recipe-page data-servings="{int(recipe.get('servings',4))}">
          <div class="wrap">{breadcrumbs([("Recipes","/recipes/"),(recipe.get("title","Recipe"),None)])}
          <div class="recipe-hero-grid">
            <img class="recipe-hero-image" src="{esc(recipe.get('image',''))}" alt="{esc(recipe.get('image_alt', recipe.get('title','Recipe')))}">
            <div><p class="eyebrow">{esc(COLLECTION_META.get(recipe.get('collection',''),(pretty_slug(recipe.get('collection','recipe')),"",""))[0])}</p>
              <h1>{esc(recipe.get('title','Recipe'))}</h1><p class="lede">{esc(recipe.get('dek',''))}</p>
              <p class="recipe-byline">Developed for DishGal · Updated {esc(recipe.get('date_modified','2026-08-17'))}</p>
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
        <div class="cook-mode" data-cook-mode><div class="cook-mode-inner"><div class="cook-mode-head"><div><strong>{esc(recipe.get('title','Recipe'))}</strong><div class="muted">Screen stays awake when supported.</div></div><button class="btn btn-dark" type="button" data-close-cook>Exit cook mode</button></div>{cook_steps}</div></div>'''
        write_page(f"/recipes/{slug}/", page(recipe.get("title","Recipe"), recipe.get("dek","Complete recipe with ingredients, directions, substitutions, storage notes, and FAQs."), f"/recipes/{slug}/", body, schema=recipe_schema(recipe)))

def build_collections():
    collections = sorted({r.get("collection","") for r in RECIPES if r.get("collection")})
    for slug in collections:
        recipes = stable_recipe_mix([r for r in RECIPES if r.get("collection") == slug])
        title, desc, _ = COLLECTION_META.get(slug, (pretty_slug(slug), f"Browse DishGal's {pretty_slug(slug).lower()} recipes.", "🍴"))
        body = f'''<section class="page-hero"><div class="wrap">{breadcrumbs([("Recipes","/recipes/"),(title,None)])}<p class="eyebrow">Dinner collection</p><h1>{esc(title)}</h1><p class="lede">{esc(desc)} Browse {len(recipes)} complete recipes with timing, cost, substitutions, and storage notes.</p></div></section>
        <section class="section-tight"><div class="wrap"><div class="recipe-grid">{''.join(recipe_card(r) for r in recipes)}</div></div></section>'''
        write_page(f"/collections/{slug}/", page(title, f"{desc} Browse complete DishGal recipes with realistic timing, substitutions, and storage notes.", f"/collections/{slug}/", body))

def build_saved():
    body = f'''<section class="page-hero"><div class="wrap"><p class="eyebrow">Your shortlist</p><h1>Saved recipes</h1><p class="lede">Recipes you heart are stored in this browser on this device. No account required.</p></div></section>
    <section class="section-tight"><div class="wrap"><div class="recipe-grid" data-saved-grid></div></div></section>'''
    write_page("/saved/", page("Saved Recipes", "Keep a browser-based shortlist of DishGal recipes without creating an account or sharing personal information.", "/saved/", body))

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
    write_page("/dinner-decider/", page("Dinner Decider", "Choose your available time and dinner preferences, then let DishGal pick one practical recipe for tonight.", "/dinner-decider/", body))

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
    write_page("/pantry-rescue/", page("Pantry Rescue", "Select ingredients you already have and DishGal will rank recipes by ingredient overlap to help reduce waste and dinner indecision.", "/pantry-rescue/", body))

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
    write_page("/meal-planner/", page("5-Night Meal Planner", "Build a five-night DishGal dinner plan based on your available cooking time, then generate a practical grocery checklist.", "/meal-planner/", body))

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
        <div class="wrap"><img class="article-hero-image" src="{esc(article.get('image',''))}" alt="{esc(article.get('image_alt', article.get('title','Guide')))}"></div>
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
        write_page(f"/guides/{article['slug']}/", page(article.get("title","Guide"), article.get("dek","Practical kitchen and meal-planning guidance from DishGal."), f"/guides/{article['slug']}/", body, schema=article_schema))

def build_category_indexes():
    for slug, (name, desc, _) in GUIDE_CATEGORY_META.items():
        matches = [a for a in ARTICLES if a.get("category","").lower().replace(" ","-") == slug]
        body = f'''<section class="page-hero"><div class="wrap"><p class="eyebrow">DishGal guides</p><h1>{esc(name)}</h1><p class="lede">{esc(desc)}</p></div></section>
        <section class="section-tight"><div class="wrap"><div class="article-grid">{''.join(article_card(a) for a in matches) if matches else '<div class="empty-state is-visible"><h3>More guides coming</h3><p>Browse all current guides while this section grows.</p></div>'}</div></div></section>'''
        write_page(f"/guides/category/{slug}/", page(name, f"{desc} Browse DishGal's current {name.lower()} guides.", f"/guides/category/{slug}/", body))

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
        ("Editorial images","Current recipe and guide images are sourced from Unsplash, Pexels, and Pixabay under their applicable platform licenses."),
        ("Attribution","Photographers retain rights under the applicable source license and platform terms. The slow-cooker image is by Your Best Digs via Wikimedia Commons, licensed CC BY 2.0."),
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
    source_js = (ROOT / "assets" / "js" / "site.js").read_text(encoding="utf-8")
    source_js = source_js.replace('href="/recipes/', 'href="${window.DISHGAL_BASE || ""}/recipes/')
    (PUBLIC / "assets" / "js" / "site.js").write_text(source_js, encoding="utf-8")
    (PUBLIC / "assets" / "js" / "recipes.js").write_text("window.DISHGAL_RECIPES=" + json_script(RECIPES) + ";", encoding="utf-8")
    social = ROOT / "assets" / "social-card.png"
    if social.exists():
        shutil.copy2(social, PUBLIC / "assets" / "social-card.png")

def build_machine_files():
    html_paths = []
    for file in sorted(PUBLIC.rglob("*.html")):
        rel = file.relative_to(PUBLIC).as_posix()
        if rel == "404.html":
            continue
        if rel == "index.html":
            url_path = "/"
        elif rel.endswith("/index.html"):
            url_path = "/" + rel[:-10]
        else:
            url_path = "/" + rel
        html_paths.append(url_path)
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in html_paths:
        sitemap.append(f"  <url><loc>{esc(canonical(path))}</loc></url>")
    sitemap.append("</urlset>")
    (PUBLIC / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (PUBLIC / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    feed_items = []
    for article in ARTICLES:
        feed_items.append(f"<item><title>{esc(article.get('title','Guide'))}</title><link>{esc(canonical('/guides/' + article['slug'] + '/'))}</link><description>{esc(article.get('dek',''))}</description></item>")
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

