# Design-Spezifikation

UI-Referenz für den Vergleichs-Viewer. Beschreibt den **realisierten** Stand (Commit `448819b` + Abschlussphase 2026-04-12 ff.) — keine historischen Drawer- oder Editor-Mockups.

## Designprinzipien

- **Funktional, nicht dekorativ.** Werkzeug für Fachleute, kein Marketing.
- **Hoher Kontrast, große Schrift.** Beamer-tauglich, Workshop-Setting.
- **Bilder dominieren.** Text ist Service.
- **Status sofort sichtbar.** Farbe + Icon, nie nur Farbe (Accessibility).
- **Kein Framework, kein Build.** Vanilla HTML + CSS + JS, direkt aus dem Repo bedienbar.
- **Read-Only.** Die Site vergleicht, sie editiert nicht. Keine Form-Felder, kein Export, kein localStorage. Siehe ADR-14.

## Farbpalette

CSS Custom Properties in `style.css` unter `:root`.

| Token | Hex | Verwendung |
|---|---|---|
| `--bg` | `#FFFFFF` | Haupthintergrund |
| `--bg-alt` | `#F5F5F5` | Sidebar, Karten-Hover |
| `--bg-panel` | `#FAFAFA` | Detail-Panel, Dashboard-Bodies |
| `--border` | `#E0E0E0` | Trennlinien |
| `--text` | `#333333` | Body-Text |
| `--text-mute` | `#666666` | Sekundärtext, Counts |
| `--accent` | `#009B91` | Teal, Aktionen, Active-States |
| `--accent-strong` | `#00766F` | Hover/Press |
| `--ai-blind` | `#7B61FF` | KI-Blind-Badge |
| `--ai-enriched` | `#3D8BFF` | KI-Enriched-Badge |
| `--ai-corrected` | `#1A3A5F` | Korrektor-Badge (dunkel = stärkeres Modell) |
| `--ground-truth` | `#5B7C99` | Original-Badge |
| `--ok` | `#2E8540` | Übereinstimmung (🟢) |
| `--warn` | `#E08A00` | Banner „Kuratorische Prüfung empfohlen", Hero-Metric |
| `--err` | `#C8362D` | Konflikt (🔴) |
| `--mute` | `#9E9E9E` | keine KI-Daten (⚪) |

## Typografie

- System-Font-Stack: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`
- Skala: 14 / 16 / 18 / 22 / 28 / 36 px
- Body 16 px, Filterlabels 14 px, Thesaurus-Tree 13 px, Detail-Heading 22 px, Galerie-Titel 18 px
- Counts in `tabular-nums` — Stellen stehen untereinander ausgerichtet

## Routen

Hash-Router mit zwei Routen (siehe ADR-15):

| Hash | View | Zustand |
|---|---|---|
| `#` oder leer oder `#/` | `#view-gallery` | Filter-Sidebar + Dashboard + Galerie |
| `#/object/:id` | `#view-detail` | Detail-Seite eines Objekts |

Beim Routing toggled `app.js` das `hidden`-Attribut der beiden View-Container. ESC in der Detail-Seite navigiert zurück auf `#/`, Browser-Back funktioniert nativ.

## Layout — Gallery-View (`#/`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER  Objekt-Bestimmung · Workshop-Demo                            │
├───────────────┬──────────────────────────────────────────────────────┤
│ FILTER        │ 245 Objekte · 20 Bereiche · 225 Kategorien           │
│               ├──────────────────────────────────────────────────────┤
│ Suche         │ ▼ Modell-Auswertung (default open, collapsible)      │
│ [_________]   │                                                      │
│               │ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                  │
│ KI vs Orig    │ │🟢 │ │🔴 │ │🟢 │ │⚪ │ │🟢 │ │🟢 │                  │
│ ☑ Übereinst.  │ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘                  │
│ ☑ Konflikt    │  Beutel Fächer  ...                                  │
│ ☑ keine KI    │                                                      │
│               │ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                  │
│ THESAURUS     │ │   │ │   │ │   │ │   │ │   │ │   │                  │
│ ▶ Architek. 9 │ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘                  │
│ ▶ Bildwerke13 │                                                      │
│ ▶ Brauch 10   │                                                      │
│ ▶ …           │                                                      │
│               │                                                      │
│ [Reset]       │                                                      │
└───────────────┴──────────────────────────────────────────────────────┘
```

Der Status-Filter hat drei Zustände (FR-5): *Übereinstimmung* (🟢 grün — KI-blind Top-Bereich passt zum Original), *Konflikt* (🔴 rot — KI-blind weicht ab), *keine KI* (⚪ grau — Objekt hat keine KI-Daten). Kein „ungeprüft/freigegeben".

## Layout — Dashboard (collapsible `<details>` über der Galerie)

Drei Panels nebeneinander in einem CSS-Grid. Jedes Panel liest aus `state.filteredObjects`, Zahlen bleiben im Kontext des aktuellen Filters.

```
┌──────────────────────────────────┬────────────────────────────────┬────────────────────────────────────┐
│ Treffergenauigkeit               │ Häufigste Verwechslungen       │ Korrektur · finale Fassung (30)    │
│ 50 %  Bereich · Nur Foto 123/245 │ Landwirt. → Handwerk · 7×      │ 70 %  Bereich · final 21/30        │
│ 25 %  Leaf   · Nur Foto  62/245  │ Architektur → Wohnen · 6×      │ 43 %  Unterkat · final 13/30       │
│ 61 %  Bereich · F+M     150/245  │ Bildwerke → Religion · 4×      │ 4     Bereichs-Änderungen (2 +)    │
│ 35 %  Leaf   · F+M       85/245  │ …                              │ 24    Objekte mit Korrekturen      │
│                                  │   [klickbar → Filter]          │ 9     für kuratorische Prüfung     │
└──────────────────────────────────┴────────────────────────────────┴────────────────────────────────────┘
```

*F = Nur Foto, F+M = Foto + Metadaten.*

Die Konfusions-Zeilen sind klickbar: ein Klick pinnt einen Filter `confusion = {fromTop, toTop}`, die Galerie zeigt daraufhin nur die Objekte, bei denen das Original im einen und das *Nur-Foto*-Modell im anderen Bereich klassifiziert. Ein „× zurücksetzen"-Link im Panel räumt den Filter auf. Das ist die Drill-Down-Interaktion für den Vortrag: „welche Werkzeuge landen beim Modell in Handwerk, obwohl die Sammlung sie woanders einordnet?"

Das „Volkskunde – "-Präfix wird in der Konfusions-Liste strip-gerendert (siehe `topLabel()` in `app.js`), weil beide Seiten des Pfeils denselben Präfix tragen und er als Redundanz stört.

Im Korrektor-Panel steht die Top-Match-Quote der finalen Fassung als Hero-Metric. Daneben werden drei weitere Kennzahlen geführt: Anzahl der Bereichs-Änderungen gegenüber dem Enriched-Lauf (und in Klammern, wie viele davon zum richtigen Treffer führten), Anzahl der Objekte mit angewandten Korrekturen (d.h. `corrections_applied` ist nicht leer), und Anzahl der für kuratorische Prüfung geflaggten Objekte (`curator_review_needed = true`). Der Erklärtext betont: der Korrektor produziert eine Auditspur, der Mensch übernimmt gezielt dort, wo die KI auf ihre Grenzen stößt.

## Layout — Detail-Seite (`#/object/:id`)

Kein Drawer, keine Overlay-Slide-Animation — eine echte Unterseite, die die Galerie ersetzt.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Zur Galerie   Beutel                                    [ ← ][ → ] │
│                 VK-20440 · Volkskunde – Kleidung                     │
├──────────────────────────────┬───────────────────────────────────────┤
│                              │ ◉ ORIGINAL                            │
│                              │ [Banner: Sammlungs-Quirk]             │
│                              │ Term: Accessoires                     │
│                              │ Bereich: Kleidung                     │
│       [GROßES FOTO]          │ Beschreibung: …                       │
│       (linke Spalte)         │ Material: Stoff, vernäht              │
│                              │ Maße: 17 × 14,5 cm                    │
│       sticky auf scroll      │ Inventar-Nr.: VK-20440                │
│                              │ [Onlinesammlung öffnen ↗]             │
│                              │                                       │
│                              │ ◉ VISION-LLM · NUR FOTO               │
│                              │   gemini-3.1-flash-lite-preview       │
│                              │   /„Das Modell sieht nur das Foto …"/ │
│                              │ Bereich: Accessoires ✓                │
│                              │ Term: Gürtel ✗                        │
│                              │ Beschreibung: …                       │
│                              │ Material / Technik / Datierung        │
│                              │ Confidence: …                         │
│                              │ Bereichs-Begründung: …                │
│                              │                                       │
│                              │ ◉ VISION-LLM · FOTO + METADATEN       │
│                              │   /„Das Modell sieht das Foto plus …"/│
│                              │ (gleiche Felder)                      │
│                              │                                       │
│                              │ ◉ KORREKTUR · FINALE FASSUNG          │
│                              │   gemini-3.1-pro-preview              │
│                              │   /„Ein stärkeres Modell prüft und …"/│
│                              │ Bereich: … ✓                          │
│                              │ Unterkategorie: … ✓                   │
│                              │ Finale Beschreibung: …                │
│                              │ Konfidenz-Notiz: …                    │
│                              │ [Banner: Kuratorische Prüfung]        │
│                              │ Angewandte Korrekturen: …             │
│                              │ Bereichs-Begründung: …                │
└──────────────────────────────┴───────────────────────────────────────┘
```

**Header:** Back-Link zur Galerie (erhält Filter-State), Titel mit Objektname + Untertitel (Inventarnummer + Bereich-Name), Prev/Next-Buttons navigieren durch die **gefilterten** Nachbarn — nicht durch die gesamten 245. Disable am Ende/Anfang.

**Body:** Zweispaltiges CSS-Grid. Links das große Foto, rechts vier `.variant-card` stapeln sich: Original (Sammlungsdaten), Vision-LLM mit nur dem Foto, Vision-LLM mit Foto + Metadaten, Korrektur (finale Fassung). Jede Karte hat unter dem Badge eine `.variant-card__subtitle`-Zeile (kursiv, muted), die in einem Satz erklärt, was *dieses* Modell gesehen hat — das ist die didaktische Kernbotschaft pro Karte. Der Korrektur-Slot bleibt bei Objekten außerhalb des Sample-Laufs leer und zeigt eine `variant-card__empty`-Zeile.

**Banner für kuratorische Prüfung:** Bei Objekten mit `ai_corrected.curator_review_needed === true` erscheint auf der Original-Karte ein gelber Banner direkt unter dem Badge: *„Korrektor: Zuordnung aus Evidenzmaterial nicht eindeutig — Sammlungs-Eigenheit, kuratorische Prüfung empfohlen"*. Das ist nicht Cosmetic, sondern der Moment, in dem die Treffergenauigkeits-Prozente vom Dashboard eine Erklärung bekommen.

**Mobile-Fallback:** Unter 900 px wird das Grid einspaltig (Foto oben, Varianten darunter), das Foto ist `position: static` und `max-height: 50vh`. Mobile ist kein Primärziel (NFR fehlt), aber die Seite bricht nicht.

## Komponenten (BEM-light in `style.css`)

- `.app-header` — oben, Projekttitel + Link zu `knowledge/README.md`
- `.app-main` — Container für beide Views
- `.view--gallery`, `.view--detail` — View-Container, per `hidden`-Attribut getoggelt
- `.filter-sidebar` — links, Filter-Controls. Enthält Suchfeld, Status-Checkboxes, Thesaurus-Tree, Reset-Button.
- `.thesaurus-tree`, `.thesaurus-tree__node`, `.thesaurus-tree__top-label`, `.thesaurus-tree__leaf`, `.thesaurus-tree__leaf--active`, `.thesaurus-tree__count` — collapsible Tree via `<details>`. „Volkskunde – "-Präfix wird auf der Anzeige-Ebene gestrippt, Rohdaten bleiben unverändert.
- `.dashboard`, `.dashboard__summary`, `.dashboard__body` — `<details>`-Element mit drei Panels
- `.dashboard__panel` — einzelnes Panel (Grid-Zelle im Dashboard)
- `.dashboard__metric`, `.dashboard__metric--hero` — Zahlen-Zeile, Hero-Variante für Quirks
- `.dashboard__note` — Erklärtext unter Hero-Metric
- `.dashboard__list`, `.is-clickable` — Konfusions-Liste mit klickbaren Einträgen
- `.gallery-section`, `.gallery` — Gallery-Container
- `.gallery__card`, `.gallery__thumb`, `.gallery__body`, `.gallery__name`, `.gallery__term`, `.gallery__top` — Objektkarte
- `.status-pill`, `.status-pill--ok/--err/--mute` — Status-Badge auf Galerie-Karten
- `.status-dot` — kleiner farbiger Punkt neben Checkboxes
- `.detail-page`, `.detail-page__header`, `.detail-page__back`, `.detail-page__title-wrap`, `.detail-page__title`, `.detail-page__meta`, `.detail-page__nav` — Detail-Seiten-Chrome
- `.detail-page__body`, `.detail-page__photo`, `.detail-page__variants` — Zwei-Spalten-Layout der Detail-Seite
- `.variant-card` — eine Variante
- `.variant-card--original` / `--ai-blind` / `--ai-enriched` / `--ai-corrected` — Farbvariante pro Quelle
- `.variant-card__header`, `.variant-card__badge`, `.variant-card__model` — Karten-Header
- `.variant-card__subtitle` — kursive Erklärzeile direkt unter dem Header: *„Das Modell sieht nur das Foto, keine Metadaten."* etc.
- `.variant-card__field`, `.variant-card__field-label`, `.variant-card__field-value` — Datenzeile
- `.variant-card__meta`, `.variant-card__hints`, `.variant-card__empty` — Footer und Spezialzeilen
- `.variant-card__quirk` — gelber Banner „Kuratorische Prüfung empfohlen" auf der Original-Karte
- `.match-mark`, `.match-mark--ok/--err` — grüne/rote ✓/✗-Markierung neben KI-Werten

## Interaktion

- **Filter wirken sofort.** Kein „Anwenden"-Button. Freitext-Input ist debounced 150 ms.
- **Galerie ohne virtuelles Scrollen** — 245 Items sind unkritisch. Bilder sind `loading="lazy"`.
- **Karten-Hover:** leichte Elevation (shadow), Cursor Pointer.
- **Klick auf Galerie-Karte:** setzt `location.hash = "#/object/:id"`, der Router rendert die Detail-Seite und scrollt nach oben.
- **Thesaurus-Tree:** Klick auf die Top-Zeile toggled den Top-Filter. Klick auf eine Leaf-Zeile setzt den Leaf-Filter (und automatisch den zugehörigen Top). Klick auf aktive Zeile räumt auf. Counts reflektieren alle *anderen* aktiven Filter (Freitext, Status), damit das Navigieren konsistent bleibt.
- **Dashboard-Konfusionen klickbar:** Pinnt `{fromTop, toTop}`-Filter, aktiviert automatisch den „Konflikt"-Status-Filter. „× zurücksetzen" im aktiven Banner räumt auf.
- **Detail-Seite Prev/Next:** Pfeiltasten ← / → UND Buttons im Header navigieren durch die gefilterten Nachbarn.
- **ESC auf Detail-Seite:** zurück zur Galerie. Filter bleiben erhalten.
- **Keine Tastatur-Shortcuts in der Galerie** — bewusste Projektentscheidung. Kein Sprung-Fokus, kein „/" für Suche, keine Zahlen-Tasten für Filter. Die Einzige Ausnahme ist die ESC/Arrow-Navigation innerhalb der Detail-Seite, weil sie für beamergestützte Vorträge essentiell ist.

## Responsivität

- Breiter Desktop: Full Layout wie oben.
- Schmaler Viewport (<900 px): Detail-Seite wird einspaltig, Sidebar der Galerie rutscht nicht weg (kein Mobile-Primärziel).
- Beamer-Empfehlung: Browser-Zoom 125 %, Fenster Vollbild. Kontrast ist `#333333` auf `#FFFFFF` (WCAG-konform) — falls der Beamer zu grau ist, Quick-Fix `--text: #333333` → `#000000` in `style.css`.
