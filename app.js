/* ============================================================
   Objekt-Bestimmung Workshop 2026 — Browser tool
   ============================================================

   Layout of this file (navigation by section heading):

   1. CONFIG
   2. STATE
   3. LOADER
   4. INDEXES
   5. STATUS
   6. FILTERS
   7. RENDER — gallery
   8. RENDER — sidebar
   9. RENDER — detail page
  10. DASHBOARD
  11. ROUTER
  12. BOOT
*/

// ============================================================
// 1. CONFIG
// ============================================================
const DATA_PATHS = {
  thesaurus: "data/json/thesaurus.json",
  thesaurusFlat: "data/json/thesaurus_flat.json",
  objects: "data/json/objects.json",
  originals: "data/json/originals.json",
  aiBlind: "data/json/ai_blind.json",
  aiEnriched: "data/json/ai_enriched.json",
  aiJudge: "data/json/ai_judge.json",
};

// ============================================================
// 2. STATE
// ============================================================
const state = {
  thesaurus: null,
  thesaurusFlat: [],
  objects: [],
  filteredObjects: [],
  objectsById: new Map(),
  originalsById: new Map(),
  aiBlindById: new Map(),
  aiEnrichedById: new Map(),
  aiJudgeById: new Map(),
  filters: {
    topId: null,
    leafId: null,
    query: "",
    status: { match: true, conflict: true, noai: true },
    confusion: null, // { fromTop, toTop } — set by clicking a dashboard row
  },
  selectedId: null,
};

// Debounce helper for the search box — 150 ms feels instant but avoids
// re-rendering on every keystroke.
function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

// ============================================================
// 3. LOADER
// ============================================================

/**
 * Fetch a JSON file, return its parsed body or null on any failure.
 * Non-existent files (M2 vollauf artifacts before they exist) must not crash
 * the app — they simply produce empty state.
 */
async function fetchJsonOrNull(path) {
  try {
    const resp = await fetch(path);
    if (!resp.ok) return null;
    return await resp.json();
  } catch (err) {
    console.warn(`fetchJsonOrNull: ${path} failed`, err);
    return null;
  }
}

async function loadAll() {
  const [
    thesaurus,
    thesaurusFlat,
    objects,
    originals,
    aiBlind,
    aiEnriched,
    aiJudge,
  ] = await Promise.all([
    fetchJsonOrNull(DATA_PATHS.thesaurus),
    fetchJsonOrNull(DATA_PATHS.thesaurusFlat),
    fetchJsonOrNull(DATA_PATHS.objects),
    fetchJsonOrNull(DATA_PATHS.originals),
    fetchJsonOrNull(DATA_PATHS.aiBlind),
    fetchJsonOrNull(DATA_PATHS.aiEnriched),
    fetchJsonOrNull(DATA_PATHS.aiJudge),
  ]);

  state.thesaurus = thesaurus;
  state.thesaurusFlat = thesaurusFlat || [];
  state.objects = objects || [];

  buildIndex(state.objectsById, state.objects, "object_id");
  buildIndex(state.originalsById, originals || [], "object_id");
  buildIndex(state.aiBlindById, aiBlind || [], "object_id");
  buildIndex(state.aiEnrichedById, aiEnriched || [], "object_id");
  buildIndex(state.aiJudgeById, aiJudge || [], "object_id");
}

// ============================================================
// 4. INDEXES
// ============================================================
function buildIndex(target, list, key) {
  target.clear();
  for (const item of list) {
    target.set(item[key], item);
  }
}

/**
 * Full list of top-area codes present in the current object set, unique,
 * preserving insertion order for stable rendering.
 */
// ============================================================
// 5. STATUS
// ============================================================
/**
 * Derive the comparison status of a single object against its AI answers:
 *   "match"    — AI blind picked the same top area as the original
 *   "conflict" — AI blind picked a different top area than the original
 *   "noai"     — no AI data available yet (Vollauf hasn't reached this object)
 */
function statusFor(objectId) {
  const blind = state.aiBlindById.get(objectId);
  const enriched = state.aiEnrichedById.get(objectId);
  if (!blind && !enriched) return "noai";

  const orig = state.objectsById.get(objectId);
  if (blind && orig && blind.top_id && blind.top_id !== orig.top_id) return "conflict";

  return "match";
}

const STATUS_LABEL = {
  match: "🟢 Übereinstimmung",
  conflict: "🔴 Konflikt",
  noai: "⚪ keine KI",
};

// ============================================================
// 6. FILTERS
// ============================================================

/**
 * True if `obj` matches the lowercased free-text query `q`. An empty `q`
 * matches everything. Search scope = object name, term, medium, dimensions,
 * dated, plus the scraped original description.
 */
function matchesQuery(obj, q) {
  if (!q) return true;
  const orig = state.originalsById.get(obj.object_id);
  const haystack = [
    obj.object_name,
    obj.thesaurus_term,
    obj.medium,
    obj.dimensions,
    obj.dated,
    orig && orig.description,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

/**
 * Apply the current filter state to state.objects and write the result into
 * state.filteredObjects. This is the single source of truth for "what shows
 * in the gallery". The sidebar and gallery both read from filteredObjects.
 */
function applyFilters() {
  const { topId, leafId, query, status, confusion } = state.filters;
  const q = query.trim().toLowerCase();

  state.filteredObjects = state.objects.filter((obj) => {
    if (!status[statusFor(obj.object_id)]) return false;

    // Thesaurus filter — leaf wins if set, otherwise top
    if (leafId) {
      if (obj.thesaurus_id !== leafId) return false;
    } else if (topId) {
      if (obj.top_id !== topId) return false;
    }

    // Confusion filter — pins objects whose original top is X and whose
    // blind AI top is Y. Used by the dashboard „Verwechslungen"-list.
    if (confusion) {
      if (obj.top_id !== confusion.fromTop) return false;
      const b = state.aiBlindById.get(obj.object_id);
      if (!b || b.top_id !== confusion.toTop) return false;
    }

    if (!matchesQuery(obj, q)) return false;

    return true;
  });
}

function resetFilters() {
  state.filters.topId = null;
  state.filters.leafId = null;
  state.filters.query = "";
  state.filters.status = { match: true, conflict: true, noai: true };
  state.filters.confusion = null;

  const queryInput = document.getElementById("filter-query");
  if (queryInput) queryInput.value = "";
  for (const s of ["match", "conflict", "noai"]) {
    const cb = document.getElementById(`filter-status-${s}`);
    if (cb) cb.checked = true;
  }

  onFiltersChanged();
}

// ============================================================
// 7. RENDER — gallery (Inkrement A)
// ============================================================

function renderGalleryStats() {
  const el = document.getElementById("gallery-stats");
  if (!el) return;
  const total = state.objects.length;
  const shown = state.filteredObjects.length;
  const tops = new Set(state.filteredObjects.map((o) => o.top_id)).size;
  const terms = new Set(state.filteredObjects.map((o) => o.thesaurus_id)).size;
  const fraction = shown === total ? `${total}` : `${shown} von ${total}`;
  el.textContent = `${fraction} Objekte · ${tops} Bereiche · ${terms} Kategorien`;
}

function renderGallery() {
  const host = document.getElementById("gallery");
  if (!host) return;
  host.setAttribute("aria-busy", "false");
  host.innerHTML = "";

  if (state.filteredObjects.length === 0) {
    const empty = document.createElement("p");
    empty.className = "gallery__empty";
    empty.textContent = "Keine Objekte mit diesen Filtern.";
    host.appendChild(empty);
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const obj of state.filteredObjects) {
    fragment.appendChild(renderGalleryCard(obj));
  }
  host.appendChild(fragment);
}

function renderGalleryCard(obj) {
  const card = document.createElement("article");
  card.className = "gallery__card";
  card.dataset.objectId = String(obj.object_id);

  const status = statusFor(obj.object_id);
  const statusClass =
    status === "match" ? "ok" : status === "conflict" ? "err" : "mute";
  const pill = document.createElement("span");
  pill.className = `status-pill status-pill--${statusClass}`;
  pill.textContent = STATUS_LABEL[status];
  card.appendChild(pill);

  const thumb = document.createElement("div");
  thumb.className = "gallery__thumb";

  if (obj.image_local) {
    const img = document.createElement("img");
    img.loading = "lazy";
    img.src = obj.image_local;
    img.alt = obj.object_name || `Objekt ${obj.object_id}`;
    img.addEventListener("error", () => {
      thumb.classList.add("gallery__thumb--missing");
      thumb.textContent = "Bild fehlt";
    });
    thumb.appendChild(img);
  } else {
    thumb.classList.add("gallery__thumb--missing");
    thumb.textContent = "kein Bild";
  }
  card.appendChild(thumb);

  const body = document.createElement("div");
  body.className = "gallery__body";

  const name = document.createElement("div");
  name.className = "gallery__name";
  name.textContent = obj.object_name || "(ohne Namen)";
  body.appendChild(name);

  const term = document.createElement("div");
  term.className = "gallery__term";
  term.textContent = obj.thesaurus_term || "";
  body.appendChild(term);

  const top = document.createElement("div");
  top.className = "gallery__top";
  // path index 1 = Volkskunde top name, see 01_build_thesaurus.py
  top.textContent = (obj.thesaurus_path && obj.thesaurus_path[1]) || obj.top_id || "";
  body.appendChild(top);

  card.appendChild(body);

  card.addEventListener("click", () => {
    location.hash = `#/object/${obj.object_id}`;
  });

  return card;
}

// ============================================================
// 8. RENDER — sidebar (Inkrement B)
// ============================================================

/**
 * Render the thesaurus tree. We only show top areas plus their direct leaf
 * children (via the flat list grouped by top_id). Mid-levels are not clickable
 * because their CN codes don't have human-readable names anyway — see
 * knowledge/data.md.
 *
 * Each node shows its object count (after applying non-thesaurus filters, so
 * the tree reflects the current search/status scope).
 */
/**
 * Strip the redundant "Volkskunde – " prefix from a top-area term. The
 * prefix appears on every top name (this is a Volkskunde-only collection
 * and the sidebar panel is already titled „THESAURUS") — repeating it 20×
 * wastes horizontal space and forces line wraps.
 */
function stripTopPrefix(term) {
  if (!term) return "";
  return term.replace(/^Volkskunde\s*[–-]\s*/, "");
}

function renderThesaurusTree() {
  const host = document.getElementById("thesaurus-tree");
  if (!host || !state.thesaurus) return;
  host.innerHTML = "";

  // Count objects per (top_id, thesaurus_id) honoring all filters *except*
  // the thesaurus filter itself — so toggling a branch always shows sensible
  // numbers relative to the current query/status.
  const counts = countsIgnoringThesaurusFilter();

  const frag = document.createDocumentFragment();
  const topsSorted = [...state.thesaurus.children].sort((a, b) =>
    a.term.localeCompare(b.term)
  );

  for (const top of topsSorted) {
    const topCount = counts.byTop.get(top.id) || 0;
    if (topCount === 0) continue;

    const details = document.createElement("details");
    details.className = "thesaurus-tree__node";
    if (state.filters.topId === top.id) details.open = true;

    const summary = document.createElement("summary");
    const active = state.filters.topId === top.id && !state.filters.leafId;
    summary.innerHTML = `
      <span class="thesaurus-tree__top-label${active ? " thesaurus-tree__leaf--active" : ""}">
        ${escapeHtml(stripTopPrefix(top.term))}
        <span class="thesaurus-tree__count">${topCount}</span>
      </span>
    `;
    summary.addEventListener("click", (e) => {
      // Click on the label (not the caret area) toggles the top filter.
      // We prevent the default so the <details> doesn't collapse the panel
      // we're trying to open.
      e.preventDefault();
      details.open = true;
      if (state.filters.topId === top.id && !state.filters.leafId) {
        state.filters.topId = null;
      } else {
        state.filters.topId = top.id;
        state.filters.leafId = null;
      }
      onFiltersChanged();
    });
    details.appendChild(summary);

    // Only flat-leaf descendants of this top area, grouped under the top.
    const leaves = state.thesaurusFlat
      .filter((l) => l.top_id === top.id && (counts.byLeaf.get(l.id) || 0) > 0)
      .sort((a, b) => a.term.localeCompare(b.term));

    for (const leaf of leaves) {
      const leafCount = counts.byLeaf.get(leaf.id) || 0;
      const leafEl = document.createElement("a");
      leafEl.href = "#";
      leafEl.className = "thesaurus-tree__leaf";
      if (state.filters.leafId === leaf.id) {
        leafEl.classList.add("thesaurus-tree__leaf--active");
      }
      leafEl.innerHTML = `${escapeHtml(leaf.term)} <span class="thesaurus-tree__count">${leafCount}</span>`;
      leafEl.addEventListener("click", (e) => {
        e.preventDefault();
        if (state.filters.leafId === leaf.id) {
          state.filters.leafId = null;
        } else {
          state.filters.leafId = leaf.id;
          state.filters.topId = top.id;
        }
        onFiltersChanged();
      });
      details.appendChild(leafEl);
    }

    frag.appendChild(details);
  }

  if (!frag.childElementCount) {
    const p = document.createElement("p");
    p.className = "filter-sidebar__placeholder";
    p.textContent = "Keine passenden Bereiche.";
    host.appendChild(p);
    return;
  }

  host.appendChild(frag);
}

/**
 * Return two maps: objects per top_id and per thesaurus_id (leaf),
 * honoring the non-thesaurus filters (query + status). The thesaurus filter
 * itself is intentionally ignored so the tree always offers a way back.
 */
function countsIgnoringThesaurusFilter() {
  const { query, status } = state.filters;
  const q = query.trim().toLowerCase();

  const byTop = new Map();
  const byLeaf = new Map();

  for (const obj of state.objects) {
    if (!status[statusFor(obj.object_id)]) continue;
    if (!matchesQuery(obj, q)) continue;

    byTop.set(obj.top_id, (byTop.get(obj.top_id) || 0) + 1);
    byLeaf.set(obj.thesaurus_id, (byLeaf.get(obj.thesaurus_id) || 0) + 1);
  }

  return { byTop, byLeaf };
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * One central place to re-flow everything after a filter change. Called
 * by the sidebar event handlers.
 */
function onFiltersChanged() {
  applyFilters();
  renderGalleryStats();
  renderGallery();
  renderThesaurusTree();
  renderDashboard();
}

function wireSidebarEvents() {
  const queryInput = document.getElementById("filter-query");
  if (queryInput) {
    const handler = debounce((e) => {
      state.filters.query = e.target.value;
      onFiltersChanged();
    }, 150);
    queryInput.addEventListener("input", handler);
  }

  for (const s of ["match", "conflict", "noai"]) {
    const cb = document.getElementById(`filter-status-${s}`);
    if (!cb) continue;
    cb.addEventListener("change", () => {
      state.filters.status[s] = cb.checked;
      onFiltersChanged();
    });
  }

  const reset = document.getElementById("btn-reset");
  if (reset) reset.addEventListener("click", resetFilters);
}

// ============================================================
// 9. RENDER — detail page (Inkrement C)
// ============================================================

/**
 * Jump to the previous/next object in the currently filtered list.
 * Returns null if there is no neighbour.
 */
function neighbourId(direction) {
  const list = state.filteredObjects;
  const i = list.findIndex((o) => o.object_id === state.selectedId);
  if (i < 0) return null;
  const j = i + direction;
  if (j < 0 || j >= list.length) return null;
  return list[j].object_id;
}

function renderDetailView() {
  const root = document.getElementById("view-detail");
  if (!root || state.selectedId == null) return;

  const obj = state.objectsById.get(state.selectedId);
  if (!obj) {
    location.hash = "";
    return;
  }
  const original = state.originalsById.get(obj.object_id);
  const blind = state.aiBlindById.get(obj.object_id);
  const enriched = state.aiEnrichedById.get(obj.object_id);
  const judge = state.aiJudgeById.get(obj.object_id);

  const prevId = neighbourId(-1);
  const nextId = neighbourId(+1);

  root.innerHTML = "";

  const page = document.createElement("div");
  page.className = "detail-page";
  page.appendChild(renderDetailHeader(obj, prevId, nextId));
  page.appendChild(renderDetailBody(obj, original, blind, enriched, judge));
  root.appendChild(page);

  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function renderDetailHeader(obj, prevId, nextId) {
  const header = document.createElement("div");
  header.className = "detail-page__header";

  const back = document.createElement("a");
  back.href = "#";
  back.className = "detail-page__back";
  back.textContent = "← Zur Galerie";
  back.addEventListener("click", (e) => {
    e.preventDefault();
    location.hash = "";
  });
  header.appendChild(back);

  const titleWrap = document.createElement("div");
  titleWrap.className = "detail-page__title-wrap";
  const title = document.createElement("h2");
  title.className = "detail-page__title";
  title.textContent = obj.object_name || "(ohne Namen)";
  const meta = document.createElement("div");
  meta.className = "detail-page__meta";
  const topTerm = (obj.thesaurus_path && obj.thesaurus_path[1]) || obj.top_id;
  meta.textContent = `${obj.object_number || ""} · ${topTerm}`;
  titleWrap.appendChild(title);
  titleWrap.appendChild(meta);
  header.appendChild(titleWrap);

  const nav = document.createElement("div");
  nav.className = "detail-page__nav";
  nav.appendChild(makeDetailNavButton("←", prevId, "Vorheriges Objekt"));
  nav.appendChild(makeDetailNavButton("→", nextId, "Nächstes Objekt"));
  header.appendChild(nav);

  return header;
}

function makeDetailNavButton(label, targetId, title) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = label;
  btn.title = title;
  btn.disabled = targetId == null;
  btn.addEventListener("click", () => {
    if (targetId != null) location.hash = `#/object/${targetId}`;
  });
  return btn;
}

function renderDetailBody(obj, original, blind, enriched, judge) {
  const body = document.createElement("div");
  body.className = "detail-page__body";

  const photo = document.createElement("div");
  photo.className = "detail-page__photo";
  const img = document.createElement("img");
  img.src = obj.image_local;
  img.alt = obj.object_name || `Objekt ${obj.object_id}`;
  img.addEventListener("error", () => {
    photo.innerHTML = '<span class="variant-card__empty">Bild fehlt</span>';
  });
  photo.appendChild(img);
  body.appendChild(photo);

  const variants = document.createElement("div");
  variants.className = "detail-page__variants";
  variants.appendChild(renderVariantOriginal(obj, original));
  variants.appendChild(renderVariantAi(obj, blind, "ai-blind", "KI BLIND"));
  variants.appendChild(renderVariantAi(obj, enriched, "ai-enriched", "KI ERWEITERT"));
  variants.appendChild(renderVariantJudge(obj, judge));
  body.appendChild(variants);

  return body;
}

function variantCard(badgeText, klass, modelText) {
  const card = document.createElement("section");
  card.className = `variant-card variant-card--${klass}`;
  const header = document.createElement("div");
  header.className = "variant-card__header";
  const badge = document.createElement("span");
  badge.className = `variant-card__badge variant-card__badge--${klass}`;
  badge.textContent = badgeText;
  header.appendChild(badge);
  if (modelText) {
    const model = document.createElement("span");
    model.className = "variant-card__model";
    model.textContent = modelText;
    header.appendChild(model);
  }
  card.appendChild(header);
  return card;
}

function variantField(card, label, value) {
  if (value == null || value === "") return;
  const row = document.createElement("div");
  row.className = "variant-card__field";
  const l = document.createElement("div");
  l.className = "variant-card__field-label";
  l.textContent = label;
  const v = document.createElement("div");
  v.className = "variant-card__field-value";
  v.textContent = value;
  row.appendChild(l);
  row.appendChild(v);
  card.appendChild(row);
}

function renderVariantOriginal(obj, original) {
  const card = variantCard("ORIGINAL", "original", "Sammlungsdaten");

  // If the judge flagged this object's sammlungs-zuordnung as a quirk,
  // surface that on the Original card — it is the didactic point of the
  // workshop: „falsche" KI-Antworten sind oft korrekte, und das Original
  // selbst ist die Kuriosität.
  const judge = state.aiJudgeById.get(obj.object_id);
  if (judge && judge.is_collection_quirk) {
    const note = document.createElement("div");
    note.className = "variant-card__quirk";
    note.textContent = "Judge: Sammlungs-Quirk — Zuordnung folgt sammlungsinterner Konvention";
    card.appendChild(note);
  }

  variantField(card, "Term", obj.thesaurus_term || "");
  variantField(card, "Bereich", (obj.thesaurus_path && obj.thesaurus_path[1]) || obj.top_id || "");
  variantField(card, "Beschreibung", (original && original.description) || "");
  variantField(card, "Material", obj.medium || (original && original.medium) || "");
  variantField(card, "Maße", obj.dimensions || (original && original.dimensions) || "");
  variantField(card, "Datierung", obj.dated || "");
  variantField(card, "Inventar-Nr.", obj.object_number || "");

  if (obj.url_object) {
    const linkRow = document.createElement("div");
    linkRow.className = "variant-card__meta";
    const a = document.createElement("a");
    a.href = obj.url_object;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = "Onlinesammlung öffnen ↗";
    linkRow.appendChild(a);
    card.appendChild(linkRow);
  }
  return card;
}

function renderVariantAi(obj, record, klass, badgeText) {
  const card = variantCard(
    badgeText,
    klass,
    record ? record.model || "" : ""
  );
  if (!record) {
    const empty = document.createElement("div");
    empty.className = "variant-card__empty";
    empty.textContent = "Noch keine KI-Antwort.";
    card.appendChild(empty);
    return card;
  }

  // Inline match indicator against the original
  const topMatch = record.top_id === obj.top_id;
  const leafMatch = record.thesaurus_id === obj.thesaurus_id;

  variantField(
    card,
    "Bereich",
    `${record.top_term || record.top_id || ""}  ${topMatch ? "✓" : "✗"}`
  );
  variantField(
    card,
    "Term",
    `${record.thesaurus_term || record.thesaurus_id || ""}  ${leafMatch ? "✓" : "✗"}`
  );
  variantField(card, "Beschreibung", record.description || "");
  variantField(card, "Material", record.material || "");
  variantField(card, "Technik", record.technique || "");
  variantField(card, "Datierung", record.dating || "");
  variantField(card, "Confidence", record.confidence_note || "");
  if (record.stage1_reasoning) {
    variantField(card, "Stufe-1-Begründung", record.stage1_reasoning);
  }

  const meta = document.createElement("div");
  meta.className = "variant-card__meta";
  const pieces = [];
  if (record.prompt_version) pieces.push(`prompt ${record.prompt_version}`);
  if (record.tokens_input != null) pieces.push(`${record.tokens_input}+${record.tokens_output} tok`);
  if (record.latency_ms != null) pieces.push(`${record.latency_ms} ms`);
  meta.textContent = pieces.join(" · ");
  if (meta.textContent) card.appendChild(meta);

  return card;
}

function renderVariantJudge(obj, judge) {
  const card = variantCard(
    "JUDGE",
    "ai-judge",
    judge ? judge.judge_model || "" : ""
  );
  if (!judge) {
    const empty = document.createElement("div");
    empty.className = "variant-card__empty";
    empty.textContent = "Kein Judge-Urteil für dieses Objekt.";
    card.appendChild(empty);
    return card;
  }

  variantField(card, "Verdict", judge.verdict || "");
  variantField(
    card,
    "Judge wählt",
    `${judge.judge_top_id || ""}  ${judge.judge_top_id === obj.top_id ? "✓" : "✗"}`
  );
  variantField(card, "Sammlungs-Quirk", judge.is_collection_quirk ? "ja" : "nein");
  variantField(
    card,
    "Qualität",
    `blind ${judge.description_quality_blind || "–"} · enriched ${judge.description_quality_enriched || "–"}`
  );
  variantField(card, "Begründung", judge.reasoning || "");

  if (judge.prompt_improvement_hints && judge.prompt_improvement_hints.length) {
    const row = document.createElement("div");
    row.className = "variant-card__field";
    const l = document.createElement("div");
    l.className = "variant-card__field-label";
    l.textContent = "Hinweise";
    const ul = document.createElement("ul");
    ul.className = "variant-card__hints";
    for (const hint of judge.prompt_improvement_hints) {
      const li = document.createElement("li");
      li.textContent = hint;
      ul.appendChild(li);
    }
    row.appendChild(l);
    row.appendChild(ul);
    card.appendChild(row);
  }

  return card;
}

function wireDetailKeys() {
  document.addEventListener("keydown", (e) => {
    if (state.selectedId == null) return;
    // Ignore when user is typing in an input/textarea
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    if (e.key === "Escape") {
      location.hash = "";
    } else if (e.key === "ArrowLeft") {
      const id = neighbourId(-1);
      if (id != null) location.hash = `#/object/${id}`;
    } else if (e.key === "ArrowRight") {
      const id = neighbourId(+1);
      if (id != null) location.hash = `#/object/${id}`;
    }
  });
}

// ============================================================
// 10. DASHBOARD
// ============================================================

/**
 * Compute accuracy + judge metrics over the current filteredObjects set.
 * Returns null if no AI data is loaded.
 */
function computeDashboard() {
  if (state.aiBlindById.size === 0 && state.aiEnrichedById.size === 0) return null;

  const list = state.filteredObjects;
  let n = 0;
  let blindCount = 0, enrichedCount = 0;
  let blindTop = 0, blindLeaf = 0;
  let enrichedTop = 0, enrichedLeaf = 0;

  const confusions = new Map(); // key `fromTop|toTop` -> {fromTop, toTop, count}

  let judgeCount = 0;
  let quirks = 0;
  const verdicts = new Map();
  let qb = 0, qe = 0;

  for (const obj of list) {
    n++;
    const b = state.aiBlindById.get(obj.object_id);
    const e = state.aiEnrichedById.get(obj.object_id);
    const j = state.aiJudgeById.get(obj.object_id);

    if (b) {
      blindCount++;
      if (b.top_id === obj.top_id) blindTop++;
      else {
        const key = `${obj.top_id}|${b.top_id}`;
        const prev = confusions.get(key);
        if (prev) prev.count++;
        else confusions.set(key, { fromTop: obj.top_id, toTop: b.top_id, count: 1 });
      }
      if (b.thesaurus_id === obj.thesaurus_id) blindLeaf++;
    }
    if (e) {
      enrichedCount++;
      if (e.top_id === obj.top_id) enrichedTop++;
      if (e.thesaurus_id === obj.thesaurus_id) enrichedLeaf++;
    }
    if (j) {
      judgeCount++;
      if (j.is_collection_quirk) quirks++;
      if (j.verdict) verdicts.set(j.verdict, (verdicts.get(j.verdict) || 0) + 1);
      qb += j.description_quality_blind || 0;
      qe += j.description_quality_enriched || 0;
    }
  }

  const topConfusions = [...confusions.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  return {
    n,
    blindCount,
    enrichedCount,
    blindTop,
    blindLeaf,
    enrichedTop,
    enrichedLeaf,
    topConfusions,
    judgeCount,
    quirks,
    verdicts,
    qbMean: judgeCount ? qb / judgeCount : 0,
    qeMean: judgeCount ? qe / judgeCount : 0,
  };
}

function pct(n, d) {
  if (!d) return "–";
  return `${Math.round((100 * n) / d)} %`;
}

function topLabel(topId) {
  if (!topId) return "";
  const tree = state.thesaurus;
  if (tree && tree.children) {
    const node = tree.children.find((c) => c.id === topId);
    if (node) return node.term;
  }
  return topId;
}

function renderDashboard() {
  const host = document.getElementById("dashboard");
  const body = document.getElementById("dashboard-body");
  if (!host || !body) return;

  const m = computeDashboard();
  if (!m) {
    host.hidden = true;
    return;
  }
  host.hidden = false;

  body.innerHTML = "";
  body.appendChild(renderDashboardAccuracyPanel(m));
  body.appendChild(renderDashboardConfusionsPanel(m));
  body.appendChild(renderDashboardJudgePanel(m));
}

function renderDashboardAccuracyPanel(m) {
  const panel = document.createElement("div");
  panel.className = "dashboard__panel";
  panel.innerHTML = `
    <h3>KI-Akkuranz (im aktuellen Filter)</h3>
    <div class="dashboard__metric">
      <b>${pct(m.blindTop, m.blindCount)}</b>
      <span>Bereich blind (${m.blindTop}/${m.blindCount})</span>
    </div>
    <div class="dashboard__metric">
      <b>${pct(m.blindLeaf, m.blindCount)}</b>
      <span>Leaf-Term blind (${m.blindLeaf}/${m.blindCount})</span>
    </div>
    <div class="dashboard__metric">
      <b>${pct(m.enrichedTop, m.enrichedCount)}</b>
      <span>Bereich erweitert (${m.enrichedTop}/${m.enrichedCount})</span>
    </div>
    <div class="dashboard__metric">
      <b>${pct(m.enrichedLeaf, m.enrichedCount)}</b>
      <span>Leaf-Term erweitert (${m.enrichedLeaf}/${m.enrichedCount})</span>
    </div>
  `;
  return panel;
}

function renderDashboardConfusionsPanel(m) {
  const panel = document.createElement("div");
  panel.className = "dashboard__panel";

  const h = document.createElement("h3");
  h.textContent = "Häufigste Verwechslungen (blind)";
  panel.appendChild(h);

  if (state.filters.confusion) {
    panel.appendChild(renderActiveConfusionBanner(state.filters.confusion));
  }

  if (m.topConfusions.length === 0) {
    const empty = document.createElement("p");
    empty.className = "dashboard__empty";
    empty.textContent = "Keine Verwechslungen im aktuellen Filter.";
    panel.appendChild(empty);
    return panel;
  }

  const ul = document.createElement("ul");
  ul.className = "dashboard__list";
  for (const c of m.topConfusions) {
    ul.appendChild(renderConfusionListItem(c));
  }
  panel.appendChild(ul);
  return panel;
}

function renderActiveConfusionBanner({ fromTop, toTop }) {
  const active = document.createElement("p");
  active.className = "dashboard__note";
  active.textContent = `Gefiltert: ${topLabel(fromTop)} → ${topLabel(toTop)}. `;

  const clear = document.createElement("a");
  clear.href = "#";
  clear.textContent = "× zurücksetzen";
  clear.addEventListener("click", (e) => {
    e.preventDefault();
    state.filters.confusion = null;
    onFiltersChanged();
  });
  active.appendChild(clear);
  return active;
}

function renderConfusionListItem(c) {
  const li = document.createElement("li");
  li.className = "is-clickable";
  li.textContent = `${topLabel(c.fromTop)} → ${topLabel(c.toTop)} · ${c.count}×`;
  li.title = "Klicken, um diese Objekte zu filtern";
  li.addEventListener("click", () => {
    // Toggle — a click on the already-active pair clears the filter.
    const cur = state.filters.confusion;
    if (cur && cur.fromTop === c.fromTop && cur.toTop === c.toTop) {
      state.filters.confusion = null;
    } else {
      state.filters.confusion = { fromTop: c.fromTop, toTop: c.toTop };
      // A confusion filter implies we want conflicts visible.
      state.filters.status.conflict = true;
      const cb = document.getElementById("filter-status-conflict");
      if (cb) cb.checked = true;
    }
    onFiltersChanged();
  });
  return li;
}

function renderDashboardJudgePanel(m) {
  const panel = document.createElement("div");
  panel.className = "dashboard__panel";

  if (m.judgeCount === 0) {
    panel.innerHTML = `
      <h3>Judge</h3>
      <p class="dashboard__empty">Kein Judge-Urteil im aktuellen Filter.</p>
    `;
    return panel;
  }

  const verdictLines = [...m.verdicts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<li>${escapeHtml(k)} · ${v}×</li>`)
    .join("");

  panel.innerHTML = `
    <h3>Judge (${m.judgeCount} bewertet)</h3>
    <div class="dashboard__metric dashboard__metric--hero">
      <b>${m.quirks} / ${m.judgeCount}</b>
      <span>Original = Sammlungs-Quirk</span>
    </div>
    <p class="dashboard__note">
      In diesen Fällen ist nicht die KI falsch, sondern die
      Sammlungs-Zuordnung folgt einer internen Konvention.
    </p>
    <div class="dashboard__metric">
      <b>${m.qbMean.toFixed(1)}</b>
      <span>Quality blind (Ø 1–5)</span>
    </div>
    <div class="dashboard__metric">
      <b>${m.qeMean.toFixed(1)}</b>
      <span>Quality erweitert (Ø 1–5)</span>
    </div>
    <ul class="dashboard__list">${verdictLines}</ul>
  `;
  return panel;
}

// ============================================================
// 11. ROUTER
// ============================================================

/**
 * Very small hash router.
 *   #            → gallery
 *   #/           → gallery
 *   #/object/:id → detail page
 */
function parseRoute() {
  const h = location.hash.replace(/^#\/?/, "");
  if (!h) return { name: "gallery" };
  const m = h.match(/^object\/(\d+)$/);
  if (m) return { name: "detail", id: Number(m[1]) };
  return { name: "gallery" };
}

function showView(name) {
  const gallery = document.getElementById("view-gallery");
  const detail = document.getElementById("view-detail");
  if (!gallery || !detail) return;
  gallery.hidden = name !== "gallery";
  detail.hidden = name !== "detail";
}

function handleRoute() {
  const route = parseRoute();
  if (route.name === "detail") {
    state.selectedId = route.id;
    showView("detail");
    renderDetailView();
  } else {
    state.selectedId = null;
    showView("gallery");
    // Nothing to rerender — the gallery state was already drawn and
    // was only hidden while the detail view was visible.
  }
}

// ============================================================
// 12. BOOT
// ============================================================
async function boot() {
  await loadAll();
  applyFilters();
  renderGalleryStats();
  renderGallery();
  renderThesaurusTree();
  renderDashboard();
  wireSidebarEvents();
  wireDetailKeys();

  window.addEventListener("hashchange", handleRoute);
  handleRoute();
}

document.addEventListener("DOMContentLoaded", boot);
