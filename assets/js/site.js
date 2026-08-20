(() => {
  const body = document.body;
  const menuButton = document.querySelector('[data-menu-button]');
  const menuClose = () => {
    body.classList.remove('nav-open');
    if (menuButton) menuButton.setAttribute('aria-expanded', 'false');
  };
  if (menuButton) {
    menuButton.addEventListener('click', () => {
      const open = body.classList.toggle('nav-open');
      menuButton.setAttribute('aria-expanded', String(open));
    });
    document.querySelectorAll('.main-nav a').forEach(a => a.addEventListener('click', menuClose));
  }

  const STORAGE_KEY = 'dishgal:saved';
  const getSaved = () => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch { return []; }
  };
  const setSaved = items => localStorage.setItem(STORAGE_KEY, JSON.stringify([...new Set(items)]));
  const syncSaveButtons = () => {
    const saved = getSaved();
    document.querySelectorAll('[data-save-recipe]').forEach(button => {
      const active = saved.includes(button.dataset.saveRecipe);
      button.classList.toggle('is-saved', active);
      button.setAttribute('aria-pressed', String(active));
      const text = button.querySelector('[data-save-label]');
      if (text) text.textContent = active ? 'Saved' : 'Save recipe';
      if (!text) button.setAttribute('aria-label', active ? 'Remove saved recipe' : 'Save recipe');
    });
  };
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-save-recipe]');
    if (!button) return;
    const slug = button.dataset.saveRecipe;
    const saved = getSaved();
    const next = saved.includes(slug) ? saved.filter(item => item !== slug) : [...saved, slug];
    setSaved(next);
    syncSaveButtons();
    if (document.querySelector('[data-saved-grid]')) renderSaved();
  });
  syncSaveButtons();

  const filterForm = document.querySelector('[data-recipe-filters]');
  if (filterForm) {
    const cards = [...document.querySelectorAll('[data-recipe-card]')];
    const count = document.querySelector('[data-result-count]');
    const empty = document.querySelector('[data-empty-state]');
    const run = () => {
      const query = (filterForm.querySelector('[name="q"]')?.value || '').trim().toLowerCase();
      const time = filterForm.querySelector('[name="time"]')?.value || '';
      const collection = filterForm.querySelector('[name="collection"]')?.value || '';
      const diet = filterForm.querySelector('[name="diet"]')?.value || '';
      let shown = 0;
      cards.forEach(card => {
        const search = card.dataset.search || '';
        const tags = card.dataset.tags || '';
        const minutes = Number(card.dataset.minutes || 999);
        const matches = (!query || search.includes(query)) &&
          (!time || minutes <= Number(time)) &&
          (!collection || card.dataset.collection === collection) &&
          (!diet || tags.includes(diet));
        card.hidden = !matches;
        if (matches) shown++;
      });
      if (count) count.textContent = `${shown} recipe${shown === 1 ? '' : 's'}`;
      if (empty) empty.classList.toggle('is-visible', shown === 0);
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (time) params.set('time', time);
      if (collection) params.set('collection', collection);
      if (diet) params.set('diet', diet);
      history.replaceState(null, '', `${location.pathname}${params.toString() ? '?' + params : ''}`);
    };
    const params = new URLSearchParams(location.search);
    ['q', 'time', 'collection', 'diet'].forEach(name => {
      const field = filterForm.querySelector(`[name="${name}"]`);
      if (field && params.get(name)) field.value = params.get(name);
    });
    filterForm.addEventListener('input', run);
    filterForm.addEventListener('change', run);
    filterForm.querySelector('[data-reset-filters]')?.addEventListener('click', () => {
      filterForm.reset();
      run();
    });
    run();
  }

  const recipePage = document.querySelector('[data-recipe-page]');
  if (recipePage) {
    const originalServings = Number(recipePage.dataset.servings);
    let servings = originalServings;
    const output = document.querySelector('[data-servings-output]');
    const ingredientEls = [...document.querySelectorAll('[data-ingredient]')];

    const parseFraction = token => {
      if (!token) return null;
      if (token.includes('/')) {
        const [a, b] = token.split('/').map(Number);
        return b ? a / b : null;
      }
      const n = Number(token);
      return Number.isFinite(n) ? n : null;
    };
    const toFraction = value => {
      const rounded = Math.round(value * 8) / 8;
      const whole = Math.floor(rounded + 1e-9);
      const fraction = Math.round((rounded - whole) * 8);
      const map = {1:'1/8',2:'1/4',3:'3/8',4:'1/2',5:'5/8',6:'3/4',7:'7/8'};
      if (!fraction) return String(whole);
      return `${whole ? whole + ' ' : ''}${map[fraction]}`;
    };
    const scaleText = (text, ratio) => text.replace(/^(\d+\s+\d+\/\d+|\d+\/\d+|\d+(?:\.\d+)?)(?=\s|$)/, raw => {
      const parts = raw.split(/\s+/);
      let number = 0;
      if (parts.length === 2) number = Number(parts[0]) + parseFraction(parts[1]);
      else number = parseFraction(parts[0]);
      return number == null ? raw : toFraction(number * ratio);
    });
    const updateServings = next => {
      servings = Math.max(1, Math.min(24, next));
      if (output) output.textContent = servings;
      const ratio = servings / originalServings;
      ingredientEls.forEach(el => { el.textContent = scaleText(el.dataset.original, ratio); });
    };
    document.querySelector('[data-serving-minus]')?.addEventListener('click', () => updateServings(servings - 1));
    document.querySelector('[data-serving-plus]')?.addEventListener('click', () => updateServings(servings + 1));
    document.querySelector('[data-print]')?.addEventListener('click', () => window.print());

    const cookMode = document.querySelector('[data-cook-mode]');
    let wakeLock = null;
    const releaseLock = async () => {
      if (wakeLock) { try { await wakeLock.release(); } catch {} }
      wakeLock = null;
    };
    document.querySelector('[data-open-cook]')?.addEventListener('click', async () => {
      cookMode?.classList.add('is-open');
      body.style.overflow = 'hidden';
      if ('wakeLock' in navigator) {
        try { wakeLock = await navigator.wakeLock.request('screen'); } catch {}
      }
    });
    document.querySelector('[data-close-cook]')?.addEventListener('click', async () => {
      cookMode?.classList.remove('is-open');
      body.style.overflow = '';
      await releaseLock();
    });
    document.addEventListener('visibilitychange', async () => {
      if (document.visibilityState === 'visible' && cookMode?.classList.contains('is-open') && 'wakeLock' in navigator) {
        try { wakeLock = await navigator.wakeLock.request('screen'); } catch {}
      }
    });
  }

  function recipeCard(recipe) {
    const tags = (recipe.tags || []).join(' ');
    return `<article class="recipe-card" data-recipe-card data-search="${escapeHtml((recipe.title + ' ' + recipe.dek + ' ' + tags).toLowerCase())}" data-tags="${escapeHtml(tags)}" data-collection="${recipe.collection}" data-minutes="${recipe.prep_minutes + recipe.cook_minutes}">
      <button class="icon-button recipe-card-save" data-save-recipe="${recipe.slug}" aria-label="Save recipe">♡</button>
      <a class="recipe-card-media" href="/recipes/${recipe.slug}/"><img src="${recipe.image}" alt="${escapeHtml(recipe.image_alt)}" loading="lazy"><span class="recipe-card-badge">${recipe.prep_minutes + recipe.cook_minutes} min</span></a>
      <div class="recipe-card-body"><h3><a href="/recipes/${recipe.slug}/">${escapeHtml(recipe.title)}</a></h3><p>${escapeHtml(recipe.dek)}</p><div class="recipe-card-meta"><span>⏱ ${recipe.prep_minutes + recipe.cook_minutes} min</span><span>${recipe.cost_per_serving}/serving</span></div></div>
    </article>`;
  }
  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }
  function renderSaved() {
    const grid = document.querySelector('[data-saved-grid]');
    if (!grid || !window.DISHGAL_RECIPES) return;
    const saved = getSaved();
    const matches = window.DISHGAL_RECIPES.filter(r => saved.includes(r.slug));
    grid.innerHTML = matches.length ? matches.map(recipeCard).join('') : '<div class="empty-state is-visible"><h3>No saved recipes yet</h3><p>Tap the heart on any recipe and it will live here on this device.</p><a class="btn btn-primary" href="/recipes/">Browse recipes</a></div>';
    syncSaveButtons();
  }
  renderSaved();

  const decider = document.querySelector('[data-decider]');
  if (decider && window.DISHGAL_RECIPES) {
    const state = { time: '', collection: '', tag: '' };
    decider.querySelectorAll('[data-choice]').forEach(button => {
      button.addEventListener('click', () => {
        const key = button.dataset.choice;
        state[key] = button.dataset.value;
        decider.querySelectorAll(`[data-choice="${key}"]`).forEach(b => b.classList.toggle('is-active', b === button));
      });
    });
    const show = recipe => {
      const target = decider.querySelector('[data-decider-result]');
      target.innerHTML = `<div class="tool-result-feature"><img src="${recipe.image}" alt="${escapeHtml(recipe.image_alt)}"><div><p class="eyebrow">Tonight's move</p><h2>${escapeHtml(recipe.title)}</h2><p class="lede">${escapeHtml(recipe.dek)}</p><div class="recipe-card-meta"><span>⏱ ${recipe.prep_minutes + recipe.cook_minutes} min</span><span>${recipe.cost_per_serving}/serving</span></div><div class="button-row" style="margin-top:1rem"><a class="btn btn-primary" href="/recipes/${recipe.slug}/">Make this</a><button class="btn btn-outline" type="button" data-reroll>Try another</button></div></div></div>`;
      target.querySelector('[data-reroll]').addEventListener('click', choose);
      target.scrollIntoView({behavior:'smooth', block:'center'});
    };
    const choose = () => {
      let pool = window.DISHGAL_RECIPES.filter(r => {
        const minutes = r.prep_minutes + r.cook_minutes;
        return (!state.time || minutes <= Number(state.time)) &&
          (!state.collection || r.collection === state.collection) &&
          (!state.tag || (r.tags || []).includes(state.tag));
      });
      if (!pool.length) pool = window.DISHGAL_RECIPES.filter(r => !state.time || r.prep_minutes + r.cook_minutes <= Number(state.time));
      if (!pool.length) pool = window.DISHGAL_RECIPES;
      show(pool[Math.floor(Math.random() * pool.length)]);
    };
    decider.querySelector('[data-decide]')?.addEventListener('click', choose);
  }

  const pantry = document.querySelector('[data-pantry-tool]');
  if (pantry && window.DISHGAL_RECIPES) {
    const run = () => {
      const selected = [...pantry.querySelectorAll('input[type="checkbox"]:checked')].map(i => i.value.toLowerCase());
      const extra = (pantry.querySelector('[name="extras"]')?.value || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
      const terms = [...selected, ...extra];
      const scored = window.DISHGAL_RECIPES.map(recipe => {
        const hay = [...(recipe.pantry || []), ...(recipe.ingredients || [])].join(' ').toLowerCase();
        const score = terms.reduce((n, term) => n + (hay.includes(term) ? 1 : 0), 0);
        return {recipe, score};
      }).filter(x => x.score > 0).sort((a,b) => b.score - a.score).slice(0, 8);
      const target = pantry.querySelector('[data-pantry-results]');
      target.innerHTML = scored.length ? `<p class="result-count">Best matches for ${terms.length} selected ingredient${terms.length === 1 ? '' : 's'}</p><div class="recipe-grid">${scored.map(x => recipeCard(x.recipe)).join('')}</div>` : '<div class="empty-state is-visible"><h3>Pick a few ingredients first</h3><p>We will rank recipes by ingredient overlap. Pantry staples like oil, salt, and pepper are assumed.</p></div>';
      syncSaveButtons();
      target.scrollIntoView({behavior:'smooth', block:'start'});
    };
    pantry.querySelector('[data-match-pantry]')?.addEventListener('click', run);
  }

  const planner = document.querySelector('[data-planner]');
  if (planner && window.DISHGAL_RECIPES) {
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    let current = [];
    const build = () => {
      const max = Number(planner.querySelector('[name="planner-time"]')?.value || 999);
      const vegetarian = planner.querySelector('[name="planner-vegetarian"]')?.checked;
      let pool = window.DISHGAL_RECIPES.filter(r => r.prep_minutes + r.cook_minutes <= max && (!vegetarian || (r.tags || []).includes('vegetarian') || (r.tags || []).includes('vegan')));
      if (pool.length < 5) pool = window.DISHGAL_RECIPES.filter(r => r.prep_minutes + r.cook_minutes <= max);
      const shuffled = [...pool].sort(() => Math.random() - .5);
      const chosen = [];
      const collections = new Set();
      for (const recipe of shuffled) {
        if (chosen.length >= 5) break;
        if (!collections.has(recipe.collection) || chosen.length >= 3) {
          chosen.push(recipe); collections.add(recipe.collection);
        }
      }
      current = chosen.slice(0,5);
      const grid = planner.querySelector('[data-plan-grid]');
      grid.innerHTML = current.map((r, i) => `<div class="plan-day"><img src="${r.image}" alt="${escapeHtml(r.image_alt)}"><small>${dayNames[i]}</small><strong><a href="/recipes/${r.slug}/">${escapeHtml(r.title)}</a></strong><span class="muted">${r.prep_minutes + r.cook_minutes} min</span></div>`).join('');
      planner.querySelector('[data-shopping-wrap]').hidden = true;
    };
    const shopping = () => {
      const all = current.flatMap(r => r.ingredients.map(item => ({item, recipe:r.title})));
      const target = planner.querySelector('[data-shopping-list]');
      target.innerHTML = all.map(x => `<li><label><input type="checkbox"> ${escapeHtml(x.item)} <small class="muted">(${escapeHtml(x.recipe)})</small></label></li>`).join('');
      planner.querySelector('[data-shopping-wrap]').hidden = false;
      planner.querySelector('[data-shopping-wrap]').scrollIntoView({behavior:'smooth'});
    };
    planner.querySelector('[data-build-plan]')?.addEventListener('click', build);
    planner.querySelector('[data-build-list]')?.addEventListener('click', shopping);
    build();
  }

  document.querySelectorAll('[data-current-year]').forEach(el => { el.textContent = new Date().getFullYear(); });
})();

(() => {
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-affiliate-active="true"]');
    if (!link) return;
    const detail = {
      event: 'affiliate_click',
      affiliate_network: link.dataset.affiliateNetwork || 'amazon',
      affiliate_tag: link.dataset.affiliateTag || 'dishgal-20',
      link_url: link.href,
      link_text: link.textContent.trim().replace(/\s+/g, ' ').slice(0, 120),
      page_path: location.pathname,
    };
    if (typeof window.gtag === 'function') window.gtag('event', 'affiliate_click', detail);
    else (window.dataLayer ||= []).push(detail);
  });
})();
