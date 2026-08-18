# DishGal.com

**DishGal — Dinner, decided.**

A fast, dependency-free recipe publishing site built for GitHub Pages. The launch build contains:

- 27 complete recipes with ingredients, directions, substitutions, storage notes, FAQs, cost-per-serving estimates, nutrition estimates, and valid Recipe JSON-LD
- seven SEO-ready recipe collections with ItemList structured data
- Dinner Decider, Pantry Rescue, five-night meal planner, printable grocery lists, browser-based saved recipes, serving scaling, print layouts, and screen-awake cook mode
- five original planning and kitchen guides
- privacy, terms, editorial policy, affiliate disclosure, contact, newsletter, image credits, sitemap, RSS, robots.txt, manifest, 404 page, and ads.txt
- automatic GitHub Pages build, validation, and deployment

## Local build

```bash
python build.py
python scripts/audit.py
python -m http.server 8000 --directory public
```

Then open `http://localhost:8000`.

## Content model

Recipes live in `content/recipes.json`; guides live in `content/articles.json`. Run `python build.py` after editing content. The generated `public/` folder is intentionally not required in source control because GitHub Actions creates it for every deployment.

## Monetization configuration

The build reads optional GitHub Actions repository variables:

| Variable | Purpose |
| --- | --- |
| `FORM_EMAIL` | Newsletter/contact destination. Defaults to `hello@dishgal.com`. FormSubmit requires one-time inbox activation. |
| `AMAZON_TAG` | Adds the Amazon Associates tag to marked category links. |
| `ADSENSE_CLIENT` | Loads the AdSense script after approval, suitable for Auto Ads. |
| `ADSENSE_PUBLISHER_ID` | Generates the approved Google seller line in `ads.txt`. |
| `CLOUDFLARE_TOKEN` | Adds Cloudflare Web Analytics when a DishGal token is available. |

Do not add invented ad IDs, affiliate tags, reviews, ratings, or product-testing claims.

## Publishing

The workflow in `.github/workflows/deploy.yml` builds and deploys `public/` from `main` using the official GitHub Pages actions. The custom domain is emitted as `dishgal.com` through `public/CNAME`.

If Pages is not already enabled, set **Settings → Pages → Source** to **GitHub Actions** once. Point the domain DNS to GitHub Pages separately.

## Editorial posture

DishGal is intentionally direct: useful information is placed early, social proof is not fabricated, commercial relationships are disclosed, and category buying guides do not pretend products were personally tested.
